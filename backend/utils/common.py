"""时间与金额工具：数据库存 UTC，出参统一 ISO 8601 带时区。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

CST = timezone(timedelta(hours=8))
TWO_PLACES = Decimal("0.01")


def utcnow() -> datetime:
    """带时区的当前 UTC 时间（业务层统一使用）。"""
    return datetime.now(timezone.utc)


def ensure_aware(value: datetime | None) -> datetime | None:
    """SQLite 不保存时区信息，读出来是 naive，统一按 UTC 解释。"""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def iso(value: datetime | None) -> str | None:
    value = ensure_aware(value)
    if value is None:
        return None
    return value.astimezone(CST).isoformat(timespec="seconds")


def minutes_later(minutes: int) -> datetime:
    return utcnow() + timedelta(minutes=minutes)


def days_later(days: int) -> datetime:
    return utcnow() + timedelta(days=days)


def parse_local_datetime(value: str | None) -> datetime | None:
    """解析前端传来的时间：无时区按东八区理解，统一转 UTC。"""
    if not value:
        return None
    text = str(value).strip().replace(" ", "T")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError("时间格式不正确，请使用 YYYY-MM-DDTHH:MM") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=CST)
    return parsed.astimezone(timezone.utc)


def to_decimal(value, field: str = "金额") -> Decimal:
    """把任意输入转成两位小数 Decimal；非法输入抛 ValueError。"""
    if isinstance(value, Decimal):
        dec = value
    elif isinstance(value, bool):
        raise ValueError(f"{field}格式不正确")
    elif isinstance(value, (int, float)):
        dec = Decimal(str(value))
    elif isinstance(value, str):
        text = value.strip().lstrip("¥￥").replace(",", "")
        if not text:
            raise ValueError(f"{field}不能为空")
        try:
            dec = Decimal(text)
        except InvalidOperation as exc:
            raise ValueError(f"{field}格式不正确") from exc
    else:
        raise ValueError(f"{field}格式不正确")
    if not dec.is_finite():
        raise ValueError(f"{field}格式不正确")
    return dec.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def money(value: Decimal | int | float | None) -> float:
    """序列化为 JSON 数字（两位小数），入库仍用 Decimal。"""
    if value is None:
        return 0.0
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return float(value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP))


def order_no(prefix: str = "CB") -> str:
    """订单号：CB + yyyyMMdd + 6 位随机（PRD FR-ORDR-01 规定格式），配合唯一索引防重复。"""
    import random

    return f"{prefix}{utcnow().astimezone(CST).strftime('%Y%m%d')}{random.randint(0, 999999):06d}"


def mask_phone(phone: str | None) -> str:
    """管理端手机号脱敏（PRD 5.2）。"""
    if not phone:
        return ""
    return f"{phone[:3]}****{phone[-4:]}" if len(phone) >= 7 else phone

