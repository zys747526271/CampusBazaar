"""后台站点配置：平台分类（Tag）与首页轮播（Banner）。"""
from __future__ import annotations

from flask import Blueprint, request
from sqlalchemy import func, select

from backend.api.admin import bp
from backend.constants import AuditAction
from backend.errors import bad_request, not_found
from backend.extensions import db
from backend.models import Banner, Product, Tag
from backend.services.serializers import banner_view, tag_view
from backend.utils.audit import record
from backend.utils.response import created, ok
from backend.utils.security import admin_required
from backend.utils.validators import Payload


# ------------------------------------------------------------------ 平台分类
@bp.get("/tags")
@admin_required
def list_tags():
    rows = Tag.query.filter(Tag.is_deleted.is_(False)).order_by(Tag.sort_order.asc(), Tag.id.asc()).all()
    counts = dict(
        db.session.execute(
            select(Product.tag_id, func.count(Product.id))
            .where(Product.is_deleted.is_(False))
            .group_by(Product.tag_id)
        ).all()
    )
    return ok({"items": [tag_view(t, int(counts.get(t.id, 0))) for t in rows], "total": len(rows)})


@bp.post("/tags")
@admin_required
def create_tag():
    payload = Payload(request.get_json(silent=True))
    name = payload.text("name", min_len=1, max_len=20, label="分类名称")
    icon = payload.text("icon", required=False, max_len=30, label="图标")
    description = payload.text("description", required=False, max_len=120, label="描述")
    sort_order = payload.integer("sort_order", required=False, default=0, label="排序")
    is_active = payload.boolean("is_active", default=True)
    payload.done()

    if Tag.query.filter(Tag.name == name, Tag.is_deleted.is_(False)).first():
        raise bad_request("分类名称已存在", {"name": "名称重复"})
    tag = Tag(name=name, icon=icon, description=description, sort_order=sort_order, is_active=is_active)
    db.session.add(tag)
    record(AuditAction.TAG_CREATE, "tag", name, name)
    db.session.commit()
    return created(tag_view(tag, 0), "分类已创建")


@bp.put("/tags/<int:tag_id>")
@admin_required
def update_tag(tag_id: int):
    tag = Tag.query.filter(Tag.id == tag_id, Tag.is_deleted.is_(False)).first()
    if tag is None:
        raise not_found("分类不存在")
    payload = Payload(request.get_json(silent=True))
    name = payload.text("name", required=False, max_len=20, label="分类名称", default=tag.name)
    icon = payload.text("icon", required=False, max_len=30, label="图标", default=tag.icon)
    description = payload.text("description", required=False, max_len=120, label="描述", default=tag.description)
    sort_order = payload.integer("sort_order", required=False, default=tag.sort_order, label="排序")
    is_active = payload.boolean("is_active", default=tag.is_active)
    payload.done()

    duplicate = Tag.query.filter(Tag.name == name, Tag.id != tag.id, Tag.is_deleted.is_(False)).first()
    if duplicate:
        raise bad_request("分类名称已存在", {"name": "名称重复"})
    tag.name = name
    tag.icon = icon
    tag.description = description
    tag.sort_order = sort_order
    tag.is_active = is_active
    record(AuditAction.TAG_UPDATE, "tag", tag.id, name)
    db.session.commit()
    return ok(tag_view(tag), "分类已更新")


@bp.delete("/tags/<int:tag_id>")
@admin_required
def delete_tag(tag_id: int):
    tag = Tag.query.filter(Tag.id == tag_id, Tag.is_deleted.is_(False)).first()
    if tag is None:
        raise not_found("分类不存在")
    used = Product.query.filter(Product.tag_id == tag.id, Product.is_deleted.is_(False)).count()
    if used:
        # 历史商品仍需可打开：软删除并改名释放唯一约束（PRD FR-CAT-04）
        tag.is_deleted = True
        tag.is_active = False
        tag.name = f"{tag.name[:18]}-del{tag.id}"
    else:
        db.session.delete(tag)
    record(AuditAction.TAG_DELETE, "tag", tag_id, f"关联商品 {used} 件")
    db.session.commit()
    return ok({"soft_deleted": bool(used), "affected_products": used}, "分类已删除")


# ------------------------------------------------------------------ 轮播
@bp.get("/banners")
@admin_required
def list_banners():
    rows = Banner.query.order_by(Banner.sort_order.asc(), Banner.id.asc()).all()
    return ok({"items": [banner_view(b) for b in rows], "total": len(rows)})


def _apply_banner(banner: Banner, payload: Payload) -> None:
    banner.title = payload.text("title", min_len=1, max_len=60, label="标题")
    banner.subtitle = payload.text("subtitle", required=False, max_len=120, label="副标题")
    banner.image_url = payload.text("image_url", min_len=1, max_len=255, label="图片")
    banner.link_url = payload.text("link_url", required=False, max_len=255, label="跳转链接")
    banner.sort_order = payload.integer("sort_order", required=False, default=banner.sort_order, label="排序")
    banner.is_active = payload.boolean("is_active", default=banner.is_active)


@bp.post("/banners")
@admin_required
def create_banner():
    payload = Payload(request.get_json(silent=True))
    banner = Banner(image_url="", is_active=True, sort_order=0)
    _apply_banner(banner, payload)
    payload.done()
    db.session.add(banner)
    db.session.flush()
    record(AuditAction.BANNER_CREATE, "banner", banner.id, banner.title)
    db.session.commit()
    return created(banner_view(banner), "轮播已创建")


@bp.put("/banners/<int:banner_id>")
@admin_required
def update_banner(banner_id: int):
    banner = Banner.query.filter(Banner.id == banner_id).first()
    if banner is None:
        raise not_found("轮播不存在")
    payload = Payload(request.get_json(silent=True))
    _apply_banner(banner, payload)
    payload.done()
    record(AuditAction.BANNER_UPDATE, "banner", banner.id, banner.title)
    db.session.commit()
    return ok(banner_view(banner), "轮播已更新")


@bp.delete("/banners/<int:banner_id>")
@admin_required
def delete_banner(banner_id: int):
    banner = Banner.query.filter(Banner.id == banner_id).first()
    if banner is None:
        raise not_found("轮播不存在")
    db.session.delete(banner)
    record(AuditAction.BANNER_DELETE, "banner", banner_id, banner.title)
    db.session.commit()
    return ok(None, "轮播已删除")
