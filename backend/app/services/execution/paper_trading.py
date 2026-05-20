from decimal import Decimal, ROUND_DOWN
from itertools import groupby

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.paper_trade import PaperTrade
from app.repositories.candle_repository import CandleRepository
from app.repositories.exchange_repository import ExchangeRepository
from app.repositories.paper_account_repository import PaperAccountRepository
from app.repositories.paper_trade_repository import PaperTradeRepository
from app.repositories.system_event_repository import SystemEventRepository
from app.repositories.trading_pair_repository import TradingPairRepository
from app.schemas.paper_trading import (
    PaperAccountRead,
    PaperTradingPerformanceRead,
    PaperTradingPerformanceByDayRead,
    PaperTradingPerformanceBySymbolRead,
    PaperTradingTestStatusRead,
    PaperTradeRead,
    PaperTradingCycleRequest,
    PaperTradingCycleResponse,
)
from app.schemas.risk import RiskEvaluationRequest
from app.schemas.strategy import StrategySignal
from app.services.risk.service import DECIMAL_8, RiskService
from app.services.notifications.telegram import TelegramNotifier
from app.services.operations.event_log import EventLogService


class PaperTradingService:
    def __init__(self, session: AsyncSession, risk_service: RiskService):
        self.session = session
        self.risk_service = risk_service
        self.exchange_repository = ExchangeRepository(session)
        self.trading_pair_repository = TradingPairRepository(session)
        self.candle_repository = CandleRepository(session)
        self.paper_account_repository = PaperAccountRepository(session)
        self.paper_trade_repository = PaperTradeRepository(session)
        self.event_repository = SystemEventRepository(session)
        self.event_log_service = EventLogService(self.event_repository)
        self.telegram_notifier = TelegramNotifier()

    async def run_cycle(self, payload: PaperTradingCycleRequest) -> PaperTradingCycleResponse:
        exchange = await self.exchange_repository.get_by_slug(payload.exchange)
        if exchange is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exchange is not configured.")

        trading_pair = await self.trading_pair_repository.get_by_exchange_and_symbol(exchange.id, payload.symbol)
        if trading_pair is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trading pair is not configured.")

        account = await self.paper_account_repository.get_or_create(
            name=payload.account_name,
            initial_balance=Decimal(str(self.risk_service.settings.risk_initial_balance)),
        )

        candles = await self.candle_repository.list_history(
            trading_pair_id=trading_pair.id,
            timeframe=payload.timeframe,
            limit=max(payload.limit, 2),
        )
        if not candles:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No candles available for paper trading.")
        latest_candle = candles[-1]

        open_positions_count = await self.paper_trade_repository.count_open_positions(account.id)
        open_trade = await self.paper_trade_repository.get_open_trade_for_symbol(
            account_id=account.id,
            trading_pair_id=trading_pair.id,
            timeframe=payload.timeframe,
        )

        resolved_strategy_name = self.risk_service.strategy_service.resolve_paper_strategy_name(
            symbol=payload.symbol,
            strategy_name=payload.strategy_name,
        )

        strategy_result = await self.risk_service.strategy_service.evaluate_strategy_inputs(
            exchange=payload.exchange,
            symbol=payload.symbol,
            timeframe=payload.timeframe,
            limit=payload.limit,
            strategy_name=resolved_strategy_name,
        )
        resolved_strategy_name = strategy_result.strategy_name

        if open_trade is not None:
            closed = self._maybe_close_trade(open_trade, latest_candle, strategy_result.signal)
            if closed is not None:
                account.current_balance = (
                    Decimal(str(account.current_balance)) + Decimal(str(closed.realized_pnl))
                ).quantize(DECIMAL_8, rounding=ROUND_DOWN)
                await self.event_log_service.record(
                    event_type="paper_trade_closed",
                    level="info",
                    message=f"Paper trade closed for {payload.symbol} on {payload.timeframe}.",
                    payload={
                        "account_name": payload.account_name,
                        "symbol": payload.symbol,
                        "timeframe": payload.timeframe,
                        "exit_reason": closed.exit_reason,
                        "realized_pnl": str(closed.realized_pnl),
                    },
                    account_id=account.id,
                    paper_trade_id=closed.id,
                )
                await self.telegram_notifier.send_message(
                    self._format_closed_trade_message(payload.symbol, closed)
                )
                await self.session.commit()
                return PaperTradingCycleResponse(
                    account=PaperAccountRead.model_validate(account),
                    action="CLOSED_POSITION",
                    reasons=[f"Trade closed by {closed.exit_reason}."],
                    trade=PaperTradeRead.model_validate(closed),
                )

            await self.event_log_service.record(
                event_type="paper_cycle_no_action",
                level="info",
                message=f"No paper trading action taken for {payload.symbol}; open position remains active.",
                payload={
                    "account_name": payload.account_name,
                    "symbol": payload.symbol,
                    "timeframe": payload.timeframe,
                },
                account_id=account.id,
                paper_trade_id=open_trade.id,
            )
            await self.session.commit()
            return PaperTradingCycleResponse(
                account=PaperAccountRead.model_validate(account),
                action="NO_ACTION",
                reasons=["An open position already exists and its exit conditions did not trigger."],
                trade=PaperTradeRead.model_validate(open_trade),
            )

        risk_result = await self.risk_service.evaluate(
            RiskEvaluationRequest(
                exchange=payload.exchange,
                symbol=payload.symbol,
                timeframe=payload.timeframe,
                limit=payload.limit,
                strategy_name=resolved_strategy_name,
                account_balance=Decimal(str(account.current_balance)),
                current_daily_loss_percent=Decimal("0"),
                current_drawdown_percent=self._current_drawdown_percent(account),
                open_positions_count=open_positions_count,
                has_open_position_for_symbol=False,
                market_data_is_fresh=True,
                exchange_api_healthy=True,
            )
        )

        if not risk_result.allowed or risk_result.trade_plan is None:
            await self.event_log_service.record(
                event_type="paper_trade_blocked",
                level="warning",
                message=f"Paper trade blocked for {payload.symbol}.",
                payload={
                    "account_name": payload.account_name,
                    "symbol": payload.symbol,
                    "timeframe": payload.timeframe,
                    "reasons": risk_result.reasons,
                },
                account_id=account.id,
            )
            await self.session.commit()
            return PaperTradingCycleResponse(
                account=PaperAccountRead.model_validate(account),
                action="NO_ACTION",
                reasons=risk_result.reasons,
                trade=None,
            )

        created_trade = await self.paper_trade_repository.create(
            self._build_open_trade(
                account_id=account.id,
                trading_pair_id=trading_pair.id,
                payload=payload,
                strategy_name=resolved_strategy_name,
                latest_candle=latest_candle,
                trade_plan=risk_result.trade_plan,
            )
        )
        await self.event_log_service.record(
            event_type="paper_trade_opened",
            level="info",
            message=f"Paper trade opened for {payload.symbol} on {payload.timeframe}.",
            payload={
                "account_name": payload.account_name,
                "symbol": payload.symbol,
                "timeframe": payload.timeframe,
                "entry_price": str(created_trade.entry_price),
                "stop_loss_price": str(created_trade.stop_loss_price),
                "take_profit_price": str(created_trade.take_profit_price),
                "position_size": str(created_trade.position_size),
            },
            account_id=account.id,
            paper_trade_id=created_trade.id,
        )
        await self.telegram_notifier.send_message(
            self._format_open_trade_message(payload.symbol, created_trade)
        )
        await self.session.commit()

        return PaperTradingCycleResponse(
            account=PaperAccountRead.model_validate(account),
            action="OPENED_POSITION",
            reasons=risk_result.reasons,
            trade=PaperTradeRead.model_validate(created_trade),
        )

    async def get_account(self, account_name: str) -> PaperAccountRead:
        account = await self.paper_account_repository.get_or_create(
            name=account_name,
            initial_balance=Decimal(str(self.risk_service.settings.risk_initial_balance)),
        )
        await self.session.commit()
        return PaperAccountRead.model_validate(account)

    async def list_trades(self, account_name: str, limit: int = 100) -> list[PaperTradeRead]:
        account = await self.paper_account_repository.get_or_create(
            name=account_name,
            initial_balance=Decimal(str(self.risk_service.settings.risk_initial_balance)),
        )
        trades = await self.paper_trade_repository.list_recent(account.id, limit)
        await self.session.commit()
        return [PaperTradeRead.model_validate(trade) for trade in trades]

    async def get_performance(self, account_name: str) -> PaperTradingPerformanceRead:
        account = await self.paper_account_repository.get_or_create(
            name=account_name,
            initial_balance=Decimal(str(self.risk_service.settings.risk_initial_balance)),
        )
        trades = await self.paper_trade_repository.list_all_for_account(account.id)
        closed_trades = [trade for trade in trades if trade.status == "CLOSED"]
        open_trades = [trade for trade in trades if trade.status == "OPEN"]
        winning_trades = [trade for trade in closed_trades if Decimal(str(trade.realized_pnl)) > 0]
        losing_trades = [trade for trade in closed_trades if Decimal(str(trade.realized_pnl)) < 0]

        realized_pnl = sum((Decimal(str(trade.realized_pnl)) for trade in closed_trades), start=Decimal("0"))
        initial_balance = Decimal(str(account.initial_balance))
        current_balance = Decimal(str(account.current_balance))
        realized_return_percent = Decimal("0")
        if initial_balance > 0:
            realized_return_percent = ((current_balance - initial_balance) / initial_balance) * Decimal("100")
        current_drawdown_percent = self._current_drawdown_percent(account).quantize(DECIMAL_8, rounding=ROUND_DOWN)
        max_drawdown_percent = self._max_drawdown_percent(
            initial_balance=initial_balance,
            closed_trades=closed_trades,
        ).quantize(DECIMAL_8, rounding=ROUND_DOWN)

        average_win = (
            sum((Decimal(str(trade.realized_pnl)) for trade in winning_trades), start=Decimal("0"))
            / Decimal(len(winning_trades))
            if winning_trades
            else Decimal("0")
        )
        average_loss = (
            sum((abs(Decimal(str(trade.realized_pnl))) for trade in losing_trades), start=Decimal("0"))
            / Decimal(len(losing_trades))
            if losing_trades
            else Decimal("0")
        )
        gross_profit = sum((Decimal(str(trade.realized_pnl)) for trade in winning_trades), start=Decimal("0"))
        gross_loss = sum((abs(Decimal(str(trade.realized_pnl))) for trade in losing_trades), start=Decimal("0"))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else Decimal("0")
        win_rate_percent = (
            (Decimal(len(winning_trades)) / Decimal(len(closed_trades))) * Decimal("100")
            if closed_trades
            else Decimal("0")
        )

        await self.session.commit()
        return PaperTradingPerformanceRead(
            account_name=account.name,
            initial_balance=initial_balance.quantize(DECIMAL_8, rounding=ROUND_DOWN),
            current_balance=current_balance.quantize(DECIMAL_8, rounding=ROUND_DOWN),
            realized_pnl=realized_pnl.quantize(DECIMAL_8, rounding=ROUND_DOWN),
            realized_return_percent=realized_return_percent.quantize(DECIMAL_8, rounding=ROUND_DOWN),
            total_trades=len(trades),
            open_trades=len(open_trades),
            closed_trades=len(closed_trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate_percent=win_rate_percent.quantize(DECIMAL_8, rounding=ROUND_DOWN),
            average_win=average_win.quantize(DECIMAL_8, rounding=ROUND_DOWN),
            average_loss=average_loss.quantize(DECIMAL_8, rounding=ROUND_DOWN),
            profit_factor=profit_factor.quantize(DECIMAL_8, rounding=ROUND_DOWN),
            current_drawdown_percent=current_drawdown_percent,
            max_drawdown_percent=max_drawdown_percent,
        )

    async def get_performance_by_day(self, account_name: str) -> list[PaperTradingPerformanceByDayRead]:
        account = await self.paper_account_repository.get_or_create(
            name=account_name,
            initial_balance=Decimal(str(self.risk_service.settings.risk_initial_balance)),
        )
        trades = await self.paper_trade_repository.list_all_for_account(account.id)
        closed_trades = sorted(
            [trade for trade in trades if trade.status == "CLOSED" and trade.closed_at is not None],
            key=lambda trade: trade.closed_at.date(),
        )

        rows: list[PaperTradingPerformanceByDayRead] = []
        for trading_day, group in groupby(closed_trades, key=lambda trade: trade.closed_at.date()):
            day_trades = list(group)
            wins = [trade for trade in day_trades if Decimal(str(trade.realized_pnl)) > 0]
            losses = [trade for trade in day_trades if Decimal(str(trade.realized_pnl)) < 0]
            realized_pnl = sum((Decimal(str(trade.realized_pnl)) for trade in day_trades), start=Decimal("0"))
            win_rate_percent = (
                (Decimal(len(wins)) / Decimal(len(day_trades))) * Decimal("100")
                if day_trades
                else Decimal("0")
            )
            rows.append(
                PaperTradingPerformanceByDayRead(
                    trading_day=trading_day,
                    closed_trades=len(day_trades),
                    winning_trades=len(wins),
                    losing_trades=len(losses),
                    realized_pnl=realized_pnl.quantize(DECIMAL_8, rounding=ROUND_DOWN),
                    win_rate_percent=win_rate_percent.quantize(DECIMAL_8, rounding=ROUND_DOWN),
                )
            )

        await self.session.commit()
        return list(reversed(rows))

    async def get_performance_by_symbol(self, account_name: str) -> list[PaperTradingPerformanceBySymbolRead]:
        account = await self.paper_account_repository.get_or_create(
            name=account_name,
            initial_balance=Decimal(str(self.risk_service.settings.risk_initial_balance)),
        )
        trades = await self.paper_trade_repository.list_all_for_account(account.id)
        closed_trades = [trade for trade in trades if trade.status == "CLOSED"]
        symbol_map = {
            pair.id: pair.symbol
            for pair in await self.trading_pair_repository.list_by_ids(
                list({trade.trading_pair_id for trade in closed_trades})
            )
        }

        grouped: dict[str, list] = {}
        for trade in closed_trades:
            symbol = symbol_map.get(trade.trading_pair_id, f"pair:{trade.trading_pair_id}")
            grouped.setdefault(symbol, []).append(trade)

        rows: list[PaperTradingPerformanceBySymbolRead] = []
        for symbol, symbol_trades in sorted(grouped.items()):
            wins = [trade for trade in symbol_trades if Decimal(str(trade.realized_pnl)) > 0]
            losses = [trade for trade in symbol_trades if Decimal(str(trade.realized_pnl)) < 0]
            realized_pnl = sum((Decimal(str(trade.realized_pnl)) for trade in symbol_trades), start=Decimal("0"))
            gross_profit = sum((Decimal(str(trade.realized_pnl)) for trade in wins), start=Decimal("0"))
            gross_loss = sum((abs(Decimal(str(trade.realized_pnl))) for trade in losses), start=Decimal("0"))
            profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else Decimal("0")
            win_rate_percent = (
                (Decimal(len(wins)) / Decimal(len(symbol_trades))) * Decimal("100")
                if symbol_trades
                else Decimal("0")
            )
            rows.append(
                PaperTradingPerformanceBySymbolRead(
                    symbol=symbol,
                    closed_trades=len(symbol_trades),
                    winning_trades=len(wins),
                    losing_trades=len(losses),
                    realized_pnl=realized_pnl.quantize(DECIMAL_8, rounding=ROUND_DOWN),
                    win_rate_percent=win_rate_percent.quantize(DECIMAL_8, rounding=ROUND_DOWN),
                    profit_factor=profit_factor.quantize(DECIMAL_8, rounding=ROUND_DOWN),
                )
            )

        await self.session.commit()
        return rows

    async def get_test_status(self, account_name: str) -> PaperTradingTestStatusRead:
        performance = await self.get_performance(account_name=account_name)
        trades = await self.list_trades(account_name=account_name, limit=100)
        day_rows = await self.get_performance_by_day(account_name=account_name)

        closed_trades = [trade for trade in trades if trade.status == "CLOSED"]
        last_closed_trade = max(
            (trade for trade in closed_trades if trade.closed_at is not None),
            key=lambda trade: trade.closed_at,
            default=None,
        )

        phase, pnl_status, ready_for_evaluation, summary = self._resolve_test_status(
            realized_pnl=performance.realized_pnl,
            closed_trades=performance.closed_trades,
            days_with_closed_trades=len(day_rows),
        )

        return PaperTradingTestStatusRead(
            account_name=performance.account_name,
            phase=phase,
            pnl_status=pnl_status,
            ready_for_evaluation=ready_for_evaluation,
            current_balance=performance.current_balance,
            realized_pnl=performance.realized_pnl,
            realized_return_percent=performance.realized_return_percent,
            closed_trades=performance.closed_trades,
            open_trades=performance.open_trades,
            days_with_closed_trades=len(day_rows),
            last_closed_trade_at=last_closed_trade.closed_at if last_closed_trade else None,
            last_closed_trade_pnl=last_closed_trade.realized_pnl if last_closed_trade else None,
            summary=summary,
        )

    def _build_open_trade(self, account_id, trading_pair_id, payload, strategy_name, latest_candle, trade_plan):
        slippage_rate = Decimal(str(self.risk_service.settings.risk_slippage_percent)) / Decimal("100")
        entry_price = (
            Decimal(str(trade_plan.entry_price)) * (Decimal("1") + slippage_rate)
        ).quantize(DECIMAL_8, rounding=ROUND_DOWN)
        return PaperTrade(
            account_id=account_id,
            trading_pair_id=trading_pair_id,
            strategy_name=strategy_name,
            timeframe=payload.timeframe,
            status="OPEN",
            side=trade_plan.side.value,
            entry_price=entry_price,
            exit_price=None,
            stop_loss_price=trade_plan.stop_loss_price,
            take_profit_price=trade_plan.take_profit_price,
            position_size=trade_plan.position_size,
            fees_paid=Decimal("0"),
            realized_pnl=Decimal("0"),
            exit_reason=None,
            opened_at=latest_candle.close_time,
            closed_at=None,
        )

    def _maybe_close_trade(self, trade: PaperTrade, candle, signal: StrategySignal) -> PaperTrade | None:
        low_price = Decimal(str(candle.low_price))
        high_price = Decimal(str(candle.high_price))
        close_price = Decimal(str(candle.close_price))

        raw_exit_price = None
        exit_reason = None

        if low_price <= Decimal(str(trade.stop_loss_price)):
            raw_exit_price = Decimal(str(trade.stop_loss_price))
            exit_reason = "stop_loss"
        elif high_price >= Decimal(str(trade.take_profit_price)):
            raw_exit_price = Decimal(str(trade.take_profit_price))
            exit_reason = "take_profit"
        elif signal == StrategySignal.SELL:
            raw_exit_price = close_price
            exit_reason = "strategy_sell"
        else:
            return None

        slippage_rate = Decimal(str(self.risk_service.settings.risk_slippage_percent)) / Decimal("100")
        exit_price = (raw_exit_price * (Decimal("1") - slippage_rate)).quantize(DECIMAL_8, rounding=ROUND_DOWN)
        fee_rate = Decimal(str(self.risk_service.settings.risk_fee_percent)) / Decimal("100")
        entry_fee = Decimal(str(trade.entry_price)) * Decimal(str(trade.position_size)) * fee_rate
        exit_fee = exit_price * Decimal(str(trade.position_size)) * fee_rate
        fees_paid = (entry_fee + exit_fee).quantize(DECIMAL_8, rounding=ROUND_DOWN)
        gross_pnl = (exit_price - Decimal(str(trade.entry_price))) * Decimal(str(trade.position_size))
        realized_pnl = (gross_pnl - fees_paid).quantize(DECIMAL_8, rounding=ROUND_DOWN)

        trade.exit_price = exit_price
        trade.fees_paid = fees_paid
        trade.realized_pnl = realized_pnl
        trade.exit_reason = exit_reason
        trade.status = "CLOSED"
        trade.closed_at = candle.close_time
        return trade

    @staticmethod
    def _current_drawdown_percent(account) -> Decimal:
        initial_balance = Decimal(str(account.initial_balance))
        current_balance = Decimal(str(account.current_balance))
        if initial_balance <= 0:
            return Decimal("0")
        if current_balance >= initial_balance:
            return Decimal("0")
        return ((initial_balance - current_balance) / initial_balance) * Decimal("100")

    @staticmethod
    def _max_drawdown_percent(initial_balance: Decimal, closed_trades: list[PaperTrade]) -> Decimal:
        if initial_balance <= 0:
            return Decimal("0")
        running_balance = initial_balance
        peak_balance = initial_balance
        max_drawdown = Decimal("0")

        ordered_trades = sorted(
            [trade for trade in closed_trades if trade.closed_at is not None],
            key=lambda trade: trade.closed_at,
        )
        for trade in ordered_trades:
            running_balance += Decimal(str(trade.realized_pnl))
            if running_balance > peak_balance:
                peak_balance = running_balance
            if peak_balance > 0:
                drawdown = ((peak_balance - running_balance) / peak_balance) * Decimal("100")
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
        return max_drawdown

    @staticmethod
    def _format_open_trade_message(symbol: str, trade: PaperTrade) -> str:
        return (
            f"{symbol} PAPER TRADE OPENED\n"
            f"Side: {trade.side}\n"
            f"Entry: {trade.entry_price}\n"
            f"Stop Loss: {trade.stop_loss_price}\n"
            f"Take Profit: {trade.take_profit_price}\n"
            f"Size: {trade.position_size}"
        )

    @staticmethod
    def _format_closed_trade_message(symbol: str, trade: PaperTrade) -> str:
        return (
            f"{symbol} PAPER TRADE CLOSED\n"
            f"Exit Reason: {trade.exit_reason}\n"
            f"Exit: {trade.exit_price}\n"
            f"PnL: {trade.realized_pnl}\n"
            f"Fees: {trade.fees_paid}"
        )

    @staticmethod
    def _resolve_test_status(
        realized_pnl: Decimal,
        closed_trades: int,
        days_with_closed_trades: int,
    ) -> tuple[str, str, bool, str]:
        if closed_trades == 0:
            return (
                "BOOTSTRAPPING",
                "NO_TRADES_YET",
                False,
                "Paper test is running, but there are no closed trades yet. Let the system collect its first results.",
            )
        if closed_trades < 5 or days_with_closed_trades < 2:
            return (
                "COLLECTING_DATA",
                "EARLY_SIGNAL",
                False,
                "Paper test has started producing trades, but there is not enough history yet for a reliable verdict.",
            )
        if realized_pnl > 0:
            return (
                "EVALUATING",
                "PROFITABLE",
                True,
                "Paper test currently shows a positive realized result. Keep observing consistency before changing the setup.",
            )
        if realized_pnl < 0:
            return (
                "EVALUATING",
                "UNPROFITABLE",
                True,
                "Paper test currently shows a negative realized result. Review the strategy or let the sample size grow further.",
            )
        return (
            "EVALUATING",
            "BREAK_EVEN",
            True,
            "Paper test is currently near break-even. More closed trades are needed before making a decision.",
        )
