from datetime import UTC, datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.config import get_settings
from app.db.session import redis_client
from app.models.daily_report_history import DailyReportHistory
from app.repositories.daily_report_history_repository import DailyReportHistoryRepository
from app.repositories.system_event_repository import SystemEventRepository
from app.schemas.paper_trading import (
    PaperTradingPerformanceByDayRead,
    PaperTradingPerformanceBySymbolRead,
    PaperTradingPerformanceRead,
)
from app.services.controls.runtime_state import runtime_control_state
from app.services.execution.paper_trading import PaperTradingService
from app.services.health import collect_health_status
from app.services.notifications.telegram import TelegramNotifier
from app.services.operations.event_log import EventLogService


class DailyReportService:
    def __init__(self, session, paper_trading_service: PaperTradingService):
        self.session = session
        self.paper_trading_service = paper_trading_service
        self.settings = get_settings()
        self.telegram_notifier = TelegramNotifier()
        self.event_log_service = EventLogService(SystemEventRepository(session))
        self.report_history_repository = DailyReportHistoryRepository(session)

    async def build_preview(self, account_name: str, automation_status: dict | None = None) -> dict:
        report_data = await self._collect_report_data(account_name=account_name, automation_status=automation_status)
        message = self._format_daily_report_message(report_data)
        return {
            "account_name": account_name,
            "report_date_local": report_data["local_now"].date().isoformat(),
            "timezone": self.settings.daily_report_timezone,
            "message": message,
        }

    async def send_report(
        self,
        account_name: str,
        automation_status: dict | None = None,
        force: bool = False,
        trigger_type: str = "manual",
    ) -> dict:
        preview = await self.build_preview(account_name=account_name, automation_status=automation_status)
        account = await self.paper_trading_service.paper_account_repository.get_or_create(
            name=account_name,
            initial_balance=Decimal(str(self.paper_trading_service.risk_service.settings.risk_initial_balance)),
        )
        local_now = datetime.now(self._timezone())
        report_date = local_now.date().isoformat()
        redis_key = self._redis_key(account_name)

        if not force:
            already_sent_for_date = await redis_client.get(redis_key)
            if already_sent_for_date == report_date:
                await self._store_report_history(
                    account_id=account.id,
                    account_name=account_name,
                    report_date=local_now.date(),
                    trigger_type=trigger_type,
                    status="skipped",
                    message=preview["message"],
                    detail=f"Daily report for {report_date} was already sent.",
                )
                await self.session.commit()
                return {
                    "delivered": False,
                    "skipped": True,
                    "reason": f"Daily report for {report_date} was already sent.",
                    "message": preview["message"],
                }

        delivered = await self.telegram_notifier.send_message(preview["message"])
        if delivered:
            await redis_client.set(redis_key, report_date)
            await self._store_report_history(
                account_id=account.id,
                account_name=account_name,
                report_date=local_now.date(),
                trigger_type=trigger_type,
                status="delivered",
                message=preview["message"],
                detail=None,
            )
            await self.event_log_service.record(
                event_type="daily_report_sent",
                level="info",
                message=f"Daily Telegram report sent for account '{account_name}'.",
                payload={
                    "account_name": account_name,
                    "report_date": report_date,
                    "timezone": self.settings.daily_report_timezone,
                },
            )
            await self.session.commit()
        else:
            await self._store_report_history(
                account_id=account.id,
                account_name=account_name,
                report_date=local_now.date(),
                trigger_type=trigger_type,
                status="failed",
                message=preview["message"],
                detail="Telegram delivery failed.",
            )
            await self.event_log_service.record(
                event_type="daily_report_failed",
                level="warning",
                message=f"Daily Telegram report failed for account '{account_name}'.",
                payload={
                    "account_name": account_name,
                    "report_date": report_date,
                    "timezone": self.settings.daily_report_timezone,
                },
            )
            await self.session.commit()

        return {
            "delivered": delivered,
            "skipped": False,
            "message": preview["message"],
            "report_date": report_date,
        }

    async def maybe_send_scheduled_report(self, automation_status: dict | None = None) -> dict:
        if not self.settings.daily_report_enabled:
            return {"delivered": False, "skipped": True, "reason": "Daily report is disabled in config."}

        local_now = datetime.now(self._timezone())
        target_time = self._report_time_local()
        if local_now.time() < target_time:
            return {
                "delivered": False,
                "skipped": True,
                "reason": f"Report window has not opened yet. Target time is {target_time.isoformat(timespec='minutes')}.",
            }

        return await self.send_report(
            account_name=self.settings.daily_report_account_name,
            automation_status=automation_status,
            force=False,
            trigger_type="scheduled",
        )

    async def _collect_report_data(self, account_name: str, automation_status: dict | None = None) -> dict:
        performance = await self.paper_trading_service.get_performance(account_name=account_name)
        by_symbol = await self.paper_trading_service.get_performance_by_symbol(account_name=account_name)
        by_day = await self.paper_trading_service.get_performance_by_day(account_name=account_name)
        health = await collect_health_status()
        recent_events = [
            event
            for event in await SystemEventRepository(self.session).list_recent(limit=10)
            if event.event_type not in {"daily_report_sent", "daily_report_failed"}
        ][:5]
        local_now = datetime.now(self._timezone())

        return {
            "local_now": local_now,
            "health": health,
            "automation": automation_status or {},
            "kill_switch": runtime_control_state.get_kill_switch_status(),
            "performance": performance,
            "by_symbol": by_symbol,
            "by_day": by_day,
            "recent_events": recent_events,
        }

    def _format_daily_report_message(self, report_data: dict) -> str:
        performance: PaperTradingPerformanceRead = report_data["performance"]
        by_symbol: list[PaperTradingPerformanceBySymbolRead] = report_data["by_symbol"]
        by_day: list[PaperTradingPerformanceByDayRead] = report_data["by_day"]
        health = report_data["health"]
        automation = report_data["automation"]
        kill_switch = report_data["kill_switch"]
        local_now: datetime = report_data["local_now"]

        symbol_lines = by_symbol[:3]
        day_lines = by_day[:3]
        recent_events = report_data["recent_events"][:3]

        lines = [
            f"DAILY REPORT | {local_now.strftime('%Y-%m-%d %H:%M')} {self.settings.daily_report_timezone}",
            f"System: {health['status']} | DB: {health['services']['database']['status']} | Redis: {health['services']['redis']['status']}",
            f"Automation: mode={automation.get('mode', 'n/a')} running={automation.get('is_running', False)} loop={self._format_loop_seconds(automation.get('loop_interval_seconds'))}",
            f"Kill switch: {'ON' if kill_switch['enabled'] else 'OFF'}" + (f" | {kill_switch['reason']}" if kill_switch["enabled"] else ""),
            f"Account: {performance.account_name}",
            f"Balance: {performance.current_balance} | Return: {performance.realized_return_percent}%",
            f"Trades: total={performance.total_trades} closed={performance.closed_trades} open={performance.open_trades} win_rate={performance.win_rate_percent}%",
            f"PnL: {performance.realized_pnl} | Profit factor: {performance.profit_factor}",
        ]

        if symbol_lines:
            lines.append("By symbol:")
            for row in symbol_lines:
                lines.append(
                    f"- {row.symbol}: pnl={row.realized_pnl} trades={row.closed_trades} win_rate={row.win_rate_percent}% pf={row.profit_factor}"
                )

        if day_lines:
            lines.append("Recent days:")
            for row in day_lines:
                lines.append(
                    f"- {row.trading_day}: pnl={row.realized_pnl} trades={row.closed_trades} win_rate={row.win_rate_percent}%"
                )

        if recent_events:
            lines.append("Recent events:")
            for event in recent_events:
                lines.append(f"- {event.event_type}: {event.message}")

        return "\n".join(lines)

    def _report_time_local(self) -> time:
        hours, minutes = self.settings.daily_report_time_local.split(":", maxsplit=1)
        return time(hour=int(hours), minute=int(minutes))

    async def _store_report_history(
        self,
        account_id: int | None,
        account_name: str,
        report_date,
        trigger_type: str,
        status: str,
        message: str,
        detail: str | None,
    ) -> None:
        await self.report_history_repository.create(
            DailyReportHistory(
                account_id=account_id,
                account_name=account_name,
                report_date=report_date,
                timezone=self.settings.daily_report_timezone,
                trigger_type=trigger_type,
                status=status,
                message=message,
                detail=detail,
            )
        )

    def _timezone(self) -> ZoneInfo:
        candidates = [self.settings.daily_report_timezone]
        if self.settings.daily_report_timezone == "Europe/Kiev":
            candidates.append("Europe/Kyiv")
        candidates.append("UTC")

        for candidate in candidates:
            try:
                return ZoneInfo(candidate)
            except ZoneInfoNotFoundError:
                continue

        return ZoneInfo("UTC")

    @staticmethod
    def _redis_key(account_name: str) -> str:
        return f"trading:daily-report:last-sent:{account_name}"

    @staticmethod
    def _format_loop_seconds(value) -> str:
        if value in (None, "n/a"):
            return "n/a"
        return f"{value}s"
