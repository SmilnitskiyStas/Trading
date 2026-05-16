from collections.abc import Sequence

import ccxt.async_support as ccxt


class CcxtMarketDataClient:
    def __init__(self, exchange_id: str):
        self.exchange_id = exchange_id
        self.exchange_class = getattr(ccxt, exchange_id)

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
        since: int | None = None,
    ) -> Sequence[Sequence[float]]:
        exchange = self.exchange_class({"enableRateLimit": True})
        try:
            return await exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                since=since,
                limit=limit,
            )
        finally:
            await exchange.close()
