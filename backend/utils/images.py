"""图片上传（PRD 7.7）：扩展名 + MIME + 文件头三重校验，重命名存储，生成缩略图。"""
from __future__ import annotations

import io
import uuid
from datetime import datetime
from pathlib import Path

from flask import current_app
from PIL import Image, ImageOps, UnidentifiedImageError

from backend.constants import Limits
from backend.errors import bad_request

#: 允许的类型：扩展名 -> (magic 前缀, PIL 格式, 输出扩展名)
ALLOWED = {
    "jpg": ("image/jpeg", b"\xff\xd8\xff", "JPEG", "jpg"),
    "jpeg": ("image/jpeg", b"\xff\xd8\xff", "JPEG", "jpg"),
    "png": ("image/png", b"\x89PNG\r\n\x1a\n", "PNG", "png"),
    "webp": ("image/webp", b"RIFF", "WEBP", "webp"),
}
THUMB_SIZE = (400, 400)

Image.MAX_IMAGE_PIXELS = 40_000_000


def _detect(raw: bytes, ext: str) -> tuple[str, str] | None:
    meta = ALLOWED.get(ext.lower())
    if not meta:
        return None
    mime, magic, fmt, out_ext = meta
    if ext.lower() == "webp":
        if not (raw[:4] == b"RIFF" and raw[8:12] == b"WEBP"):
            return None
    elif not raw.startswith(magic):
        return None
    return fmt, out_ext


def save_image(file_storage) -> dict:
    if file_storage is None or not file_storage.filename:
        raise bad_request("请选择要上传的图片", {"file": "文件不能为空"})

    filename = file_storage.filename
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    raw = file_storage.read()
    if not raw:
        raise bad_request("图片内容为空", {"file": "文件内容为空"})
    if len(raw) > Limits.IMAGE_MAX_BYTES:
        raise bad_request("单张图片不能超过 5MB", {"file": "图片过大"})

    detected = _detect(raw, ext)
    if detected is None:
        raise bad_request("仅支持 JPG / PNG / WebP 图片", {"file": "图片格式不支持"})
    pil_format, out_ext = detected

    declared_mime = (file_storage.mimetype or "").lower()
    if declared_mime and declared_mime not in ("application/octet-stream",) and not declared_mime.startswith("image/"):
        raise bad_request("图片类型校验失败", {"file": "MIME 类型不匹配"})

    try:
        image = Image.open(io.BytesIO(raw))
        image.verify()
        image = Image.open(io.BytesIO(raw))  # verify 之后必须重新打开
    except (UnidentifiedImageError, OSError) as exc:
        raise bad_request("图片已损坏或不是有效图片", {"file": "图片解析失败"}) from exc

    width, height = image.size
    if width < 10 or height < 10:
        raise bad_request("图片尺寸过小", {"file": "图片尺寸不合法"})
    if width > 8000 or height > 8000:
        raise bad_request("图片尺寸过大（最大 8000px）", {"file": "图片尺寸不合法"})

    # 统一转 RGB（JPEG 不支持透明通道），并丢弃 EXIF 等可能携带的敏感信息
    if pil_format == "JPEG":
        image = image.convert("RGB")
    elif pil_format == "PNG":
        image = image.convert("RGBA") if image.mode in ("RGBA", "LA", "P") else image.convert("RGB")

    now = datetime.now()
    relative_dir = Path(f"{now:%Y}/{now:%m}")
    target_dir = Path(current_app.config["UPLOAD_ROOT"]) / relative_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    stem = uuid.uuid4().hex
    filename_out = f"{stem}.{out_ext}"
    save_kwargs = {"optimize": True}
    if pil_format == "JPEG":
        save_kwargs.update({"quality": 86, "progressive": True})
    image.save(target_dir / filename_out, pil_format, **save_kwargs)

    # 列表用缩略图：等比裁切为正方形，减小首屏体积
    thumb = ImageOps.fit(image.convert("RGB"), THUMB_SIZE, Image.LANCZOS)
    thumb_name = f"{stem}_thumb.jpg"
    thumb.save(target_dir / thumb_name, "JPEG", quality=82, optimize=True)

    url_base = f"/static/uploads/{relative_dir.as_posix()}"
    return {
        "url": f"{url_base}/{filename_out}",
        "thumb_url": f"{url_base}/{thumb_name}",
        "width": width,
        "height": height,
        "size": len(raw),
    }
