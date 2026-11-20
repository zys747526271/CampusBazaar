"""评价、点赞、收藏、浏览记录、举报。"""
from __future__ import annotations

from backend.constants import ReportStatus, ReportTarget
from backend.extensions import db
from backend.models.base import SoftDeleteMixin, TimestampMixin
from backend.utils.common import utcnow


class Comment(db.Model, TimestampMixin):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    rating = db.Column(db.Integer, nullable=False)
    content = db.Column(db.String(500), default="", nullable=False)
    images = db.Column(db.JSON, default=list, nullable=False)

    is_hidden = db.Column(db.Boolean, default=False, nullable=False, index=True)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    like_count = db.Column(db.Integer, default=0, nullable=False)

    seller_reply = db.Column(db.String(300), default="", nullable=False)
    seller_reply_at = db.Column(db.DateTime(timezone=True), nullable=True)

    order = db.relationship("Order", lazy="selectin")
    product = db.relationship("Product", lazy="selectin")
    user = db.relationship("User", lazy="selectin")

    __table_args__ = (
        db.UniqueConstraint("order_id", "product_id", name="uk_comment_order_product"),
        db.Index("idx_comment_product_visible", "product_id", "is_hidden", "is_deleted"),
    )

    @property
    def visible(self) -> bool:
        return not self.is_hidden and not self.is_deleted


class CommentLike(db.Model):
    __tablename__ = "comment_likes"

    id = db.Column(db.Integer, primary_key=True)
    comment_id = db.Column(db.Integer, db.ForeignKey("comments.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("comment_id", "user_id", name="uk_comment_like"),
    )


class Favorite(db.Model):
    __tablename__ = "favorites"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    product = db.relationship("Product", lazy="selectin")

    __table_args__ = (
        db.UniqueConstraint("user_id", "product_id", name="uk_favorite_user_product"),
    )


class BrowseHistory(db.Model):
    __tablename__ = "browse_histories"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    viewed_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    view_count = db.Column(db.Integer, default=1, nullable=False)

    product = db.relationship("Product", lazy="selectin")

    __table_args__ = (
        db.UniqueConstraint("user_id", "product_id", name="uk_history_user_product"),
    )


class Report(db.Model, TimestampMixin):
    __tablename__ = "reports"

    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    target_type = db.Column(db.String(12), default=ReportTarget.PRODUCT, nullable=False)
    target_id = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(60), nullable=False)
    detail = db.Column(db.String(500), default="", nullable=False)
    status = db.Column(db.String(10), default=ReportStatus.PENDING, nullable=False, index=True)
    handler_id = db.Column(db.Integer, db.ForeignKey("admins.id"), nullable=True)
    handle_result = db.Column(db.String(200), default="", nullable=False)
    handled_at = db.Column(db.DateTime(timezone=True), nullable=True)

    reporter = db.relationship("User", lazy="selectin")


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("admins.id"), nullable=False, index=True)
    admin_name = db.Column(db.String(40), default="", nullable=False)
    action = db.Column(db.String(60), nullable=False, index=True)
    target_type = db.Column(db.String(30), default="", nullable=False)
    target_id = db.Column(db.String(40), default="", nullable=False)
    detail = db.Column(db.String(500), default="", nullable=False)
    ip = db.Column(db.String(60), default="", nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    type = db.Column(db.String(10), default="系统", nullable=False)
    title = db.Column(db.String(80), nullable=False)
    content = db.Column(db.String(500), default="", nullable=False)
    link = db.Column(db.String(200), default="", nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    __table_args__ = (
        db.Index("idx_message_user_read", "user_id", "is_read"),
    )
