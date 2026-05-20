# backend/services/performance/cache_manager.py
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from collections import OrderedDict
import hashlib
import json
import threading
import logging

logger = logging.getLogger(__name__)

class LRUCache:
    """Thread-safe LRU cache with TTL support"""

    def __init__(self, max_size: int = 100, default_ttl_hours: int = 24):
        self.max_size = max_size
        self.default_ttl = timedelta(hours=default_ttl_hours)
        self.cache: OrderedDict = OrderedDict()
        self.ttl_map: Dict[str, datetime] = {}
        self.lock = threading.RLock()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        """Get item from cache if not expired"""
        with self.lock:
            if key not in self.cache:
                self.misses += 1
                return None

            # Check TTL
            if datetime.now() > self.ttl_map[key]:
                self._evict(key)
                self.misses += 1
                return None

            # Move to end (most recently used)
            value = self.cache.pop(key)
            self.cache[key] = value
            self.hits += 1
            return value

    def set(self, key: str, value: Any, ttl_hours: Optional[int] = None):
        """Set item in cache with optional TTL"""
        with self.lock:
            if key in self.cache:
                self._evict(key)

            # Evict oldest if at capacity
            if len(self.cache) >= self.max_size:
                oldest_key = next(iter(self.cache))
                self._evict(oldest_key)

            # Store value
            self.cache[key] = value
            ttl = ttl_hours if ttl_hours else self.default_ttl
            self.ttl_map[key] = datetime.now() + timedelta(hours=ttl) if isinstance(ttl, int) else ttl

    def _evict(self, key: str):
        """Remove item from cache"""
        if key in self.cache:
            del self.cache[key]
        if key in self.ttl_map:
            del self.ttl_map[key]

    def get_stats(self) -> Dict:
        """Get cache statistics"""
        with self.lock:
            total = self.hits + self.misses
            hit_rate = self.hits / total if total > 0 else 0
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": f"{hit_rate:.2%}"
            }

class MenuCacheManager:
    """Specialized cache for menu data"""

    def __init__(self):
        self.content_cache = LRUCache(max_size=200, default_ttl_hours=24)
        self.semantic_cache = LRUCache(max_size=100, default_ttl_hours=168)  # 1 week for similar menus

    def get_file_hash(self, file_content: bytes) -> str:
        """Generate hash for exact content matching"""
        return hashlib.sha256(file_content).hexdigest()

    def get_semantic_hash(self, text: str) -> str:
        """Generate hash for semantic similarity (simplified)"""
        # Take first 1000 chars as signature
        signature = text[:1000] if len(text) > 1000 else text
        return hashlib.md5(signature.encode()).hexdigest()

    def get_cached_menu(self, file_hash: str) -> Optional[Dict]:
        """Retrieve cached menu by exact hash"""
        return self.content_cache.get(file_hash)

    def cache_menu(self, file_hash: str, menu_data: Dict, ttl_hours: int = 24):
        """Cache menu data"""
        self.content_cache.set(file_hash, menu_data, ttl_hours)

    def get_similar_menu(self, text: str) -> Optional[Dict]:
        """Check if similar menu was processed before"""
        semantic_hash = self.get_semantic_hash(text)
        return self.semantic_cache.get(semantic_hash)