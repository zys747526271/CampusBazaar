"""接口覆盖巡检：把每个模块至少打一遍，捕捉 500/未预期 4xx。

用法：python scripts/api_sweep.py [base_url]
只在本地演示环境运行；会创建并清理测试数据。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import requests

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000").rstrip("/")
API = f"{BASE}/api"
ROOT = Path(__file__).resolve().parent.parent
issues: list[str] = []
checked = 0


def accounts() -> dict:
    text = (ROOT / "instance" / "demo-accounts.txt").read_text(encoding="utf-8")
    phones = {p: pwd for p, _n, pwd in re.findall(r"(1\d{10})\s+(\S+)\s+密码：(\S+)", text)}
    admin = re.search(r"admin\s+密码：(\S+)", text).group(1)
    return {"phones": phones, "admin": admin}


def call(method: str, path: str, token: str | None = None, expect: tuple[int, ...] = (200, 201), **kwargs):
    global checked
    checked += 1
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = requests.request(method, f"{API}{path}", headers=headers, timeout=15, **kwargs)
    if resp.status_code not in expect:
        issues.append(f"{method} {path} -> {resp.status_code} {resp.text[:160]}")
    return resp


def main() -> int:
    data = accounts()
    buyer = "13800000004"
    seller = "13800000001"
    buyer_token = requests.post(f"{API}/auth/login", json={"phone": buyer, "password": data["phones"][buyer]}, timeout=10).json()["data"]["token"]
    seller_token = requests.post(f"{API}/auth/login", json={"phone": seller, "password": data["phones"][seller]}, timeout=10).json()["data"]["token"]
    admin_token = requests.post(f"{API}/auth/admin/login", json={"username": "admin", "password": data["admin"]}, timeout=10).json()["data"]["token"]

    # 公开
    for path in ("/meta/home", "/meta/filters", "/meta/options", "/tags", "/products", "/products/1",
                 "/products/1/comments", "/products/1/related", "/shops/1", "/shops/1/products",
                 "/search/suggest?keyword=教材", "/health"):
        call("GET", path)

    # 买家
    for path in ("/auth/profile", "/carts", "/carts/count", "/carts/checkout", "/orders", "/orders/counts",
                 "/favorites", "/history", "/comments/mine", "/messages", "/messages/unread",
                 "/addresses", "/balance", "/balance/logs"):
        call("GET", path, buyer_token, expect=(200, 400))  # checkout 无勾选时 400 属预期

    address = call("POST", "/addresses", buyer_token, json={"name": "巡检", "phone": buyer, "campus_area": "东校区", "detail": "1 号楼 101"}).json()["data"]
    call("PUT", f"/addresses/{address['id']}", buyer_token, json={"name": "巡检改", "phone": buyer, "campus_area": "东校区", "detail": "1 号楼 102"})
    call("PUT", f"/addresses/{address['id']}/default", buyer_token)
    call("DELETE", f"/addresses/{address['id']}", buyer_token)

    call("POST", "/favorites", buyer_token, json={"product_id": 1})
    call("DELETE", "/favorites/1", buyer_token)
    call("DELETE", "/history", buyer_token)
    call("POST", "/messages/read-all", buyer_token)
    call("POST", "/reports", buyer_token, expect=(201, 400), json={"target_type": "product", "target_id": 2, "reason": "虚假信息", "detail": "巡检"})
    call("GET", "/notifications-not-exist", buyer_token, expect=(404,))

    # 卖家
    for path in ("/seller/overview", "/seller/products", "/seller/orders", "/seller/categories", "/seller/comments"):
        call("GET", path, seller_token)

    product = call("POST", "/seller/products", seller_token, json={
        "name": "巡检临时商品", "description": "巡检用", "price": "9.90", "quantity": 2,
        "condition": "几乎全新", "location": "图书馆", "tag_id": 1,
        "images": ["/static/uploads/demo/p1-1.svg"],
    }).json()["data"]
    call("PUT", f"/seller/products/{product['id']}", seller_token, json={
        "name": "巡检临时商品改", "description": "巡检用", "price": "8.80", "quantity": 2,
        "condition": "全新", "location": "图书馆", "tag_id": 1,
        "images": ["/static/uploads/demo/p1-1.svg"],
    })
    call("POST", f"/seller/products/{product['id']}/toggle", seller_token)
    call("POST", f"/seller/products/{product['id']}/toggle", seller_token)
    call("GET", f"/seller/products/{product['id']}", seller_token)
    call("DELETE", f"/seller/products/{product['id']}", seller_token)

    category = call("POST", "/seller/categories", seller_token, json={"name": "巡检分类"}).json()["data"]
    call("PUT", f"/seller/categories/{category['id']}", seller_token, json={"name": "巡检分类改", "sort_order": 9})
    call("DELETE", f"/seller/categories/{category['id']}", seller_token)

    # 管理员
    for path in ("/admin/stats", "/admin/users", "/admin/users/1", "/admin/users/1/orders", "/admin/users/1/products",
                 "/admin/sellers", "/admin/sellers/1/products", "/admin/products", "/admin/products/1",
                 "/admin/products/tags", "/admin/comments", "/admin/orders", "/admin/orders/1",
                 "/admin/orders/summary", "/admin/tags", "/admin/banners", "/admin/reports",
                 "/admin/audit-logs"):
        call("GET", path, admin_token)

    call("POST", "/admin/jobs/run", admin_token)
    call("PUT", "/admin/products/1/feature", admin_token, json={"featured": False})
    call("POST", "/admin/products/batch-status", admin_token, json={"ids": [2], "status": "已通过", "reason": ""})

    tag = call("POST", "/admin/tags", admin_token, json={"name": "巡检平台分类", "sort_order": 99}).json()["data"]
    call("PUT", f"/admin/tags/{tag['id']}", admin_token, json={"name": "巡检平台分类改", "sort_order": 99, "is_active": False})
    call("DELETE", f"/admin/tags/{tag['id']}", admin_token)

    banner = call("POST", "/admin/banners", admin_token, json={
        "title": "巡检轮播", "image_url": "/static/uploads/demo/banner-1.svg", "link_url": "/products", "sort_order": 99,
    }).json()["data"]
    call("PUT", f"/admin/banners/{banner['id']}", admin_token, json={
        "title": "巡检轮播改", "image_url": "/static/uploads/demo/banner-1.svg", "link_url": "/products",
        "sort_order": 99, "is_active": False,
    })
    call("DELETE", f"/admin/banners/{banner['id']}", admin_token)

    for kind in ("users", "orders", "products"):
        resp = call("GET", f"/admin/export/{kind}", admin_token)
        if not resp.headers.get("Content-Type", "").startswith("text/csv"):
            issues.append(f"export {kind} 返回类型异常: {resp.headers.get('Content-Type')}")

    print(f"\n检查 {checked} 个请求，问题 {len(issues)} 个")
    for item in issues:
        print(" -", item)
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
