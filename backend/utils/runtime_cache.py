"""统一运行时存储适配层。

设计目标：同一份业务代码在 local/testing（无 Redis）与 production（有 Redis）都能运行。
  - 生产：底层用 Redis（REDIS_URL）
  - 本地：底层用进程内字典（按 CACHE_TYPE 是否 RedisCache 自动判定）
对外暴露的方法刻意对齐 redis-py 的常用签名（返回 bytes），
使原先用 Redis 的模块只需把 get_redis_client() 换成本模块的 get_store() 即可。
"""
import threading
import fnmatch
from flask import current_app

_lock = threading.RLock()
_memory = {}          # key -> value（str/int）
_memory_sets = {}     # key -> set(str)


class _MemoryStore:
    """进程内存储，接口对齐 redis-py 常用方法。"""

    def get(self, key):
        with _lock:
            v = _memory.get(key)
            return None if v is None else str(v).encode('utf-8')

    def set(self, key, value, ex=None):
        with _lock:
            _memory[key] = value
        return True

    def setex(self, key, seconds, value):
        return self.set(key, value, ex=seconds)

    def delete(self, key):
        with _lock:
            existed = key in _memory or key in _memory_sets
            _memory.pop(key, None)
            _memory_sets.pop(key, None)
            return 1 if existed else 0

    def incr(self, key):
        with _lock:
            try:
                v = int(_memory.get(key, 0)) + 1
            except (ValueError, TypeError):
                v = 1
            _memory[key] = v
            return v

    def sadd(self, key, member):
        with _lock:
            s = _memory_sets.setdefault(key, set())
            added = member not in s
            s.add(member)
            return 1 if added else 0

    def srem(self, key, member):
        with _lock:
            s = _memory_sets.get(key, set())
            if member not in s:
                return 0
            s.discard(member)
            return 1

    def sismember(self, key, member):
        with _lock:
            return member in _memory_sets.get(key, set())

    def scan_iter(self, pattern='*'):
        with _lock:
            keys = list(_memory.keys()) + list(_memory_sets.keys())
        for k in keys:
            if fnmatch.fnmatch(k, pattern):
                yield k.encode('utf-8')

    def keys(self, pattern='*'):
        return list(self.scan_iter(pattern))


class _RedisAdapter:
    """薄封装，保持与 _MemoryStore 一致的方法集合。"""

    def __init__(self, client):
        self._r = client

    def get(self, key):
        return self._r.get(key)

    def set(self, key, value, ex=None):
        return self._r.set(key, value, ex=ex)

    def setex(self, key, seconds, value):
        return self._r.setex(key, seconds, value)

    def delete(self, key):
        return self._r.delete(key)

    def incr(self, key):
        return self._r.incr(key)

    def sadd(self, key, member):
        return self._r.sadd(key, member)

    def srem(self, key, member):
        return self._r.srem(key, member)

    def sismember(self, key, member):
        return self._r.sismember(key, member)

    def scan_iter(self, pattern='*'):
        return self._r.scan_iter(match=pattern)

    def keys(self, pattern='*'):
        return self._r.keys(pattern)


def get_store():
    """按运行模式返回统一存储：生产用 Redis，本地用内存。"""
    cache_type = current_app.config.get('CACHE_TYPE', 'SimpleCache')
    if cache_type == 'RedisCache':
        try:
            import redis
            url = current_app.config.get('REDIS_URL', 'redis://localhost:6379/0')
            return _RedisAdapter(redis.Redis.from_url(url))
        except Exception:
            # Redis 连接失败时降级到内存，保证接口不崩
            return _MemoryStore()
    return _MemoryStore()
