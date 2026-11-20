"""应用配置：四套环境（local / testing / staging / production）。

核心原则（PRD 9.1）：环境差异只通过 ``CAMPUS_CONFIG`` + 环境变量表达，
同一份代码跑通四套环境，禁止维护 ``app_local.py`` 之类的分叉。
"""
from __future__ import annotations

import os
import secrets
from datetime import timedelta
from pathlib import Path

try:  # 本地开发从 .env 读配置；生产由部署平台注入环境变量
    from dotenv import load_dotenv

    ROOT_DIR = Path(__file__).resolve().parent.parent
    load_dotenv(ROOT_DIR / ".env")
except ImportError:  # pragma: no cover - 未安装 python-dotenv 时降级
    ROOT_DIR = Path(__file__).resolve().parent.parent

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = ROOT_DIR / "instance"


def env_str(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    return value.strip() if value is not None and value.strip() != "" else default


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, ""))
    except (TypeError, ValueError):
        return default


def _local_secret(name: str) -> str:
    """本地/测试环境自动生成并持久化密钥，避免重启后登录态全部失效。"""
    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    secret_file = INSTANCE_DIR / ".dev-secrets"
    data: dict[str, str] = {}
    if secret_file.exists():
        for line in secret_file.read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, _, value = line.partition("=")
                data[key.strip()] = value.strip()
    if data.get(name):
        return data[name]
    data[name] = secrets.token_urlsafe(48)
    secret_file.write_text(
        "\n".join(f"{k}={v}" for k, v in data.items()), encoding="utf-8"
    )
    return data[name]


class BaseConfig:
    ENV = "base"
    DEBUG = False
    TESTING = False
    PROPAGATE_EXCEPTIONS = False

    # ---------- 安全 ----------
    # 生产必须由环境变量注入；本地由子类补默认值（见 LocalConfig）。
    SECRET_KEY = env_str("SECRET_KEY")
    JWT_SECRET_KEY = env_str("JWT_SECRET_KEY")
    JWT_ALGORITHM = "HS256"
    #: PRD FR-AUTH-05：用户令牌有效期 7 天
    JWT_EXPIRES = timedelta(days=env_int("JWT_EXPIRES_DAYS", 7))
    #: 管理员令牌更短，降低泄露风险
    JWT_ADMIN_EXPIRES = timedelta(hours=env_int("JWT_ADMIN_EXPIRES_HOURS", 12))

    # ---------- 数据库 ----------
    SQLALCHEMY_DATABASE_URI = env_str("DATABASE_URL", "sqlite:///:memory:")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS: dict = {"pool_pre_ping": True}

    # ---------- 缓存 ----------
    CACHE_TYPE = "SimpleCache"
    CACHE_DEFAULT_TIMEOUT = 300
    REDIS_URL = env_str("REDIS_URL")
    CACHE_REDIS_URL = REDIS_URL

    # ---------- 业务开关（禁止硬编码分支）----------
    #: 本地发布即通过；生产必须人工审核
    AUTO_APPROVE_PRODUCT = env_bool("AUTO_APPROVE_PRODUCT", True)
    #: dev 模式验证码回显；prod 走短信网关
    CAPTCHA_MODE = env_str("CAPTCHA_MODE", "dev")
    SMS_GATEWAY_ENABLED = env_bool("SMS_GATEWAY_ENABLED", False)
    #: 演示数据
    SEED_DEMO_DATA = env_bool("SEED_DEMO_DATA", False)
    #: 管理员自助注册
    ADMIN_REGISTRATION_ENABLED = env_bool("ADMIN_REGISTRATION_ENABLED", True)
    ADMIN_REGISTER_INVITE_CODE = env_str("ADMIN_REGISTER_INVITE_CODE", "")
    #: 后台定时任务（超时取消 / 自动确认收货）
    ENABLE_SCHEDULER = env_bool("ENABLE_SCHEDULER", True)
    SCHEDULER_INTERVAL_SECONDS = env_int("SCHEDULER_INTERVAL_SECONDS", 60)
    #: 演示充值（无第三方支付通道时的余额入金开关，生产必须关闭）
    ENABLE_DEMO_RECHARGE = env_bool("ENABLE_DEMO_RECHARGE", False)
    #: 同一 IP 每 5 分钟允许的注册次数（生产 5 次；本地/演示环境放宽便于反复验收）
    RATE_REGISTER_PER_5MIN = env_int("RATE_REGISTER_PER_5MIN", 5)

    # ---------- 上传 ----------
    UPLOAD_ROOT = BASE_DIR / "static" / "uploads"
    MAX_CONTENT_LENGTH = 12 * 1024 * 1024  # 请求体上限，单图 5MB 由业务层校验

    # ---------- 日志 ----------
    LOG_TO_FILE = True
    LOG_DIR = ROOT_DIR / "logs"
    LOG_LEVEL = env_str("LOG_LEVEL", "INFO")
    LOG_FORMAT = env_str("LOG_FORMAT", "text")
    LOG_RETENTION_DAYS = env_int("LOG_RETENTION_DAYS", 14)
    LOG_MAX_BYTES = 50 * 1024 * 1024

    # ---------- 前端 ----------
    #: 允许跨域来源（本地走 Vite 代理，通常不需要）
    CORS_ORIGINS = [o.strip() for o in (env_str("CORS_ORIGINS", "") or "").split(",") if o.strip()]
    #: 是否由 Flask 托管前端构建产物（单命令演示用）
    SERVE_FRONTEND = env_bool("SERVE_FRONTEND", False)
    FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"

    JSON_AS_ASCII = False
    JSON_SORT_KEYS = False


