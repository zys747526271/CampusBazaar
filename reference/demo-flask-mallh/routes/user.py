from flask import Blueprint, request, session, jsonify
from models.models import db, User, Address, Court, Vip, goodsCourt, Goods
from utils.utils import result
from datetime import datetime
import json

user_bp = Blueprint('user', __name__)

@user_bp.route("/api/self", methods=["GET"])
def self_info():
    """获取用户信息"""
    sId = session.get('_id')
    if not sId:
        return result(203, {"info": "未登录"})
    user = User.query.get(sId)
    if not user:
        return result(201, {"info": "用户不存在"})
    user_dict = dict(user.__dict__, _sa_instance_state=None)
    for key, value in user_dict.items():
        if isinstance(value, datetime):
            user_dict[key] = value.strftime("%Y-%m-%d %H:%M:%S")
    user_dict['vip'] = Vip.query.get(user_dict['vip']).name if user_dict['vip'] else '暂无VIP'
    user_dict['address'] = [dict(a.__dict__, _sa_instance_state=None) for a in Address.query.filter_by(user_id=sId).all()]
    user_dict['name'] = user_dict['name'] or '未命名'
    return result(200, user_dict)

@user_bp.route("/api/update/self", methods=["POST"])
def update_self():
    """更新用户信息"""
    sId = session.get("_id")
    user = User.query.get(sId)
    if not user:
        return result(201, {"info": "用户不存在"})
    data = request.get_json()
    user.name = data.get("name", user.name)
    user.gender = data.get("gender", user.gender)
    addresses = json.loads(data.get("address", "[]"))
    Address.query.filter_by(user_id=sId).delete()
    for addr in addresses:
        db.session.add(Address(province=addr["province"], town=addr["town"], county=addr["county"], detail=addr["detail"], user_id=sId))
    db.session.commit()
    return result(200)

@user_bp.route("/api/self/address", methods=["GET"])
def self_address():
    """获取用户地址列表"""
    addresses = Address.query.filter_by(user_id=session['_id']).all()
    data = [dict(a.__dict__, _sa_instance_state=None) for a in addresses]
    return result(200, {"address": data})

@user_bp.route("/api/address/delete", methods=["DELETE"])
def address_delete():
    data = request.get_json() or request.form  # 支持 JSON 或 form 数据
    print(f"Received delete data: {data}")  # 添加日志
    try:
        _id = data.get("id")
        if not _id:
            return jsonify({"code": 400, "info": "缺少地址ID"}), 400
        Address.query.filter_by(_id=_id).delete()
        db.session.commit()
        return result(200)
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 500, "info": "服务器错误", "error": str(e)}), 500

@user_bp.route("/api/self/address/add", methods=["POST"])
def self_address_add():
    """添加用户地址"""
    sId = session.get('_id')
    if not sId:
        return result(203, {"info": "未登录"})
    # 支持 JSON 或 form 数据
    data = request.get_json() or request.form
    try:
        required_fields = ["province", "town", "county", "detail"]
        data_dict = {k: data.get(k) for k in required_fields}
        if not all(data_dict.values()):
            return jsonify({"code": 400, "info": "请填写完整的地址信息"})
        data_dict["user_id"] = sId
        db.session.add(Address(**data_dict))
        db.session.commit()
        return result(200)
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 500, "info": "服务器错误", "error": str(e)})

@user_bp.route("/api/address/add", methods=["POST"])
def address_add():
    data = request.get_json() or request.form  # 支持 JSON 或 form 数据
    print(f"Received address data: {data}")  # 添加日志
    try:
        required_fields = ["province", "town", "county", "detail"]
        data_dict = {k: data.get(k) for k in required_fields}
        if not all(data_dict.values()):  # 检查是否所有字段都有值
            return jsonify({"code": 400, "info": "请填写完整的地址信息"}), 400
        db.session.add(Address(**data_dict))
        db.session.commit()
        return result(200)
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 500, "info": "服务器错误", "error": str(e)}), 500

@user_bp.route("/api/address", methods=["GET"])
def address():
    """获取无用户绑定的地址列表"""
    addresses = Address.query.filter_by(user_id=None).all()
    data = {"data": [dict(a.__dict__, _sa_instance_state=None) for a in addresses]}
    return result(200, data)

@user_bp.route("/api/balance", methods=["POST"])
def balance():
    """充值余额"""
    sId = session.get("_id")
    if not sId:
        return jsonify({"code": 203, "info": "未登录"})
    data = request.form
    try:
        recharge_amount = float(data["balance"])
        if recharge_amount <= 0:
            return jsonify({"code": 400, "info": "充值金额必须大于0"})
        user = User.query.get(sId)
        user.balance = (user.balance or 0) + recharge_amount
        db.session.commit()
        return jsonify({"code": 200})
    except ValueError:
        return jsonify({"code": 400, "info": "无效的金额格式"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 500, "info": "充值失败", "error": str(e)})

@user_bp.route("/api/self/court", methods=["GET"])
def self_court():
    """获取用户购物车"""
    sId = session.get("_id")
    if not sId:
        return jsonify({"code": 203, "info": "未登录"})
    court = Court.query.filter_by(user_id=sId).first()
    if not court or court.number == 0:
        return jsonify({"code": 200, "data": {"data": []}})
    goods = court.goods.all()
    data = {"data": []}
    for good in goods:
        court_item = db.session.query(goodsCourt).filter_by(court_id=court._id, goods_id=good._id).first()
        quantity = court_item.quantity if court_item else 1
        data["data"].append({
            "_id": good._id,
            "name": good.name,
            "originPrice": float(good.originPrice or 0),
            "sellPrice": float(good.sellPrice or 0),
            "image": json.loads(good.images)[0] if good.images and json.loads(good.images) else "https://via.placeholder.com/150",
            "lookTimes": good.lookTimes,
            "likeTimes": good.likeTimes,
            "buyTimes": good.buyTimes,
            "quantity": quantity,
            "contains": good.contains
        })
    return jsonify({"code": 200, "data": data})

@user_bp.route("/api/update/court", methods=["POST"])
def update_court():
    """更新购物车商品数量"""
    sId = session.get("_id")
    user = User.query.get(sId)
    if not user:
        return jsonify({"code": 201, "info": "用户不存在"})
    data = request.get_json()
    goodsId = data.get("goodsId")
    quantity = int(data.get("quantity", 1))
    court = Court.query.filter_by(user_id=sId).first()
    if not court:
        return jsonify({"code": 202, "info": "购物车不存在"})
    result = db.session.query(goodsCourt).filter_by(court_id=court._id, goods_id=goodsId).first()
    if not result:
        return jsonify({"code": 202, "info": "商品不在购物车中"})
    good = Goods.query.get(goodsId)
    if not good or quantity < 1 or quantity > good.contains:
        return jsonify({"code": 202, "info": "商品不存在或数量超出限制", "oldQuantity": result.quantity})
    try:
        db.session.execute(goodsCourt.update().where(goodsCourt.c.court_id == court._id).where(goodsCourt.c.goods_id == goodsId).values(quantity=quantity))
        good.contains -= (quantity - result.quantity)
        db.session.commit()
        return jsonify({"code": 200, "info": "数量更新成功"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 500, "info": "服务器错误", "error": str(e)})