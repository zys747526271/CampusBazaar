"""应用配置（全部敏感项均从环境变量读取，请勿在代码中写入明文密钥）。

启动前请复制项目根目录的 .env.example 为 .env 并按需修改，
或直接通过系统环境变量注入以下键：
  SECRET_KEY, JWT_SECRET_KEY, ENCRYPTION_KEY, DATABASE_URL, REDIS_URL
"""
import os
from datetime import timedelta


class Config:
    # ---------- 基础安全配置（必须通过环境变量提供） ----------
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-only-change-me'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'dev-only-change-me-jwt'
    # Fernet 对称密钥，用于身份证等敏感字段加解密（32 字节 urlsafe base64）
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY') or None

    DEBUG = False

    # ---------- 数据库 ----------
    # 格式示例：mysql+pymysql://user:password@host:3306/campus_bazaar
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 'mysql+pymysql://root@localhost:3306/campus_bazaar'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ---------- 缓存 / Redis ----------
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    CACHE_TYPE = 'RedisCache'
    CACHE_REDIS_URL = REDIS_URL

    # ---------- JWT ----------
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    # ---------- 文件上传 ----------
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

    # ---------- 分页 ----------
    DEFAULT_PAGE_SIZE = 10
    MAX_PAGE_SIZE = 100


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False

    @classmethod
    def validate(cls):
        """部署前调用：生产环境必须显式提供关键密钥。"""
        missing = [k for k in ('SECRET_KEY', 'JWT_SECRET_KEY', 'ENCRYPTION_KEY', 'DATABASE_URL')
                   if not os.environ.get(k)]
        if missing:
            raise RuntimeError('生产环境缺少必需环境变量: ' + ', '.join(missing))


config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}
