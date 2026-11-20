"""买家订单：结算预览、下单、支付、取消、确认收货、退款。"""
from __future__ import annotations

from decimal import Decimal

from flask import Blueprint, request
from sqlalchemy import func

from backend.constants import DeliveryType, OrderStatus, PayMethod
from backend.errors import bad_request, forbidden, not_found
from backend.extensions import db
from backend.models import Address, Cart, Comment, Order
from backend.services import orders as order_service
from backend.services.serializers import order_view
from backend.utils.idempotency import idempotent
from backend.utils.limiter import by_user
from backend.utils.response import created, ok, paginate
from backend.utils.security import current_user, login_required
from backend.utils.validators import Payload

bp = Blueprint("orders", __name__, url_prefix="/api/orders")


# ------------------------------------------------------------------ 结算数据
def _resolve_items(user, payload: Payload) -> list[dict]:
    source = payload.choice("source", ("cart", "now"), required=False, default="cart", label="下单来源")
    if source == "now":
        items = payload.take("items")
        if not isinstance(items, list) or not items:
            raise bad_request("请选择要购买的商品")
        return [{"product_id": item.get("product_id"), "quantity": item.get("quantity", 1)} for item in items]

    cart_ids = payload.int_list("cart_ids", max_items=100, label="购物车条目")
    query = Cart.query.filter(Cart.user_id == user.id)
    if cart_ids:
        query = query.filter(Cart.id.in_(cart_ids))
    else:
        query = query.filter(Cart.selected.is_(True))
    rows = query.all()
    if not rows:
        raise bad_request("请先勾选要结算的商品")
    return [{"product_id": row.product_id, "quantity": row.quantity, "cart_id": row.id} for row in rows]


def _resolve_receiver(user, payload: Payload) -> tuple[str, str, str]:
    address_id = payload.integer("address_id", required=False, min_value=1, default=0)
    if address_id:
        address = Address.query.filter(Address.id == address_id, Address.user_id == user.id, Address.is_deleted.is_(False)).first()
        if address is None:
            raise not_found("收货地址不存在")
        return address.name, address.phone, f"{address.campus_area} {address.detail}".strip()

    name = payload.text("receiver_name", required=False, max_len=30, label="联系人")
    phone = payload.text("receiver_phone", required=False, max_len=11, label="联系电话")
    address_text = payload.text("address_text", required=False, max_len=200, label="交易地点")
    if not name or not phone:
        raise bad_request("请填写联系人与联系电话", {"receiver_name": "联系人不能为空"})
    if len(phone) != 11 or not phone.isdigit():
        raise bad_request("联系电话格式不正确", {"receiver_phone": "请填写 11 位手机号"})
    return name, phone, address_text


def _quote(user, payload: Payload) -> tuple[list[dict], dict]:
    """复用下单前的价格计算，保证预览与实付一致。"""
    items = _resolve_items(user, payload)
    total = Decimal("0.00")
    groups: dict[int, dict] = {}
    from backend.models import Product

    for item in items:
        product = Product.query.filter(Product.id == item["product_id"], Product.is_deleted.is_(False)).first()
        if product is None:
            raise not_found("商品不存在或已删除")
        if product.seller_id == user.id:
            raise forbidden("不能购买自己发布的商品")
        if not product.is_on_sale:
            raise bad_request(f"《{product.name}》已下架或售罄，请从购物车移除")
        quantity = int(item["quantity"])
        if quantity <= 0 or quantity > product.quantity:
            raise bad_request(f"《{product.name}》库存不足")
        amount = (Decimal(product.price) * quantity).quantize(Decimal("0.01"))
        total += amount
        group = groups.setdefault(
            product.seller_id,
            {
                "seller_id": product.seller_id,
                "seller_name": product.seller.nickname if product.seller else "",
                "items": [],
                "amount": Decimal("0.00"),
            },
        )
        group["items"].append(
            {
                "product_id": product.id,
                "name": product.name,
                "image": product.cover_image,
                "price": float(product.price),
                "quantity": quantity,
                "subtotal": float(amount),
                "cart_id": item.get("cart_id"),
            }
        )
        group["amount"] += amount

    return items, {
        "groups": [
            {**group, "amount": float(group["amount"])} for group in groups.values()
        ],
        "items_total": float(total),
        "shipping_fee": 0.0,
        "total_amount": float(total),
    }


@bp.post("/preview")
@login_required
def preview():
    user = current_user()
    payload = Payload(request.get_json(silent=True))
    _, quote = _quote(user, payload)
    payload.done()
    return ok(quote)


