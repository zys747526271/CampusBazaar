"""认证：验证码、注册、登录、资料、改密、找回密码、管理员入口。"""
from __future__ import annotations

from flask import Blueprint, current_app, request

from backend.config import env_str
from backend.constants import AdminLevel, Limits
from backend.errors import bad_request, forbidden
from backend.extensions import db
from backend.models import Admin, Balance, User
from backend.utils import captcha as captcha_service
from backend.utils import limiter
from backend.utils.common import utcnow
from backend.utils.idempotency import idempotent
from backend.utils.logging import app_log, security_log
from backend.utils.response import created, ok
from backend.utils.security import (
    admin_required,
    bearer_token,
    create_token,
    current_admin,
    current_user,
    decode_token,
    hash_password,
    login_required,
    revoke_token,
    token_required,
    verify_password,
)
from backend.utils.validators import Payload
from backend.services.serializers import admin_view, user_me

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


# ------------------------------------------------------------------ 验证码
@bp.post("/captcha")
def send_captcha():
    payload = Payload(request.get_json(silent=True))
    phone = payload.phone()
    scene = payload.choice("scene", captcha_service.SCENES.keys(), required=False, default="register", label="场景")
    payload.done()

    limiter.by_phone("captcha", phone, Limits.RATE_CAPTCHA, "验证码发送过于频繁，请 60 秒后再试")
    result = captcha_service.issue(phone, scene)
    return ok(result, "验证码已发送")


# ------------------------------------------------------------------ 注册 / 登录
@bp.post("/register")
@idempotent("auth.register")
def register():
    payload = Payload(request.get_json(silent=True))
    phone = payload.phone()
    password = payload.password()
    nickname = payload.text("nickname", min_len=1, max_len=20, label="昵称")
    code = payload.text("code", max_len=6, label="验证码")
    campus = payload.text("campus", required=False, max_len=30, label="校区")
    agree = payload.boolean("agree_terms", default=False)
    payload.done()

    if not agree:
        raise bad_request("请先阅读并同意用户协议与隐私政策", {"agree_terms": "必须同意协议"})
    per_window = int(current_app.config.get("RATE_REGISTER_PER_5MIN", 5))
    limiter.by_ip("register", (per_window, 300), "注册过于频繁，请稍后再试")

    if User.query.filter(User.phone == phone, User.is_deleted.is_(False)).first():
        raise bad_request("该手机号已注册，可直接登录", {"phone": "手机号已注册"})

    captcha_service.verify(phone, "register", code)

    user = User(
        phone=phone,
        nickname=nickname,
        password_hash=hash_password(password),
        campus=campus,
        last_login_at=utcnow(),
    )
    db.session.add(user)
    db.session.flush()
    db.session.add(Balance(user_id=user.id, amount=0))
    db.session.commit()
    app_log("user.register", f"user_id={user.id}", user_id=user.id)

    token = create_token(user.id, "user")
    return created({"token": token, "user": user_me(user)}, "注册成功")


@bp.post("/login")
def login():
    payload = Payload(request.get_json(silent=True))
    phone = payload.phone()
    password = payload.text("password", max_len=64, label="密码")
    payload.done()

    limiter.by_phone("login", phone, Limits.RATE_LOGIN, "登录尝试过于频繁，请稍后再试")

    user = User.query.filter(User.phone == phone, User.is_deleted.is_(False)).first()
    if user is None or not verify_password(password, user.password_hash):
        security_log("login.failed", f"phone={phone[:3]}****", phone_prefix=phone[:3], ip=limiter.client_ip_or_unknown())
        raise bad_request("手机号或密码不正确", {"password": "手机号或密码不正确"})
    if user.is_banned:
        security_log("login.banned", f"user_id={user.id}", user_id=user.id)
        raise forbidden(user.ban_reason or "账号已被封禁，请联系管理员")

    user.last_login_at = utcnow()
    db.session.commit()
    token = create_token(user.id, "user")
    return ok({"token": token, "user": user_me(user)}, "登录成功")


@bp.post("/logout")
@token_required
def logout():
    revoke_token(decode_token(bearer_token()))
    return ok(None, "已退出登录")


# ------------------------------------------------------------------ 资料
@bp.get("/profile")
@login_required
def get_profile():
    return ok(user_me(current_user()))


@bp.put("/profile")
@login_required
def update_profile():
    user = current_user()
    payload = Payload(request.get_json(silent=True))
    user.nickname = payload.text("nickname", required=False, max_len=20, label="昵称", default=user.nickname)
    user.email = payload.text("email", required=False, max_len=120, label="邮箱", default=user.email)
    user.campus = payload.text("campus", required=False, max_len=30, label="校区", default=user.campus)
    avatar = payload.text("avatar_url", required=False, max_len=255, label="头像", default=user.avatar_url)
    payload.done()
    if user.email and "@" not in user.email:
        raise bad_request("邮箱格式不正确", {"email": "邮箱格式不正确"})
    user.avatar_url = avatar
    db.session.commit()
    return ok(user_me(user), "资料已更新")


