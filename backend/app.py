from flask import Flask, jsonify, render_template
from flask_cors import CORS
from backend.config import get_config
from backend.routes import register_blueprints  # 假设 routes/__init__.py 已定义
from datetime import datetime
from backend.models import db
from backend.extensions import cache


def create_app(config_class=None):
    app = Flask(__name__)
    # 未显式传入时，按环境变量 CAMPUS_CONFIG 选择配置（development/testing/production）
    config_class = config_class or get_config()
    if config_class.__name__ == 'ProductionConfig':
        config_class.validate()
    app.config.from_object(config_class)

    # 关闭严格斜杠重定向：/api/products 与 /api/products/ 都能直达。
    # 308 重定向会让浏览器/axios 丢失 Authorization 头，表现为"点击按钮就跳登录页"。
    app.url_map.strict_slashes = False

    # 初始化扩展
    db.init_app(app)
    CORS(app)
    cache.init_app(app)

    # 分类日志：logs/{app,access,error,security}.log，按天滚动
    from backend.utils.logging_config import install_request_logging
    install_request_logging(app)

    # 注册蓝图
    register_blueprints(app)

    # 创建所有数据库表 + 旧库平滑迁移 + 本地演示种子数据
    with app.app_context():
        try:
            db.create_all()
            from backend.bootstrap import ensure_columns, seed_demo_data
            ensure_columns(app, db)
            if app.config.get('SEED_DEMO_DATA'):
                seed_demo_data(app, db)
        except Exception as e:
            print(f"数据库初始化失败: {e}")

    # 定义端点中文描述
    endpoint_descriptions = {
        # 认证相关 (/api/auth)
        '/api/auth/captcha': '获取验证码（邮箱或短信）',
        '/api/auth/register': '用户注册',
        '/api/auth/login': '用户登录',
        '/api/auth/admin/register': '管理员注册',
        '/api/auth/admin/login': '管理员登录',
        '/api/auth/profile': '获取用户信息（需要令牌）',
        '/api/auth/profile/<method:PUT>': '更新用户信息（需要令牌）',
        '/api/auth/profile/id-card': '切换身份证号显示模式（需要令牌）',
        '/api/auth/dev/captchas': '查看测试验证码台账（仅 dev 模式，生产模式 404）',

        # 管理员相关 (/api/admin)
        '/api/admin/users': '获取用户列表（支持分页和搜索）',
        '/api/admin/users/<int:user_id>': '获取用户详情',
        '/api/admin/users/<int:user_id>/ban': '封禁/解封用户',
        '/api/admin/users/<int:user_id>/<method:DELETE>': '删除用户（软删除）',
        '/api/admin/products/pending': '获取待审核商品列表',
        '/api/admin/products/batch/status': '批量更新商品状态',
        '/api/admin/users/<int:user_id>/orders': '获取用户订单列表',
        '/api/admin/users/<int:user_id>/reset_password': '重置用户密码',
        '/api/admin/users/<int:user_id>/<method:PUT>': '修改用户信息',

        # 用户相关 (/api/users)
        '/api/users/profile': '获取个人资料（需要登录）',
        '/api/users/profile/<method:PUT>': '更新个人资料（需要登录）',
        '/api/users/password': '修改密码（需要登录）',

        # 商品相关 (/api/products)
        '/api/products': '获取商品列表（支持分页、排序和搜索）',
        '/api/products/<int:product_id>': '获取商品详情',
        '/api/products/<method:POST>': '创建商品（需要登录）',
        '/api/products/<int:product_id>/<method:PUT>': '更新商品信息（需要登录）',
        '/api/products/<int:product_id>/images': '上传商品图片（需要登录）',
        '/api/products/<int:product_id>/<method:DELETE>': '删除商品（软删除，需要登录）',
        '/api/products/<int:product_id>/status': '更新商品状态（需要管理员权限）',
        '/api/products/recommended': '获取推荐商品（需要登录）',
        '/api/products/hot': '获取热门商品',

        # 购物车相关 (/api/carts)
        '/api/carts/cart': '获取购物车商品列表（需要登录）',
        '/api/carts/cart/<method:POST>': '添加商品到购物车（需要登录）',
        '/api/carts/<int:cart_id>': '更新购物车商品数量（需要登录）',
        '/api/carts/<int:cart_id>/<method:DELETE>': '从购物车中删除商品（软删除，需要登录）',
        '/api/carts/batch': '批量删除购物车商品（需要登录）',

        # 订单相关 (/api/orders)
        '/api/orders': '获取订单列表（支持分页和状态筛选，需要登录）',
        '/api/orders/<int:order_id>': '获取订单详情（需要登录）',
        '/api/orders/<method:POST>': '创建订单（需要登录）',
        '/api/orders/<int:order_id>/status': '更新订单状态（需要登录）',
        '/api/orders/<int:order_id>/<method:DELETE>': '删除订单（软删除，需要登录）',
        '/api/orders/admin/orders': '管理员获取所有订单列表（需要管理员权限）',
        '/api/orders/admin/orders/<int:order_id>/ship': '管理员发货（需要管理员权限）',

        # 地址相关 (/api/addresses)
        '/api/addresses/': '获取用户的所有地址（需要令牌）',
        '/api/addresses/<method:POST>': '创建新地址（需要令牌）',
        '/api/addresses/<int:address_id>': '更新地址信息（需要令牌）',
        '/api/addresses/<int:address_id>/<method:DELETE>': '删除地址（需要令牌）',
        '/api/addresses/default': '获取默认地址（需要令牌）',
        '/api/addresses/set-default/<int:address_id>': '设置默认地址（需要令牌）',
        '/api/addresses/regions': '获取省市区数据',

        # 标签相关 (/api/tags)
        '/api/tags': '获取标签列表（支持分页和搜索）',
        '/api/tags/<int:tag_id>': '获取标签详情',
        '/api/tags/<method:POST>': '创建标签（需要管理员权限）',
        '/api/tags/<int:tag_id>/<method:PUT>': '更新标签（需要管理员权限）',
        '/api/tags/<int:tag_id>/<method:DELETE>': '删除标签（软删除，需要管理员权限）',

        # 评论相关 (/api/comments)
        '/api/comments/product/<int:product_id>': '获取商品的所有评论',
        '/api/comments/': '创建新评论（需要令牌）',
        '/api/comments/<int:comment_id>/like': '点赞评论（需要令牌）',
        '/api/comments/<int:comment_id>/unlike': '取消点赞评论（需要令牌）',
        '/api/comments/<int:comment_id>/<method:PUT>': '更新评论（需要令牌，仅限作者或管理员）',
        '/api/comments/<int:comment_id>/<method:DELETE>': '删除评论（需要令牌，仅限作者或管理员）',

        # 余额相关 (/api/balances)
        '/api/balances/': '获取当前用户的余额信息（需要令牌）',
        '/api/balances/recharge': '充值余额（需要令牌）',
        '/api/balances/pay': '从余额中支付（需要令牌）',
        '/api/balances/refund': '退款到余额（需要令牌）',
        '/api/balances/records': '获取余额变动记录（需要令牌）',

        # 消息相关 (/api/messages)
        '/api/messages': '获取消息列表（支持分页和类型筛选，需要令牌）',
        '/api/messages/unread_count': '获取未读消息数量（需要令牌）',
        '/api/messages/<int:message_id>/read': '标记消息为已读（需要令牌）',
        '/api/messages/read_all': '标记所有消息为已读（需要令牌）',
        '/api/messages/<int:message_id>/<method:DELETE>': '删除消息（软删除，需要令牌）',
        '/api/messages/batch': '批量删除消息（需要令牌）',

        # 健康检查
        '/api/health': '检查服务健康状态'
    }

    # 添加根路径路由，返回动态生成的 API 概览页面
    @app.route('/')
    def index():
        # 动态获取所有端点
        endpoints = []
        for rule in app.url_map.iter_rules():
            if rule.endpoint != 'static':  # 排除静态文件路由
                methods = sorted(rule.methods - {'HEAD', 'OPTIONS'})  # 排除 HEAD 和 OPTIONS
                for method in methods:
                    endpoint_key = f"{rule.rule}/<method:{method}>"
                    endpoint_display = f"{method} {rule.rule}"
                    description = endpoint_descriptions.get(endpoint_key,
                                                            endpoint_descriptions.get(rule.rule, '未提供描述'))
                    endpoints.append({
                        'method': method,
                        'path': rule.rule,
                        'display': endpoint_display,
                        'description': description
                    })
        # 按路径排序
        endpoints.sort(key=lambda x: (x['path'], x['method']))
        return render_template('index.html', current_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                               captcha_mode=app.config.get('CAPTCHA_MODE', 'dev'),
                               endpoints=endpoints)

    # 测试模式验证码展示页：把后端生成的验证码直接显示在网页上
    @app.route('/dev/captchas')
    def dev_captchas_page():
        if app.config.get('CAPTCHA_MODE', 'dev') == 'prod':
            return '生产模式不提供验证码展示页面', 404
        from backend.utils.auth_helper import list_dev_captchas
        items = list_dev_captchas()
        for item in items:
            item['created_at_text'] = datetime.fromtimestamp(
                item['created_at']).strftime('%H:%M:%S')
        return render_template(
            'dev_captchas.html',
            current_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            items=items)

    # 处理 favicon.ico 请求，避免 404
    @app.route('/favicon.ico')
    def favicon():
        return '', 204

    return app


app = create_app()


@app.route('/api/health')
def health_check():
    return jsonify({'status': 'ok', 'message': '服务正常运行'})


if __name__ == '__main__':
    # debug 由所选配置类的 DEBUG 决定，不再硬编码为 True
    app.run(host='0.0.0.0', port=5000)