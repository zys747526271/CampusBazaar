"""后台用户管理：检索、详情、封禁/解封、重置密码、注销。"""
from __future__ import annotations

import secrets
import string

from flask import Blueprint, request
from sqlalchemy import func, or_, select

from backend.api.admin import bp
from backend.constants import AuditAction, MessageType
from backend.errors import bad_request, not_found
from backend.extensions import db
from backend.models import Order, Product, User
from backend.services.serializers import order_view, user_admin_view
from backend.utils.audit import record
from backend.utils.common import mask_phone, utcnow
from backend.utils.notify import notify
from backend.utils.response import ok, page_args, page_result
from backend.utils.security import admin_required, hash_password
from backend.utils.validators import Payload


def _spent_map(user_ids: list[int]) -> dict[int, dict]:
    if not user_ids:
        return {}
    rows = db.session.execute(
        select(Order.user_id, func.count(Order.id), func.coalesce(func.sum(Order.total_amount), 0))
        .where(Order.user_id.in_(user_ids))
        .group_by(Order.user_id)
    ).all()
    return {row[0]: {"order_count": int(row[1]), "spent": float(row[2] or 0)} for row in rows}


@bp.get("/users")
@admin_required
def list_users():
    query = User.query.filter(User.is_deleted.is_(False))
    keyword = (request.args.get("keyword") or "").strip()
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(or_(User.nickname.ilike(like), User.phone.ilike(like)))
    status = (request.args.get("status") or "").strip()
    if status == "banned":
        query = query.filter(User.is_banned.is_(True))
    elif status == "seller":
        query = query.filter(User.is_seller.is_(True))
    elif status == "buyer":
        query = query.filter(User.is_seller.is_(False))
    query = query.order_by(User.created_at.desc())

    page, per_page = page_args(20)
    total = query.order_by(None).count()
    rows = query.limit(per_page).offset((page - 1) * per_page).all()
    spent = _spent_map([u.id for u in rows])
    items = []
    for user in rows:
        item = user_admin_view(user, spent.get(user.id))
        item["phone"] = mask_phone(user.phone)
        items.append(item)
    return ok(page_result(items, total, page, per_page))


@bp.get("/users/<int:user_id>")
@admin_required
def user_detail(user_id: int):
    user = User.query.filter(User.id == user_id).first()
    if user is None:
        raise not_found("用户不存在")
    spent = _spent_map([user.id]).get(user.id, {})
    data = user_admin_view(user, spent)
    data["phone"] = mask_phone(user.phone)
    data["products"] = {
        "total": Product.query.filter(Product.seller_id == user.id, Product.is_deleted.is_(False)).count(),
        "on_sale": Product.query.filter(
            Product.seller_id == user.id,
            Product.is_deleted.is_(False),
            Product.is_available.is_(True),
        ).count(),
    }
    orders = Order.query.filter(Order.user_id == user.id).order_by(Order.created_at.desc()).limit(5).all()
    data["recent_orders"] = [order_view(o, "admin") for o in orders]
    return ok(data)


@bp.put("/users/<int:user_id>/ban")
@admin_required
def ban_user(user_id: int):
    user = User.query.filter(User.id == user_id, User.is_deleted.is_(False)).first()
    if user is None:
        raise not_found("用户不存在")
    payload = Payload(request.get_json(silent=True))
    banned = payload.boolean("banned", default=True)
    reason = payload.text("reason", required=False, max_len=100, label="原因")
    payload.done()

    if banned and not reason:
        raise bad_request("请填写封禁原因", {"reason": "封禁原因不能为空"})

    if banned:
        user.ban(reason)
        # 封禁后其商品自动下架（PRD 3.5）
        Product.query.filter(Product.seller_id == user.id, Product.is_deleted.is_(False)).update(
            {"is_available": False}, synchronize_session=False
        )
        record(AuditAction.USER_BAN, "user", user.id, reason)
    else:
        user.unban()
        notify(user.id, MessageType.SYSTEM, "账号已解封", "你的账号已恢复正常，欢迎回来。", "/")
        record(AuditAction.USER_UNBAN, "user", user.id, "")
    user.banned_at = utcnow() if banned else None
    db.session.commit()
    return ok(user_admin_view(user), "已封禁" if banned else "已解封")


@bp.put("/users/<int:user_id>/reset-password")
@admin_required
def reset_password(user_id: int):
    user = User.query.filter(User.id == user_id, User.is_deleted.is_(False)).first()
    if user is None:
        raise not_found("用户不存在")
    payload = Payload(request.get_json(silent=True))
    new_password = payload.take("new_password")
    payload.done()
    if new_password:
        parsed = Payload({"new_password": new_password})
        password = parsed.password("new_password", "新密码")
        parsed.done()
    else:
        alphabet = string.ascii_letters + string.digits
        password = "".join(secrets.choice(alphabet) for _ in range(10))

    user.password_hash = hash_password(password)
    record(AuditAction.USER_RESET_PASSWORD, "user", user.id, "")
    notify(user.id, MessageType.SYSTEM, "密码已被管理员重置", "如非本人操作请立即联系管理员。", "/profile")
    db.session.commit()
    return ok({"new_password": password}, "密码已重置")


@bp.delete("/users/<int:user_id>")
@admin_required
def delete_user(user_id: int):
    user = User.query.filter(User.id == user_id, User.is_deleted.is_(False)).first()
    if user is None:
        raise not_found("用户不存在")
    user.soft_delete()
    user.phone = f"deleted_{user.id}"
    Product.query.filter(Product.seller_id == user.id).update({"is_available": False}, synchronize_session=False)
    record("注销用户", "user", user.id, "")
    db.session.commit()
    return ok(None, "账号已注销")


@bp.get("/users/<int:user_id>/orders")
@admin_required
def user_orders(user_id: int):
    query = Order.query.filter(Order.user_id == user_id).order_by(Order.created_at.desc())
    page, per_page = page_args(10)
    total = query.order_by(None).count()
    rows = query.limit(per_page).offset((page - 1) * per_page).all()
    return ok(page_result([order_view(o, "admin") for o in rows], total, page, per_page))


@bp.get("/users/<int:user_id>/products")
@admin_required
def user_products(user_id: int):
    from backend.services.serializers import product_seller_view

    query = Product.query.filter(Product.seller_id == user_id, Product.is_deleted.is_(False)).order_by(
        Product.created_at.desc()
    )
    page, per_page = page_args(10)
    total = query.order_by(None).count()
    rows = query.limit(per_page).offset((page - 1) * per_page).all()
    return ok(page_result([product_seller_view(p) for p in rows], total, page, per_page))
