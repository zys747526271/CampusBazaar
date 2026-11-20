"""认证与鉴权（PRD 2.3 / 7.4 / 附录 A 第 2、3 条）。

- 401：没有令牌、令牌过期、令牌被吊销、签名错误
- 403：令牌有效但类型不对（例如用户令牌访问管理接口）、权限不足、账号被封禁
前端只对 401 清理登录态，403 仅提示，因此这里必须严格区分。
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable

import jwt
from flask import current_app, g, request
from werkzeug.security import check_password_hash, generate_password_hash

from backend.errors import forbidden, unauthorized
from backend.extensions import cache


def hash_password(raw: str) -> str:
    return generate_password_hash(raw, method="pbkdf2:sha256:260000")


def verify_password(raw: str, hashed: str) -> bool:
    if not raw or not hashed:
        return False
    try:
        return check_password_hash(hashed, raw)
    except (ValueError, TypeError):
        return False


def create_token(
    subject_id: int | str,
    identity_type: str = "user",
    expires=None,
    extra: dict | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    if expires is None:
        expires = (
            current_app.config["JWT_ADMIN_EXPIRES"]
            if identity_type == "admin"
            else current_app.config["JWT_EXPIRES"]
        )
    payload = {
        "sub": str(subject_id),
        "typ": identity_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires).timestamp()),
        "jti": uuid.uuid4().hex,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, current_app.config["JWT_SECRET_KEY"], algorithm=current_app.config["JWT_ALGORITHM"])


def decode_token(token: str) -> dict:
    if not token:
        raise unauthorized("请先登录")
    try:
        payload = jwt.decode(
            token,
            current_app.config["JWT_SECRET_KEY"],
            algorithms=[current_app.config["JWT_ALGORITHM"]],
        )
    except jwt.ExpiredSignatureError as exc:
        raise unauthorized("登录已过期，请重新登录") from exc
    except jwt.InvalidTokenError as exc:
        raise unauthorized("登录状态无效，请重新登录") from exc
    if cache.get(f"token:revoked:{payload.get('jti')}"):
        raise unauthorized("登录状态已失效，请重新登录")
    return payload


def bearer_token() -> str:
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header[7:].strip()
    return ""


def revoke_token(payload: dict) -> None:
    jti = payload.get("jti")
    exp = payload.get("exp")
    if not jti or not exp:
        return
    ttl = max(int(exp - datetime.now(timezone.utc).timestamp()), 60)
    cache.set(f"token:revoked:{jti}", 1, timeout=ttl)


def _authenticate() -> dict:
    payload = decode_token(bearer_token())
    try:
        identity_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise unauthorized("登录状态无效，请重新登录") from exc
    g.token_payload = payload
    g.identity_type = payload.get("typ")
    g.identity_id = identity_id
    return payload


def current_identity() -> tuple[str | None, int | None]:
    return getattr(g, "identity_type", None), getattr(g, "identity_id", None)


def current_user(required: bool = True):
    """取当前登录用户；未登录时返回 None（required=True 时抛 401）。

    缓存键带上身份标识，避免同一 app context 内多次请求复用 g 时串号
    （测试客户端与长连接场景会复用 app context）。
    """
    from backend.models import User

    typ, uid = current_identity()
    cache_key = f"_cached_user_{typ}_{uid}"
    cached = getattr(g, cache_key, None)
    if cached is not None:
        return cached
    if typ != "user" or not uid:
        if required:
            raise unauthorized("请先登录")
        return None
    user = User.query.filter(User.id == uid, User.is_deleted.is_(False)).first()
    if user is None:
        raise unauthorized("账号不存在或已注销")
    if user.is_banned:
        raise forbidden(user.ban_reason or "账号已被封禁，请联系管理员")
    setattr(g, cache_key, user)
    return user


def current_admin(required: bool = True):
    from backend.models import Admin

    typ, aid = current_identity()
    cache_key = f"_cached_admin_{typ}_{aid}"
    cached = getattr(g, cache_key, None)
    if cached is not None:
        return cached
    if typ != "admin" or not aid:
        if required:
            raise unauthorized("请先登录管理后台")
        return None
    admin = Admin.query.filter(Admin.id == aid).first()
    if admin is None or not admin.is_active:
        raise forbidden("管理员账号不可用")
    setattr(g, cache_key, admin)
    return admin


def token_required(view: Callable) -> Callable:
    @wraps(view)
    def wrapper(*args, **kwargs):
        _authenticate()
        return view(*args, **kwargs)

    return wrapper


def login_required(view: Callable) -> Callable:
    """仅普通用户（买家/卖家）。管理员令牌访问用户接口返回 403。"""

    @wraps(view)
    def wrapper(*args, **kwargs):
        payload = _authenticate()
        if payload.get("typ") != "user":
            raise forbidden("该接口仅对普通用户开放")
        current_user()
        return view(*args, **kwargs)

    return wrapper


def seller_required(view: Callable) -> Callable:
    @wraps(view)
    def wrapper(*args, **kwargs):
        payload = _authenticate()
        if payload.get("typ") != "user":
            raise forbidden("该接口仅对卖家开放")
        user = current_user()
        if not user.is_seller:
            raise forbidden("请先在卖家中心开通卖家身份")
        return view(*args, **kwargs)

    return wrapper


def admin_required(view: Callable) -> Callable:
    @wraps(view)
    def wrapper(*args, **kwargs):
        payload = _authenticate()
        if payload.get("typ") != "admin":
            raise forbidden("需要管理员权限")
        current_admin()
        return view(*args, **kwargs)

    return wrapper


def optional_user():
    """公开接口里识别"谁在看"，无效令牌按游客处理，不报错。"""
    typ, uid = current_identity()
    if typ == "user" and uid:
        try:
            return current_user(required=False)
        except Exception:  # noqa: BLE001 - 封禁用户在公开接口按游客处理
            return None
    if not bearer_token():
        return None
    try:
        payload = decode_token(bearer_token())
    except Exception:  # noqa: BLE001 - 公开接口忽略无效令牌
        return None
    if payload.get("typ") != "user":
        return None
    g.identity_type = "user"
    g.identity_id = int(payload["sub"])
    g.token_payload = payload
    try:
        return current_user(required=False)
    except Exception:  # noqa: BLE001
        return None


def client_ip() -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "-"


def public_user(user) -> dict[str, Any]:
    """对外可见的用户信息（不含手机号全量，仅脱敏）。"""
    from backend.utils.common import iso

    return {
        "id": user.id,
        "nickname": user.nickname,
        "avatar_url": user.avatar_url or "",
        "is_seller": user.is_seller,
        "campus": user.campus or "",
        "created_at": iso(user.created_at),
    }
