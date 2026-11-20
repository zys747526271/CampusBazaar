"""管理后台蓝图集合：统一挂载在 ``/api/admin`` 下，全部要求管理员令牌。"""
from flask import Blueprint

bp = Blueprint("admin", __name__, url_prefix="/api/admin")

from backend.api.admin import catalog, comments, dashboard, moderation, orders, products, sellers, users  # noqa: E402,F401
