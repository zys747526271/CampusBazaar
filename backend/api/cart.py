"""购物车（PRD 4.5）。"""
from __future__ import annotations

from decimal import Decimal

from flask import Blueprint, request
from sqlalchemy import false

from backend.constants import ProductStatus
from backend.errors import bad_request, conflict, forbidden, not_found
from backend.extensions import db
from backend.models import Cart, Product
from backend.services.serializers import cart_item_view
from backend.utils.response import ok
from backend.utils.security import current_user, login_required
from backend.utils.validators import Payload

bp = Blueprint("cart", __name__, url_prefix="/api/carts")


def _cart_query(user_id: int):
    return Cart.query.filter(Cart.user_id == user_id).order_by(Cart.created_at.desc())


def _summary(items: list[dict]) -> dict:
    valid = [item for item in items if not item["invalid_reason"]]
    selected = [item for item in valid if item["selected"]]
    return {
        "total_count": sum(item["quantity"] for item in items),
        "valid_count": len(valid),
        "invalid_count": len(items) - len(valid),
        "selected_count": sum(item["quantity"] for item in selected),
        "selected_amount": round(sum(item["subtotal"] for item in selected), 2),
    }


@bp.get("")
@login_required
def list_cart():
    user = current_user()
    items = [cart_item_view(row) for row in _cart_query(user.id).all()]
    return ok({"items": items, "summary": _summary(items)})


@bp.get("/count")
@login_required
def cart_count():
    user = current_user()
    total = sum(row.quantity for row in Cart.query.filter_by(user_id=user.id).all())
    return ok({"count": total})


@bp.post("")
@login_required
def add_to_cart():
    user = current_user()
    payload = Payload(request.get_json(silent=True))
    product_id = payload.integer("product_id", min_value=1, label="商品")
    quantity = payload.integer("quantity", required=False, min_value=1, max_value=99, default=1, label="数量")
    payload.done()

    product = Product.query.filter(Product.id == product_id, Product.is_deleted.is_(False)).first()
    if product is None:
        raise not_found("商品不存在")
    if product.seller_id == user.id:
        raise forbidden("不能购买自己发布的商品")
    if product.status != ProductStatus.APPROVED or not product.is_available or product.quantity <= 0:
        raise conflict("商品已下架或售罄")

    row = Cart.query.filter_by(user_id=user.id, product_id=product_id).first()
    new_quantity = quantity + (row.quantity if row else 0)
    if new_quantity > product.quantity:
        raise conflict(f"库存不足，最多可购买 {product.quantity} 件")
    if row:
        row.quantity = new_quantity
        row.selected = True
    else:
        db.session.add(Cart(user_id=user.id, product_id=product_id, quantity=quantity))
    db.session.commit()
    total = sum(r.quantity for r in Cart.query.filter_by(user_id=user.id).all())
    return ok({"count": total}, "已加入购物车")


@bp.put("/<int:cart_id>")
@login_required
def update_cart(cart_id: int):
    user = current_user()
    row = Cart.query.filter_by(id=cart_id, user_id=user.id).first()
    if row is None:
        raise not_found("购物车条目不存在")

    payload = Payload(request.get_json(silent=True))
    if payload.take("quantity") is not None:
        quantity = payload.integer("quantity", min_value=1, max_value=99, label="数量")
        payload.done()
        product = row.product
        if product is None or product.is_deleted:
            raise conflict("商品已删除")
        if product.status != ProductStatus.APPROVED or not product.is_available:
            raise conflict("商品已下架")
        if quantity > product.quantity:
            raise conflict(f"库存不足，最多可购买 {product.quantity} 件")
        row.quantity = quantity
    if payload.take("selected") is not None:
        row.selected = payload.boolean("selected", default=row.selected)
    payload.done()
    db.session.commit()
    return ok({"item": cart_item_view(row), "summary": _summary([cart_item_view(r) for r in _cart_query(user.id)])})


@bp.delete("/<int:cart_id>")
@login_required
def delete_cart(cart_id: int):
    user = current_user()
    row = Cart.query.filter_by(id=cart_id, user_id=user.id).first()
    if row is None:
        raise not_found("购物车条目不存在")
    db.session.delete(row)
    db.session.commit()
    return ok(None, "已移除")


@bp.delete("")
@login_required
def clear_cart():
    user = current_user()
    mode = (request.args.get("mode") or "all").lower()
    query = Cart.query.filter_by(user_id=user.id)
    if mode == "selected":
        query = query.filter(Cart.selected.is_(True))
    elif mode == "invalid":
        invalid_ids = [row.id for row in Cart.query.filter_by(user_id=user.id).all() if cart_item_view(row)["invalid_reason"]]
        query = Cart.query.filter(Cart.id.in_(invalid_ids)) if invalid_ids else query.filter(false())
    count = query.delete(synchronize_session=False)
    db.session.commit()
    return ok({"deleted": count}, f"已清理 {count} 件商品")


@bp.post("/batch")
@login_required
def batch_action():
    user = current_user()
    payload = Payload(request.get_json(silent=True))
    action = payload.choice("action", ("delete", "select", "unselect"), label="操作")
    ids = payload.int_list("ids", max_items=100, label="条目")
    payload.done()
    if not ids:
        raise bad_request("请选择要操作的条目")

    rows = Cart.query.filter(Cart.user_id == user.id, Cart.id.in_(ids)).all()
    if action == "delete":
        for row in rows:
            db.session.delete(row)
    else:
        for row in rows:
            row.selected = action == "select"
    db.session.commit()
    return ok({"affected": len(rows)}, "操作成功")


@bp.put("/select-all")
@login_required
def select_all():
    user = current_user()
    payload = Payload(request.get_json(silent=True))
    selected = payload.boolean("selected", default=True)
    payload.done()
    for row in Cart.query.filter_by(user_id=user.id).all():
        row.selected = selected
    db.session.commit()
    return ok({"selected": selected}, "已更新勾选")


@bp.get("/checkout")
@login_required
def checkout_items():
    """结算页数据：仅取选中且有效的条目，附带按卖家分组的小计。"""
    user = current_user()
    items = [cart_item_view(row) for row in _cart_query(user.id).all()]
    selected = [item for item in items if item["selected"] and not item["invalid_reason"]]
    if not selected:
        raise bad_request("请先勾选要结算的商品")

    groups: dict[int, dict] = {}
    for item in selected:
        seller = item["product"]["seller"]
        group = groups.setdefault(
            seller["id"],
            {"seller": seller, "items": [], "amount": Decimal("0.00")},
        )
        group["items"].append(item)
        group["amount"] += Decimal(str(item["subtotal"]))

    return ok(
        {
            "items": selected,
            "groups": [
                {"seller": g["seller"], "items": g["items"], "amount": float(g["amount"])} for g in groups.values()
            ],
            "summary": _summary(items),
        }
    )
