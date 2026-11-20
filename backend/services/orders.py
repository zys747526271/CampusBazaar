"""订单服务：下单、支付、发货、确认收货、取消、退款、超时处理。

设计要点：
- 库存扣减用条件更新 ``UPDATE ... WHERE quantity >= n``，影响行数为 0 即库存不足；
- 所有状态变更必须经过 ``_transition``，非法迁移返回 409 并写流水；
- 金额一律服务端用 Decimal 计算，客户端传入的价格不参与。
"""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from sqlalchemy import update

from backend.constants import (
    BalanceLogType,
    DeliveryType,
    Limits,
    MessageType,
    OperatorType,
    OrderStatus,
    PayMethod,
    ProductStatus,
)
from backend.errors import bad_request, conflict, forbidden, not_found
from backend.extensions import db
from backend.models import Balance, BalanceLog, Order, OrderItem, OrderStatusLog, Product, User
from backend.utils.common import order_no, utcnow
from backend.utils.notify import notify

ZERO = Decimal("0.00")


# ------------------------------------------------------------------ 内部工具
def _log(order: Order, from_status: str, to_status: str, operator_type: str, operator_id=None, operator_name="", remark=""):
    db.session.add(
        OrderStatusLog(
            order_id=order.id,
            from_status=from_status,
            to_status=to_status,
            operator_type=operator_type,
            operator_id=operator_id,
            operator_name=(operator_name or "")[:40],
            remark=(remark or "")[:200],
            created_at=utcnow(),
        )
    )


def _transition(order: Order, to_status: str, operator_type: str, operator_id=None, operator_name="", remark=""):
    from_status = order.status
    order.status = to_status
    _log(order, from_status, to_status, operator_type, operator_id, operator_name, remark)


def _restore_stock(order: Order) -> None:
    for item in order.items:
        if not item.product_id:
            continue
        db.session.execute(
            update(Product)
            .where(Product.id == item.product_id)
            .values(quantity=Product.quantity + item.quantity)
        )


def _apply_sales(order: Order, sign: int = 1) -> None:
    for item in order.items:
        if not item.product_id:
            continue
        db.session.execute(
            update(Product)
            .where(Product.id == item.product_id)
            .values(sales=Product.sales + sign * item.quantity)
        )


def get_balance(user_id: int, create: bool = True) -> Balance | None:
    balance = Balance.query.filter_by(user_id=user_id).first()
    if balance is None and create:
        balance = Balance(user_id=user_id, amount=ZERO)
        db.session.add(balance)
        db.session.flush()
    return balance


def _deduct_balance(user_id: int, amount: Decimal, ref_type: str, ref_id: str, remark: str) -> None:
    result = db.session.execute(
        update(Balance)
        .where(Balance.user_id == user_id, Balance.amount >= amount)
        .values(amount=Balance.amount - amount)
    )
    if result.rowcount == 0:
        raise bad_request("余额不足，请先充值或改用线下支付")
    balance = get_balance(user_id, create=False)
    db.session.refresh(balance)
    db.session.add(
        BalanceLog(
            user_id=user_id,
            amount=-amount,
            balance_after=balance.amount,
            type=BalanceLogType.PAY,
            ref_type=ref_type,
            ref_id=ref_id,
            remark=remark[:120],
        )
    )


def _add_balance(user_id: int, amount: Decimal, log_type: str, ref_type: str, ref_id: str, remark: str) -> None:
    result = db.session.execute(
        update(Balance).where(Balance.user_id == user_id).values(amount=Balance.amount + amount)
    )
    if result.rowcount == 0:
        db.session.add(Balance(user_id=user_id, amount=amount))
    balance = get_balance(user_id, create=False)
    db.session.refresh(balance)
    db.session.add(
        BalanceLog(
            user_id=user_id,
            amount=amount,
            balance_after=balance.amount,
            type=log_type,
            ref_type=ref_type,
            ref_id=ref_id,
            remark=remark[:120],
        )
    )


