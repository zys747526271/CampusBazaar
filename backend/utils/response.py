"""统一响应包装与分页（PRD 7.2）。

所有列表接口固定返回 ``{"items": [...], "total": n, "page": 1, "per_page": 20, "pages": m}``，
禁止出现 ``products`` / ``list`` / ``rows`` 等别名。
"""
from __future__ import annotations

import math
from typing import Any, Callable, Iterable

from flask import g, jsonify, request

from backend.constants import SORT_ALIASES
from backend.errors import ErrorCode


def request_id() -> str:
    return getattr(g, "request_id", "") or ""


def respond(
    data: Any = None,
    message: str = "操作成功",
    code: str = ErrorCode.OK,
    status: int = 200,
):
    """构造统一响应；``success`` 与 HTTP 状态码严格一致。"""
    body = {
        "success": 200 <= status < 400,
        "code": code,
        "message": message,
        "data": data,
        "request_id": request_id(),
    }
    response = jsonify(body)
    response.status_code = status
    return response


def ok(data: Any = None, message: str = "操作成功"):
    return respond(data, message, ErrorCode.OK, 200)


def created(data: Any = None, message: str = "创建成功"):
    return respond(data, message, ErrorCode.CREATED, 201)


def page_result(items: Iterable, total: int, page: int, per_page: int) -> dict:
    return {
        "items": list(items),
        "total": int(total),
        "page": page,
        "per_page": per_page,
        "pages": math.ceil(total / per_page) if per_page else 0,
    }


def page_args(default_per_page: int = 20, max_per_page: int = 100) -> tuple[int, int]:
    try:
        page = int(request.args.get("page", 1))
    except (TypeError, ValueError):
        page = 1
    try:
        per_page = int(request.args.get("per_page", default_per_page))
    except (TypeError, ValueError):
        per_page = default_per_page
    return max(page, 1), min(max(per_page, 1), max_per_page)


def paginate(query, serializer: Callable[[Any], dict], default_per_page: int = 20) -> dict:
    page, per_page = page_args(default_per_page)
    total = query.order_by(None).count()
    rows = query.limit(per_page).offset((page - 1) * per_page).all()
    return page_result([serializer(row) for row in rows], total, page, per_page)


def normalize_sort(sort: str | None, order: str | None) -> tuple[str, str]:
    """白名单校验；非法值回退 created_at，不允许把用户输入拼进 SQL。"""
    key = (sort or "created_at").strip().lower()
    key = SORT_ALIASES.get(key, key)
    if key not in ("created_at", "price", "sales", "views"):
        key = "created_at"
    direction = (order or "desc").strip().lower()
    if direction not in ("asc", "desc"):
        direction = "desc"
    return key, direction
