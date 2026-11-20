from flask import Blueprint, request, session, jsonify
from models.models import db, Vip, User, VipReceipt
from utils.utils import result, getNowDateTime, getOrderNum
import traceback

vip_bp = Blueprint('vip', __name__)

@vip_bp.route("/api/vip", methods=["GET"])
def vip():
    """获取VIP列表"""
    vips = Vip.query.all()
    data = [{"_id": v._id, "name": v.name, "level": v.level} for v in vips]
    return jsonify({"code": 200, "data": data})

@vip_bp.route("/api/vip/add", methods=["POST"])
def vip_add():
    """添加VIP类型"""
    name = request.form["name"]
    level = request.form["level"]
    db.session.add(Vip(name=name, level=level))
    db.session.commit()
    return result(200)

@vip_bp.route("/api/vip/delete", methods=["DELETE"])
def vip_delete():
    """删除VIP类型"""
    _id = request.form["id"]
    Vip.query.filter_by(_id=_id).delete()
    db.session.commit()
    return result(200)

@vip_bp.route("/api/buy/vip", methods=["POST"])
def buy_vip():
    """购买VIP"""
    sId = session.get("_id")
    if not sId:
        return jsonify({"code": 203, "info": "未登录"})
    data = request.get_json()
    vip_id = data.get("vipId")
    if not vip_id:
        return jsonify({"code": 400, "info": "VIP 卡 ID 不能为空"})
    vip = Vip.query.get(vip_id)
    user = User.query.get(sId)
    if not vip or not user:
        return jsonify({"code": 404, "info": "VIP 卡或用户不存在"})
    vip_price = vip.level * 100
    if user.balance < vip_price:
        return jsonify({"code": 204, "info": "余额不足"})
    try:
        user.balance -= vip_price
        db.session.add(VipReceipt(orderNum=getOrderNum(), createTime=getNowDateTime(), payValue=vip_price, cutoffValue=0, user_id=sId, vipId=vip_id))
        user.vip = vip_id
        db.session.commit()
        return jsonify({"code": 200, "info": "购买成功"})
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({"code": 500, "info": "购买失败", "error": str(e)})

@vip_bp.route("/api/self/vip", methods=["GET"])
def self_vip():
    """获取用户VIP购买记录"""
    sId = session.get("_id")
    if not sId:
        return result(203, {"info": "未登录"})
    vrs = VipReceipt.query.filter_by(user_id=sId).all()
    data = {"data": [dict(vr.__dict__, _sa_instance_state=None) for vr in vrs]}
    return result(200, data)