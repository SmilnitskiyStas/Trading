from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from math import sqrt

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.candle import Candle
from app.models.exchange import Exchange
from app.models.trading_pair import TradingPair
from app.services.indicators.service import IndicatorService


DECIMAL_8 = Decimal("0.00000001")


@dataclass
class Config:
    name: str
    trend_period: int
    buy_rsi: float
    sell_rsi: float
    atr_multiplier: float
    reward_to_risk: float
    require_macd_improving: bool


@dataclass
class OpenTrade:
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    position_size: Decimal


async def load_candles(symbol: str, timeframe: str, limit: int) -> list[Candle]:
    async with SessionLocal() as session:
        exchange = (
            await session.execute(select(Exchange).where(Exchange.slug == "binance"))
        ).scalar_one()
        trading_pair = (
            await session.execute(
                select(TradingPair).where(
                    TradingPair.exchange_id == exchange.id,
                    TradingPair.symbol == symbol,
                )
            )
        ).scalar_one()
        result = await session.execute(
            select(Candle)
            .where(
                Candle.trading_pair_id == trading_pair.id,
                Candle.timeframe == timeframe,
            )
            .order_by(Candle.open_time.asc())
            .limit(limit)
        )
        return list(result.scalars().all())


def ema(values: list[float], period: int) -> list[float | None]:
    result: list[float | None] = [None] * len(values)
    if len(values) < period:
        return result
    seed = sum(values[:period]) / period
    result[period - 1] = seed
    multiplier = 2 / (period + 1)
    previous = seed
    for idx in range(period, len(values)):
        current = (values[idx] - previous) * multiplier + previous
        result[idx] = current
        previous = current
    return result


