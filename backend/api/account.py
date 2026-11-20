"""账户：收货地址、余额与流水、站内消息。"""
from __future__ import annotations

from decimal import Decimal

from flask import Blueprint, current_app, request
from sqlalchemy import func

from backend.constants import BalanceLogType, Limits, MessageType
from backend.errors import bad_request, forbidden, not_found
from backend.extensions import db
from backend.models import Address, BalanceLog, Message
from backend.services.orders import _add_balance, get_balance
from backend.services.serializers import address_view, balance_log_view, message_view
from backend.utils.response import created, ok, paginate
from backend.utils.security import current_user, login_required
from backend.utils.validators import Payload

bp = Blueprint("account", __name__, url_prefix="/api")


# ------------------------------------------------------------------ 地址
@bp.get("/addresses")
@login_required
def list_addresses():
    user = current_user()
    rows = (
        Address.query.filter_by(user_id=user.id, is_deleted=False)
        .order_by(Address.is_default.desc(), Address.id.desc())
        .all()
    )
    return ok({"items": [address_view(a) for a in rows], "total": len(rows)})


def _apply_address(address: Address, payload: Payload) -> None:
    address.name = payload.text("name", min_len=1, max_len=30, label="联系人")
    address.phone = payload.phone("phone", "联系电话")
    address.campus_area = payload.text("campus_area", required=False, max_len=60, label="校区/区域")
    address.detail = payload.text("detail", min_len=2, max_len=200, label="详细地址")
    address.is_default = payload.boolean("is_default", default=address.is_default)


def _clear_other_defaults(user_id: int, keep_id: int | None) -> None:
    query = Address.query.filter(Address.user_id == user_id, Address.is_default.is_(True), Address.is_deleted.is_(False))
    if keep_id:
        query = query.filter(Address.id != keep_id)
    for row in query.all():
        row.is_default = False


@bp.post("/addresses")
@login_required
def create_address():
    user = current_user()
    payload = Payload(request.get_json(silent=True))
    address = Address(user_id=user.id, is_default=False)
    _apply_address(address, payload)
    payload.done()
    if not Address.query.filter_by(user_id=user.id, is_deleted=False).first():
        address.is_default = True
    db.session.add(address)
    db.session.flush()
    if address.is_default:
        _clear_other_defaults(user.id, address.id)
    db.session.commit()
    return created(address_view(address), "地址已保存")


@bp.put("/addresses/<int:address_id>")
@login_required
def update_address(address_id: int):
    user = current_user()
    address = Address.query.filter_by(id=address_id, user_id=user.id, is_deleted=False).first()
    if address is None:
        raise not_found("地址不存在")
    payload = Payload(request.get_json(silent=True))
    _apply_address(address, payload)
    payload.done()
    if address.is_default:
        _clear_other_defaults(user.id, address.id)
    db.session.commit()
    return ok(address_view(address), "地址已更新")


@bp.delete("/addresses/<int:address_id>")
@login_required
def delete_address(address_id: int):
    user = current_user()
    address = Address.query.filter_by(id=address_id, user_id=user.id, is_deleted=False).first()
    if address is None:
        raise not_found("地址不存在")
    address.is_deleted = True
    address.is_default = False
    db.session.commit()
    return ok(None, "地址已删除")


@bp.put("/addresses/<int:address_id>/default")
@login_required
def set_default_address(address_id: int):
    user = current_user()
    address = Address.query.filter_by(id=address_id, user_id=user.id, is_deleted=False).first()
    if address is None:
        raise not_found("地址不存在")
    address.is_default = True
    _clear_other_defaults(user.id, address.id)
    db.session.commit()
    return ok(address_view(address), "已设为默认地址")


