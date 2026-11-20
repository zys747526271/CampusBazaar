"""启动时的数据库自举：平滑迁移 + 演示种子数据。

- 平滑迁移：为旧版 SQLite 库补齐后来新增的列（SQLite 的 create_all 不会 ALTER 已存在的表）。
- 种子数据：仅当 SEED_DEMO_DATA=True（本地/开发/测试模式默认开）且商品表为空时写入，
  让主页打开即可看到商品，便于浏览演示。生产环境默认关闭。
密钥与数据写入均使用 ORM，不落地任何明文凭据。
"""
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)


def ensure_columns(app, db):
    """为 SQLite 旧库补齐新增列（幂等）。"""
    if 'sqlite' not in db.engine.url.get_backend_name():
        return
    with db.engine.connect() as conn:
        cols = {row[1] for row in conn.exec_driver_sql('PRAGMA table_info(users)')}
        if 'is_seller' not in cols:
            conn.exec_driver_sql('ALTER TABLE users ADD COLUMN is_seller BOOLEAN DEFAULT 0')
            conn.commit()
            logger.info('已为 users 表补齐 is_seller 列')
        msg_cols = {row[1] for row in conn.exec_driver_sql('PRAGMA table_info(messages)')}
        if 'is_deleted' not in msg_cols:
            conn.exec_driver_sql('ALTER TABLE messages ADD COLUMN is_deleted BOOLEAN DEFAULT 0')
            conn.commit()
            logger.info('已为 messages 表补齐 is_deleted 列')
        product_cols = {row[1] for row in conn.exec_driver_sql('PRAGMA table_info(products)')}
        if 'seller_category_id' not in product_cols:
            conn.exec_driver_sql('ALTER TABLE products ADD COLUMN seller_category_id INTEGER')
            conn.commit()
            logger.info('已为 products 表补齐 seller_category_id 列')
        comment_cols = {row[1] for row in conn.exec_driver_sql('PRAGMA table_info(comments)')}
        if 'is_hidden' not in comment_cols:
            conn.exec_driver_sql('ALTER TABLE comments ADD COLUMN is_hidden BOOLEAN DEFAULT 0')
            conn.commit()
            logger.info('已为 comments 表补齐 is_hidden 列')


def seed_demo_data(app, db):
    """写入演示数据（商品为空时才写），仅本地环境。"""
    from .models import User, Tag, Product

    with app.app_context():
        if Product.query.count() > 0:
            return

        # 演示标签
        tag_names = ['电子产品', '图书教材', '生活用品', '运动户外']
        tags = {}
        for name in tag_names:
            tag = Tag.query.filter_by(name=name).first()
            if not tag:
                tag = Tag(name=name, description=f'{name}分类')
                db.session.add(tag)
        db.session.flush()
        for name in tag_names:
            tags[name] = Tag.query.filter_by(name=name).first()

        # 演示卖家
        seller = User.query.filter_by(phone='13900000001').first()
        if not seller:
            seller = User(
                quick_id=f'U{uuid.uuid4().hex[:8].upper()}',
                nickname='校园卖家小明', phone='13900000001',
                password='demo123456', email='seller@demo.local',
                is_seller=True, register_time=datetime.utcnow()
            )
            db.session.add(seller)
            db.session.flush()
            from .models import Balance
            db.session.add(Balance(user_id=seller.id, amount=0.0))

        demo_products = [
            ('九成新高等数学教材', 25.0, '高等数学第七版上下册，笔记已擦净，考研可伴读。', '图书教材', 3),
            ('宿舍迷你电风扇', 39.0, '静音三档风力，毕业出闲置，功能完好。', '生活用品', 2),
            ('机械键盘 87 键', 120.0, '青轴，手感清脆，自用一年，无磕碰。', '电子产品', 1),
            ('二手篮球 7 号', 45.0, '室外场地使用过，磨损轻微，充气充足。', '运动户外', 2),
            ('考研英语真题套装', 30.0, '近十年真题带解析，品相良好。', '图书教材', 4),
            ('折叠式台灯', 20.0, '护眼暖光，可折叠，宿舍学习适用。', '生活用品', 2),
        ]
        for name, price, desc, tag_name, qty in demo_products:
            db.session.add(Product(
                quick_id=f'P{uuid.uuid4().hex[:8].upper()}',
                name=name, price=price, description=desc,
                tag_id=tags[tag_name].id if tags.get(tag_name) else None,
                seller_id=seller.id, quantity=qty,
                status='已通过', is_available=True, views=10
            ))
        try:
            db.session.commit()
            logger.info('演示种子数据已写入')
        except Exception as e:
            db.session.rollback()
            logger.error(f'写入种子数据失败: {str(e)}')
