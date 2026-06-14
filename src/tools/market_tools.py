"""MCP tools for market data (ticker, klines, orderbook, etc.)."""

import json
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

from src.api.client import BingXClient
from src.services.market import MarketService

mcp = FastMCP("bingx-market", include_fastmcp_meta=False)
_client = BingXClient()
_service = MarketService(_client)


def _serialize(obj: Any) -> Any:
    """Recursively convert Pydantic models and complex objects to JSON-serializable types."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, list):
        return [_serialize(item) for item in obj]
    if isinstance(obj, dict):
        return {key: _serialize(val) for key, val in obj.items()}
    return obj


def _to_json(data: Any) -> str:
    """Convert any data structure to pretty JSON string."""
    return json.dumps(_serialize(data), indent=2, ensure_ascii=False, default=str)


@mcp.tool()
async def get_ticker(symbol: str) -> str:
    """Get current ticker with last price, bid, ask, and spread.

    Args:
        symbol: Trading pair (e.g. BTC-USDT).

    Returns current ticker data including last price, bid, ask, spread.
    """
    try:
        ticker = await _service.get_ticker(symbol)
        return _to_json(ticker)
    except Exception as e:
        return _to_json({"error": str(e)})


@mcp.tool()
async def get_klines(
    symbol: str,
    interval: str = "1h",
    limit: int = 100,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
) -> str:
    """Get candlestick / OHLCV data.

    Supported intervals: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M

    Args:
        symbol: Trading pair (e.g. BTC-USDT).
        interval: Kline interval (default 1h).
        limit: Number of candles (default 100, max 1440).
        start_time: Start timestamp in ms. Optional.
        end_time: End timestamp in ms. Optional.

    Returns OHLCV candle data.
    """
    try:
        klines = await _service.get_klines(
            symbol=symbol,
            interval=interval,
            limit=limit,
            start_time=start_time,
            end_time=end_time,
        )
        return _to_json(klines)
    except Exception as e:
        return _to_json({"error": str(e)})


@mcp.tool()
async def get_orderbook(symbol: str, depth: int = 20) -> str:
    """Get order book with bid/ask levels and imbalance.

    Args:
        symbol: Trading pair (e.g. BTC-USDT).
        depth: Number of levels to return (default 20, max 100).

    Returns bids, asks, bid_volume, ask_volume, and imbalance ratio.
    Imbalance formula: (bid_volume - ask_volume) / (bid_volume + ask_volume)
    Positive = buying pressure, Negative = selling pressure.
    """
    try:
        book = await _service.get_orderbook(symbol, depth)
        return _to_json(book)
    except Exception as e:
        return _to_json({"error": str(e)})


@mcp.tool()
async def get_recent_trades(symbol: str, limit: int = 500) -> str:
    """Get recent public trades for a symbol.

    Args:
        symbol: Trading pair (e.g. BTC-USDT).
        limit: Number of trades to return (default 500, max 1000).

    Returns list of trades with price, quantity, side, and timestamp.
    """
    try:
        trades = await _service.get_recent_trades(symbol, limit)
        return _to_json(trades)
    except Exception as e:
        return _to_json({"error": str(e)})


@mcp.tool()
async def get_open_interest(symbol: str) -> str:
    """Get current open interest for a symbol.

    Args:
        symbol: Trading pair (e.g. BTC-USDT).

    Returns open interest value and timestamp.
    """
    try:
        oi = await _service.get_open_interest(symbol)
        return _to_json(oi)
    except Exception as e:
        return _to_json({"error": str(e)})


@mcp.tool()
async def get_funding_rate(symbol: str) -> str:
    """Get current funding rate and mark price.

    Args:
        symbol: Trading pair (e.g. BTC-USDT).

    Returns funding rate, mark price, index price, next funding time.
    """
    try:
        fr = await _service.get_funding_rate(symbol)
        return _to_json(fr)
    except Exception as e:
        return _to_json({"error": str(e)})


@mcp.tool()
async def get_long_short_ratio(symbol: str, period: str = "5m") -> str:
    """Get long/short ratio for a symbol.

    Estimated from recent trade directions. Higher values indicate
    more buying pressure.

    Args:
        symbol: Trading pair (e.g. BTC-USDT).
        period: Aggregation period (default 5m).

    Returns long ratio, short ratio, and long/short ratio.
    """
    try:
        lsr = await _service.get_long_short_ratio(symbol, period)
        return _to_json(lsr)
    except Exception as e:
        return _to_json({"error": str(e)})


@mcp.tool()
async def get_taker_flow(symbol: str, limit: int = 1000) -> str:
    """Get taker buy/sell volume flow.

    Calculates taker buy volume vs taker sell volume from recent trades.
    Positive delta = more buying pressure.

    Args:
        symbol: Trading pair (e.g. BTC-USDT).
        limit: Number of trades to analyze (default 1000).

    Returns taker buy volume, taker sell volume, and delta.
    """
    try:
        flow = await _service.get_taker_flow(symbol, limit)
        return _to_json(flow)
    except Exception as e:
        return _to_json({"error": str(e)})
