"""认证路由：验证码、注册、登录、管理员注册/登录、个人资料。

安全设计（测试/生产分离）：
- 验证码：dev 模式生成后打印到后端控制台并随接口回显 dev_code 便于测试；
  prod 模式经预留短信网关发送、不回显。两种模式注册都强制校验。
- 管理员注册：默认关闭；生产环境需显式开启并提供邀请码；本地环境可开启用于测试。
"""
from flask import Blueprint, request, jsonify, current_app
import jwt
import time
from ..models import db, User, Balance, Admin
from ..utils.decorators import token_required
from ..extensions import cache as shared_cache
from ..utils.auth_helper import (
    generate_verification_code, save_verification_code, verify_code,
    record_dev_captcha, list_dev_captchas
)
import uuid
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
import logging

auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)


def json_response(success, message, data=None, status=200):
    return jsonify({'success': success, 'message': message, 'data': data}), status


def get_cipher_suite():
    return Fernet(current_app.config['ENCRYPTION_KEY'])


def encrypt_data(data):
    if not data:
        return None
    return get_cipher_suite().encrypt(data.encode()).decode()


def decrypt_data(encrypted_data):
    if not encrypted_data:
        return None
    return get_cipher_suite().decrypt(encrypted_data.encode()).decode()


def is_dev_mode():
    return current_app.config.get('CAPTCHA_MODE', 'dev') != 'prod'


def send_sms_code(phone, code):
    """预留短信发送接口（生产模式接入真实网关前不实际发送）。

    接入点：在此函数内调用短信服务商 SDK。返回 True 表示发送成功。
    未配置网关时返回 False，注册接口据此给出明确提示，避免静默放行。
    """
    if current_app.config.get('SMS_GATEWAY_ENABLED'):
        # TODO: 接入真实短信网关，例如：
        #   return sms_client.send(phone, f'您的验证码是 {code}')
        logger.warning('短信网关已标记启用，但尚未接入真实 SDK')
        return False
    logger.warning('生产模式未启用短信网关，验证码不会真实发送')
    return False


@auth_bp.route('/captcha', methods=['POST'])
def get_captcha():
    """获取验证码（测试模式回显 dev_code；生产模式走短信网关）。"""
    data = request.get_json()
    if not data or ('phone' not in data and 'email' not in data):
        return json_response(False, '请提供手机号或邮箱', status=400)

    key = data.get('phone') or data.get('email')
    if not isinstance(key, str) or not key.strip():
        return json_response(False, '手机号或邮箱格式错误', status=400)

    captcha = generate_verification_code()
    save_verification_code(key, captcha)
    expire = current_app.config.get('CAPTCHA_EXPIRE_MINUTES', 5)

    if is_dev_mode():
        # 测试模式额外登记到后端网页台账，可在 /dev/captchas 直接查看
        record_dev_captcha(key, captcha, expire * 60)

    # 始终在后端控制台清晰打印（便于开发调试与测试）
    print('\n' + '=' * 56)
    print(f'[验证码] 接收者: {key}')
    print(f'[验证码] 内容: {captcha}（有效期 {expire} 分钟）')
    print(f'[验证码] 模式: {"dev(测试)" if is_dev_mode() else "prod(生产)"}')
    print('=' * 56 + '\n')
    logger.info(f'验证码已生成: {key}')

    resp = {'expire_seconds': expire * 60}
    if is_dev_mode():
        # 测试模式：回显验证码，便于自动化/手工测试填写
        resp['dev_code'] = captcha
        return json_response(True, '验证码已生成（测试模式，见后端控制台）', resp)

    # 生产模式：经预留网关发送，不回显
    sent = send_sms_code(key, captcha)
    if not sent:
        return json_response(False, '验证码发送服务尚未配置，请联系管理员', status=503)
    return json_response(True, '验证码已发送，请注意查收', resp)


@auth_bp.route('/dev/captchas', methods=['GET'])
def dev_captchas():
    """测试模式后端验证码台账（仅 dev 模式可见，生产模式直接 404）。"""
    if not is_dev_mode():
        return json_response(False, '生产模式不提供验证码展示', status=404)
    items = list_dev_captchas()
    for item in items:
        item['created_at_text'] = time.strftime(
            '%H:%M:%S', time.localtime(item['created_at']))
        item.pop('created_at', None)
        item.pop('expire_at', None)
    return json_response(True, '获取测试验证码成功', {'items': items})


