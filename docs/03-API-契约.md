# 03 · API 契约

基础路径 `/api`，除特别标注外均为 `Content-Type: application/json; charset=utf-8`，文件上传为 `multipart/form-data`。

## 1. 通用约定

### 1.1 响应结构

```json
{
  "success": true,
  "code": "OK",
  "message": "操作成功",
  "data": {},
  "request_id": "d769ff0368704da7"
}
```

- `success` 与 HTTP 状态码严格一致（2xx 为 true，4xx/5xx 为 false）；
- 列表数据固定在 `data` 内：

```json
{ "items": [], "total": 0, "page": 1, "per_page": 20, "pages": 0 }
```

- 字段级校验失败时 `data` 为 `{ "字段": "原因" }`；
- 响应头 `X-Request-Id` 与 `request_id` 一致。

### 1.2 错误码

| HTTP | code | 语义 | 前端行为 |
| --- | --- | --- | --- |
| 200/201 | OK / CREATED | 成功 | 正常处理 |
| 400 | BAD_REQUEST | 参数或业务校验失败 | 展示 message，字段错误回填 |
| 401 | UNAUTHORIZED | 未登录、令牌无效/过期/吊销 | 清对应令牌，跳登录 |
| 403 | FORBIDDEN | 已登录但无权限、令牌类型不符、账号封禁 | 仅提示 |
| 404 | NOT_FOUND | 资源不存在或不可见 | 空态 / 404 |
| 409 | CONFLICT | 库存不足、非法状态迁移、唯一约束冲突 | 提示并刷新 |
| 422 | VALIDATION_ERROR | 字段校验失败 | 定位表单字段 |
| 429 | TOO_MANY_REQUESTS | 限流或管理员锁定 | 展示 `retry_after` |
| 500 | INTERNAL_ERROR | 服务异常 | 提示 + request_id |
| 503 | SERVICE_UNAVAILABLE | 短信网关未配置等依赖未就绪 | 提示稍后重试 |

### 1.3 鉴权

```
Authorization: Bearer <token>
```

| 令牌 | 载荷 | 有效期 | 适用 |
| --- | --- | --- | --- |
| 用户令牌 | `{sub, typ:"user", exp}` | 7 天 | `/api/**` 用户接口 |
| 管理员令牌 | `{sub, typ:"admin", exp}` | 12 小时 | `/api/admin/**` |

登出后 `jti` 进入黑名单。类型不匹配返回 403（不是 401）。

### 1.4 分页、排序、筛选

| 参数 | 规则 |
| --- | --- |
| `page` | 从 1 开始，默认 1 |
| `per_page` | 默认 20（部分列表 10/12/15），上限 100 |
| `sort` | 白名单 `created_at / price / sales / views`，非法值回退 `created_at` |
| `order` | `asc / desc`，默认 `desc` |
| `keyword` | ≤50 字，匹配名称与描述 |

### 1.5 幂等

写接口接受 `Idempotency-Key` 头，10 分钟内同一用户 + 同一路径 + 同一 key 的重复请求返回首次结果，并带 `X-Idempotent-Replay: true`（下单、支付、注册、找回密码已启用）。

### 1.6 枚举（传输值，中文，前后端字面一致）

| 枚举 | 取值 |
| --- | --- |
| 商品状态 | 待审核 / 已通过 / 已下架 |
| 订单状态 | 待付款 / 已付款 / 已发货 / 已完成 / 已取消 / 退款中 |
| 支付方式 | 余额 / 线下（微信、支付宝为预留） |
| 履约方式 | 自提 / 面交 / 快递 |
| 成色 | 全新 / 几乎全新 / 轻微使用 / 明显使用 |

## 2. 认证 `/api/auth`

