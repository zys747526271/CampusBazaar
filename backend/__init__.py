"""应用工厂：把配置、扩展、日志、蓝图、错误处理装配成 Flask app。"""
from __future__ import annotations

import sqlite3  # noqa: F401  (供测试与运维脚本判断本地库类型)
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, request, send_from_directory
from flask_cors import CORS
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from werkzeug.exceptions import HTTPException

from backend.config import get_config
from backend.errors import ApiError, ErrorCode, not_found
from backend.extensions import cache, db
from backend.utils.logging import install_request_hooks, setup_logging
from backend.utils.response import respond

__version__ = "2.2.0"


def create_app(config_object=None, overrides: dict | None = None) -> Flask:
    app = Flask(__name__, static_folder="static", static_url_path="/static")

    config_object = config_object or get_config()
    if hasattr(config_object, "validate"):
        config_object.validate()
    app.config.from_object(config_object)
    # 启动参数覆盖（如 --serve-dist），必须在注册路由前生效
    if overrides:
        app.config.update(overrides)
    # 中文直接输出，避免前端看到 \uXXXX；字段顺序保持稳定便于排查
    app.json.ensure_ascii = False
    app.json.sort_keys = False

    # 关闭严格斜杠重定向：308 会丢失 Authorization 头（附录 A 第 5 条）
    app.url_map.strict_slashes = False

    _ensure_sqlite_dir(app)
    db.init_app(app)
    cache.init_app(app)
    setup_logging(app)
    install_request_hooks(app)

    if app.config.get("CORS_ORIGINS"):
        CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}}, supports_credentials=False)

    _register_error_handlers(app)
    _register_blueprints(app)
    _register_ops_routes(app)
    _register_frontend(app)
    return app


def _ensure_sqlite_dir(app: Flask) -> None:
    """SQLite 文件库：确保所在目录存在，避免首次启动因缺目录失败。"""
    uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if not uri.startswith("sqlite:///") or ":memory:" in uri:
        return
    path = Path(uri.replace("sqlite:///", "", 1))
    if path.parent and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ApiError)
    def _api_error(exc: ApiError):
        return respond(exc.details, exc.message, exc.code, exc.status)

    @app.errorhandler(HTTPException)
    def _http_error(exc: HTTPException):
        code_map = {
            400: ErrorCode.BAD_REQUEST,
            401: ErrorCode.UNAUTHORIZED,
            403: ErrorCode.FORBIDDEN,
            404: ErrorCode.NOT_FOUND,
            405: ErrorCode.BAD_REQUEST,
            413: ErrorCode.BAD_REQUEST,
            429: ErrorCode.TOO_MANY_REQUESTS,
            503: ErrorCode.SERVICE_UNAVAILABLE,
        }
        messages = {
            404: "接口或资源不存在",
            405: "请求方法不被允许",
            413: "请求体过大",
        }
        code = code_map.get(exc.code or 500, ErrorCode.BAD_REQUEST)
        message = messages.get(exc.code or 0, exc.description or "请求有误")
        if request.path.startswith("/api"):
            return respond(None, message, code, exc.code or 400)
        return exc

    @app.errorhandler(IntegrityError)
    def _integrity_error(exc: IntegrityError):
        db.session.rollback()
        return respond(None, "数据冲突：记录已存在或违反唯一约束", ErrorCode.CONFLICT, 409)

    @app.errorhandler(SQLAlchemyError)
    def _db_error(exc: SQLAlchemyError):
        db.session.rollback()
        app.logger.exception("database error: %s", exc)
        return respond(None, "数据库暂时不可用，请稍后重试", ErrorCode.INTERNAL_ERROR, 500)

    @app.errorhandler(Exception)
    def _unhandled(exc: Exception):
        db.session.rollback()
        if isinstance(exc, HTTPException):
            return _http_error(exc)
        app.logger.exception("unhandled error: %s", exc)
        return respond(None, "服务器开小差了，请稍后重试", ErrorCode.INTERNAL_ERROR, 500)


def _register_blueprints(app: Flask) -> None:
    from backend.api import register_blueprints

    register_blueprints(app)


