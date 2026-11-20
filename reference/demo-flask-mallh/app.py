from flask import Flask
from config.settings import MySQLConfig
from models.models import db
from flask_migrate import Migrate
from routes.auth import auth_bp
from routes.user import user_bp
from routes.goods import goods_bp
from routes.order import order_bp
from routes.admin import admin_bp
from routes.vip import vip_bp
from routes.ad import ad_bp
from routes.comment import comment_bp
import logging

# 配置日志，便于调试和监控
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 初始化 Flask 应用
app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config.from_object(MySQLConfig)

# 配置会话，确保在WebView环境中正常工作
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_DOMAIN'] = None
app.config['SESSION_COOKIE_PATH'] = '/'

# 配置CORS以支持跨域请求
from flask_cors import CORS
CORS(app, supports_credentials=True, resources={r"/*": {"origins": "*"}})

# 初始化数据库和迁移
db.init_app(app)
migrate = Migrate(app, db)


# 在应用启动时检查和初始化数据
def init_data():
    with app.app_context():
        db.create_all()  # 创建所有表（如果不存在）
        from models.models import Vip, Goods
        # 初始化 VIP 数据
        vips = Vip.query.all()
        if not vips:
            db.session.add(Vip(name="VIP1", level=1))
            db.session.add(Vip(name="VIP2", level=2))
            db.session.add(Vip(name="VIP3", level=3))
            db.session.commit()
            logger.info("初始化 VIP 数据成功")
        # 更新 Goods 表中 is_active 为 None 的记录
        updated = Goods.query.filter_by(is_active=None).update({"is_active": True})
        if updated:
            db.session.commit()
            logger.info(f"更新了 {updated} 条 Goods 数据，设置 is_active=True")


# 注册 Blueprint
app.register_blueprint(auth_bp)
app.register_blueprint(user_bp)
app.register_blueprint(goods_bp)
app.register_blueprint(order_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(vip_bp)
app.register_blueprint(ad_bp)
app.register_blueprint(comment_bp)

if __name__ == '__main__':
    # 初始化数据
    init_data()

    # 使用 waitress 启动服务（Windows 兼容）
    from waitress import serve

    logger.info("Starting server with Waitress on 0.0.0.0:5000")
    # serve(app, host="0.0.0.0", port=5000, threads=8)  # 8 个线程处理并发请求
    app.run(host="0.0.0.0", debug=True)