| 方法 | 路径 | 鉴权 | 说明 |
| --- | --- | --- | --- |
| POST | `/captcha` | 公开 | 发送验证码，`{phone, scene: register/reset}`；dev 模式回显 `dev_code` |
| POST | `/register` | 公开 | `{phone, password, nickname, code, campus?, agree_terms}` → `{token, user}` |
| POST | `/login` | 公开 | `{phone, password}` → `{token, user}` |
| POST | `/logout` | 用户 | 吊销当前令牌 |
| GET | `/profile` | 用户 | 当前用户资料 |
| PUT | `/profile` | 用户 | 修改昵称/头像/邮箱/校区 |
| PUT | `/password` | 用户 | `{old_password, new_password}` |
| POST | `/reset-password` | 公开 | `{phone, code, new_password}` |
| POST | `/admin/login` | 公开 | `{username, password}`，连续失败 5 次锁定 15 分钟 |
| POST | `/admin/register` | 开关+邀请码 | `{username, password, name?, invite_code?}` |
| GET | `/admin/profile` | 管理员 | 当前管理员信息 |

```json
// POST /api/auth/login
{ "phone": "13800000004", "password": "******" }

// 200
{
  "success": true, "code": "OK", "message": "登录成功",
  "data": {
    "token": "eyJhbGciOi...",
    "user": { "id": 1, "nickname": "赵一鸣", "phone": "13800000004", "is_seller": false }
  },
  "request_id": "..."
}
```

## 3. 公开商城

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/meta/home` | 首页聚合：`banners`、`tags`、`blocks.recommended/hot/latest`、`hot_keywords` |
| GET | `/meta/filters` | 分类、成色、履约/支付方式、排序选项 |
| GET | `/meta/options` | 下单相关枚举、举报原因、图片上限 |
| GET | `/products` | 列表/搜索/筛选：`keyword tag_id min_price max_price condition sort order page per_page` |
| GET | `/products/{id}` | 详情：含 `rating` 评分统计、`favorited`、`related`、`cart_quantity` |
| GET | `/products/{id}/related` | 相关推荐 |
| GET | `/products/{id}/comments` | 评价列表（`sort=newest/helpful/rating`）+ `summary` |
| GET | `/tags` | 启用中的平台分类 |
| GET | `/shops/{seller_id}` | 店铺主页与统计 |
| GET | `/shops/{seller_id}/products` | 店铺在售商品 |
| GET | `/search/suggest` | 搜索联想：`{keywords, products}` |
| GET | `/health` | 健康检查：`{status, db, cache, env, version}` |

商品对象（列表卡片）主要字段：

```json
{
  "id": 3,
  "name": "iPad Air 4 64G 深空灰",
  "price": 1680.0,
  "original_price": 4399.0,
  "discount": 3.8,
  "cover_image": "/static/uploads/demo/p3-1.svg",
  "quantity": 1, "sales": 0, "views": 123,
  "condition": "轻微使用",
  "status": "已通过", "is_available": true, "is_on_sale": true, "stock_state": "在售",
  "tag": { "id": 2, "name": "数码电子" },
  "seller": { "id": 1, "nickname": "林小满", "rating": 5.0, "sold_count": 2 },
  "created_at": "2026-11-20T21:00:00+08:00"
}
```

## 4. 购物车

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/carts` | `{items, summary}`，`summary` 含选中件数/金额与失效数 |
| GET | `/carts/count` | 角标数量 |
| POST | `/carts` | `{product_id, quantity}`，同商品累加，超库存 409 |
| PUT | `/carts/{id}` | `{quantity?, selected?}` |
| DELETE | `/carts/{id}` | 移除单条 |
| DELETE | `/carts?mode=all|selected|invalid` | 批量清空 |
| POST | `/carts/batch` | `{action: delete/select/unselect, ids: []}` |
| PUT | `/carts/select-all` | `{selected: bool}` |
| GET | `/carts/checkout` | 结算数据：选中且有效的条目，按卖家分组 |

条目中的 `invalid_reason` 非空表示失效（已下架/售罄/超库存），前端置灰且不允许结算。

## 5. 订单

| 方法 | 路径 | 鉴权 | 说明 |
| --- | --- | --- | --- |
| POST | `/orders/preview` | 用户 | 结算预览，金额与实付同源计算 |
| POST | `/orders` | 用户 | 下单，支持 `Idempotency-Key` |
| GET | `/orders` | 用户 | 我的订单，`status` 筛选 |
| GET | `/orders/counts` | 用户 | 各状态数量 |
| GET | `/orders/{id}` | 买卖双方 | 详情：商品快照、金额、时间线、`actions` |
| POST | `/orders/{id}/pay` | 买家 | 余额支付（线下支付不可调用） |
| POST | `/orders/{id}/cancel` | 买家 | `{reason}` |
| POST | `/orders/{id}/confirm` | 买家 | 确认收货 |
| POST | `/orders/{id}/refund` | 买家 | `{reason}` → 退款中 |

