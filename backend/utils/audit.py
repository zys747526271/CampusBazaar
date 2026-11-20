"""管理操作审计（PRD FR-ADMN-09 / 3.5）：所有治理动作同时落 audit_logs 与 security 日志。"""
from __future__ import annotations

from flask import has_request_context

from backend.extensions import db
from backend.utils.logging import security_log
from backend.utils.security import client_ip


def record(action: str, target_type: str = "", target_id: int | str | None = None, detail: str = "") -> None:
    """记录一次管理员操作；不提交事务，由调用方统一提交。"""
    from backend.models import AuditLog
    from backend.utils.security import current_admin

    admin = current_admin(required=False)
    if admin is None:
        return
    ip = client_ip() if has_request_context() else "-"
    db.session.add(
        AuditLog(
            admin_id=admin.id,
            admin_name=admin.username,
            action=action,
            target_type=target_type,
            target_id=str(target_id) if target_id is not None else "",
            detail=detail[:500],
            ip=ip,
        )
    )
    security_log("admin." + action, detail, admin=admin.username, target=f"{target_type}:{target_id}", ip=ip)
