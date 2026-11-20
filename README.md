# CampusBazaar · 校园集市

> 一个面向校园场景的购物/交易平台骨架：学生买家、学生卖家、网站管理员三类角色共存。
> 当前状态：**结构整合与构建优先，业务功能尚未完成**，适合在此基础上继续开发。

CampusBazaar 由两个早期原型项目整合而来，目标是提供一个目录清晰、依赖明确、密钥安全、文档完整的校园购物平台起点。本仓库保留了两份原始代码作为参考，统一了技术栈与配置方式，并给出了面向三角色（买家 / 卖家 / 管理员）的数据模型与 API 设计蓝图。

---

## 1. 角色与定位

| 角色 | 定位 | 典型能力（规划） |
| --- | --- | --- |
| 学生买家 | 浏览、购买、收货、评价 | 商品浏览/搜索、购物车、下单支付、订单管理、评价、余额充值 |
| 学生卖家 | 发布商品、管理自己的店铺 | 商品发布与审核跟踪、库存管理、订单发货、经营数据 |
| 网站管理员 | 平台治理 | 用户/卖家审核、商品审核、订单监管、分类/标签管理、封禁、数据统计 |

---

## 2. 技术栈

**后端（主）**：Flask 3.1 + Flask-SQLAlchemy 3.1（MySQL）+ Flask-Caching 2.5（Redis）+ 手写 JWT 鉴权 + PyJWT 2.15
**前端（主）**：Vue 3.5 + Vite 6 + Pinia 3 + Element Plus 2.4 + Axios 1.x
**可选运行方式**：waitress（WSGI 服务器）

> 说明：原始 demo 项目使用的是 Vue 2 + Element UI + Flask Session 方案，作为参考代码保留在 `reference/`，未合并进主工程，避免两套技术栈互相污染。

---

## 3. 目录结构

```
CampusBazaar/
├── README.md                 本文件
├── .env.example              环境变量模板（复制为 .env 使用）
├── requirements.txt          后端 Python 依赖
├── backend/                  主后端（Flask）
│   ├── app.py                应用入口（create_app 工厂 + 健康检查）
│   ├── config.py             配置（密钥/数据库/Redis 均从环境变量读取）
│   ├── models/               数据模型（User/Admin/Product/Cart/Order/Address/...）
│   ├── routes/               蓝图路由（auth/admin/user/product/cart/order/...）
│   ├── utils/                JWT 鉴权、缓存、上传、推荐、支付桩等工具
│   ├── templates/            API 概览页
│   └── static/              上传目录与数据目录（运行时生成）
├── frontend/                 主前端（Vue 3 + Vite）
│   ├── src/views/            页面（home/product/cart/order/user/auth/admin）
│   ├── src/router/           路由与守卫
│   ├── src/stores/           Pinia 状态
│   └── src/utils/api.js      Axios 封装
├── reference/                原始项目参考代码（只读留存，不参与构建）
│   ├── demo-vue2-mall/       原 demo 的 Vue 2 + Element UI 前端
│   └── demo-flask-mallh/     原 demo 的 Flask + Session 后端
├── docs/                     设计与整合文档
│   ├── 01-项目分析与整合说明.md
│   ├── 02-数据模型设计.md
│   ├── 03-角色与权限设计.md
│   ├── 04-API清单.md
│   └── 05-已知问题与路线图.md
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

具体整合依据与改造建议见 `docs/` 目录。

---

## 6. 来源与许可

本项目整合自以下两个早期原型（作为参考保留于 `reference/`）：
- `demo-----`（Vue 2 + Flask Session 商城）
- `FlaskWebProject`（Vue 3 + Flask JWT 校园二手平台）

整合后的代码采用 **Apache License 2.0**，见 `LICENSE`（原项目声明为 MIT，其许可条款仍归原作者所有）。