下单请求：

```json
// 购物车结算
{
  "source": "cart",
  "cart_ids": [12, 13],
  "address_id": 3,
  "pay_method": "余额",
  "delivery_type": "面交",
  "remark": "晚上 7 点后图书馆门口"
}

// 立即购买（不传 address_id 时用 receiver_* 字段）
{
  "source": "now",
  "items": [{ "product_id": 3, "quantity": 1 }],
  "pay_method": "线下",
  "delivery_type": "自提",
  "receiver_name": "赵一鸣",
  "receiver_phone": "13800000004",
  "address_text": "3 号宿舍楼下"
}
```

响应 `data`：`{orders: [...], order_ids: [], total_amount, pay_method}`。一次结算按卖家拆单，金额一律服务端计算。

订单中的 `actions` 由服务端给出，前端只渲染：

| action | 角色 | 含义 |
| --- | --- | --- |
| `pay` | 买家 | 待付款且为余额支付 |
| `cancel` | 买家 | 待付款可取消 |
| `refund` | 买家 | 已付款/已发货可申请退款 |
| `confirm` | 买家 | 已发货可确认收货 |
| `comment` | 买家 | 已完成且仍有未评价商品 |
| `ship` | 卖家 | 已付款可发货 |
| `confirm_paid` | 卖家 | 线下支付待确认收款 |
| `close` | 卖家 | 待付款可关闭 |
| `refund_approve` / `refund_reject` | 卖家/管理员 | 处理退款 |
| `admin_cancel` | 管理员 | 介入取消 |

## 6. 互动与账户

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET/POST | `/favorites` | 收藏列表 / 收藏 `{product_id}` |
| DELETE | `/favorites/{product_id}` | 取消收藏 |
| GET/DELETE | `/history` | 浏览记录 / 清空 |
| POST | `/comments` | 评价 `{order_id, product_id, rating, content?, images?}`，仅已完成订单 |
| GET | `/comments/mine` | 我的评价 |
| POST | `/comments/{id}/like` | 点赞/取消（幂等切换） |
| DELETE | `/comments/{id}` | 软删除自己的评价 |
| POST | `/reports` | 举报 `{target_type: product/comment/user, target_id, reason, detail?}` |
| GET | `/messages` | 站内消息，`unread=1` 筛选 |
| GET | `/messages/unread` | 未读数 |
| POST | `/messages/{id}/read`、`/messages/read-all` | 标记已读 |
| DELETE | `/messages/{id}` | 删除消息 |
| GET/POST | `/addresses` | 地址列表 / 新增 |
| PUT/DELETE | `/addresses/{id}` | 编辑 / 删除 |
| PUT | `/addresses/{id}/default` | 设为默认 |
| GET | `/balance` | 余额、累计入账、最近流水、充值开关 |
| GET | `/balance/logs` | 流水分页 |
| POST | `/balance/recharge` | 演示充值 `{amount}`（`ENABLE_DEMO_RECHARGE=false` 时 403） |
| POST | `/uploads/image` | 通用图片上传，返回 `{url, thumb_url, width, height, size}` |

## 7. 卖家中心 `/api/seller`（需卖家身份）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/become` | 一键开通卖家 |
| GET | `/overview` | 经营看板：今日/累计销售额、订单数、待发货、商品数、浏览量、最近订单、热销商品 |
| GET | `/products` | 我的商品（状态、关键词、分页） |
| POST | `/products` | 发布，`{name, description, price, original_price?, quantity, condition, location?, tag_id, seller_category_id?, images[]}` |
| GET/PUT | `/products/{id}` | 详情 / 编辑（PUT 需传完整字段） |
| POST | `/products/{id}/toggle` | 上下架；`已下架` 重新上架时按 `AUTO_APPROVE_PRODUCT` 决定状态 |
| DELETE | `/products/{id}` | 软删除；有进行中订单时 409 |
| GET | `/orders` | 收到的订单，`status/keyword` 筛选 |
| POST | `/orders/{id}/confirm-paid` | 确认线下收款 |
| POST | `/orders/{id}/ship` | `{ship_company?, tracking_no?, note?}`，快递必填单号 |
| POST | `/orders/{id}/close` | 关闭待付款订单 |
| POST | `/orders/{id}/refund` | `{approve, note}` |
| GET/POST | `/categories` | 自定义分类列表 / 新增 |
| PUT/DELETE | `/categories/{id}` | 重命名 / 删除（有商品 400） |
| GET | `/comments` | 自己商品的评价，`unreplied=1` 过滤 |
| POST | `/comments/{id}/reply` | `{reply}` |