@auth_bp.route('/register', methods=['POST'])
def register():
    """用户注册（强制校验验证码）。"""
    data = request.get_json()
    required_fields = ['nickname', 'phone', 'password', 'captcha']
    if not data or not all(field in data for field in required_fields):
        return json_response(False, f'缺少必填字段: {", ".join(required_fields)}', status=400)

    # 强制校验验证码（一次性、限时）
    if not verify_code(data['phone'], data['captcha']):
        return json_response(False, '验证码错误或已过期', status=400)

    if User.query.filter_by(phone=data['phone']).first():
        return json_response(False, '该手机号已注册', status=400)
    if data.get('email') and User.query.filter_by(email=data['email']).first():
        return json_response(False, '该邮箱已注册', status=400)

    quick_id = f'U{uuid.uuid4().hex[:8].upper()}'
    new_user = User(
        quick_id=quick_id,
        nickname=data['nickname'],
        phone=data['phone'],
        password=data['password'],
        email=data.get('email'),
        avatar_url=data.get('avatar_url'),
        register_time=datetime.utcnow()
    )
    try:
        db.session.add(new_user)
        db.session.commit()
        db.session.add(Balance(user_id=new_user.id, amount=0.0))
        db.session.commit()
        logger.info(f'用户注册成功: {new_user.id}')
        return json_response(True, '注册成功', {
            'user_id': new_user.id, 'quick_id': new_user.quick_id, 'nickname': new_user.nickname
        }, 201)
    except Exception as e:
        db.session.rollback()
        logger.error(f'注册失败: {str(e)}')
        return json_response(False, f'注册失败: {str(e)}', status=500)


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or 'phone' not in data or 'password' not in data:
        return json_response(False, '请提供手机号和密码', status=400)

    user = User.query.filter_by(phone=data['phone'], is_deleted=False).first()
    if not user or not user.verify_password(data['password']):
        return json_response(False, '手机号或密码错误', status=401)
    if user.is_banned:
        return json_response(False, '账号已被封禁，请联系管理员', status=403)

    user.last_login_time = datetime.utcnow()
    try:
        db.session.commit()
        token = jwt.encode(
            {'user_id': user.id, 'type': 'user', 'exp': datetime.utcnow() + timedelta(hours=1)},
            current_app.config['JWT_SECRET_KEY'], algorithm='HS256'
        )
        return json_response(True, '登录成功', {'token': token, 'user': user.to_dict()})
    except Exception as e:
        db.session.rollback()
        logger.error(f'登录失败: {str(e)}')
        return json_response(False, f'登录失败: {str(e)}', status=500)


@auth_bp.route('/admin/register', methods=['POST'])
def admin_register():
    """管理员注册（受安全开关与邀请码保护）。"""
    # 安全闸：默认关闭，需显式开启
    if not current_app.config.get('ADMIN_REGISTRATION_ENABLED'):
        return json_response(False, '管理员注册已关闭，请联系系统管理员', status=403)

    data = request.get_json()
    required_fields = ['username', 'password', 'email']
    if not data or not all(field in data for field in required_fields):
        return json_response(False, f'缺少必填字段: {", ".join(required_fields)}', status=400)

    # 生产模式额外要求邀请码
    if not is_dev_mode():
        invite = current_app.config.get('ADMIN_REGISTER_INVITE_CODE', '')
        if not invite or data.get('invite_code') != invite:
            return json_response(False, '邀请码错误或未提供', status=403)

    if Admin.query.filter_by(username=data['username']).first():
        return json_response(False, '该用户名已存在', status=400)
    if Admin.query.filter_by(email=data['email']).first():
        return json_response(False, '该邮箱已注册', status=400)

    new_admin = Admin(
        username=data['username'], password=data['password'], email=data['email'],
        permission_level=data.get('permission_level', '普通')
    )
    try:
        db.session.add(new_admin)
        db.session.commit()
        return json_response(True, '管理员注册成功', {
            'admin_id': new_admin.id, 'username': new_admin.username
        }, 201)
    except Exception as e:
        db.session.rollback()
        logger.error(f'管理员注册失败: {str(e)}')
        return json_response(False, f'注册失败: {str(e)}', status=500)


