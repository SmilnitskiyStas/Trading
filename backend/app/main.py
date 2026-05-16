from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.automation import router as automation_router
from app.api.routes.backtesting import router as backtesting_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.exports import router as exports_router
from app.api.routes.health import router as health_router
from app.api.routes.indicators import router as indicators_router
from app.api.routes.market_data import router as market_data_router
from app.api.routes.ml import router as ml_router
from app.api.routes.paper_trading import router as paper_trading_router
from app.api.routes.reports import router as reports_router
from app.api.routes.risk import router as risk_router
from app.api.routes.strategy import router as strategy_router
from app.api.routes.system_events import router as system_events_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.services.automation.runner import automation_runner


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    await automation_runner.start()
    yield
    await automation_runner.stop()


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(health_router)
app.include_router(dashboard_router)
app.include_router(exports_router)
app.include_router(automation_router)
app.include_router(backtesting_router)
app.include_router(indicators_router)
app.include_router(market_data_router)
app.include_router(ml_router)
app.include_router(paper_trading_router)
app.include_router(reports_router)
app.include_router(risk_router)
app.include_router(strategy_router)
app.include_router(system_events_router)


@app.get("/", tags=["meta"])
async def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "environment": settings.app_env,
        "docs_url": "/docs",
    }
