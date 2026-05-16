from datetime import UTC, datetime
from decimal import Decimal

from app.schemas.backtesting import BacktestTrade
from app.services.backtesting.service import BacktestingService


def test_drawdown_percent_is_zero_at_peak():
    result = BacktestingService._drawdown_percent(Decimal("1000"), Decimal("1000"))
    assert result == Decimal("0")


def test_daily_loss_percent_uses_only_negative_realized_pnl():
    assert BacktestingService._daily_loss_percent(Decimal("-50"), Decimal("1000")) == Decimal("5")
    assert BacktestingService._daily_loss_percent(Decimal("20"), Decimal("1000")) == Decimal("0")


def test_sharpe_ratio_returns_zero_for_short_series():
    assert BacktestingService._sharpe_ratio([0.01]) == 0.0


def test_max_drawdown_percent_tracks_equity_drops():
    service = BacktestingService.__new__(BacktestingService)
    trades = [
        BacktestTrade(
            opened_at=datetime(2026, 5, 15, 0, 0, tzinfo=UTC),
            closed_at=datetime(2026, 5, 15, 1, 0, tzinfo=UTC),
            entry_price=Decimal("100"),
            exit_price=Decimal("110"),
            stop_loss_price=Decimal("95"),
            take_profit_price=Decimal("120"),
            position_size=Decimal("1"),
            fees_paid=Decimal("0"),
            pnl=Decimal("100"),
            pnl_percent=Decimal("10"),
            exit_reason="take_profit",
        ),
        BacktestTrade(
            opened_at=datetime(2026, 5, 16, 0, 0, tzinfo=UTC),
            closed_at=datetime(2026, 5, 16, 1, 0, tzinfo=UTC),
            entry_price=Decimal("110"),
            exit_price=Decimal("90"),
            stop_loss_price=Decimal("100"),
            take_profit_price=Decimal("130"),
            position_size=Decimal("1"),
            fees_paid=Decimal("0"),
            pnl=Decimal("-150"),
            pnl_percent=Decimal("-15"),
            exit_reason="stop_loss",
        ),
    ]

    result = service._max_drawdown_percent(Decimal("1000"), trades)

    assert result == Decimal("13.63636363")
