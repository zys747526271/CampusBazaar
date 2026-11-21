"""履约方式、运费、自提流程与交易快照（v2.2）。"""
from __future__ import annotations

import pathlib

from conftest import headers, login, place_order
from backend.constants import OrderStatus
from backend.extensions import db
from backend.models import Comment, Message, Order, Product


def create_address(client, token, **overrides) -> int:
    payload = {
        "name": "买家一号",
        "phone": "13800000001",
        "campus_area": "东校区",
        "detail": "1 栋 102",
        "is_default": True,
    }
    payload.update(overrides)
    resp = client.post("/api/addresses", json=payload, headers=headers(token))
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()["data"]["id"]


def create_product(client, seller_token, **overrides) -> dict:
    payload = {
        "name": "履约测试商品",
        "description": "测试用",
        "price": "10.00",
        "quantity": 3,
        "condition": "轻微使用",
        "images": ["/static/uploads/demo/p1-1.svg"],
        "tag_id": 1,
        "supports_pickup": True,
        "pickup_location": "图书馆一楼",
        "supports_express": True,
        "free_shipping": True,
    }
    payload.update(overrides)
    resp = client.post("/api/seller/products", json=payload, headers=headers(seller_token))
    assert resp.status_code == 200, resp.get_json()
    return resp.get_json()["data"]


def test_express_requires_saved_address(client, buyer_token, seller_token):
    product = create_product(client, seller_token)
    missing = place_order(client, buyer_token, product_id=product["id"], delivery_type="快递", pay_method="余额")
    assert missing.status_code == 400
    assert "收货地址" in missing.get_json()["message"]

    address_id = create_address(client, buyer_token)
    ok = place_order(
        client, buyer_token, product_id=product["id"], delivery_type="快递", pay_method="余额", address_id=address_id
    )
    assert ok.status_code == 201, ok.get_json()
    order = ok.get_json()["data"]["orders"][0]
    assert order["receiver_name"] == "买家一号"
    assert order["address_text"] == "东校区 1 栋 102"


def test_express_rejects_offline_payment(client, buyer_token, seller_token):
    product = create_product(client, seller_token)
    address_id = create_address(client, buyer_token)
    resp = place_order(
        client,
        buyer_token,
        product_id=product["id"],
        delivery_type="快递",
        pay_method="线下",
        address_id=address_id,
    )
    assert resp.status_code == 400
    assert "线下支付" in resp.get_json()["message"]


def test_shipping_fee_is_added_to_total(client, buyer_token, seller_token):
    product = create_product(
        client, seller_token, price="100.00", supports_pickup=False, free_shipping=False, shipping_fee="12.00"
    )
    address_id = create_address(client, buyer_token)
    resp = place_order(
        client, buyer_token, product_id=product["id"], delivery_type="快递", pay_method="余额", address_id=address_id
    )
    assert resp.status_code == 201, resp.get_json()
    order = resp.get_json()["data"]["orders"][0]
    assert order["items_total"] == 100.0
    assert order["shipping_fee"] == 12.0
    assert order["total_amount"] == 112.0


def test_pickup_only_product_rejects_express(client, buyer_token, seller_token):
    product = create_product(client, seller_token, supports_express=False)
    address_id = create_address(client, buyer_token)
    resp = place_order(
        client, buyer_token, product_id=product["id"], delivery_type="快递", pay_method="余额", address_id=address_id
    )
    assert resp.status_code == 400
    assert "不支持快递" in resp.get_json()["message"]


