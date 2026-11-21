"""商品查询与聚合：买家可见性、筛选排序、卖家统计、首页区块。"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, or_, select

from backend.constants import OrderStatus, ProductCondition, ProductStatus
from backend.extensions import db
from backend.models import Comment, Order, OrderItem, Product, Tag
from backend.utils.response import normalize_sort
from backend.utils.validators import escape_like, normalize_keyword


def visible_query():
    """买家侧唯一可见口径（PRD 3.2）：已通过 + 上架 + 有库存 + 未删除。"""
    return Product.query.filter(
        Product.status == ProductStatus.APPROVED,
        Product.is_available.is_(True),
        Product.quantity > 0,
        Product.is_deleted.is_(False),
    )


def apply_filters(query, args) -> object:
    keyword = normalize_keyword(args.get("keyword"))
    if keyword:
        pattern = f"%{escape_like(keyword)}%"
        query = query.filter(
            or_(Product.name.ilike(pattern, escape="\\"), Product.description.ilike(pattern, escape="\\"))
        )

    tag_id = args.get("tag_id", type=int)
    if tag_id:
        query = query.filter(Product.tag_id == tag_id)

    seller_id = args.get("seller_id", type=int)
    if seller_id:
        query = query.filter(Product.seller_id == seller_id)

    min_price = args.get("min_price", type=float)
    if min_price is not None:
        query = query.filter(Product.price >= Decimal(str(min_price)))
    max_price = args.get("max_price", type=float)
    if max_price is not None:
        query = query.filter(Product.price <= Decimal(str(max_price)))

    condition = (args.get("condition") or "").strip()
    if condition in ProductCondition.ALL:
        query = query.filter(Product.product_condition == condition)

    if args.get("featured") in ("1", "true"):
        query = query.filter(Product.is_featured.is_(True))

    # 履约筛选：自提 / 快递 / 包邮（v2.2）
    delivery = (args.get("delivery") or "").strip()
    if delivery == "pickup":
        query = query.filter(Product.supports_pickup.is_(True))
    elif delivery == "express":
        query = query.filter(Product.supports_express.is_(True))
    if args.get("free_shipping") in ("1", "true"):
        query = query.filter(Product.supports_express.is_(True), Product.free_shipping.is_(True))

    return query


def apply_sort(query, args):
    key, direction = normalize_sort(args.get("sort"), args.get("order"))
    column = {
        "price": Product.price,
        "sales": Product.sales,
        "views": Product.views,
        "created_at": Product.created_at,
    }[key]
    # 同分时用 id 兜底，保证翻页稳定不重复
    if direction == "asc":
        return query.order_by(column.asc(), Product.id.desc())
    return query.order_by(column.desc(), Product.id.desc())


def seller_stats_map(seller_ids: list[int]) -> dict[int, dict]:
    """批量算卖家评分与成交，避免列表页 N+1 查询。"""
    if not seller_ids:
        return {}
    ids = list(set(seller_ids))

    sold_rows = db.session.execute(
        select(Order.seller_id, func.coalesce(func.sum(OrderItem.quantity), 0))
        .join(OrderItem, OrderItem.order_id == Order.id)
        .where(Order.seller_id.in_(ids), Order.status == OrderStatus.DONE)
        .group_by(Order.seller_id)
    ).all()
    sold = {row[0]: int(row[1] or 0) for row in sold_rows}

    rating_rows = db.session.execute(
        select(
            Product.seller_id,
            func.avg(Comment.rating),
            func.count(Comment.id),
        )
        .join(Comment, Comment.product_id == Product.id)
        .where(
            Product.seller_id.in_(ids),
            Comment.is_hidden.is_(False),
            Comment.is_deleted.is_(False),
        )
        .group_by(Product.seller_id)
    ).all()

    result: dict[int, dict] = {}
    for seller_id in ids:
        result[seller_id] = {"rating": None, "comment_count": 0, "sold_count": sold.get(seller_id, 0)}
    for seller_id, avg_rating, count in rating_rows:
        result.setdefault(seller_id, {})
        result[seller_id]["rating"] = round(float(avg_rating or 0), 1)
        result[seller_id]["comment_count"] = int(count or 0)
    return result


def seller_stats(seller_id: int) -> dict:
    data = seller_stats_map([seller_id]).get(seller_id, {"rating": None, "sold_count": 0, "comment_count": 0})
    base = Product.query.filter(Product.seller_id == seller_id, Product.is_deleted.is_(False))
    data.update(
        {
            "product_count": base.count(),
            "on_sale_count": base.filter(
                Product.status == ProductStatus.APPROVED, Product.is_available.is_(True), Product.quantity > 0
            ).count(),
            "follower_count": 0,
        }
    )
    return data


def comment_summary(product_id: int) -> dict:
    from backend.services.serializers import rating_summary

    rows = db.session.execute(
        select(Comment.rating, func.count(Comment.id))
        .where(
            Comment.product_id == product_id,
            Comment.is_hidden.is_(False),
            Comment.is_deleted.is_(False),
        )
        .group_by(Comment.rating)
    ).all()
    total = sum(int(count) for _, count in rows)
    return rating_summary([(int(r), int(c)) for r, c in rows], total)


def related_products(product: Product, limit: int = 8) -> list[Product]:
    query = visible_query().filter(Product.id != product.id)
    if product.tag_id:
        same_tag = query.filter(Product.tag_id == product.tag_id).order_by(Product.sales.desc()).limit(limit).all()
    else:
        same_tag = []
    if len(same_tag) >= limit:
        return same_tag
    exclude_ids = [product.id] + [item.id for item in same_tag]
    extra = (
        visible_query()
        .filter(Product.id.notin_(exclude_ids))
        .order_by((Product.sales * 5 + Product.views).desc())
        .limit(limit - len(same_tag))
        .all()
    )
    return same_tag + extra


def track_view(product: Product, user=None) -> None:
    """浏览量自增；登录用户同时更新浏览记录（同商品去重，PRD FR-PROD-08）。"""
    from backend.models import BrowseHistory
    from backend.utils.common import utcnow

    product.views = (product.views or 0) + 1
    if user is not None:
        history = BrowseHistory.query.filter_by(user_id=user.id, product_id=product.id).first()
        if history:
            history.viewed_at = utcnow()
            history.view_count = (history.view_count or 0) + 1
        else:
            db.session.add(BrowseHistory(user_id=user.id, product_id=product.id))
            _trim_history(user.id, keep=100)


def _trim_history(user_id: int, keep: int) -> None:
    """只保留最近 N 条浏览记录，避免单用户数据无限膨胀。"""
    from backend.models import BrowseHistory

    stale_ids = [
        row.id
        for row in BrowseHistory.query.filter_by(user_id=user_id)
        .order_by(BrowseHistory.viewed_at.desc())
        .offset(keep)
        .limit(200)
        .all()
    ]
    if stale_ids:
        BrowseHistory.query.filter(BrowseHistory.id.in_(stale_ids)).delete(synchronize_session=False)


def paginate_products(query, default_per_page: int = 20) -> dict:
    """商品列表统一分页：一次批量取卖家评分，避免 N+1。"""
    from backend.services.serializers import product_card
    from backend.utils.response import page_args, page_result

    page, per_page = page_args(default_per_page)
    total = query.order_by(None).count()
    rows = query.limit(per_page).offset((page - 1) * per_page).all()
    stats = seller_stats_map([p.seller_id for p in rows])
    items = [product_card(p, stats.get(p.seller_id)) for p in rows]
    return page_result(items, total, page, per_page)


def home_payload() -> dict:
    from backend.models import Banner

    banners = (
        Banner.query.filter(Banner.is_active.is_(True)).order_by(Banner.sort_order.asc(), Banner.id.asc()).limit(6).all()
    )
    tags = (
        Tag.query.filter(Tag.is_active.is_(True), Tag.is_deleted.is_(False))
        .order_by(Tag.sort_order.asc(), Tag.id.asc())
        .all()
    )
    counts = dict(
        db.session.execute(
            select(Product.tag_id, func.count(Product.id))
            .where(
                Product.status == ProductStatus.APPROVED,
                Product.is_available.is_(True),
                Product.quantity > 0,
                Product.is_deleted.is_(False),
            )
            .group_by(Product.tag_id)
        ).all()
    )

    recommended = (
        visible_query().order_by(Product.is_featured.desc(), (Product.sales * 5 + Product.views).desc()).limit(10).all()
    )
    hot = visible_query().order_by((Product.sales * 8 + Product.views).desc(), Product.created_at.desc()).limit(8).all()
    latest = visible_query().order_by(Product.created_at.desc()).limit(10).all()

    seller_ids = [p.seller_id for p in recommended + hot + latest]
    stats = seller_stats_map(seller_ids)

    from backend.services.serializers import banner_view, product_card, tag_view

    return {
        "banners": [banner_view(b) for b in banners],
        "tags": [tag_view(t, int(counts.get(t.id, 0))) for t in tags],
        "blocks": {
            "recommended": [product_card(p, stats.get(p.seller_id)) for p in recommended],
            "hot": [product_card(p, stats.get(p.seller_id)) for p in hot],
            "latest": [product_card(p, stats.get(p.seller_id)) for p in latest],
        },
        "hot_keywords": [t.name for t in tags[:6]],
    }
