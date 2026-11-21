"""演示数据（幂等）：``python -m backend.seed``。

只在 ``SEED_DEMO_DATA=true`` 时写入；按唯一键 upsert，重复执行不会产生重复数据。
本地演示的商品图用 SVG 现场生成，不依赖任何外部图片素材。
"""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from backend.constants import (
    AdminLevel,
    BalanceLogType,
    DeliveryType,
    OperatorType,
    OrderStatus,
    PayMethod,
    ProductCondition,
    ProductStatus,
)
from backend.extensions import db
from backend.models import (
    Admin,
    Balance,
    BalanceLog,
    Banner,
    Comment,
    Order,
    OrderItem,
    OrderStatusLog,
    Product,
    Tag,
    User,
)
from backend.utils.common import utcnow
from backend.utils.security import hash_password

DEMO_PASSWORD = "Campus123"
ADMIN_PASSWORD = "Admin12345"

TAGS = [
    ("教材书籍", "book", "课本、考研资料、笔记", 1),
    ("数码电子", "device", "手机、平板、耳机、配件", 2),
    ("生活百货", "home", "宿舍好物、收纳、小家电", 3),
    ("运动户外", "sport", "球拍、跑鞋、健身器材", 4),
    ("乐器文娱", "music", "吉他、键盘、桌游", 5),
    ("美妆个护", "beauty", "护肤、香水、小样", 6),
]

SELLERS = [
    ("13800000001", "林小满", "东校区 · 3 号宿舍楼", "数码爱好者，毕业清仓，价格好商量。"),
    ("13800000002", "陈屿", "西校区 · 图书馆旁", "考研上岸，资料全套转让，可小刀。"),
    ("13800000003", "苏晴", "南校区 · 6 号宿舍楼", "喜欢收纳和布置宿舍，闲置都好用。"),
]

BUYERS = [
    ("13800000004", "赵一鸣", "东校区 · 1 号宿舍楼"),
    ("13800000005", "何佳", "西校区 · 2 号宿舍楼"),
]

#: (名称, 价格, 原价, 分类, 成色, 交易地点, 卖家序号, 描述, 图片数)
PRODUCTS = [
    ("高等数学 同济第七版 上下册", "28.00", "79.00", "教材书籍", ProductCondition.GOOD, "图书馆一楼大厅", 1,
     "课上用完，笔记用铅笔写的，可以擦掉。上册书角有点卷，内页完整无缺页，考期末完全够用。", 3),
    ("考研英语一 真题解析（2010-2024）", "35.00", "128.00", "教材书籍", ProductCondition.LIKE_NEW, "西区食堂门口", 2,
     "今年上岸，全套真题+解析，做过一遍答案写在草稿纸上，书上基本干净。送作文模板打印稿。", 3),
    ("iPad Air 4 64G 深空灰", "1680.00", "4399.00", "数码电子", ProductCondition.GOOD, "3 号宿舍楼下", 1,
     "自用两年，屏幕无划痕（一直贴膜带壳），电池健康 88%，追剧记笔记完全够用。配原装充电器和第三方保护壳。", 4),
    ("罗技 MX Master 3 无线鼠标", "268.00", "699.00", "数码电子", ProductCondition.LIKE_NEW, "东区咖啡厅", 1,
     "换了 Mac 之后闲置，滚轮顺滑，侧键自定义，办公神器。附 Type-C 线。", 2),
    ("Kindle Paperwhite 4 8G 防水版", "320.00", "998.00", "数码电子", ProductCondition.GOOD, "图书馆二楼", 2,
     "看书很舒服，墨水瓶无坏点，送一个磁吸保护套。已经重置为出厂设置。", 2),
    ("宿舍小冰箱 桌面 20L", "150.00", "399.00", "生活百货", ProductCondition.GOOD, "6 号宿舍楼下自提", 3,
     "毕业带不走，制冷正常，声音很小，放饮料水果刚好。需要自己搬，楼下有电梯。", 3),
    ("北欧风桌面收纳架 三层", "25.00", "69.00", "生活百货", ProductCondition.LIKE_NEW, "6 号楼 512", 3,
     "买回来发现尺寸不合适，只用了一周，无磕碰。可以拆装，女生一个人也能装好。", 2),
    ("耐克 Air Zoom 跑鞋 42 码", "199.00", "699.00", "运动户外", ProductCondition.GOOD, "操场看台", 3,
     "跑了大概 100 公里，鞋底磨损很轻，鞋面清洗过。尺码偏标准，脚感软弹。", 3),
    ("尤尼克斯羽毛球拍 双拍套装", "120.00", "358.00", "运动户外", ProductCondition.GOOD, "体育馆羽毛球场", 3,
     "打了一学期，拍框无变形，已重新拉线 24 磅。送两个拍套和三个球。", 2),
    ("雅马哈 F310 民谣吉他 41 寸", "420.00", "899.00", "乐器文娱", ProductCondition.GOOD, "艺术楼 201", 2,
     "入门神器，琴颈无变形，音准稳定。送琴包、变调夹、拨片和一包备用弦。", 3),
    ("大学物理 教材 + 习题册（两本）", "22.00", "68.00", "教材书籍", ProductCondition.GOOD, "西区教学楼", 2,
     "上册有少量荧光笔标记，习题册没写过。工科必修，考试重点都标出来了。", 2),
    ("香奈儿 5 号淡香 小样 5ml", "88.00", "199.00", "美妆个护", ProductCondition.NEW, "南门快递点", 3,
     "专柜赠品，全新未拆封，喷头正常。适合先试香再入正装。", 2),
]

