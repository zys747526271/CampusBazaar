"""卖家中心：开通卖家、商品管理、订单履约、自定义分类、评价回复。"""
from __future__ import annotations

from decimal import Decimal

from flask import Blueprint, request
from sqlalchemy import func, select

from backend.constants import DeliveryType, Limits, MessageType, OperatorType, OrderStatus, ProductCondition, ProductStatus
from backend.errors import bad_request, conflict, forbidden, not_found
from backend.extensions import db
from backend.models import Comment, Order, OrderItem, Product, SellerCategory, Tag
from backend.services import orders as order_service
from backend.services import stats as stats_service
from backend.services.serializers import (
    comment_view,
    order_view,
    product_seller_view,
    seller_category_view,
)
from backend.utils.common import iso, utcnow
from backend.utils.notify import notify
from backend.utils.response import ok, page_args, paginate
from backend.utils.security import current_user, login_required, seller_required
from backend.utils.validators import Payload

bp = Blueprint("seller", __name__, url_prefix="/api/seller")


# ------------------------------------------------------------------ 身份与概览
@bp.post("/become")
@login_required
def become_seller():
    user = current_user()
    if user.is_seller:
        return ok({"is_seller": True}, "你已经是卖家了")
    user.activate_seller()
    notify(user.id, MessageType.SYSTEM, "卖家身份已开通", "现在可以发布商品了，祝早日出手。", "/seller/products/new")
    db.session.commit()
    return ok({"is_seller": True, "seller_since": iso(user.seller_since)}, "卖家身份开通成功")


@bp.get("/overview")
@seller_required
def overview():
    return ok(stats_service.seller_overview(current_user().id))


# ------------------------------------------------------------------ 商品
@bp.get("/products")
@seller_required
def list_products():
    user = current_user()
    query = Product.query.filter(Product.seller_id == user.id, Product.is_deleted.is_(False))
    status = (request.args.get("status") or "").strip()
    if status in ProductStatus.ALL:
        query = query.filter(Product.status == status)
    keyword = (request.args.get("keyword") or "").strip()
    if keyword:
        query = query.filter(Product.name.ilike(f"%{keyword}%"))
    query = query.order_by(Product.created_at.desc())

    page, per_page = page_args(12)
    total = query.order_by(None).count()
    rows = query.limit(per_page).offset((page - 1) * per_page).all()
    counts = _comment_count_map([p.id for p in rows])
    items = [product_seller_view(p, counts.get(p.id, 0)) for p in rows]
    return ok(
        {
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": -(-total // per_page),
        }
    )


def _comment_count_map(product_ids: list[int]) -> dict[int, int]:
    if not product_ids:
        return {}
    rows = db.session.execute(
        select(Comment.product_id, func.count(Comment.id))
        .where(Comment.product_id.in_(product_ids), Comment.is_deleted.is_(False), Comment.is_hidden.is_(False))
        .group_by(Comment.product_id)
    ).all()
    return {row[0]: int(row[1]) for row in rows}


def _owned_product(product_id: int, user) -> Product:
    product = Product.query.filter(Product.id == product_id, Product.is_deleted.is_(False)).first()
    if product is None:
        raise not_found("商品不存在")
    if product.seller_id != user.id:
        raise forbidden("只能操作自己发布的商品")
    return product


