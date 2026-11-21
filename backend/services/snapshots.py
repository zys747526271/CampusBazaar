"""交易快照：下单瞬间固化商品介绍页与详情页，作为纠纷取证材料。

设计取舍：
- 快照文件是**自包含 HTML**（图片内联为 data URI），不依赖商品后续改价、下架或删除；
- 同时保留结构化 ``data``，接口可直接渲染，不必解析 HTML；
- 生成时机为下单成功，历史订单在首次查看时补生成（商品可能已删除，退化为订单明细快照）。
"""
from __future__ import annotations

import base64
import html
import mimetypes
from datetime import datetime
from pathlib import Path

from flask import current_app

from backend.extensions import db
from backend.models import OrderSnapshot
from backend.utils.common import iso
from backend.utils.logging import app_log

MAX_INLINE_IMAGE_BYTES = 2 * 1024 * 1024


def _static_file(url: str) -> Path | None:
    """/static/uploads/xxx → 本地文件；外链返回 None。"""
    if not url or not url.startswith("/static/uploads/"):
        return None
    relative = url.replace("/static/uploads/", "", 1)
    root = Path(current_app.config["UPLOAD_ROOT"]).resolve()
    target = (root / relative).resolve()
    if root not in target.parents and target != root:
        return None
    return target if target.is_file() else None


def _data_uri(url: str) -> str:
    path = _static_file(url)
    if path is None:
        return url
    try:
        if path.stat().st_size > MAX_INLINE_IMAGE_BYTES:
            return url
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"
    except OSError:
        return url


def build_payload(order) -> dict:
    """快照结构化内容：订单信息 + 每件商品的介绍页/详情页数据。"""
    items = []
    for item in order.items:
        product = item.product
        items.append(
            {
                "product_id": item.product_id,
                "name": item.name,
                "price": float(item.price),
                "quantity": item.quantity,
                "subtotal": float(item.subtotal),
                "condition": item.product_condition or "",
                # 介绍页：列表卡片能看到的信息
                "listing": {
                    "cover_image": item.image or "",
                    "price": float(item.price),
                    "condition": item.product_condition or "",
                    "location": (product.location if product else "") or "",
                    "delivery_labels": list(product.delivery_labels) if product else [],
                    "pickup_location": (product.pickup_location if product else "") or "",
                    "free_shipping": bool(product.free_shipping) if product else True,
                    "shipping_fee": float(product.shipping_amount) if product else 0.0,
                    "seller_nickname": (product.seller.nickname if product and product.seller else ""),
                    "created_at": iso(product.created_at) if product else "",
                },
                # 详情页：描述、图集、分类、库存
                "detail": {
                    "description": (product.description if product else "") or "",
                    "images": list(product.images or []) if product else ([item.image] if item.image else []),
                    "tag": (product.tag.name if product and product.tag else ""),
                    "seller_category": (
                        product.seller_category.name if product and product.seller_category else ""
                    ),
                    "quantity_left": product.quantity if product else None,
                    "sales": product.sales if product else None,
                    "views": product.views if product else None,
                    "product_status": product.status if product else "已删除",
                },
            }
        )

    return {
        "order_no": order.order_no,
        "status": order.status,
        "created_at": iso(order.created_at),
        "buyer": {"nickname": order.buyer.nickname if order.buyer else "", "phone": order.receiver_phone},
        "seller": {"nickname": order.seller.nickname if order.seller else "", "id": order.seller_id},
        "delivery_type": order.delivery_type,
        "pay_method": order.pay_method,
        "pickup_location": order.pickup_location or "",
        "pickup_time": iso(order.pickup_time),
        "receiver": {
            "name": order.receiver_name,
            "phone": order.receiver_phone,
            "address": order.address_text,
        },
        "remark": order.remark or "",
        "items": items,
        "amounts": {
            "items_total": float(order.items_total or 0),
            "shipping_fee": float(order.shipping_fee or 0),
            "total_amount": float(order.total_amount or 0),
        },
        "captured_at": iso(datetime.now().astimezone()),
    }


STYLE = """
* { box-sizing: border-box; }
body { margin: 0; padding: 28px 20px 40px; background: #f5f6f8; color: #20242b;
  font-family: "PingFang SC", "Microsoft YaHei", system-ui, sans-serif; }
.wrap { max-width: 920px; margin: 0 auto; }
.head { background: #fff; border-radius: 12px; padding: 20px 24px; margin-bottom: 16px;
  border: 1px solid #ebedf0; }
.head h1 { margin: 0 0 6px; font-size: 20px; }
.meta { color: #6b7280; font-size: 13px; line-height: 1.9; }
.grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px 24px; margin-top: 12px; }
.grid div { font-size: 13px; color: #374151; }
.grid b { color: #111827; }
.card { background: #fff; border: 1px solid #ebedf0; border-radius: 12px; padding: 20px 24px; margin-bottom: 16px; }
.card h2 { margin: 0 0 14px; font-size: 16px; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 999px; background: #fff1e8; color: #c2410c;
  font-size: 12px; margin-right: 6px; }
.listing { display: flex; gap: 16px; align-items: flex-start; padding: 14px 0; border-top: 1px dashed #eceef1; }
.listing:first-of-type { border-top: 0; padding-top: 0; }
.thumb { width: 96px; height: 96px; border-radius: 10px; object-fit: cover; background: #f3f4f6; flex: none; }
.title { font-size: 15px; font-weight: 600; margin: 0 0 6px; }
.price { color: #e8481c; font-weight: 700; font-size: 16px; }
.sub { color: #6b7280; font-size: 12.5px; margin-top: 4px; }
.desc { white-space: pre-wrap; line-height: 1.8; font-size: 14px; color: #374151; margin: 8px 0 12px; }
.gallery { display: flex; flex-wrap: wrap; gap: 10px; }
.gallery img { width: 128px; height: 128px; border-radius: 8px; object-fit: cover; border: 1px solid #eceef1; }
.foot { color: #9ca3af; font-size: 12px; text-align: center; margin-top: 24px; }
table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
td { padding: 8px 0; color: #374151; }
td:last-child { text-align: right; font-weight: 600; color: #111827; }
.total td { border-top: 1px solid #eceef1; padding-top: 10px; font-size: 15px; color: #e8481c; }
@media (max-width: 640px) { .grid { grid-template-columns: 1fr; } .listing { flex-direction: column; } }
"""


