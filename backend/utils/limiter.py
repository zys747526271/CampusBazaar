"""接口限流（PRD 5.2）：基于缓存的固定窗口计数，生产用 Redis，本地用进程内缓存。"""
from __future__ import annotations

from flask import request

from backend.constants import Limits
from backend.errors import too_many
from backend.extensions import cache
from backend.utils.security import client_ip, current_identity


def hit(scope: str, subject: str, rule: tuple[int, int], message: str | None = None) -> None:
    """记一次访问；超限抛 429，并带上剩余等待秒数。

    ``rule`` = (允许次数, 窗口秒数)
    """
    limit, window = rule
    if limit <= 0:
        return
    import time

    key = f"rl:{scope}:{subject}"
    record = cache.get(key) or {"n": 0, "exp": 0}
    current = time.time()
    if not record.get("exp") or record["exp"] <= current:
        record = {"n": 0, "exp": current + window}
    record["n"] += 1
    remaining = max(int(record["exp"] - current), 1)
    cache.set(key, record, timeout=window + 1)
    if record["n"] > limit:
        raise too_many(
            message or f"操作过于频繁，请 {remaining} 秒后再试",
            {"retry_after": remaining},
        )


def by_ip(scope: str, rule: tuple[int, int], message: str | None = None) -> None:
    hit(scope, client_ip(), rule, message)


def by_user(scope: str, rule: tuple[int, int], message: str | None = None) -> None:
    typ, identity_id = current_identity()
    subject = f"{typ}:{identity_id}" if identity_id else f"ip:{client_ip()}"
    hit(scope, subject, rule, message)


def by_phone(scope: str, phone: str, rule: tuple[int, int], message: str | None = None) -> None:
    hit(scope, f"{phone}|{client_ip()}", rule, message)


# ---------- 管理员登录锁定：连续失败 N 次锁定 15 分钟 ----------
def admin_lock_key(username: str) -> str:
    return f"admin:lock:{username.lower()}"


def assert_admin_not_locked(username: str) -> None:
    state = cache.get(admin_lock_key(username))
    if not state or not state.get("until"):
        return
    import time

    remaining = int(state.get("until", 0) - time.time())
    if remaining > 0:
        raise too_many(
            f"登录失败次数过多，请 {max(remaining // 60 + 1, 1)} 分钟后再试",
            {"retry_after": remaining},
        )
    # 锁定已到期，清掉计数重新开始
    cache.delete(admin_lock_key(username))


def record_admin_failure(username: str) -> int:
    key = admin_lock_key(username)
    state = cache.get(key) or {"count": 0, "until": 0}
    state["count"] += 1
    if state["count"] >= Limits.ADMIN_LOGIN_MAX_ATTEMPTS:
        import time

        state["until"] = time.time() + Limits.ADMIN_LOGIN_LOCK_MINUTES * 60
        state["count"] = 0
    cache.set(key, state, timeout=Limits.ADMIN_LOGIN_LOCK_MINUTES * 60 + 60)
    return state["count"]


def clear_admin_failure(username: str) -> None:
    cache.delete(admin_lock_key(username))


def client_ip_or_unknown() -> str:
    return client_ip() or request.remote_addr or "-"
