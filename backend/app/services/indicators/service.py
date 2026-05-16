from app.schemas.indicators import IndicatorResponse, IndicatorSnapshot
from app.core.config import get_settings
from app.services.indicators.calculations import atr, ema, macd, rsi
from app.services.market_data.service import MarketDataService


class IndicatorService:
    def __init__(self, market_data_service: MarketDataService):
        self.market_data_service = market_data_service
        self.settings = get_settings()

    async def get_indicator_snapshot(
        self,
        exchange_slug: str,
        symbol: str,
        timeframe: str,
        limit: int,
    ) -> IndicatorResponse:
        candles = await self.market_data_service.list_candles(
            exchange_slug=exchange_slug,
            symbol=symbol,
            timeframe=timeframe,
            limit=limit,
        )
        snapshots = self.calculate_snapshots(candles)

        return IndicatorResponse(
            exchange=exchange_slug,
            symbol=symbol,
            timeframe=timeframe,
            candle_count=len(candles),
            indicators=snapshots,
        )

    @staticmethod
    def calculate_snapshots(candles) -> list[IndicatorSnapshot]:
        settings = get_settings()
        closes = [float(candle.close_price) for candle in candles]
        highs = [float(candle.high_price) for candle in candles]
        lows = [float(candle.low_price) for candle in candles]
        trend_periods = sorted({100, 200, settings.strategy_rsi_ema_multi_v1_trend_period})

        ema_fast_values = ema(closes, period=20)
        ema_slow_values = ema(closes, period=50)
        ema_trend_series = {
            period: ema(closes, period=period)
            for period in trend_periods
        }
        rsi_values = rsi(closes, period=14)
        macd_line, macd_signal, macd_histogram = macd(closes, 12, 26, 9)
        atr_values = atr(highs, lows, closes, period=14)

        return [
            IndicatorSnapshot(
                open_time=candle.open_time,
                close_time=candle.close_time,
                close_price=candle.close_price,
                ema_fast=ema_fast_values[index],
                ema_slow=ema_slow_values[index],
                ema_trend=ema_trend_series[200][index] if 200 in ema_trend_series else None,
                ema_by_period={
                    period: values[index]
                    for period, values in ema_trend_series.items()
                },
                rsi=rsi_values[index],
                macd=macd_line[index],
                macd_signal=macd_signal[index],
                macd_histogram=macd_histogram[index],
                atr=atr_values[index],
            )
            for index, candle in enumerate(candles)
        ]