#: 演示用履约配置：覆盖「仅自提」「仅快递」「包邮」「到付运费」四种展示
DELIVERY_MAP = {
    "高等数学 同济第七版 上下册": {"pickup": True, "express": True, "free": True, "fee": 0},
    "考研英语一 真题解析（2010-2024）": {"pickup": True, "express": True, "free": True, "fee": 0},
    "iPad Air 4 64G 深空灰": {"pickup": True, "express": True, "free": False, "fee": 12},
    "罗技 MX Master 3 无线鼠标": {"pickup": True, "express": True, "free": True, "fee": 0},
    "Kindle Paperwhite 4 8G 防水版": {"pickup": True, "express": True, "free": True, "fee": 0},
    "宿舍小冰箱 桌面 20L": {"pickup": True, "express": False, "free": True, "fee": 0},
    "北欧风桌面收纳架 三层": {"pickup": True, "express": False, "free": True, "fee": 0},
    "耐克 Air Zoom 跑鞋 42 码": {"pickup": True, "express": True, "free": False, "fee": 10},
    "尤尼克斯羽毛球拍 双拍套装": {"pickup": True, "express": True, "free": True, "fee": 0},
    "雅马哈 F310 民谣吉他 41 寸": {"pickup": True, "express": False, "free": True, "fee": 0},
    "大学物理 教材 + 习题册（两本）": {"pickup": True, "express": True, "free": True, "fee": 0},
    "香奈儿 5 号淡香 小样 5ml": {"pickup": False, "express": True, "free": False, "fee": 8},
}

BANNERS = [
    ("毕业季 · 闲置好物大清仓", "教材 / 数码 / 宿舍神器，低至 3 折", "#ff5000", "#ff8a3d", "/products?sort=sales"),
    ("考研资料专区", "真题、笔记、参考书，学长学姐亲测", "#2b5cff", "#5b8cff", "/products?tag_id=1"),
    ("校内自提 · 当面验货", "同校交易，见面自提，省心又安全", "#0f9d76", "#3ec49b", "/products?sort=created_at"),
]


# ------------------------------------------------------------------ 图片
PALETTES = [
    ("#ffe8dc", "#ffb98a", "#ff5000"),
    ("#e8efff", "#a9c2ff", "#2b5cff"),
    ("#e6f7f0", "#9fe0c6", "#0f9d76"),
    ("#f4ecff", "#c9b0ff", "#7a3ff2"),
    ("#fff6e0", "#ffd98a", "#d98c00"),
]


