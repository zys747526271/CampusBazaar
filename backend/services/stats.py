"""经营与运营统计（PRD FR-SELL-07 / FR-ADMN-02）。"""
from __future__ import annotations

from datetime import timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select

from backend.constants import OrderStatus, ProductStatus, ReportStatus
from backend.extensions import db
from backend.models import Comment, Order, OrderItem, Product, Report, User
from backend.utils.common import CST, money, utcnow


def _day_start_utc(days_ago: int = 0):
    now_cst = utcnow().astimezone(CST) - timedelta(days=days_ago)
    start = now_cst.replace(hour=0, minute=0, second=0, microsecond=0)
    return start.astimezone(timezone.utc)


def _sum_amount(query) -> Decimal:
    value = query.scalar()
    return Decimal(value or 0)


def seller_overview(seller_id: int) -> dict:
    total_sales = _sum_amount(
        db.session.query(func.coalesce(func.sum(Order.total_amount), 0)).filter(
            Order.seller_id == seller_id, Order.status == OrderStatus.DONE
        )
    )
    today_sales = _sum_amount(
        db.session.query(func.coalesce(func.sum(Order.total_amount), 0)).filter(
            Order.seller_id == seller_id,
            Order.status == OrderStatus.DONE,
            Order.finished_at >= _day_start_utc(),
        )
    )
    product_query = Product.query.filter(Product.seller_id == seller_id, Product.is_deleted.is_(False))
    status_counts = dict(
        db.session.execute(
            select(Order.status, func.count(Order.id)).where(Order.seller_id == seller_id).group_by(Order.status)
        ).all()
    )
    views = db.session.query(func.coalesce(func.sum(Product.views), 0)).filter(
        Product.seller_id == seller_id, Product.is_deleted.is_(False)
    ).scalar() or 0

    recent_orders = (
        Order.query.filter(Order.seller_id == seller_id).order_by(Order.created_at.desc()).limit(5).all()
    )
    top_products = (
        Product.query.filter(Product.seller_id == seller_id, Product.is_deleted.is_(False))
        .order_by(Product.sales.desc(), Product.views.desc())
        .limit(5)
        .all()
    )

    from backend.services.serializers import order_view, product_seller_view

    return {
        "today_sales": money(today_sales),
        "total_sales": money(total_sales),
        "today_orders": int(
            db.session.query(func.count(Order.id))
            .filter(Order.seller_id == seller_id, Order.created_at >= _day_start_utc())
            .scalar()
            or 0
        ),
        "total_orders": int(sum(status_counts.values())),
        "pending_ship": int(status_counts.get(OrderStatus.PAID, 0)),
        "refunding": int(status_counts.get(OrderStatus.REFUNDING, 0)),
        "unpaid": int(status_counts.get(OrderStatus.UNPAID, 0)),
        "product_count": product_query.count(),
        "on_sale_count": product_query.filter(
            Product.status == ProductStatus.APPROVED, Product.is_available.is_(True), Product.quantity > 0
        ).count(),
        "pending_audit": product_query.filter(Product.status == ProductStatus.PENDING).count(),
        "total_views": int(views),
        "recent_orders": [order_view(o, "seller") for o in recent_orders],
        "top_products": [product_seller_view(p) for p in top_products],
    }


def admin_overview() -> dict:
    today = _day_start_utc()
    user_total = User.query.filter(User.is_deleted.is_(False)).count()
    user_today = User.query.filter(User.is_deleted.is_(False), User.created_at >= today).count()
    seller_total = User.query.filter(User.is_deleted.is_(False), User.is_seller.is_(True)).count()
    product_total = Product.query.filter(Product.is_deleted.is_(False)).count()
    product_on_sale = Product.query.filter(
        Product.is_deleted.is_(False),
        Product.status == ProductStatus.APPROVED,
        Product.is_available.is_(True),
        Product.quantity > 0,
    ).count()
    product_pending = Product.query.filter(
        Product.is_deleted.is_(False), Product.status == ProductStatus.PENDING
    ).count()
    order_total = Order.query.count()
    order_today = Order.query.filter(Order.created_at >= today).count()
    gmv = _sum_amount(
        db.session.query(func.coalesce(func.sum(Order.total_amount), 0)).filter(Order.status == OrderStatus.DONE)
    )
    gmv_today = _sum_amount(
        db.session.query(func.coalesce(func.sum(Order.total_amount), 0)).filter(
            Order.status == OrderStatus.DONE, Order.finished_at >= today
        )
    )
    pending_reports = Report.query.filter(Report.status == ReportStatus.PENDING).count()
    comment_total = Comment.query.filter(Comment.is_deleted.is_(False)).count()

    return {
        "users": {"total": user_total, "today": user_today, "sellers": seller_total},
        "products": {"total": product_total, "on_sale": product_on_sale, "pending": product_pending},
        "orders": {"total": order_total, "today": order_today},
        "gmv": {"total": money(gmv), "today": money(gmv_today)},
        "moderation": {
            "pending_products": product_pending,
            "pending_reports": pending_reports,
            "comments": comment_total,
        },
        "trend": trend_7d(),
    }


def trend_7d() -> list[dict]:
    """最近 7 天（含今天）的订单量与成交额，供后台折线图使用。"""
    start = _day_start_utc(days_ago=6)
    rows = db.session.execute(
        select(
            func.date(Order.created_at).label("day"),
            func.count(Order.id),
            func.coalesce(func.sum(Order.total_amount), 0),
        )
        .where(Order.created_at >= start)
        .group_by(func.date(Order.created_at))
    ).all()
    bucket = {str(row[0]): {"orders": int(row[1]), "amount": money(row[2])} for row in rows}
    result = []
    for offset in range(6, -1, -1):
        day = (_day_start_utc(days_ago=offset)).astimezone(CST).date().isoformat()
        item = bucket.get(day, {"orders": 0, "amount": 0.0})
        result.append({"date": day, "orders": item["orders"], "amount": item["amount"]})
    return result


def seller_order_stats(seller_id: int) -> dict:
    rows = db.session.execute(
        select(Order.status, func.count(Order.id)).where(Order.seller_id == seller_id).group_by(Order.status)
    ).all()
    counts = {status: 0 for status in OrderStatus.ALL}
    for status, count in rows:
        counts[status] = int(count)
    return counts


def product_sales(product_id: int) -> dict:
    """已售 = 已完成订单中该商品的数量之和（PRD FR-SELL-05）。"""
    quantity = (
        db.session.query(func.coalesce(func.sum(OrderItem.quantity), 0))
        .join(Order, Order.id == OrderItem.order_id)
        .filter(OrderItem.product_id == product_id, Order.status == OrderStatus.DONE)
        .scalar()
        or 0
    )
    revenue = (
        db.session.query(func.coalesce(func.sum(OrderItem.price * OrderItem.quantity), 0))
        .join(Order, Order.id == OrderItem.order_id)
        .filter(OrderItem.product_id == product_id, Order.status == OrderStatus.DONE)
        .scalar()
        or 0
    )
    return {"sold": int(quantity), "revenue": money(revenue)}