def _apply_product_fields(product: Product, payload: Payload, user, creating: bool) -> None:
    product.name = payload.text("name", min_len=2, max_len=80, label="商品名称")
    product.description = payload.text("description", required=False, max_len=2000, label="商品描述")
    product.price = payload.decimal("price", min_value=Decimal("0.01"), max_value=Decimal("999999"), label="价格")
    original_price = payload.decimal("original_price", required=False, min_value=Decimal("0"), max_value=Decimal("999999"), label="原价", default=Decimal("0"))
    product.original_price = original_price if original_price > 0 else None
    product.quantity = payload.integer("quantity", min_value=1, max_value=9999, label="库存")
    product.product_condition = payload.choice(
        "condition", ProductCondition.ALL, required=False, default=product.product_condition, label="成色"
    )
    product.location = payload.text("location", required=False, max_len=60, label="交易地点")

    # ---- 履约方式（v2.2）：自提点可留空，快递需明确包邮与运费 ----
    supports_pickup = payload.boolean("supports_pickup", default=True)
    supports_express = payload.boolean("supports_express", default=True)
    if not supports_pickup and not supports_express:
        raise bad_request("至少选择一种履约方式", {"supports_pickup": "自提与快递至少选一个"})
    pickup_location = payload.text("pickup_location", required=False, max_len=120, label="自提点")
    free_shipping = payload.boolean("free_shipping", default=True)
    shipping_fee = payload.decimal(
        "shipping_fee", required=False, min_value=Decimal("0"), max_value=Decimal("9999"), label="运费", default=Decimal("0")
    )
    if supports_express and not free_shipping and shipping_fee <= 0:
        raise bad_request("不包邮时请填写运费", {"shipping_fee": "运费必须大于 0"})
    product.supports_pickup = supports_pickup
    product.pickup_location = pickup_location.strip()[:120]
    product.supports_express = supports_express
    product.free_shipping = free_shipping if supports_express else True
    product.shipping_fee = Decimal("0.00") if (free_shipping or not supports_express) else shipping_fee

    images = payload.str_list("images", max_items=Limits.PRODUCT_MAX_IMAGES, max_len=255, label="图片")
    if creating and not images:
        raise bad_request("请至少上传一张商品图片", {"images": "至少 1 张图片"})
    if images:
        product.images = images

    tag_id = payload.integer("tag_id", required=False, min_value=1, default=0, label="平台分类")
    if tag_id:
        tag = Tag.query.filter(Tag.id == tag_id, Tag.is_deleted.is_(False), Tag.is_active.is_(True)).first()
        if tag is None:
            raise bad_request("平台分类不存在或已停用", {"tag_id": "分类不可用"})
        product.tag_id = tag.id
    elif creating:
        raise bad_request("请选择商品分类", {"tag_id": "分类不能为空"})

    category_id = payload.integer("seller_category_id", required=False, min_value=1, default=0, label="自定义分类")
    if category_id:
        category = SellerCategory.query.filter_by(id=category_id).first()
        if category is None:
            raise bad_request("自定义分类不存在", {"seller_category_id": "分类不存在"})
        if category.seller_id != user.id:
            raise forbidden("不能使用其他卖家的分类")
        product.seller_category_id = category.id
    else:
        product.seller_category_id = None


@bp.post("/products")
@seller_required
def create_product():
    from flask import current_app

    user = current_user()
    payload = Payload(request.get_json(silent=True))
    product = Product(seller_id=user.id, status=ProductStatus.PENDING, is_available=True)
    _apply_product_fields(product, payload, user, creating=True)
    payload.done()

    if current_app.config.get("AUTO_APPROVE_PRODUCT"):
        product.status = ProductStatus.APPROVED
        product.audited_at = utcnow()
    db.session.add(product)
    db.session.commit()
    if product.status == ProductStatus.PENDING:
        notify(user.id, MessageType.AUDIT, "商品已提交审核", f"《{product.name}》正在审核中，通过后会展示给买家。", "/seller/products")
    return ok(product_seller_view(product), "发布成功" if product.status == ProductStatus.APPROVED else "已提交审核")


@bp.get("/products/<int:product_id>")
@seller_required
def product_detail(product_id: int):
    user = current_user()
    product = _owned_product(product_id, user)
    data = product_seller_view(product, _comment_count_map([product.id]).get(product.id, 0))
    data["stats"] = stats_service.product_sales(product.id)
    return ok(data)


@bp.put("/products/<int:product_id>")
@seller_required
def update_product(product_id: int):
    user = current_user()
    product = _owned_product(product_id, user)
    payload = Payload(request.get_json(silent=True))
    _apply_product_fields(product, payload, user, creating=False)
    payload.done()
    db.session.commit()
    return ok(product_seller_view(product), "商品已更新")


@bp.post("/products/<int:product_id>/toggle")
@seller_required
def toggle_product(product_id: int):
    from flask import current_app

    user = current_user()
    product = _owned_product(product_id, user)
    if product.status == ProductStatus.APPROVED and product.is_available:
        product.is_available = False
        message = "商品已下架"
    else:
        if product.quantity <= 0:
            raise bad_request("库存为 0，请先补充库存后再上架")
        product.is_available = True
        if current_app.config.get("AUTO_APPROVE_PRODUCT"):
            product.status = ProductStatus.APPROVED
            message = "商品已重新上架"
        else:
            product.status = ProductStatus.PENDING
            message = "已提交重新审核"
        product.sold_out_at = None
    db.session.commit()
    return ok(product_seller_view(product), message)


