"""蓝图注册：所有路由都挂在 ``/api`` 下（管理端为 ``/api/admin``）。"""
from flask import Flask


def register_blueprints(app: Flask) -> None:
    from backend.api import account, auth, cart, interactions, orders, public, seller, uploads
    from backend.api.admin import bp as admin_bp

    for module in (auth, public, cart, orders, seller, interactions, account, uploads):
        app.register_blueprint(module.bp)
    app.register_blueprint(admin_bp)
