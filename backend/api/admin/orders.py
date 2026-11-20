"""后台订单管理：全站检索、详情、异常处理（取消 / 退款）。"""
from __future__ import annotations

from flask import Blueprint, request
from sqlalchemy import or_

from backend.api.admin import bp
from backend.constants import AuditAction, OperatorType, OrderStatus
from backend.errors import not_found
from backend.extensions import db
from backend.models import Order, User
from backend.services import orders as order_service
from backend.services.serializers import order_admin_view
from backend.utils.audit import record
from backend.utils.response import ok, page_args, page_result
from backend.utils.security import admin_required, current_admin
from backend.utils.validators import Payload


@bp.get("/orders")
@admin_required
def list_orders():
    query = Order.query
    status = (request.args.get("status") or "").strip()
    if status in OrderStatus.ALL:
        query = query.filter(Order.status == status)
    keyword = (request.args.get("keyword") or "").strip()
    if keyword:
        like = f"%{keyword}%"
        query = query.join(User, User.id == Order.user_id).filter(
            or_(Order.order_no.ilike(like), User.nickname.ilike(like), Order.receiver_phone.ilike(like))
        )
    query = query.order_by(Order.created_at.desc())

    page, per_page = page_args(20)
    total = query.order_by(None).count()
    rows = query.limit(per_page).offset((page - 1) * per_page).all()
    return ok(page_result([order_admin_view(o) for o in rows], total, page, per_page))


@bp.get("/orders/<int:order_id>")
@admin_required
def order_detail(order_id: int):
    order = Order.query.filter(Order.id == order_id).first()
    if order is None:
        raise not_found("订单不存在")
    return ok(order_admin_view(order))


@bp.post("/orders/<int:order_id>/cancel")
@admin_required
def cancel_order(order_id: int):
    order = Order.query.filter(Order.id == order_id).first()
    if order is None:
        raise not_found("订单不存在")
    payload = Payload(request.get_json(silent=True))
    reason = payload.text("reason", min_len=2, max_len=100, label="取消原因")
    payload.done()
    order_service.cancel_order(order, OperatorType.ADMIN, current_admin(), f"管理员取消：{reason}")
    record(AuditAction.ORDER_REFUND, "order", order.id, reason)
    db.session.commit()
    return ok(order_admin_view(order), "订单已取消并退款")


@bp.post("/orders/<int:order_id>/refund")
@admin_required
def handle_refund(order_id: int):
    order = Order.query.filter(Order.id == order_id).first()
    if order is None:
        raise not_found("订单不存在")
    payload = Payload(request.get_json(silent=True))
    approve = payload.boolean("approve", default=True)
    note = payload.text("note", required=False, max_len=200, label="处理说明")
    payload.done()
    order_service.handle_refund(order, current_admin(), approve, note, OperatorType.ADMIN)
    record(AuditAction.ORDER_REFUND, "order", order.id, note or ("同意退款" if approve else "驳回退款"))
    return ok(order_admin_view(order), "已同意退款" if approve else "已驳回退款")
