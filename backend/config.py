"""应用配置（全部敏感项均从环境变量读取，请勿在代码中写入明文密钥）。

启动前请复制项目根目录的 .env.example 为 .env 并按需修改，
或直接通过系统环境变量注入以下键：
  SECRET_KEY, JWT_SECRET_KEY, ENCRYPTION_KEY, DATABASE_URL, REDIS_URL

运行模式由 CAMPUS_CONFIG 决定：
  local/development/testing —— 本地开发/演示/测试（验证码走 dev 模式，后端可见）
  production              —— 生产（验证码走真实网关，需显式密钥，管理员注册默认关闭）
"""
import os
from datetime import timedelta

# 自动加载项目根目录的 .env（若存在），便于本地开发/测试；环境变量优先。
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
except ImportError:
    pass  # 未安装 python-dotenv 时静默跳过，仍支持系统环境变量


def _env_bool(name, default=False):
    """读取布尔型环境变量，未设置时返回 default。"""
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in ('1', 'true', 'yes', 'on')


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

    # ---------- 验证码（测试/生产分离） ----------
    # CAPTCHA_MODE=dev  : 测试模式，生成后在后端控制台打印，并随接口返回 dev_code 供测试填写
    # CAPTCHA_MODE=prod : 生产模式，经预留短信网关发送，不回显验证码，必须真实校验
    CAPTCHA_MODE = os.environ.get('CAPTCHA_MODE', 'dev').lower()
    CAPTCHA_EXPIRE_MINUTES = int(os.environ.get('CAPTCHA_EXPIRE_MINUTES', '5'))
    # 生产短信网关：预留接口，未接入真实服务前生产模式注册会给出明确提示
    SMS_GATEWAY_ENABLED = _env_bool('SMS_GATEWAY_ENABLED', False)

    # ---------- 管理员注册（安全开关） ----------
    # 生产环境默认禁止开放注册，需显式开启并提供邀请码
    ADMIN_REGISTRATION_ENABLED = _env_bool('ADMIN_REGISTRATION_ENABLED', False)
    ADMIN_REGISTER_INVITE_CODE = os.environ.get('ADMIN_REGISTER_INVITE_CODE', '')
    # 管理员登录失败锁定：连续失败达到上限后锁定一段时间，防止暴力破解
    ADMIN_LOGIN_MAX_ATTEMPTS = int(os.environ.get('ADMIN_LOGIN_MAX_ATTEMPTS', '5'))
    ADMIN_LOGIN_LOCK_MINUTES = int(os.environ.get('ADMIN_LOGIN_LOCK_MINUTES', '15'))

    # ---------- 种子数据 ----------
    # 本地环境可自动播种演示数据，生产默认关闭
    SEED_DEMO_DATA = _env_bool('SEED_DEMO_DATA', False)


class DevelopmentConfig(Config):
    DEBUG = True
    # 本地开发默认测试验证码 + 自动播种演示数据
    CAPTCHA_MODE = os.environ.get('CAPTCHA_MODE', 'dev').lower()
    SEED_DEMO_DATA = _env_bool('SEED_DEMO_DATA', True)
    ADMIN_REGISTRATION_ENABLED = _env_bool('ADMIN_REGISTRATION_ENABLED', True)


class TestingConfig(Config):
    """本地快速测试专用：SQLite 内存库 + SimpleCache，无需 MySQL / Redis。

    用于在不安装数据库服务的情况下起服务、跑通 API 结构。
    仅供测试，切勿用于生产。通过环境变量 CAMPUS_CONFIG=testing 启用。
    """
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL', 'sqlite:///:memory:')
    CACHE_TYPE = 'SimpleCache'
    CAPTCHA_MODE = 'dev'
    SEED_DEMO_DATA = _env_bool('SEED_DEMO_DATA', True)
    ADMIN_REGISTRATION_ENABLED = True


class LocalConfig(Config):
    """本地轻量持久化：SQLite 文件库 + SimpleCache，无需 MySQL / Redis。

    数据在 instance/campus_bazaar.db 落盘，重启不丢失；缓存用进程内 SimpleCache。
    适合本地开发与演示，切勿用于生产。通过环境变量 CAMPUS_CONFIG=local 启用。
    """
    DEBUG = True
    # 数据库文件放项目根目录下的 instance/（已在 .gitignore 忽略，不会被提交）
    _db_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            'instance', 'campus_bazaar.db')
    os.makedirs(os.path.dirname(_db_file), exist_ok=True)
    SQLALCHEMY_DATABASE_URI = os.environ.get('LOCAL_DATABASE_URL', 'sqlite:///' + _db_file)
    CACHE_TYPE = 'SimpleCache'
    CAPTCHA_MODE = os.environ.get('CAPTCHA_MODE', 'dev').lower()
    SEED_DEMO_DATA = _env_bool('SEED_DEMO_DATA', True)
    ADMIN_REGISTRATION_ENABLED = _env_bool('ADMIN_REGISTRATION_ENABLED', True)


class ProductionConfig(Config):
    DEBUG = False
    CAPTCHA_MODE = 'prod'
    ADMIN_REGISTRATION_ENABLED = _env_bool('ADMIN_REGISTRATION_ENABLED', False)
    SEED_DEMO_DATA = False

    @classmethod
    def validate(cls):
        """部署前调用：生产环境必须显式提供关键密钥。"""
        missing = [k for k in ('SECRET_KEY', 'JWT_SECRET_KEY', 'ENCRYPTION_KEY', 'DATABASE_URL')
                   if not os.environ.get(k)]
        if missing:
            raise RuntimeError('生产环境缺少必需环境变量: ' + ', '.join(missing))


config_map = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'local': LocalConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}


def get_config(name=None):
    """按名称返回配置类，默认读取环境变量 CAMPUS_CONFIG。"""
    name = (name or os.environ.get('CAMPUS_CONFIG') or 'default').lower()
    return config_map.get(name, DevelopmentConfig)
