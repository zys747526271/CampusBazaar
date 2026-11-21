"""DTO 序列化：前后端字段契约的唯一来源（PRD 附录 A 第 1、7 条）。

任何接口都从这里取字段，禁止在路由里手搓响应字典，避免出现
``items`` / ``products`` / ``data`` 三套同义结构。
"""
from __future__ import annotations

from backend.constants import (
    DeliveryType,
    OrderStatus,
    PayMethod,
    ProductStatus,
    ReportTarget,
)
from backend.utils.common import iso, money


# ---------------------------------------------------------------- 用户
def user_brief(user) -> dict | None:
    if user is None:
        return None
    return {
        "id": user.id,
        "nickname": user.nickname,
        "avatar_url": user.avatar_url or "",
    }


def user_public(user, stats: dict | None = None) -> dict:
    data = {
        "id": user.id,
        "nickname": user.nickname,
        "avatar_url": user.avatar_url or "",
        "campus": user.campus or "",
        "is_seller": user.is_seller,
        "seller_since": iso(user.seller_since),
        "created_at": iso(user.created_at),
    }
    if stats:
        data.update(stats)
    return data


def user_me(user) -> dict:
    data = user_public(user)
    data.update(
        {
            "phone": user.phone,
            "email": user.email or "",
            "is_banned": user.is_banned,
            "ban_reason": user.ban_reason or "",
        }
    )
    return data


def user_admin_view(user, stats: dict | None = None) -> dict:
    data = user_me(user)
    data.update(
        {
            "is_deleted": user.is_deleted,
            "last_login_at": iso(user.last_login_at),
            "banned_at": iso(user.banned_at),
        }
    )
    if stats:
        data.update(stats)
    return data


def admin_view(admin) -> dict:
    return {
        "id": admin.id,
        "username": admin.username,
        "name": admin.name or admin.username,
        "permission_level": admin.permission_level,
        "is_active": admin.is_active,
        "last_login_at": iso(admin.last_login_at),
    }


# ---------------------------------------------------------------- 分类 / 轮播
def tag_view(tag, product_count: int | None = None) -> dict:
    data = {
        "id": tag.id,
        "name": tag.name,
        "icon": tag.icon or "",
        "description": tag.description or "",
        "sort_order": tag.sort_order,
        "is_active": tag.is_active,
    }
    if product_count is not None:
        data["product_count"] = product_count
    return data


def seller_category_view(category, product_count: int | None = None) -> dict:
    data = {
        "id": category.id,
        "name": category.name,
        "sort_order": category.sort_order,
    }
    if product_count is not None:
        data["product_count"] = product_count
    return data


def banner_view(banner) -> dict:
    return {
        "id": banner.id,
        "title": banner.title,
        "subtitle": banner.subtitle or "",
        "image_url": banner.image_url,
        "link_url": banner.link_url or "",
        "sort_order": banner.sort_order,
        "is_active": banner.is_active,
    }


# ---------------------------------------------------------------- 商品
def product_card(product, seller_stats: dict | None = None) -> dict:
    seller = product.seller
    return {
        "id": product.id,
        "name": product.name,
        "price": money(product.price),
        "original_price": money(product.original_price) if product.original_price else None,
        "discount": product.discount,
        "cover_image": product.cover_image,
        "quantity": product.quantity,
        "sales": product.sales,
        "views": product.views,
        "condition": product.product_condition,
        "location": product.location or "",
        "status": product.status,
        "is_available": product.is_available,
        "is_featured": product.is_featured,
        "is_on_sale": product.is_on_sale,
        "stock_state": product.stock_state,
        "supports_pickup": bool(product.supports_pickup),
        "pickup_location": product.pickup_location or "",
        "supports_express": bool(product.supports_express),
        "free_shipping": bool(product.free_shipping),
        "shipping_fee": money(product.shipping_amount),
        "delivery_labels": list(product.delivery_labels),
        "tag": {"id": product.tag.id, "name": product.tag.name} if product.tag else None,
        "seller": {
            **(user_brief(seller) or {}),
            "is_seller": bool(seller and seller.is_seller),
            "rating": (seller_stats or {}).get("rating"),
            "sold_count": (seller_stats or {}).get("sold_count"),
        },
        "created_at": iso(product.created_at),
    }


def product_detail(product, seller_stats: dict | None = None, viewer=None) -> dict:
    data = product_card(product, seller_stats)
    images = list(product.images or [])
    data.update(
        {
            "description": product.description or "",
            "images": images,
            "seller_category": (
                {"id": product.seller_category.id, "name": product.seller_category.name}
                if product.seller_category
                else None
            ),
            "reject_reason": product.reject_reason or "",
            "updated_at": iso(product.updated_at),
            "is_owner": bool(viewer and viewer.id == product.seller_id),
            "can_buy": product.is_on_sale and not (viewer and viewer.id == product.seller_id),
        }
    )
    return data


