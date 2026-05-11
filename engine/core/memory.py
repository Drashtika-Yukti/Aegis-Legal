import json
import redis.asyncio as redis
from typing import Dict, List

from core.logger import get_logger
from core.config import settings

logger = get_logger("MemoryService")

class AegisMemory:
    """Redis-backed memory layer for chat history and caching."""
    def __init__(self):
        self.redis = None
        if settings.REDIS_URL:
            try:
                self.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
                logger.info("Memory initialized with Redis.")
            except Exception as e:
                logger.error(f"Redis Connection Failed: {e}")
        else:
            logger.info("Memory initialized in Standalone mode (No Redis).")

    async def add_message(self, session_id: str, user_id: str, role: str, content: str):

        # 2. Update Redis Cache (Chat History)
        if self.redis:
            try:
                key = f"chat_history:{session_id}"
                message = json.dumps({"role": role, "content": content})
                await self.redis.lpush(key, message)
                await self.redis.ltrim(key, 0, 9) # Keep last 10 messages
            except Exception as e:
                logger.error(f"Redis Cache Error: {e}")

    async def get_history(self, session_id: str, user_id: str, k: int = 10) -> List[Dict]:
        # 1. Try Redis First
        if self.redis:
            try:
                key = f"chat_history:{session_id}"
                history = await self.redis.lrange(key, 0, k-1)
                if history:
                    # Redis stores them in reverse order due to LPUSH
                    return [json.loads(m) for m in reversed(history)]
            except Exception as e:
                logger.error(f"Redis History Fetch Error: {e}")

        return []

    async def get_cache(self, key: str):
        if self.redis:
            try:
                return await self.redis.get(f"cache:{key}")
            except Exception as e:
                logger.error(f"Redis Get Cache Error: {e}")
        return None

    async def set_cache(self, key: str, value: str, expire: int = 3600):
        if self.redis:
            try:
                await self.redis.set(f"cache:{key}", value, ex=expire)
            except Exception as e:
                logger.error(f"Redis Set Cache Error: {e}")

    async def save_fact(self, user_id: str, fact: str):
        try:
            await db.store_facts(user_id, [fact])
        except Exception as e:
            logger.error(f"Local Fact Save Error: {e}")

memory = AegisMemory()
