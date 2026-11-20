"""短信验证码（PRD FR-AUTH-02/03/04）。

- dev 模式：不真的发短信，控制台打印 + 接口回显 dev_code + ``/dev/captchas`` 页面可查；
- prod 模式：未配置短信网关时注册直接 503，禁止静默放行；
- 验证码一次性消费、5 分钟过期。
"""
from __future__ import annotations

import random
import time

from flask import current_app

from backend.constants import Limits
from backend.errors import bad_request, unavailable
from backend.extensions import cache
from backend.utils.logging import app_log

SCENES = {"register": "注册", "reset": "重置密码", "login": "登录"}
_DEV_LEDGER_KEY = "captcha:dev:ledger"


def _key(scene: str, phone: str) -> str:
    return f"captcha:{scene}:{phone}"


def issue(phone: str, scene: str) -> dict:
    if scene not in SCENES:
        raise bad_request("验证码场景不合法")
    mode = current_app.config.get("CAPTCHA_MODE", "dev")
    if mode == "prod" and not current_app.config.get("SMS_GATEWAY_ENABLED"):
        raise unavailable("短信服务未配置，暂时无法发送验证码，请联系管理员")

    code = f"{random.randint(0, 999999):06d}"
    ttl = Limits.CAPTCHA_TTL_MINUTES * 60
    cache.set(_key(scene, phone), {"code": code, "issued_at": time.time()}, timeout=ttl)

    result = {"expires_in": ttl, "scene": scene, "phone": _mask_phone(phone)}
    if mode == "dev":
        print(f"[CampusBazaar] 验证码 {phone}（{SCENES[scene]}）= {code}（{Limits.CAPTCHA_TTL_MINUTES} 分钟内有效）")
        _remember_dev(phone, scene, code)
        result["dev_code"] = code
    else:
        # 生产：此处接入真实短信网关（预留适配点，不改变业务代码结构）
        app_log("sms.send", f"scene={scene} phone={_mask_phone(phone)}")
    return result


def verify(phone: str, scene: str, code: str) -> None:
    if not code:
        raise bad_request("请填写验证码", {"code": "验证码不能为空"})
    record = cache.get(_key(scene, phone))
    if not record:
        raise bad_request("验证码已过期，请重新获取", {"code": "验证码已过期"})
    if record.get("code") != str(code).strip():
        raise bad_request("验证码不正确", {"code": "验证码不正确"})
    # 一次性消费
    cache.delete(_key(scene, phone))


def _remember_dev(phone: str, scene: str, code: str) -> None:
    ledger = cache.get(_DEV_LEDGER_KEY) or []
    ledger.insert(0, {"phone": phone, "scene": scene, "code": code, "created_at": time.time()})
    cache.set(_DEV_LEDGER_KEY, ledger[:20], timeout=3600)


def dev_ledger() -> list[dict]:
    if current_app.config.get("CAPTCHA_MODE") == "prod":
        return []
    return cache.get(_DEV_LEDGER_KEY) or []


def _mask_phone(phone: str) -> str:
    return f"{phone[:3]}****{phone[-4:]}" if len(phone) >= 7 else phone
