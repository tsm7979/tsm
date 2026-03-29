"""
Intelligent Caching Layer
=========================

Response caching for cost reduction and performance optimization.
"""

from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import OrderedDict
import hashlib
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """A cached response."""
    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    ttl_seconds: int = 3600
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        if self.ttl_seconds == 0:
            return False  # Never expires
        age = (datetime.utcnow() - self.created_at).total_seconds()
        return age > self.ttl_seconds

    def touch(self):
        """Update last accessed time."""
        self.last_accessed = datetime.utcnow()
        self.access_count += 1


class CacheStrategy(str):
    """Cache eviction strategies."""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    TTL = "ttl"  # Time To Live
    FIFO = "fifo"  # First In First Out


class ResponseCache:
    """
    In-memory response cache with configurable eviction strategies.

    In production, this would use Redis or Memcached.
    """

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: int = 3600,
        strategy: str = CacheStrategy.LRU
    ):
        """
        Initialize response cache.

        Args:
            max_size: Maximum number of cached entries
            default_ttl: Default time-to-live in seconds
            strategy: Eviction strategy
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.strategy = strategy

        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()

        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0

        logger.info(
            f"ResponseCache initialized (max_size={max_size}, "
            f"ttl={default_ttl}s, strategy={strategy})"
        )

    def get(self, key: str) -> Optional[Any]:
        """
        Get cached value.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        if key not in self.cache:
            self.misses += 1
            return None

        entry = self.cache[key]

        # Check expiration
        if entry.is_expired():
            logger.debug(f"Cache expired: {key}")
            del self.cache[key]
            self.misses += 1
            return None

        # Update access info
        entry.touch()

        # Move to end for LRU
        if self.strategy == CacheStrategy.LRU:
            self.cache.move_to_end(key)

        self.hits += 1
        logger.debug(f"Cache hit: {key}")
        return entry.value

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Set cached value.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (None = use default)
            metadata: Optional metadata
        """
        now = datetime.utcnow()

        # Create cache entry
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=now,
            last_accessed=now,
            ttl_seconds=ttl if ttl is not None else self.default_ttl,
            metadata=metadata or {}
        )

        # Evict if needed
        if key not in self.cache and len(self.cache) >= self.max_size:
            self._evict()

        # Store entry
        self.cache[key] = entry

        logger.debug(f"Cache set: {key} (ttl={entry.ttl_seconds}s)")

    def delete(self, key: str) -> bool:
        """
        Delete cached entry.

        Args:
            key: Cache key

        Returns:
            True if deleted, False if not found
        """
        if key in self.cache:
            del self.cache[key]
            logger.debug(f"Cache delete: {key}")
            return True
        return False

    def clear(self):
        """Clear all cached entries."""
        count = len(self.cache)
        self.cache.clear()
        logger.info(f"Cache cleared ({count} entries)")

    def _evict(self):
        """Evict entry based on strategy."""
        if not self.cache:
            return

        if self.strategy == CacheStrategy.LRU:
            # Remove least recently used (first item)
            key, _ = self.cache.popitem(last=False)
        elif self.strategy == CacheStrategy.LFU:
            # Remove least frequently used
            key = min(
                self.cache.keys(),
                key=lambda k: self.cache[k].access_count
            )
            del self.cache[key]
        elif self.strategy == CacheStrategy.TTL:
            # Remove oldest entry
            key = min(
                self.cache.keys(),
                key=lambda k: self.cache[k].created_at
            )
            del self.cache[key]
        elif self.strategy == CacheStrategy.FIFO:
            # Remove first entry
            key, _ = self.cache.popitem(last=False)
        else:
            # Default to LRU
            key, _ = self.cache.popitem(last=False)

        self.evictions += 1
        logger.debug(f"Cache eviction ({self.strategy}): {key}")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0.0

        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "evictions": self.evictions,
            "strategy": self.strategy,
        }


class SmartCache:
    """
    Smart caching layer with request fingerprinting and invalidation.

    Automatically generates cache keys from request parameters.
    """

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: int = 3600,
        enable_semantic_caching: bool = False
    ):
        """
        Initialize smart cache.

        Args:
            max_size: Maximum cache size
            default_ttl: Default TTL in seconds
            enable_semantic_caching: Use semantic similarity for cache hits
        """
        self.cache = ResponseCache(
            max_size=max_size,
            default_ttl=default_ttl,
            strategy=CacheStrategy.LRU
        )
        self.enable_semantic_caching = enable_semantic_caching

        # Cache key templates for different request types
        self.key_templates = {
            "simple": "{model}:{prompt_hash}",
            "context": "{model}:{prompt_hash}:{context_hash}",
            "full": "{model}:{prompt_hash}:{context_hash}:{options_hash}"
        }

        logger.info(
            f"SmartCache initialized (semantic_caching={enable_semantic_caching})"
        )

    def generate_key(
        self,
        prompt: str,
        model: str,
        context: Optional[Dict[str, Any]] = None,
        options: Optional[Dict[str, Any]] = None,
        template: str = "simple"
    ) -> str:
        """
        Generate cache key from request parameters.

        Args:
            prompt: Input prompt
            model: Model name
            context: Optional context
            options: Optional options
            template: Key template to use

        Returns:
            Cache key (SHA256 hash)
        """
        # Hash prompt
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]

        # Hash context if provided
        context_hash = ""
        if context and template in ["context", "full"]:
            context_json = json.dumps(context, sort_keys=True)
            context_hash = hashlib.sha256(context_json.encode()).hexdigest()[:16]

        # Hash options if provided
        options_hash = ""
        if options and template == "full":
            options_json = json.dumps(options, sort_keys=True)
            options_hash = hashlib.sha256(options_json.encode()).hexdigest()[:16]

        # Build key
        key_template = self.key_templates[template]
        key = key_template.format(
            model=model,
            prompt_hash=prompt_hash,
            context_hash=context_hash,
            options_hash=options_hash
        )

        return key

    def get_cached_response(
        self,
        prompt: str,
        model: str,
        context: Optional[Dict[str, Any]] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Optional[Tuple[Any, str]]:
        """
        Get cached response if available.

        Args:
            prompt: Input prompt
            model: Model name
            context: Optional context
            options: Optional options

        Returns:
            Tuple of (cached_response, cache_key) or None
        """
        # Try full match first
        key = self.generate_key(prompt, model, context, options, template="full")
        result = self.cache.get(key)
        if result is not None:
            logger.info(f"Cache hit (full): {key[:32]}...")
            return result, key

        # Try context match
        if context:
            key = self.generate_key(prompt, model, context, None, template="context")
            result = self.cache.get(key)
            if result is not None:
                logger.info(f"Cache hit (context): {key[:32]}...")
                return result, key

        # Try simple match
        key = self.generate_key(prompt, model, None, None, template="simple")
        result = self.cache.get(key)
        if result is not None:
            logger.info(f"Cache hit (simple): {key[:32]}...")
            return result, key

        # Semantic caching (placeholder - would use embeddings in production)
        if self.enable_semantic_caching:
            # TODO: Implement semantic similarity search
            pass

        logger.debug("Cache miss")
        return None

    def cache_response(
        self,
        prompt: str,
        model: str,
        response: Any,
        context: Optional[Dict[str, Any]] = None,
        options: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None
    ) -> str:
        """
        Cache a response.

        Args:
            prompt: Input prompt
            model: Model name
            response: Response to cache
            context: Optional context
            options: Optional options
            ttl: Optional TTL override

        Returns:
            Cache key
        """
        # Determine template based on what's provided
        if options:
            template = "full"
        elif context:
            template = "context"
        else:
            template = "simple"

        key = self.generate_key(prompt, model, context, options, template)

        # Build metadata
        metadata = {
            "model": model,
            "prompt_length": len(prompt),
            "template": template,
        }

        # Cache the response
        self.cache.set(key, response, ttl=ttl, metadata=metadata)

        logger.info(f"Cached response: {key[:32]}... (template={template})")
        return key

    def invalidate_model(self, model: str):
        """Invalidate all cache entries for a model."""
        keys_to_delete = [
            key for key, entry in self.cache.cache.items()
            if entry.metadata.get("model") == model
        ]

        for key in keys_to_delete:
            self.cache.delete(key)

        logger.info(f"Invalidated {len(keys_to_delete)} entries for model {model}")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = self.cache.get_stats()
        stats["semantic_caching"] = self.enable_semantic_caching
        return stats


class CacheWarmer:
    """
    Pre-warms cache with common queries.

    Useful for production deployment to reduce cold-start latency.
    """

    def __init__(self, cache: SmartCache):
        """
        Initialize cache warmer.

        Args:
            cache: SmartCache instance
        """
        self.cache = cache
        self.common_queries = []

    def add_common_query(
        self,
        prompt: str,
        model: str,
        response: Any,
        ttl: Optional[int] = None
    ):
        """Add a common query to warm cache."""
        self.common_queries.append({
            "prompt": prompt,
            "model": model,
            "response": response,
            "ttl": ttl
        })

    def warm_cache(self):
        """Warm cache with common queries."""
        count = 0
        for query in self.common_queries:
            self.cache.cache_response(
                prompt=query["prompt"],
                model=query["model"],
                response=query["response"],
                ttl=query.get("ttl")
            )
            count += 1

        logger.info(f"Cache warmed with {count} common queries")
        return count


# Global cache instance
smart_cache = SmartCache(
    max_size=1000,
    default_ttl=3600,  # 1 hour
    enable_semantic_caching=False  # Enable in production with embeddings
)
