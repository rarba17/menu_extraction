# backend/services/performance/load_balancer.py
import psutil
import asyncio
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class LoadBalancer:
    """Intelligent load balancing based on system resources"""

    def __init__(self):
        self.backends = []
        self.health_check_interval = 30
        self.current_index = 0

    async def monitor_resources(self) -> Dict:
        """Monitor system resources for scaling decisions"""
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "load_avg": psutil.getloadavg(),
            "queue_size": 0  # Would be from actual queue
        }

    async def get_best_backend(self) -> str:
        """Get backend with lowest load"""
        resources = await self.monitor_resources()

        # Auto-scaling decision
        if resources["cpu_percent"] > 80 or resources["memory_percent"] > 85:
            logger.warning("High load detected, consider scaling up")
            # Trigger auto-scaling webhook
            await self._trigger_auto_scaling()

        # Simple round-robin for now
        backend = self.backends[self.current_index % len(self.backends)]
        self.current_index += 1
        return backend

    async def _trigger_auto_scaling(self):
        """Trigger webhook for auto-scaling (Kubernetes, AWS, etc.)"""
        # Call cloud provider API to add more instances
        pass