## 8. 管理后台 `/api/admin`（需管理员令牌）

| 模块 | 路径 | 说明 |
| --- | --- | --- |
| 概览 | GET `/stats` | 用户/商品/订单/GMV、今日增量、治理待办、7 天趋势 |
| 运维 | POST `/jobs/run` | 手动执行超时取消/自动确认/售罄下架 |
| 用户 | GET `/users` | `keyword/status(buyer/seller/banned)/page` |
| 用户 | GET `/users/{id}` | 详情 + 最近订单 + 商品数 |
| 用户 | PUT `/users/{id}/ban` | `{banned, reason}`，封禁同时下架其商品 |
| 用户 | PUT `/users/{id}/reset-password` | 不传新密码则生成随机密码并返回 |
| 用户 | DELETE `/users/{id}` | 注销（软删除 + 手机号脱敏） |
| 用户 | GET `/users/{id}/orders`、`/users/{id}/products` | 该用户的订单/商品 |
| 商家 | GET `/sellers` | 商家列表（商品数、订单数、成交额） |
| 商家 | GET `/sellers/{id}/products` | 商家商品检索 |
| 商品 | GET `/products` | `status/keyword/tag_id/seller_id` |
| 商品 | PUT `/products/{id}/status` | `{status, reason}`，下架需原因并通知卖家 |
| 商品 | POST `/products/batch-status` | `{ids, status, reason}`，返回逐条结果 |
| 商品 | PUT `/products/{id}/feature` | `{featured}` 推荐位 |
| 评价 | GET `/comments` | 全站检索，`visibility=hidden/visible` |
| 评价 | PUT `/comments/{id}/visibility` | `{hidden, reason}` |
| 评价 | DELETE `/comments/{id}` | 软删除 |
| 订单 | GET `/orders`、`/orders/{id}`、`/orders/summary` | 检索 / 详情 / 状态汇总 |
| 订单 | POST `/orders/{id}/cancel`、`/refund` | 介入取消（退款入余额）/ 处理退款 |
| 分类 | GET/POST `/tags`、PUT/DELETE `/tags/{id}` | 平台分类；有商品的删除会转软删除并改名 |
| 轮播 | GET/POST `/banners`、PUT/DELETE `/banners/{id}` | 首页轮播 |
| 举报 | GET `/reports` | `status=待处理/已处理/已驳回` |
| 举报 | PUT `/reports/{id}` | `{status, result, action: none/hide_comment/off_product/ban_user}` |
| 审计 | GET `/audit-logs` | `keyword` 检索操作人与动作 |
| 导出 | GET `/export/{users|orders|products}` | CSV（UTF-8 BOM，Excel 直接可读） |

## 9. 前端调用示例

```js
// 登录后所有请求自动带 Authorization
const data = await orderApi.create({
  source: 'now',
  items: [{ product_id: 3, quantity: 1 }],
  pay_method: '余额',
  delivery_type: '面交',
  receiver_name: '赵一鸣',
  receiver_phone: '13800000004',
  address_text: '图书馆一楼'
})
// data.orders[0].actions => ['pay', 'cancel']
```

## 10. 变更策略

- 首版沿用 `/api`；升级到 `/api/v1` 时保留旧路径兼容层，不直接改名；
- 新增字段向后兼容；删除/改名字段必须同步 `services/serializers.py`、前端页面与本文档；
- 状态枚举只允许在 `backend/constants.py` 与 `frontend/src/utils/format.js` 同步修改。
