import redis.asyncio as redis
import redis as redis_sync
from app.config import settings
from typing import Optional
import json
import asyncio
import os

def _is_celery_worker() -> bool:
    """Check if we're running in a Celery worker process"""
    # Check the call stack to see if we're being called from worker.py
    import inspect
    stack = inspect.stack()
    for frame in stack:
        filename = frame.filename
        if 'worker.py' in filename or 'celery' in filename.lower():
            return True
    return False

class RedisClient:
    _instance: Optional[redis.Redis] = None
    _sync_instance: Optional[redis_sync.Redis] = None

    @classmethod
    def get_instance(cls) -> redis.Redis:
        """Get Redis instance - creates new one each time to avoid event loop issues in Celery workers"""
        # Always create a new connection to avoid event loop conflicts in forked Celery workers
        # This is safe because Redis connections are lightweight
        return redis.from_url(
            settings.REDIS_URL, 
            decode_responses=True,
            encoding="utf-8"
        )

    @classmethod
    def get_sync_instance(cls) -> redis_sync.Redis:
        """Get synchronous Redis instance for Celery workers"""
        if cls._sync_instance is None:
            cls._sync_instance = redis_sync.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                encoding="utf-8"
            )
        return cls._sync_instance

    @classmethod
    async def close(cls):
        if cls._instance:
            await cls._instance.close()
            cls._instance = None
        if cls._sync_instance:
            cls._sync_instance.close()
            cls._sync_instance = None

    @classmethod
    async def set_json(cls, key: str, value: dict, expire: int = None):
        # Use sync Redis in Celery workers to avoid event loop issues
        if _is_celery_worker():
            client = cls.get_sync_instance()
            client.set(key, json.dumps(value), ex=expire)
            return
        
        # Use async Redis in FastAPI context
        client = cls.get_instance()
        try:
            await client.set(key, json.dumps(value), ex=expire)
        finally:
            # Always close the connection after use
            await client.aclose()

    @classmethod
    async def get_json(cls, key: str) -> Optional[dict]:
        # Use sync Redis in Celery workers to avoid event loop issues
        if _is_celery_worker():
            client = cls.get_sync_instance()
            value = client.get(key)
            if value:
                return json.loads(value)
            return None
        
        # Use async Redis in FastAPI context
        client = cls.get_instance()
        try:
            value = await client.get(key)
            if value:
                return json.loads(value)
            return None
        finally:
            # Always close the connection after use
            await client.aclose()

# Global dependency
async def get_redis() -> redis.Redis:
    return RedisClient.get_instance()

