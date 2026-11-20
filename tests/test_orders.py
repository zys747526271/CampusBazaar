"""订单状态机、库存并发、幂等与退款。"""
from __future__ import annotations

import re

from conftest import headers, login, place_order
from backend.constants import OrderStatus
from backend.extensions import db
from backend.models import Order, Product


def test_order_creation_locks_stock(client, buyer_token):
    resp = place_order(client, buyer_token, quantity=2)
    assert resp.status_code == 201, resp.get_json()
    order = resp.get_json()["data"]["orders"][0]
    assert order["status"] == OrderStatus.UNPAID
    # PRD FR-ORDR-01：CB + yyyyMMdd + 6 位随机
    assert re.fullmatch(r"CB\d{14}", order["order_no"]), order["order_no"]
    assert order["total_amount"] == 20.0
    product = db.session.get(Product, 1)
    assert product.quantity == 1


def test_out_of_stock_returns_409(client, buyer_token):
    assert place_order(client, buyer_token, quantity=5).status_code == 409


def test_cannot_buy_own_product(client, seller_token):
    assert place_order(client, seller_token, product_id=1).status_code == 403


def test_illegal_transition_returns_409(client, buyer_token):
    order_id = place_order(client, buyer_token).get_json()["data"]["orders"][0]["id"]
    resp = client.post(f"/api/orders/{order_id}/confirm", headers=headers(buyer_token))
    assert resp.status_code == 409


def test_offline_order_full_lifecycle(client, buyer_token, seller_token):
    order_id = place_order(client, buyer_token).get_json()["data"]["orders"][0]["id"]

    assert client.post(f"/api/seller/orders/{order_id}/confirm-paid", headers=headers(seller_token)).status_code == 200
    assert (
        client.post(
            f"/api/seller/orders/{order_id}/ship", json={"note": "门口面交"}, headers=headers(seller_token)
        ).status_code
        == 200
    )
    assert client.post(f"/api/orders/{order_id}/confirm", headers=headers(buyer_token)).status_code == 200

    order = db.session.get(Order, order_id)
    assert order.status == OrderStatus.DONE
    assert len(order.logs) >= 4
    assert db.session.get(Product, 1).sales == 1


def test_balance_payment_deducts_and_cancel_refunds(client, buyer_token):
    order_id = place_order(client, buyer_token, pay_method="余额").get_json()["data"]["orders"][0]["id"]
    assert client.post(f"/api/orders/{order_id}/pay", headers=headers(buyer_token)).status_code == 200

    balance = client.get("/api/balance", headers=headers(buyer_token)).get_json()["data"]
    assert balance["amount"] == 990.0

    refund = client.post(f"/api/orders/{order_id}/refund", json={"reason": "不想买了"}, headers=headers(buyer_token))
    assert refund.status_code == 200
    assert refund.get_json()["data"]["status"] == OrderStatus.REFUNDING


def test_cancel_restores_stock(client, buyer_token):
    order_id = place_order(client, buyer_token, quantity=2).get_json()["data"]["orders"][0]["id"]
    assert db.session.get(Product, 1).quantity == 1
    resp = client.post(f"/api/orders/{order_id}/cancel", json={"reason": "改主意了"}, headers=headers(buyer_token))
    assert resp.status_code == 200
    assert db.session.get(Product, 1).quantity == 3


def test_idempotency_key_prevents_duplicate_orders(client, buyer_token):
    payload = {
        "source": "now",
        "items": [{"product_id": 1, "quantity": 1}],
        "pay_method": "线下",
        "delivery_type": "自提",
        "receiver_name": "买家一号",
        "receiver_phone": "13800000001",
        "address_text": "图书馆",
    }
    first = client.post("/api/orders", json=payload, headers={**headers(buyer_token), "Idempotency-Key": "abc"})
    second = client.post("/api/orders", json=payload, headers={**headers(buyer_token), "Idempotency-Key": "abc"})
    assert first.status_code == 201
    assert second.headers.get("X-Idempotent-Replay") == "true"
    assert Order.query.count() == 1


def test_expired_unpaid_order_cancelled_by_job(client, buyer_token, app):
    from datetime import timedelta

    from backend.services import jobs
    from backend.utils.common import utcnow

    order_id = place_order(client, buyer_token).get_json()["data"]["orders"][0]["id"]
    order = db.session.get(Order, order_id)
    order.pay_deadline = utcnow() - timedelta(minutes=5)
    db.session.commit()

    result = jobs.run_once()
    assert result["expired_orders"] == 1
    assert db.session.get(Order, order_id).status == OrderStatus.CANCELLED
    assert db.session.get(Product, 1).quantity == 3


def test_comment_requires_completed_order(client, buyer_token):
    order_id = place_order(client, buyer_token).get_json()["data"]["orders"][0]["id"]
    resp = client.post(
        "/api/comments",
        json={"order_id": order_id, "product_id": 1, "rating": 5, "content": "还没完成就评价"},
        headers=headers(buyer_token),
    )
    assert resp.status_code == 409


def test_buyer_can_cancel_refund(client, buyer_token):
    order_id = place_order(client, buyer_token, pay_method="余额").get_json()["data"]["orders"][0]["id"]
    client.post(f"/api/orders/{order_id}/pay", headers=headers(buyer_token))
    client.post(f"/api/orders/{order_id}/refund", json={"reason": "买错了"}, headers=headers(buyer_token))

    resp = client.post(f"/api/orders/{order_id}/cancel-refund", headers=headers(buyer_token))
    assert resp.status_code == 200
    assert resp.get_json()["data"]["status"] == OrderStatus.PAID


def test_seller_approve_refund_returns_balance_and_stock(client, buyer_token, seller_token):
    order_id = place_order(client, buyer_token, pay_method="余额").get_json()["data"]["orders"][0]["id"]
    client.post(f"/api/orders/{order_id}/pay", headers=headers(buyer_token))
    client.post(f"/api/orders/{order_id}/refund", json={"reason": "商品与描述不符"}, headers=headers(buyer_token))

    resp = client.post(
        f"/api/seller/orders/{order_id}/refund",
        json={"approve": True, "note": "同意退款"},
        headers=headers(seller_token),
    )
    assert resp.status_code == 200
    assert resp.get_json()["data"]["status"] == OrderStatus.CANCELLED
    balance = client.get("/api/balance", headers=headers(buyer_token)).get_json()["data"]
    assert balance["amount"] == 1000.0
    assert db.session.get(Product, 1).quantity == 3
