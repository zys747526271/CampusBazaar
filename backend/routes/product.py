from flask import Blueprint, request, jsonify, current_app
from ..models import db, Product, User
from ..utils.decorators import token_required, admin_required
from ..utils.file_upload import save_file
from ..utils.recommender import get_recommended_products, get_hot_products
from sqlalchemy import desc
import logging

product_bp = Blueprint('product', __name__)
logger = logging.getLogger(__name__)


def _cache():
    """使用 app 已初始化的缓存实例（避免自建未 init 的 Cache 导致 500）。"""
    return current_app.extensions['cache']

def json_response(success, message, data=None, status=200):
    """统一响应格式"""
    return jsonify({'success': success, 'message': message, 'data': data}), status

@product_bp.route('/', methods=['GET'])
def get_products():
    """获取商品列表，支持分页、排序和搜索。

    仅展示审核通过且上架的商品（status='已通过'）。
    """
    page = max(1, request.args.get('page', 1, type=int))
    per_page = max(1, min(100, request.args.get('per_page', 10, type=int)))
    sort_by = request.args.get('sort_by', 'created_at')
    order = request.args.get('order', 'desc').lower()
    search = request.args.get('search', '').strip()
    # 兼容前端 category_id / tag_id 两种写法，实际字段是 tag_id
    tag_id = request.args.get('tag_id', type=int) or request.args.get('category_id', type=int)

    query = Product.query.filter_by(is_deleted=False, status='已通过', is_available=True)
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))
    if tag_id:
        query = query.filter_by(tag_id=tag_id)

    if hasattr(Product, sort_by):
        sort_attr = getattr(Product, sort_by)
        query = query.order_by(desc(sort_attr) if order == 'desc' else sort_attr)
    else:
        query = query.order_by(desc(Product.created_at))

    pagination = query.paginate(page=page, per_page=per_page)
    logger.info(f"获取商品列表 page={page} search={search}")
    return json_response(True, '获取商品列表成功', {
        'items': [p.to_dict(with_seller=True) for p in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    })

@product_bp.route('/<int:product_id>', methods=['GET'])
def get_product(product_id):
    """获取商品详情

    Args:
        product_id (int): 商品ID

    Returns:
        JSON: 商品信息
    """
    product = Product.query.filter_by(id=product_id, is_deleted=False).first()
    if not product:
        return json_response(False, '商品不存在', status=404)

    product.views += 1
    try:
        db.session.commit()
        logger.info(f"Fetched product {product_id}, views incremented")
        return json_response(True, '获取商品详情成功', product.to_dict(with_seller=True))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to increment views for product {product_id}: {str(e)}")
        return json_response(False, f'获取详情失败: {str(e)}', status=500)

@product_bp.route('/', methods=['POST'])
@token_required
def create_product(current_user):
    """创建商品

    Args:
        name (str): 商品名称
        price (float): 价格
        description (str): 描述
        category_id (int): 分类ID
        quantity (int, optional): 库存，默认1

    Returns:
        JSON: 新商品信息
    """
    from ..models import Tag
    data = request.get_json()
    required_fields = ['name', 'price', 'description']
    if not data or not all(field in data for field in required_fields):
        return json_response(False, f'缺少必填字段: {", ".join(required_fields)}', status=400)

    try:
        price = float(data['price'])
        if price < 0:
            raise ValueError
        quantity = int(data.get('quantity', 1))
        if quantity < 0:
            raise ValueError
    except ValueError:
        return json_response(False, 'price 必须为非负数，quantity 必须为非负整数', status=400)

    if not isinstance(data['name'], str) or not data['name'].strip():
        return json_response(False, 'name 必须为非空字符串', status=400)

    # 分类可选：兼容 tag_id / category_id；未指定则用第一个可用标签
    tag_id = data.get('tag_id') or data.get('category_id')
    if tag_id is None:
        first_tag = Tag.query.filter_by(is_deleted=False).first()
        tag_id = first_tag.id if first_tag else None

    # 卖家自定义分类：必须属于当前卖家本人，防止越权绑定他人分类
    seller_category_id = data.get('seller_category_id')
    if seller_category_id:
        from ..models import SellerCategory
        own = SellerCategory.query.filter_by(
            id=int(seller_category_id), seller_id=current_user.id,
            is_deleted=False).first()
        if not own:
            return json_response(False, '卖家分类不存在或不属于当前账号', status=400)
        seller_category_id = own.id
    else:
        seller_category_id = None

    # 本地/开发模式商品直接通过审核，便于演示；生产模式需管理员审核
    from flask import current_app
    initial_status = '待审核' if current_app.config.get('CAPTCHA_MODE') == 'prod' else '已通过'
    product = Product(
        quick_id=f'P{__import__("uuid").uuid4().hex[:8].upper()}',
        name=data['name'],
        price=price,
        description=data['description'],
        tag_id=tag_id,
        seller_category_id=seller_category_id,
        seller_id=current_user.id,
        quantity=quantity,
        status=initial_status
    )
    if isinstance(data.get('images'), list):
        product.image_list = [str(u) for u in data['images'] if u]

    try:
        db.session.add(product)
        db.session.commit()
        logger.info(f"User {current_user.id} created product {product.id}")
        return json_response(True, '创建商品成功', product.to_dict(), 201)
    except Exception as e:
        db.session.rollback()
        logger.error(f"User {current_user.id} failed to create product: {str(e)}")
        return json_response(False, f'创建失败: {str(e)}', status=500)

@product_bp.route('/<int:product_id>', methods=['PUT'])
@token_required
def update_product(current_user, product_id):
    """更新商品信息

    Args:
        product_id (int): 商品ID
        name (str, optional): 新名称
        price (float, optional): 新价格
        description (str, optional): 新描述
        quantity (int, optional): 新库存
        category_id (int, optional): 新分类ID

    Returns:
        JSON: 更新后的商品信息
    """
    product = Product.query.filter_by(id=product_id, is_deleted=False).first()
    if not product:
        return json_response(False, '商品不存在', status=404)

    is_admin = getattr(current_user, 'is_admin', False)
    if product.seller_id != current_user.id and not is_admin:
        return json_response(False, '无权限修改此商品', status=403)

    data = request.get_json()
    if not data:
        return json_response(False, '请求数据为空', status=400)

    # 兼容前端 category_id 写法，内部字段是 tag_id
    if 'category_id' in data and 'tag_id' not in data:
        data['tag_id'] = data['category_id']
    allowed_fields = ['name', 'price', 'description', 'quantity', 'tag_id', 'seller_category_id']
    if isinstance(data.get('images'), list):
        product.image_list = [str(u) for u in data['images'] if u]
    if 'seller_category_id' in data and data['seller_category_id']:
        from ..models import SellerCategory
        own = SellerCategory.query.filter_by(
            id=int(data['seller_category_id']), seller_id=current_user.id,
            is_deleted=False).first()
        if not own:
            return json_response(False, '卖家分类不存在或不属于当前账号', status=400)
        data['seller_category_id'] = own.id
    for field in allowed_fields:
        if field in data:
            if field == 'price':
                try:
                    value = float(data[field])
                    if value < 0:
                        raise ValueError
                except ValueError:
                    return json_response(False, 'price 必须为非负数', status=400)
                setattr(product, field, value)
            elif field == 'quantity':
                try:
                    value = int(data[field])
                    if value < 0:
                        raise ValueError
                except ValueError:
                    return json_response(False, 'quantity 必须为非负整数', status=400)
                setattr(product, field, value)
            elif field in ['name', 'description'] and (not isinstance(data[field], str) or not data[field].strip()):
                return json_response(False, f'{field} 必须为非空字符串', status=400)
            else:
                setattr(product, field, data[field])

    try:
        db.session.commit()
        logger.info(f"User {current_user.id} updated product {product_id}")
        return json_response(True, '更新商品成功', product.to_dict())
    except Exception as e:
        db.session.rollback()
        logger.error(f"User {current_user.id} failed to update product {product_id}: {str(e)}")
        return json_response(False, f'更新失败: {str(e)}', status=500)

@product_bp.route('/upload-images', methods=['POST'])
@token_required
def upload_images_standalone(current_user):
    """发布前先上传图片，返回 URL 列表（无需商品 ID）。"""
    if 'images' not in request.files:
        return json_response(False, '没有上传文件', status=400)
    urls = []
    for image in request.files.getlist('images'):
        if image.filename:
            try:
                urls.append(save_file(image))
            except Exception as e:
                logger.error(f'上传图片失败: {e}')
                return json_response(False, f'上传图片失败: {e}', status=500)
    return json_response(True, '上传图片成功', {'urls': urls})


@product_bp.route('/<int:product_id>/images', methods=['POST'])
@token_required
def upload_product_images(current_user, product_id):
    """上传商品图片

    Args:
        product_id (int): 商品ID
        images (files): 图片文件列表

    Returns:
        JSON: 上传的图片URL列表
    """
    product = Product.query.filter_by(id=product_id, is_deleted=False).first()
    if not product:
        return json_response(False, '商品不存在', status=404)

    is_admin = getattr(current_user, 'is_admin', False)
    if product.seller_id != current_user.id and not is_admin:
        return json_response(False, '无权限上传图片', status=403)

    if 'images' not in request.files:
        return json_response(False, '没有上传文件', status=400)

    images = request.files.getlist('images')
    image_urls = []
    for image in images:
        if image.filename:
            try:
                image_url = save_file(image)
                image_urls.append(image_url)
            except Exception as e:
                logger.error(f"Failed to save image for product {product_id}: {str(e)}")
                return json_response(False, f'上传图片失败: {str(e)}', status=500)

    if image_urls:
        # 模型用 images（JSON 字符串）存储，通过 image_list 属性读写
        existing = product.image_list
        product.image_list = existing + image_urls
        try:
            db.session.commit()
            logger.info(f"User {current_user.id} uploaded images for product {product_id}")
            return json_response(True, '上传图片成功', {'image_urls': product.image_list})
        except Exception as e:
            db.session.rollback()
            logger.error(f"User {current_user.id} failed to upload images for product {product_id}: {str(e)}")
            return json_response(False, f'上传失败: {str(e)}', status=500)

    return json_response(False, '没有有效图片上传', status=400)

@product_bp.route('/<int:product_id>', methods=['DELETE'])
@token_required
def delete_product(current_user, product_id):
    """删除商品（软删除）

    Args:
        product_id (int): 商品ID

    Returns:
        JSON: 删除结果
    """
    product = Product.query.filter_by(id=product_id, is_deleted=False).first()
    if not product:
        return json_response(False, '商品不存在', status=404)

    is_admin = getattr(current_user, 'is_admin', False)
    if product.seller_id != current_user.id and not is_admin:
        return json_response(False, '无权限删除此商品', status=403)

    product.is_deleted = True
    try:
        db.session.commit()
        logger.info(f"User {current_user.id} deleted product {product_id}")
        return json_response(True, '商品已删除')
    except Exception as e:
        db.session.rollback()
        logger.error(f"User {current_user.id} failed to delete product {product_id}: {str(e)}")
        return json_response(False, f'删除失败: {str(e)}', status=500)

@product_bp.route('/<int:product_id>/status', methods=['PUT'])
@admin_required
def update_product_status(current_admin, product_id):
    """更新商品状态（管理员）

    Args:
        product_id (int): 商品ID
        status (str): 新状态（pending/approved/rejected）

    Returns:
        JSON: 更新结果
    """
    product = Product.query.filter_by(id=product_id, is_deleted=False).first()
    if not product:
        return json_response(False, '商品不存在', status=404)

    data = request.get_json()
    if 'status' not in data:
        return json_response(False, '缺少status字段', status=400)

    # 统一为中文枚举（与模型一致），同时兼容旧的英文入参
    status_map = {'pending': '待审核', 'approved': '已通过', 'rejected': '已下架',
                  '待审核': '待审核', '已通过': '已通过', '已下架': '已下架'}
    new_status = status_map.get(data['status'])
    if not new_status:
        return json_response(False, '非法的状态值，可用值: 待审核/已通过/已下架', status=400)

    product.status = new_status
    product.is_available = (new_status == '已通过')
    try:
        db.session.commit()
        logger.info(f"Admin {current_admin.id} updated product {product_id} status to {data['status']}")
        return json_response(True, '商品状态更新成功', {'status': product.status})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Admin {current_admin.id} failed to update product {product_id} status: {str(e)}")
        return json_response(False, f'更新失败: {str(e)}', status=500)

def _login_user_id():
    """尝试从令牌解析用户ID，未登录或无效时返回 None（不抛异常）。"""
    from ..utils.decorators import get_token_from_header, verify_token
    token = get_token_from_header()
    if not token:
        return None
    try:
        payload = verify_token(token)
        return payload.get('user_id') if payload.get('type') == 'user' else None
    except Exception:
        return None


@product_bp.route('/recommended', methods=['GET'])
def get_recommended_products_route():
    """获取推荐商品：登录用户按偏好推荐，未登录用户展示热门商品。"""
    limit = max(1, min(50, request.args.get('limit', 10, type=int)))
    try:
        user_id = _login_user_id()
        products = get_recommended_products(user_id, limit) if user_id else get_hot_products(limit)
        return json_response(True, '获取推荐商品成功', {'items': [p.to_dict(with_seller=True) for p in products]})
    except Exception as e:
        logger.error(f"获取推荐商品失败: {str(e)}")
        return json_response(False, f'获取失败: {str(e)}', status=500)


@product_bp.route('/hot', methods=['GET'])
def get_hot_products_route():
    """获取热门商品（免登录，供主页浏览）。"""
    limit = max(1, min(50, request.args.get('limit', 10, type=int)))
    try:
        products = get_hot_products(limit)
        return json_response(True, '获取热门商品成功', {'items': [p.to_dict(with_seller=True) for p in products]})
    except Exception as e:
        logger.error(f"获取热门商品失败: {str(e)}")
        return json_response(False, f'获取失败: {str(e)}', status=500)
