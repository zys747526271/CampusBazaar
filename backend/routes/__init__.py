from .auth import auth_bp
from .admin import admin_bp
from .user import user_bp
from .product import product_bp
from .cart import cart_bp
from .order import order_bp
from .address import address_bp
from .tag import tag_bp
from .comment import comment_bp
from .balance import balance_bp
from .message import message_bp
from .favorite import favorite_bp
from .seller import seller_bp
from .seller_category import seller_category_bp

def register_blueprints(app):
    """注册所有蓝图"""
    # 注意：admin/order/tag/message 四个蓝图内部路由已自带完整路径（如 /admin/users、/orders、/tags），
    # 因此统一挂到 /api 前缀，避免 /api/admin/admin/users、/api/orders/orders 这类重复路径。
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(admin_bp, url_prefix='/api')
    app.register_blueprint(user_bp, url_prefix='/api/users')
    app.register_blueprint(product_bp, url_prefix='/api/products')
    app.register_blueprint(cart_bp, url_prefix='/api/carts')
    app.register_blueprint(order_bp, url_prefix='/api')
    app.register_blueprint(address_bp, url_prefix='/api/addresses')
    app.register_blueprint(tag_bp, url_prefix='/api')
    app.register_blueprint(comment_bp, url_prefix='/api/comments')
    app.register_blueprint(balance_bp, url_prefix='/api/balances')
    app.register_blueprint(message_bp, url_prefix='/api')
    app.register_blueprint(favorite_bp, url_prefix='/api')
    app.register_blueprint(seller_bp, url_prefix='/api')
    app.register_blueprint(seller_category_bp, url_prefix='/api')