# ------------------------------------------------------------------ 下单
@bp.post("")
@login_required
@idempotent("order.create")
def create_order():
    user = current_user()
    by_user("order.create", (10, 60), "下单过于频繁，请稍后再试")

    payload = Payload(request.get_json(silent=True))
    source = payload.choice("source", ("cart", "now"), required=False, default="cart", label="下单来源")
    pay_method = payload.choice("pay_method", (PayMethod.BALANCE, PayMethod.OFFLINE), label="支付方式")
    delivery_type = payload.choice("delivery_type", DeliveryType.ALL, required=False, default=DeliveryType.PICKUP, label="履约方式")
    remark = payload.text("remark", required=False, max_len=200, label="备注")
    items = _resolve_items(user, payload)
    receiver_name, receiver_phone, address_text = _resolve_receiver(user, payload)
    payload.done()

    orders = order_service.create_orders(
        user,
        items,
        pay_method=pay_method,
        delivery_type=delivery_type,
        receiver_name=receiver_name,
        receiver_phone=receiver_phone,
        address_text=address_text,
        remark=remark,
    )

    if source == "cart":
        cart_ids = [item["cart_id"] for item in items if item.get("cart_id")]
        if cart_ids:
            Cart.query.filter(Cart.user_id == user.id, Cart.id.in_(cart_ids)).delete(synchronize_session=False)
            db.session.commit()

    data = {
        "orders": [_view(order, "buyer") for order in orders],
        "order_ids": [order.id for order in orders],
        "total_amount": float(sum(Decimal(order.total_amount) for order in orders)),
        "pay_method": pay_method,
    }
    return created(data, "下单成功")


def _commented_ids(order_ids: list[int]) -> dict[int, set[int]]:
    if not order_ids:
        return {}
    rows = Comment.query.filter(Comment.order_id.in_(order_ids), Comment.is_deleted.is_(False)).all()
    result: dict[int, set[int]] = {}
    for row in rows:
        result.setdefault(row.order_id, set()).add(row.product_id)
    return result


def _view(order: Order, viewer_type: str = "buyer") -> dict:
    commented = _commented_ids([order.id]).get(order.id, set())
    return order_view(order, viewer_type, commented)


# ------------------------------------------------------------------ 查询
@bp.get("")
@login_required
def list_orders():
    user = current_user()
    query = Order.query.filter(Order.user_id == user.id)
    status = (request.args.get("status") or "").strip()
    if status and status in OrderStatus.ALL:
        query = query.filter(Order.status == status)
    query = query.order_by(Order.created_at.desc(), Order.id.desc())
    return ok(paginate(query, lambda o: _view(o, "buyer")))


@bp.get("/counts")
@login_required
def order_counts():
    user = current_user()
    rows = db.session.query(Order.status, func.count(Order.id)).filter(Order.user_id == user.id).group_by(Order.status).all()
    counts = {status: 0 for status in OrderStatus.ALL}
    for status, count in rows:
        counts[status] = int(count)
    return ok({"counts": counts, "total": sum(counts.values())})


@bp.get("/<int:order_id>")
@login_required
def order_detail(order_id: int):
    user = current_user()
    order = Order.query.filter(Order.id == order_id).first()
    if order is None:
        raise not_found("订单不存在")
    if order.user_id == user.id:
        viewer = "buyer"
    elif order.seller_id == user.id:
        viewer = "seller"
    else:
        raise forbidden("无权查看该订单")
    return ok(_view(order, viewer))


# ------------------------------------------------------------------ 操作
@bp.post("/<int:order_id>/pay")
@login_required
@idempotent("order.pay")
def pay(order_id: int):
    user = current_user()
    order = _load(order_id)
    order_service.pay_order(order, user)
    return ok(_view(order, "buyer"), "支付成功")


@bp.post("/<int:order_id>/cancel")
@login_required
def cancel(order_id: int):
    user = current_user()
    order = _load(order_id)
    if order.user_id != user.id:
        raise forbidden("只能操作自己的订单")
    payload = Payload(request.get_json(silent=True))
    reason = payload.text("reason", required=False, max_len=100, label="取消原因", default="买家主动取消")
    payload.done()
    order_service.cancel_order(order, "买家", user, reason)
    db.session.commit()
    return ok(_view(order, "buyer"), "订单已取消")


@bp.post("/<int:order_id>/confirm")
@login_required
def confirm(order_id: int):
    user = current_user()
    order = _load(order_id)
    order_service.confirm_order(order, user)
    return ok(_view(order, "buyer"), "已确认收货")


@bp.post("/<int:order_id>/refund")
@login_required
def refund(order_id: int):
    user = current_user()
    order = _load(order_id)
    payload = Payload(request.get_json(silent=True))
    reason = payload.text("reason", min_len=2, max_len=100, label="退款原因")
    payload.done()
    order_service.request_refund(order, user, reason)
    return ok(_view(order, "buyer"), "退款申请已提交")


@bp.post("/<int:order_id>/cancel-refund")
@login_required
def cancel_refund(order_id: int):
    user = current_user()
    order = _load(order_id)
    order_service.cancel_refund(order, user)
    return ok(_view(order, "buyer"), "已撤销退款申请")


def _load(order_id: int) -> Order:
    order = Order.query.filter(Order.id == order_id).first()
    if order is None:
        raise not_found("订单不存在")
    return order