def product_seller_view(product, comment_count: int = 0) -> dict:
    """卖家中心列表：额外暴露审核状态与运营数据。"""
    data = product_card(product)
    data.update(
        {
            "description": product.description or "",
            "images": list(product.images or []),
            "reject_reason": product.reject_reason or "",
            "seller_category_id": product.seller_category_id,
            "tag_id": product.tag_id,
            "comment_count": comment_count,
            "audited_at": iso(product.audited_at),
            "updated_at": iso(product.updated_at),
        }
    )
    return data


# ---------------------------------------------------------------- 评价
def comment_view(comment, viewer=None, liked: bool = False, *, with_product: bool = False) -> dict:
    data = {
        "id": comment.id,
        "rating": comment.rating,
        "content": comment.content or "",
        "images": list(comment.images or []),
        "like_count": comment.like_count,
        "liked": liked,
        "is_hidden": comment.is_hidden,
        "seller_reply": comment.seller_reply or "",
        "seller_reply_at": iso(comment.seller_reply_at),
        "created_at": iso(comment.created_at),
        "user": user_brief(comment.user),
        "is_own": bool(viewer and comment.user_id == viewer.id),
    }
    if with_product and comment.product:
        data["product"] = {
            "id": comment.product.id,
            "name": comment.product.name,
            "cover_image": comment.product.cover_image,
            "status": comment.product.status,
            "is_on_sale": comment.product.is_on_sale,
            "stock_state": comment.product.stock_state,
        }
    if with_product:
        data["order_id"] = comment.order_id
        data["deleted"] = comment.is_deleted
    return data


def rating_summary(rows: list[tuple[int, int]], total: int) -> dict:
    """rows: [(rating, count)]；输出平均分与 1~5 星分布。"""
    dist = {str(star): 0 for star in range(1, 6)}
    for rating, count in rows:
        if str(rating) in dist:
            dist[str(rating)] = count
    average = 0.0
    if total:
        average = round(sum(int(r) * c for r, c in rows) / total, 1)
    return {"average": average, "total": total, "distribution": dist}


# ---------------------------------------------------------------- 购物车
def cart_item_view(cart) -> dict:
    product = cart.product
    invalid_reason = ""
    if product is None or product.is_deleted:
        invalid_reason = "商品已删除"
    elif product.status != ProductStatus.APPROVED or not product.is_available:
        invalid_reason = "商品已下架"
    elif product.quantity <= 0:
        invalid_reason = "商品已售罄"
    elif cart.quantity > product.quantity:
        invalid_reason = f"库存仅剩 {product.quantity} 件"
    subtotal = float(product.price) * cart.quantity if product else 0.0
    return {
        "id": cart.id,
        "quantity": cart.quantity,
        "selected": cart.selected,
        "invalid_reason": invalid_reason,
        "subtotal": round(subtotal, 2),
        "product": product_card(product) if product else None,
    }


# ---------------------------------------------------------------- 订单
def order_item_view(item) -> dict:
    return {
        "id": item.id,
        "product_id": item.product_id,
        "name": item.name,
        "image": item.image or "",
        "price": money(item.price),
        "quantity": item.quantity,
        "condition": item.product_condition or "",
        "subtotal": money(item.subtotal),
    }


def status_log_view(log) -> dict:
    return {
        "from_status": log.from_status,
        "to_status": log.to_status,
        "operator_type": log.operator_type,
        "operator_name": log.operator_name or "",
        "remark": log.remark or "",
        "created_at": iso(log.created_at),
    }


def order_view(order, viewer_type: str = "buyer", commented_product_ids: set[int] | None = None) -> dict:
    commented = commented_product_ids or set()
    items = [order_item_view(item) for item in order.items]
    for item in items:
        item["commented"] = item["product_id"] in commented
    pending_comment = any(item["product_id"] not in commented for item in items)
    data = {
        "id": order.id,
        "order_no": order.order_no,
        "status": order.status,
        "pay_method": order.pay_method,
        "delivery_type": order.delivery_type,
        "items_total": money(order.items_total),
        "shipping_fee": money(order.shipping_fee),
        "is_pickup": order.is_pickup,
        "pickup_location": order.pickup_location or "",
        "pickup_time": iso(order.pickup_time),
        "pickup_time_confirmed_at": iso(order.pickup_time_confirmed_at),
        "needs_pickup_location": order.needs_pickup_location,
        "has_snapshot": order.snapshot is not None,
        "total_amount": money(order.total_amount),
        "item_count": order.item_count,
        "receiver_name": order.receiver_name,
        "receiver_phone": order.receiver_phone,
        "address_text": order.address_text,
        "remark": order.remark or "",
        "ship_company": order.ship_company or "",
        "tracking_no": order.tracking_no or "",
        "cancel_reason": order.cancel_reason or "",
        "refund_reason": order.refund_reason or "",
        "refund_note": order.refund_note or "",
        "buyer": user_brief(order.buyer),
        "seller": user_brief(order.seller),
        "items": items,
        "timeline": [status_log_view(log) for log in order.logs],
        "actions": order_actions(order, viewer_type, pending_comment),
        "created_at": iso(order.created_at),
        "pay_deadline": iso(order.pay_deadline),
        "paid_at": iso(order.paid_at),
        "shipped_at": iso(order.shipped_at),
        "finished_at": iso(order.finished_at),
        "cancelled_at": iso(order.cancelled_at),
    }
    return data


