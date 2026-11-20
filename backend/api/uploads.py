"""通用图片上传（PRD FR-SELL-03 / 7.7）：不依赖业务 ID，先传图后建商品。"""
from __future__ import annotations

from flask import Blueprint, request

from backend.constants import Limits
from backend.errors import bad_request
from backend.utils import limiter
from backend.utils.images import save_image
from backend.utils.response import created
from backend.utils.security import login_required

bp = Blueprint("uploads", __name__, url_prefix="/api/uploads")


@bp.post("/image")
@login_required
def upload_image():
    limiter.by_user("upload", Limits.RATE_UPLOAD, "上传过于频繁，请稍后再试")
    file = request.files.get("file")
    if file is None:
        raise bad_request("请选择要上传的图片", {"file": "文件不能为空"})
    result = save_image(file)
    return created(result, "上传成功")
