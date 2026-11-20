"""写操作幂等（PRD 7.6）：同一 ``Idempotency-Key`` 在 10 分钟内重复提交，返回首次结果。"""
from __future__ import annotations

import hashlib
from functools import wraps

from flask import request

from backend.extensions import cache
from backend.utils.security import current_identity

WINDOW_SECONDS = 600


def _key(scope: str) -> str | None:
    raw = request.headers.get("Idempotency-Key", "").strip()
    if not raw:
        return None
    typ, identity_id = current_identity()
    digest = hashlib.sha256(f"{scope}|{typ}:{identity_id}|{request.path}|{raw}".encode()).hexdigest()[:40]
    return f"idem:{digest}"


def idempotent(scope: str):
    """装饰器：缓存首次成功响应，重放时带上 ``X-Idempotent-Replay: true``。"""

    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            key = _key(scope)
            if not key:
                return view(*args, **kwargs)
            cached = cache.get(key)
            if cached is not None:
                from backend.utils.response import respond

                snapshot = dict(cached)
                status = snapshot.pop("_status", 200)
                response = respond(
                    snapshot.get("data"),
                    snapshot.get("message", "操作成功"),
                    snapshot.get("code", "OK"),
                    status,
                )
                response.headers["X-Idempotent-Replay"] = "true"
                return response
            response = view(*args, **kwargs)
            status = getattr(response, "status_code", 200)
            if 200 <= status < 300:
                try:
                    body = response.get_json()
                except Exception:  # noqa: BLE001 - 非 JSON 响应不需要幂等快照
                    body = None
                if isinstance(body, dict):
                    snapshot = dict(body)
                    snapshot["_status"] = status
                    cache.set(key, snapshot, timeout=WINDOW_SECONDS)
            return response

        return wrapper

    return decorator
