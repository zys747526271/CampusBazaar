"""公开接口：首页、商品列表/详情、评价、店铺、分类、搜索建议。"""
from __future__ import annotations

from flask import Blueprint, request
from sqlalchemy import func, select

from backend.constants import OrderStatus, ProductCondition, ProductStatus
from backend.errors import not_found
from backend.extensions import db
from backend.models import Comment, CommentLike, Favorite, Order, OrderItem, Product, Tag, User
from backend.services import catalog
from backend.services.serializers import (
    comment_view,
    delivery_options,
    pay_options,
    product_card,
    product_detail,
    tag_view,
    user_public,
)
from backend.utils.response import ok, page_args, page_result
from backend.utils.security import optional_user
from backend.utils.validators import normalize_keyword

bp = Blueprint("public", __name__, url_prefix="/api")


@bp.get("/meta/home")
def home():
    return ok(catalog.home_payload())


@bp.get("/meta/filters")
def filters():
    tags = (
        Tag.query.filter(Tag.is_active.is_(True), Tag.is_deleted.is_(False))
        .order_by(Tag.sort_order.asc(), Tag.id.asc())
        .all()
    )
    counts = dict(
        db.session.execute(
            select(Product.tag_id, func.count(Product.id))
            .where(
                Product.status == ProductStatus.APPROVED,
                Product.is_available.is_(True),
                Product.quantity > 0,
                Product.is_deleted.is_(False),
            )
            .group_by(Product.tag_id)
        ).all()
    )
    return ok(
        {
            "tags": [tag_view(t, int(counts.get(t.id, 0))) for t in tags],
            "conditions": list(ProductCondition.ALL),
            "delivery_types": delivery_options(),
            "pay_methods": pay_options(),
            "sorts": [
                {"value": "created_at", "label": "最新发布"},
                {"value": "price", "label": "价格"},
                {"value": "sales", "label": "销量"},
                {"value": "views", "label": "浏览量"},
            ],
        }
    )


@bp.get("/tags")
def list_tags():
    tags = (
        Tag.query.filter(Tag.is_active.is_(True), Tag.is_deleted.is_(False))
        .order_by(Tag.sort_order.asc(), Tag.id.asc())
        .all()
    )
    return ok({"items": [tag_view(t) for t in tags], "total": len(tags)})


@bp.get("/products")
def list_products():
    query = catalog.apply_filters(catalog.visible_query(), request.args)
    query = catalog.apply_sort(query, request.args)
    return ok(catalog.paginate_products(query))


@bp.get("/products/<int:product_id>")
def product_detail_api(product_id: int):
    product = Product.query.filter(Product.id == product_id, Product.is_deleted.is_(False)).first()
    if product is None:
        raise not_found("商品不存在或已删除")
    viewer = optional_user()
    is_owner = bool(viewer and viewer.id == product.seller_id)
    if not product.is_on_sale and not is_owner:
        raise not_found("商品已下架或已售罄")

    catalog.track_view(product, viewer)
    db.session.commit()

    stats = catalog.seller_stats(product.seller_id)
    data = product_detail(product, stats, viewer)
    data["rating"] = catalog.comment_summary(product.id)
    data["favorited"] = _is_favorited(product.id, viewer)
    data["seller"]["product_count"] = stats.get("on_sale_count", 0)
    data["seller"]["sold_count"] = stats.get("sold_count", 0)
    data["seller"]["comment_count"] = stats.get("comment_count", 0)
    data["related"] = [product_card(p, stats) for p in catalog.related_products(product, 8)]
    data["cart_quantity"] = _cart_quantity(viewer, product.id)
    return ok(data)


def _is_favorited(product_id: int, viewer) -> bool:
    if viewer is None:
        return False
    return db.session.query(Favorite.id).filter_by(user_id=viewer.id, product_id=product_id).first() is not None


def _cart_quantity(viewer, product_id: int) -> int:
    from backend.models import Cart

    if viewer is None:
        return 0
    row = Cart.query.filter_by(user_id=viewer.id, product_id=product_id).first()
    return row.quantity if row else 0


