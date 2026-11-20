"""后台商品管理：审核、强制下架、批量操作、推荐位。"""
from __future__ import annotations

from flask import Blueprint, request
from sqlalchemy import or_

from backend.api.admin import bp
from backend.constants import AuditAction, MessageType, ProductStatus
from backend.errors import bad_request, not_found
from backend.extensions import db
from backend.models import Product, Tag, User
from backend.services.serializers import product_seller_view
from backend.utils.audit import record
from backend.utils.common import utcnow
from backend.utils.notify import notify
from backend.utils.response import ok, page_args, page_result
from backend.utils.security import admin_required, current_admin
from backend.utils.validators import Payload


@bp.get("/products")
@admin_required
def list_products():
    query = Product.query.filter(Product.is_deleted.is_(False))
    status = (request.args.get("status") or "").strip()
    if status in ProductStatus.ALL:
        query = query.filter(Product.status == status)
    keyword = (request.args.get("keyword") or "").strip()
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(or_(Product.name.ilike(like), Product.description.ilike(like)))
    tag_id = request.args.get("tag_id", type=int)
    if tag_id:
        query = query.filter(Product.tag_id == tag_id)
    seller_id = request.args.get("seller_id", type=int)
    if seller_id:
        query = query.filter(Product.seller_id == seller_id)
    query = query.order_by(Product.created_at.desc())

    page, per_page = page_args(20)
    total = query.order_by(None).count()
    rows = query.limit(per_page).offset((page - 1) * per_page).all()
    items = []
    for product in rows:
        item = product_seller_view(product)
        item["seller"] = {
            "id": product.seller_id,
            "nickname": product.seller.nickname if product.seller else "",
            "avatar_url": product.seller.avatar_url if product.seller else "",
        }
        item["stock_state"] = product.stock_state
        items.append(item)
    return ok(page_result(items, total, page, per_page))


@bp.get("/products/<int:product_id>")
@admin_required
def product_detail(product_id: int):
    product = Product.query.filter(Product.id == product_id).first()
    if product is None:
        raise not_found("商品不存在")
    item = product_seller_view(product)
    item["description"] = product.description or ""
    item["seller"] = {
        "id": product.seller_id,
        "nickname": product.seller.nickname if product.seller else "",
    }
    return ok(item)


def _apply_status(product: Product, status: str, reason: str) -> None:
    from flask import current_app

    if status not in (ProductStatus.APPROVED, ProductStatus.OFF, ProductStatus.PENDING):
        raise bad_request("商品状态不合法")
    if status == ProductStatus.APPROVED and product.quantity <= 0:
        raise bad_request("库存为 0 的商品不能通过审核")
    if status == ProductStatus.OFF and not reason:
        raise bad_request("请填写下架原因", {"reason": "下架原因不能为空"})

    previous = product.status
    product.status = status
    product.audited_at = utcnow()
    product.audited_by = current_admin().id
    if status == ProductStatus.APPROVED:
        product.is_available = True
        product.reject_reason = ""
        product.sold_out_at = None
    elif status == ProductStatus.OFF:
        product.is_available = False
        product.reject_reason = reason[:200]

    if status == ProductStatus.APPROVED and previous != ProductStatus.APPROVED:
        notify(
            product.seller_id,
            MessageType.AUDIT,
            "商品审核通过",
            f"《{product.name}》已上架，买家可以看到它了。",
            f"/products/{product.id}",
        )
    elif status == ProductStatus.OFF and previous != ProductStatus.OFF:
        notify(
            product.seller_id,
            MessageType.AUDIT,
            "商品被下架",
            f"《{product.name}》已下架：{reason}",
            "/seller/products",
        )


@bp.put("/products/<int:product_id>/status")
@admin_required
def update_status(product_id: int):
    product = Product.query.filter(Product.id == product_id, Product.is_deleted.is_(False)).first()
    if product is None:
        raise not_found("商品不存在")
    payload = Payload(request.get_json(silent=True))
    status = payload.choice("status", (ProductStatus.APPROVED, ProductStatus.OFF, ProductStatus.PENDING), label="状态")
    reason = payload.text("reason", required=False, max_len=200, label="原因")
    payload.done()

    _apply_status(product, status, reason)
    action = AuditAction.PRODUCT_APPROVE if status == ProductStatus.APPROVED else AuditAction.PRODUCT_OFF
    record(action, "product", product.id, reason or status)
    db.session.commit()
    return ok(product_seller_view(product), "操作成功")


@bp.post("/products/batch-status")
@admin_required
def batch_status():
    payload = Payload(request.get_json(silent=True))
    ids = payload.int_list("ids", max_items=100, label="商品")
    status = payload.choice("status", (ProductStatus.APPROVED, ProductStatus.OFF), label="状态")
    reason = payload.text("reason", required=False, max_len=200, label="原因")
    payload.done()
    if not ids:
        raise bad_request("请选择要操作的商品")
    if status == ProductStatus.OFF and not reason:
        raise bad_request("批量下架必须填写原因", {"reason": "下架原因不能为空"})

    results = []
    products = Product.query.filter(Product.id.in_(ids), Product.is_deleted.is_(False)).all()
    found_ids = {p.id for p in products}
    for product in products:
        try:
            _apply_status(product, status, reason)
            results.append({"id": product.id, "name": product.name, "success": True, "message": "成功"})
        except Exception as exc:  # noqa: BLE001 - 批量操作需要逐条结果
            results.append({"id": product.id, "name": product.name, "success": False, "message": str(getattr(exc, "message", exc))})
    for missing in set(ids) - found_ids:
        results.append({"id": missing, "name": "", "success": False, "message": "商品不存在或已删除"})

    action = AuditAction.PRODUCT_APPROVE if status == ProductStatus.APPROVED else AuditAction.PRODUCT_OFF
    record(action, "product", ",".join(str(i) for i in ids), f"批量{status}：{reason}")
    db.session.commit()
    return ok({"results": results, "success_count": sum(1 for r in results if r["success"])}, "批量操作完成")


@bp.put("/products/<int:product_id>/feature")
@admin_required
def feature_product(product_id: int):
    product = Product.query.filter(Product.id == product_id, Product.is_deleted.is_(False)).first()
    if product is None:
        raise not_found("商品不存在")
    payload = Payload(request.get_json(silent=True))
    featured = payload.boolean("featured", default=True)
    payload.done()
    product.is_featured = featured
    record(AuditAction.PRODUCT_FEATURE, "product", product.id, "推荐" if featured else "取消推荐")
    db.session.commit()
    return ok(product_seller_view(product), "已设为推荐" if featured else "已取消推荐")


@bp.get("/products/tags")
@admin_required
def product_tags():
    from backend.services.serializers import tag_view

    tags = Tag.query.filter(Tag.is_deleted.is_(False)).order_by(Tag.sort_order.asc()).all()
    return ok({"items": [tag_view(t) for t in tags], "total": len(tags)})
