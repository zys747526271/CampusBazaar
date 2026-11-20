"""卖家端路由：身份切换、商品管理、收到的订单、经营统计。"""
from flask import Blueprint, request
from ..models import db, User, Product, Order, Comment
from ..utils.decorators import login_required
from sqlalchemy import func
import json
import logging

seller_bp = Blueprint('seller', __name__)
logger = logging.getLogger(__name__)


def json_response(success, message, data=None, status=200):
    from flask import jsonify
    return jsonify({'success': success, 'message': message, 'data': data}), status


def _seller_or_403(current_user):
    if not current_user.is_seller:
        return None, json_response(False, '尚未开通卖家身份', status=403)
    return current_user, None


@seller_bp.route('/seller/become', methods=['POST'])
@login_required
def become_seller(current_user):
    """买家开通卖家身份（任何买家均可开通）。"""
    if current_user.is_seller:
        return json_response(True, '已是卖家', {'is_seller': True})
    current_user.is_seller = True
    try:
        db.session.commit()
        return json_response(True, '已开通卖家身份', {'is_seller': True})
    except Exception as e:
        db.session.rollback()
        return json_response(False, f'开通失败: {str(e)}', status=500)


@seller_bp.route('/seller/products', methods=['GET'])
@login_required
def my_products(current_user):
    """我发布的商品（含待审核/已下架，供卖家管理）。"""
    _, err = _seller_or_403(current_user)
    if err:
        return err
    items = Product.query.filter_by(seller_id=current_user.id, is_deleted=False).order_by(
        Product.created_at.desc()).all()

    # 从订单中统计每个商品的销量（排除已取消订单）
    sold = {}
    for order in Order.query.filter_by(is_deleted=False).all():
        if order.status == '已取消':
            continue
        try:
            order_items = json.loads(order.products_info) if order.products_info else []
        except (ValueError, TypeError):
            order_items = []
        for line in order_items:
            pid = line.get('product_id')
            if pid is not None:
                sold[pid] = sold.get(pid, 0) + int(line.get('quantity') or 0)

    result = []
    for p in items:
        d = p.to_dict()
        d['sold_count'] = sold.get(p.id, 0)
        d['stock'] = p.quantity or 0
        result.append(d)
    return json_response(True, '获取商品成功', result)


@seller_bp.route('/seller/products/<int:product_id>/comments', methods=['GET'])
@login_required
def product_comments(current_user, product_id):
    """查看自己某个商品的评论（含已隐藏，供卖家了解反馈）。"""
    _, err = _seller_or_403(current_user)
    if err:
        return err
    product = Product.query.filter_by(
        id=product_id, seller_id=current_user.id, is_deleted=False).first()
    if not product:
        return json_response(False, '商品不存在', status=404)
    items = Comment.query.filter_by(
        product_id=product_id, is_deleted=False
    ).order_by(Comment.create_time.desc()).all()
    return json_response(True, '获取商品评论成功', [c.to_dict(with_user=True) for c in items])


@seller_bp.route('/seller/orders', methods=['GET'])
@login_required
def received_orders(current_user):
    """我收到的订单（订单里包含我出售的商品）。"""
    _, err = _seller_or_403(current_user)
    if err:
        return err
    import json
    my_product_ids = {p.id for p in Product.query.filter_by(seller_id=current_user.id).all()}
    orders = Order.query.filter_by(is_deleted=False).order_by(Order.create_time.desc()).all()
    result = []
    for o in orders:
        try:
            items = json.loads(o.products_info) if o.products_info else []
        except (ValueError, TypeError):
            items = []
        # 仅保留包含本卖家商品的条目
        mine = [i for i in items if i.get('product_id') in my_product_ids]
        if mine:
            d = o.to_dict()
            d['my_items'] = mine
            result.append(d)
    return json_response(True, '获取收到的订单成功', result)


@seller_bp.route('/seller/products/<int:product_id>/toggle', methods=['PUT'])
@login_required
def toggle_my_product(current_user, product_id):
    """卖家上架/下架自己的商品。"""
    _, err = _seller_or_403(current_user)
    if err:
        return err
    product = Product.query.filter_by(id=product_id, seller_id=current_user.id, is_deleted=False).first()
    if not product:
        return json_response(False, '商品不存在', status=404)
    data = request.get_json(silent=True) or {}
    if product.status == '已通过' and product.is_available:
        product.is_available = False
        product.status = '已下架'
        action = '已下架'
    else:
        product.is_available = True
        product.status = '已通过'
        action = '已上架'
    try:
        db.session.commit()
        return json_response(True, f'商品{action}', {'status': product.status})
    except Exception as e:
        db.session.rollback()
        return json_response(False, f'操作失败: {str(e)}', status=500)


@seller_bp.route('/seller/stats', methods=['GET'])
@login_required
def seller_stats(current_user):
    """经营数据：在售数、总销量、总销售额、浏览总量。"""
    _, err = _seller_or_403(current_user)
    if err:
        return err
    products = Product.query.filter_by(seller_id=current_user.id, is_deleted=False).all()
    on_sale = sum(1 for p in products if p.status == '已通过' and p.is_available)
    total_views = sum(p.views or 0 for p in products)
    return json_response(True, '获取经营数据成功', {
        'product_count': len(products),
        'on_sale_count': on_sale,
        'total_views': total_views,
    })
