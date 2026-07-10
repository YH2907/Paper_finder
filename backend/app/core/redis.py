"""Redis 连接配置

开发环境如果没有 Redis，使用内存缓存替代
"""
import os
import json
from typing import Optional

# Redis URL
REDIS_URL = os.getenv("REDIS_URL", "")

# Redis 客户端（延迟初始化）
_redis_client = None
_memory_cache: dict = {}


def get_redis():
    """获取 Redis 客户端"""
    global _redis_client
    
    if not REDIS_URL:
        return None
    
    if _redis_client is None:
        try:
            import redis
            _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
            _redis_client.ping()
        except Exception:
            _redis_client = None
    
    return _redis_client


async def cache_get(key: str) -> Optional[str]:
    """获取缓存值"""
    redis_client = get_redis()
    
    if redis_client:
        try:
            return redis_client.get(key)
        except Exception:
            pass
    
    # 内存缓存回退
    return _memory_cache.get(key)


async def cache_set(key: str, value: str, expire: int = 3600):
    """设置缓存值"""
    redis_client = get_redis()
    
    if redis_client:
        try:
            redis_client.setex(key, expire, value)
            return
        except Exception:
            pass
    
    # 内存缓存回退
    _memory_cache[key] = value


async def cache_delete(key: str):
    """删除缓存"""
    redis_client = get_redis()
    
    if redis_client:
        try:
            redis_client.delete(key)
        except Exception:
            pass
    
    _memory_cache.pop(key, None)


async def cache_get_json(key: str) -> Optional[dict]:
    """获取 JSON 缓存"""
    value = await cache_get(key)
    if value:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
    return None


async def cache_set_json(key: str, value: dict, expire: int = 3600):
    """设置 JSON 缓存"""
    await cache_set(key, json.dumps(value, ensure_ascii=False), expire)
