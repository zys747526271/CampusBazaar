from flask import Blueprint, request, jsonify
from models.models import db, Ad
from utils.utils import result, getNowDateTime

ad_bp = Blueprint('ad', __name__)

@ad_bp.route("/api/ads/add", methods=["POST"])
def ads_add():
    """添加广告"""
    form = request.form
    image = request.files["image"]
    save_path = "./static/ads/" + image.filename
    image.save(save_path)
    data = {
        "content": form["content"],
        "createTime": getNowDateTime(),
        "displayTime": form["displayTime"],
        "endTime": form["endTime"],
        "image": save_path,
        "title": form["title"],
        "intro": form["intro"],
    }
    db.session.add(Ad(**data))
    db.session.commit()
    return result(200)

@ad_bp.route("/api/ads", methods=["GET"])
def ads():
    """获取广告列表"""
    ads = Ad.query.filter(Ad.displayTime >= getNowDateTime()).all()
    data = {"data": [dict(a.__dict__, _sa_instance_state=None) for a in ads]}
    return result(200, data)

@ad_bp.route("/api/ads/delete", methods=["DELETE"])
def ads_delete():
    """删除广告"""
    _id = request.form["id"]
    Ad.query.filter_by(_id=_id).delete()
    db.session.commit()
    return result(200)