"""生成 README 使用的功能截图（无头 Edge + CDP，真实页面实拍）。

依赖：websocket-client、requests、Pillow；本机需安装 Edge/Chrome。
产出：docs/assets/screenshots/*.png（已压缩，宽度 1400）。

用法：
    # 先启动后端（托管 dist）
    python -m backend.dev --host 127.0.0.1 --port 5001 --serve-dist
    python scripts/capture_screenshots.py [base_url]
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
from PIL import Image

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5001").rstrip("/")
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "assets" / "screenshots"
TMP = ROOT / "instance" / "shots-raw"
WIDTH = 1440
SCALE = 2  # 设备像素比，保证中文小字清晰
TARGET_WIDTH = 1400

EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"/usr/bin/google-chrome",
    r"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]

BUYER, SELLER, ADMIN = "13800000004", "13800000001", "admin"


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

    def eval(self, expression: str):
        result = self.call(
            "Runtime.evaluate",
            {"expression": expression, "awaitPromise": True, "returnByValue": True},
        )
        return result.get("result", {}).get("value")

    def goto(self, path: str, wait: float = 2.4) -> None:
        self.call("Page.navigate", {"url": f"{BASE}{path}"})
        time.sleep(wait)

    def viewport(self, height: int) -> None:
        self.call(
            "Emulation.setDeviceMetricsOverride",
            {"width": WIDTH, "height": height, "deviceScaleFactor": SCALE, "mobile": False},
        )

    def shot(self, path: Path) -> None:
        data = self.call("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(base64.b64decode(data["data"]))

    def click_text(self, text: str, scope: str = "button,a") -> str:
        return self.eval(
            f"""(() => {{
              const want = {json.dumps(text, ensure_ascii=False)};
              const nodes = [...document.querySelectorAll({json.dumps(scope)})]
                .filter((n) => n.offsetParent !== null);
              const hit = nodes.find((n) => (n.textContent || '').replace(/\\s+/g, '').includes(want));
              if (!hit) return 'MISS';
              hit.scrollIntoView({{ block: 'center' }});
              hit.click();
              return 'OK';
            }})()"""
        )

    def scroll_to(self, selector: str, offset: int = -96) -> str:
        return self.eval(
            f"""(() => {{
              const el = document.querySelector({json.dumps(selector)});
              if (!el) return 'MISS';
              const y = el.getBoundingClientRect().top + window.scrollY + ({offset});
              window.scrollTo(0, Math.max(0, y));
              return 'OK';
            }})()"""
        )

    def scroll_to_text(self, text: str, offset: int = -96) -> str:
        return self.eval(
            f"""(() => {{
              const want = {json.dumps(text, ensure_ascii=False)};
              const el = [...document.querySelectorAll('h1,h2,h3,button,a,p,span,li,td,div,section')]
                .filter((n) => n.offsetParent !== null)
                .find((n) => (n.textContent || '').replace(/\\s+/g, '') === want);
              if (!el) return 'MISS';
              const y = el.getBoundingClientRect().top + window.scrollY + ({offset});
              window.scrollTo(0, Math.max(0, y));
              return 'OK';
            }})()"""
        )


def login(phone: str, password: str, admin: bool = False) -> str:
    path = "/api/auth/admin/login" if admin else "/api/auth/login"
    body = {"username": phone, "password": password} if admin else {"phone": phone, "password": password}
    data = requests.post(f"{BASE}{path}", json=body, timeout=10).json()
    return (data.get("data") or {}).get("token", "")


def read_password() -> tuple[str, str]:
    text = (ROOT / "instance" / "demo-accounts.txt").read_text(encoding="utf-8")
    import re

    user_pwd = re.search(r"13800000004\s+\S+\s+密码：(\S+)", text)
    admin_pwd = re.search(r"admin\s+密码：(\S+)", text)
    if not user_pwd or not admin_pwd:
        raise SystemExit("无法从 instance/demo-accounts.txt 解析密码，请先启动后端生成演示数据")
    return user_pwd.group(1), admin_pwd.group(1)


def prepare_cart(buyer_token: str) -> None:
    """购物车放两件商品：一件「自提+包邮」，一件「快递带运费」，便于切两种结算态。"""
    headers = {"Authorization": f"Bearer {buyer_token}"}
    requests.delete(f"{BASE}/api/carts", headers=headers, timeout=10)
    for product_id in (1, 3):
        requests.post(
            f"{BASE}/api/carts",
            json={"product_id": product_id, "quantity": 1},
            headers=headers,
            timeout=10,
        )
    # 演示余额若不足以覆盖购物车，用演示充值补齐，避免截图停在「余额不足」态
    balance = requests.get(f"{BASE}/api/balance", headers=headers, timeout=10).json()["data"]["amount"]
    if balance < 2000:
        requests.post(
            f"{BASE}/api/balance/recharge",
            json={"amount": f"{2000 - balance + 500:.2f}"},
            headers=headers,
            timeout=10,
        )


def main() -> int:
    edge = next((p for p in EDGE_CANDIDATES if Path(p).exists()), None)
    if not edge:
        print("未找到 Edge/Chrome")
        return 1
    if requests.get(f"{BASE}/api/health", timeout=5).status_code != 200:
        print("后端未就绪")
        return 1

    user_pwd, admin_pwd = read_password()
    buyer_token = login(BUYER, user_pwd)
    seller_token = login(SELLER, user_pwd)
    admin_token = login(ADMIN, admin_pwd, admin=True)
    prepare_cart(buyer_token)

    profile = Path(tempfile.mkdtemp(prefix="cb-shot-"))
    proc = subprocess.Popen(
        [
            edge,
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--no-first-run",
            f"--window-size={WIDTH},{900}",
            "--remote-debugging-port=9344",
            f"--user-data-dir={profile}",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        target = None
        for _ in range(40):
            try:
                pages = requests.get("http://127.0.0.1:9344/json", timeout=2).json()
                target = next((t for t in pages if t.get("type") == "page"), None)
                if target:
                    break
            except requests.RequestException:
                pass
            time.sleep(0.3)
        if not target:
            print("无法连接无头浏览器")
            return 1

        cdp = CDP(target["webSocketDebuggerUrl"])
        cdp.call("Page.enable")
        cdp.call("Runtime.enable")
        cdp.goto("/")

        def use(token: str, key: str) -> None:
            cdp.eval(f"localStorage.setItem('{key}', '{token}'); true")

        def capture(name: str, height: int) -> None:
            cdp.viewport(height)
            cdp.shot(TMP / f"{name}.png")
            print("拍摄", name)

        # 1. 列表页：履约筛选 + 卡片小标
        use(buyer_token, "cb_token")
        cdp.goto("/products")
        cdp.click_text("支持自提", ".chip")
        time.sleep(1.2)
        cdp.click_text("仅看包邮", ".chip")
        time.sleep(1.4)
        cdp.eval("window.scrollTo(0,0); true")
        time.sleep(0.5)
        capture("01-list-filter", 1150)

        # 2. 商品详情：履约说明区（自提点 / 运费）
        cdp.goto("/products/3")
        cdp.eval("window.scrollTo(0,0); true")
        time.sleep(0.9)
        capture("02-product-detail", 900)

        # 3. 结算页：自提态
        cdp.goto("/checkout", 3.0)
        cdp.eval("window.scrollTo(0,0); true")
        time.sleep(0.6)
        capture("03-checkout-pickup", 1200)

        # 4. 结算页：快递态（仅地址簿 + 仅余额）
        cdp.click_text("快递", ".choice")
        time.sleep(2.0)
        cdp.eval("window.scrollTo(0,0); true")
        time.sleep(0.4)
        capture("04-checkout-express", 1200)

        # 5. 卖家商品编辑：履约方式与运费设置
        use(seller_token, "cb_token")
        cdp.goto("/seller/products/3/edit", 3.0)
        cdp.scroll_to_text("履约方式", -120)
        time.sleep(0.8)
        capture("05-seller-product-form", 760)

        # 6. 卖家订单：待补自提点的订单行 + 补录弹窗
        cdp.goto("/seller/orders", 3.0)
        if cdp.scroll_to_text("填自提点", -320) == "OK":
            time.sleep(0.9)
            capture("06-seller-orders-pickup", 860)
            if cdp.click_text("填自提点") == "OK":
                time.sleep(1.2)
                capture("07-seller-pickup-modal", 900)
        else:
            print("未找到「填自提点」按钮，跳过该组图")

        # 8. 订单详情：交易快照
        use(buyer_token, "cb_token")
        cdp.goto("/orders/3", 3.0)
        if cdp.click_text("交易快照") == "OK":
            time.sleep(3.4)  # 等 iframe 内的 HTML 快照渲染
            capture("08-order-snapshot", 1000)
        else:
            print("未找到「交易快照」按钮，跳过该图")

        # 9. 店铺主页：历史评价（含已售出商品）
        cdp.goto("/shops/1", 3.0)
        cdp.scroll_to_text("店铺评价", -60)
        time.sleep(0.3)
        cdp.eval("window.scrollBy(0, 70); true")
        time.sleep(1.4)
        capture("09-shop-reviews", 760)

        # 10. 后台：商家商品弹窗内的「管理」入口
        use(admin_token, "cb_admin_token")
        cdp.goto("/admin/sellers", 3.0)
        if cdp.click_text("查看商品") == "OK":
            time.sleep(1.8)
            capture("10-admin-seller-products", 900)
        else:
            print("未找到「查看商品」按钮，跳过后台图")

        print(f"原始截图：{TMP}")
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        shutil.rmtree(profile, ignore_errors=True)


def shrink() -> None:
    """统一压到 1400 宽，去掉元数据，输出到 docs/assets/screenshots。"""
    OUT.mkdir(parents=True, exist_ok=True)
    total = 0
    for raw in sorted(TMP.glob("*.png")):
        image = Image.open(raw).convert("RGB")
        if image.width > TARGET_WIDTH:
            height = round(image.height * TARGET_WIDTH / image.width)
            image = image.resize((TARGET_WIDTH, height), Image.LANCZOS)
        target = OUT / raw.name
        image.save(target, format="PNG", optimize=True)
        size = target.stat().st_size / 1024
        total += size
        print(f"{target.name:<32} {image.width}x{image.height}  {size:6.1f} KB")
    print(f"合计 {total:.0f} KB -> {OUT}")


if __name__ == "__main__":
    code = main()
    if code == 0:
        shrink()
    raise SystemExit(code)