class LocalConfig(BaseConfig):
    """本地开发 / 演示：SQLite 文件库 + 进程内缓存，零外部依赖。"""

    ENV = "local"
    DEBUG = True
    SECRET_KEY = env_str("SECRET_KEY") or _local_secret("SECRET_KEY")
    JWT_SECRET_KEY = env_str("JWT_SECRET_KEY") or _local_secret("JWT_SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = env_str(
        "LOCAL_DATABASE_URL", f"sqlite:///{(INSTANCE_DIR / 'campus.db').as_posix()}"
    )
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "connect_args": {"check_same_thread": False}}
    CACHE_TYPE = "SimpleCache"
    CAPTCHA_MODE = "dev"
    AUTO_APPROVE_PRODUCT = env_bool("AUTO_APPROVE_PRODUCT", True)
    SEED_DEMO_DATA = env_bool("SEED_DEMO_DATA", True)
    ADMIN_REGISTRATION_ENABLED = env_bool("ADMIN_REGISTRATION_ENABLED", True)
    ENABLE_DEMO_RECHARGE = env_bool("ENABLE_DEMO_RECHARGE", True)
    RATE_REGISTER_PER_5MIN = env_int("RATE_REGISTER_PER_5MIN", 50)
    LOG_LEVEL = env_str("LOG_LEVEL", "DEBUG")


class TestingConfig(BaseConfig):
    """自动化测试：SQLite 内存库，关闭文件日志与调度线程。"""

    ENV = "testing"
    TESTING = True
    DEBUG = False
    SECRET_KEY = "testing-secret-key-not-for-production"
    JWT_SECRET_KEY = "testing-jwt-key-not-for-production"
    SQLALCHEMY_DATABASE_URI = env_str("TEST_DATABASE_URL", "sqlite:///:memory:")
    SQLALCHEMY_ENGINE_OPTIONS = {"connect_args": {"check_same_thread": False}}
    CACHE_TYPE = "SimpleCache"
    CAPTCHA_MODE = "dev"
    AUTO_APPROVE_PRODUCT = True
    SEED_DEMO_DATA = False
    ADMIN_REGISTRATION_ENABLED = True
    ENABLE_DEMO_RECHARGE = True
    RATE_REGISTER_PER_5MIN = env_int("RATE_REGISTER_PER_5MIN", 50)
    ENABLE_SCHEDULER = False
    LOG_TO_FILE = False
    SERVE_FRONTEND = False


class StagingConfig(BaseConfig):
    """预发：MySQL + Redis，密钥必须显式注入。"""

    ENV = "staging"
    SQLALCHEMY_DATABASE_URI = env_str("DATABASE_URL", "")
    CACHE_TYPE = "RedisCache"
    CAPTCHA_MODE = "prod"
    AUTO_APPROVE_PRODUCT = False
    SEED_DEMO_DATA = env_bool("SEED_DEMO_DATA", True)
    ADMIN_REGISTRATION_ENABLED = env_bool("ADMIN_REGISTRATION_ENABLED", True)
    SERVE_FRONTEND = env_bool("SERVE_FRONTEND", True)


class ProductionConfig(BaseConfig):
    """生产：MySQL 主从 + Redis + 短信网关，缺密钥直接拒绝启动。"""

    ENV = "production"
    SQLALCHEMY_DATABASE_URI = env_str("DATABASE_URL", "")
    CACHE_TYPE = "RedisCache"
    CAPTCHA_MODE = "prod"
    SMS_GATEWAY_ENABLED = env_bool("SMS_GATEWAY_ENABLED", True)
    AUTO_APPROVE_PRODUCT = False
    SEED_DEMO_DATA = False
    ADMIN_REGISTRATION_ENABLED = env_bool("ADMIN_REGISTRATION_ENABLED", False)
    LOG_FORMAT = env_str("LOG_FORMAT", "json")
    SERVE_FRONTEND = env_bool("SERVE_FRONTEND", True)

    @classmethod
    def validate(cls) -> None:
        missing = []
        for key in ("SECRET_KEY", "JWT_SECRET_KEY", "DATABASE_URL"):
            if not os.environ.get(key):
                missing.append(key)
        if missing:
            raise RuntimeError(
                "生产环境缺少必需环境变量：" + "、".join(missing) + "（禁止使用默认密钥启动）"
            )
        if not os.environ.get("REDIS_URL"):
            raise RuntimeError("生产环境缺少必需环境变量：REDIS_URL")


CONFIG_MAP = {
    "local": LocalConfig,
    "testing": TestingConfig,
    "staging": StagingConfig,
    "production": ProductionConfig,
}


def get_config(name: str | None = None):
    """按 ``CAMPUS_CONFIG`` 返回配置类；未知值直接报错，避免静默降级到开发配置。"""
    key = (name or os.environ.get("CAMPUS_CONFIG") or "local").strip().lower()
    if key not in CONFIG_MAP:
        raise RuntimeError(f"未知的 CAMPUS_CONFIG={key}，可选值：{', '.join(CONFIG_MAP)}")
    return CONFIG_MAP[key]