def test_seller_fills_pickup_location_then_buyer_confirms_time(client, buyer_token, seller_token):
    product = create_product(client, seller_token, pickup_location="", supports_express=False)
    resp = place_order(client, buyer_token, product_id=product["id"], pay_method="余额", pickup_time="")
    order = resp.get_json()["data"]["orders"][0]
    assert order["needs_pickup_location"] is True
    assert order["pickup_location"] == ""

    filled = client.post(
        f"/api/seller/orders/{order['id']}/pickup-location",
        json={"pickup_location": "图书馆北门"},
        headers=headers(seller_token),
    )
    assert filled.status_code == 200
    assert filled.get_json()["data"]["pickup_location"] == "图书馆北门"
    assert Message.query.filter_by(user_id=1, title="卖家已设置自提点").count() == 1

    client.post(f"/api/orders/{order['id']}/pay", headers=headers(buyer_token))
    client.post(f"/api/seller/orders/{order['id']}/ship", json={"note": "已备好"}, headers=headers(seller_token))

    blocked = client.post(f"/api/orders/{order['id']}/confirm", headers=headers(buyer_token))
    assert blocked.status_code == 409
    assert "自提时间" in blocked.get_json()["message"]

    confirmed = client.post(
        f"/api/orders/{order['id']}/pickup-time",
        json={"pickup_time": "2030-01-02T18:30"},
        headers=headers(buyer_token),
    )
    assert confirmed.status_code == 200
    done = client.post(f"/api/orders/{order['id']}/confirm", headers=headers(buyer_token))
    assert done.status_code == 200
    assert done.get_json()["data"]["status"] == OrderStatus.DONE


def test_order_creates_viewable_snapshot(client, buyer_token):
    resp = place_order(client, buyer_token, product_id=1)
    order = resp.get_json()["data"]["orders"][0]
    assert order["has_snapshot"] is True

    snapshot = client.get(f"/api/orders/{order['id']}/snapshot", headers=headers(buyer_token))
    assert snapshot.status_code == 200
    data = snapshot.get_json()["data"]
    assert data["html_url"].endswith(".html")
    assert data["data"]["items"][0]["listing"]["cover_image"]
    assert data["data"]["amounts"]["total_amount"] == 10.0

    from backend import create_app

    root = pathlib.Path(create_app().config["UPLOAD_ROOT"])
    relative = data["html_url"].replace("/static/uploads/", "", 1)
    assert (root / relative).is_file()


def test_product_list_filters_by_delivery_and_free_shipping(client, seller_token):
    pickup_only = create_product(client, seller_token, name="仅自提商品", supports_express=False)
    fee_product = create_product(
        client, seller_token, name="到付商品", free_shipping=False, shipping_fee="8.00"
    )

    pickup_items = client.get("/api/products?delivery=pickup").get_json()["data"]["items"]
    assert pickup_only["id"] in [item["id"] for item in pickup_items]

    express_items = client.get("/api/products?delivery=express").get_json()["data"]["items"]
    express_ids = [item["id"] for item in express_items]
    assert fee_product["id"] in express_ids
    assert pickup_only["id"] not in express_ids

    free_items = client.get("/api/products?free_shipping=1").get_json()["data"]["items"]
    assert fee_product["id"] not in [item["id"] for item in free_items]


def test_shop_comments_keep_offshelf_products(client, buyer_token, seller_token):
    order_id = place_order(client, buyer_token, product_id=1).get_json()["data"]["orders"][0]["id"]
    client.post(f"/api/seller/orders/{order_id}/confirm-paid", headers=headers(seller_token))
    client.post(f"/api/seller/orders/{order_id}/ship", json={"note": "已交付"}, headers=headers(seller_token))
    client.post(f"/api/orders/{order_id}/confirm", headers=headers(buyer_token))
    comment = client.post(
        "/api/comments",
        json={"order_id": order_id, "product_id": 1, "rating": 5, "content": "书很好"},
        headers=headers(buyer_token),
    )
    assert comment.status_code == 201, comment.get_json()

    # 下架商品后，店铺评价仍可查看
    product = db.session.get(Product, 1)
    product.is_available = False
    db.session.commit()

    resp = client.get("/api/shops/2/comments")
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["product"]["id"] == 1
    assert data["items"][0]["product"]["is_on_sale"] is False
