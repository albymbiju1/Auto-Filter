"""
Redis service for CineAI Bot
Handles caching, rate limiting, and temporary storage
"""

import json
import logging
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, timedelta

import redis.asyncio as redis
from redis.asyncio import Redis

from app.config import config

logger = logging.getLogger(__name__)


class RedisService:
    """Redis service for caching and temporary storage"""

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.client: Optional[Redis] = None
        self.default_ttl = config.bot_settings.CACHE_TTL

    async def initialize(self):
        """Initialize Redis connection"""
        try:
            self.client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20,
                retry_on_timeout=True
            )

            # Test connection
            await self.client.ping()
            logger.info("Connected to Redis successfully")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def close(self):
        """Close Redis connection"""
        if self.client:
            await self.client.close()
            logger.info("Redis connection closed")

    async def health_check(self) -> bool:
        """Check Redis health"""
        try:
            await self.client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False

    # Basic operations
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a key-value pair"""
        try:
            ttl = ttl or self.default_ttl
            if isinstance(value, (dict, list)):
                value = json.dumps(value)

            await self.client.setex(key, ttl, value)
            return True
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False

    async def get(self, key: str) -> Optional[Any]:
        """Get value by key"""
        try:
            value = await self.client.get(key)
            if value is None:
                return None

            # Try to parse as JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value

        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None

    async def delete(self, *keys: str) -> int:
        """Delete keys"""
        try:
            return await self.client.delete(*keys)
        except Exception as e:
            logger.error(f"Redis DELETE error for keys {keys}: {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            return bool(await self.client.exists(key))
        except Exception as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
            return False

    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration for key"""
        try:
            return bool(await self.client.expire(key, ttl))
        except Exception as e:
            logger.error(f"Redis EXPIRE error for key {key}: {e}")
            return False

    async def ttl(self, key: str) -> int:
        """Get time to live for key"""
        try:
            return await self.client.ttl(key)
        except Exception as e:
            logger.error(f"Redis TTL error for key {key}: {e}")
            return -1

    # Hash operations
    async def hset(self, name: str, mapping: Dict[str, Any], ttl: Optional[int] = None) -> int:
        """Set hash fields"""
        try:
            # Convert values to JSON if needed
            serialized_mapping = {}
            for key, value in mapping.items():
                if isinstance(value, (dict, list)):
                    serialized_mapping[key] = json.dumps(value)
                else:
                    serialized_mapping[key] = str(value)

            result = await self.client.hset(name, mapping=serialized_mapping)

            if ttl:
                await self.client.expire(name, ttl)

            return result
        except Exception as e:
            logger.error(f"Redis HSET error for hash {name}: {e}")
            return 0

    async def hget(self, name: str, key: str) -> Optional[Any]:
        """Get hash field"""
        try:
            value = await self.client.hget(name, key)
            if value is None:
                return None

            # Try to parse as JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value

        except Exception as e:
            logger.error(f"Redis HGET error for hash {name}, field {key}: {e}")
            return None

    async def hgetall(self, name: str) -> Dict[str, Any]:
        """Get all hash fields"""
        try:
            data = await self.client.hgetall(name)
            result = {}

            for key, value in data.items():
                # Try to parse as JSON
                try:
                    result[key] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    result[key] = value

            return result

        except Exception as e:
            logger.error(f"Redis HGETALL error for hash {name}: {e}")
            return {}

    async def hdel(self, name: str, *keys: str) -> int:
        """Delete hash fields"""
        try:
            return await self.client.hdel(name, *keys)
        except Exception as e:
            logger.error(f"Redis HDEL error for hash {name}, keys {keys}: {e}")
            return 0

    # List operations
    async def lpush(self, name: str, *values: Any) -> int:
        """Push values to list head"""
        try:
            serialized_values = []
            for value in values:
                if isinstance(value, (dict, list)):
                    serialized_values.append(json.dumps(value))
                else:
                    serialized_values.append(str(value))

            return await self.client.lpush(name, *serialized_values)
        except Exception as e:
            logger.error(f"Redis LPUSH error for list {name}: {e}")
            return 0

    async def rpush(self, name: str, *values: Any) -> int:
        """Push values to list tail"""
        try:
            serialized_values = []
            for value in values:
                if isinstance(value, (dict, list)):
                    serialized_values.append(json.dumps(value))
                else:
                    serialized_values.append(str(value))

            return await self.client.rpush(name, *serialized_values)
        except Exception as e:
            logger.error(f"Redis RPUSH error for list {name}: {e}")
            return 0

    async def lpop(self, name: str) -> Optional[Any]:
        """Pop value from list head"""
        try:
            value = await self.client.lpop(name)
            if value is None:
                return None

            # Try to parse as JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value

        except Exception as e:
            logger.error(f"Redis LPOP error for list {name}: {e}")
            return None

    async def lrange(self, name: str, start: int = 0, end: int = -1) -> List[Any]:
        """Get list range"""
        try:
            values = await self.client.lrange(name, start, end)
            result = []

            for value in values:
                # Try to parse as JSON
                try:
                    result.append(json.loads(value))
                except (json.JSONDecodeError, TypeError):
                    result.append(value)

            return result

        except Exception as e:
            logger.error(f"Redis LRANGE error for list {name}: {e}")
            return []

    # Set operations
    async def sadd(self, name: str, *values: Any) -> int:
        """Add values to set"""
        try:
            serialized_values = []
            for value in values:
                if isinstance(value, (dict, list)):
                    serialized_values.append(json.dumps(value))
                else:
                    serialized_values.append(str(value))

            return await self.client.sadd(name, *serialized_values)
        except Exception as e:
            logger.error(f"Redis SADD error for set {name}: {e}")
            return 0

    async def srem(self, name: str, *values: Any) -> int:
        """Remove values from set"""
        try:
            serialized_values = []
            for value in values:
                if isinstance(value, (dict, list)):
                    serialized_values.append(json.dumps(value))
                else:
                    serialized_values.append(str(value))

            return await self.client.srem(name, *serialized_values)
        except Exception as e:
            logger.error(f"Redis SREM error for set {name}: {e}")
            return 0

    async def smembers(self, name: str) -> set:
        """Get all set members"""
        try:
            values = await self.client.smembers(name)
            result = set()

            for value in values:
                # Try to parse as JSON
                try:
                    result.add(json.loads(value))
                except (json.JSONDecodeError, TypeError):
                    result.add(value)

            return result

        except Exception as e:
            logger.error(f"Redis SMEMBERS error for set {name}: {e}")
            return set()

    # Rate limiting
    async def check_rate_limit(
        self,
        key: str,
        limit: int,
        window: int
    ) -> tuple[bool, int]:
        """
        Check rate limit using sliding window algorithm
        Returns (allowed, remaining_requests)
        """
        try:
            current_time = int(datetime.utcnow().timestamp())
            window_start = current_time - window

            # Remove old entries
            await self.client.zremrangebyscore(key, 0, window_start)

            # Count current requests
            current_requests = await self.client.zcard(key)

            if current_requests >= limit:
                return False, 0

            # Add current request
            await self.client.zadd(key, {str(current_time): current_time})
            await self.client.expire(key, window)

            remaining = limit - current_requests - 1
            return True, remaining

        except Exception as e:
            logger.error(f"Rate limit check error for key {key}: {e}")
            return True, limit  # Allow on error

    # Cache-specific methods
    async def cache_user_session(self, user_id: int, session_data: Dict[str, Any], ttl: int = 3600):
        """Cache user session"""
        key = f"session:{user_id}"
        await self.hset(key, session_data, ttl)

    async def get_user_session(self, user_id: int) -> Dict[str, Any]:
        """Get user session"""
        key = f"session:{user_id}"
        return await self.hgetall(key)

    async def cache_search_results(self, query: str, results: List[Dict], ttl: int = 1800):
        """Cache search results"""
        key = f"search:{hash(query)}"
        await self.set(key, results, ttl)

    async def get_cached_search_results(self, query: str) -> Optional[List[Dict]]:
        """Get cached search results"""
        key = f"search:{hash(query)}"
        return await self.get(key)

    async def cache_file_metadata(self, file_id: str, metadata: Dict[str, Any], ttl: int = 7200):
        """Cache file metadata"""
        key = f"file_meta:{file_id}"
        await self.hset(key, metadata, ttl)

    async def get_cached_file_metadata(self, file_id: str) -> Dict[str, Any]:
        """Get cached file metadata"""
        key = f"file_meta:{file_id}"
        return await self.hgetall(key)

    async def cache_bot_stats(self, stats: Dict[str, Any], ttl: int = 300):
        """Cache bot statistics"""
        key = "stats:bot"
        await self.set(key, stats, ttl)

    async def get_cached_bot_stats(self) -> Optional[Dict[str, Any]]:
        """Get cached bot statistics"""
        key = "stats:bot"
        return await self.get(key)

    # Queue operations (for background tasks)
    async def enqueue_task(self, queue: str, task_data: Dict[str, Any]):
        """Enqueue background task"""
        key = f"queue:{queue}"
        await self.rpush(key, task_data)

    async def dequeue_task(self, queue: str) -> Optional[Dict[str, Any]]:
        """Dequeue background task"""
        key = f"queue:{queue}"
        return await self.lpop(key)

    async def get_queue_size(self, queue: str) -> int:
        """Get queue size"""
        key = f"queue:{queue}"
        try:
            return await self.client.llen(key)
        except Exception as e:
            logger.error(f"Queue size check error for {queue}: {e}")
            return 0

    # Lock operations
    async def acquire_lock(self, lock_name: str, ttl: int = 30) -> bool:
        """Acquire distributed lock"""
        key = f"lock:{lock_name}"
        return await self.client.set(key, "locked", ex=ttl, nx=True) is not None

    async def release_lock(self, lock_name: str) -> bool:
        """Release distributed lock"""
        key = f"lock:{lock_name}"
        return await self.delete(key) > 0

    async def is_locked(self, lock_name: str) -> bool:
        """Check if lock exists"""
        key = f"lock:{lock_name}"
        return await self.exists(key)

    # Cleanup operations
    async def cleanup_expired_sessions(self):
        """Clean up expired user sessions"""
        pattern = "session:*"
        keys = []
        async for key in self.client.scan_iter(match=pattern):
            if await self.ttl(key) == -1:  # No expiration set
                keys.append(key)

        if keys:
            await self.delete(*keys)
            logger.info(f"Cleaned up {len(keys)} expired sessions")

    async def cleanup_old_cache(self):
        """Clean up old cache entries"""
        patterns = [
            "search:*",
            "file_meta:*",
            "temp:*"
        ]

        total_cleaned = 0
        for pattern in patterns:
            keys = []
            async for key in self.client.scan_iter(match=pattern):
                if await self.ttl(key) == -1:  # No expiration set
                    keys.append(key)

            if keys:
                total_cleaned += len(keys)
                await self.delete(*keys)

        if total_cleaned > 0:
            logger.info(f"Cleaned up {total_cleaned} old cache entries")