@bp.delete("/products/<int:product_id>")
@seller_required
def delete_product(product_id: int):
    user = current_user()
    product = _owned_product(product_id, user)
    active_orders = (
        db.session.query(func.count(OrderItem.id))
        .join(Order, Order.id == OrderItem.order_id)
        .filter(OrderItem.product_id == product.id, Order.status.in_(OrderStatus.ACTIVE))
        .scalar()
        or 0
    )
    if active_orders:
        raise conflict("该商品有进行中的订单，处理完成后再删除")
    product.soft_delete()
    product.is_available = False
    db.session.commit()
    return ok(None, "商品已删除")


# ------------------------------------------------------------------ 订单
@bp.get("/orders")
@seller_required
def seller_orders():
    user = current_user()
    query = Order.query.filter(Order.seller_id == user.id)
    status = (request.args.get("status") or "").strip()
    if status in OrderStatus.ALL:
        query = query.filter(Order.status == status)
    keyword = (request.args.get("keyword") or "").strip()
    if keyword:
        query = query.filter(Order.order_no.ilike(f"%{keyword}%"))
    query = query.order_by(Order.created_at.desc())
    return ok(paginate(query, lambda o: order_view(o, "seller")))


def _seller_order(order_id: int, user) -> Order:
    order = Order.query.filter(Order.id == order_id).first()
    if order is None:
        raise not_found("订单不存在")
    if order.seller_id != user.id:
        raise forbidden("只能操作自己店铺的订单")
    return order


@bp.post("/orders/<int:order_id>/ship")
@seller_required
def ship(order_id: int):
    user = current_user()
    order = _seller_order(order_id, user)
    payload = Payload(request.get_json(silent=True))
    company = payload.text("ship_company", required=False, max_len=40, label="快递公司")
    tracking_no = payload.text("tracking_no", required=False, max_len=60, label="快递单号")
    note = payload.text("note", required=False, max_len=100, label="备注")
    payload.done()
    if order.delivery_type == DeliveryType.EXPRESS and not company:
        raise bad_request("请填写快递公司", {"ship_company": "快递公司不能为空"})
    order_service.ship_order(order, user, ship_company=company, tracking_no=tracking_no, note=note)
    return ok(order_view(order, "seller"), "发货成功")


@bp.post("/orders/<int:order_id>/pickup-location")
@seller_required
def set_pickup_location(order_id: int):
    user = current_user()
    order = Order.query.filter(Order.id == order_id).first()
    if order is None:
        raise not_found("订单不存在")
    if order.seller_id != user.id:
        raise forbidden("只能操作自己的订单")
    payload = Payload(request.get_json(silent=True))
    location = payload.text("pickup_location", min_len=2, max_len=120, label="自提点")
    payload.done()
    order_service.set_pickup_location(order, user, location)
    return ok(order_view(order, "seller"), "自提点已更新并通知买家")


@bp.post("/orders/<int:order_id>/confirm-paid")
@seller_required
def confirm_paid(order_id: int):
    user = current_user()
    order = _seller_order(order_id, user)
    order_service.confirm_offline_paid(order, user)
    return ok(order_view(order, "seller"), "已确认收款")


@bp.post("/orders/<int:order_id>/close")
@seller_required
def close_order(order_id: int):
    user = current_user()
    order = _seller_order(order_id, user)
    payload = Payload(request.get_json(silent=True))
    reason = payload.text("reason", required=False, max_len=100, label="关闭原因", default="卖家关闭订单")
    payload.done()
    order_service.cancel_order(order, OperatorType.SELLER, user, reason)
    db.session.commit()
    return ok(order_view(order, "seller"), "订单已关闭")


@bp.post("/orders/<int:order_id>/refund")
@seller_required
def handle_refund(order_id: int):
    user = current_user()
    order = _seller_order(order_id, user)
    payload = Payload(request.get_json(silent=True))
    approve = payload.boolean("approve", default=False)
    note = payload.text("note", required=False, max_len=200, label="处理说明")
    payload.done()
    order_service.handle_refund(order, user, approve, note, OperatorType.SELLER)
    return ok(order_view(order, "seller"), "已同意退款" if approve else "已驳回退款")