def _svg_cover(title: str, subtitle: str, seed: int) -> str:
    """生成商品占位图：渐变背景 + 两行商品名，避免演示依赖外部素材。"""
    bg, mid, accent = PALETTES[seed % len(PALETTES)]
    line1, line2 = _split_title(title)
    second = (
        f'<text x="400" y="430" text-anchor="middle" font-family="PingFang SC, Microsoft YaHei, sans-serif"'
        f' font-size="40" font-weight="700" fill="#20242b">{line2}</text>'
        if line2
        else ""
    )
    base_y = 372 if line2 else 404
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="800" height="800" viewBox="0 0 800 800">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
<stop offset="0%" stop-color="{bg}"/><stop offset="100%" stop-color="{mid}"/></linearGradient></defs>
<rect width="800" height="800" fill="url(#g)"/>
<circle cx="650" cy="140" r="120" fill="{accent}" opacity="0.12"/>
<circle cx="140" cy="670" r="170" fill="{accent}" opacity="0.09"/>
<rect x="64" y="64" width="672" height="672" rx="40" fill="#ffffff" opacity="0.26"/>
<text x="400" y="{base_y}" text-anchor="middle" font-family="PingFang SC, Microsoft YaHei, sans-serif"
 font-size="44" font-weight="700" fill="#20242b">{line1}</text>
{second}
<text x="400" y="510" text-anchor="middle" font-family="PingFang SC, Microsoft YaHei, sans-serif"
 font-size="22" fill="{accent}" opacity="0.85">{subtitle}</text>
<text x="400" y="704" text-anchor="middle" font-family="PingFang SC, Microsoft YaHei, sans-serif"
 font-size="19" fill="#20242b" opacity="0.3">CampusBazaar · 校园集市</text>
</svg>"""


def _split_title(title: str) -> tuple[str, str]:
    """把商品名拆成两行，长名优先在空格/中间断开。"""
    text = title.strip()
    if len(text) <= 13:
        return text, ""
    space = text.find(" ")
    if 0 < space <= 16:
        return text[:space], text[space + 1 : space + 15]
    cut = min(len(text) // 2 + 1, 14)
    return text[:cut], text[cut : cut + 14]


def _write_svg(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def _ensure_product_images(index: int, name: str, count: int) -> list[str]:
    from flask import current_app

    root = Path(current_app.config["UPLOAD_ROOT"]) / "demo"
    urls = []
    for n in range(count):
        filename = f"p{index + 1}-{n + 1}.svg"
        _write_svg(root / filename, _svg_cover(name, f"实拍图 {n + 1}", index + n))
        urls.append(f"/static/uploads/demo/{filename}")
    return urls


def _ensure_banner_image(index: int, title: str, c1: str, c2: str) -> str:
    """轮播图：文字居中排版，适配不同宽高比的裁切。"""
    from flask import current_app

    root = Path(current_app.config["UPLOAD_ROOT"]) / "demo"
    filename = f"banner-{index + 1}.svg"
    content = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="420" viewBox="0 0 1200 420">
<defs><linearGradient id="b" x1="0" y1="0" x2="1" y2="1">
<stop offset="0%" stop-color="{c1}"/><stop offset="100%" stop-color="{c2}"/></linearGradient></defs>
<rect width="1200" height="420" fill="url(#b)"/>
<circle cx="1010" cy="80" r="170" fill="#fff" opacity="0.12"/>
<circle cx="180" cy="380" r="150" fill="#fff" opacity="0.10"/>
<rect x="470" y="86" width="260" height="34" rx="17" fill="#ffffff" opacity="0.22"/>
<text x="600" y="110" text-anchor="middle" font-family="PingFang SC, Microsoft YaHei, sans-serif"
 font-size="17" fill="#ffffff" opacity="0.9">校园集市 · 同校二手交易</text>
<text x="600" y="206" text-anchor="middle" font-family="PingFang SC, Microsoft YaHei, sans-serif"
 font-size="46" font-weight="700" fill="#ffffff">{title[:18]}</text>
<text x="600" y="256" text-anchor="middle" font-family="PingFang SC, Microsoft YaHei, sans-serif"
 font-size="21" fill="#ffffff" opacity="0.86">校内自提 · 当面验货 · 交易留痕</text>
<rect x="512" y="292" width="176" height="48" rx="24" fill="#ffffff" opacity="0.94"/>
<text x="600" y="324" text-anchor="middle" font-family="PingFang SC, Microsoft YaHei, sans-serif"
 font-size="19" font-weight="600" fill="{c1}">立即逛逛</text>
</svg>"""
    _write_svg(root / filename, content)
    return f"/static/uploads/demo/{filename}"


