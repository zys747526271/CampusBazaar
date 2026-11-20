"""认证与鉴权：401/403 语义、验证码一次性、管理员锁定。"""
from __future__ import annotations

from conftest import headers, login


def test_public_endpoints_are_anonymous(client):
    assert client.get("/api/products").status_code == 200
    body = client.get("/api/products").get_json()
    assert body["success"] is True
    assert set(body["data"]) >= {"items", "total", "page", "per_page", "pages"}


def test_missing_token_returns_401(client):
    assert client.get("/api/carts").status_code == 401
    resp = client.get("/api/carts", headers={"Authorization": "Bearer not-a-token"})
    assert resp.status_code == 401
    assert resp.get_json()["code"] == "UNAUTHORIZED"


def test_user_token_on_admin_api_returns_403(client):
    token = login(client)
    resp = client.get("/api/admin/stats", headers=headers(token))
    assert resp.status_code == 403
    assert resp.get_json()["code"] == "FORBIDDEN"


def test_admin_token_on_user_api_returns_403(client):
    token = client.post("/api/auth/admin/login", json={"username": "admin", "password": "Admin12345"}).get_json()[
        "data"
    ]["token"]
    assert client.get("/api/carts", headers=headers(token)).status_code == 403


def test_weak_password_rejected(client):
    client.post("/api/auth/captcha", json={"phone": "13900000003", "scene": "register"})
    resp = client.post(
        "/api/auth/register",
        json={"phone": "13900000003", "password": "12345678", "nickname": "弱密码", "code": "123456",
              "agree_terms": True},
    )
    assert resp.status_code == 422
    assert "password" in resp.get_json()["data"]


def test_captcha_single_use(client):
    phone = "13900000009"
    code = client.post("/api/auth/captcha", json={"phone": phone, "scene": "register"}).get_json()["data"]["dev_code"]
    payload = {"phone": phone, "password": "abc12345", "nickname": "验证码用户", "code": code, "agree_terms": True}
    assert client.post("/api/auth/register", json=payload).status_code == 201
    again = client.post("/api/auth/register", json=payload)
    assert again.status_code == 400


def test_admin_login_lockout(client):
    for _ in range(5):
        assert client.post("/api/auth/admin/login", json={"username": "ghost", "password": "bad-pass"}).status_code == 400
    locked = client.post("/api/auth/admin/login", json={"username": "ghost", "password": "bad-pass"})
    assert locked.status_code == 429
    assert locked.get_json()["data"]["retry_after"] > 0


def test_seller_endpoint_requires_seller_identity(client):
    token = login(client)  # 买家
    assert client.get("/api/seller/overview", headers=headers(token)).status_code == 403
    assert client.get("/api/seller/overview").status_code == 401
