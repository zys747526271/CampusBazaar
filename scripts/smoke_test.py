"""接口冒烟脚本：按 PRD 验收用例走一遍完整交易闭环（可重复运行）。

用法：python scripts/smoke_test.py [base_url]
默认 http://127.0.0.1:5000。演示账号密码从 instance/demo-accounts.txt 读取
（由 backend.seed 生成），不会与种子数据脱节。

每次运行会以卖家身份发布一件测试商品，走完「加购 → 下单 → 收款 → 发货 → 收货 → 评价」
后删除，因此不会污染演示商品列表。
"""
from __future__ import annotations

import random
import re
import sys
import uuid
from pathlib import Path

import requests

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000").rstrip("/")
API = f"{BASE}/api"
ROOT = Path(__file__).resolve().parent.parent
RUN = uuid.uuid4().hex[:6]

passed = 0
failed: list[str] = []


def load_demo_accounts() -> dict:
    """从种子生成的账号文件里取账号密码，避免脚本里硬编码。"""
    accounts = {"buyer": ("13800000004", ""), "seller": ("13800000001", ""), "admin": ("admin", "")}
    path = ROOT / "instance" / "demo-accounts.txt"
    if not path.exists():
        return accounts
    text = path.read_text(encoding="utf-8")
    for phone, _name, password in re.findall(r"(1\d{10})\s+(\S+)\s+密码：(\S+)", text):
        if phone == "13800000004":
            accounts["buyer"] = (phone, password)
        elif phone == "13800000001":
            accounts["seller"] = (phone, password)
    match = re.search(r"admin\s+密码：(\S+)", text)
    if match:
        accounts["admin"] = ("admin", match.group(1))
    return accounts


def check(name: str, condition: bool, extra: str = "") -> None:
    global passed
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed.append(name)
        print(f"  [FAIL] {name} {extra}")


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def login(phone: str, password: str) -> str:
    resp = requests.post(f"{API}/auth/login", json={"phone": phone, "password": password}, timeout=10)
    payload = resp.json()
    check(f"登录 {phone}", resp.status_code == 200, payload.get("message", ""))
    return payload.get("data", {}).get("token", "")


