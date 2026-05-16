from decimal import Decimal

from app.models.paper_trade import PaperTrade
from app.schemas.paper_trading import PaperTradingPerformanceRead
from app.services.reports.daily_report import DailyReportService
from app.services.execution.paper_trading import PaperTradingService


def test_open_trade_message_contains_core_fields():
    trade = PaperTrade(
        account_id=1,
        trading_pair_id=1,
        strategy_name="rsi_ema_trend_v1",
        timeframe="1h",
        status="OPEN",
        side="BUY",
        entry_price=Decimal("100"),
        exit_price=None,
        stop_loss_price=Decimal("95"),
        take_profit_price=Decimal("110"),
        position_size=Decimal("2"),
        fees_paid=Decimal("0"),
        realized_pnl=Decimal("0"),
        exit_reason=None,
        opened_at=None,
        closed_at=None,
    )

    message = PaperTradingService._format_open_trade_message("BTC/USDT", trade)

    assert "BTC/USDT PAPER TRADE OPENED" in message
    assert "Entry: 100" in message
    assert "Stop Loss: 95" in message


def test_closed_trade_message_contains_pnl_and_exit_reason():
    trade = PaperTrade(
        account_id=1,
        trading_pair_id=1,
        strategy_name="rsi_ema_trend_v1",
        timeframe="1h",
        status="CLOSED",
        side="BUY",
        entry_price=Decimal("100"),
        exit_price=Decimal("108"),
        stop_loss_price=Decimal("95"),
        take_profit_price=Decimal("110"),
        position_size=Decimal("2"),
        fees_paid=Decimal("0.5"),
        realized_pnl=Decimal("15.5"),
        exit_reason="take_profit",
        opened_at=None,
        closed_at=None,
    )

    message = PaperTradingService._format_closed_trade_message("BTC/USDT", trade)

    assert "Exit Reason: take_profit" in message
    assert "PnL: 15.5" in message


def test_daily_report_format_contains_core_sections():
    report_service = DailyReportService(session=None, paper_trading_service=None)
    message = report_service._format_daily_report_message(
        {
            "local_now": __import__("datetime").datetime(2026, 5, 15, 9, 0),
            "health": {
                "status": "ok",
                "services": {
                    "database": {"status": "ok"},
                    "redis": {"status": "ok"},
                },
            },
            "automation": {
                "mode": "running",
                "is_running": False,
                "loop_interval_seconds": 300,
            },
            "kill_switch": {
                "enabled": False,
                "reason": "",
            },
            "performance": PaperTradingPerformanceRead(
                account_name="paper-main",
                initial_balance=Decimal("1000"),
                current_balance=Decimal("1010"),
                realized_pnl=Decimal("10"),
                realized_return_percent=Decimal("1"),
                total_trades=4,
                open_trades=1,
                closed_trades=3,
                winning_trades=2,
                losing_trades=1,
                win_rate_percent=Decimal("66.6"),
                average_win=Decimal("12"),
                average_loss=Decimal("5"),
                profit_factor=Decimal("2.4"),
            ),
            "by_symbol": [],
            "by_day": [],
            "recent_events": [],
        }
    )

    assert "DAILY REPORT | 2026-05-15 09:00" in message
    assert "System: ok | DB: ok | Redis: ok" in message
    assert "Account: paper-main" in message
    assert "Balance: 1010 | Return: 1%" in message