ADMIN_LOGIN_FAIL_PREFIX = 'admin_login_fail:'


def _admin_login_state(username):
    state = shared_cache.get(ADMIN_LOGIN_FAIL_PREFIX + username)
    return state if isinstance(state, dict) else {'count': 0, 'locked_until': 0}


def _save_admin_login_state(username, state):
    lock_minutes = current_app.config.get('ADMIN_LOGIN_LOCK_MINUTES', 15)
    shared_cache.set(ADMIN_LOGIN_FAIL_PREFIX + username, state,
                     timeout=int(lock_minutes * 60) + 60)


@auth_bp.route('/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return json_response(False, '请提供用户名和密码', status=400)

    username = data['username']
    state = _admin_login_state(username)
    now = time.time()
    if state.get('locked_until', 0) > now:
        retry = int(state['locked_until'] - now)
        return json_response(False, f'登录失败次数过多，请在 {retry} 秒后重试', status=429)

    admin = Admin.query.filter_by(username=username).first()
    if not admin or not admin.verify_password(data['password']):
        max_attempts = current_app.config.get('ADMIN_LOGIN_MAX_ATTEMPTS', 5)
        lock_minutes = current_app.config.get('ADMIN_LOGIN_LOCK_MINUTES', 15)
        state['count'] = int(state.get('count', 0)) + 1
        if state['count'] >= max_attempts:
            state['count'] = max_attempts
            state['locked_until'] = now + lock_minutes * 60
            _save_admin_login_state(username, state)
            logger.warning(f'管理员登录触发锁定: username={username}')
            return json_response(
                False, f'连续登录失败 {max_attempts} 次，账号已锁定 {lock_minutes} 分钟',
                status=429)
        _save_admin_login_state(username, state)
        return json_response(
            False, f'用户名或密码错误，还可尝试 {max_attempts - state["count"]} 次',
            status=401)

    # 登录成功即清零失败计数
    shared_cache.delete(ADMIN_LOGIN_FAIL_PREFIX + username)
    admin.last_login_at = datetime.utcnow()
    admin.login_count += 1
    try:
        db.session.commit()
        token = jwt.encode(
            {'admin_id': admin.id, 'type': 'admin', 'permission_level': admin.permission_level},
            current_app.config['JWT_SECRET_KEY'], algorithm='HS256'
        )
        return json_response(True, '登录成功', {'token': token, 'admin': admin.to_dict()})
    except Exception as e:
        db.session.rollback()
        logger.error(f'管理员登录失败: {str(e)}')
        return json_response(False, f'登录失败: {str(e)}', status=500)


def mask_id_card(id_card):
    if not id_card:
        return None
    return id_card[:6] + '*' * 8 + id_card[-4:]


@auth_bp.route('/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    return json_response(True, '获取用户信息成功', current_user.to_dict(include_sensitive=True))


@auth_bp.route('/profile', methods=['PUT'])
@token_required
def update_profile(current_user):
    data = request.get_json()
    if not data:
        return json_response(False, '请求数据为空', status=400)
    allowed_fields = ['nickname', 'email', 'gender', 'avatar_url']
    update_data = {}
    for field in allowed_fields:
        if field in data:
            update_data[field] = data[field]
    try:
        for field, value in update_data.items():
            setattr(current_user, field, value)
        db.session.commit()
        return json_response(True, '用户信息更新成功', current_user.to_dict(include_sensitive=True))
    except Exception as e:
        db.session.rollback()
        return json_response(False, f'更新失败: {str(e)}', status=500)


@auth_bp.route('/profile/id-card', methods=['GET'])
@token_required
def toggle_id_card_display(current_user):
    user_data = current_user.to_dict(include_sensitive=True)
    if not user_data.get('id_card'):
        return json_response(False, '未设置身份证号', status=400)
    decrypted_id_card = decrypt_data(user_data['id_card'])
    show_full = request.args.get('show_full', 'false').lower() == 'true'
    user_data['id_card'] = decrypted_id_card if show_full else mask_id_card(decrypted_id_card)
    user_data['id_card_full'] = show_full
    return json_response(True, '切换身份证显示成功', user_data)
