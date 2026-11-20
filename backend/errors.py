"""统一错误模型。

设计要点（PRD 7.3 / 附录 A 第 2、3 条）：
- HTTP 状态码与 ``code`` 一一对应，禁止 200 包错误；
- 401 只表示"未认证/令牌无效"，403 只表示"已认证但无权限"；
- 任何异常最终都会被 app 级 errorhandler 转成统一响应结构。
"""
from typing import Any


class ErrorCode:
    OK = "OK"
    CREATED = "CREATED"
    BAD_REQUEST = "BAD_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    TOO_MANY_REQUESTS = "TOO_MANY_REQUESTS"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ApiError(Exception):
    """业务异常。由 app.errorhandler 统一渲染。"""

    def __init__(
        self,
        message: str,
        status: int = 400,
        code: str = ErrorCode.BAD_REQUEST,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code
        self.details = details


def bad_request(message: str = "请求参数有误", details: Any = None) -> ApiError:
    return ApiError(message, 400, ErrorCode.BAD_REQUEST, details)


def unauthorized(message: str = "请先登录") -> ApiError:
    return ApiError(message, 401, ErrorCode.UNAUTHORIZED)


def forbidden(message: str = "没有操作权限") -> ApiError:
    return ApiError(message, 403, ErrorCode.FORBIDDEN)


def not_found(message: str = "资源不存在") -> ApiError:
    return ApiError(message, 404, ErrorCode.NOT_FOUND)


def conflict(message: str = "操作冲突，请刷新后重试", details: Any = None) -> ApiError:
    return ApiError(message, 409, ErrorCode.CONFLICT, details)


def validation(message: str = "字段校验失败", details: Any = None) -> ApiError:
    return ApiError(message, 422, ErrorCode.VALIDATION_ERROR, details)


def too_many(message: str = "操作过于频繁，请稍后再试", details: Any = None) -> ApiError:
    return ApiError(message, 429, ErrorCode.TOO_MANY_REQUESTS, details)


def unavailable(message: str = "服务暂不可用，请稍后再试") -> ApiError:
    return ApiError(message, 503, ErrorCode.SERVICE_UNAVAILABLE)