# ------------------------------------------------------------------ 自定义分类
@bp.get("/categories")
@seller_required
def list_categories():
    user = current_user()
    rows = SellerCategory.query.filter_by(seller_id=user.id).order_by(SellerCategory.sort_order.asc(), SellerCategory.id.asc()).all()
    counts = dict(
        db.session.execute(
            select(Product.seller_category_id, func.count(Product.id))
            .where(Product.seller_id == user.id, Product.is_deleted.is_(False))
            .group_by(Product.seller_category_id)
        ).all()
    )
    return ok({"items": [seller_category_view(c, counts.get(c.id, 0)) for c in rows], "total": len(rows)})


@bp.post("/categories")
@seller_required
def create_category():
    user = current_user()
    payload = Payload(request.get_json(silent=True))
    name = payload.text("name", min_len=1, max_len=30, label="分类名称")
    sort_order = payload.integer("sort_order", required=False, default=0, label="排序")
    payload.done()
    if SellerCategory.query.filter_by(seller_id=user.id, name=name).first():
        raise bad_request("分类名称已存在", {"name": "名称重复"})
    category = SellerCategory(seller_id=user.id, name=name, sort_order=sort_order)
    db.session.add(category)
    db.session.commit()
    return ok(seller_category_view(category, 0), "分类已创建")


@bp.put("/categories/<int:category_id>")
@seller_required
def update_category(category_id: int):
    user = current_user()
    category = SellerCategory.query.filter_by(id=category_id).first()
    if category is None:
        raise not_found("分类不存在")
    if category.seller_id != user.id:
        raise forbidden("只能操作自己的分类")
    payload = Payload(request.get_json(silent=True))
    name = payload.text("name", required=False, max_len=30, label="分类名称", default=category.name)
    sort_order = payload.integer("sort_order", required=False, default=category.sort_order, label="排序")
    payload.done()
    duplicate = SellerCategory.query.filter(
        SellerCategory.seller_id == user.id, SellerCategory.name == name, SellerCategory.id != category.id
    ).first()
    if duplicate:
        raise bad_request("分类名称已存在", {"name": "名称重复"})
    category.name = name
    category.sort_order = sort_order
    db.session.commit()
    return ok(seller_category_view(category), "分类已更新")


@bp.delete("/categories/<int:category_id>")
@seller_required
def delete_category(category_id: int):
    user = current_user()
    category = SellerCategory.query.filter_by(id=category_id).first()
    if category is None:
        raise not_found("分类不存在")
    if category.seller_id != user.id:
        raise forbidden("只能操作自己的分类")
    used = Product.query.filter(
        Product.seller_category_id == category.id, Product.is_deleted.is_(False)
    ).count()
    if used:
        raise bad_request(f"该分类下还有 {used} 件商品，请先移动或删除商品")
    db.session.delete(category)
    db.session.commit()
    return ok(None, "分类已删除")


# ------------------------------------------------------------------ 评价
@bp.get("/comments")
@seller_required
def seller_comments():
    user = current_user()
    product_ids = [row[0] for row in db.session.execute(
        select(Product.id).where(Product.seller_id == user.id, Product.is_deleted.is_(False))
    ).all()]
    if not product_ids:
        return ok({"items": [], "total": 0, "page": 1, "per_page": 10, "pages": 0})
    query = Comment.query.filter(Comment.product_id.in_(product_ids), Comment.is_deleted.is_(False))
    if request.args.get("unreplied") in ("1", "true"):
        query = query.filter(Comment.seller_reply == "")
    query = query.order_by(Comment.created_at.desc())
    return ok(paginate(query, lambda c: comment_view(c, with_product=True), default_per_page=10))


@bp.post("/comments/<int:comment_id>/reply")
@seller_required
def reply_comment(comment_id: int):
    user = current_user()
    comment = Comment.query.filter(Comment.id == comment_id, Comment.is_deleted.is_(False)).first()
    if comment is None:
        raise not_found("评价不存在")
    if not comment.product or comment.product.seller_id != user.id:
        raise forbidden("只能回复自己商品的评价")
    payload = Payload(request.get_json(silent=True))
    reply = payload.text("reply", min_len=1, max_len=300, label="回复内容")
    payload.done()
    comment.seller_reply = reply
    comment.seller_reply_at = utcnow()
    notify(comment.user_id, MessageType.SYSTEM, "卖家回复了你的评价", reply, f"/products/{comment.product_id}")
    db.session.commit()
    return ok(comment_view(comment, with_product=True), "回复成功")
