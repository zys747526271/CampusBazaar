"""商品模型（PRD 3.2 商品状态机）。"""
from __future__ import annotations

from decimal import Decimal

from backend.constants import ProductCondition, ProductStatus
from backend.extensions import db
from backend.models.base import SoftDeleteMixin, TimestampMixin


class Product(db.Model, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False, index=True)
    description = db.Column(db.Text, default="", nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    #: 划线价（原价），仅用于展示折扣感，不参与结算
    original_price = db.Column(db.Numeric(10, 2), nullable=True)

    quantity = db.Column(db.Integer, default=1, nullable=False)
    sales = db.Column(db.Integer, default=0, nullable=False)
    views = db.Column(db.Integer, default=0, nullable=False)

    #: 图片 URL 列表，第一张为主图
    images = db.Column(db.JSON, default=list, nullable=False)
    product_condition = db.Column(db.String(10), default=ProductCondition.LIKE_NEW, nullable=False)
    location = db.Column(db.String(60), default="", nullable=False)

    tag_id = db.Column(db.Integer, db.ForeignKey("tags.id"), nullable=True, index=True)
    seller_category_id = db.Column(db.Integer, db.ForeignKey("seller_categories.id"), nullable=True)
    seller_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    status = db.Column(db.String(10), default=ProductStatus.PENDING, nullable=False)
    is_available = db.Column(db.Boolean, default=True, nullable=False)
    is_featured = db.Column(db.Boolean, default=False, nullable=False)
    reject_reason = db.Column(db.String(200), default="", nullable=False)
    audited_at = db.Column(db.DateTime(timezone=True), nullable=True)
    audited_by = db.Column(db.Integer, db.ForeignKey("admins.id"), nullable=True)
    sold_out_at = db.Column(db.DateTime(timezone=True), nullable=True)

    seller = db.relationship("User", lazy="selectin")
    tag = db.relationship("Tag", lazy="selectin")
    seller_category = db.relationship("SellerCategory", lazy="selectin")

    __table_args__ = (
        db.Index("idx_product_status_created", "status", "created_at"),
        db.Index("idx_product_seller", "seller_id", "is_deleted"),
        db.Index("idx_product_tag_status", "tag_id", "status"),
        db.Index("idx_product_price", "price"),
        db.Index("idx_product_sales", "sales"),
    )

    @property
    def cover_image(self) -> str:
        images = self.images or []
        return images[0] if images else ""

    @property
    def is_on_sale(self) -> bool:
        """买家侧唯一可见判定，列表、详情、下单三处共用。"""
        return (
            self.status == ProductStatus.APPROVED
            and bool(self.is_available)
            and self.quantity > 0
            and not self.is_deleted
        )

    @property
    def stock_state(self) -> str:
        if self.is_deleted:
            return "已删除"
        if self.status != ProductStatus.APPROVED:
            return self.status
        if not self.is_available or self.quantity <= 0:
            return "已售罄"
        return "在售"

    @property
    def discount(self) -> float:
        if self.original_price and self.original_price > 0 and self.original_price > self.price:
            return round(float(Decimal(self.price) / Decimal(self.original_price)) * 10, 1)
        return 0.0

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Product {self.id} {self.name}>"
