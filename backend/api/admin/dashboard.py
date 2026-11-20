"""后台概览与运维任务。"""
from __future__ import annotations

from backend.api.admin import bp
from backend.services import jobs, stats
from backend.utils.response import ok
from backend.utils.security import admin_required, current_admin


@bp.get("/stats")
@admin_required
def overview():
    return ok(stats.admin_overview())


@bp.post("/jobs/run")
@admin_required
def run_jobs():
    """手动触发一次定时任务，便于验收超时取消/自动确认收货（PRD FR-ORDR-04）。"""
    result = jobs.run_once()
    return ok({**result, "operator": current_admin().username}, "任务已执行")
