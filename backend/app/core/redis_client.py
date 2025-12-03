import redis.asyncio as redis
from app.config import settings
from typing import Optional
import json

class RedisClient:
    _instance: Optional[redis.Redis] = None

    @classmethod
    def get_instance(cls) -> redis.Redis:
        if cls._instance is None:
            cls._instance = redis.from_url(
                settings.REDIS_URL, 
                decode_responses=True,
                encoding="utf-8"
            )
        return cls._instance

    @classmethod
    async def close(cls):
        if cls._instance:
            await cls._instance.close()
            cls._instance = None

    @classmethod
    async def set_json(cls, key: str, value: dict, expire: int = None):
        client = cls.get_instance()
        await client.set(key, json.dumps(value), ex=expire)

    @classmethod
    async def get_json(cls, key: str) -> Optional[dict]:
        client = cls.get_instance()
        value = await client.get(key)
        if value:
            return json.loads(value)
        return None

# Global dependency
async def get_redis() -> redis.Redis:
    return RedisClient.get_instance()