def order_actions(order, viewer_type: str, pending_comment: bool = True) -> list[str]:
    """服务端计算可用动作，前端只渲染不判断，避免前后端状态机漂移。"""
    status = order.status
    actions: list[str] = []
    if viewer_type == "buyer":
        if status == OrderStatus.UNPAID:
            actions.append("pay")
            if order.pay_method == PayMethod.OFFLINE:
                actions.append("confirm_offline")
            actions.append("cancel")
        elif status == OrderStatus.PAID:
            actions.append("refund")
        elif status == OrderStatus.SHIPPED:
            actions.append("confirm")
            actions.append("refund")
        if (
            viewer_type == "buyer"
            and order.is_pickup
            and not order.pickup_time
            and status in (OrderStatus.UNPAID, OrderStatus.PAID, OrderStatus.SHIPPED)
        ):
            actions.append("set_pickup_time")
        elif status == OrderStatus.DONE and pending_comment:
            actions.append("comment")
        elif status == OrderStatus.REFUNDING:
            actions.append("cancel_refund")
    elif viewer_type == "seller":
        if status == OrderStatus.UNPAID:
            actions.append("close")
        elif status == OrderStatus.PAID:
            actions.append("ship")
        elif status == OrderStatus.REFUNDING:
            actions.append("refund_approve")
            actions.append("refund_reject")
    elif viewer_type == "admin":
        if status in (OrderStatus.UNPAID, OrderStatus.PAID, OrderStatus.SHIPPED):
            actions.append("admin_cancel")
        if status == OrderStatus.REFUNDING:
            actions.append("refund_approve")
            actions.append("refund_reject")
    return actions


def order_admin_view(order) -> dict:
    data = order_view(order, "admin")
    data["buyer_phone"] = order.receiver_phone
    return data


# ---------------------------------------------------------------- 其他
def message_view(message) -> dict:
    return {
        "id": message.id,
        "type": message.type,
        "title": message.title,
        "content": message.content or "",
        "link": message.link or "",
        "is_read": message.is_read,
        "created_at": iso(message.created_at),
    }


def report_view(report, with_target: dict | None = None) -> dict:
    data = {
        "id": report.id,
        "target_type": report.target_type,
        "target_type_label": ReportTarget.LABELS.get(report.target_type, report.target_type),
        "target_id": report.target_id,
        "reason": report.reason,
        "detail": report.detail or "",
        "status": report.status,
        "handle_result": report.handle_result or "",
        "reporter": user_brief(report.reporter),
        "created_at": iso(report.created_at),
        "handled_at": iso(report.handled_at),
    }
    if with_target:
        data["target"] = with_target
    return data


def balance_log_view(log) -> dict:
    return {
        "id": log.id,
        "amount": money(log.amount),
        "balance_after": money(log.balance_after),
        "type": log.type,
        "ref_type": log.ref_type or "",
        "ref_id": log.ref_id or "",
        "remark": log.remark or "",
        "created_at": iso(log.created_at),
    }


def address_view(address) -> dict:
    return {
        "id": address.id,
        "name": address.name,
        "phone": address.phone,
        "campus_area": address.campus_area or "",
        "detail": address.detail,
        "is_default": address.is_default,
    }


def audit_view(log) -> dict:
    return {
        "id": log.id,
        "admin_name": log.admin_name,
        "action": log.action,
        "target_type": log.target_type or "",
        "target_id": log.target_id or "",
        "detail": log.detail or "",
        "ip": log.ip or "",
        "created_at": iso(log.created_at),
    }


def delivery_options() -> list[dict]:
    return [{"value": item, "label": item} for item in DeliveryType.ALL]


def pay_options(delivery_type: str | None = None) -> list[dict]:
    """支付方式：快递只提供余额，自提可用余额/线下。"""
    from backend.constants import PAY_METHODS_BY_DELIVERY

    methods = PAY_METHODS_BY_DELIVERY.get(delivery_type, (PayMethod.BALANCE, PayMethod.OFFLINE))
    return [{"value": item, "label": item} for item in methods]
