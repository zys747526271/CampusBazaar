"""后台内容治理：举报处理、操作审计、数据导出。"""
from __future__ import annotations

import csv
import io
from datetime import datetime

from flask import Blueprint, Response, request

from backend.api.admin import bp
from backend.constants import AuditAction, MessageType, ProductStatus, ReportStatus, ReportTarget
from backend.errors import bad_request, not_found
from backend.extensions import db
from backend.models import AuditLog, Comment, Order, Product, Report, User
from backend.services.serializers import audit_view, product_card, report_view
from backend.utils.audit import record
from backend.utils.common import iso, mask_phone, utcnow
from backend.utils.notify import notify
from backend.utils.response import ok, page_args, page_result
from backend.utils.security import admin_required, current_admin
from backend.utils.validators import Payload


# ------------------------------------------------------------------ 举报
def _target_summary(report: Report) -> dict:
    if report.target_type == ReportTarget.PRODUCT:
        product = Product.query.filter(Product.id == report.target_id).first()
        if product:
            return {"type": "product", "id": product.id, "title": product.name, "status": product.status,
                    "seller_id": product.seller_id}
    elif report.target_type == ReportTarget.COMMENT:
        comment = Comment.query.filter(Comment.id == report.target_id).first()
        if comment:
            return {"type": "comment", "id": comment.id, "title": (comment.content or "")[:60],
                    "hidden": comment.is_hidden, "product_id": comment.product_id}
    elif report.target_type == ReportTarget.USER:
        user = User.query.filter(User.id == report.target_id).first()
        if user:
            return {"type": "user", "id": user.id, "title": user.nickname, "banned": user.is_banned}
    return {"type": report.target_type, "id": report.target_id, "title": "对象已删除"}


@bp.get("/reports")
@admin_required
def list_reports():
    query = Report.query
    status = (request.args.get("status") or ReportStatus.PENDING).strip()
    if status in ReportStatus.ALL:
        query = query.filter(Report.status == status)
    query = query.order_by(Report.created_at.desc())
    page, per_page = page_args(20)
    total = query.order_by(None).count()
    rows = query.limit(per_page).offset((page - 1) * per_page).all()
    items = [report_view(r, _target_summary(r)) for r in rows]
    return ok(page_result(items, total, page, per_page))


@bp.put("/reports/<int:report_id>")
@admin_required
def handle_report(report_id: int):
    report = Report.query.filter(Report.id == report_id).first()
    if report is None:
        raise not_found("举报不存在")
    payload = Payload(request.get_json(silent=True))
    status = payload.choice("status", (ReportStatus.RESOLVED, ReportStatus.REJECTED), label="处理结果")
    result = payload.text("result", required=False, max_len=200, label="处理说明")
    action = payload.text("action", required=False, max_len=30, label="处置动作", default="none")
    payload.done()
    if status == ReportStatus.RESOLVED and not result and action == "none":
        raise bad_request("请填写处理说明或选择处置动作", {"result": "处理说明不能为空"})

    if action == "hide_comment":
        comment = Comment.query.filter(Comment.id == report.target_id).first()
        if comment:
            comment.is_hidden = True
    elif action == "off_product":
        product = Product.query.filter(Product.id == report.target_id).first()
        if product:
            product.status = ProductStatus.OFF
            product.is_available = False
            product.reject_reason = (result or "举报核实违规")[:200]
            notify(product.seller_id, MessageType.AUDIT, "商品被下架", f"《{product.name}》因违规被下架。", "/seller/products")
    elif action == "ban_user":
        user = User.query.filter(User.id == report.target_id).first()
        if user:
            user.ban(result or "举报核实违规")
            Product.query.filter(Product.seller_id == user.id).update({"is_available": False}, synchronize_session=False)

    report.status = status
    report.handle_result = result[:200]
    report.handler_id = current_admin().id
    report.handled_at = utcnow()
    record(AuditAction.REPORT_HANDLE, "report", report.id, f"{status} {action} {result}")
    notify(
        report.reporter_id,
        MessageType.SYSTEM,
        "举报已处理",
        f"你举报的内容已处理：{result or status}",
        "",
    )
    db.session.commit()
    return ok(report_view(report, _target_summary(report)), "已处理")


# ------------------------------------------------------------------ 审计
@bp.get("/audit-logs")
@admin_required
def list_audit_logs():
    query = AuditLog.query
    keyword = (request.args.get("keyword") or "").strip()
    if keyword:
        like = f"%{keyword}%"
        query = query.filter((AuditLog.action.ilike(like)) | (AuditLog.admin_name.ilike(like)))
    query = query.order_by(AuditLog.created_at.desc())
    page, per_page = page_args(30)
    total = query.order_by(None).count()
    rows = query.limit(per_page).offset((page - 1) * per_page).all()
    return ok(page_result([audit_view(log) for log in rows], total, page, per_page))


# ------------------------------------------------------------------ 导出
EXPORT_KINDS = {"users", "orders", "products"}


@bp.get("/export/<kind>")
@admin_required
def export_csv(kind: str):
    if kind not in EXPORT_KINDS:
        raise not_found("不支持的导出类型")
    limit = 20000
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    if kind == "users":
        writer.writerow(["ID", "昵称", "手机号", "校区", "是否卖家", "是否封禁", "注册时间"])
        rows = User.query.filter(User.is_deleted.is_(False)).order_by(User.id.desc()).limit(limit).all()
        for user in rows:
            writer.writerow([user.id, user.nickname, mask_phone(user.phone), user.campus, "是" if user.is_seller else "否",
                             "是" if user.is_banned else "否", iso(user.created_at)])
    elif kind == "orders":
        writer.writerow(["订单号", "买家", "卖家", "状态", "支付方式", "金额", "商品数", "创建时间", "完成时间"])
        rows = Order.query.order_by(Order.id.desc()).limit(limit).all()
        for order in rows:
            writer.writerow([
                order.order_no,
                order.buyer.nickname if order.buyer else "",
                order.seller.nickname if order.seller else "",
                order.status,
                order.pay_method,
                float(order.total_amount),
                sum(item.quantity for item in order.items),
                iso(order.created_at),
                iso(order.finished_at) or "",
            ])
    else:
        writer.writerow(["ID", "商品名", "卖家", "分类", "价格", "库存", "已售", "浏览量", "状态", "创建时间"])
        rows = Product.query.filter(Product.is_deleted.is_(False)).order_by(Product.id.desc()).limit(limit).all()
        for product in rows:
            writer.writerow([
                product.id,
                product.name,
                product.seller.nickname if product.seller else "",
                product.tag.name if product.tag else "",
                float(product.price),
                product.quantity,
                product.sales,
                product.views,
                product.status,
                iso(product.created_at),
            ])

    filename = f"campus-{kind}-{datetime.now().strftime('%Y%m%d%H%M')}.csv"
    data = "\ufeff" + buffer.getvalue()  # BOM 让 Excel 正确识别中文
    return Response(
        data.encode("utf-8"),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@bp.get("/orders/summary")
@admin_required
def order_summary():
    from sqlalchemy import func

    rows = db.session.query(Order.status, func.count(Order.id), func.coalesce(func.sum(Order.total_amount), 0)).group_by(
        Order.status
    ).all()
    return ok({"items": [{"status": s, "count": int(c), "amount": float(a or 0)} for s, c, a in rows]})
