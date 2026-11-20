"""互动：收藏、浏览记录、评价、举报。"""
from __future__ import annotations

from flask import Blueprint, request

from backend.constants import Limits, MessageType, OrderStatus, ReportStatus, ReportTarget
from backend.errors import bad_request, conflict, forbidden, not_found
from backend.extensions import db
from backend.models import (
    BrowseHistory,
    Comment,
    CommentLike,
    Favorite,
    Order,
    Product,
    Report,
)
from backend.services import catalog
from backend.services.serializers import comment_view, product_card, report_view
from backend.utils import limiter
from backend.utils.common import iso
from backend.utils.notify import notify
from backend.utils.response import created, ok, paginate
from backend.utils.security import current_user, login_required
from backend.utils.validators import Payload

bp = Blueprint("interactions", __name__, url_prefix="/api")


# ------------------------------------------------------------------ 收藏
@bp.get("/favorites")
@login_required
def list_favorites():
    user = current_user()
    query = Favorite.query.filter_by(user_id=user.id).order_by(Favorite.created_at.desc())

    from backend.utils.response import page_args, page_result

    page, per_page = page_args(20)
    total = query.order_by(None).count()
    rows = query.limit(per_page).offset((page - 1) * per_page).all()
    products = [row.product for row in rows if row.product is not None]
    stats = catalog.seller_stats_map([p.seller_id for p in products])
    items = []
    for row in rows:
        if row.product is None:
            continue
        card = product_card(row.product, stats.get(row.product.seller_id))
        card["favorited_at"] = iso(row.created_at)
        items.append(card)
    return ok(page_result(items, total, page, per_page))


@bp.post("/favorites")
@login_required
def add_favorite():
    user = current_user()
    payload = Payload(request.get_json(silent=True))
    product_id = payload.integer("product_id", min_value=1, label="商品")
    payload.done()
    product = Product.query.filter(Product.id == product_id, Product.is_deleted.is_(False)).first()
    if product is None:
        raise not_found("商品不存在")
    if Favorite.query.filter_by(user_id=user.id, product_id=product_id).first():
        return ok({"favorited": True}, "已收藏")
    db.session.add(Favorite(user_id=user.id, product_id=product_id))
    db.session.commit()
    return ok({"favorited": True}, "已收藏")


@bp.delete("/favorites/<int:product_id>")
@login_required
def remove_favorite(product_id: int):
    user = current_user()
    row = Favorite.query.filter_by(user_id=user.id, product_id=product_id).first()
    if row is None:
        return ok({"favorited": False}, "已取消收藏")
    db.session.delete(row)
    db.session.commit()
    return ok({"favorited": False}, "已取消收藏")


# ------------------------------------------------------------------ 浏览记录
@bp.get("/history")
@login_required
def list_history():
    user = current_user()
    from backend.utils.response import page_args, page_result

    query = BrowseHistory.query.filter_by(user_id=user.id).order_by(BrowseHistory.viewed_at.desc())
    page, per_page = page_args(20)
    total = query.order_by(None).count()
    rows = [h for h in query.limit(per_page).offset((page - 1) * per_page).all() if h.product is not None]
    stats = catalog.seller_stats_map([h.product.seller_id for h in rows])
    items = [
        {**product_card(h.product, stats.get(h.product.seller_id)), "viewed_at": iso(h.viewed_at)}
        for h in rows
    ]
    return ok(page_result(items, total, page, per_page))


@bp.delete("/history")
@login_required
def clear_history():
    user = current_user()
    count = BrowseHistory.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    db.session.commit()
    return ok({"deleted": count}, "浏览记录已清空")


