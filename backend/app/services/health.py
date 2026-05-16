from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import SessionLocal, redis_client


async def _database_health() -> dict[str, str]:
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as exc:  # pragma: no cover - defensive fallback
        return {"status": "error", "detail": str(exc)}


async def _redis_health() -> dict[str, str]:
    try:
        await redis_client.ping()
        return {"status": "ok"}
    except Exception as exc:  # pragma: no cover - defensive fallback
        return {"status": "error", "detail": str(exc)}


async def collect_health_status() -> dict[str, object]:
    settings = get_settings()
    database = await _database_health()
    redis = await _redis_health()
    overall_status = "ok" if database["status"] == "ok" and redis["status"] == "ok" else "degraded"

    return {
        "status": overall_status,
        "application": settings.app_name,
        "environment": settings.app_env,
        "services": {
            "database": database,
            "redis": redis,
        },
    }

