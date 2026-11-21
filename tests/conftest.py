"""pytest 夹具：内存 SQLite + 测试客户端 + 造数工厂。

说明：测试环境用 ``db.create_all()`` 建表，生产结构变更仍只走 Alembic（PRD 附录 A 第 8 条）。
"""
from __future__ import annotations

import pytest

from backend import create_app
from backend.config import TestingConfig
from backend.constants import ProductStatus
from backend.extensions import db
from backend.models import Admin, Balance, Product, Tag, User
from backend.utils.security import hash_password

TEST_PASSWORD = "Test12345"


@pytest.fixture()
def app():
    application = create_app(TestingConfig)
    with application.app_context():
        db.create_all()
        _bootstrap_reference_data()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


# ------------------------------------------------------------------ 造数
def _bootstrap_reference_data() -> None:
    tag = Tag(name="教材书籍", icon="book", sort_order=1, is_active=True)
    db.session.add(tag)
    db.session.add(
        Admin(username="admin", name="测试管理员", password_hash=hash_password("Admin12345"), permission_level="超级")
    )
    buyer = User(phone="13800000001", nickname="买家一号", password_hash=hash_password(TEST_PASSWORD))
    seller = User(
        phone="13800000002", nickname="卖家一号", password_hash=hash_password(TEST_PASSWORD), is_seller=True
    )
    db.session.add_all([buyer, seller])
    db.session.flush()
    db.session.add_all([Balance(user_id=buyer.id, amount=1000), Balance(user_id=seller.id, amount=0)])
    db.session.add(
        Product(
            name="测试教材",
            description="用于测试的商品",
            price=10,
            quantity=3,
            images=["/static/uploads/demo/p1-1.svg"],
            tag_id=tag.id,
            seller_id=seller.id,
            status=ProductStatus.APPROVED,
            is_available=True,
        )
    )
    db.session.commit()


def login(client, phone: str = "13800000001", password: str = TEST_PASSWORD) -> str:
    resp = client.post("/api/auth/login", json={"phone": phone, "password": password})
    assert resp.status_code == 200, resp.get_json()
    return resp.get_json()["data"]["token"]


def admin_login(client, username: str = "admin", password: str = "Admin12345") -> str:
    resp = client.post("/api/auth/admin/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.get_json()
    return resp.get_json()["data"]["token"]


def headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def place_order(
    client,
    token: str,
    product_id: int = 1,
    quantity: int = 1,
    pay_method: str = "线下",
    delivery_type: str = "自提",
    pickup_time: str = "2030-01-01T12:00",
    address_id: int | None = None,
):
    payload = {
        "source": "now",
        "items": [{"product_id": product_id, "quantity": quantity}],
        "pay_method": pay_method,
        "delivery_type": delivery_type,
    }
    if delivery_type == "自提":
        payload.update({"receiver_name": "买家一号", "receiver_phone": "13800000001", "address_text": "图书馆"})
        if pickup_time:
            payload["pickup_time"] = pickup_time
    if address_id:
        payload["address_id"] = address_id
    return client.post("/api/orders", json=payload, headers=headers(token))


@pytest.fixture()
def buyer_token(client):
    return login(client)


@pytest.fixture()
def seller_token(client):
    return login(client, phone="13800000002")


@pytest.fixture()
def admin_token(client):
    return admin_login(client)
