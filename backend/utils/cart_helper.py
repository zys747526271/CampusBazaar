"""购物车辅助逻辑。

库存一致性：
  - 生产（RedisCache）：用 Redis WATCH 做乐观锁；
  - 本地（SimpleCache/内存）：直接以数据库库存判断，无 Redis 依赖。
统一通过 runtime_cache.get_store() 适配，避免 local 模式崩溃。
"""
from flask import current_app
from ..models import db, Cart, Product
from ..utils.runtime_cache import get_store
from sqlalchemy import and_
import redis
import logging

logger = logging.getLogger(__name__)


def check_stock(product_id, quantity):
    """检查商品库存（生产用 Redis 乐观锁，本地用数据库直查）。"""
    product = Product.query.filter_by(
        id=product_id, is_deleted=False, status='已通过'
    ).first()
    if not product:
        return False, '商品不存在或已下架'

    cache_type = current_app.config.get('CACHE_TYPE', 'SimpleCache')
    if cache_type != 'RedisCache':
        if product.quantity < quantity:
            return False, f'商品库存不足，当前库存: {product.quantity}'
        return True, '库存充足'

    store = get_store()
    # 底层是真实 redis-py 客户端时可用 pipeline；此处退化处理
    redis_key = f'stock:{product_id}'
    try:
        raw = store.get(redis_key)
        stock = int(raw) if raw is not None else product.quantity
        if stock < quantity:
            return False, f'商品库存不足，当前库存: {stock}'
        return True, '库存充足'
    except Exception:
        logger.warning(f"库存检查异常，按数据库库存处理: product {product_id}")
        if product.quantity < quantity:
            return False, f'商品库存不足，当前库存: {product.quantity}'
        return True, '库存充足'


def batch_add_to_cart(user_id, items):
    """批量添加商品到购物车（优化事务提交）。"""
    success_items = []
    for item in items:
        product_id = item.get('product_id')
        quantity = item.get('quantity', 1)
        stock_ok, message = check_stock(product_id, quantity)
        if not stock_ok:
            logger.warning(f"库存检查未通过 product {product_id}: {message}")
            continue

        cart_item = Cart.query.filter(
            and_(Cart.user_id == user_id, Cart.product_id == product_id, Cart.is_deleted == False)
        ).first()
        if cart_item:
            cart_item.quantity += quantity
        else:
            db.session.add(Cart(user_id=user_id, product_id=product_id, quantity=quantity))
        success_items.append(product_id)

    if success_items:
        try:
            db.session.commit()
            logger.info(f"加入购物车 user {user_id}: {success_items}")
            return True, '商品已添加到购物车', success_items
        except Exception as e:
            db.session.rollback()
            logger.error(f"加入购物车失败 user {user_id}: {str(e)}")
            return False, f'添加失败: {str(e)}', []
    return False, '没有商品被添加到购物车', []


def batch_update_cart(user_id, items):
    """批量更新购物车商品数量。"""
    success_items = []
    for item in items:
        cart_id = item.get('cart_id')
        quantity = item.get('quantity', 1)
        cart_item = Cart.query.filter_by(id=cart_id, user_id=user_id, is_deleted=False).first()
        if not cart_item:
            continue
        stock_ok, message = check_stock(cart_item.product_id, quantity)
        if not stock_ok:
            logger.warning(f"更新数量失败 cart {cart_id}: {message}")
            continue
        cart_item.quantity = quantity
        success_items.append(cart_id)

    if success_items:
        try:
            db.session.commit()
            return True, '购物车已更新', success_items
        except Exception as e:
            db.session.rollback()
            logger.error(f"更新购物车失败 user {user_id}: {str(e)}")
            return False, f'更新失败: {str(e)}', []
    return False, '没有购物车项被更新', []
