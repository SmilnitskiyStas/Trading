from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, ROUND_DOWN
from math import sqrt

from fastapi import HTTPException, status

from app.repositories.candle_repository import CandleRepository
from app.repositories.exchange_repository import ExchangeRepository
from app.repositories.trading_pair_repository import TradingPairRepository
from app.schemas.backtesting import BacktestMetrics, BacktestRequest, BacktestResponse, BacktestTrade
from app.schemas.risk import TradePlan
from app.schemas.strategy import StrategySignal
from app.services.indicators.service import IndicatorService
from app.services.risk.service import DECIMAL_8, RiskService


@dataclass
class OpenPosition:
    opened_at: object
    entry_price: Decimal
    stop_loss_price: Decimal
    take_profit_price: Decimal
    position_size: Decimal


class BacktestingService:
    def __init__(
        self,
        exchange_repository: ExchangeRepository,
        trading_pair_repository: TradingPairRepository,
        candle_repository: CandleRepository,
        risk_service: RiskService,
    ):
        self.exchange_repository = exchange_repository
        self.trading_pair_repository = trading_pair_repository
        self.candle_repository = candle_repository
        self.risk_service = risk_service

    async def run_backtest(self, payload: BacktestRequest) -> BacktestResponse:
        exchange = await self.exchange_repository.get_by_slug(payload.exchange)
        if exchange is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exchange is not configured.")

        trading_pair = await self.trading_pair_repository.get_by_exchange_and_symbol(exchange.id, payload.symbol)
        if trading_pair is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trading pair is not configured.")

        candles = await self.candle_repository.list_history(
            trading_pair_id=trading_pair.id,
            timeframe=payload.timeframe,
            limit=payload.limit,
        )
        if len(candles) < 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Not enough candles to run a backtest. Load more history first.",
            )

        indicator_snapshots = IndicatorService.calculate_snapshots(candles)
        resolved_strategy_name = self.risk_service.strategy_service.resolve_strategy_name(
            symbol=payload.symbol,
            strategy_name=payload.strategy_name,
        )
        strategy = self.risk_service.strategy_service.strategies.get(resolved_strategy_name)
        if strategy is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Strategy '{resolved_strategy_name}' is not available.",
            )

        balance = Decimal(payload.initial_balance)
        peak_balance = balance
        open_position: OpenPosition | None = None
        trades: list[BacktestTrade] = []
        trade_returns: list[float] = []
        daily_realized_pnl: dict[date, Decimal] = {}

        for index, candle in enumerate(candles):
            current_day = candle.open_time.date()
            daily_pnl = daily_realized_pnl.get(current_day, Decimal("0"))
            current_drawdown_percent = self._drawdown_percent(balance, peak_balance)
            current_daily_loss_percent = self._daily_loss_percent(
                daily_pnl=daily_pnl,
                initial_balance=Decimal(payload.initial_balance),
            )
            latest = indicator_snapshots[index]
            previous = indicator_snapshots[index - 1] if index > 0 else None
            signal, _ = strategy.evaluate(latest=latest, previous=previous)

            if open_position is not None:
                closed_trade = self._try_close_position(
                    candle=candle,
                    open_position=open_position,
                    initial_balance=Decimal(payload.initial_balance),
                    signal=signal,
                )
                if closed_trade is not None:
                    trades.append(closed_trade)
                    balance += closed_trade.pnl
                    peak_balance = max(peak_balance, balance)
                    trade_returns.append(float(closed_trade.pnl_percent) / 100)
                    daily_realized_pnl[current_day] = daily_pnl + closed_trade.pnl
                    open_position = None
                    current_drawdown_percent = self._drawdown_percent(balance, peak_balance)
                    current_daily_loss_percent = self._daily_loss_percent(
                        daily_pnl=daily_realized_pnl[current_day],
                        initial_balance=Decimal(payload.initial_balance),
                    )

            if open_position is not None:
                continue

            if signal != StrategySignal.BUY:
                continue

            trade_plan = self.risk_service._build_trade_plan(  # noqa: SLF001
                self._make_strategy_result(payload, latest, signal),
                balance,
            )

            if not self._risk_allows_entry(
                payload=payload,
                signal=signal,
                balance=balance,
                daily_loss_percent=current_daily_loss_percent,
                drawdown_percent=current_drawdown_percent,
                trade_plan=trade_plan,
            ):
                continue

            if trade_plan is None:
                continue

            open_position = self._open_position(candle=candle, trade_plan=trade_plan)

        if open_position is not None:
            final_candle = candles[-1]
            forced_trade = self._close_at_market(
                candle=final_candle,
                open_position=open_position,
                initial_balance=Decimal(payload.initial_balance),
                exit_reason="end_of_backtest",
            )
            trades.append(forced_trade)
            balance += forced_trade.pnl
            trade_returns.append(float(forced_trade.pnl_percent) / 100)

        metrics = self._build_metrics(
            initial_balance=Decimal(payload.initial_balance),
            ending_balance=balance,
            trades=trades,
            trade_returns=trade_returns,
        )

        return BacktestResponse(
            exchange=payload.exchange,
            symbol=payload.symbol,
            timeframe=payload.timeframe,
            strategy_name=resolved_strategy_name,
            initial_balance=Decimal(payload.initial_balance),
            metrics=metrics,
            trades=trades,
        )

    def _risk_allows_entry(
        self,
        payload: BacktestRequest,
        signal: StrategySignal,
        balance: Decimal,
        daily_loss_percent: Decimal,
        drawdown_percent: Decimal,
        trade_plan: TradePlan | None,
    ) -> bool:
        if signal != StrategySignal.BUY:
            return False
        if payload.symbol not in self.risk_service.settings.market_data_symbol_list:
            return False
        if payload.timeframe not in self.risk_service.settings.market_data_timeframe_list:
            return False
        if daily_loss_percent >= Decimal(str(self.risk_service.settings.risk_max_daily_loss_percent)):
            return False
        if drawdown_percent >= Decimal(str(self.risk_service.settings.risk_max_total_drawdown_percent)):
            return False
        if trade_plan is None:
            return False
        return True

    def _open_position(self, candle, trade_plan: TradePlan) -> OpenPosition:
        slippage_rate = Decimal(str(self.risk_service.settings.risk_slippage_percent)) / Decimal("100")
        entry_price = (
            trade_plan.entry_price * (Decimal("1") + slippage_rate)
        ).quantize(DECIMAL_8, rounding=ROUND_DOWN)
        return OpenPosition(
            opened_at=candle.close_time,
            entry_price=entry_price,
            stop_loss_price=trade_plan.stop_loss_price or Decimal("0"),
            take_profit_price=trade_plan.take_profit_price or Decimal("0"),
            position_size=trade_plan.position_size or Decimal("0"),
        )

    def _try_close_position(
        self,
        candle,
        open_position: OpenPosition,
        initial_balance: Decimal,
        signal: StrategySignal,
    ) -> BacktestTrade | None:
        exit_reason = None
        raw_exit_price: Decimal | None = None

        low_price = Decimal(str(candle.low_price))
        high_price = Decimal(str(candle.high_price))
        close_price = Decimal(str(candle.close_price))

        if low_price <= open_position.stop_loss_price:
            exit_reason = "stop_loss"
            raw_exit_price = open_position.stop_loss_price
        elif high_price >= open_position.take_profit_price:
            exit_reason = "take_profit"
            raw_exit_price = open_position.take_profit_price
        elif signal == StrategySignal.SELL:
            exit_reason = "strategy_sell"
            raw_exit_price = close_price
        else:
            return None

        return self._build_closed_trade(
            candle=candle,
            open_position=open_position,
            initial_balance=initial_balance,
            raw_exit_price=raw_exit_price,
            exit_reason=exit_reason,
        )

    def _close_at_market(
        self,
        candle,
        open_position: OpenPosition,
        initial_balance: Decimal,
        exit_reason: str,
    ) -> BacktestTrade:
        close_price = Decimal(str(candle.close_price))
        return self._build_closed_trade(
            candle=candle,
            open_position=open_position,
            initial_balance=initial_balance,
            raw_exit_price=close_price,
            exit_reason=exit_reason,
        )

    def _build_closed_trade(
        self,
        candle,
        open_position: OpenPosition,
        initial_balance: Decimal,
        raw_exit_price: Decimal,
        exit_reason: str,
    ) -> BacktestTrade:
        slippage_rate = Decimal(str(self.risk_service.settings.risk_slippage_percent)) / Decimal("100")
        exit_price = (raw_exit_price * (Decimal("1") - slippage_rate)).quantize(DECIMAL_8, rounding=ROUND_DOWN)

        fee_rate = Decimal(str(self.risk_service.settings.risk_fee_percent)) / Decimal("100")
        entry_fee = open_position.entry_price * open_position.position_size * fee_rate
        exit_fee = exit_price * open_position.position_size * fee_rate
        fees_paid = (entry_fee + exit_fee).quantize(DECIMAL_8, rounding=ROUND_DOWN)

        gross_pnl = (exit_price - open_position.entry_price) * open_position.position_size
        pnl = (gross_pnl - fees_paid).quantize(DECIMAL_8, rounding=ROUND_DOWN)
        pnl_percent = ((pnl / initial_balance) * Decimal("100")).quantize(DECIMAL_8, rounding=ROUND_DOWN)

        return BacktestTrade(
            opened_at=open_position.opened_at,
            closed_at=candle.close_time,
            entry_price=open_position.entry_price,
            exit_price=exit_price,
            stop_loss_price=open_position.stop_loss_price,
            take_profit_price=open_position.take_profit_price,
            position_size=open_position.position_size,
            fees_paid=fees_paid,
            pnl=pnl,
            pnl_percent=pnl_percent,
            exit_reason=exit_reason,
        )

    def _build_metrics(
        self,
        initial_balance: Decimal,
        ending_balance: Decimal,
        trades: list[BacktestTrade],
        trade_returns: list[float],
    ) -> BacktestMetrics:
        total_trades = len(trades)
        winning_trades = sum(1 for trade in trades if trade.pnl > 0)
        losing_trades = sum(1 for trade in trades if trade.pnl < 0)
        gross_profit = sum((trade.pnl for trade in trades if trade.pnl > 0), start=Decimal("0"))
        gross_loss = sum((abs(trade.pnl) for trade in trades if trade.pnl < 0), start=Decimal("0"))
        total_return_percent = (
            ((ending_balance - initial_balance) / initial_balance) * Decimal("100")
        ).quantize(DECIMAL_8, rounding=ROUND_DOWN)
        win_rate_percent = (
            (Decimal(winning_trades) / Decimal(total_trades) * Decimal("100"))
            if total_trades
            else Decimal("0")
        ).quantize(DECIMAL_8, rounding=ROUND_DOWN)
        profit_factor = (
            (gross_profit / gross_loss).quantize(DECIMAL_8, rounding=ROUND_DOWN)
            if gross_loss > 0
            else Decimal("0")
        )
        sharpe_ratio = Decimal(str(self._sharpe_ratio(trade_returns))).quantize(DECIMAL_8, rounding=ROUND_DOWN)
        max_drawdown_percent = self._max_drawdown_percent(initial_balance, trades)

        return BacktestMetrics(
            total_return_percent=total_return_percent,
            ending_balance=ending_balance.quantize(DECIMAL_8, rounding=ROUND_DOWN),
            max_drawdown_percent=max_drawdown_percent,
            win_rate_percent=win_rate_percent,
            profit_factor=profit_factor,
            sharpe_ratio=sharpe_ratio,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
        )

    def _max_drawdown_percent(self, initial_balance: Decimal, trades: list[BacktestTrade]) -> Decimal:
        equity = initial_balance
        peak = initial_balance
        max_drawdown = Decimal("0")

        for trade in trades:
            equity += trade.pnl
            peak = max(peak, equity)
            drawdown = self._drawdown_percent(equity, peak)
            max_drawdown = max(max_drawdown, drawdown)

        return max_drawdown.quantize(DECIMAL_8, rounding=ROUND_DOWN)

    @staticmethod
    def _drawdown_percent(balance: Decimal, peak_balance: Decimal) -> Decimal:
        if peak_balance <= 0:
            return Decimal("0")
        return ((peak_balance - balance) / peak_balance) * Decimal("100")

    @staticmethod
    def _daily_loss_percent(daily_pnl: Decimal, initial_balance: Decimal) -> Decimal:
        if daily_pnl >= 0 or initial_balance <= 0:
            return Decimal("0")
        return (abs(daily_pnl) / initial_balance) * Decimal("100")

    @staticmethod
    def _sharpe_ratio(returns: list[float]) -> float:
        if len(returns) < 2:
            return 0.0
        average = sum(returns) / len(returns)
        variance = sum((value - average) ** 2 for value in returns) / (len(returns) - 1)
        standard_deviation = variance ** 0.5
        if standard_deviation == 0:
            return 0.0
        return (average / standard_deviation) * sqrt(len(returns))

    @staticmethod
    def _make_strategy_result(payload: BacktestRequest, latest, signal: StrategySignal):
        from app.schemas.strategy import StrategyEvaluationResponse

        return StrategyEvaluationResponse(
            strategy_name=payload.strategy_name,
            exchange=payload.exchange,
            symbol=payload.symbol,
            timeframe=payload.timeframe,
            signal=signal,
            reasons=[],
            candle_count=0,
            evaluated_at=datetime.now(tz=UTC),
            latest_close_price=latest.close_price,
            latest_indicators=latest,
        )