def _register_ops_routes(app: Flask) -> None:
    @app.get("/api/health")
    def health():
        db_ok, cache_ok = True, True
        try:
            db.session.execute(db.text("SELECT 1"))
        except Exception:  # noqa: BLE001
            db_ok = False
        try:
            cache.set("health:ping", "1", timeout=5)
            cache_ok = cache.get("health:ping") == "1"
        except Exception:  # noqa: BLE001
            cache_ok = False
        status = "ok" if db_ok and cache_ok else "degraded"
        return respond(
            {
                "status": status,
                "db": db_ok,
                "cache": cache_ok,
                "env": app.config.get("ENV"),
                "version": __version__,
            },
            "服务正常" if status == "ok" else "部分依赖不可用",
        )

    @app.get("/dev/captchas")
    def dev_captchas():
        """本地演示用验证码台账；生产模式一律 404（PRD FR-AUTH-03 / AC-12）。"""
        if app.config.get("CAPTCHA_MODE") == "prod":
            raise not_found("页面不存在")
        from backend.utils.captcha import dev_ledger

        rows = "".join(
            f"<tr><td>{item['phone']}</td><td>{item['scene']}</td>"
            f"<td class='code'>{item['code']}</td>"
            f"<td>{datetime.fromtimestamp(item['created_at'], timezone.utc).astimezone().strftime('%H:%M:%S')}</td></tr>"
            for item in dev_ledger()
        ) or "<tr><td colspan='4' class='muted'>暂无验证码，先去注册页获取一个</td></tr>"
        html = f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<title>本地验证码台账 · CampusBazaar</title>
<style>
body{{font-family:-apple-system,"Segoe UI",Roboto,"Microsoft YaHei",sans-serif;background:#f6f7f9;margin:0;padding:40px;color:#1f2329}}
.wrap{{max-width:760px;margin:0 auto;background:#fff;border-radius:12px;padding:28px 32px;box-shadow:0 8px 30px rgba(0,0,0,.06)}}
h1{{font-size:20px;margin:0 0 6px}}p.muted,td.muted{{color:#8a9099;font-size:13px}}
table{{width:100%;border-collapse:collapse;margin-top:18px;font-size:14px}}
th,td{{text-align:left;padding:10px 8px;border-bottom:1px solid #eef0f3}}
th{{color:#6b7280;font-weight:500;font-size:12px;text-transform:uppercase;letter-spacing:.04em}}
.code{{font-family:ui-monospace,Consolas,monospace;font-size:18px;color:#ff5000;letter-spacing:2px}}
.tag{{display:inline-block;background:#fff3ec;color:#ff5000;border-radius:999px;padding:2px 10px;font-size:12px}}
</style></head><body><div class="wrap">
<span class="tag">仅本地 / 演示环境</span>
<h1>短信验证码台账</h1>
<p class="muted">生产环境（CAPTCHA_MODE=prod）访问本页返回 404。刷新页面查看最新验证码。</p>
<table><thead><tr><th>手机号</th><th>场景</th><th>验证码</th><th>生成时间</th></tr></thead>
<tbody>{rows}</tbody></table></div></body></html>"""
        return html, 200, {"Content-Type": "text/html; charset=utf-8"}

    @app.get("/favicon.ico")
    def favicon():
        return "", 204


def _register_frontend(app: Flask) -> None:
    """可选：由 Flask 托管前端构建产物，实现"一条命令演示"。"""
    dist: Path = app.config["FRONTEND_DIST"]
    if not app.config.get("SERVE_FRONTEND") or not (dist / "index.html").exists():
        return

    @app.get("/assets/<path:filename>")
    def _dist_assets(filename: str):
        return send_from_directory(dist / "assets", filename)

    @app.get("/", defaults={"path": ""})
    @app.get("/<path:path>")
    def _spa(path: str):
        if path.startswith("api/") or path.startswith("static/") or path.startswith("dev/"):
            raise not_found("接口或资源不存在")
        candidate = dist / path
        if path and candidate.is_file():
            return send_from_directory(dist, path)
        return send_from_directory(dist, "index.html")


def _sqlite_path(app: Flask) -> str | None:
    """运维辅助：返回 SQLite 文件路径（内存库返回 None）。"""
    uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if not uri.startswith("sqlite:///"):
        return None
    return uri.replace("sqlite:///", "", 1) or None


__all__ = ["create_app", "__version__"]