@bp.put("/password")
@login_required
def change_password():
    user = current_user()
    payload = Payload(request.get_json(silent=True))
    old_password = payload.text("old_password", max_len=64, label="原密码")
    new_password = payload.password("new_password", "新密码")
    payload.done()
    if not verify_password(old_password, user.password_hash):
        raise bad_request("原密码不正确", {"old_password": "原密码不正确"})
    if old_password == new_password:
        raise bad_request("新密码不能与原密码相同", {"new_password": "请设置不同的新密码"})
    user.password_hash = hash_password(new_password)
    db.session.commit()
    security_log("password.changed", f"user_id={user.id}", user_id=user.id)
    return ok(None, "密码已修改，请使用新密码登录")


@bp.post("/reset-password")
@idempotent("auth.reset")
def reset_password():
    payload = Payload(request.get_json(silent=True))
    phone = payload.phone()
    code = payload.text("code", max_len=6, label="验证码")
    new_password = payload.password("new_password", "新密码")
    payload.done()

    limiter.by_phone("reset", phone, (5, 600), "操作过于频繁，请稍后再试")
    user = User.query.filter(User.phone == phone, User.is_deleted.is_(False)).first()
    if user is None:
        raise bad_request("该手机号未注册", {"phone": "手机号未注册"})
    if user.is_banned:
        raise forbidden("账号已被封禁，请联系管理员")
    captcha_service.verify(phone, "reset", code)
    user.password_hash = hash_password(new_password)
    db.session.commit()
    security_log("password.reset", f"user_id={user.id}", user_id=user.id)
    return ok(None, "密码已重置，请使用新密码登录")


# ------------------------------------------------------------------ 管理员
@bp.post("/admin/login")
def admin_login():
    payload = Payload(request.get_json(silent=True))
    username = payload.text("username", min_len=3, max_len=40, label="管理员账号")
    password = payload.text("password", max_len=64, label="密码")
    payload.done()

    limiter.assert_admin_not_locked(username)
    admin = Admin.query.filter(Admin.username == username).first()
    if admin is None or not verify_password(password, admin.password_hash):
        limiter.record_admin_failure(username)
        security_log("admin.login.failed", f"username={username}", username=username)
        raise bad_request("账号或密码不正确", {"password": "账号或密码不正确"})
    if not admin.is_active:
        raise forbidden("该管理员账号已停用")

    limiter.clear_admin_failure(username)
    admin.last_login_at = utcnow()
    db.session.commit()
    token = create_token(admin.id, "admin")
    security_log("admin.login", f"admin={admin.username}", admin=admin.username)
    return ok({"token": token, "admin": admin_view(admin)}, "登录成功")


@bp.post("/admin/register")
def admin_register():
    if not _admin_registration_enabled():
        raise forbidden("管理员注册入口未开放")

    payload = Payload(request.get_json(silent=True))
    username = payload.text("username", min_len=3, max_len=40, label="管理员账号")
    password = payload.password()
    name = payload.text("name", required=False, max_len=40, label="姓名")
    invite_code = payload.text("invite_code", required=False, max_len=64, label="邀请码")
    payload.done()

    required_code = _admin_invite_code()
    if required_code and invite_code != required_code:
        security_log("admin.register.bad_invite", f"username={username}", username=username)
        raise forbidden("邀请码不正确")
    if Admin.query.filter(Admin.username == username).first():
        raise bad_request("该管理员账号已存在", {"username": "账号已存在"})

    admin = Admin(
        username=username,
        name=name or username,
        password_hash=hash_password(password),
        permission_level=AdminLevel.NORMAL,
    )
    db.session.add(admin)
    db.session.commit()
    security_log("admin.register", f"admin={admin.username}", admin=admin.username)
    return created({"admin": admin_view(admin)}, "管理员账号创建成功")


@bp.get("/admin/profile")
@admin_required
def admin_profile():
    return ok(admin_view(current_admin()))


def _admin_registration_enabled() -> bool:
    from flask import current_app

    return bool(current_app.config.get("ADMIN_REGISTRATION_ENABLED"))


def _admin_invite_code() -> str:
    from flask import current_app

    return (current_app.config.get("ADMIN_REGISTER_INVITE_CODE") or env_str("ADMIN_REGISTER_INVITE_CODE", "") or "").strip()
