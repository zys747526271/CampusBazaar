"""平台分类（Tag）、卖家私有分类（SellerCategory）、首页轮播（Banner）。"""
from __future__ import annotations

from backend.extensions import db
from backend.models.base import SoftDeleteMixin, TimestampMixin


class Tag(db.Model, TimestampMixin, SoftDeleteMixin):
    """平台分类：全站导航与筛选的唯一来源，由管理员维护。"""

    __tablename__ = "tags"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), nullable=False, unique=True)
    icon = db.Column(db.String(30), default="", nullable=False)
    description = db.Column(db.String(120), default="", nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Tag {self.name}>"


class SellerCategory(db.Model, TimestampMixin):
    """卖家私有分类：只用于卖家自己整理商品，绝不参与全站导航。"""

    __tablename__ = "seller_categories"

    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(30), nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("seller_id", "name", name="uk_seller_category_name"),
    )


class Banner(db.Model, TimestampMixin):
    """首页轮播位：管理员可配置，前台按 sort_order 升序展示。"""

    __tablename__ = "banners"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(60), nullable=False)
    subtitle = db.Column(db.String(120), default="", nullable=False)
    image_url = db.Column(db.String(255), nullable=False)
    link_url = db.Column(db.String(255), default="", nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
