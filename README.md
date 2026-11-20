# CampusBazaar · 校园集市

> 一个面向校园场景的购物/交易平台骨架：学生买家、学生卖家、网站管理员三类角色共存。
> 当前状态：**骨架构建与整理优先，业务功能尚未完成**，适合在此基础上继续开发。

CampusBazaar 是面向校园购物/交易场景的项目起点：目录清晰、依赖明确、密钥安全、文档完整，并给出面向三角色（买家 / 卖家 / 管理员）的数据模型与 API 设计蓝图。

---

## 1. 角色与定位

| 角色 | 定位 | 典型能力（规划） |
| --- | --- | --- |
| 学生买家 | 浏览、购买、收货、评价 | 商品浏览/搜索、购物车、下单支付、订单管理、评价、余额充值 |
| 学生卖家 | 发布商品、管理自己的店铺 | 商品发布与审核跟踪、库存管理、订单发货、经营数据 |
| 网站管理员 | 平台治理 | 用户/卖家审核、商品审核、订单监管、分类/标签管理、封禁、数据统计 |

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

### 4.1 准备工具

项目附带的便携 Python 位于同级目录 `../tool/python-win/`（WorkBuddy 便携运行时，Python 3.11）。
也可以直接使用系统已安装的 Python 3.11+。

```bash
# 用便携 Python（从项目根目录执行，按实际路径调整）
../tool/python-win/python.exe -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt
```

### 4.2 配置

```bash
# 复制环境变量模板
cp .env.example .env
# 编辑 .env，填入数据库、Redis、密钥等真实配置
```

数据库需要先手动创建（例如 `campus_bazaar`），表结构由 `db.create_all()` 自动创建。
Fernet 密钥可用 `python backend/utils/miyao.py` 生成。

### 4.3 启动后端

```bash
# 从项目根目录
python -m backend.app
# 默认监听 0.0.0.0:5000，访问 http://localhost:5000 查看 API 概览
```

### 4.4 启动前端

```bash
cd frontend
npm install
npm run dev
# 默认 http://localhost:8080，代理 /api 到 localhost:5000
```

---

## 5. 当前状态与后续工作

- 后端 11 个蓝图、前端主要页面均已就位，但**字段/URL/状态枚举存在多处不一致**，详见 `docs/05-已知问题与路线图.md`。
- 三角色（买家/卖家/管理员）的**完整权限体系尚未落地**：目前 `Admin` 独立表 + `User` 兼做买家/卖家，身份模型需要统一设计。
- 管理员注册接口当前是开放的，生产环境前必须关闭或加审批。
- 支付相关为 TODO 桩，未接入真实网关。

设计文档与改造建议见 `docs/` 目录。

---

## 6. 许可

本项目采用 **Apache License 2.0**，详见 `LICENSE`。
