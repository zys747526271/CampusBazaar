from functools import wraps
from flask import request, jsonify, current_app
import jwt
from typing import Optional, Union, Callable
import logging
import pickle
from datetime import timedelta
import redis
from ..models import User, Admin

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AuthError(ValueError):
    """认证失败（HTTP 401）：令牌缺失、过期、无效，或账号不存在/被封禁。"""


class PermissionDenied(ValueError):
    """权限不足（HTTP 403）：身份已确认，但角色或权限级别不符合接口要求。"""


def get_redis_client():
    """仅在 RedisCache 模式下尝试连接 Redis；本地 SimpleCache 模式直接返回 None。"""
    cache_type = current_app.config.get('CACHE_TYPE', 'SimpleCache')
    if cache_type != 'RedisCache':
        return None
    try:
        redis_url = current_app.config.get('REDIS_URL', 'redis://localhost:6379/0')
        redis_pool = redis.ConnectionPool.from_url(redis_url)
        client = redis.Redis(connection_pool=redis_pool)
        client.ping()
        return client
    except Exception as e:
        logger.warning(f"Redis 不可用，跳过用户缓存: {str(e)}")
        return None


def get_token_from_header() -> Optional[str]:
    """从请求头中获取令牌"""
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        logger.debug("No Authorization header found")
        return None
    if not auth_header.startswith('Bearer '):
        logger.debug(f"Invalid Authorization header format: {auth_header}")
        return None
    token = auth_header.split(' ')[1]
    logger.debug(f"Extracted token: {token}")
    return token


def verify_token(token: str) -> dict:
    """验证并解码JWT令牌"""
    if not token:
        raise AuthError('令牌为空')
    try:
        # 确保 JWT_SECRET_KEY 存在
        secret_key = current_app.config.get('JWT_SECRET_KEY')
        if not secret_key:
            logger.error("JWT_SECRET_KEY is not set in config")
            raise AuthError('服务器配置错误：缺少JWT密钥')
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        logger.debug(f"Token decoded successfully: {payload}")
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthError('令牌已过期，请重新登录')
    except jwt.InvalidTokenError as e:
        logger.error(f"Token verification failed: {str(e)}")
        raise AuthError(f'令牌验证失败: {str(e)}')


def get_current_user(payload: dict) -> Union[User, Admin]:
    """根据令牌载荷获取当前用户（带缓存）"""
    redis_client = get_redis_client()
    user_type = payload.get("type")
    user_id = payload.get("user_id") if user_type == "user" else payload.get("admin_id")
    if not user_id:
        raise AuthError('令牌中缺少用户ID')

    cache_key = f'user:{user_id}'

    # 检查缓存
    if redis_client:
        try:
            cached_user = redis_client.get(cache_key)
            if cached_user:
                return pickle.loads(cached_user)
        except redis.RedisError as e:
            logger.warning(f"Redis cache error: {str(e)}. Proceeding without cache.")

    # 查询数据库
    if user_type == 'user':
        user = User.query.filter_by(id=user_id, is_deleted=False).first()
        if not user:
            raise AuthError('用户不存在')
        if user.is_banned:
            raise AuthError('用户已被封禁')
        if redis_client:
            try:
                redis_client.setex(cache_key, timedelta(minutes=10), pickle.dumps(user))
            except redis.RedisError as e:
                logger.warning(f"Failed to cache user {user_id}: {str(e)}")
        return user
    elif user_type == 'admin':
        admin = Admin.query.filter_by(id=user_id).first()
        if not admin:
            raise AuthError('管理员不存在')
        if redis_client:
            try:
                redis_client.setex(cache_key, timedelta(minutes=10), pickle.dumps(admin))
            except redis.RedisError as e:
                logger.warning(f"Failed to cache admin {user_id}: {str(e)}")
        return admin
    else:
        raise AuthError('无效的令牌类型')


def auth_decorator(user_type: str = None, permission_level: int = None) -> Callable:
    """通用认证装饰器"""

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated(*args, **kwargs):
            token = get_token_from_header()
            if not token:
                return jsonify({'success': False, 'message': '缺少认证令牌'}), 401

            try:
                payload = verify_token(token)

                if user_type and payload.get('type') != user_type:
                    raise PermissionDenied(
                        f'需要{"普通用户" if user_type == "user" else "管理员"}身份，当前身份不匹配')

                current_user = get_current_user(payload)

                if permission_level is not None:
                    if not isinstance(current_user, Admin):
                        raise PermissionDenied('需要管理员权限')
                    if hasattr(current_user, 'permission_level') and current_user.permission_level < permission_level:
                        raise PermissionDenied('权限不足')
                    if not hasattr(current_user, 'is_super_admin') or (
                            not current_user.is_super_admin() and permission_level >= 2):
                        raise PermissionDenied('需要超级管理员权限')

                logger.info(f"User {current_user.id} (type: {user_type or 'any'}) accessed {request.path}")
                return f(current_user, *args, **kwargs)

            except PermissionDenied as e:
                # 身份已确认但角色/权限不匹配：403，前端不得据此清除登录态
                logger.warning(f"Permission denied: {str(e)}")
                return jsonify({'success': False, 'message': str(e)}), 403
            except AuthError as e:
                logger.warning(f"Auth failed: {str(e)}")
                return jsonify({'success': False, 'message': str(e)}), 401
            except Exception as e:
                logger.error(f"Unexpected error during authentication: {str(e)}")
                return jsonify({'success': False, 'message': '认证过程中发生未知错误'}), 500

        return decorated

    return decorator


def token_required(f: Callable) -> Callable:
    """验证用户JWT令牌的装饰器"""
    return auth_decorator()(f)


def login_required(f: Callable) -> Callable:
    """验证普通用户JWT令牌的装饰器"""
    return auth_decorator(user_type='user')(f)


def admin_required(f: Callable) -> Callable:
    """验证管理员JWT令牌的装饰器"""
    return auth_decorator(user_type='admin')(f)


def super_admin_required(f: Callable) -> Callable:
    """验证超级管理员JWT令牌的装饰器"""
    return auth_decorator(user_type='admin', permission_level=2)(f)