# ------------------------------------------------------------------ 主流程
def seed_demo_data() -> dict:
    stats = {"users": 0, "tags": 0, "products": 0, "banners": 0, "orders": 0, "comments": 0}

    tag_map = {}
    for name, icon, desc, order in TAGS:
        tag = Tag.query.filter_by(name=name).first()
        if tag is None:
            tag = Tag(name=name, icon=icon, description=desc, sort_order=order, is_active=True)
            db.session.add(tag)
            db.session.flush()
            stats["tags"] += 1
        tag_map[name] = tag

    sellers = []
    for phone, nickname, campus, _bio in SELLERS:
        user = User.query.filter_by(phone=phone).first()
        if user is None:
            user = User(
                phone=phone,
                nickname=nickname,
                password_hash=hash_password(DEMO_PASSWORD),
                campus=campus,
                is_seller=True,
                seller_since=utcnow(),
                avatar_url="",
            )
            db.session.add(user)
            db.session.flush()
            db.session.add(Balance(user_id=user.id, amount=Decimal("0.00")))
            stats["users"] += 1
        sellers.append(user)

    buyers = []
    for phone, nickname, campus in BUYERS:
        user = User.query.filter_by(phone=phone).first()
        if user is None:
            user = User(
                phone=phone,
                nickname=nickname,
                password_hash=hash_password(DEMO_PASSWORD),
                campus=campus,
                avatar_url="",
            )
            db.session.add(user)
            db.session.flush()
            db.session.add(Balance(user_id=user.id, amount=Decimal("520.00")))
            db.session.add(
                BalanceLog(
                    user_id=user.id,
                    amount=Decimal("520.00"),
                    balance_after=Decimal("520.00"),
                    type=BalanceLogType.RECHARGE,
                    remark="演示初始余额",
                )
            )
            stats["users"] += 1
        buyers.append(user)

    admin = Admin.query.filter_by(username="admin").first()
    if admin is None:
        db.session.add(
            Admin(
                username="admin",
                name="平台运营",
                password_hash=hash_password(ADMIN_PASSWORD),
                permission_level=AdminLevel.SUPER,
                is_active=True,
            )
        )
        stats["users"] += 1

    # 先确保占位图存在（幂等：文件已存在则跳过），再写库，避免重复执行缺图
    for index, item in enumerate(BANNERS):
        _ensure_banner_image(index, item[0], item[2], item[3])
    for index, item in enumerate(PRODUCTS):
        _ensure_product_images(index, item[0], item[8])

    for index, item in enumerate(BANNERS):
        title, subtitle, c1, c2, link = item
        if Banner.query.filter_by(title=title).first() is None:
            db.session.add(
                Banner(
                    title=title,
                    subtitle=subtitle,
                    image_url=_ensure_banner_image(index, title, c1, c2),
                    link_url=link,
                    sort_order=index + 1,
                    is_active=True,
                )
            )
            stats["banners"] += 1

    db.session.flush()

    product_map: dict[str, Product] = {}
    for index, (name, price, original, tag_name, condition, location, seller_index, desc, img_count) in enumerate(PRODUCTS):
        seller = sellers[(seller_index - 1) % len(sellers)]
        product = Product.query.filter_by(name=name, seller_id=seller.id).first()
        if product is not None:
            product_map[name] = product
            continue
        delivery = DELIVERY_MAP[name]
        product = Product(
            name=name,
            description=desc,
            price=Decimal(price),
            original_price=Decimal(original),
            quantity=1,
            sales=0,
            views=120 + index * 37,
            images=_ensure_product_images(index, name, img_count),
            product_condition=condition,
            location=location,
            supports_pickup=delivery["pickup"],
            pickup_location=location if delivery["pickup"] else "",
            supports_express=delivery["express"],
            free_shipping=delivery["free"],
            shipping_fee=Decimal("0.00") if delivery["free"] else Decimal(str(delivery["fee"])),
            tag_id=tag_map[tag_name].id,
            seller_id=seller.id,
            status=ProductStatus.APPROVED,
            is_available=True,
            is_featured=index in (0, 2, 9),
            audited_at=utcnow(),
            # 发布时间分散到最近几天，首页"最新上架"与趋势更真实
            created_at=utcnow() - timedelta(hours=index * 9 + 3),
            updated_at=utcnow() - timedelta(hours=index * 9 + 3),
        )
        db.session.add(product)
        db.session.flush()
        product_map[name] = product
        stats["products"] += 1

    db.session.commit()
    _seed_demo_orders(buyers, product_map, stats)
    db.session.commit()

    print("\n演示数据就绪：")
    print(f"  平台分类 {len(TAGS)} 个 · 商品 {len(PRODUCTS)} 件 · 演示订单 {stats['orders']} 笔")
    print("  买家账号 13800000004 / 13800000005  密码：Campus123")
    print("  卖家账号 13800000001 / 13800000002 / 13800000003  密码：Campus123")
    print(f"  管理员 admin / {ADMIN_PASSWORD}")
    account_file = _write_accounts_file()
    print(f"  账号密码已写入 {account_file}\n")
    return stats


