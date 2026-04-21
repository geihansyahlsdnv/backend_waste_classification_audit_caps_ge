import json
from typing import Optional, Any
import redis.asyncio as redis
import logging

from ..core.config import settings

logger = logging.getLogger(__name__)

class RedisService:
    def __init__(self):
        self.redis = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True
        )
    
    async def get(self, key: str) -> Optional[Any]:
        try:
            value = await self.redis.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            logger.error(f"Redis get error: {str(e)}")
            return None
    
    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        try:
            await self.redis.set(key, json.dumps(value), ex=expire)
            return True
        except Exception as e:
            logger.error(f"Redis set error: {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis delete error: {str(e)}")
            return False
    
    async def invalidate_stats_cache(self):
        try:
            keys = await self.redis.keys("stats:*")
            if keys:
                await self.redis.delete(*keys)
            return True
        except Exception as e:
            logger.error(f"Redis invalidate cache error: {str(e)}")
            return False

redis_service = RedisService()