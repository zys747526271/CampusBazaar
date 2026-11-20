from flask import Blueprint, request, jsonify
from ..models import db, User, Product, Order, Comment
from ..utils.decorators import admin_required, super_admin_required
from sqlalchemy import desc, func
from datetime import datetime, timedelta
import logging

admin_bp = Blueprint('admin', __name__)
logger = logging.getLogger(__name__)

def json_response(success, message, data=None, status=200):
    """统一响应格式"""
    return jsonify({'success': success, 'message': message, 'data': data}), status


@admin_bp.route('/admin/stats', methods=['GET'])
@admin_required
def dashboard_stats(current_admin):
    """管理控制台统计数据。"""
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    user_count = User.query.filter_by(is_deleted=False).count()
    new_users = User.query.filter(User.created_at >= today, User.is_deleted == False).count()
    product_count = Product.query.filter_by(is_deleted=False).count()
    new_products = Product.query.filter(Product.created_at >= today, Product.is_deleted == False).count()
    order_count = Order.query.filter_by(is_deleted=False).count()
    new_orders = Order.query.filter(Order.create_time >= today, Order.is_deleted == False).count()
    paid_orders = Order.query.filter(Order.status.in_(['已付款', '已发货', '已完成']), Order.is_deleted == False).all()
    total_sales = sum(o.total_amount for o in paid_orders)
    today_sales = sum(o.total_amount for o in paid_orders if o.payment_time and o.payment_time >= today)
    return json_response(True, '获取统计成功', {
        'userCount': user_count, 'newUserCount': new_users,
        'productCount': product_count, 'newProductCount': new_products,
        'orderCount': order_count, 'newOrderCount': new_orders,
        'totalSales': total_sales, 'todaySales': today_sales
    })


@admin_bp.route('/admin/orders/recent', methods=['GET'])
@admin_required
def recent_orders(current_admin):
    """最近订单（供控制台展示）。"""
    orders = Order.query.filter_by(is_deleted=False).order_by(desc(Order.create_time)).limit(10).all()
    result = []
    for o in orders:
        d = o.to_dict()
        d['created_at'] = d.get('create_time')
        result.append(d)
    return json_response(True, '获取最近订单成功', result)

@admin_bp.route('/admin/sellers', methods=['GET'])
@admin_required
def admin_sellers(current_admin):
    """商家列表：支持按昵称/手机号搜索，并带出每个商家的商品数量。"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = (request.args.get('search') or '').strip()

    query = User.query.filter(User.is_seller == True, User.is_deleted == False)
    if search:
        like = f'%{search}%'
        query = query.filter(db.or_(User.nickname.like(like), User.phone.like(like)))
    paginate = query.order_by(desc(User.created_at)).paginate(
        page=page, per_page=per_page, error_out=False)

    items = []
    for u in paginate.items:
        d = u.to_dict()
        d['product_count'] = Product.query.filter_by(
            seller_id=u.id, is_deleted=False).count()
        items.append(d)
    return json_response(True, '获取商家列表成功', {
        'items': items, 'total': paginate.total,
        'current_page': page, 'per_page': per_page
    })


@admin_bp.route('/admin/sellers/<int:seller_id>/products', methods=['GET'])
@admin_required
def admin_seller_products(current_admin, seller_id):
    """查看指定商家的商品，支持按名称/编号搜索。"""
    seller = User.query.filter_by(id=seller_id, is_deleted=False).first()
    if not seller:
        return json_response(False, '商家不存在', status=404)
    search = (request.args.get('search') or '').strip()
    query = Product.query.filter_by(seller_id=seller_id, is_deleted=False)
    if search:
        query = query.filter(Product.name.like(f'%{search}%'))
    items = query.order_by(desc(Product.created_at)).all()
    return json_response(True, '获取商家商品成功', {
        'seller': {'id': seller.id, 'nickname': seller.nickname, 'phone': seller.phone},
        'items': [p.to_dict(with_seller=True) for p in items]
    })


@admin_bp.route('/admin/comments', methods=['GET'])
@admin_required
def admin_comments(current_admin):
    """全站评论列表：支持按商品名称、卖家、隐藏状态筛选。"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = (request.args.get('search') or '').strip()
    seller_id = request.args.get('seller_id', type=int)
    hidden = request.args.get('hidden')

    query = Comment.query.filter_by(is_deleted=False)
    if search:
        like = f'%{search}%'
        query = query.join(Product, Comment.product_id == Product.id).filter(
            db.or_(Product.name.like(like), Comment.content.like(like)))
    if seller_id:
        query = query.join(Product, Comment.product_id == Product.id).filter(
            Product.seller_id == seller_id)
    if hidden in ('true', 'false', '1', '0'):
        query = query.filter(Comment.is_hidden == (hidden in ('true', '1')))

    paginate = query.order_by(desc(Comment.create_time)).paginate(
        page=page, per_page=per_page, error_out=False)
    items = []
    for c in paginate.items:
        d = c.to_dict(with_user=True)
        product = Product.query.get(c.product_id)
        d['product_name'] = product.name if product else ''
        items.append(d)
    return json_response(True, '获取评论成功', {
        'items': items, 'total': paginate.total,
        'current_page': page, 'per_page': per_page
    })


