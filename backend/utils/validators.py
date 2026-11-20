"""请求参数校验：集中收集字段级错误，一次性返回 422。

用法::

    p = Payload(request.get_json(silent=True))
    name = p.text("name", min_len=2, max_len=60)
    price = p.decimal("price", min_value=Decimal("0.01"))
    p.done()   # 有错误则抛 422 VALIDATION_ERROR，details 为 {字段: 原因}
"""
from __future__ import annotations

import re
from decimal import Decimal
from typing import Any, Iterable

from backend.constants import Limits
from backend.errors import validation
from backend.utils.common import to_decimal

PHONE_RE = re.compile(r"^1[3-9]\d{9}$")
PASSWORD_LETTER = re.compile(r"[A-Za-z]")
PASSWORD_DIGIT = re.compile(r"\d")
NICKNAME_RE = re.compile(r"^[^\s<>\"'`\\/]{1,20}$")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def clean_text(value: str, max_len: int | None = None) -> str:
    text = _CONTROL_RE.sub("", value).strip()
    if max_len:
        text = text[:max_len]
    return text


class Payload:
    def __init__(self, data: Any) -> None:
        self.raw: dict = data if isinstance(data, dict) else {}
        self.errors: dict[str, str] = {}

    # ---------- 内部 ----------
    def _label(self, key: str, label: str | None) -> str:
        return label or key

    def _missing(self, key: str, label: str | None, required: bool, default: Any) -> bool:
        value = self.raw.get(key)
        if value is None or (isinstance(value, str) and value.strip() == ""):
            if required:
                self.errors[key] = f"{self._label(key, label)}不能为空"
            return True
        return False

    def add_error(self, key: str, message: str) -> None:
        self.errors.setdefault(key, message)

    # ---------- 字段 ----------
    def text(
        self,
        key: str,
        *,
        required: bool = True,
        min_len: int = 1,
        max_len: int = 200,
        label: str | None = None,
        default: str = "",
    ) -> str:
        if self._missing(key, label, required, default):
            return default
        value = clean_text(str(self.raw[key]))
        name = self._label(key, label)
        if len(value) < min_len:
            self.errors[key] = f"{name}至少 {min_len} 个字符"
        elif len(value) > max_len:
            self.errors[key] = f"{name}不能超过 {max_len} 个字符"
        return value

    def phone(self, key: str = "phone", label: str = "手机号") -> str:
        value = self.text(key, label=label, max_len=11)
        if value and not PHONE_RE.match(value):
            self.errors[key] = "请输入 11 位有效手机号"
        return value

    def password(self, key: str = "password", label: str = "密码") -> str:
        value = str(self.raw.get(key) or "")
        if not value:
            self.errors[key] = f"{label}不能为空"
            return ""
        if len(value) < 8 or len(value) > 32:
            self.errors[key] = f"{label}长度需为 8~32 位"
        elif not PASSWORD_LETTER.search(value) or not PASSWORD_DIGIT.search(value):
            self.errors[key] = f"{label}必须同时包含字母和数字"
        return value

    def integer(
        self,
        key: str,
        *,
        required: bool = True,
        min_value: int | None = None,
        max_value: int | None = None,
        label: str | None = None,
        default: int = 0,
    ) -> int:
        if self._missing(key, label, required, default):
            return default
        raw = self.raw[key]
        try:
            value = int(str(raw).strip())
        except (TypeError, ValueError):
            self.errors[key] = f"{self._label(key, label)}必须是整数"
            return default
        if min_value is not None and value < min_value:
            self.errors[key] = f"{self._label(key, label)}不能小于 {min_value}"
        if max_value is not None and value > max_value:
            self.errors[key] = f"{self._label(key, label)}不能大于 {max_value}"
        return value

    def decimal(
        self,
        key: str,
        *,
        required: bool = True,
        min_value: Decimal | None = None,
        max_value: Decimal | None = None,
        label: str | None = None,
        default: Decimal = Decimal("0"),
    ) -> Decimal:
        if self._missing(key, label, required, default):
            return default
        name = self._label(key, label)
        try:
            value = to_decimal(self.raw[key], name)
        except ValueError as exc:
            self.errors[key] = str(exc)
            return default
        if min_value is not None and value < min_value:
            self.errors[key] = f"{name}不能小于 {min_value}"
        if max_value is not None and value > max_value:
            self.errors[key] = f"{name}不能大于 {max_value}"
        return value

    def boolean(self, key: str, *, default: bool = False) -> bool:
        raw = self.raw.get(key, default)
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, (int, float)):
            return bool(raw)
        if isinstance(raw, str):
            return raw.strip().lower() in ("1", "true", "yes", "on")
        return default

    def choice(
        self,
        key: str,
        allowed: Iterable[str],
        *,
        required: bool = True,
        label: str | None = None,
        default: str = "",
    ) -> str:
        if self._missing(key, label, required, default):
            return default
        value = str(self.raw[key]).strip()
        allowed = tuple(allowed)
        if value not in allowed:
            self.errors[key] = f"{self._label(key, label)}只能是：{'、'.join(allowed)}"
        return value

    def str_list(
        self,
        key: str,
        *,
        max_items: int = 9,
        max_len: int = 500,
        label: str | None = None,
        default: list[str] | None = None,
    ) -> list[str]:
        raw = self.raw.get(key)
        if raw is None:
            return list(default or [])
        if not isinstance(raw, list):
            self.errors[key] = f"{self._label(key, label)}格式不正确"
            return []
        if len(raw) > max_items:
            self.errors[key] = f"{self._label(key, label)}最多 {max_items} 项"
        values = [clean_text(str(item), max_len) for item in raw if str(item).strip()]
        return values[:max_items]

    def int_list(self, key: str, *, max_items: int = 100, label: str | None = None) -> list[int]:
        raw = self.raw.get(key)
        if raw is None:
            return []
        if not isinstance(raw, list):
            self.errors[key] = f"{self._label(key, label)}格式不正确"
            return []
        result: list[int] = []
        for item in raw:
            try:
                result.append(int(item))
            except (TypeError, ValueError):
                self.errors[key] = f"{self._label(key, label)}包含非法值"
                return []
        return result[:max_items]

    # ---------- 收尾 ----------
    def take(self, key: str) -> Any:
        return self.raw.get(key)

    def done(self) -> None:
        if self.errors:
            first = next(iter(self.errors.values()))
            raise validation(first, self.errors)


def validate_nickname(value: str) -> str:
    if not NICKNAME_RE.match(value):
        raise validation("昵称不能包含空格或特殊符号", {"nickname": "昵称格式不正确"})
    return value


def normalize_keyword(value: str | None) -> str:
    """搜索关键词：去控制字符、限长，不做 LIKE 通配符转义外的任何拼接。"""
    if not value:
        return ""
    return clean_text(value, Limits.KEYWORD_MAX_LEN)


def escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
