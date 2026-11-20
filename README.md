# CampusBazaar · 校园集市

> 一个面向校园场景的二手交易平台：学生买家、学生卖家、网站管理员三类角色共存。  
> 当前状态：**v1 已完成交易主链路，正在进行 v2 重构**。重建基线见 **`docs/00-需求规格说明书.md`**（需求冻结后以它为准，`docs/01`~`05` 降级为历史参考）。

CampusBazaar 面向校园内的二手交易场景：买家免登录即可浏览，购买时才需要登录；任何学生都能一键开通卖家身份管理自己的商品；管理员拥有独立的入口与治理后台。项目同时支持「本地零依赖演示」与「生产多实例部署」两种形态。

---

## 1. 角色与定位

| 角色    | 定位           | 典型能力（规划）                          |
| ----- | ------------ | --------------------------------- |
| 学生买家  | 浏览、购买、收货、评价  | 商品浏览/搜索、购物车、下单支付、订单管理、评价、余额充值     |
| 学生卖家  | 发布商品、管理自己的店铺 | 商品发布与审核跟踪、库存管理、订单发货、经营数据          |
| 网站管理员 | 平台治理         | 用户/卖家审核、商品审核、订单监管、分类/标签管理、封禁、数据统计 |

---

## 2. 技术栈

**后端**：Flask 3.1 + Flask-SQLAlchemy 3.1（MySQL）+ Flask-Caching 2.5（Redis）+ 手写 JWT 鉴权 + PyJWT 2.15  
**前端**：Vue 3.5 + Vite 6 + Pinia 3 + Element Plus 2.4 + Axios 1.x  
**可选运行方式**：waitress（WSGI 服务器）

---

## 3. 目录结构

```
CampusBazaar/
├── README.md                 本文件
├── .env.example              环境变量模板（复制为 .env 使用）
├── requirements.txt          后端 Python 依赖
├── backend/                  后端（Flask）
│   ├── app.py                应用入口（create_app 工厂 + 健康检查）
│   ├── config.py             配置（密钥/数据库/Redis 均从环境变量读取）
│   ├── models/               数据模型（User/Admin/Product/Cart/Order/Address/...）
│   ├── routes/               蓝图路由（auth/admin/user/product/cart/order/...）
│   ├── utils/                JWT 鉴权、缓存、上传、推荐、支付桩等工具
│   ├── templates/            API 概览页
│   └── static/              上传目录与数据目录（运行时生成）
├── frontend/                 前端（Vue 3 + Vite）
│   ├── src/views/            页面（home/product/cart/order/user/auth/admin）
│   ├── src/router/           路由与守卫
│   ├── src/stores/           Pinia 状态
│   └── src/utils/api.js      Axios 封装
├── docs/                     设计与规划文档
│   ├── 00-需求规格说明书.md     ★ v2 需求基线（先读这份）
│   ├── 01-项目架构与现状说明.md
│   ├── 02-数据模型设计.md
│   ├── 03-角色与权限设计.md
│   ├── 04-API清单.md
│   ├── 05-已知问题与路线图.md
│   └── 06-本地运行与测试指南.md
└── scripts/                  辅助脚本
```

---

## 4. 快速开始

> 完整、逐步的运行与测试方法（含免数据库的快速冒烟模式）见 **`docs/06-本地运行与测试指南.md`**。

###

### 4.1 配置

```bash
cp .env.example .env
# 本地开发无需改数据库配置：CAMPUS_CONFIG=local 会使用
# instance/campus_bazaar.db（SQLite）与进程内缓存，不需要安装 MySQL / Redis
```

生产环境才需要设置 `CAMPUS_CONFIG=production` 与数据库、Redis、JWT 密钥等变量，详见 `docs/00-需求规格说明书.md` 第 9 章「环境与部署」。

### 4.2 启动后端

```bash
# 从项目根目录
python -m backend.app
# 默认监听 0.0.0.0:5000，访问 http://localhost:5000 查看 API 概览
```

### 4.3 启动前端

```bash
cd frontend
npm install
npm run dev
# 默认 http://localhost:8080，代理 /api 到 localhost:5000
```

---

## 5. 当前状态与后续工作

v1 已跑通的主链路：注册/登录（含验证码）、商品浏览与发布、收藏与浏览记录、购物车、下单与订单状态机、卖家中心、管理后台（含商家与评价治理）。

v1 遗留的问题集中在"契约不一致"而非功能缺失，v2 以需求为基线重建，不做增量修补。完整需求、业务规则、验收标准与部署方案见 **`docs/00-需求规格说明书.md`**，摘要如下：

- **运行形态**：本地用 SQLite + 进程内缓存，零外部依赖启动；生产切 MySQL + Redis，同一份代码靠 `CAMPUS_CONFIG` 切换。
- **权限模型**：用户令牌与管理员令牌彻底分离；401 仅表示未认证，403 表示无权限，前端不再"见 401 就跳登录"。
- **接口契约**：统一响应 `{success, code, message, data, request_id}`，列表固定 `data.items + data.total`。
- **治理能力**：商品审核、评价隐藏、用户封禁、操作审计。
- **运维**：`logs/` 下按 access / error / security / app 分类落盘，按天滚动。

后续按 M1（交易闭环）→ M2（卖家与治理）→ M3（生产就绪）→ M4（体验优化）推进。

---

## 6. 许可

本项目采用 **Apache License 2.0**，详见 `LICENSE`。
