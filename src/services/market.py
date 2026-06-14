"""Market data service for BingX perpetual futures."""

from datetime import datetime, timezone
from typing import Optional

from loguru import logger

from src.api.client import BingXClient
from src.models.market import (
    BookTicker,
    FundingRateData,
    Kline,
    LongShortRatio,
    OpenInterestData,
    OrderBook,
    OrderBookLevel,
    RecentTrade,
    SimpleTicker,
    TakerFlow,
    TickerData,
)
from src.models.common import KlineInterval


class MarketService:
    """Service for accessing BingX perpetual futures market data."""

    def __init__(self, client: BingXClient | None = None) -> None:
        """Initialize the market service.

        Args:
            client: BingX API client instance. Creates a new one if not provided.
        """
        self._client = client or BingXClient()

    async def get_server_time(self) -> int:
        """Get current server time.

        Returns:
            Server timestamp in milliseconds.
        """
        data = await self._client.get("/openApi/swap/v2/server/time")
        return int(data.get("serverTime", 0))

    async def get_ticker(self, symbol: str) -> SimpleTicker:
        """Get current ticker with bid/ask/spread.

        Fetches the 24h ticker and book ticker to calculate spread.

        Args:
            symbol: Trading pair (e.g. BTC-USDT).

        Returns:
            SimpleTicker with last price, bid, ask, spread, volume, change.
        """
        symbol = symbol.upper()

        ticker_data, book_ticker_raw = await self._client.get(
            "/openApi/swap/v2/quote/ticker", {"symbol": symbol}
        ), await self._client.get(
            "/openApi/swap/v2/quote/bookTicker", {"symbol": symbol}
        )

        ticker = TickerData.model_validate(ticker_data)
        book_raw = book_ticker_raw.get("book_ticker", book_ticker_raw)
        book = BookTicker.model_validate(book_raw)

        last = ticker.last_price
        bid = book.bid_price
        ask = book.ask_price
        spread = ask - bid
        spread_pct = (spread / ask * 100) if ask > 0 else 0.0

        return SimpleTicker(
            symbol=symbol,
            last_price=last,
            bid_price=bid,
            ask_price=ask,
            spread=round(spread, 8),
            spread_percent=round(spread_pct, 4),
        )

    async def get_24h_ticker(self, symbol: Optional[str] = None) -> list[TickerData] | TickerData:
        """Get 24-hour price change statistics.

        Args:
            symbol: Trading pair. If None, returns all symbols.

        Returns:
            Ticker data (single or list).
        """
        params = {"symbol": symbol.upper()} if symbol else {}
        data = await self._client.get("/openApi/swap/v2/quote/ticker", params if params else None)

        if symbol:
            return TickerData.model_validate(data)
        return [TickerData.model_validate(item) for item in data]

    async def get_klines(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 100,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> list[Kline]:
        """Get candlestick / kline data.

        Args:
            symbol: Trading pair (e.g. BTC-USDT).
            interval: Kline interval (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, etc.).
            limit: Number of candles (default 100, max 1440).
            start_time: Start time in milliseconds.
            end_time: End time in milliseconds.

        Returns:
            List of Kline objects.
        """
        KlineInterval(value=interval)  # validate

        params: dict[str, Any] = {
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": min(limit, 1440),
        }
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time

        data = await self._client.get("/openApi/swap/v3/quote/klines", params)

        if isinstance(data, list):
            result: list[Kline] = []
            for item in data:
                if isinstance(item, list):
                    result.append(Kline(
                        open_time=int(item[0]),
                        open=float(item[1]),
                        high=float(item[2]),
                        low=float(item[3]),
                        close=float(item[4]),
                        volume=float(item[5]),
                        close_time=int(item[6]) if len(item) > 6 else 0,
                        quote_volume=float(item[7]) if len(item) > 7 else 0.0,
                        trades=int(item[8]) if len(item) > 8 else 0,
                    ))
                elif isinstance(item, dict):
                    open_time = int(item.get("time", 0))
                    result.append(Kline(
                        open_time=open_time,
                        open=float(item.get("open", 0)),
                        high=float(item.get("high", 0)),
                        low=float(item.get("low", 0)),
                        close=float(item.get("close", 0)),
                        volume=float(item.get("volume", 0)),
                        close_time=open_time,  # v3 uses single 'time' field
                        quote_volume=float(item.get("quoteVolume", 0)),
                        trades=int(item.get("trades", 0)),
                    ))
            return result
        return []

    async def get_orderbook(self, symbol: str, depth: int = 20) -> OrderBook:
        """Get order book depth with imbalance calculation.

        Args:
            symbol: Trading pair (e.g. BTC-USDT).
            depth: Number of levels (default 20, max 100).

        Returns:
            OrderBook with bids, asks, volumes, and imbalance ratio.
        """
        data = await self._client.get(
            "/openApi/swap/v2/quote/depth",
            {"symbol": symbol.upper(), "limit": min(depth, 100)},
        )

        bids_raw = data.get("bids", [])
        asks_raw = data.get("asks", [])

        bids = [OrderBookLevel(price=float(b[0]), quantity=float(b[1])) for b in bids_raw]
        asks = [OrderBookLevel(price=float(a[0]), quantity=float(a[1])) for a in asks_raw]

        bid_volume = sum(b.price * b.quantity for b in bids)
        ask_volume = sum(a.price * a.quantity for a in asks)
        total = bid_volume + ask_volume
        imbalance = (bid_volume - ask_volume) / total if total > 0 else 0.0

        return OrderBook(
            symbol=symbol.upper(),
            bids=bids,
            asks=asks,
            bid_volume=round(bid_volume, 2),
            ask_volume=round(ask_volume, 2),
            imbalance=round(imbalance, 4),
        )

    async def get_recent_trades(self, symbol: str, limit: int = 500) -> list[RecentTrade]:
        """Get recent public trades.

        Args:
            symbol: Trading pair.
            limit: Number of trades (default 500, max 1000).

        Returns:
            List of recent trades.
        """
        data = await self._client.get(
            "/openApi/swap/v2/quote/trades",
            {"symbol": symbol.upper(), "limit": min(limit, 1000)},
        )

        if isinstance(data, list):
            return [
                RecentTrade(
                    id=item.get("id", ""),
                    price=float(item.get("price", 0)),
                    qty=float(item.get("qty", 0)),
                    time=int(item.get("time", 0)),
                    isBuyerMaker=item.get("isBuyerMaker", False),
                    quoteQty=str(item.get("quoteQty", "0")),
                )
                for item in data
            ]
        return []

    async def get_open_interest(self, symbol: str) -> OpenInterestData:
        """Get open interest for a symbol.

        Args:
            symbol: Trading pair.

        Returns:
            Open interest data.
        """
        data = await self._client.get(
            "/openApi/swap/v2/quote/openInterest",
            {"symbol": symbol.upper()},
        )
        return OpenInterestData.model_validate(data)

    async def get_funding_rate(self, symbol: str) -> FundingRateData:
        """Get current funding rate and mark price.

        Args:
            symbol: Trading pair.

        Returns:
            Funding rate data including mark price, index price.
        """
        data = await self._client.get(
            "/openApi/swap/v2/quote/premiumIndex",
            {"symbol": symbol.upper()},
        )
        return FundingRateData.model_validate(data)

    async def get_funding_rate_history(
        self, symbol: str, limit: int = 100
    ) -> list[FundingRateData]:
        """Get funding rate history.

        Args:
            symbol: Trading pair.
            limit: Number of records.

        Returns:
            List of funding rate data.
        """
        data = await self._client.get(
            "/openApi/swap/v2/quote/fundingRate",
            {"symbol": symbol.upper(), "limit": limit},
        )
        if isinstance(data, list):
            return [FundingRateData.model_validate(item) for item in data]
        return []

    async def get_long_short_ratio(
        self, symbol: str, period: str = "5m", limit: int = 1
    ) -> LongShortRatio:
        """Get long/short account ratio for a symbol.

        Note: BingX does not expose a direct long/short ratio endpoint.
        This method estimates the ratio from open interest and recent trade
        directions. For more accurate data, consider using external sources
        like Coinglass.

        Args:
            symbol: Trading pair.
            period: Time period (informational, used for trade aggregation).
            limit: Number of records.

        Returns:
            Estimated long/short ratio data.
        """
        trades = await self.get_recent_trades(symbol, limit=1000)

        buy_volume = 0.0
        sell_volume = 0.0

        for trade in trades:
            vol = trade.price * trade.quantity
            if trade.is_buyer_maker:
                sell_volume += vol
            else:
                buy_volume += vol

        total = buy_volume + sell_volume
        long_ratio = buy_volume / total if total > 0 else 0.5
        short_ratio = sell_volume / total if total > 0 else 0.5
        lsr = long_ratio / short_ratio if short_ratio > 0 else 1.0

        return LongShortRatio(
            symbol=symbol.upper(),
            long_ratio=round(long_ratio, 4),
            short_ratio=round(short_ratio, 4),
            long_short_ratio=round(lsr, 4),
            timestamp=int(datetime.now(timezone.utc).timestamp() * 1000),
        )

    async def get_taker_flow(
        self, symbol: str, limit: int = 1000
    ) -> TakerFlow:
        """Get taker buy/sell volume flow.

        Calculates from recent trades: a trade where the buyer is the taker
        (isBuyerMaker=False) counts as buy volume; otherwise sell volume.

        Args:
            symbol: Trading pair.
            limit: Number of recent trades to analyze.

        Returns:
            Taker flow data with buy/sell volume and delta.
        """
        trades = await self.get_recent_trades(symbol, limit=limit)

        taker_buy = 0.0
        taker_sell = 0.0

        for trade in trades:
            vol = trade.price * trade.quantity
            if trade.is_buyer_maker:
                taker_sell += vol
            else:
                taker_buy += vol

        return TakerFlow(
            symbol=symbol.upper(),
            taker_buy_volume=round(taker_buy, 2),
            taker_sell_volume=round(taker_sell, 2),
            delta=round(taker_buy - taker_sell, 2),
            timestamp=int(datetime.now(timezone.utc).timestamp() * 1000),
        )
