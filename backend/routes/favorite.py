"""收藏与浏览记录路由。"""
from flask import Blueprint, request
from ..models import db, Favorite, BrowseHistory, Product
from ..utils.decorators import login_required
import logging

favorite_bp = Blueprint('favorite', __name__)
logger = logging.getLogger(__name__)


def json_response(success, message, data=None, status=200):
    return jsonify_data(success, message, data, status)


from flask import jsonify
def jsonify_data(success, message, data=None, status=200):
    return jsonify({'success': success, 'message': message, 'data': data}), status


# ---------------- 收藏 ----------------
@favorite_bp.route('/favorites', methods=['GET'])
@login_required
def list_favorites(current_user):
    items = Favorite.query.filter_by(user_id=current_user.id).order_by(Favorite.created_at.desc()).all()
    return json_response(True, '获取收藏成功', [f.to_dict() for f in items])


@favorite_bp.route('/favorites/<int:product_id>', methods=['POST'])
@login_required
def add_favorite(current_user, product_id):
    product = Product.query.filter_by(id=product_id, is_deleted=False).first()
    if not product:
        return json_response(False, '商品不存在', status=404)
    if Favorite.query.filter_by(user_id=current_user.id, product_id=product_id).first():
        return json_response(True, '已收藏')
    db.session.add(Favorite(user_id=current_user.id, product_id=product_id))
    try:
        db.session.commit()
        return json_response(True, '收藏成功', {'product_id': product_id}, 201)
    except Exception as e:
        db.session.rollback()
        return json_response(False, f'收藏失败: {str(e)}', status=500)


@favorite_bp.route('/favorites/<int:product_id>', methods=['DELETE'])
@login_required
def remove_favorite(current_user, product_id):
    fav = Favorite.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if not fav:
        return json_response(False, '未收藏该商品', status=404)
    db.session.delete(fav)
    try:
        db.session.commit()
        return json_response(True, '已取消收藏')
    except Exception as e:
        db.session.rollback()
        return json_response(False, f'取消收藏失败: {str(e)}', status=500)


@favorite_bp.route('/favorites/<int:product_id>/check', methods=['GET'])
@login_required
def check_favorite(current_user, product_id):
    exists = Favorite.query.filter_by(user_id=current_user.id, product_id=product_id).first() is not None
    return json_response(True, '查询成功', {'is_favorite': exists})


# ---------------- 浏览记录 ----------------
@favorite_bp.route('/history', methods=['GET'])
@login_required
def list_history(current_user):
    items = BrowseHistory.query.filter_by(user_id=current_user.id).order_by(BrowseHistory.viewed_at.desc()).all()
    return json_response(True, '获取浏览记录成功', [h.to_dict() for h in items])


@favorite_bp.route('/history/<int:product_id>', methods=['POST'])
@login_required
def record_history(current_user, product_id):
    product = Product.query.filter_by(id=product_id, is_deleted=False).first()
    if not product:
        return json_response(False, '商品不存在', status=404)
    from datetime import datetime
    item = BrowseHistory.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if item:
        item.viewed_at = datetime.utcnow()
    else:
        db.session.add(BrowseHistory(user_id=current_user.id, product_id=product_id))
    try:
        db.session.commit()
        return json_response(True, '记录成功')
    except Exception as e:
        db.session.rollback()
        return json_response(False, f'记录失败: {str(e)}', status=500)


@favorite_bp.route('/history', methods=['DELETE'])
@login_required
def clear_history(current_user):
    BrowseHistory.query.filter_by(user_id=current_user.id).delete(synchronize_session=False)
    try:
        db.session.commit()
        return json_response(True, '浏览记录已清空')
    except Exception as e:
        db.session.rollback()
        return json_response(False, f'清空失败: {str(e)}', status=500)