# ------------------------------------------------------------------ 评价
@bp.post("/comments")
@login_required
def create_comment():
    user = current_user()
    payload = Payload(request.get_json(silent=True))
    order_id = payload.integer("order_id", min_value=1, label="订单")
    product_id = payload.integer("product_id", min_value=1, label="商品")
    rating = payload.integer("rating", min_value=1, max_value=5, label="评分")
    content = payload.text("content", required=False, max_len=Limits.COMMENT_MAX_LEN, label="评价内容", default="")
    images = payload.str_list("images", max_items=3, max_len=255, label="评价图片")
    payload.done()

    order = Order.query.filter(Order.id == order_id).first()
    if order is None:
        raise not_found("订单不存在")
    if order.user_id != user.id:
        raise forbidden("只能评价自己购买的订单")
    if order.status != OrderStatus.DONE:
        raise conflict("订单完成后才能评价")
    item = next((i for i in order.items if i.product_id == product_id), None)
    if item is None:
        raise bad_request("该订单不包含此商品")
    if Comment.query.filter_by(order_id=order_id, product_id=product_id).first():
        raise bad_request("该商品已评价，不能重复评价")

    comment = Comment(
        order_id=order_id,
        product_id=product_id,
        user_id=user.id,
        rating=rating,
        content=content,
        images=images,
    )
    db.session.add(comment)
    notify(
        order.seller_id,
        MessageType.SYSTEM,
        "收到新的商品评价",
        f"《{item.name}》获得 {rating} 星评价。",
        f"/products/{product_id}",
    )
    db.session.commit()
    return created(comment_view(comment, user, with_product=True), "评价成功")


@bp.get("/comments/mine")
@login_required
def my_comments():
    user = current_user()
    query = Comment.query.filter(Comment.user_id == user.id, Comment.is_deleted.is_(False)).order_by(Comment.created_at.desc())
    return ok(paginate(query, lambda c: comment_view(c, user, with_product=True)))


@bp.post("/comments/<int:comment_id>/like")
@login_required
def toggle_like(comment_id: int):
    user = current_user()
    comment = Comment.query.filter(Comment.id == comment_id, Comment.is_deleted.is_(False)).first()
    if comment is None:
        raise not_found("评价不存在")
    row = CommentLike.query.filter_by(comment_id=comment_id, user_id=user.id).first()
    if row:
        db.session.delete(row)
        comment.like_count = max((comment.like_count or 0) - 1, 0)
        liked = False
    else:
        db.session.add(CommentLike(comment_id=comment_id, user_id=user.id))
        comment.like_count = (comment.like_count or 0) + 1
        liked = True
    db.session.commit()
    return ok({"liked": liked, "like_count": comment.like_count})


@bp.delete("/comments/<int:comment_id>")
@login_required
def delete_comment(comment_id: int):
    user = current_user()
    comment = Comment.query.filter(Comment.id == comment_id, Comment.is_deleted.is_(False)).first()
    if comment is None:
        raise not_found("评价不存在")
    if comment.user_id != user.id:
        raise forbidden("只能删除自己的评价")
    comment.is_deleted = True
    db.session.commit()
    return ok(None, "评价已删除")


# ------------------------------------------------------------------ 举报
@bp.post("/reports")
@login_required
def create_report():
    user = current_user()
    limiter.by_user("report", Limits.RATE_REPORT, "举报过于频繁，请稍后再试")

    payload = Payload(request.get_json(silent=True))
    target_type = payload.choice("target_type", ReportTarget.ALL, label="举报对象")
    target_id = payload.integer("target_id", min_value=1, label="对象 ID")
    reason = payload.text("reason", min_len=2, max_len=60, label="举报原因")
    detail = payload.text("detail", required=False, max_len=500, label="补充说明")
    payload.done()

    if Report.query.filter_by(
        reporter_id=user.id, target_type=target_type, target_id=target_id, status=ReportStatus.PENDING
    ).first():
        raise bad_request("你已举报过该对象，请等待处理")

    _ensure_target_exists(target_type, target_id)
    report = Report(
        reporter_id=user.id,
        target_type=target_type,
        target_id=target_id,
        reason=reason,
        detail=detail,
    )
    db.session.add(report)
    db.session.commit()
    return created(report_view(report), "举报已提交，管理员会尽快处理")


def _ensure_target_exists(target_type: str, target_id: int) -> None:
    if target_type == ReportTarget.PRODUCT:
        exists = Product.query.filter(Product.id == target_id, Product.is_deleted.is_(False)).first()
    elif target_type == ReportTarget.COMMENT:
        exists = Comment.query.filter(Comment.id == target_id, Comment.is_deleted.is_(False)).first()
    else:
        from backend.models import User

        exists = User.query.filter(User.id == target_id, User.is_deleted.is_(False)).first()
    if exists is None:
        raise not_found("举报对象不存在")
