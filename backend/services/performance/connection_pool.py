# backend/services/performance/connection_pool.py
import aiohttp
import asyncio
from typing import Optional, List, Dict
import time
import logging

logger = logging.getLogger(__name__)

class GeminiConnectionPool:
    """Pool of connections for Gemini API requests"""

    def __init__(self, max_connections: int = 10, max_retries: int = 3):
        self.max_connections = max_connections
        self.max_retries = max_retries
        self.session: Optional[aiohttp.ClientSession] = None
        self.semaphore = asyncio.Semaphore(max_connections)
        self.batch_queue = []
        self.batch_size = 5
        self.batch_timeout = 0.5  # seconds

    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create session"""
        if not self.session:
            self.session = aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(
                    limit=self.max_connections,
                    ttl_dns_cache=300,
                    keepalive_timeout=30
                ),
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self.session

    async def batch_gemini_requests(self, requests: List[Dict]) -> List[Dict]:
        """Batch multiple Gemini requests"""
        async with self.semaphore:
            session = await self.get_session()

            # Prepare batch request
            batch_payload = {
                "requests": requests
            }

            for attempt in range(self.max_retries):
                try:
                    async with session.post(
                        "https://generativelanguage.googleapis.com/v1/batch",
                        json=batch_payload,
                        params={"key": config.GEMINI_API_KEY}
                    ) as response:
                        if response.status == 200:
                            return await response.json()
                        else:
                            logger.warning(f"Batch request failed (attempt {attempt + 1})")
                            await asyncio.sleep(2 ** attempt)
                except Exception as e:
                    logger.error(f"Batch error: {e}")

            raise Exception("Max retries exceeded for batch request")

    async def close(self):
        """Close session"""
        if self.session:
            await self.session.close()