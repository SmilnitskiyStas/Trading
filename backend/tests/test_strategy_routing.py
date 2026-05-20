from app.services.strategies.service import StrategyService


def test_strategy_service_routes_btc_to_v2_when_default_requested():
    service = StrategyService(indicator_service=None)

    resolved = service.resolve_strategy_name(
        symbol="BTC/USDT",
        strategy_name=service.settings.strategy_default_name,
    )

    assert resolved == "rsi_ema_trend_v2"


def test_strategy_service_routes_eth_to_multi_when_default_requested():
    service = StrategyService(indicator_service=None)

    resolved = service.resolve_strategy_name(
        symbol="ETH/USDT",
        strategy_name=service.settings.strategy_default_name,
    )

    assert resolved == "rsi_ema_trend_multi_v1"


def test_strategy_service_preserves_explicit_override():
    service = StrategyService(indicator_service=None)

    resolved = service.resolve_strategy_name(
        symbol="BTC/USDT",
        strategy_name="rsi_ema_trend_multi_v1",
    )

    assert resolved == "rsi_ema_trend_multi_v1"


def test_strategy_service_routes_btc_to_paper_preset_for_paper_execution():
    service = StrategyService(indicator_service=None)

    resolved = service.resolve_paper_strategy_name(
        symbol="BTC/USDT",
        strategy_name=service.settings.strategy_default_name,
    )

    assert resolved == "rsi_ema_trend_paper_v1"


def test_strategy_service_routes_eth_to_paper_preset_for_paper_execution():
    service = StrategyService(indicator_service=None)

    resolved = service.resolve_paper_strategy_name(
        symbol="ETH/USDT",
        strategy_name=service.settings.strategy_default_name,
    )

    assert resolved == "rsi_ema_trend_paper_v1"
