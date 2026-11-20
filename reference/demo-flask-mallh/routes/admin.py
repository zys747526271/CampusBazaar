from flask import Blueprint, request, session, jsonify
from models.models import db, User, Admin, Receipt, ReceiptItem, Goods, VipReceipt
from utils.utils import result
from datetime import datetime  # 导入 datetime 用于时间格式处理
from sqlalchemy.exc import SQLAlchemyError
import traceback

admin_bp = Blueprint('admin', __name__)

@admin_bp.route("/api/users", methods=["POST", "GET"])
def get_users():
    """获取用户列表（支持模糊搜索）"""
    sId = session.get("_id")
    if not sId:
        return jsonify({"code": 203, "info": "未登录"})
    if not Admin.query.get(sId):
        return jsonify({"code": 403, "info": "仅管理员可访问"})
    if request.method == "GET":
        try:
            nums = User.query.count()
            return jsonify({"code": 200, "data": {"nums": nums}})
        except SQLAlchemyError as e:
            traceback.print_exc()
            return jsonify({"code": 500, "info": "数据库错误", "error": str(e)})
    if request.method == "POST":
        try:
            start = int(request.form.get("start", 0))
            nums = int(request.form.get("nums", 15))
            search = request.form.get("search", "").strip()
            search_type = request.form.get("search_type", "user")
            query = User.query
            if search:
                if search_type == "user":
                    query = query.filter(db.or_(User.name.ilike(f"%{search}%"), User.account.ilike(f"%{search}%")))
                elif search_type == "order":
                    receipts = Receipt.query.filter(Receipt.orderNum.ilike(f"%{search}%")).all()
                    user_ids = [r.user_id for r in receipts]
                    query = query.filter(User._id.in_(user_ids))
                elif search_type == "goods":
                    goods = Goods.query.filter(Goods.name.ilike(f"%{search}%")).all()
                    goods_ids = [g._id for g in goods]
                    receipt_items = ReceiptItem.query.filter(ReceiptItem.goodsId.in_(goods_ids)).all()
                    receipt_ids = [ri._id for ri in receipt_items]
                    receipts = Receipt.query.filter(Receipt.itemId.contains(str(receipt_ids))).all()
                    user_ids = [r.user_id for r in receipts]
                    query = query.filter(User._id.in_(user_ids))
            users = query.order_by(User.createTime.desc()).offset(start).limit(nums).all()
            data = {"data": [], "search": search, "search_type": search_type}
            for user in users:
                user_dict = dict(user.__dict__, _sa_instance_state=None)
                for key, value in user_dict.items():
                    if isinstance(value, datetime):
                        user_dict[key] = value.strftime("%Y-%m-%d %H:%M:%S")
                user_dict["banned"] = user.banned if hasattr(user, "banned") else False
                data["data"].append(user_dict)
            return jsonify({"code": 200, "data": data})
        except SQLAlchemyError as e:
            db.session.rollback()
            traceback.print_exc()
            return jsonify({"code": 500, "info": "数据库错误", "error": str(e)})
        except Exception as e:
            db.session.rollback()
            traceback.print_exc()
            return jsonify({"code": 502, "info": "服务端错误", "error": str(e)})

@admin_bp.route("/api/user/ban", methods=["POST"])
def ban_user():
    """封禁或解封用户"""
    sId = session.get("_id")
    if not sId or not Admin.query.get(sId):
        return jsonify({"code": 403, "info": "仅管理员可操作"})
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        is_banned = data.get("is_banned")
        user = User.query.get(user_id)
        if not user:
            return jsonify({"code": 404, "info": "用户不存在"})
        user.banned = is_banned
        db.session.commit()
        action = "封禁" if is_banned else "解封"
        return jsonify({"code": 200, "info": f"用户已{action}"})
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"code": 500, "info": "操作失败", "error": str(e)})

@admin_bp.route("/api/admin/receipt/<int:start>/<int:nums>", methods=["POST", "GET"])
def admin_receipt(start, nums):
    """管理员获取订单列表"""
    if request.method == "GET":
        nums = Receipt.query.count()
        return result(200, {"nums": nums})
    if request.method == "POST":
        receipts = Receipt.query.offset(start).limit(nums).all()
        data = {"data": []}
        for receipt in receipts:
            goodsIdList = receipt.get_goods_id_list()
            dic = dict(receipt.__dict__, _sa_instance_state=None)
            dic["goodsList"] = [dict(g.__dict__, _sa_instance_state=None) for g in Goods.query.filter(Goods._id.in_(goodsIdList)).with_entities(Goods.name, Goods.originPrice, Goods.sellPrice).all()]
            data["data"].append(dic)
        return result(200, data)

@admin_bp.route("/api/admin/vipreceipt/<int:start>/<int:nums>", methods=["POST", "GET"])
def admin_vipreceipt(start, nums):
    """管理员获取VIP购买记录"""
    if request.method == "GET":
        nums = VipReceipt.query.count()
        return result(200, {"nums": nums})
    if request.method == "POST":
        receipts = VipReceipt.query.offset(start).limit(nums).all()
        data = {"data": [dict(r.__dict__, _sa_instance_state=None) for r in receipts]}
        return result(200, data)