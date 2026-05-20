# backend/configs/performance_configs.py

# Small scale (development)
DEV_CONFIG = {
    "max_connections": 5,
    "cache_size": 50,
    "max_concurrent_requests": 3,
    "rate_limit": 30,
    "image_quality": 85,
    "model": "gemini-1.5-flash"
}

# Medium scale (production)
PROD_CONFIG = {
    "max_connections": 20,
    "cache_size": 500,
    "max_concurrent_requests": 10,
    "rate_limit": 60,
    "image_quality": 80,
    "model": "gemini-1.5-pro",
    "redis_enabled": True,
    "distributed_processing": True
}

# Large scale (enterprise)
ENTERPRISE_CONFIG = {
    "max_connections": 100,
    "cache_size": 5000,
    "max_concurrent_requests": 50,
    "rate_limit": 300,
    "image_quality": 75,
    "model": "gemini-1.5-pro",
    "redis_enabled": True,
    "distributed_processing": True,
    "auto_scaling": True,
    "cdn_enabled": True,
    "streaming_responses": True
}
