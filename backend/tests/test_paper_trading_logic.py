from decimal import Decimal

from app.services.execution.paper_trading import PaperTradingService
from app.services.risk.service import DECIMAL_8


class DummyAccount:
    initial_balance = Decimal("1000")
    current_balance = Decimal("850")


def test_current_drawdown_percent_uses_account_balances():
    result = PaperTradingService._current_drawdown_percent(DummyAccount())
    assert result == Decimal("15")


def test_current_drawdown_percent_is_zero_when_balance_above_initial():
    account = DummyAccount()
    account.current_balance = Decimal("1200")
    result = PaperTradingService._current_drawdown_percent(account)
    assert result == Decimal("0")


def test_resolve_test_status_reports_bootstrapping_without_closed_trades():
    phase, pnl_status, ready, summary = PaperTradingService._resolve_test_status(
        realized_pnl=Decimal("0"),
        closed_trades=0,
        days_with_closed_trades=0,
    )
    assert phase == "BOOTSTRAPPING"
    assert pnl_status == "NO_TRADES_YET"
    assert ready is False
    assert "no closed trades" in summary.lower()


def test_resolve_test_status_reports_profitable_when_sample_is_large_enough():
    phase, pnl_status, ready, summary = PaperTradingService._resolve_test_status(
        realized_pnl=Decimal("12.50"),
        closed_trades=8,
        days_with_closed_trades=3,
    )
    assert phase == "EVALUATING"
    assert pnl_status == "PROFITABLE"
    assert ready is True
    assert "positive realized result" in summary.lower()


def test_max_drawdown_percent_tracks_peak_to_trough_path():
    class Trade:
        def __init__(self, pnl, closed_order):
            self.realized_pnl = Decimal(pnl)
            self.closed_at = closed_order

    trades = [
        Trade("100", 1),
        Trade("-50", 2),
        Trade("-100", 3),
        Trade("80", 4),
    ]

    result = PaperTradingService._max_drawdown_percent(Decimal("1000"), trades)

    assert result == Decimal("13.63636363636363636363636364")
