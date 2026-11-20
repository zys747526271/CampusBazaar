"""用户与管理员（两套独立账号体系，PRD 3.1）。"""
from __future__ import annotations

from backend.constants import AdminLevel
from backend.extensions import db
from backend.models.base import SoftDeleteMixin, TimestampMixin
from backend.utils.common import utcnow


class User(db.Model, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), nullable=False, unique=True)
    nickname = db.Column(db.String(40), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    avatar_url = db.Column(db.String(255), default="", nullable=False)
    email = db.Column(db.String(120), default="", nullable=False)
    campus = db.Column(db.String(60), default="", nullable=False)

    is_seller = db.Column(db.Boolean, default=False, nullable=False, index=True)
    seller_since = db.Column(db.DateTime(timezone=True), nullable=True)
    is_banned = db.Column(db.Boolean, default=False, nullable=False, index=True)
    ban_reason = db.Column(db.String(200), default="", nullable=False)
    banned_at = db.Column(db.DateTime(timezone=True), nullable=True)

    last_login_at = db.Column(db.DateTime(timezone=True), nullable=True)

    __table_args__ = (
        db.Index("idx_user_seller", "is_seller", "is_deleted"),
    )

    def activate_seller(self) -> None:
        if not self.is_seller:
            self.is_seller = True
            self.seller_since = utcnow()

    def ban(self, reason: str) -> None:
        self.is_banned = True
        self.ban_reason = (reason or "")[:200]
        self.banned_at = utcnow()

    def unban(self) -> None:
        self.is_banned = False
        self.ban_reason = ""
        self.banned_at = None

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User {self.id} {self.nickname}>"


class Admin(db.Model, TimestampMixin):
    __tablename__ = "admins"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), nullable=False, unique=True)
    name = db.Column(db.String(40), default="", nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    permission_level = db.Column(db.String(10), default=AdminLevel.NORMAL, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    last_login_at = db.Column(db.DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Admin {self.id} {self.username}>"
