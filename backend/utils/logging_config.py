"""集中日志配置：按业务分类写入项目根目录下的 logs/。

分类：
- app.log      通用运行/业务日志
- access.log   HTTP 访问日志（每个请求一行）
- error.log    错误与异常
- security.log 认证、授权、管理员操作等安全相关事件

按天滚动，保留 14 天，单文件上限 10 MB。生产可通过 LOG_DIR / LOG_LEVEL 覆盖。
"""
import os
import logging
from logging.handlers import TimedRotatingFileHandler

# 本文件位于 backend/utils/，向上两级才是项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_DIR = os.environ.get('LOG_DIR', os.path.join(PROJECT_ROOT, 'logs'))
os.makedirs(LOG_DIR, exist_ok=True)

LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()
LOG_RETENTION_DAYS = int(os.environ.get('LOG_RETENTION_DAYS', '14'))
LOG_MAX_BYTES = int(os.environ.get('LOG_MAX_BYTES', str(10 * 1024 * 1024)))

_FORMAT = logging.Formatter(
    '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')


def _file_handler(filename):
    handler = TimedRotatingFileHandler(
        os.path.join(LOG_DIR, filename), when='midnight',
        interval=1, backupCount=LOG_RETENTION_DAYS, encoding='utf-8')
    handler.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    handler.setFormatter(_FORMAT)
    handler.maxBytes = LOG_MAX_BYTES
    return handler


def get_logger(name, category='app'):
    """获取一个带分类文件 handler 的 logger，重复调用不会重复挂载。"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    key = f'_campus_{category}_handler'
    if not getattr(logger, key, None):
        handler = _file_handler(f'{category}.log')
        setattr(logger, key, handler)
        logger.addHandler(handler)
    return logger


def install_request_logging(app):
    """为每个请求写访问日志，并按状态码把 4xx/5xx 同步写入 error.log。"""
    access = get_logger('access', 'access')
    errors = get_logger('errors', 'error')

    @app.after_request
    def _log_request(response):
        remote = request.remote_addr or '-'
        user = getattr(getattr(request, 'current_user', None), 'id', '-')
        access.info('%s %s %s -> %s user=%s', remote, request.method,
                    request.path, response.status_code, user)
        if response.status_code >= 500:
            errors.error('HTTP %s %s -> %s', request.method, request.path,
                         response.status_code)
        elif response.status_code in (401, 403):
            errors.warning('HTTP %s %s -> %s', request.method, request.path,
                           response.status_code)
        return response

    return app


from flask import request  # noqa: E402  放在此处避免循环导入开销