# ------------------------------------------------------------------ 下单
def create_orders(
    user: User,
    items: list[dict],
    *,
    pay_method: str,
    delivery_type: str,
    receiver_name: str,
    receiver_phone: str,
    address_text: str,
    remark: str = "",
) -> list[Order]:
    if pay_method not in PayMethod.SUPPORTED:
        raise bad_request("暂不支持该支付方式")
    if delivery_type not in DeliveryType.ALL:
        raise bad_request("履约方式不合法")
    if not items:
        raise bad_request("请选择要购买的商品")
    if len(items) > Limits.ORDER_MAX_ITEMS:
        raise bad_request(f"单次最多购买 {Limits.ORDER_MAX_ITEMS} 件商品")

    # 合并同商品数量
    merged: dict[int, int] = {}
    for item in items:
        try:
            product_id = int(item["product_id"])
            quantity = int(item["quantity"])
        except (KeyError, TypeError, ValueError) as exc:
            raise bad_request("商品参数不正确") from exc
        if quantity <= 0:
            raise bad_request("购买数量必须大于 0")
        merged[product_id] = merged.get(product_id, 0) + quantity

    products = Product.query.filter(Product.id.in_(merged.keys())).all()
    product_map = {p.id: p for p in products}
    missing = [pid for pid in merged if pid not in product_map]
    if missing:
        raise not_found(f"商品不存在或已被删除（ID: {missing[0]}）")

    for product in products:
        if product.seller_id == user.id:
            raise forbidden("不能购买自己发布的商品")
        if product.status != ProductStatus.APPROVED or not product.is_available or product.is_deleted:
            raise conflict(f"《{product.name}》已下架，无法购买")
        if product.quantity < merged[product.id]:
            raise conflict(f"《{product.name}》库存不足，仅剩 {max(product.quantity, 0)} 件")

    # 逐件条件扣减库存（并发下只有一句 UPDATE 成功）
    for product in products:
        quantity = merged[product.id]
        result = db.session.execute(
            update(Product)
            .where(
                Product.id == product.id,
                Product.quantity >= quantity,
                Product.status == ProductStatus.APPROVED,
                Product.is_available.is_(True),
                Product.is_deleted.is_(False),
            )
            .values(quantity=Product.quantity - quantity)
        )
        if result.rowcount == 0:
            raise conflict(f"《{product.name}》刚被其他同学买走了，请刷新后重试")

    # 按卖家拆单（与主流电商一致：一次结算生成多个卖家订单）
    grouped: dict[int, list[Product]] = {}
    for product in products:
        grouped.setdefault(product.seller_id, []).append(product)

    orders: list[Order] = []
    for seller_id, seller_products in grouped.items():
        items_total = ZERO
        order = Order(
            order_no=_unique_order_no(),
            user_id=user.id,
            seller_id=seller_id,
            status=OrderStatus.UNPAID,
            pay_method=pay_method,
            delivery_type=delivery_type,
            receiver_name=receiver_name,
            receiver_phone=receiver_phone,
            address_text=address_text,
            remark=remark[:200],
            pay_deadline=utcnow() + timedelta(minutes=Limits.ORDER_PAY_TIMEOUT_MINUTES),
        )
        db.session.add(order)
        db.session.flush()
        for product in seller_products:
            quantity = merged[product.id]
            subtotal = (Decimal(product.price) * quantity).quantize(Decimal("0.01"))
            items_total += subtotal
            db.session.add(
                OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    name=product.name,
                    image=product.cover_image,
                    price=product.price,
                    quantity=quantity,
                    product_condition=product.product_condition,
                )
            )
        order.items_total = items_total
        order.shipping_fee = ZERO
        order.total_amount = items_total
        _log(order, "", OrderStatus.UNPAID, OperatorType.BUYER, user.id, user.nickname, "提交订单")
        notify(
            seller_id,
            MessageType.ORDER,
            "你有新的订单",
            f"订单 {order.order_no} 待处理，请及时与买家确认交易方式。",
            f"/seller/orders",
        )
        orders.append(order)

    # 商品库存为 0 时自动置为不可售（PRD 3.2）
    for product in products:
        remaining = product.quantity - merged[product.id]
        if remaining <= 0:
            db.session.execute(
                update(Product).where(Product.id == product.id).values(is_available=False, sold_out_at=utcnow())
            )
    db.session.commit()
    for order in orders:
        db.session.refresh(order)
    return orders


