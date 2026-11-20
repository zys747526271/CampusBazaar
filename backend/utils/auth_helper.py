"""验证码与密码重置令牌工具。

存储层统一使用 Flask-Caching（由 app 的 cache 实例初始化），
本地 local/testing 用 SimpleCache（进程内存，无需 Redis），
生产用 RedisCache（多进程共享），从而彻底移除对 Redis 的硬编码直接连接。

测试/生产分离：
  - dev  模式：调用方（路由）可在响应中回显 dev_code，便于本地测试填写；
  - prod 模式：仅通过预留短信网关发送，不回显，必须真实校验。
"""
from flask import current_app
from ..extensions import cache as _cache_instance
from werkzeug.security import generate_password_hash, check_password_hash
import random
import string
import threading
import time
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

# 验证码 / 令牌在缓存中的 key 前缀
CAPTCHA_PREFIX = 'verification_code:'
RESET_TOKEN_PREFIX = 'reset_token:'

# 测试模式验证码展示台账：仅 dev 模式写入，供后端网页 /dev/captchas 查看。
# 只保留未过期且在上限内的最近记录，避免无限增长；生产模式不写入任何记录。
DEV_CAPTCHA_LOG_LIMIT = 50
_dev_captcha_log = []
_dev_captcha_log_lock = threading.Lock()


def record_dev_captcha(key, code, expire_seconds):
    """记录一条测试验证码，供后端页面展示（调用方须确保处于 dev 模式）。"""
    now = time.time()
    with _dev_captcha_log_lock:
        _dev_captcha_log.append({
            'key': key,
            'code': code,
            'created_at': now,
            'expire_at': now + expire_seconds,
            'consumed': False
        })
        while len(_dev_captcha_log) > DEV_CAPTCHA_LOG_LIMIT:
            _dev_captcha_log.pop(0)


def mark_dev_captcha_consumed(key):
    """把该接收者最近一条仍有效的测试验证码标记为已使用。"""
    now = time.time()
    with _dev_captcha_log_lock:
        for item in reversed(_dev_captcha_log):
            if item['key'] == key and not item['consumed'] and item['expire_at'] > now:
                item['consumed'] = True
                break


def list_dev_captchas():
    """返回当前仍有效的测试验证码列表（最新的在前）。"""
    now = time.time()
    with _dev_captcha_log_lock:
        items = [dict(item) for item in _dev_captcha_log if item['expire_at'] > now]
    items.reverse()
    for item in items:
        item['remaining_seconds'] = max(0, int(item['expire_at'] - now))
    return items


def _cache():
    """获取全局缓存实例（在 create_app 中 init_app）。"""
    return _cache_instance


def hash_password(password):
    """对密码进行加密。"""
    return generate_password_hash(password)


def verify_password(password_hash, password):
    """验证密码。"""
    return check_password_hash(password_hash, password)


def generate_verification_code(length=6, use_letters=False):
    """生成验证码，支持数字或字母+数字组合。"""
    chars = string.digits + (string.ascii_letters if use_letters else '')
    return ''.join(random.choices(chars, k=length))


def save_verification_code(key, code, expire_minutes=None):
    """保存验证码到缓存（SimpleCache 或 RedisCache，随运行模式）。"""
    if expire_minutes is None:
        expire_minutes = current_app.config.get('CAPTCHA_EXPIRE_MINUTES', 5)
    _cache().set(CAPTCHA_PREFIX + key, code, timeout=int(timedelta(minutes=expire_minutes).total_seconds()))
    logger.info(f"验证码已保存: {key}（有效期 {expire_minutes} 分钟）")


def verify_code(key, code, consume=True):
    """校验验证码。consume=True 时校验成功即销毁（一次性）。"""
    stored = _cache().get(CAPTCHA_PREFIX + key)
    if stored is None:
        return False
    stored = str(stored)
    if stored != str(code):
        return False
    if consume:
        _cache().delete(CAPTCHA_PREFIX + key)
        mark_dev_captcha_consumed(key)
    return True


def peek_code(key):
    """读取当前验证码（仅 dev 模式用于测试回显，prod 模式不应调用）。"""
    stored = _cache().get(CAPTCHA_PREFIX + key)
    return str(stored) if stored is not None else None


def generate_reset_token(user_id, expire_hours=24):
    """生成密码重置令牌。"""
    token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    _cache().set(RESET_TOKEN_PREFIX + token, str(user_id),
                timeout=int(timedelta(hours=expire_hours).total_seconds()))
    return token


def verify_reset_token(token):
    """验证密码重置令牌，成功返回用户ID，否则 None。"""
    user_id = _cache().get(RESET_TOKEN_PREFIX + token)
    if not user_id:
        return None
    _cache().delete(RESET_TOKEN_PREFIX + token)
    try:
        return int(user_id)
    except (ValueError, TypeError):
        return None
