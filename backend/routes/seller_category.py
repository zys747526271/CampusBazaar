"""卖家自定义分类：每个卖家只能管理自己的分类。"""
from flask import Blueprint, request, current_app
from ..models import db, SellerCategory, Product
from ..utils.decorators import login_required
import logging

seller_category_bp = Blueprint('seller_category', __name__)
logger = logging.getLogger(__name__)


def json_response(success, message, data=None, status=200):
    return jsonify_response(success, message, data, status)


def jsonify_response(success, message, data, status):
    from flask import jsonify
    return jsonify({'success': success, 'message': message, 'data': data}), status


def _require_seller(current_user):
    if not current_user.is_seller:
        return json_response(False, '尚未开通卖家身份', status=403)
    return None


@seller_category_bp.route('/seller/categories', methods=['GET'])
@login_required
def list_categories(current_user):
    err = _require_seller(current_user)
    if err:
        return err
    items = SellerCategory.query.filter_by(
        seller_id=current_user.id, is_deleted=False
    ).order_by(SellerCategory.sort_order, SellerCategory.id).all()
    return json_response(True, '获取分类成功', [c.to_dict() for c in items])


@seller_category_bp.route('/seller/categories', methods=['POST'])
@login_required
def create_category(current_user):
    err = _require_seller(current_user)
    if err:
        return err
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name or len(name) > 50:
        return json_response(False, '分类名称必须为 1-50 个字符', status=400)
    if SellerCategory.query.filter_by(
            seller_id=current_user.id, name=name, is_deleted=False).first():
        return json_response(False, '该分类已存在', status=400)
    category = SellerCategory(
        seller_id=current_user.id, name=name,
        sort_order=int(data.get('sort_order') or 0))
    try:
        db.session.add(category)
        db.session.commit()
        return json_response(True, '分类创建成功', category.to_dict(), 201)
    except Exception as e:
        db.session.rollback()
        logger.error(f'卖家 {current_user.id} 创建分类失败: {e}')
        return json_response(False, f'创建失败: {e}', status=500)


@seller_category_bp.route('/seller/categories/<int:category_id>', methods=['PUT'])
@login_required
def update_category(current_user, category_id):
    err = _require_seller(current_user)
    if err:
        return err
    category = SellerCategory.query.filter_by(
        id=category_id, seller_id=current_user.id, is_deleted=False).first_or_404()
    data = request.get_json() or {}
    if 'name' in data:
        name = (data['name'] or '').strip()
        if not name or len(name) > 50:
            return json_response(False, '分类名称必须为 1-50 个字符', status=400)
        dup = SellerCategory.query.filter_by(
            seller_id=current_user.id, name=name, is_deleted=False).first()
        if dup and dup.id != category.id:
            return json_response(False, '该分类已存在', status=400)
        category.name = name
    if 'sort_order' in data:
        category.sort_order = int(data['sort_order'] or 0)
    try:
        db.session.commit()
        return json_response(True, '分类更新成功', category.to_dict())
    except Exception as e:
        db.session.rollback()
        return json_response(False, f'更新失败: {e}', status=500)


@seller_category_bp.route('/seller/categories/<int:category_id>', methods=['DELETE'])
@login_required
def delete_category(current_user, category_id):
    err = _require_seller(current_user)
    if err:
        return err
    category = SellerCategory.query.filter_by(
        id=category_id, seller_id=current_user.id, is_deleted=False).first_or_404()
    in_use = Product.query.filter_by(
        seller_id=current_user.id, seller_category_id=category_id,
        is_deleted=False).count()
    if in_use:
        return json_response(False, f'该分类下还有 {in_use} 件商品，请先转移商品', status=400)
    category.is_deleted = True
    try:
        db.session.commit()
        return json_response(True, '分类已删除')
    except Exception as e:
        db.session.rollback()
        return json_response(False, f'删除失败: {e}', status=500)
