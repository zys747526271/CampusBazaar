"""收货地址、余额与余额流水。"""
from __future__ import annotations

from decimal import Decimal

from backend.extensions import db
from backend.models.base import TimestampMixin
from backend.utils.common import utcnow


class Address(db.Model, TimestampMixin):
    __tablename__ = "addresses"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(30), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    campus_area = db.Column(db.String(60), default="", nullable=False)
    detail = db.Column(db.String(200), nullable=False)
    is_default = db.Column(db.Boolean, default=False, nullable=False)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False, index=True)


class Balance(db.Model, TimestampMixin):
    __tablename__ = "balances"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    amount = db.Column(db.Numeric(12, 2), default=Decimal("0.00"), nullable=False)


class BalanceLog(db.Model):
    __tablename__ = "balance_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    balance_after = db.Column(db.Numeric(12, 2), nullable=False)
    type = db.Column(db.String(10), nullable=False)
    ref_type = db.Column(db.String(20), default="", nullable=False)
    ref_id = db.Column(db.String(40), default="", nullable=False)
    remark = db.Column(db.String(120), default="", nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    __table_args__ = (
        db.Index("idx_balance_log_user", "user_id", "created_at"),
    )
