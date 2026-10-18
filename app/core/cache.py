"""Small Redis helpers for application caches and token revocation metadata."""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

import redis
from redis.exceptions import RedisError

from app.core.config import settings


_redis_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis:
    """Return a shared Redis client configured from application settings."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


def build_policy_cache_key(policy_id: int, *, actor_id: int, role: str, actor_region: str | None) -> str:
    region_key = (actor_region or "").strip().casefold()
    return f"policy:{policy_id}:user:{actor_id}:{role}:{region_key}"


def build_policy_list_cache_key(
    *, actor_id: int, role: str, actor_region: str | None, region: str | None, skip: int, limit: int
) -> str:
    actor_region_key = (actor_region or "").strip().casefold()
    normalized_region = (region or "all").strip().casefold()
    return f"policies:list:{actor_id}:{role}:{actor_region_key}:{normalized_region}:{skip}:{limit}"


def build_ai_cache_key(
    question: str,
    *,
    user_id: int,
    policy_id: int | None,
    top_k: int | None,
) -> str:
    key_data = json.dumps(
        {
            "question": question.strip(),
            "user_id": user_id,
            "policy_id": policy_id,
            "top_k": top_k,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(key_data.encode("utf-8")).hexdigest()
    return f"ai:result:{digest}"


def get_cached_json(key: str, default: Any = None) -> Any:
    """Return a decoded cache value, or default if Redis/data is unavailable."""
    try:
        value = get_redis_client().get(key)
        return default if value is None else json.loads(value)
    except (RedisError, TypeError, ValueError):
        return default


def set_cached_json(key: str, payload: Any, ttl_seconds: int = 300) -> bool:
    """Cache a JSON-serializable payload for a bounded period."""
    if ttl_seconds <= 0:
        return False
    try:
        get_redis_client().setex(key, ttl_seconds, json.dumps(payload, default=str))
        return True
    except (RedisError, TypeError, ValueError):
        return False


def delete_cache_key(key: str) -> bool:
    """Delete a cache key; return False if Redis is unavailable or absent."""
    try:
        return bool(get_redis_client().delete(key))
    except RedisError:
        return False


def delete_cache_prefix(prefix: str) -> int:
    """Delete keys matching a prefix using SCAN rather than blocking KEYS."""
    try:
        client = get_redis_client()
        keys = list(client.scan_iter(match=f"{prefix}*"))
        return int(client.delete(*keys)) if keys else 0
    except RedisError:
        return 0


def build_token_cache_key(jti: str) -> str:
    return f"token:revoked:{jti}"


def is_token_revoked(jti: str | None) -> bool:
    """Check the short-lived Redis revocation marker."""
    if not jti:
        return False
    try:
        return bool(get_redis_client().exists(build_token_cache_key(jti)))
    except RedisError:
        return False


def mark_token_revoked(jti: str | None, expires_at: datetime | None) -> bool:
    """Cache a revocation marker until the JWT's expiration time."""
    if not jti:
        return False
    try:
        if expires_at is None:
            ttl_seconds = 3600
        else:
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            ttl_seconds = int((expires_at - datetime.now(timezone.utc)).total_seconds())
            if ttl_seconds <= 0:
                return False
        get_redis_client().setex(build_token_cache_key(jti), ttl_seconds, "1")
        return True
    except (RedisError, OverflowError, TypeError, ValueError):
        return False
