"""可选的视觉巡检脚本：用无头 Edge + CDP 登录后批量截图。

依赖：websocket-client、本机安装 Edge/Chrome。仅开发期使用，不参与构建。

用法：
    python scripts/visual_check.py [base_url] [out_dir]
"""
from __future__ import annotations

import base64
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import requests
import websocket

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000").rstrip("/")
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "instance/screens")
ROOT = Path(__file__).resolve().parent.parent
ACCOUNTS = ROOT / "instance" / "demo-accounts.txt"

EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"/usr/bin/google-chrome",
    r"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]


class CDP:
    def __init__(self, ws_url: str) -> None:
        self.ws = websocket.create_connection(ws_url, timeout=30)
        self.msg_id = 0

    def call(self, method: str, params: dict | None = None):
        self.msg_id += 1
        self.ws.send(json.dumps({"id": self.msg_id, "method": method, "params": params or {}}))
        while True:
            message = json.loads(self.ws.recv())
            if message.get("id") == self.msg_id:
                return message.get("result", {})

    def eval(self, expression: str, await_promise: bool = True):
        result = self.call(
            "Runtime.evaluate",
            {"expression": expression, "awaitPromise": await_promise, "returnByValue": True},
        )
        return result.get("result", {}).get("value")

    def goto(self, url: str, wait: float = 2.2) -> None:
        self.call("Page.navigate", {"url": url})
        time.sleep(wait)

    def shot(self, path: Path, height: int = 1000) -> None:
        self.call("Emulation.setDeviceMetricsOverride", {"width": 1440, "height": height, "deviceScaleFactor": 1, "mobile": False})
        data = self.call("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(base64.b64decode(data["data"]))


def read_accounts() -> dict:
    """从 demo-accounts.txt 解析手机号与密码（格式：手机号 昵称 密码：xxx）。"""
    import re

    text = ACCOUNTS.read_text(encoding="utf-8") if ACCOUNTS.exists() else ""
    phones = {phone: pwd for phone, _name, pwd in re.findall(r"(1\d{10})\s+(\S+)\s+密码：(\S+)", text)}
    match = re.search(r"admin\s+密码：(\S+)", text)
    return {"phones": phones, "admin": match.group(1) if match else ""}


def main() -> int:
    edge = next((p for p in EDGE_CANDIDATES if Path(p).exists()), None)
    if not edge:
        print("未找到 Edge/Chrome，跳过视觉巡检")
        return 0
    if not ACCOUNTS.exists():
        print("缺少演示账号文件，请先启动后端")
        return 1

    accounts = read_accounts()
    buyer = next((p for p in accounts["phones"] if p.endswith("4")), "")
    seller = next((p for p in accounts["phones"] if p.endswith("1")), "")
    if not buyer or not seller:
        print("演示账号解析失败")
        return 1

    profile = Path(tempfile.mkdtemp(prefix="cb-visual-"))
    proc = subprocess.Popen(
        [
            edge,
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--no-first-run",
            "--remote-debugging-port=9333",
            f"--user-data-dir={profile}",
            "--window-size=1440,1000",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        target = None
        for _ in range(30):
            try:
                targets = requests.get("http://127.0.0.1:9333/json", timeout=2).json()
                target = next((t for t in targets if t.get("type") == "page"), None)
                if target:
                    break
            except requests.RequestException:
                pass
            time.sleep(0.4)
        if not target:
            print("无法连接无头浏览器")
            return 1

        cdp = CDP(target["webSocketDebuggerUrl"])
        cdp.call("Page.enable")
        cdp.call("Runtime.enable")

        cdp.goto(f"{BASE}/")

        def api_login(path: str, payload: dict) -> str:
            resp = requests.post(f"{BASE}/api{path}", json=payload, timeout=10)
            data = resp.json()
            return (data.get("data") or {}).get("token", "")

        buyer_token = api_login("/auth/login", {"phone": buyer, "password": accounts["phones"][buyer]})
        print("买家登录：", bool(buyer_token))

        # 预置购物车，便于看到有数据的购物车与结算页
        headers = {"Authorization": f"Bearer {buyer_token}"}
        products = requests.get(f"{BASE}/api/products", params={"per_page": 6}, timeout=10).json()["data"]["items"]
        requests.delete(f"{BASE}/api/carts", headers=headers, timeout=10)
        for item in products[:2]:
            requests.post(
                f"{BASE}/api/carts",
                json={"product_id": item["id"], "quantity": 1},
                headers=headers,
                timeout=10,
            )

        # 保证有收货地址，便于截取快递结算态
        existing = requests.get(f"{BASE}/api/addresses", headers=headers, timeout=10).json()["data"]["items"]
        if not existing:
            requests.post(
                f"{BASE}/api/addresses",
                json={"name": "赵一鸣", "phone": buyer, "campus_area": "东校区", "detail": "1 栋 102", "is_default": True},
                headers=headers,
                timeout=10,
            )

        cdp.eval(f"localStorage.setItem('cb_token', '{buyer_token}'); true", await_promise=False)

        pages = [
            ("list", "/products", 1300),
            ("detail", "/products/3", 1300),
            ("shop", "/shops/1", 1500),
            ("cart", "/cart", 1000),
            ("checkout", "/checkout", 1100),
            ("orders", "/orders", 1000),
            ("order-detail", "/orders/1", 1200),
            ("favorites", "/favorites", 900),
            ("profile", "/profile", 900),
            ("messages", "/messages", 900),
            ("balance", "/balance", 900),
        ]
        for name, path, height in pages:
            cdp.goto(f"{BASE}{path}")
            cdp.shot(OUT / f"{name}.png", height)
            print("截图", name)
            if name == "checkout":
                cdp.eval("[...document.querySelectorAll('.choice')].find(b => b.textContent.includes('快递'))?.click(); true")
                time.sleep(1.8)
                cdp.shot(OUT / "checkout-express.png", 1100)
                print("截图 checkout-express")

        # 卖家视角
        seller_token = api_login("/auth/login", {"phone": seller, "password": accounts["phones"][seller]})
        print("卖家登录：", bool(seller_token))
        cdp.eval(f"localStorage.setItem('cb_token', '{seller_token}'); true", await_promise=False)
        for name, path, height in [
            ("seller-dashboard", "/seller", 1200),
            ("seller-products", "/seller/products", 1000),
            ("seller-form", "/seller/products/new", 1300),
            ("seller-orders", "/seller/orders", 1000),
        ]:
            cdp.goto(f"{BASE}{path}")
            cdp.shot(OUT / f"{name}.png", height)
            print("截图", name)
            if name == "checkout":
                cdp.eval("[...document.querySelectorAll('.choice')].find(b => b.textContent.includes('快递'))?.click(); true")
                time.sleep(1.8)
                cdp.shot(OUT / "checkout-express.png", 1100)
                print("截图 checkout-express")

        # 管理员
        admin_token = api_login("/auth/admin/login", {"username": "admin", "password": accounts["admin"]})
        print("管理员登录：", bool(admin_token))
        cdp.eval(f"localStorage.setItem('cb_admin_token', '{admin_token}'); true", await_promise=False)
        for name, path, height in [
            ("admin-dashboard", "/admin", 1200),
            ("admin-products", "/admin/products", 1000),
            ("admin-users", "/admin/users", 1000),
            ("admin-orders", "/admin/orders", 1000),
            ("admin-comments", "/admin/comments", 1000),
        ]:
            cdp.goto(f"{BASE}{path}")
            cdp.shot(OUT / f"{name}.png", height)
            print("截图", name)
            if name == "checkout":
                cdp.eval("[...document.querySelectorAll('.choice')].find(b => b.textContent.includes('快递'))?.click(); true")
                time.sleep(1.8)
                cdp.shot(OUT / "checkout-express.png", 1100)
                print("截图 checkout-express")

        # 清理预置购物车，避免污染演示数据
        requests.delete(f"{BASE}/api/carts", headers=headers, timeout=10)
        print(f"截图输出目录：{OUT}")
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        shutil.rmtree(profile, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
