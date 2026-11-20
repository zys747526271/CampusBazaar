# 04 · API 清单

> 以下为主工程后端 `backend/routes/` 中注册的实际路由（蓝图前缀 + 路由内路径推导）。
> 标注 ⚠️ 的表示实现与模型/前端存在已知不一致，详见 `05-已知问题与路线图.md`。

## 认证 `/api/auth`
| 方法 | 路径 | 鉴权 | 说明 |
| --- | --- | --- | --- |
| POST | /captcha | 无 | 验证码（⚠️ 当前 print 到控制台并写日志） |
| POST | /register | 无 | 学生注册（自动创建余额账户） |
| POST | /login | 无 | 登录签发 JWT |
| POST | /admin/register | 无 | ⚠️ 管理员注册开放，需关闭 |
| POST | /admin/login | 无 | 管理员登录 |
| GET | /profile | token | 个人信息 |
| PUT | /profile | token | 更新资料 |
| GET | /profile/id-card | token | 身份证号掩码/完整切换 |

## 用户 `/api/users`
GET /profile、PUT /profile、PUT /password（均需登录）

## 商品 `/api/products`
| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | / | 商品列表（缓存 300s，⚠️ 字段 category_id） |
| GET | /<id> | 详情（⚠️ to_dict 参数名） |
| POST | / | 发布商品（⚠️ 应限制卖家角色） |
| PUT | /<id> | 修改商品 |
| POST | /<id>/images | 上传图片（⚠️ 字段 image_urls） |
| DELETE | /<id> | 软删除 |
| PUT | /<id>/status | 管理员改审核状态（⚠️ 中英文状态冲突） |
| GET | /recommended | 协同过滤推荐 |
| GET | /hot | 热门商品 |

## 购物车 `/api/carts`
GET /cart、POST /cart、PUT /cart/<id>、DELETE /cart/<id>、DELETE /cart/batch
（⚠️ 状态值 `'已通过'` 与 `'approved'` 冲突，可能导致商品无法下单）

## 订单 `/api/orders`
列表/详情/创建/改状态/删除 + 管理端接口；注意蓝图前缀重复导致实际路径为 `/api/orders/orders`（⚠️）

## 地址 `/api/addresses`
列表/新增/修改/删除/默认地址/省市区数据（⚠️ 依赖缺失的 `static/data/regions.json`）

## 分类 `/api/tags`、评论 `/api/comments`、余额 `/api/balances`、消息 `/api/messages`、管理 `/api/admin`
详见源码 `backend/routes/`；其中 tag/message/admin/order 蓝图存在路径双前缀问题。

## 健康检查
GET `/api/health` → `{ "status": "ok" }`；GET `/` → API 概览页。