def render_html(payload: dict) -> str:
    rows = []
    for item in payload["items"]:
        listing = item["listing"]
        detail = item["detail"]
        badges = "".join(f'<span class="badge">{html.escape(label)}</span>' for label in listing["delivery_labels"])
        gallery = "".join(
            f'<img src="{html.escape(_data_uri(src))}" alt="{html.escape(item["name"])}" />'
            for src in detail["images"]
        )
        rows.append(
            f"""
    <section class="card">
      <h2>商品介绍 · {html.escape(item["name"])}</h2>
      <div class="listing">
        <img class="thumb" src="{html.escape(_data_uri(listing["cover_image"]))}" alt="{html.escape(item["name"])}" />
        <div>
          <p class="title">{html.escape(item["name"])}</p>
          <p class="price">¥{item["price"]:.2f} <span class="sub">× {item["quantity"]} 件</span></p>
          <p class="sub">成色：{html.escape(item["condition"] or "-")}　交易地点：{html.escape(listing["location"] or "-")}</p>
          <p class="sub">履约：{badges or "未设置"}</p>
          <p class="sub">卖家：{html.escape(listing["seller_nickname"] or "-")}　上架时间：{html.escape(listing["created_at"] or "-")}</p>
        </div>
      </div>
      <h2 style="margin-top:18px">商品详情页</h2>
      <p class="desc">{html.escape(detail["description"] or "卖家未填写描述")}</p>
      <p class="sub">分类：{html.escape(detail["tag"] or "-")}　卖家分组：{html.escape(detail["seller_category"] or "-")}
        　下单时剩余库存：{detail["quantity_left"] if detail["quantity_left"] is not None else "-"}</p>
      <div class="gallery">{gallery}</div>
    </section>"""
        )

    receiver = payload["receiver"]
    pickup = (
        f'<div><b>自提点：</b>{html.escape(payload["pickup_location"] or "卖家待补充")}</div>'
        f'<div><b>自提时间：</b>{html.escape(payload["pickup_time"] or "待买家确认")}</div>'
        if payload["delivery_type"] == "自提"
        else f'<div><b>收货地址：</b>{html.escape(receiver["address"] or "-")}</div>'
    )
    amounts = payload["amounts"]
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>交易快照 {html.escape(payload["order_no"])}</title>
<style>{STYLE}</style></head>
<body><div class="wrap">
  <header class="head">
    <h1>交易快照 · {html.escape(payload["order_no"])}</h1>
    <div class="meta">快照生成时间：{html.escape(payload["captured_at"])}　下单时间：{html.escape(payload["created_at"] or "-")}</div>
    <div class="grid">
      <div><b>买家：</b>{html.escape(payload["buyer"]["nickname"] or "-")}（{html.escape(receiver["phone"] or "-")}）</div>
      <div><b>卖家：</b>{html.escape(payload["seller"]["nickname"] or "-")}</div>
      <div><b>履约方式：</b>{html.escape(payload["delivery_type"])}</div>
      <div><b>支付方式：</b>{html.escape(payload["pay_method"])}</div>
      <div><b>联系人：</b>{html.escape(receiver["name"] or "-")}</div>
      {pickup}
      <div><b>备注：</b>{html.escape(payload["remark"] or "-")}</div>
    </div>
  </header>
  {''.join(rows)}
  <section class="card">
    <h2>金额</h2>
    <table>
      <tr><td>商品金额</td><td>¥{amounts["items_total"]:.2f}</td></tr>
      <tr><td>运费</td><td>¥{amounts["shipping_fee"]:.2f}</td></tr>
      <tr class="total"><td>实付金额</td><td>¥{amounts["total_amount"]:.2f}</td></tr>
    </table>
  </section>
  <p class="foot">本页由 CampusBazaar 在下单瞬间自动生成，用于交易纠纷取证；商品后续改价、下架或删除不影响本快照。</p>
</div></body></html>"""


def ensure_snapshot(order) -> OrderSnapshot:
    """取快照，不存在则生成（历史订单首次查看时补生成）。"""
    if order.snapshot is not None:
        return order.snapshot
    payload = build_payload(order)
    try:
        relative_dir = Path("snapshots")
        target_dir = Path(current_app.config["UPLOAD_ROOT"]) / relative_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{order.order_no}.html"
        (target_dir / filename).write_text(render_html(payload), encoding="utf-8")
        html_path = f"/static/uploads/{relative_dir.as_posix()}/{filename}"
    except OSError as exc:
        app_log.warning("快照文件写入失败 order=%s: %s", order.order_no, exc)
        html_path = ""

    snapshot = OrderSnapshot(order_id=order.id, html_path=html_path, data=payload)
    db.session.add(snapshot)
    db.session.flush()
    order.snapshot = snapshot
    return snapshot


def snapshot_payload(order) -> dict:
    snapshot = ensure_snapshot(order)
    return {
        "order_no": order.order_no,
        "created_at": iso(snapshot.created_at),
        "html_url": snapshot.html_path or "",
        "data": snapshot.data or {},
    }
