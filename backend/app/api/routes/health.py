from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.services.health import collect_health_status

router = APIRouter(tags=["health"])


@router.get("/health")
@router.get("/api/v1/health")
async def health_check():
    health = await collect_health_status()
    status_code = (
        status.HTTP_200_OK if health["status"] == "ok" else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    return JSONResponse(status_code=status_code, content=health)

