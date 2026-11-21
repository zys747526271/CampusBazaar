"""购物车、订单、订单明细与状态流水（PRD 3.3 / 3.4）。"""
from __future__ import annotations

from decimal import Decimal

from backend.constants import DeliveryType, OrderStatus, PayMethod
from backend.extensions import db
from backend.models.base import TimestampMixin
from backend.utils.common import utcnow


class Cart(db.Model, TimestampMixin):
    __tablename__ = "carts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    selected = db.Column(db.Boolean, default=True, nullable=False)

    product = db.relationship("Product", lazy="selectin")

    __table_args__ = (
        db.UniqueConstraint("user_id", "product_id", name="uk_cart_user_product"),
    )


class Order(db.Model, TimestampMixin):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    order_no = db.Column(db.String(24), nullable=False, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    seller_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    status = db.Column(db.String(10), default=OrderStatus.UNPAID, nullable=False)
    pay_method = db.Column(db.String(10), default=PayMethod.OFFLINE, nullable=False)
    delivery_type = db.Column(db.String(10), default=DeliveryType.PICKUP, nullable=False)

    items_total = db.Column(db.Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    shipping_fee = db.Column(db.Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), default=Decimal("0.00"), nullable=False)

    receiver_name = db.Column(db.String(30), default="", nullable=False)
    receiver_phone = db.Column(db.String(20), default="", nullable=False)
    address_text = db.Column(db.String(255), default="", nullable=False)
    remark = db.Column(db.String(200), default="", nullable=False)

    # ---- 自提信息（v2.2）----
    #: 下单时从商品带过来的自提点；卖家可补录
    pickup_location = db.Column(db.String(120), default="", nullable=False)
    #: 买卖双方约定的自提时间，确认收货前必填
    pickup_time = db.Column(db.DateTime(timezone=True), nullable=True)
    pickup_time_confirmed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    pickup_location_set_at = db.Column(db.DateTime(timezone=True), nullable=True)


    pay_deadline = db.Column(db.DateTime(timezone=True), nullable=True)
    paid_at = db.Column(db.DateTime(timezone=True), nullable=True)
    shipped_at = db.Column(db.DateTime(timezone=True), nullable=True)
    finished_at = db.Column(db.DateTime(timezone=True), nullable=True)
    cancelled_at = db.Column(db.DateTime(timezone=True), nullable=True)

    ship_company = db.Column(db.String(40), default="", nullable=False)
    tracking_no = db.Column(db.String(60), default="", nullable=False)

    cancel_reason = db.Column(db.String(200), default="", nullable=False)
    refund_reason = db.Column(db.String(200), default="", nullable=False)
    refund_note = db.Column(db.String(200), default="", nullable=False)
    #: 申请退款前的状态，用于卖家驳回后退回原状态
    refund_prev_status = db.Column(db.String(10), default="", nullable=False)

    items = db.relationship(
        "OrderItem", back_populates="order", lazy="selectin", cascade="all, delete-orphan"
    )
    logs = db.relationship(
        "OrderStatusLog",
        back_populates="order",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="OrderStatusLog.id",
    )
    buyer = db.relationship("User", foreign_keys=[user_id], lazy="selectin")
    seller = db.relationship("User", foreign_keys=[seller_id], lazy="selectin")
    snapshot = db.relationship(
        "OrderSnapshot", back_populates="order", uselist=False, lazy="selectin", cascade="all, delete-orphan"
    )

    __table_args__ = (
        db.Index("idx_order_user_status", "user_id", "status"),
        db.Index("idx_order_seller_status", "seller_id", "status"),
        db.Index("idx_order_created", "created_at"),
    )

    @property
    def item_count(self) -> int:
        return sum(item.quantity for item in self.items)

    @property
    def is_pickup(self) -> bool:
        return self.delivery_type == DeliveryType.PICKUP

    @property
    def needs_pickup_location(self) -> bool:
        """自提点为空时，需要卖家下单后补录并推送买家。"""
        return self.is_pickup and not (self.pickup_location or "").strip()

    @property
    def is_expired(self) -> bool:
        from backend.utils.common import ensure_aware, utcnow

        if self.status != OrderStatus.UNPAID or not self.pay_deadline:
            return False
        return ensure_aware(self.pay_deadline) <= utcnow()


class OrderItem(db.Model):
    """订单商品快照：下单瞬间固化名称、单价、图片，后续改价不影响历史订单。"""

    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=True, index=True)

    name = db.Column(db.String(80), nullable=False)
    image = db.Column(db.String(255), default="", nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    product_condition = db.Column(db.String(10), default="", nullable=False)

    order = db.relationship("Order", back_populates="items")
    product = db.relationship("Product", lazy="selectin")

    @property
    def subtotal(self):
        return (Decimal(self.price) * self.quantity).quantize(Decimal("0.01"))


class OrderStatusLog(db.Model):
    """状态流水：追加写，作为纠纷证据（PRD 3.3）。"""

    __tablename__ = "order_status_logs"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False, index=True)
    from_status = db.Column(db.String(10), default="", nullable=False)
    to_status = db.Column(db.String(10), nullable=False)
    operator_type = db.Column(db.String(10), default="系统", nullable=False)
    operator_id = db.Column(db.Integer, nullable=True)
    operator_name = db.Column(db.String(40), default="", nullable=False)
    remark = db.Column(db.String(200), default="", nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    order = db.relationship("Order", back_populates="logs")


class OrderSnapshot(db.Model):
    """交易快照：下单瞬间固化商品介绍页与详情页内容，供纠纷取证。

    ``html_path`` 指向自包含 HTML（图片已内联为 data URI），
    ``data`` 保留结构化字段，便于接口二次展示与后续检索。
    """

    __tablename__ = "order_snapshots"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False, unique=True, index=True)
    html_path = db.Column(db.String(255), default="", nullable=False)
    data = db.Column(db.JSON, default=dict, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    order = db.relationship("Order", back_populates="snapshot")