# ------------------------------------------------------------------ 余额
@bp.get("/balance")
@login_required
def balance_info():
    user = current_user()
    balance = get_balance(user.id)
    db.session.commit()
    logs = (
        BalanceLog.query.filter_by(user_id=user.id).order_by(BalanceLog.created_at.desc()).limit(5).all()
    )
    income = (
        db.session.query(func.coalesce(func.sum(BalanceLog.amount), 0))
        .filter(BalanceLog.user_id == user.id, BalanceLog.amount > 0)
        .scalar()
        or 0
    )
    return ok(
        {
            "amount": float(balance.amount),
            "total_income": float(income),
            "recent_logs": [balance_log_view(log) for log in logs],
            "recharge_enabled": bool(current_app.config.get("ENABLE_DEMO_RECHARGE")),
        }
    )


@bp.get("/balance/logs")
@login_required
def balance_logs():
    user = current_user()
    query = BalanceLog.query.filter_by(user_id=user.id).order_by(BalanceLog.created_at.desc())
    return ok(paginate(query, balance_log_view))


@bp.post("/balance/recharge")
@login_required
def recharge():
    if not current_app.config.get("ENABLE_DEMO_RECHARGE"):
        raise forbidden("当前环境未开放充值")
    user = current_user()
    payload = Payload(request.get_json(silent=True))
    amount = payload.decimal("amount", min_value=Decimal("0.01"), max_value=Limits.RECHARGE_MAX, label="充值金额")
    payload.done()
    get_balance(user.id)
    _add_balance(user.id, amount, BalanceLogType.RECHARGE, "recharge", "", "演示充值")
    db.session.commit()
    balance = get_balance(user.id, create=False)
    return ok({"amount": float(balance.amount)}, "充值成功（演示）")


# ------------------------------------------------------------------ 消息
@bp.get("/messages")
@login_required
def list_messages():
    user = current_user()
    query = Message.query.filter_by(user_id=user.id)
    if request.args.get("unread") in ("1", "true"):
        query = query.filter(Message.is_read.is_(False))
    msg_type = (request.args.get("type") or "").strip()
    if msg_type in MessageType.ALL:
        query = query.filter(Message.type == msg_type)
    query = query.order_by(Message.created_at.desc())
    return ok(paginate(query, message_view))


@bp.get("/messages/unread")
@login_required
def unread_count():
    user = current_user()
    count = Message.query.filter_by(user_id=user.id, is_read=False).count()
    return ok({"unread": count})


@bp.post("/messages/<int:message_id>/read")
@login_required
def read_message(message_id: int):
    user = current_user()
    message = Message.query.filter_by(id=message_id, user_id=user.id).first()
    if message is None:
        raise not_found("消息不存在")
    message.is_read = True
    db.session.commit()
    return ok(message_view(message), "已读")


@bp.post("/messages/read-all")
@login_required
def read_all():
    user = current_user()
    count = Message.query.filter_by(user_id=user.id, is_read=False).update({"is_read": True}, synchronize_session=False)
    db.session.commit()
    return ok({"updated": count}, "全部已读")


@bp.delete("/messages/<int:message_id>")
@login_required
def delete_message(message_id: int):
    user = current_user()
    message = Message.query.filter_by(id=message_id, user_id=user.id).first()
    if message is None:
        raise not_found("消息不存在")
    db.session.delete(message)
    db.session.commit()
    return ok(None, "消息已删除")


@bp.get("/meta/options")
def options():
    """前端下拉选项：履约方式、支付方式、成色、举报原因等统一从这里取。"""
    from backend.constants import DeliveryType, ProductCondition
    from backend.services.serializers import delivery_options, pay_options

    return ok(
        {
            "delivery_types": delivery_options(),
            "pay_methods": pay_options(),
            "conditions": list(ProductCondition.ALL),
            "report_reasons": ["虚假信息", "违禁物品", "价格欺诈", "辱骂骚扰", "联系方式引流", "其他"],
            "max_images": Limits.PRODUCT_MAX_IMAGES,
            "order_pay_timeout_minutes": Limits.ORDER_PAY_TIMEOUT_MINUTES,
            "delivery_type_list": list(DeliveryType.ALL),
        }
    )