@admin_bp.route('/admin/comments/<int:comment_id>/visibility', methods=['PUT'])
@admin_required
def admin_toggle_comment_visibility(current_admin, comment_id):
    """隐藏/恢复评论（参考电商平台的评论治理，不物理删除）。"""
    comment = Comment.query.filter_by(id=comment_id, is_deleted=False).first()
    if not comment:
        return json_response(False, '评论不存在', status=404)
    data = request.get_json(silent=True) or {}
    if 'is_hidden' in data:
        comment.is_hidden = bool(data['is_hidden'])
    else:
        comment.is_hidden = not bool(comment.is_hidden)
    action = '已隐藏' if comment.is_hidden else '已恢复显示'
    try:
        db.session.commit()
        logger.info(f'管理员 {current_admin.id} {action}评论 {comment_id}')
        return json_response(True, f'评论{action}', {'is_hidden': comment.is_hidden})
    except Exception as e:
        db.session.rollback()
        return json_response(False, f'操作失败: {e}', status=500)


@admin_bp.route('/admin/users', methods=['GET'])
@admin_required
def get_users(current_admin):
    """获取用户列表，支持分页和搜索

    Args:
        page (int, optional): 页码，默认1
        per_page (int, optional): 每页数量，默认10
        search (str, optional): 搜索关键词

    Returns:
        JSON: 用户列表
    """
    page = max(1, request.args.get('page', 1, type=int))
    per_page = max(1, min(100, request.args.get('per_page', 10, type=int)))
    search = request.args.get('search', '').strip()

    query = User.query.filter_by(is_deleted=False)
    if search:
        query = query.filter(
            (User.nickname.ilike(f'%{search}%')) |
            (User.quick_id.ilike(f'%{search}%'))
        )

    pagination = query.order_by(desc(User.created_at)).paginate(page=page, per_page=per_page)
    logger.info(f"Admin {current_admin.id} fetched user list (page={page}, search={search})")
    return json_response(True, '获取用户列表成功', {
        'items': [user.to_dict(include_sensitive=True) for user in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    })

@admin_bp.route('/admin/users/<int:user_id>', methods=['GET'])
@admin_required
def get_user(current_admin, user_id):
    """获取用户详情

    Args:
        user_id (int): 用户ID

    Returns:
        JSON: 用户信息
    """
    user = User.query.get_or_404(user_id)
    if user.is_deleted:
        return json_response(False, '用户不存在', status=404)

    logger.info(f"Admin {current_admin.id} fetched user {user_id} details")
    return json_response(True, '获取用户详情成功', user.to_dict(include_sensitive=True))

@admin_bp.route('/admin/users/<int:user_id>/ban', methods=['PUT'])
@admin_required
def ban_user(current_admin, user_id):
    """封禁/解封用户

    Args:
        user_id (int): 用户ID
        is_banned (bool): 是否封禁

    Returns:
        JSON: 操作结果
    """
    user = User.query.get_or_404(user_id)
    if user.is_deleted:
        return json_response(False, '用户不存在', status=404)

    data = request.get_json()
    if 'is_banned' not in data or not isinstance(data['is_banned'], bool):
        return json_response(False, '缺少is_banned字段或格式错误', status=400)

    user.is_banned = data['is_banned']
    try:
        db.session.commit()
        action = "封禁" if data["is_banned"] else "解封"
        logger.info(f"Admin {current_admin.id} {action}ed user {user_id}")
        return json_response(True, f'用户已{action}', {'is_banned': user.is_banned})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Admin {current_admin.id} failed to {action} user {user_id}: {str(e)}")
        return json_response(False, f'操作失败: {str(e)}', status=500)

@admin_bp.route('/admin/users/<int:user_id>', methods=['DELETE'])
@super_admin_required
def delete_user(current_admin, user_id):
    """删除用户（软删除，需超级管理员权限）

    Args:
        user_id (int): 用户ID

    Returns:
        JSON: 删除结果
    """
    user = User.query.get_or_404(user_id)
    user.is_deleted = True
    try:
        db.session.commit()
        logger.info(f"Super admin {current_admin.id} deleted user {user_id}")
        return json_response(True, '用户已删除')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Super admin {current_admin.id} failed to delete user {user_id}: {str(e)}")
        return json_response(False, f'删除失败: {str(e)}', status=500)

@admin_bp.route('/admin/products/pending', methods=['GET'])
@admin_required
def get_pending_products(current_admin):
    """获取待审核商品列表

    Args:
        page (int, optional): 页码，默认1
        per_page (int, optional): 每页数量，默认10

    Returns:
        JSON: 商品列表
    """
    page = max(1, request.args.get('page', 1, type=int))
    per_page = max(1, min(100, request.args.get('per_page', 10, type=int)))

    pagination = Product.query.filter_by(status='待审核', is_deleted=False).order_by(desc(Product.created_at)).paginate(
        page=page, per_page=per_page)
    logger.info(f"Admin {current_admin.id} fetched pending products (page={page})")
    return json_response(True, '获取待审核商品成功', {
        'items': [product.to_dict(with_seller=True) for product in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    })

@admin_bp.route('/admin/products/batch/status', methods=['PUT'])
@admin_required
def batch_update_product_status(current_admin):
    """批量更新商品状态

    Args:
        product_ids (list): 商品ID列表
        status (str): 新状态（已通过/已下架）

    Returns:
        JSON: 更新结果
    """
    data = request.get_json()
    if not data or not all(k in data for k in ['product_ids', 'status']) or not isinstance(data['product_ids'], list):
        return json_response(False, '缺少必填字段或格式错误: product_ids, status', status=400)

    if data['status'] not in ['已通过', '已下架']:
        return json_response(False, '无效的状态值', status=400)

    Product.query.filter(Product.id.in_(data['product_ids']), Product.is_deleted == False).update(
        {Product.status: data['status']}, synchronize_session=False
    )
    try:
        db.session.commit()
        logger.info(f"Admin {current_admin.id} updated product statuses: {data['product_ids']} to {data['status']}")
        return json_response(True, f'商品状态已更新为{data["status"]}')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Admin {current_admin.id} failed to update product statuses: {str(e)}")
        return json_response(False, f'更新失败: {str(e)}', status=500)

@admin_bp.route('/admin/users/<int:user_id>/orders', methods=['GET'])
@admin_required
def get_user_orders(current_admin, user_id):
    """获取指定用户的订单列表

    Args:
        user_id (int): 用户ID
        page (int, optional): 页码，默认1
        per_page (int, optional): 每页数量，默认10
        status (str, optional): 订单状态

    Returns:
        JSON: 订单列表
    """
    page = max(1, request.args.get('page', 1, type=int))
    per_page = max(1, min(100, request.args.get('per_page', 10, type=int)))
    status = request.args.get('status')

    query = Order.query.filter_by(user_id=user_id, is_deleted=False)
    if status:
        query = query.filter_by(status=status)

    pagination = query.order_by(desc(Order.create_time)).paginate(page=page, per_page=per_page)
    logger.info(f"Admin {current_admin.id} fetched orders for user {user_id} (page={page}, status={status})")
    return json_response(True, '获取订单列表成功', {
        'items': [order.to_dict() for order in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    })

@admin_bp.route('/admin/users/<int:user_id>/reset_password', methods=['PUT'])
@admin_required
def reset_user_password(current_admin, user_id):
    """重置用户密码

    Args:
        user_id (int): 用户ID
        new_password (str): 新密码

    Returns:
        JSON: 重置结果
    """
    user = User.query.get_or_404(user_id)
    if user.is_deleted:
        return json_response(False, '用户不存在', status=404)

    data = request.get_json()
    if 'new_password' not in data or not isinstance(data['new_password'], str) or len(data['new_password']) < 6:
        return json_response(False, '缺少new_password字段或密码长度不足6位', status=400)

    user.password = data['new_password']
    try:
        db.session.commit()
        logger.info(f"Admin {current_admin.id} reset password for user {user_id}")
        return json_response(True, '密码重置成功')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Admin {current_admin.id} failed to reset password for user {user_id}: {str(e)}")
        return json_response(False, f'重置失败: {str(e)}', status=500)

@admin_bp.route('/admin/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(current_admin, user_id):
    """修改用户信息

    Args:
        user_id (int): 用户ID
        nickname (str, optional): 昵称
        phone (str, optional): 手机号
        email (str, optional): 邮箱
        avatar_url (str, optional): 头像URL

    Returns:
        JSON: 更新后的用户信息
    """
    user = User.query.get_or_404(user_id)
    if user.is_deleted:
        return json_response(False, '用户不存在', status=404)

    data = request.get_json()
    if not data:
        return json_response(False, '请求数据为空', status=400)

    allowed_fields = ['nickname', 'phone', 'email', 'avatar_url']
    for field in allowed_fields:
        if field in data:
            if field in ['nickname', 'phone'] and (not isinstance(data[field], str) or not data[field].strip()):
                return json_response(False, f'{field} 必须为非空字符串', status=400)
            setattr(user, field, data[field])

    try:
        db.session.commit()
        logger.info(f"Admin {current_admin.id} updated user {user_id}")
        return json_response(True, '用户信息更新成功', user.to_dict(include_sensitive=True))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Admin {current_admin.id} failed to update user {user_id}: {str(e)}")
        return json_response(False, f'更新失败: {str(e)}', status=500)