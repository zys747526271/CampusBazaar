"""后台商家管理：商家列表、商家商品检索。"""
from __future__ import annotations

from flask import Blueprint, request
from sqlalchemy import func, select

from backend.api.admin import bp
from backend.constants import OrderStatus, ProductStatus
from backend.errors import not_found
from backend.extensions import db
from backend.models import Order, Product, User
from backend.services.serializers import product_seller_view, user_public
from backend.utils.common import mask_phone
from backend.utils.response import ok, page_args, page_result
from backend.utils.security import admin_required


@bp.get("/sellers")
@admin_required
def list_sellers():
    query = User.query.filter(User.is_deleted.is_(False), User.is_seller.is_(True))
    keyword = (request.args.get("keyword") or "").strip()
    if keyword:
        like = f"%{keyword}%"
        query = query.filter((User.nickname.ilike(like)) | (User.phone.ilike(like)))
    query = query.order_by(User.seller_since.desc(), User.id.desc())

    page, per_page = page_args(20)
    total = query.order_by(None).count()
    rows = query.limit(per_page).offset((page - 1) * per_page).all()
    ids = [u.id for u in rows]

    product_counts = dict(
        db.session.execute(
            select(Product.seller_id, func.count(Product.id))
            .where(Product.seller_id.in_(ids), Product.is_deleted.is_(False))
            .group_by(Product.seller_id)
        ).all()
    ) if ids else {}
    on_sale_counts = dict(
        db.session.execute(
            select(Product.seller_id, func.count(Product.id))
            .where(
                Product.seller_id.in_(ids),
                Product.is_deleted.is_(False),
                Product.status == ProductStatus.APPROVED,
                Product.is_available.is_(True),
                Product.quantity > 0,
            )
            .group_by(Product.seller_id)
        ).all()
    ) if ids else {}
    gmv = dict(
        db.session.execute(
            select(Order.seller_id, func.coalesce(func.sum(Order.total_amount), 0))
            .where(Order.seller_id.in_(ids), Order.status == OrderStatus.DONE)
            .group_by(Order.seller_id)
        ).all()
    ) if ids else {}
    order_counts = dict(
        db.session.execute(
            select(Order.seller_id, func.count(Order.id)).where(Order.seller_id.in_(ids)).group_by(Order.seller_id)
        ).all()
    ) if ids else {}

    items = []
    for user in rows:
        item = user_public(user)
        item.update(
            {
                "phone": mask_phone(user.phone),
                "is_banned": user.is_banned,
                "product_count": int(product_counts.get(user.id, 0)),
                "on_sale_count": int(on_sale_counts.get(user.id, 0)),
                "order_count": int(order_counts.get(user.id, 0)),
                "gmv": float(gmv.get(user.id, 0) or 0),
            }
        )
        items.append(item)
    return ok(page_result(items, total, page, per_page))


@bp.get("/sellers/<int:seller_id>/products")
@admin_required
def seller_products(seller_id: int):
    seller = User.query.filter(User.id == seller_id).first()
    if seller is None:
        raise not_found("商家不存在")
    query = Product.query.filter(Product.seller_id == seller_id, Product.is_deleted.is_(False))
    keyword = (request.args.get("keyword") or "").strip()
    if keyword:
        query = query.filter(Product.name.ilike(f"%{keyword}%"))
    status = (request.args.get("status") or "").strip()
    if status in ProductStatus.ALL:
        query = query.filter(Product.status == status)
    query = query.order_by(Product.created_at.desc())

    page, per_page = page_args(20)
    total = query.order_by(None).count()
    rows = query.limit(per_page).offset((page - 1) * per_page).all()
    return ok(page_result([product_seller_view(p) for p in rows], total, page, per_page))