def _unique_order_no(attempts: int = 8) -> str:
    """同日 6 位随机，重试避让已有订单号；极端情况下宁可报 409 也不出重复单号。"""
    for _ in range(attempts):
        candidate = order_no()
        if not Order.query.filter_by(order_no=candidate).first():
            return candidate
    raise conflict("订单号生成失败，请重试")


# ------------------------------------------------------------------ 支付
def pay_order(order: Order, user: User) -> Order:
    _ensure_owner(order, user)
    if order.status != OrderStatus.UNPAID:
        raise conflict("订单当前状态不可支付，请刷新后重试")
    if order.is_expired:
        cancel_order(order, OperatorType.SYSTEM, None, "超时未支付，系统自动取消")
        db.session.commit()
        raise conflict("订单已超时取消，请重新下单")
    if order.pay_method != PayMethod.BALANCE:
        raise bad_request("该订单为线下支付，请等待卖家确认收款")

    _deduct_balance(user.id, Decimal(order.total_amount), "order", str(order.id), f"支付订单 {order.order_no}")
    _transition(order, OrderStatus.PAID, OperatorType.BUYER, user.id, user.nickname, "余额支付成功")
    order.paid_at = utcnow()
    notify(
        order.seller_id,
        MessageType.ORDER,
        "买家已付款",
        f"订单 {order.order_no} 已付款，请尽快发货或约定自提。",
        "/seller/orders",
    )
    db.session.commit()
    db.session.refresh(order)
    return order


def confirm_offline_paid(order: Order, seller: User) -> Order:
    _ensure_seller(order, seller)
    if order.status != OrderStatus.UNPAID:
        raise conflict("订单当前状态不可确认收款")
    if order.pay_method != PayMethod.OFFLINE:
        raise bad_request("该订单不是线下支付")
    _transition(order, OrderStatus.PAID, OperatorType.SELLER, seller.id, seller.nickname, "卖家确认线下收款")
    order.paid_at = utcnow()
    notify(
        order.user_id,
        MessageType.ORDER,
        "卖家已确认收款",
        f"订单 {order.order_no} 已进入待发货状态。",
        f"/orders/{order.id}",
    )
    db.session.commit()
    db.session.refresh(order)
    return order


# ------------------------------------------------------------------ 履约
def ship_order(order: Order, seller: User, *, ship_company: str = "", tracking_no: str = "", note: str = "") -> Order:
    _ensure_seller(order, seller)
    if order.status != OrderStatus.PAID:
        raise conflict("只有已付款订单可以发货")
    if order.delivery_type == DeliveryType.EXPRESS and not tracking_no.strip():
        raise bad_request("快递发货请填写快递单号", {"tracking_no": "快递单号不能为空"})
    order.ship_company = ship_company[:40]
    order.tracking_no = tracking_no[:60]
    _transition(
        order,
        OrderStatus.SHIPPED,
        OperatorType.SELLER,
        seller.id,
        seller.nickname,
        note or (f"{order.delivery_type}已安排" if order.delivery_type != DeliveryType.EXPRESS else "已发货"),
    )
    order.shipped_at = utcnow()
    notify(
        order.user_id,
        MessageType.ORDER,
        "卖家已发货",
        f"订单 {order.order_no} 已发货，请及时确认收货。",
        f"/orders/{order.id}",
    )
    db.session.commit()
    db.session.refresh(order)
    return order


