from flask import Blueprint, request, session, jsonify
from models.models import db, User, Admin, Court
from utils.utils import result, bcrypt_hash, bcrypt_check, getNowDateTime
from config.settings import WHITE_NAME_LIST
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.before_request
def before():
    """请求前中间件：检查登录状态"""
    url = request.path
    if url in WHITE_NAME_LIST or "static" in url or "/api/goods/detail/" in url:
        return
    _id = session.get("_id")
    if not _id:
        return result(203, {"info": "未登录"})

@auth_bp.route("/api/login", methods=["POST"])
def login():
    # 尝试从 JSON 或 form 中获取数据
    data = request.get_json() or request.form
    account = data.get("account")
    password = data.get("password")
    _type = data.get("type")
    # print(f"Received login data: {data}")  # 添加日志
    if not account or not password:
        return jsonify({"code": 400, "info": "账号或密码不能为空"}), 400
    if _type == "admin":
        admin = Admin.query.filter_by(account=account).first()
        if admin and bcrypt_check(password, admin.password):
            session["_id"] = admin._id
            admin.loginTime = getNowDateTime()
            db.session.commit()
            return jsonify({"code": 200, "_id": str(admin._id)}), 200
        return jsonify({"code": 202 if admin else 201, "info": "密码错误" if admin else "管理员不存在"}), 202 if admin else 201
    else:
        user = User.query.filter_by(account=account).first()
        if user and bcrypt_check(password, user.password):
            session["_id"] = user._id
            user.loginTime = getNowDateTime()
            db.session.commit()
            return jsonify({"code": 200, "_id": str(user._id)}), 200
        return jsonify({"code": 202 if user else 201, "info": "密码错误" if user else "用户不存在"}), 202 if user else 201

@auth_bp.route("/api/islogin", methods=["POST"])
def is_login():
    """检查用户是否已登录"""
    _id = session.get("_id")
    if not _id:
        return jsonify({"code": 203, "info": "未登录"})
    admin = Admin.query.get(_id)
    if admin:
        return jsonify({"code": 200, "data": {"type": "admin"}})
    user = User.query.get(_id)
    if user:
        return jsonify({"code": 200, "data": {"type": "user"}})
    return jsonify({"code": 201, "info": "用户不存在"})

@auth_bp.route("/api/quit", methods=["POST"])
def quit():
    """退出登录"""
    _id = session.get("_id")
    _type = request.form.get("type")
    if _type == "admin":
        admin = Admin.query.get(_id)
        if admin:
            admin.logoutTime = getNowDateTime()
    else:
        user = User.query.get(_id)
        if user:
            user.logoutTime = getNowDateTime()
    if "_id" in session:
        del session["_id"]
    db.session.commit()
    return result(200)

@auth_bp.route("/api/regist", methods=["POST"])
def regist():
    data = request.get_json() or request.form  # 支持 JSON 或 form 数据
    print(f"Received regist data: {data}")  # 添加日志
    user = User(
        account=data.get("account"),
        password=bcrypt_hash(data.get("password")),
        idCard=data.get("idCard"),
        name=data.get("name"),
        birthDate=datetime.strptime(data.get("birthDate"), "%Y-%m-%d") if data.get("birthDate") else None,
        gender=data.get("gender"),
        createTime=getNowDateTime()
    )
    try:
        db.session.add(user)
        db.session.commit()
    except:
        return jsonify({"code": 205, "info": "重复注册"}), 205
    user = User.query.filter_by(account=data["account"]).first()
    db.session.add(Court(user_id=user._id))
    db.session.commit()
    session["_id"] = user._id
    return jsonify({"code": 200, "_id": str(user._id)}), 200

@auth_bp.route("/api/admin/add", methods=["POST"])
def admin_add():
    data = request.get_json() or request.form  # 支持 JSON 或 form 数据
    print(f"Received admin add data: {data}")  # 添加日志
    account = data.get("account")
    password = data.get("password")
    if not account or not password:
        return jsonify({"code": 400, "info": "账号或密码不能为空"}), 400
    password = bcrypt_hash(password)
    name = data.get("name", "Admin")
    level = int(data.get("level", 1))
    if Admin.query.filter_by(account=account).first():
        return jsonify({"code": 205, "info": "该账号已注册"}), 205
    try:
        db.session.add(Admin(account=account, password=password, name=name, level=level, createTime=getNowDateTime()))
        db.session.commit()
        return jsonify({"code": 200, "info": "注册成功"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 500, "info": "服务器错误", "error": str(e)}), 500