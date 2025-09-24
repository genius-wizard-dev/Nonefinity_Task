"""
Health check utilities for monitoring service status.
"""

import asyncio
from typing import Dict, Any

from src.infrastructure.celery import check_redis_connection
from src.infrastructure.database import ping_mongodb, QdrantService
from src.utils.logger import logger


async def check_mongodb_health() -> Dict[str, Any]:
    """Check MongoDB connection health."""
    try:
        is_connected = await ping_mongodb()
        return {
            "service": "mongodb",
            "status": "healthy" if is_connected else "unhealthy",
            "connected": is_connected
        }
    except Exception as e:
        return {
            "service": "mongodb",
            "status": "error",
            "error": str(e),
            "connected": False
        }


def check_qdrant_health() -> Dict[str, Any]:
    """Check Qdrant connection health."""
    try:
        qdrant = QdrantService()
        info = qdrant.get_collection_info()

        if info.get("status") == "success":
            return {
                "service": "qdrant",
                "status": "healthy",
                "points_count": info.get("points_count", 0),
                "vectors_count": info.get("vectors_count", 0)
            }
        else:
            return {
                "service": "qdrant",
                "status": "unhealthy",
                "error": info.get("message", "Unknown error")
            }
    except Exception as e:
        return {
            "service": "qdrant",
            "status": "error",
            "error": str(e)
        }


def check_redis_health() -> Dict[str, Any]:
    """Check Redis connection health."""
    try:
        result = check_redis_connection()
        if "healthy" in result:
            return {
                "service": "redis",
                "status": "healthy",
                "message": result
            }
        else:
            return {
                "service": "redis",
                "status": "unhealthy",
                "error": result
            }
    except Exception as e:
        return {
            "service": "redis",
            "status": "error",
            "error": str(e)
        }


async def get_system_health() -> Dict[str, Any]:
    """Get comprehensive system health status."""
    try:
        logger.info("Running system health check")

        # Run health checks
        mongodb_health = await check_mongodb_health()
        qdrant_health = check_qdrant_health()
        redis_health = check_redis_health()

        health_checks = [mongodb_health, qdrant_health, redis_health]

        # Determine overall status
        all_healthy = all(check["status"] == "healthy" for check in health_checks)
        any_error = any(check["status"] == "error" for check in health_checks)

        if all_healthy:
            overall_status = "healthy"
        elif any_error:
            overall_status = "error"
        else:
            overall_status = "degraded"

        result = {
            "overall_status": overall_status,
            "timestamp": asyncio.get_event_loop().time(),
            "services": health_checks
        }

        logger.info("System health check completed", overall_status=overall_status)
        return result

    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return {
            "overall_status": "error",
            "error": str(e),
            "services": []
        }


def print_health_status():
    """Print health status to console."""
    async def _print_health():
        health = await get_system_health()

        print("🏥 System Health Check")
        print("=" * 50)
        print(f"Overall Status: {health['overall_status'].upper()}")
        print()

        for service in health.get('services', []):
            status_emoji = {
                'healthy': '✅',
                'unhealthy': '⚠️',
                'error': '❌'
            }.get(service['status'], '❓')

            print(f"{status_emoji} {service['service'].upper()}: {service['status']}")

            if service['status'] != 'healthy':
                if 'error' in service:
                    print(f"   Error: {service['error']}")
            else:
                # Show additional info for healthy services
                if service['service'] == 'qdrant':
                    points = service.get('points_count', 0)
                    vectors = service.get('vectors_count', 0)
                    print(f"   Points: {points}, Vectors: {vectors}")

        print()

    asyncio.run(_print_health())


if __name__ == "__main__":
    print_health_status()
