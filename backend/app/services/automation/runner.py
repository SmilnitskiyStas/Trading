import asyncio
from contextlib import suppress
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.schemas.market_data import MarketDataSyncRequest
from app.schemas.paper_trading import PaperTradingCycleRequest
from app.services.execution.paper_trading import PaperTradingService
from app.services.indicators.service import IndicatorService
from app.services.market_data.service import MarketDataService
from app.services.reports.daily_report import DailyReportService
from app.services.risk.service import RiskService
from app.services.strategies.service import StrategyService


@dataclass
class AutomationCycleSummary:
    started_at: str
    finished_at: str
    synced_jobs: list[dict] = field(default_factory=list)
    execution_jobs: list[dict] = field(default_factory=list)
    status: str = "ok"
    error: str | None = None


class AutomationRunner:
    def __init__(self):
        self.settings = get_settings()
        self._task: asyncio.Task | None = None
        self._lock = asyncio.Lock()
        self._stop_event = asyncio.Event()
        self._status: dict = {
            "enabled": self.settings.automation_enabled,
            "mode": "running" if self.settings.automation_enabled else "stopped",
            "is_running": False,
            "loop_interval_seconds": self.settings.automation_loop_interval_seconds,
            "last_cycle": None,
            "last_started_at": None,
            "last_finished_at": None,
            "last_control_action": None,
        }

    async def start(self) -> None:
        if not self.settings.automation_enabled or self._task is not None or self._status["mode"] != "running":
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run_loop(), name="automation-runner")

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        self._status["is_running"] = False
        if self._status["mode"] == "running":
            self._status["mode"] = "stopped"

    async def pause(self) -> dict:
        self._status["mode"] = "paused"
        self._status["last_control_action"] = "pause"
        await self._shutdown_task_only()
        return self.get_status()

    async def resume(self) -> dict:
        self._status["mode"] = "running"
        self._status["last_control_action"] = "resume"
        await self.start()
        return self.get_status()

    async def shutdown(self) -> dict:
        self._status["mode"] = "stopped"
        self._status["last_control_action"] = "stop"
        await self._shutdown_task_only()
        return self.get_status()

    def get_status(self) -> dict:
        return self._status

    async def run_once(self) -> dict:
        async with self._lock:
            self._status["is_running"] = True
            started_at = datetime.now(tz=UTC)
            self._status["last_started_at"] = started_at.isoformat()
            summary = AutomationCycleSummary(started_at=started_at.isoformat(), finished_at=started_at.isoformat())

            try:
                async with SessionLocal() as session:
                    market_data_service = MarketDataService(session)
                    indicator_service = IndicatorService(market_data_service)
                    strategy_service = StrategyService(indicator_service)
                    paper_trading_service = PaperTradingService(
                        session=session,
                        risk_service=RiskService(strategy_service=strategy_service),
                    )

                    for symbol in self.settings.market_data_symbol_list:
                        for timeframe in self.settings.market_data_timeframe_list:
                            sync_result = await market_data_service.sync_ohlcv(
                                MarketDataSyncRequest(
                                    exchange=self.settings.market_data_exchange,
                                    symbol=symbol,
                                    timeframe=timeframe,
                                    limit=self.settings.market_data_default_fetch_limit,
                                )
                            )
                            summary.synced_jobs.append(sync_result.model_dump())

                    for symbol in self.settings.market_data_symbol_list:
                        for timeframe in self.settings.automation_execution_timeframe_list:
                            execution_result = await paper_trading_service.run_cycle(
                                PaperTradingCycleRequest(
                                    account_name=self.settings.automation_account_name,
                                    exchange=self.settings.market_data_exchange,
                                    symbol=symbol,
                                    timeframe=timeframe,
                                    limit=max(250, self.settings.market_data_default_fetch_limit),
                                )
                            )
                            summary.execution_jobs.append(
                                {
                                    "symbol": symbol,
                                    "timeframe": timeframe,
                                    "action": execution_result.action,
                                    "reasons": execution_result.reasons,
                                    "strategy_name": execution_result.trade.strategy_name
                                    if execution_result.trade is not None
                                    else strategy_service.resolve_strategy_name(
                                        symbol=symbol,
                                        strategy_name=self.settings.strategy_default_name,
                                    ),
                                }
                            )

                    daily_report_result = await DailyReportService(
                        session=session,
                        paper_trading_service=paper_trading_service,
                    ).maybe_send_scheduled_report(automation_status=self._status)
                    summary.execution_jobs.append(
                        {
                            "type": "daily_report",
                            "result": daily_report_result,
                        }
                    )
            except Exception as exc:
                summary.status = "error"
                summary.error = str(exc)
            finally:
                finished_at = datetime.now(tz=UTC)
                summary.finished_at = finished_at.isoformat()
                self._status["is_running"] = False
                self._status["last_finished_at"] = finished_at.isoformat()
                self._status["last_cycle"] = asdict(summary)

            return self._status

    async def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            if self._status["mode"] != "running":
                break
            await self.run_once()
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.settings.automation_loop_interval_seconds,
                )
            except TimeoutError:
                continue

    async def _shutdown_task_only(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        self._status["is_running"] = False
        self._stop_event = asyncio.Event()


automation_runner = AutomationRunner()
