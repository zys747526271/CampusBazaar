import os

class MySQLConfig:
    """数据库和全局配置类"""

    # Flask 配置（已脱敏：原项目此处为明文弱密钥，发布前改用环境变量）
    DEBUG = False
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-only-change-me')

    # 数据库配置（已脱敏：口令不再写入源码）
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'mysql+pymysql://root@127.0.0.1:3306/mall')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    # 数据库连接池配置
    SQLALCHEMY_POOL_SIZE = 100
    SQLALCHEMY_MAX_OVERFLOW = 50
    SQLALCHEMY_POOL_RECYCLE = 3600

    # Redis 配置
    REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)
    REDIS_DB = int(os.getenv('REDIS_DB', 0))
    REDIS_MAX_CONNECTIONS = 500

# 接口白名单
WHITE_NAME_LIST = [
    "/api/login",
    "/api/regist",
    "/api/goods/type",
    "/api/by/tag/goods",
    "/api/admin/add"
]

# Gunicorn 配置
GUNICORN_CONFIG = {
    "workers": 8,
    "threads": 200,
    "bind": "0.0.0.0:5000",
    "timeout": 120,
    "worker_class": "gevent",
    "max_requests": 1000,
    "max_requests_jitter": 50,
}

# 日志配置
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
        "file": {
            "level": "ERROR",
            "class": "logging.FileHandler",
            "filename": "error.log",
            "formatter": "standard",
        },
    },
    "loggers": {
        "": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": True,
        },
    },
}