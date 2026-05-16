from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.schemas.ml import MLAdvisorySignal
from app.schemas.strategy import StrategyEvaluationResponse, StrategySignal


class RiskEvaluationRequest(BaseModel):
    exchange: str = Field(default="binance")
    symbol: str = Field(default="BTC/USDT")
    timeframe: str = Field(default="1h")
    limit: int = Field(default=250, ge=50, le=1000)
    strategy_name: str = Field(default=get_settings().strategy_default_name)
    account_balance: Decimal = Field(default=Decimal("1000"))
    current_daily_loss_percent: Decimal = Field(default=Decimal("0"))
    current_drawdown_percent: Decimal = Field(default=Decimal("0"))
    open_positions_count: int = Field(default=0, ge=0)
    has_open_position_for_symbol: bool = Field(default=False)
    market_data_is_fresh: bool = Field(default=True)
    exchange_api_healthy: bool = Field(default=True)


class TradePlan(BaseModel):
    side: StrategySignal
    entry_price: Decimal
    stop_loss_price: Decimal | None
    take_profit_price: Decimal | None
    position_size: Decimal | None
    account_risk_amount: Decimal | None
    trade_risk_per_unit: Decimal | None
    estimated_slippage_percent: Decimal
    estimated_fee_percent: Decimal


class RiskMLFilterResult(BaseModel):
    enabled: bool
    available: bool
    model_id: str | None = None
    advisory_signal: MLAdvisorySignal | None = None
    probability_up: float | None = None
    confidence: float | None = None
    passes_confidence_threshold: bool | None = None
    confidence_threshold: float | None = None
    detail: str | None = None


class RiskEvaluationResponse(BaseModel):
    mode: str
    allowed: bool
    reasons: list[str]
    evaluated_at: datetime
    strategy: StrategyEvaluationResponse
    trade_plan: TradePlan | None
    ml_filter: RiskMLFilterResult | None = None
