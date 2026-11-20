"""后台定时任务：超时取消、自动确认收货、售罄下架（PRD FR-ORDR-04）。

本地用守护线程跑；多实例部署时改为外部调度（cron / Celery beat），
业务函数保持无状态，可直接复用。
"""
from __future__ import annotations

import logging
import threading

from flask import Flask

from backend.extensions import db
from backend.services import orders as order_service

logger = logging.getLogger("campus.app")
_scheduler_started = False
_lock = threading.Lock()


def run_once() -> dict:
    expired = order_service.expire_unpaid_orders()
    confirmed = order_service.auto_confirm_shipped()
    sold_out = order_service.mark_sold_out_products()
    result = {"expired_orders": expired, "auto_confirmed": confirmed, "sold_out": sold_out}
    if any(result.values()):
        logger.info("scheduler run: %s", result, extra={"fields": result})
    return result


class _Worker(threading.Thread):
    def __init__(self, app: Flask, interval: int) -> None:
        super().__init__(name="campus-scheduler", daemon=True)
        self.app = app
        self.interval = max(interval, 15)
        self._stop_event = threading.Event()

    def run(self) -> None:  # pragma: no cover - 线程逻辑不参与单测
        while not self._stop_event.wait(self.interval):
            try:
                with self.app.app_context():
                    run_once()
            except Exception as exc:  # noqa: BLE001 - 定时任务不能因单次异常退出
                logger.warning("scheduler error: %s", exc)
                try:
                    db.session.rollback()
                except Exception:  # noqa: BLE001
                    pass

    def stop(self) -> None:
        self._stop_event.set()


def start_scheduler(app: Flask) -> _Worker | None:  # pragma: no cover
    global _scheduler_started
    if not app.config.get("ENABLE_SCHEDULER"):
        return None
    with _lock:
        if _scheduler_started:
            return None
        _scheduler_started = True
    worker = _Worker(app, app.config.get("SCHEDULER_INTERVAL_SECONDS", 60))
    worker.start()
    logger.info("scheduler started", extra={"fields": {"interval": worker.interval}})
    return worker
