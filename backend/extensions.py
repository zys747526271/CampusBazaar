"""Flask 扩展实例（单一来源，避免循环导入）。"""
from flask_caching import Cache
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
cache = Cache()
