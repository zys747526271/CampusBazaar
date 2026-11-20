"""全站唯一枚举与常量来源（PRD 6.3 强制约定）。

任何模块（后端 / 前端 / 数据库）都只能使用这里的字面值；
禁止在业务代码里再定义一套同义枚举或做"猜测式"映射。
"""
from decimal import Decimal


class ProductStatus:
    PENDING = "待审核"
    APPROVED = "已通过"
    OFF = "已下架"

    ALL = (PENDING, APPROVED, OFF)
    #: 买家侧可见
    VISIBLE = (APPROVED,)


class OrderStatus:
    UNPAID = "待付款"
    PAID = "已付款"
    SHIPPED = "已发货"
    DONE = "已完成"
    CANCELLED = "已取消"
    REFUNDING = "退款中"

    ALL = (UNPAID, PAID, SHIPPED, DONE, CANCELLED, REFUNDING)
    #: 进行中（占用库存 / 待履约）
    ACTIVE = (UNPAID, PAID, SHIPPED, REFUNDING)
    #: 终态
    TERMINAL = (DONE, CANCELLED)


class PayMethod:
    BALANCE = "余额"
    OFFLINE = "线下"
    WECHAT = "微信"
    ALIPAY = "支付宝"

    ALL = (BALANCE, OFFLINE, WECHAT, ALIPAY)
    #: 首版可用
    SUPPORTED = (BALANCE, OFFLINE)


class DeliveryType:
    PICKUP = "自提"
    MEETUP = "面交"
    EXPRESS = "快递"

    ALL = (PICKUP, MEETUP, EXPRESS)


class ProductCondition:
    NEW = "全新"
    LIKE_NEW = "几乎全新"
    GOOD = "轻微使用"
    FAIR = "明显使用"

    ALL = (NEW, LIKE_NEW, GOOD, FAIR)


class BalanceLogType:
    RECHARGE = "充值"
    PAY = "支付"
    REFUND = "退款"
    INCOME = "收入"


class MessageType:
    ORDER = "订单"
    SYSTEM = "系统"
    AUDIT = "审核"
    FUND = "资金"

    ALL = (ORDER, SYSTEM, AUDIT, FUND)


class ReportStatus:
    PENDING = "待处理"
    RESOLVED = "已处理"
    REJECTED = "已驳回"

    ALL = (PENDING, RESOLVED, REJECTED)


class ReportTarget:
    PRODUCT = "product"
    COMMENT = "comment"
    USER = "user"

    ALL = (PRODUCT, COMMENT, USER)
    LABELS = {PRODUCT: "商品", COMMENT: "评价", USER: "用户"}


class AdminLevel:
    NORMAL = "普通"
    SENIOR = "高级"
    SUPER = "超级"

    ALL = (NORMAL, SENIOR, SUPER)


class OperatorType:
    BUYER = "买家"
    SELLER = "卖家"
    ADMIN = "管理员"
    SYSTEM = "系统"


class AuditAction:
    #: 商品治理
    PRODUCT_APPROVE = "商品审核通过"
    PRODUCT_REJECT = "商品审核驳回"
    PRODUCT_OFF = "商品强制下架"
    PRODUCT_FEATURE = "商品推荐位调整"
    #: 账号治理
    USER_BAN = "封禁用户"
    USER_UNBAN = "解封用户"
    USER_RESET_PASSWORD = "重置用户密码"
    #: 内容治理
    COMMENT_HIDE = "隐藏评价"
    COMMENT_RESTORE = "恢复评价"
    COMMENT_DELETE = "删除评价"
    #: 站点配置
    TAG_CREATE = "新增平台分类"
    TAG_UPDATE = "修改平台分类"
    TAG_DELETE = "删除平台分类"
    BANNER_CREATE = "新增轮播图"
    BANNER_UPDATE = "修改轮播图"
    BANNER_DELETE = "删除轮播图"
    #: 交易
    ORDER_REFUND = "处理退款"
    REPORT_HANDLE = "处理举报"


class Limits:
    """业务阈值集中配置，避免魔法数字散落。"""

    #: 待付款订单自动取消（分钟）
    ORDER_PAY_TIMEOUT_MINUTES = 30
    #: 已发货自动确认收货（天）
    ORDER_AUTO_CONFIRM_DAYS = 7
    #: 单个商品图片上限
    PRODUCT_MAX_IMAGES = 5
    #: 单张图片上限（字节）
    IMAGE_MAX_BYTES = 5 * 1024 * 1024
    #: 单次下单最大件数
    ORDER_MAX_ITEMS = 50
    #: 搜索关键词长度
    KEYWORD_MAX_LEN = 50
    #: 评价内容长度
    COMMENT_MAX_LEN = 500
    #: 浏览记录保留条数
    HISTORY_KEEP = 100
    #: 余额充值演示上限
    RECHARGE_MAX = Decimal("10000.00")
    #: 单笔订单金额上限
    ORDER_AMOUNT_MAX = Decimal("999999.99")

    #: 限流规则：(次数, 窗口秒)
    RATE_LOGIN = (10, 60)
    RATE_CAPTCHA = (1, 60)
    RATE_ORDER = (10, 60)
    RATE_REGISTER = (5, 300)
    RATE_UPLOAD = (20, 60)
    RATE_REPORT = (10, 600)

    #: 管理员登录连续失败锁定
    ADMIN_LOGIN_MAX_ATTEMPTS = 5
    ADMIN_LOGIN_LOCK_MINUTES = 15

    #: 验证码有效期（分钟）
    CAPTCHA_TTL_MINUTES = 5


SORT_WHITELIST = ("created_at", "price", "sales", "views")
SORT_ALIASES = {
    "latest": "created_at",
    "newest": "created_at",
    "price": "price",
    "sales": "sales",
    "views": "views",
    "hot": "views",
}