def _write_accounts_file() -> Path:
    """把演示账号写到 instance/demo-accounts.txt，避免文档与代码里的密码不一致。"""
    from backend.config import ROOT_DIR

    lines = [
        "CampusBazaar 演示账号（仅本地/演示环境）",
        "",
        "买家（可下单、收藏、评价）",
    ]
    for phone, nickname, _campus in BUYERS:
        lines.append(f"  {phone}  {nickname}  密码：{DEMO_PASSWORD}")
    lines.append("")
    lines.append("卖家（可发布商品、发货、看经营数据）")
    for phone, nickname, _campus, _bio in SELLERS:
        lines.append(f"  {phone}  {nickname}  密码：{DEMO_PASSWORD}")
    lines.extend(
        [
            "",
            "管理员（后台 /admin/login）",
            f"  admin  密码：{ADMIN_PASSWORD}",
            "",
            "卖家/买家同一套账号体系：卖家账号也能当买家下单。",
        ]
    )
    target = Path(ROOT_DIR) / "instance" / "demo-accounts.txt"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def _seed_demo_orders(buyers, product_map: dict[str, Product], stats: dict) -> None:
    """造几笔真实感的订单与评价，让首页/后台/卖家看板都有数据可看。"""
    #: (订单号, 买家, 商品, 状态, 支付方式, 评分, 评价, 卖家回复, 距今天数, 履约方式)
    demo_orders = [
        ("CB20260101000001", buyers[0], "高等数学 同济第七版 上下册", OrderStatus.DONE, PayMethod.BALANCE, 5,
         "书很干净，学长还送了笔记！自提也很准时。", True, 5, DeliveryType.PICKUP),
        ("CB20260101000002", buyers[1], "考研英语一 真题解析（2010-2024）", OrderStatus.DONE, PayMethod.OFFLINE, 4,
         "资料挺全的，就是有几页有折角，整体可以接受。", True, 3, DeliveryType.PICKUP),
        ("CB20260101000003", buyers[0], "宿舍小冰箱 桌面 20L", OrderStatus.DONE, PayMethod.BALANCE, 5,
         "冰箱制冷很好，学姐还帮忙搬下楼，太感谢了。", False, 1, DeliveryType.PICKUP),
        ("CB20260101000004", buyers[1], "耐克 Air Zoom 跑鞋 42 码", OrderStatus.SHIPPED, PayMethod.BALANCE, 0, "", False, 1, DeliveryType.EXPRESS),
        ("CB20260101000005", buyers[0], "雅马哈 F310 民谣吉他 41 寸", OrderStatus.PAID, PayMethod.BALANCE, 0, "", False, 0, DeliveryType.PICKUP),
        ("CB20260101000006", buyers[1], "大学物理 教材 + 习题册（两本）", OrderStatus.UNPAID, PayMethod.OFFLINE, 0, "", False, 0, DeliveryType.PICKUP),
    ]

    for order_no, buyer, product_name, status, pay_method, rating, comment_text, reply, days_ago, delivery_type in demo_orders:
        if Order.query.filter_by(order_no=order_no).first():
            continue
        product = product_map.get(product_name)
        if product is None:
            continue

        created = utcnow() - timedelta(days=days_ago, hours=2)
        shipping_fee = product.shipping_amount if delivery_type == DeliveryType.EXPRESS else Decimal("0.00")
        order = Order(
            order_no=order_no,
            created_at=created,
            updated_at=created,
            user_id=buyer.id,
            seller_id=product.seller_id,
            status=status,
            pay_method=pay_method,
            delivery_type=delivery_type,
            items_total=product.price,
            shipping_fee=shipping_fee,
            total_amount=product.price + shipping_fee,
            receiver_name=buyer.nickname,
            receiver_phone=buyer.phone,
            address_text=product.location or "校内自提",
            pickup_location=product.pickup_location if delivery_type == DeliveryType.PICKUP else "",
            pickup_time=created + timedelta(days=1, hours=3) if delivery_type == DeliveryType.PICKUP else None,
            pickup_time_confirmed_at=created + timedelta(hours=6) if delivery_type == DeliveryType.PICKUP else None,
            pickup_location_set_at=created if delivery_type == DeliveryType.PICKUP else None,
            remark="",
            pay_deadline=utcnow() + timedelta(minutes=25),
        )
        if status in (OrderStatus.PAID, OrderStatus.SHIPPED, OrderStatus.DONE):
            order.paid_at = created + timedelta(minutes=9)
        if status in (OrderStatus.SHIPPED, OrderStatus.DONE):
            order.shipped_at = created + timedelta(hours=5)
            order.ship_company = "" if order.delivery_type != DeliveryType.EXPRESS else "顺丰"
        if status == OrderStatus.DONE:
            order.finished_at = created + timedelta(days=1)
            product.sales = (product.sales or 0) + 1
        db.session.add(order)
        db.session.flush()

        db.session.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                name=product.name,
                image=product.cover_image,
                price=product.price,
                quantity=1,
                product_condition=product.product_condition,
            )
        )
        flow = ["待付款"]
        if status in (OrderStatus.PAID, OrderStatus.SHIPPED, OrderStatus.DONE):
            flow.append("已付款")
        if status in (OrderStatus.SHIPPED, OrderStatus.DONE):
            flow.append("已发货")
        if status == OrderStatus.DONE:
            flow.append("已完成")
        previous = ""
        step_time = created
        for index, step in enumerate(flow):
            step_time = created + timedelta(minutes=25 * index)
            db.session.add(
                OrderStatusLog(
                    order_id=order.id,
                    created_at=step_time,
                    from_status=previous,
                    to_status=step,
                    operator_type=OperatorType.BUYER if step != "已发货" else OperatorType.SELLER,
                    operator_id=buyer.id if step != "已发货" else product.seller_id,
                    operator_name=buyer.nickname if step != "已发货" else "卖家",
                    remark="演示数据",
                )
            )
            previous = step

        if rating and status == OrderStatus.DONE:
            exists = Comment.query.filter_by(order_id=order.id, product_id=product.id).first()
            if exists is None:
                db.session.add(
                    Comment(
                        order_id=order.id,
                        product_id=product.id,
                        user_id=buyer.id,
                        rating=rating,
                        content=comment_text,
                        images=[],
                        seller_reply="谢谢支持，祝使用愉快！" if reply else "",
                        seller_reply_at=(created + timedelta(days=1, hours=2)) if reply else None,
                        like_count=2 if rating == 5 else 0,
                        created_at=created + timedelta(days=1, hours=1),
                        updated_at=created + timedelta(days=1, hours=1),
                    )
                )
                stats["comments"] += 1

        stats["orders"] += 1


def main() -> None:
    """命令行入口：``python -m backend.seed``。"""
    from backend import create_app

    app = create_app()
    with app.app_context():
        seed_demo_data()


if __name__ == "__main__":
    main()
