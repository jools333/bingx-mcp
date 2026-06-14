"""MCP tools for scalping metrics and technical indicator calculations."""

import json
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

from src.api.client import BingXClient
from src.services.market import MarketService
from src.services.indicators import calculate_indicators, INDICATOR_MAP

mcp = FastMCP("bingx-scalping", include_fastmcp_meta=False)
_client = BingXClient()
_service = MarketService(_client)


def _to_json(data: Any) -> str:
    """Convert data to pretty JSON string."""
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)


@mcp.tool()
async def calculate_indicators(
    symbol: str,
    timeframe: str = "1h",
    indicators: Optional[str] = None,
    period: int = 14,
    limit: int = 100,
) -> str:
    """Calculate technical indicators for a trading pair.

    Supported indicators: ema, sma, vwap, rsi, atr, macd,
    bollinger_bands, volume_delta, cvd, momentum, roc

    Args:
        symbol: Trading pair (e.g. BTC-USDT).
        timeframe: Kline interval (1m, 5m, 15m, 30m, 1h, default 1h).
        indicators: Comma-separated indicator names (e.g. "rsi,ema,macd").
                    If not specified, calculates all available indicators.
        period: Base period for indicators (default 14).
        limit: Number of candles to fetch (default 100).

    Returns calculated indicator values for the latest candle.
    """
    try:
        klines = await _service.get_klines(
            symbol=symbol, interval=timeframe, limit=limit
        )

        if not klines:
            return _to_json({"error": "No kline data available"})

        opens = [k.open for k in klines]
        highs = [k.high for k in klines]
        lows = [k.low for k in klines]
        closes = [k.close for k in klines]
        volumes = [k.volume for k in klines]

        if indicators:
            ind_list = [name.strip().lower() for name in indicators.split(",")]
        else:
            ind_list = list(INDICATOR_MAP.keys())

        result = calculate_indicators(
            symbol=symbol,
            timeframe=timeframe,
            opens=opens,
            highs=highs,
            lows=lows,
            closes=closes,
            volumes=volumes,
            indicators=ind_list,
            period=period,
        )

        return _to_json(result)
    except Exception as e:
        return _to_json({"error": str(e)})


@mcp.tool()
async def get_scalping_metrics(symbol: str) -> str:
    """Get comprehensive scalping metrics for a trading pair.

    Combines multiple data sources into a single snapshot:
    spread, orderbook imbalance, buy/sell delta, volume spike,
    ATR, RSI, VWAP distance, funding rate, open interest.

    Args:
        symbol: Trading pair (e.g. BTC-USDT).

    Returns dictionary of scalping metrics.
    """
    try:
        ticker = await _service.get_ticker(symbol)
        book = await _service.get_orderbook(symbol, depth=20)
        trades = await _service.get_recent_trades(symbol, limit=500)
        klines = await _service.get_klines(symbol, interval="1m", limit=100)
        oi = await _service.get_open_interest(symbol)
        fr = await _service.get_funding_rate(symbol)

        if not klines:
            return _to_json({"error": "No kline data for indicators"})

        closes = [k.close for k in klines]
        highs = [k.high for k in klines]
        lows = [k.low for k in klines]
        volumes = [k.volume for k in klines]

        ind_result = calculate_indicators(
            symbol=symbol,
            timeframe="1m",
            opens=[k.open for k in klines],
            highs=highs,
            lows=lows,
            closes=closes,
            volumes=volumes,
            indicators=["rsi", "atr", "vwap", "volume_delta"],
            period=14,
        )

        taker_buy = 0.0
        taker_sell = 0.0
        for t in trades:
            vol = t.price * t.quantity
            if t.is_buyer_maker:
                taker_sell += vol
            else:
                taker_buy += vol

        taker_delta = taker_buy - taker_sell

        avg_volume = sum(v for v in volumes[:-5]) / max(len(volumes) - 5, 1)
        last_volume = volumes[-1] if volumes else 0
        volume_spike = last_volume / avg_volume if avg_volume > 0 else 1.0

        vwap = ind_result.get("vwap", closes[-1]) if isinstance(ind_result, dict) else closes[-1]
        last_close = closes[-1] if closes else 0
        vwap_distance = (
            (last_close - vwap) / vwap * 100 if isinstance(vwap, (int, float)) and vwap and vwap > 0 else 0.0
        )

        metrics = {
            "symbol": symbol.upper(),
            "spread": ticker.spread,
            "spread_percent": ticker.spread_percent,
            "orderbook_imbalance": book.imbalance,
            "buy_sell_delta": round(taker_delta, 2),
            "volume_spike": round(volume_spike, 2),
            "atr": ind_result.get("atr") if isinstance(ind_result, dict) else None,
            "rsi": ind_result.get("rsi") if isinstance(ind_result, dict) else None,
            "vwap": vwap if isinstance(vwap, (int, float)) else None,
            "vwap_distance_percent": round(vwap_distance, 4),
            "funding_rate": fr.funding_rate,
            "mark_price": fr.mark_price,
            "open_interest": oi.open_interest,
            "last_price": ticker.last_price,
            "bid": ticker.bid_price,
            "ask": ticker.ask_price,
        }

        return _to_json(metrics)
    except Exception as e:
        return _to_json({"error": str(e)})
