from datetime import UTC, datetime
from decimal import Decimal, ROUND_DOWN

from fastapi import HTTPException

from app.core.config import get_settings
from app.schemas.ml import MLAdvisorySignal, MLPredictRequest
from app.schemas.risk import RiskEvaluationRequest, RiskEvaluationResponse, RiskMLFilterResult, TradePlan
from app.schemas.strategy import StrategySignal
from app.services.controls.runtime_state import runtime_control_state
from app.services.ml.service import MLService
from app.services.strategies.service import StrategyService


DECIMAL_8 = Decimal("0.00000001")


class RiskService:
    def __init__(self, strategy_service: StrategyService, ml_service: MLService | None = None):
        self.strategy_service = strategy_service
        self.settings = get_settings()
        self.ml_service = ml_service
        if self.ml_service is None and hasattr(strategy_service, "indicator_service"):
            self.ml_service = MLService(strategy_service.indicator_service)

    async def evaluate(self, payload: RiskEvaluationRequest) -> RiskEvaluationResponse:
        strategy_result = await self.strategy_service.evaluate_strategy_inputs(
            exchange=payload.exchange,
            symbol=payload.symbol,
            timeframe=payload.timeframe,
            limit=payload.limit,
            strategy_name=payload.strategy_name,
        )

        reasons: list[str] = []
        allowed = True
        ml_filter_result: RiskMLFilterResult | None = None

        if strategy_result.signal != StrategySignal.BUY:
            allowed = False
            reasons.append(f"Strategy signal is {strategy_result.signal}, so no long entry is allowed.")

        if payload.symbol not in self.settings.market_data_symbol_list:
            allowed = False
            reasons.append(f"Symbol '{payload.symbol}' is outside the allowed MVP list.")

        if payload.timeframe not in self.settings.market_data_timeframe_list:
            allowed = False
            reasons.append(f"Timeframe '{payload.timeframe}' is outside the allowed MVP list.")

        if payload.current_daily_loss_percent >= Decimal(str(self.settings.risk_max_daily_loss_percent)):
            allowed = False
            reasons.append("Daily loss limit has already been reached.")

        if payload.current_drawdown_percent >= Decimal(str(self.settings.risk_max_total_drawdown_percent)):
            allowed = False
            reasons.append("Maximum total drawdown limit has already been reached.")

        if payload.open_positions_count >= self.settings.risk_max_open_positions:
            allowed = False
            reasons.append("Maximum number of open positions has already been reached.")

        if payload.has_open_position_for_symbol:
            allowed = False
            reasons.append("An open position for this symbol already exists.")

        if not payload.market_data_is_fresh:
            allowed = False
            reasons.append("Market data is stale, so trading is blocked.")

        if not payload.exchange_api_healthy:
            allowed = False
            reasons.append("Exchange API is unhealthy, so trading is blocked.")

        kill_switch = runtime_control_state.get_kill_switch_status()
        if kill_switch["enabled"]:
            allowed = False
            reasons.append(f"Emergency kill switch is active: {kill_switch['reason']}")

        if self.settings.ml_risk_filter_enabled and payload.symbol in self.settings.ml_risk_filter_symbol_list:
            ml_filter_result = await self._evaluate_ml_filter(
                payload=payload,
                strategy_signal=strategy_result.signal,
            )
            if (
                allowed
                and ml_filter_result.available
                and (
                    ml_filter_result.advisory_signal != MLAdvisorySignal.UP
                    or not ml_filter_result.passes_confidence_threshold
                )
            ):
                allowed = False
                reasons.append(
                    "ML confidence filter did not confirm the long entry with enough confidence."
                )
            elif (
                allowed
                and not ml_filter_result.available
                and self.settings.ml_risk_filter_require_model
            ):
                allowed = False
                reasons.append(
                    f"ML confidence filter is required but unavailable: {ml_filter_result.detail}"
                )

        trade_plan = self._build_trade_plan(strategy_result, payload.account_balance) if allowed else None

        if trade_plan is None and allowed:
            allowed = False
            reasons.append("Risk engine could not build a valid trade plan.")

        if self.settings.risk_require_stop_loss and trade_plan is not None and trade_plan.stop_loss_price is None:
            allowed = False
            reasons.append("Stop-loss is required for every trade in MVP.")
            trade_plan = None

        if self.settings.risk_use_real_trading:
            reasons.append("Real trading is enabled in config, but execution is still out of scope in MVP.")
        else:
            reasons.append("Mode is paper trading only.")

        return RiskEvaluationResponse(
            mode=self.settings.risk_mode,
            allowed=allowed,
            reasons=reasons,
            evaluated_at=datetime.now(tz=UTC),
            strategy=strategy_result,
            trade_plan=trade_plan,
            ml_filter=ml_filter_result,
        )

    async def _evaluate_ml_filter(
        self,
        payload: RiskEvaluationRequest,
        strategy_signal: StrategySignal,
    ) -> RiskMLFilterResult:
        if strategy_signal != StrategySignal.BUY:
            return RiskMLFilterResult(
                enabled=True,
                available=False,
                detail="ML filter skipped because the strategy signal is not BUY.",
            )

        if self.ml_service is None:
            return RiskMLFilterResult(
                enabled=True,
                available=False,
                detail="ML service is not available in the current risk context.",
            )

        try:
            prediction = await self.ml_service.predict(
                MLPredictRequest(
                    exchange=payload.exchange,
                    symbol=payload.symbol,
                    timeframe=payload.timeframe,
                    limit=max(payload.limit, 250),
                    confidence_threshold=self.settings.ml_risk_filter_confidence_threshold,
                )
            )
        except HTTPException as exc:
            return RiskMLFilterResult(
                enabled=True,
                available=False,
                confidence_threshold=self.settings.ml_risk_filter_confidence_threshold,
                detail=str(exc.detail),
            )

        return RiskMLFilterResult(
            enabled=True,
            available=True,
            model_id=prediction.model_id,
            advisory_signal=prediction.advisory_signal,
            probability_up=prediction.probability_up,
            confidence=prediction.confidence,
            passes_confidence_threshold=prediction.passes_confidence_threshold,
            confidence_threshold=prediction.confidence_threshold,
            detail="ML prediction evaluated successfully.",
        )

    def _build_trade_plan(self, strategy_result, account_balance: Decimal) -> TradePlan | None:
        latest = strategy_result.latest_indicators

        if latest.atr is None or latest.atr <= 0:
            return None

        entry_price = Decimal(str(latest.close_price))
        atr_value = Decimal(str(latest.atr))
        stop_distance = atr_value * Decimal(str(self.settings.risk_atr_stop_multiplier))
        stop_loss = entry_price - stop_distance

        if stop_loss <= 0:
            return None

        trade_risk_per_unit = entry_price - stop_loss
        if trade_risk_per_unit <= 0:
            return None

        account_risk_amount = (
            Decimal(str(account_balance))
            * Decimal(str(self.settings.risk_per_trade_percent))
            / Decimal("100")
        )
        position_size = (account_risk_amount / trade_risk_per_unit).quantize(DECIMAL_8, rounding=ROUND_DOWN)

        take_profit = entry_price + (
            trade_risk_per_unit * Decimal(str(self.settings.risk_reward_to_risk_ratio))
        )

        return TradePlan(
            side=StrategySignal.BUY,
            entry_price=entry_price,
            stop_loss_price=stop_loss.quantize(DECIMAL_8, rounding=ROUND_DOWN),
            take_profit_price=take_profit.quantize(DECIMAL_8, rounding=ROUND_DOWN),
            position_size=position_size,
            account_risk_amount=account_risk_amount.quantize(DECIMAL_8, rounding=ROUND_DOWN),
            trade_risk_per_unit=trade_risk_per_unit.quantize(DECIMAL_8, rounding=ROUND_DOWN),
            estimated_slippage_percent=Decimal(str(self.settings.risk_slippage_percent)),
            estimated_fee_percent=Decimal(str(self.settings.risk_fee_percent)),
        )