def main() -> int:
    accounts = load_demo_accounts()
    buyer_phone, buyer_pwd = accounts["buyer"]
    seller_phone, seller_pwd = accounts["seller"]
    admin_user, admin_pwd = accounts["admin"]
    if not buyer_pwd or not admin_pwd:
        print("未找到演示账号文件，请先启动后端（会自动灌入演示数据）。")
        return 2

    print(f"\n== CampusBazaar 冒烟测试 @ {BASE}（run {RUN}）==\n")

    # ---------- AC-01 游客浏览 ----------
    for path in ("/meta/home", "/products", "/products/1", "/tags", "/meta/filters"):
        resp = requests.get(f"{API}{path}", timeout=10)
        check(f"游客访问 {path} -> 200", resp.status_code == 200, f"status={resp.status_code}")
    home = requests.get(f"{API}/meta/home", timeout=10).json()["data"]
    check("首页三区块有数据", all(home["blocks"][k] for k in ("recommended", "hot", "latest")))
    check("首页分类/轮播非空", bool(home["tags"]) and bool(home["banners"]))

    # ---------- 列表筛选 ----------
    cheap = requests.get(f"{API}/products", params={"sort": "price", "order": "asc", "per_page": 5}, timeout=10).json()
    prices = [item["price"] for item in cheap["data"]["items"]]
    check("价格升序排序生效", prices == sorted(prices), str(prices))
    filtered = requests.get(f"{API}/products", params={"tag_id": home["tags"][0]["id"]}, timeout=10).json()
    check("按分类筛选可用", filtered["data"]["total"] >= 1, str(filtered["data"]["total"]))
    check("列表统一返回 items/total", "items" in filtered["data"] and "total" in filtered["data"])

    # ---------- AC-05/06 验证码 ----------
    phone = f"139{random.randint(10000000, 99999999)}"
    resp = requests.post(f"{API}/auth/captcha", json={"phone": phone, "scene": "register"}, timeout=10)
    code = resp.json().get("data", {}).get("dev_code", "")
    check("获取验证码（dev 回显）", resp.status_code == 200 and len(code) == 6, resp.text[:120])

    bad = requests.post(
        f"{API}/auth/register",
        json={"phone": phone, "password": "abc12345", "nickname": "冒烟测试", "code": "000000", "agree_terms": True},
        timeout=10,
    )
    check("错误验证码注册 -> 400", bad.status_code == 400, f"status={bad.status_code}")

    ok_reg = requests.post(
        f"{API}/auth/register",
        json={"phone": phone, "password": "abc12345", "nickname": f"冒烟{RUN}", "code": code, "agree_terms": True},
        timeout=10,
    )
    check("正确验证码注册 -> 201", ok_reg.status_code == 201, ok_reg.text[:160])
    new_token = ok_reg.json().get("data", {}).get("token", "")

    reuse = requests.post(
        f"{API}/auth/register",
        json={"phone": phone, "password": "abc12345", "nickname": "冒烟", "code": code, "agree_terms": True},
        timeout=10,
    )
    check("同一验证码二次使用 -> 400", reuse.status_code == 400, f"status={reuse.status_code}")

    weak = requests.post(
        f"{API}/auth/register",
        json={"phone": "13900001235", "password": "12345678", "nickname": "弱密码", "code": "123456", "agree_terms": True},
        timeout=10,
    )
    check("弱密码被拒 -> 422", weak.status_code == 422, f"status={weak.status_code}")

    # ---------- 登录与令牌隔离 ----------
    buyer_token = login(buyer_phone, buyer_pwd)
    seller_token = login(seller_phone, seller_pwd)
    admin_login = requests.post(
        f"{API}/auth/admin/login", json={"username": admin_user, "password": admin_pwd}, timeout=10
    )
    admin_token = admin_login.json().get("data", {}).get("token", "")
    check("管理员登录", admin_login.status_code == 200, admin_login.text[:120])

    check(
        "用户令牌访问管理接口 -> 403",
        requests.get(f"{API}/admin/stats", headers=auth(buyer_token), timeout=10).status_code == 403,
    )
    check(
        "管理员令牌访问用户接口 -> 403",
        requests.get(f"{API}/carts", headers=auth(admin_token), timeout=10).status_code == 403,
    )
    check("未登录访问购物车 -> 401", requests.get(f"{API}/carts", timeout=10).status_code == 401)
    check(
        "普通买家访问卖家接口 -> 403",
        requests.get(f"{API}/seller/overview", headers=auth(new_token), timeout=10).status_code == 403,
    )

    # ---------- 卖家发布商品 ----------
    filters = requests.get(f"{API}/meta/filters", timeout=10).json()["data"]
    product_name = f"冒烟测试商品 {RUN}"
    publish = requests.post(
        f"{API}/seller/products",
        json={
            "name": product_name,
            "description": "自动化冒烟测试创建的临时商品，测试结束会自动删除。",
            "price": "9.90",
            "original_price": "29.90",
            "quantity": 2,
            "condition": "几乎全新",
            "location": "图书馆门口",
            "tag_id": filters["tags"][0]["id"],
            "images": ["/static/uploads/demo/p1-1.svg"],
        },
        headers=auth(seller_token),
        timeout=10,
    )
    check("卖家发布商品", publish.status_code == 200, publish.text[:160])
    product = publish.json()["data"]
    product_id = product["id"]
    check("发布后状态为已通过（本地自动审核）", product["status"] == "已通过", product["status"])

    found = requests.get(f"{API}/products", params={"keyword": product_name}, timeout=10).json()["data"]
    check("新商品可被搜索到", found["total"] == 1, str(found["total"]))

    # ---------- 收藏 / 购物车 / 下单 ----------
    check(
        "收藏商品",
        requests.post(
            f"{API}/favorites", json={"product_id": product_id}, headers=auth(buyer_token), timeout=10
        ).status_code
        == 200,
    )
    requests.delete(f"{API}/carts", headers=auth(buyer_token), timeout=10)
    add = requests.post(
        f"{API}/carts", json={"product_id": product_id, "quantity": 1}, headers=auth(buyer_token), timeout=10
    )
    check("加入购物车", add.status_code == 200, add.text[:120])

    preview = requests.post(
        f"{API}/orders/preview",
        json={"source": "cart", "pay_method": "线下", "delivery_type": "面交"},
        headers=auth(buyer_token),
        timeout=10,
    )
    preview_amount = preview.json().get("data", {}).get("total_amount")
    check("结算预览金额 = 商品价", preview_amount == 9.9, str(preview_amount))

    idem = {"Idempotency-Key": f"smoke-{RUN}"}
    order_payload = {
        "source": "cart",
        "pay_method": "线下",
        "delivery_type": "面交",
        "receiver_name": "赵一鸣",
        "receiver_phone": buyer_phone,
        "address_text": "图书馆一楼",
        "remark": "冒烟测试",
    }
    order_resp = requests.post(f"{API}/orders", json=order_payload, headers={**auth(buyer_token), **idem}, timeout=10)
    check("创建订单 -> 201", order_resp.status_code == 201, order_resp.text[:200])
    order = order_resp.json()["data"]["orders"][0]
    order_id = order["id"]
    check(
        "订单号符合 CB+时间戳格式",
        order["order_no"].startswith("CB") and len(order["order_no"]) >= 18,
        order["order_no"],
    )

    replay = requests.post(f"{API}/orders", json=order_payload, headers={**auth(buyer_token), **idem}, timeout=10)
    check(
        "重复提交命中幂等",
        replay.status_code == 201 and replay.headers.get("X-Idempotent-Replay") == "true",
        replay.text[:120],
    )

    cart_after = requests.get(f"{API}/carts", headers=auth(buyer_token), timeout=10).json()["data"]
    check("AC-14 下单后已购项从购物车移除", all(i["product"]["id"] != product_id for i in cart_after["items"]))
    seller_view = requests.get(
        f"{API}/seller/products/{product_id}", headers=auth(seller_token), timeout=10
    ).json()["data"]
    check("AC-14 库存扣减", seller_view["quantity"] == 1, str(seller_view["quantity"]))

    check(
        "AC-08 待付款直接确认收货 -> 409",
        requests.post(f"{API}/orders/{order_id}/confirm", headers=auth(buyer_token), timeout=10).status_code == 409,
    )
    check(
        "越权操作他人订单 -> 403",
        requests.post(f"{API}/orders/{order_id}/pay", headers=auth(new_token), timeout=10).status_code == 403,
    )

    # ---------- 履约 ----------
    paid = requests.post(f"{API}/seller/orders/{order_id}/confirm-paid", headers=auth(seller_token), timeout=10)
    check("卖家确认线下收款", paid.status_code == 200, paid.text[:160])
    ship = requests.post(
        f"{API}/seller/orders/{order_id}/ship",
        json={"note": "图书馆门口面交"},
        headers=auth(seller_token),
        timeout=10,
    )
    check("卖家发货", ship.status_code == 200, ship.text[:160])
    done = requests.post(f"{API}/orders/{order_id}/confirm", headers=auth(buyer_token), timeout=10)
    check("买家确认收货", done.status_code == 200, done.text[:160])
    detail = requests.get(f"{API}/orders/{order_id}", headers=auth(buyer_token), timeout=10).json()["data"]
    check(
        "订单状态时间线完整",
        len(detail["timeline"]) >= 3 and detail["status"] == "已完成",
        str(len(detail["timeline"])),
    )

    comment = requests.post(
        f"{API}/comments",
        json={"order_id": order_id, "product_id": product_id, "rating": 5, "content": "冒烟测试评价，很满意"},
        headers=auth(buyer_token),
        timeout=10,
    )
    check("已购用户发表评价", comment.status_code == 201, comment.text[:160])
    dup = requests.post(
        f"{API}/comments",
        json={"order_id": order_id, "product_id": product_id, "rating": 4, "content": "重复评价"},
        headers=auth(buyer_token),
        timeout=10,
    )
    check("重复评价 -> 400", dup.status_code == 400, f"status={dup.status_code}")
    summary = requests.get(f"{API}/products/{product_id}/comments", timeout=10).json()["data"]["summary"]
    check("商品评分统计生效", summary["total"] >= 1 and summary["average"] > 0, str(summary))

    # ---------- 卖家中心 ----------
    overview = requests.get(f"{API}/seller/overview", headers=auth(seller_token), timeout=10)
    check("卖家经营概览", overview.status_code == 200 and "today_sales" in overview.json()["data"])
    cat = requests.post(
        f"{API}/seller/categories", json={"name": f"冒烟分类{RUN}"}, headers=auth(seller_token), timeout=10
    )
    check("卖家创建自定义分类", cat.status_code == 200, cat.text[:120])
    cat_id = cat.json().get("data", {}).get("id")
    if cat_id:
        deleted = requests.delete(f"{API}/seller/categories/{cat_id}", headers=auth(seller_token), timeout=10)
        check("卖家删除空分类", deleted.status_code == 200, deleted.text[:120])

    # ---------- 管理员 ----------
    stats = requests.get(f"{API}/admin/stats", headers=auth(admin_token), timeout=10)
    check("管理后台概览", stats.status_code == 200 and "trend" in stats.json()["data"])
    admin_products = requests.get(
        f"{API}/admin/products", params={"keyword": product_name}, headers=auth(admin_token), timeout=10
    )
    check("后台可检索到商品", admin_products.json()["data"]["total"] == 1, admin_products.text[:120])
    hide = requests.put(
        f"{API}/admin/comments/{comment.json()['data']['id']}/visibility",
        json={"hidden": True, "reason": "冒烟测试"},
        headers=auth(admin_token),
        timeout=10,
    )
    check("管理员隐藏评价", hide.status_code == 200, hide.text[:120])
    visible_after = requests.get(f"{API}/products/{product_id}/comments", timeout=10).json()["data"]["total"]
    check("隐藏后前台不可见", visible_after == 0, str(visible_after))

    # ---------- AC-13 管理员登录锁定 ----------
    lock_user = f"probe-{RUN}"
    for _ in range(5):
        requests.post(f"{API}/auth/admin/login", json={"username": lock_user, "password": "wrong-pass"}, timeout=10)
    locked = requests.post(f"{API}/auth/admin/login", json={"username": lock_user, "password": "wrong-pass"}, timeout=10)
    check("AC-13 连续失败后锁定 -> 429", locked.status_code == 429, f"status={locked.status_code}")

    # ---------- 收尾：删除测试商品 ----------
    cleanup = requests.delete(f"{API}/seller/products/{product_id}", headers=auth(seller_token), timeout=10)
    check("删除测试商品", cleanup.status_code == 200, cleanup.text[:120])

    page = requests.get(f"{BASE}/dev/captchas", timeout=10)
    check("本地验证码页面可访问", page.status_code == 200)

    print(f"\n通过 {passed} 项，失败 {len(failed)} 项")
    if failed:
        print("失败项：" + "、".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
