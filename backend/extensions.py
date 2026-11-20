"""共享扩展实例（供应用初始化与各模块统一访问，避免循环导入）。"""
from flask_caching import Cache

# 全应用唯一的缓存实例；在 create_app() 中调用 cache.init_app(app)
cache = Cache()
