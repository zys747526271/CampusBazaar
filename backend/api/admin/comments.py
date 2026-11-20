"""后台评价管理：全站检索、隐藏/恢复、删除。"""
from __future__ import annotations

from flask import Blueprint, request
from sqlalchemy import or_

from backend.api.admin import bp
from backend.constants import AuditAction, MessageType
from backend.errors import not_found
from backend.extensions import db
from backend.models import Comment, Product
from backend.services.serializers import comment_view
from backend.utils.audit import record
from backend.utils.notify import notify
from backend.utils.response import ok, page_args, page_result
from backend.utils.security import admin_required
from backend.utils.validators import Payload


@bp.get("/comments")
@admin_required
def list_comments():
    query = Comment.query.filter(Comment.is_deleted.is_(False))
    keyword = (request.args.get("keyword") or "").strip()
    if keyword:
        like = f"%{keyword}%"
        query = query.join(Product, Product.id == Comment.product_id).filter(
            or_(Comment.content.ilike(like), Product.name.ilike(like))
        )
    product_id = request.args.get("product_id", type=int)
    if product_id:
        query = query.filter(Comment.product_id == product_id)
    user_id = request.args.get("user_id", type=int)
    if user_id:
        query = query.filter(Comment.user_id == user_id)
    visibility = (request.args.get("visibility") or "").strip()
    if visibility == "hidden":
        query = query.filter(Comment.is_hidden.is_(True))
    elif visibility == "visible":
        query = query.filter(Comment.is_hidden.is_(False))
    query = query.order_by(Comment.created_at.desc())

    page, per_page = page_args(20)
    total = query.order_by(None).count()
    rows = query.limit(per_page).offset((page - 1) * per_page).all()
    items = []
    for comment in rows:
        item = comment_view(comment, with_product=True)
        item["order_id"] = comment.order_id
        items.append(item)
    return ok(page_result(items, total, page, per_page))


@bp.put("/comments/<int:comment_id>/visibility")
@admin_required
def set_visibility(comment_id: int):
    comment = Comment.query.filter(Comment.id == comment_id, Comment.is_deleted.is_(False)).first()
    if comment is None:
        raise not_found("评价不存在")
    payload = Payload(request.get_json(silent=True))
    hidden = payload.boolean("hidden", default=True)
    reason = payload.text("reason", required=False, max_len=200, label="原因")
    payload.done()

    comment.is_hidden = hidden
    record(AuditAction.COMMENT_HIDE if hidden else AuditAction.COMMENT_RESTORE, "comment", comment.id, reason)
    notify(
        comment.user_id,
        MessageType.AUDIT,
        "评价被隐藏" if hidden else "评价已恢复",
        reason or ("评价含违规内容，已被管理员隐藏。" if hidden else "你的评价已重新展示。"),
        f"/products/{comment.product_id}",
    )
    db.session.commit()
    return ok(comment_view(comment, with_product=True), "已隐藏" if hidden else "已恢复")


@bp.delete("/comments/<int:comment_id>")
@admin_required
def delete_comment(comment_id: int):
    comment = Comment.query.filter(Comment.id == comment_id, Comment.is_deleted.is_(False)).first()
    if comment is None:
        raise not_found("评价不存在")
    comment.is_deleted = True
    record(AuditAction.COMMENT_DELETE, "comment", comment.id, "")
    db.session.commit()
    return ok(None, "评价已删除")