def confirm_order(order: Order, user: User) -> Order:
    _ensure_owner(order, user)
    if order.status != OrderStatus.SHIPPED:
        raise conflict("只有已发货订单可以确认收货")
    _transition(order, OrderStatus.DONE, OperatorType.BUYER, user.id, user.nickname, "买家确认收货")
    order.finished_at = utcnow()
    _apply_sales(order, 1)
    notify(
        order.seller_id,
        MessageType.FUND,
        "订单已完成",
        f"订单 {order.order_no} 买家已确认收货，货款计入你的收入。",
        "/seller/orders",
    )
    notify(order.user_id, MessageType.ORDER, "交易完成", "感谢使用校园集市，别忘了给卖家一个评价。", f"/orders/{order.id}")
    db.session.commit()
    db.session.refresh(order)
    return order


def cancel_order(order: Order, operator_type: str, operator, reason: str = "") -> Order:
    if order.status not in (OrderStatus.UNPAID, OrderStatus.PAID):
        raise conflict("当前状态不可取消")
    was_paid = order.status == OrderStatus.PAID and order.paid_at is not None
    operator_name = getattr(operator, "nickname", "") or getattr(operator, "username", "") or "系统"
    _restore_stock(order)
    _transition(
        order,
        OrderStatus.CANCELLED,
        operator_type,
        getattr(operator, "id", None),
        operator_name,
        reason or "订单取消",
    )
    order.cancelled_at = utcnow()
    order.cancel_reason = (reason or "订单取消")[:200]
    # 已付款订单被取消（买家申请后管理员介入 / 卖家关单）需退回余额
    if was_paid and order.pay_method == PayMethod.BALANCE:
        _add_balance(
            order.user_id,
            Decimal(order.total_amount),
            BalanceLogType.REFUND,
            "order",
            str(order.id),
            f"订单 {order.order_no} 取消退款",
        )
    notify(
        order.user_id,
        MessageType.ORDER,
        "订单已取消",
        f"订单 {order.order_no} 已取消：{order.cancel_reason}",
        f"/orders/{order.id}",
    )
    return order


# ------------------------------------------------------------------ 退款
def request_refund(order: Order, user: User, reason: str) -> Order:
    _ensure_owner(order, user)
    if order.status not in (OrderStatus.PAID, OrderStatus.SHIPPED):
        raise conflict("当前状态不可申请退款")
    if not reason.strip():
        raise bad_request("请填写退款原因", {"reason": "退款原因不能为空"})
    order.refund_prev_status = order.status
    order.refund_reason = reason[:200]
    _transition(order, OrderStatus.REFUNDING, OperatorType.BUYER, user.id, user.nickname, f"申请退款：{reason}")
    notify(
        order.seller_id,
        MessageType.ORDER,
        "买家申请退款",
        f"订单 {order.order_no} 申请退款：{reason}",
        "/seller/orders",
    )
    db.session.commit()
    db.session.refresh(order)
    return order


def cancel_refund(order: Order, user: User) -> Order:
    """买家在卖家处理前撤销退款申请，回到申请前的状态。"""
    _ensure_owner(order, user)
    if order.status != OrderStatus.REFUNDING:
        raise conflict("该订单没有待处理的退款申请")
    back_status = order.refund_prev_status or OrderStatus.PAID
    order.refund_reason = ""
    order.refund_note = "买家撤销退款申请"
    _transition(order, back_status, OperatorType.BUYER, user.id, user.nickname, "买家撤销退款申请")
    notify(
        order.seller_id,
        MessageType.ORDER,
        "买家撤销了退款申请",
        f"订单 {order.order_no} 已恢复为「{back_status}」。",
        "/seller/orders",
    )
    db.session.commit()
    db.session.refresh(order)
    return order


