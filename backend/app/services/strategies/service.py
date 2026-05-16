from datetime import UTC, datetime

from fastapi import HTTPException, status

from app.core.config import get_settings
from app.schemas.strategy import (
    StrategyEvaluationRequest,
    StrategyEvaluationResponse,
)
from app.services.indicators.service import IndicatorService
from app.services.strategies.rsi_ema_trend import RsiEmaTrendStrategy


class StrategyService:
    def __init__(self, indicator_service: IndicatorService):
        self.indicator_service = indicator_service
        self.settings = get_settings()
        self.strategies = {
            "rsi_ema_trend_v1": RsiEmaTrendStrategy(
                name="rsi_ema_trend_v1",
                trend_period=200,
                buy_rsi_max=self.settings.strategy_rsi_ema_v1_buy_rsi_max,
                sell_rsi_min=self.settings.strategy_rsi_ema_v1_sell_rsi_min,
                require_macd_improving=self.settings.strategy_rsi_ema_v1_require_macd_improving,
            ),
            "rsi_ema_trend_v2": RsiEmaTrendStrategy(
                name="rsi_ema_trend_v2",
                trend_period=200,
                buy_rsi_max=self.settings.strategy_rsi_ema_v2_buy_rsi_max,
                sell_rsi_min=self.settings.strategy_rsi_ema_v2_sell_rsi_min,
                require_macd_improving=self.settings.strategy_rsi_ema_v2_require_macd_improving,
            ),
            "rsi_ema_trend_multi_v1": RsiEmaTrendStrategy(
                name="rsi_ema_trend_multi_v1",
                trend_period=self.settings.strategy_rsi_ema_multi_v1_trend_period,
                buy_rsi_max=self.settings.strategy_rsi_ema_multi_v1_buy_rsi_max,
                sell_rsi_min=self.settings.strategy_rsi_ema_multi_v1_sell_rsi_min,
                require_macd_improving=self.settings.strategy_rsi_ema_multi_v1_require_macd_improving,
            ),
        }

    async def evaluate(self, payload: StrategyEvaluationRequest) -> StrategyEvaluationResponse:
        return await self.evaluate_strategy_inputs(
            exchange=payload.exchange,
            symbol=payload.symbol,
            timeframe=payload.timeframe,
            limit=payload.limit,
            strategy_name=payload.strategy_name,
        )

    async def evaluate_strategy_inputs(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        limit: int,
        strategy_name: str,
    ) -> StrategyEvaluationResponse:
        resolved_strategy_name = self.resolve_strategy_name(symbol=symbol, strategy_name=strategy_name)
        strategy = self.strategies.get(resolved_strategy_name)
        if strategy is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Strategy '{resolved_strategy_name}' is not available.",
            )

        indicator_response = await self.indicator_service.get_indicator_snapshot(
            exchange_slug=exchange,
            symbol=symbol,
            timeframe=timeframe,
            limit=limit,
        )

        if not indicator_response.indicators:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No candles available for strategy evaluation.",
            )

        latest = indicator_response.indicators[-1]
        previous = indicator_response.indicators[-2] if len(indicator_response.indicators) > 1 else None
        signal, reasons = strategy.evaluate(latest=latest, previous=previous)

        return StrategyEvaluationResponse(
            strategy_name=resolved_strategy_name,
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            signal=signal,
            reasons=reasons,
            candle_count=indicator_response.candle_count,
            evaluated_at=datetime.now(tz=UTC),
            latest_close_price=latest.close_price,
            latest_indicators=latest,
        )

    def resolve_strategy_name(self, symbol: str, strategy_name: str | None) -> str:
        if strategy_name and strategy_name != self.settings.strategy_default_name:
            return strategy_name
        return self.settings.strategy_symbol_override_map.get(symbol, self.settings.strategy_default_name)