@bp.get("/products/<int:product_id>/related")
def product_related(product_id: int):
    product = Product.query.filter(Product.id == product_id).first()
    if product is None:
        raise not_found("商品不存在")
    stats = catalog.seller_stats_map([product.seller_id]).get(product.seller_id, {})
    return ok({"items": [product_card(p, stats) for p in catalog.related_products(product, 8)]})


@bp.get("/products/<int:product_id>/comments")
def product_comments(product_id: int):
    product = Product.query.filter(Product.id == product_id, Product.is_deleted.is_(False)).first()
    if product is None:
        raise not_found("商品不存在")
    query = Comment.query.filter(
        Comment.product_id == product_id, Comment.is_hidden.is_(False), Comment.is_deleted.is_(False)
    )
    sort = (request.args.get("sort") or "newest").lower()
    if sort == "rating":
        query = query.order_by(Comment.rating.desc(), Comment.id.desc())
    elif sort == "helpful":
        query = query.order_by(Comment.like_count.desc(), Comment.id.desc())
    else:
        query = query.order_by(Comment.created_at.desc(), Comment.id.desc())

    viewer = optional_user()
    page, per_page = page_args(default_per_page=10)
    total = query.order_by(None).count()
    rows = query.limit(per_page).offset((page - 1) * per_page).all()
    liked_ids = _liked_ids([c.id for c in rows], viewer)
    items = [comment_view(c, viewer, liked=c.id in liked_ids) for c in rows]
    result = page_result(items, total, page, per_page)
    return ok({"summary": catalog.comment_summary(product_id), **result})


def _liked_ids(comment_ids: list[int], viewer) -> set[int]:
    if viewer is None or not comment_ids:
        return set()
    rows = db.session.execute(
        select(CommentLike.comment_id).where(
            CommentLike.user_id == viewer.id, CommentLike.comment_id.in_(comment_ids)
        )
    ).all()
    return {row[0] for row in rows}


@bp.get("/shops/<int:seller_id>")
def shop_detail(seller_id: int):
    seller = User.query.filter(User.id == seller_id, User.is_deleted.is_(False)).first()
    if seller is None or not seller.is_seller:
        raise not_found("店铺不存在")
    stats = catalog.seller_stats(seller_id)
    total_sales = (
        db.session.query(func.coalesce(func.sum(Order.total_amount), 0))
        .filter(Order.seller_id == seller_id, Order.status == OrderStatus.DONE)
        .scalar()
        or 0
    )
    items_total = (
        db.session.query(func.coalesce(func.sum(OrderItem.quantity), 0))
        .join(Order, Order.id == OrderItem.order_id)
        .filter(Order.seller_id == seller_id, Order.status == OrderStatus.DONE)
        .scalar()
        or 0
    )
    data = user_public(seller)
    data.update(
        {
            "stats": {
                **stats,
                "total_sales": float(total_sales),
                "sold_items": int(items_total),
            }
        }
    )
    return ok(data)


@bp.get("/shops/<int:seller_id>/products")
def shop_products(seller_id: int):
    query = catalog.visible_query().filter(Product.seller_id == seller_id)
    query = catalog.apply_filters(query, request.args)
    query = catalog.apply_sort(query, request.args)
    return ok(catalog.paginate_products(query))


@bp.get("/search/suggest")
def search_suggest():
    keyword = normalize_keyword(request.args.get("keyword"))
    if not keyword:
        return ok({"keywords": [], "products": []})
    pattern = f"%{keyword}%"
    products = (
        catalog.visible_query()
        .filter(Product.name.ilike(pattern))
        .order_by(Product.sales.desc(), Product.views.desc())
        .limit(6)
        .all()
    )
    tags = (
        Tag.query.filter(Tag.name.ilike(pattern), Tag.is_active.is_(True), Tag.is_deleted.is_(False))
        .limit(4)
        .all()
    )
    return ok(
        {
            "keywords": [t.name for t in tags],
            "products": [
                {"id": p.id, "name": p.name, "price": float(p.price), "cover_image": p.cover_image}
                for p in products
            ],
        }
    )
