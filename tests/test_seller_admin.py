"""卖家权限隔离、分类约束、管理员治理与审计。"""
from __future__ import annotations

from conftest import headers, login


def _create_product(client, token, **overrides):
    payload = {
        "name": overrides.pop("name", "新商品"),
        "description": "测试",
        "price": "12.50",
        "quantity": 2,
        "condition": "几乎全新",
        "location": "图书馆",
        "tag_id": 1,
        "images": ["/static/uploads/demo/p1-1.svg"],
    }
    payload.update(overrides)
    return client.post("/api/seller/products", json=payload, headers=headers(token))


def test_seller_category_duplicate_and_delete_guard(client, seller_token):
    first = client.post("/api/seller/categories", json={"name": "我的教材"}, headers=headers(seller_token))
    assert first.status_code == 200
    dup = client.post("/api/seller/categories", json={"name": "我的教材"}, headers=headers(seller_token))
    assert dup.status_code == 400

    category_id = first.get_json()["data"]["id"]
    product = _create_product(client, seller_token, seller_category_id=category_id)
    assert product.status_code == 200

    blocked = client.delete(f"/api/seller/categories/{category_id}", headers=headers(seller_token))
    assert blocked.status_code == 400
    assert "还有 1 件商品" in blocked.get_json()["message"]


def test_seller_cannot_use_other_sellers_category(client, seller_token):
    from backend.extensions import db
    from backend.models import SellerCategory, User

    other = User(phone="13800000003", nickname="另一个卖家", password_hash=User.query.first().password_hash, is_seller=True)
    db.session.add(other)
    db.session.flush()
    category = SellerCategory(seller_id=other.id, name="别人的分类")
    db.session.add(category)
    db.session.commit()

    resp = _create_product(client, seller_token, seller_category_id=category.id)
    assert resp.status_code == 403


def test_product_requires_image_and_tag(client, seller_token):
    no_image = _create_product(client, seller_token, name="没图商品", images=[])
    assert no_image.status_code == 400
    no_tag = _create_product(client, seller_token, name="没分类商品", tag_id=None)
    assert no_tag.status_code == 400


def test_other_seller_cannot_edit_product(client, seller_token):
    from backend.extensions import db
    from backend.models import User
    from backend.utils.security import hash_password

    intruder = User(phone="13800000007", nickname="闯入者", password_hash=hash_password("Test12345"), is_seller=True)
    db.session.add(intruder)
    db.session.commit()
    token = login(client, phone="13800000007")
    resp = client.put("/api/seller/products/1", json={"name": "改别人的"}, headers=headers(token))
    assert resp.status_code == 403


def test_admin_hide_comment_and_audit(client, buyer_token, seller_token, admin_token):
    from conftest import place_order
    from backend.extensions import db
    from backend.models import AuditLog, Comment

    order_id = place_order(client, buyer_token).get_json()["data"]["orders"][0]["id"]
    client.post(f"/api/seller/orders/{order_id}/confirm-paid", headers=headers(seller_token))
    client.post(f"/api/seller/orders/{order_id}/ship", json={"note": "已送达"}, headers=headers(seller_token))
    client.post(f"/api/orders/{order_id}/confirm", headers=headers(buyer_token))
    comment = client.post(
        "/api/comments",
        json={"order_id": order_id, "product_id": 1, "rating": 3, "content": "一般"},
        headers=headers(buyer_token),
    )
    assert comment.status_code == 201
    comment_id = comment.get_json()["data"]["id"]

    hidden = client.put(
        f"/api/admin/comments/{comment_id}/visibility",
        json={"hidden": True, "reason": "含联系方式"},
        headers=headers(admin_token),
    )
    assert hidden.status_code == 200
    assert db.session.get(Comment, comment_id).is_hidden is True
    assert AuditLog.query.filter_by(action="隐藏评价").count() == 1
    # 隐藏后前台列表不再出现
    assert client.get("/api/products/1/comments").get_json()["data"]["total"] == 0