def simulate(
    candles: list[Candle],
    trend_values: list[float | None],
    config: Config,
    initial_balance: Decimal = Decimal("1000"),
    risk_per_trade_percent: Decimal = Decimal("1"),
    slippage_percent: Decimal = Decimal("0.05"),
    fee_percent: Decimal = Decimal("0.1"),
) -> dict:
    snapshots = IndicatorService.calculate_snapshots(candles)
    balance = initial_balance
    peak = initial_balance
    trades = []
    returns = []
    open_trade: OpenTrade | None = None

    for idx, candle in enumerate(candles):
        snap = snapshots[idx]
        prev = snapshots[idx - 1] if idx > 0 else None

        if open_trade is not None:
            low = Decimal(str(candle.low_price))
            high = Decimal(str(candle.high_price))
            close = Decimal(str(candle.close_price))

            exit_reason = None
            raw_exit = None
            if low <= open_trade.stop_loss:
                exit_reason = "stop_loss"
                raw_exit = open_trade.stop_loss
            elif high >= open_trade.take_profit:
                exit_reason = "take_profit"
                raw_exit = open_trade.take_profit
            elif snap.rsi is not None and snap.ema_slow is not None and snap.rsi > config.sell_rsi and float(close) < snap.ema_slow:
                exit_reason = "strategy_sell"
                raw_exit = close

            if raw_exit is not None:
                exit_price = (raw_exit * (Decimal("1") - slippage_percent / Decimal("100"))).quantize(DECIMAL_8, rounding=ROUND_DOWN)
                fee_rate = fee_percent / Decimal("100")
                entry_fee = open_trade.entry_price * open_trade.position_size * fee_rate
                exit_fee = exit_price * open_trade.position_size * fee_rate
                fees = (entry_fee + exit_fee).quantize(DECIMAL_8, rounding=ROUND_DOWN)
                pnl = ((exit_price - open_trade.entry_price) * open_trade.position_size - fees).quantize(DECIMAL_8, rounding=ROUND_DOWN)
                balance += pnl
                peak = max(peak, balance)
                trades.append(float(pnl))
                returns.append(float((pnl / initial_balance)))
                open_trade = None
                continue

        if open_trade is not None:
            continue

        trend = trend_values[idx]
        if trend is None or snap.rsi is None or snap.macd_histogram is None or snap.atr is None:
            continue

        macd_improving = prev is not None and prev.macd_histogram is not None and snap.macd_histogram > prev.macd_histogram
        if config.require_macd_improving and not macd_improving:
            continue

        close = Decimal(str(snap.close_price))
        if float(close) <= trend:
            continue
        if snap.rsi >= config.buy_rsi:
            continue

        atr_value = Decimal(str(snap.atr))
        stop_distance = atr_value * Decimal(str(config.atr_multiplier))
        stop_loss = close - stop_distance
        if stop_loss <= 0:
            continue
        risk_per_unit = close - stop_loss
        account_risk = balance * risk_per_trade_percent / Decimal("100")
        position_size = (account_risk / risk_per_unit).quantize(DECIMAL_8, rounding=ROUND_DOWN)
        take_profit = close + (risk_per_unit * Decimal(str(config.reward_to_risk)))
        entry = (close * (Decimal("1") + slippage_percent / Decimal("100"))).quantize(DECIMAL_8, rounding=ROUND_DOWN)
        open_trade = OpenTrade(entry_price=entry, stop_loss=stop_loss, take_profit=take_profit, position_size=position_size)

    gross_profit = sum(p for p in trades if p > 0)
    gross_loss = abs(sum(p for p in trades if p < 0))
    total_return = float((balance - initial_balance) / initial_balance * Decimal("100"))
    win_count = sum(1 for p in trades if p > 0)
    total = len(trades)
    win_rate = (win_count / total * 100) if total else 0.0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0.0
    max_drawdown = float((((peak - balance) / peak) * Decimal("100")) if peak > 0 else Decimal("0"))
    sharpe = 0.0
    if len(returns) > 1:
        avg = sum(returns) / len(returns)
        var = sum((r - avg) ** 2 for r in returns) / (len(returns) - 1)
        std = var ** 0.5
        if std > 0:
            sharpe = (avg / std) * sqrt(len(returns))

    return {
        "name": config.name,
        "total_return_percent": round(total_return, 4),
        "ending_balance": float(balance),
        "win_rate_percent": round(win_rate, 4),
        "profit_factor": round(profit_factor, 4),
        "max_drawdown_percent": round(max_drawdown, 4),
        "sharpe_ratio": round(sharpe, 4),
        "total_trades": total,
    }


async def main() -> None:
    symbol = "BTC/USDT"
    timeframe = "1h"
    candles = await load_candles(symbol, timeframe, 1000)
    closes = [float(c.close_price) for c in candles]

    configs = []
    for trend_period in (100, 150, 200):
        trend_values = ema(closes, trend_period)
        for buy_rsi in (32, 35, 38, 40, 42):
            for sell_rsi in (58, 60, 62, 65):
                for atr_mult in (1.25, 1.5, 1.75, 2.0):
                    for rr in (1.5, 2.0, 2.5):
                        for macd_rule in (True, False):
                            name = f"trend{trend_period}_buy{buy_rsi}_sell{sell_rsi}_atr{atr_mult}_rr{rr}_macd{int(macd_rule)}"
                            cfg = Config(name, trend_period, buy_rsi, sell_rsi, atr_mult, rr, macd_rule)
                            result = simulate(candles, trend_values, cfg)
                            result["trend_period"] = trend_period
                            result["buy_rsi"] = buy_rsi
                            result["sell_rsi"] = sell_rsi
                            result["atr_multiplier"] = atr_mult
                            result["reward_to_risk"] = rr
                            result["require_macd_improving"] = macd_rule
                            configs.append(result)

    configs.sort(
        key=lambda item: (
            item["total_return_percent"],
            item["profit_factor"],
            item["sharpe_ratio"],
            -item["max_drawdown_percent"],
            item["total_trades"],
        ),
        reverse=True,
    )
    print(json.dumps(configs[:20], indent=2))


if __name__ == "__main__":
    asyncio.run(main())
