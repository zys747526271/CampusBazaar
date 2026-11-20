import bcrypt
import time
import simplejson as json
from datetime import datetime
import redis
from config.settings import MySQLConfig

# 初始化 Redis 连接池
redis_pool = redis.ConnectionPool(
    host=MySQLConfig.REDIS_HOST,
    port=MySQLConfig.REDIS_PORT,
    password=MySQLConfig.REDIS_PASSWORD,
    db=MySQLConfig.REDIS_DB,
    decode_responses=True
)
redis_client = redis.Redis(connection_pool=redis_pool)

def result(code=200, d=None):
    """统一返回 JSON 格式数据"""
    if d is None:
        d = {}
    data = {'code': code, 'data': d}
    return json.dumps(data, ensure_ascii=False)

def bcrypt_hash(password):
    """生成加盐的哈希密码"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def bcrypt_check(password, hashed):
    """检查密码是否匹配哈希值"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def getNowDateTime():
    """获取当前日期时间字符串"""
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

def getTimeStamp():
    """获取当前时间戳"""
    return time.time()

def getOrderNum():
    """生成毫秒级订单号"""
    return "{:.0f}".format(getTimeStamp() * 1000)

def generate_order_num():
    """生成带日期和序号的订单号"""
    timestamp = int(time.time() * 1000)
    today = datetime.strptime(getNowDateTime(), "%Y-%m-%d %H:%M:%S").date()
    from models.models import Receipt
    order_count = Receipt.query.filter(Receipt.createTime >= today).count() + 1
    return f"{timestamp}{order_count:03d}"

def cache_get(key):
    """从 Redis 缓存中获取数据"""
    cached_data = redis_client.get(key)
    if cached_data:
        return json.loads(cached_data)
    return None

def cache_set(key, data, expire_time=3600):
    """将数据存入 Redis 缓存"""
    redis_client.set(key, json.dumps(data), ex=expire_time)