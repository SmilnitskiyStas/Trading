from app.models import Candle, Exchange, TradingPair


def test_model_tablenames_match_domain_design():
    assert Exchange.__tablename__ == "exchanges"
    assert TradingPair.__tablename__ == "trading_pairs"
    assert Candle.__tablename__ == "candles"


def test_candle_has_expected_unique_constraint():
    constraint_names = {constraint.name for constraint in Candle.__table__.constraints}
    assert "uq_candles_pair_timeframe_open_time" in constraint_names