def handle_refund(order: Order, actor, approve: bool, note: str = "", operator_type: str = OperatorType.SELLER) -> Order:
    if order.status != OrderStatus.REFUNDING:
        raise conflict("该订单没有待处理的退款申请")
    actor_id = getattr(actor, "id", None)
    actor_name = getattr(actor, "nickname", "") or getattr(actor, "username", "")
    if approve:
        _restore_stock(order)
        if order.pay_method == PayMethod.BALANCE:
            _add_balance(
                order.user_id,
                Decimal(order.total_amount),
                BalanceLogType.REFUND,
                "order",
                str(order.id),
                f"订单 {order.order_no} 退款",
            )
        _transition(order, OrderStatus.CANCELLED, operator_type, actor_id, actor_name, note or "同意退款")
        order.cancelled_at = utcnow()
        order.cancel_reason = "退款关闭"
        order.refund_note = (note or "卖家同意退款")[:200]
        notify(
            order.user_id,
            MessageType.FUND,
            "退款已处理",
            f"订单 {order.order_no} 已退款，金额已退回余额（线下支付请与卖家线下结算）。",
            f"/orders/{order.id}",
        )
    else:
        back_status = order.refund_prev_status or OrderStatus.PAID
        order.refund_note = (note or "卖家驳回退款")[:200]
        _transition(order, back_status, operator_type, actor_id, actor_name, f"驳回退款：{note or '不符合退款条件'}")
        notify(
            order.user_id,
            MessageType.ORDER,
            "退款被驳回",
            f"订单 {order.order_no} 的退款申请被驳回：{note or '不符合退款条件'}",
            f"/orders/{order.id}",
        )
    db.session.commit()
    db.session.refresh(order)
    return order


# ------------------------------------------------------------------ 系统任务
def expire_unpaid_orders(limit: int = 200) -> int:
    now = utcnow()
    orders = (
        Order.query.filter(Order.status == OrderStatus.UNPAID, Order.pay_deadline.isnot(None), Order.pay_deadline <= now)
        .limit(limit)
        .all()
    )
    for order in orders:
        _restore_stock(order)
        _transition(order, OrderStatus.CANCELLED, OperatorType.SYSTEM, None, "系统", "超时未支付，自动取消")
        order.cancelled_at = now
        order.cancel_reason = "超时未支付，系统自动取消"
        notify(order.user_id, MessageType.ORDER, "订单已自动取消", f"订单 {order.order_no} 超过 30 分钟未支付，已自动取消。", f"/orders/{order.id}")
    if orders:
        db.session.commit()
    return len(orders)


def auto_confirm_shipped(days: int = 7, limit: int = 200) -> int:
    from datetime import timedelta

    deadline = utcnow() - timedelta(days=days)
    orders = (
        Order.query.filter(
            Order.status == OrderStatus.SHIPPED,
            Order.shipped_at.isnot(None),
            Order.shipped_at <= deadline,
        )
        .limit(limit)
        .all()
    )
    for order in orders:
        _transition(order, OrderStatus.DONE, OperatorType.SYSTEM, None, "系统", f"发货满 {days} 天自动确认收货")
        order.finished_at = utcnow()
        _apply_sales(order, 1)
        notify(order.seller_id, MessageType.FUND, "订单已完成", f"订单 {order.order_no} 已自动确认收货。", "/seller/orders")
    if orders:
        db.session.commit()
    return len(orders)


def mark_sold_out_products(limit: int = 200) -> int:
    rows = (
        Product.query.filter(
            Product.quantity <= 0,
            Product.is_available.is_(True),
            Product.status == ProductStatus.APPROVED,
            Product.is_deleted.is_(False),
        )
        .limit(limit)
        .all()
    )
    for product in rows:
        product.is_available = False
        product.sold_out_at = utcnow()
    if rows:
        db.session.commit()
    return len(rows)


# ------------------------------------------------------------------ 校验
def _ensure_owner(order: Order, user: User) -> None:
    if order.user_id != user.id:
        raise forbidden("只能操作自己的订单")


def _ensure_seller(order: Order, user: User) -> None:
    if order.seller_id != user.id:
        raise forbidden("只能操作自己店铺的订单")
