"""分类日志与请求追踪（PRD 4.13 / 10）。

四类日志各自落盘、按天滚动且单文件不超过 50MB：
``logs/access.log`` ``logs/error.log`` ``logs/security.log`` ``logs/app.log``
每个请求生成 ``request_id``，通过响应头 ``X-Request-Id`` 回传，便于全链路串查。
"""
from __future__ import annotations

import json
import logging
import os
import time
import uuid
from logging.handlers import TimedRotatingFileHandler
from typing import Any

from flask import Flask, g, request

from backend.utils.security import client_ip, current_identity

ACCESS = "campus.access"
ERROR = "campus.error"
SECURITY = "campus.security"
APP = "campus.app"

_LOGGERS = {ACCESS: "access.log", ERROR: "error.log", SECURITY: "security.log", APP: "app.log"}
_SENSITIVE_KEYS = {"password", "old_password", "new_password", "token", "authorization", "code"}


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        record.request_id = getattr(g, "request_id", "-") if _has_app_context() else "-"
        return True


def _has_app_context() -> bool:
    from flask import has_app_context

    return has_app_context()


class DailySizeRotatingHandler(TimedRotatingFileHandler):
    """按天滚动，同时限制单文件大小（PRD FR-OPS-02）。"""

    def __init__(self, filename: str, max_bytes: int = 50 * 1024 * 1024, **kwargs):
        super().__init__(filename, when="midnight", backupCount=kwargs.pop("backup_count", 14), encoding="utf-8", delay=True)
        self.max_bytes = max_bytes

    def shouldRollover(self, record: logging.LogRecord) -> bool:  # noqa: N802
        if super().shouldRollover(record):
            return True
        if self.max_bytes <= 0:
            return False
        if self.stream is None:
            self.stream = self._open()
        self.stream.seek(0, os.SEEK_END)
        return self.stream.tell() + len(self.format(record)) > self.max_bytes


class TextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = (
            f"{self.formatTime(record, '%Y-%m-%d %H:%M:%S')} "
            f"{record.levelname:<7} [{getattr(record, 'request_id', '-')}] {record.getMessage()}"
        )
        if record.exc_info:
            base += "\n" + self.formatException(record.exc_info)
        extras = getattr(record, "fields", None)
        if extras:
            base += " " + json.dumps(extras, ensure_ascii=False, default=str)
        return base


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "message": record.getMessage(),
        }
        payload.update(getattr(record, "fields", {}) or {})
        if record.exc_info:
            payload["error"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def _sanitize(fields: dict) -> dict:
    return {k: ("***" if k.lower() in _SENSITIVE_KEYS else v) for k, v in fields.items()}


def setup_logging(app: Flask) -> None:
    level = getattr(logging, str(app.config.get("LOG_LEVEL", "INFO")).upper(), logging.INFO)
    fmt_cls = JsonFormatter if app.config.get("LOG_FORMAT") == "json" else TextFormatter

    for name, filename in _LOGGERS.items():
        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.propagate = False
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
        if app.config.get("LOG_TO_FILE"):
            log_dir = app.config["LOG_DIR"]
            log_dir.mkdir(parents=True, exist_ok=True)
            handler = DailySizeRotatingHandler(
                str(log_dir / filename),
                max_bytes=app.config.get("LOG_MAX_BYTES", 50 * 1024 * 1024),
                backup_count=app.config.get("LOG_RETENTION_DAYS", 14),
            )
            handler.setFormatter(fmt_cls())
            handler.addFilter(RequestIdFilter())
            logger.addHandler(handler)
        else:
            logger.addHandler(logging.NullHandler())

    # Werkzeug 自带访问日志与我们的 access 日志重复，降级到 WARNING
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def _log(logger_name: str, message: str, level: int = logging.INFO, **fields) -> None:
    logger = logging.getLogger(logger_name)
    logger.log(level, message, extra={"fields": _sanitize(fields)})


def app_log(event: str, message: str = "", level: int = logging.INFO, **fields) -> None:
    _log(APP, f"{event}{(' ' + message) if message else ''}", level, **fields)


def security_log(event: str, message: str = "", level: int = logging.WARNING, **fields) -> None:
    _log(SECURITY, f"{event}{(' ' + message) if message else ''}", level, **fields)


def error_log(message: str, level: int = logging.ERROR, **fields) -> None:
    _log(ERROR, message, level, **fields)


def access_log(message: str, level: int = logging.INFO, **fields) -> None:
    _log(ACCESS, message, level, **fields)


def install_request_hooks(app: Flask) -> None:
    @app.before_request
    def _start_timer():  # noqa: ANN202
        g.request_id = (request.headers.get("X-Request-Id") or uuid.uuid4().hex)[:32]
        g.request_started_at = time.perf_counter()

    @app.after_request
    def _log_request(response):  # noqa: ANN001, ANN202
        duration_ms = round((time.perf_counter() - getattr(g, "request_started_at", time.perf_counter())) * 1000, 2)
        typ, identity_id = current_identity()
        fields = {
            "method": request.method,
            "path": request.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
            "ip": client_ip(),
            "identity": f"{typ}:{identity_id}" if typ else "guest",
        }
        level = logging.INFO
        logger_name = ACCESS
        if response.status_code >= 500:
            level, logger_name = logging.ERROR, ERROR
        elif response.status_code == 401 or response.status_code == 403:
            logger_name = SECURITY
            level = logging.WARNING
        _log(logger_name, "request", level, **fields)
        response.headers["X-Request-Id"] = getattr(g, "request_id", "")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and response.status_code < 400:
            app_log("write", f"{request.method} {request.path}", **fields)
        return response

    @app.teardown_request
    def _log_exception(exc):  # noqa: ANN001, ANN202
        if exc is not None:
            error_log(f"unhandled exception on {request.method} {request.path}: {exc!r}", exc_info=exc)