def test_ban_user_blocks_login_and_hides_products(client, buyer_token, admin_token):
    from backend.extensions import db
    from backend.models import Product, User

    banned_user = User.query.filter_by(phone="13800000001").first()
    resp = client.put(
        f"/api/admin/users/{banned_user.id}/ban",
        json={"banned": True, "reason": "多次骚扰他人"},
        headers=headers(admin_token),
    )
    assert resp.status_code == 200

    login_attempt = client.post("/api/auth/login", json={"phone": "13800000001", "password": "Test12345"})
    assert login_attempt.status_code == 403
    assert login_attempt.get_json()["message"] == "多次骚扰他人"

    # 卖家商品被一并下架
    client.put(
        f"/api/admin/users/{User.query.filter_by(phone='13800000002').first().id}/ban",
        json={"banned": True, "reason": "测试"},
        headers=headers(admin_token),
    )
    assert db.session.get(Product, 1).is_available is False


def test_admin_batch_status_returns_per_item_result(client, admin_token):
    from backend.extensions import db
    from backend.models import Product

    product = db.session.get(Product, 1)
    resp = client.post(
        "/api/admin/products/batch-status",
        json={"ids": [product.id, 9999], "status": "已下架", "reason": "批量下架测试"},
        headers=headers(admin_token),
    )
    body = resp.get_json()["data"]
    assert resp.status_code == 200
    assert body["success_count"] == 1
    assert any(item["success"] is False for item in body["results"])


def test_export_csv_requires_admin(client, admin_token, buyer_token):
    assert client.get("/api/admin/export/orders").status_code == 401
    assert client.get("/api/admin/export/orders", headers=headers(buyer_token)).status_code == 403
    resp = client.get("/api/admin/export/orders", headers=headers(admin_token))
    assert resp.status_code == 200
    assert resp.headers["Content-Type"].startswith("text/csv")


def test_seller_can_reply_to_comment(client, buyer_token, seller_token):
    from conftest import place_order

    order_id = place_order(client, buyer_token).get_json()["data"]["orders"][0]["id"]
    client.post(f"/api/seller/orders/{order_id}/confirm-paid", headers=headers(seller_token))
    client.post(f"/api/seller/orders/{order_id}/ship", json={"note": "已送达"}, headers=headers(seller_token))
    client.post(f"/api/orders/{order_id}/confirm", headers=headers(buyer_token))
    comment = client.post(
        "/api/comments",
        json={"order_id": order_id, "product_id": 1, "rating": 5, "content": "很好"},
        headers=headers(buyer_token),
    ).get_json()["data"]

    reply = client.post(
        f"/api/seller/comments/{comment['id']}/reply",
        json={"reply": "谢谢支持"},
        headers=headers(seller_token),
    )
    assert reply.status_code == 200
    assert reply.get_json()["data"]["seller_reply"] == "谢谢支持"


def test_admin_reset_password_returns_temporary(client, admin_token):
    from backend.extensions import db
    from backend.models import User

    user = User.query.filter_by(phone="13800000001").first()
    resp = client.put(f"/api/admin/users/{user.id}/reset-password", json={}, headers=headers(admin_token))
    assert resp.status_code == 200
    temporary = resp.get_json()["data"]["new_password"]
    assert len(temporary) >= 8

    # 旧密码失效，新密码可登录
    assert client.post("/api/auth/login", json={"phone": "13800000001", "password": "Test12345"}).status_code == 400
    assert client.post("/api/auth/login", json={"phone": "13800000001", "password": temporary}).status_code == 200


def test_admin_handles_report_with_action(client, buyer_token, admin_token):
    from backend.extensions import db
    from backend.models import Comment

    report = client.post(
        "/api/reports",
        json={"target_type": "product", "target_id": 1, "reason": "虚假信息", "detail": "描述与实物不符"},
        headers=headers(buyer_token),
    )
    assert report.status_code == 201
    report_id = report.get_json()["data"]["id"]

    handled = client.put(
        f"/api/admin/reports/{report_id}",
        json={"status": "已处理", "result": "核实后下架", "action": "off_product"},
        headers=headers(admin_token),
    )
    assert handled.status_code == 200
    assert handled.get_json()["data"]["status"] == "已处理"

    from backend.models import Product

    assert db.session.get(Product, 1).status == "已下架"
