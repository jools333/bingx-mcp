"""BingX MCP Server - Production-ready MCP server for BingX crypto exchange.

Usage:
    python main.py          # Start server with default transport (stdio)
    python main.py --sse    # Start server with SSE transport on http://0.0.0.0:8000/sse
    python main.py --sse --port 9000  # Custom port
"""

import argparse
import json
import os
import sys
from typing import Any, Optional

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

from src.api.client import BingXClient
from src.models.market import TickerData
from src.services.account import AccountService
from src.services.market import MarketService
from src.services.trade import TradeService
from src.services.indicators import calculate_indicators, INDICATOR_MAP
from src.utils.logging import logger

# host/port/defaults are set here, not in .run()
mcp = FastMCP("bingx-mcp", host="0.0.0.0", port=8000)
_client = BingXClient()
_account = AccountService(_client)
_market = MarketService(_client)
_trade = TradeService(_client)


def _to_json(data: Any) -> str:
    """Convert data to pretty JSON string."""
    def _serialize(obj: Any) -> Any:
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if isinstance(obj, list):
            return [_serialize(item) for item in obj]
        if isinstance(obj, dict):
            return {k: _serialize(v) for k, v in obj.items()}
        return obj

    return json.dumps(_serialize(data), indent=2, ensure_ascii=False, default=str)


# ─── Account Tools ───────────────────────────────────────────────────────────

@mcp.tool()
async def get_balance() -> str:
    """Get account balance: list of per-asset balances with total, free, locked amounts."""
    try:
        balance = await _account.get_balance()
        result = [
            {
                "asset": a.asset,
                "total": a.balance,
                "free": a.available_balance,
                "locked": round(a.cross_wallet_balance - a.available_balance, 4),
            }
            for a in balance.assets
        ]
        return _to_json(result)
    except Exception as e:
        return _to_json({"error": str(e)})


@mcp.tool()
async def get_positions(symbol: Optional[str] = None) -> str:
    """Get open positions: symbol, side, leverage, entry price, current price, liq price, unrealized PnL, quantity."""
    try:
        positions = await _account.get_positions(symbol)
        result = [
            {
                "id": p.position_id,
                "symbol": p.symbol,
                "side": p.position_side,
                "leverage": p.leverage,
                "entry_price": p.entry_price,
                "current_price": p.mark_price,
                "liquidation_price": p.liquidation_price,
                "unrealized_pnl": p.unrealized_profit,
                "unrealized_pnl_pct": round(p.unrealized_profit / (p.entry_price * p.position_amt) * p.leverage * 100, 4) if p.entry_price and p.position_amt else 0.0,
                "quantity": p.position_amt,
            }
            for p in positions
        ]
        return _to_json(result)
    except Exception as e:
        return _to_json({"error": str(e)})


# ─── Market Data Tools ───────────────────────────────────────────────────────

@mcp.tool()
async def get_ticker(symbol: str) -> str:
    """Get current price: last price, bid, ask, spread (absolute & percent), 24h change, volume."""
    try:
        ticker = await _market.get_ticker(symbol)
        t24 = await _market.get_24h_ticker(symbol)
        result = {
            "symbol": ticker.symbol,
            "last_price": ticker.last_price,
            "bid_price": ticker.bid_price,
            "ask_price": ticker.ask_price,
            "spread": ticker.spread,
            "spread_percent": ticker.spread_percent,
            "volume_24h": float(t24.volume) if isinstance(t24, TickerData) else 0,
            "high_24h": float(t24.high_price) if isinstance(t24, TickerData) else 0,
            "low_24h": float(t24.low_price) if isinstance(t24, TickerData) else 0,
            "change_24h": float(t24.price_change_percent) if isinstance(t24, TickerData) else 0,
        }
        return _to_json(result)
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
    """Get OHLCV candlestick data. Intervals: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M."""
    try:
        klines = await _market.get_klines(
            symbol=symbol, interval=interval, limit=min(limit, 1440),
            start_time=start_time, end_time=end_time,
        )
        result = [
            {
                "symbol": symbol.upper(),
                "timeframe": interval,
                "open_time": k.open_time,
                "open": k.open,
                "high": k.high,
                "low": k.low,
                "close": k.close,
                "volume": k.volume,
                "close_time": k.close_time,
            }
            for k in klines
        ]
        return _to_json(result)
    except Exception as e:
        return _to_json({"error": str(e)})


@mcp.tool()
async def get_orderbook(symbol: str, depth: int = 20) -> str:
    """Get order book: bids, asks, bid/ask volume, imbalance = (bid_vol - ask_vol) / (bid_vol + ask_vol). Positive = buying pressure."""
    try:
        import time as _time
        book = await _market.get_orderbook(symbol, min(depth, 100))
        result = book.model_dump()
        result["timestamp"] = int(_time.time() * 1000)
        return _to_json(result)
    except Exception as e:
        return _to_json({"error": str(e)})


@mcp.tool()
async def get_recent_trades(symbol: str, limit: int = 500) -> str:
    """Get recent trades: price, volume, direction (buy=aggressive buy), timestamp."""
    try:
        trades = await _market.get_recent_trades(symbol, min(limit, 1000))
        return _to_json(trades)
    except Exception as e:
        return _to_json({"error": str(e)})


@mcp.tool()
async def get_open_interest(symbol: str) -> str:
    """Get open interest for a symbol."""
    try:
        oi = await _market.get_open_interest(symbol)
        return _to_json(oi)
    except Exception as e:
        return _to_json({"error": str(e)})


@mcp.tool()
async def get_funding_rate(symbol: str) -> str:
    """Get funding rate, mark price, index price, next funding time."""
    try:
        fr = await _market.get_funding_rate(symbol)
        return _to_json(fr)
    except Exception as e:
        return _to_json({"error": str(e)})


@mcp.tool()
async def get_long_short_ratio(symbol: str, period: str = "5m") -> str:
    """Get long/short ratio estimated from recent trade directions."""
    try:
        lsr = await _market.get_long_short_ratio(symbol, period)
        return _to_json(lsr)
    except Exception as e:
        return _to_json({"error": str(e)})


@mcp.tool()
async def get_taker_flow(symbol: str, limit: int = 1000) -> str:
    """Get taker buy/sell volume. Calculated from recent trades. Positive delta = more buying pressure."""
    try:
        flow = await _market.get_taker_flow(symbol, min(limit, 1000))
        return _to_json(flow)
    except Exception as e:
        return _to_json({"error": str(e)})


# ─── Trade Tools ─────────────────────────────────────────────────────────────

@mcp.tool()
async def get_open_orders(symbol: Optional[str] = None) -> str:
    """Get currently open orders, optionally filtered by symbol."""
    try:
        orders = await _trade.get_open_orders(symbol)
        result = [
            {
                "order_id": o.order_id, "symbol": o.symbol,
                "side": o.side, "position_side": o.position_side,
                "type": o.type, "price": o.price, "stop_price": o.stop_price,
                "orig_quantity": o.orig_quantity, "executed_quantity": o.executed_quantity,
                "status": o.status, "reduce_only": o.reduce_only,
                "avg_price": o.avg_price, "time": o.time,
            }
            for o in orders
        ]
        return _to_json(result)
    except Exception as e:
        return _to_json({"error": str(e)})


@mcp.tool()
async def get_order_history(
    symbol: Optional[str] = None,
    limit: int = 100,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
) -> str:
    """Get historical orders with optional time range and symbol filter."""
    try:
        orders = await _trade.get_order_history(
            symbol=symbol, limit=min(limit, 500),
            start_time=start_time, end_time=end_time,
        )
        result = [
            {
                "order_id": o.order_id, "symbol": o.symbol,
                "side": o.side, "position_side": o.position_side,
                "type": o.type, "price": o.price, "stop_price": o.stop_price,
                "orig_quantity": o.orig_quantity, "executed_quantity": o.executed_quantity,
                "status": o.status, "avg_price": o.avg_price,
                "cum_quote": o.cum_quote, "profit": o.profit, "time": o.time,
            }
            for o in orders
        ]
        return _to_json(result)
    except Exception as e:
        return _to_json({"error": str(e)})


@mcp.tool()
async def create_order(
    symbol: str,
    side: str,
    type: str,
    quantity: Optional[float] = None,
    price: Optional[float] = None,
    stop_price: Optional[float] = None,
    position_side: str = "LONG",
    reduce_only: bool = False,
    close_position: bool = False,
) -> str:
    """Create order. Types: MARKET, LIMIT, STOP_MARKET, STOP, TAKE_PROFIT_MARKET, TAKE_PROFIT.
    LIMIT requires price. STOP_MARKET/TAKE_PROFIT_MARKET require stop_price.
    STOP/TAKE_PROFIT require both price and stop_price.
    Set close_position=true to close entire position (hedge mode — quantity is not needed)."""
    try:
        import time as _time
        result = await _trade.create_order(
            symbol=symbol, side=side, position_side=position_side,
            type=type, quantity=quantity, price=price,
            stop_price=stop_price, reduce_only=reduce_only,
            close_position=close_position,
        )
        order = result.get("order", result)
        raw_side = str(order.get("side", side.upper())).upper()
        norm_side = "BUY" if raw_side in ("BID", "BUY") else "SELL"
        normalized = {
            "id": str(order.get("orderId", order.get("id", ""))),
            "symbol": order.get("symbol", symbol.upper()),
            "side": norm_side,
            "type": order.get("type", type.upper()),
            "quantity": float(order.get("origQty", order.get("quantity", quantity or 0))),
            "price": float(order.get("price", price or 0)) if (order.get("price") or price) else None,
            "stop_price": float(order.get("stopPrice", stop_price or 0)) if (order.get("stopPrice") or stop_price) else None,
            "status": order.get("status", "NEW"),
            "created_at": int(_time.time() * 1000),
            "filled_quantity": float(order.get("executedQty", 0)) if order.get("executedQty") else None,
            "avg_fill_price": float(order.get("avgPrice", 0)) if order.get("avgPrice") else None,
        }
        return _to_json(normalized)
    except Exception as e:
        return _to_json({"error": str(e)})


@mcp.tool()
async def cancel_order(symbol: str, order_id: int) -> str:
    """Cancel an open order by ID."""
    try:
        result = await _trade.cancel_order(symbol, order_id)
        return _to_json(result)
    except Exception as e:
        return _to_json({"error": str(e)})


@mcp.tool()
async def cancel_all_orders(symbol: str) -> str:
    """Cancel all open orders for a symbol."""
    try:
        result = await _trade.cancel_all_orders(symbol)
        return _to_json(result)
    except Exception as e:
        return _to_json({"error": str(e)})


@mcp.tool()
async def set_leverage(symbol: str, leverage: int, side: str = "LONG") -> str:
    """Set leverage for a trading pair (1-125)."""
    try:
        result = await _trade.set_leverage(symbol, min(max(leverage, 1), 125), side)
        return _to_json(result)
    except Exception as e:
        return _to_json({"error": str(e)})


@mcp.tool()
async def close_position(symbol: str, position_id: Optional[str] = None) -> str:
    """Close an open position. If position_id is omitted, closes all positions for the symbol."""
    try:
        import time as _time
        result = await _trade.close_position(symbol, position_id)
        order = result.get("order", result)
        raw_side = str(order.get("side", "SELL")).upper()
        side = "BUY" if raw_side in ("BID", "BUY") else "SELL"
        normalized = {
            "id": str(order.get("orderId", order.get("id", ""))),
            "symbol": order.get("symbol", symbol.upper()),
            "side": side,
            "type": order.get("type", "MARKET"),
            "quantity": float(order.get("origQty", order.get("quantity", 0))),
            "price": None,
            "stop_price": None,
            "status": order.get("status", "FILLED"),
            "created_at": int(_time.time() * 1000),
            "filled_quantity": float(order.get("executedQty", 0)) if order.get("executedQty") else None,
            "avg_fill_price": float(order.get("avgPrice", 0)) if order.get("avgPrice") else None,
        }
        return _to_json(normalized)
    except Exception as e:
        return _to_json({"error": str(e)})


# ─── Scalping & Indicators Tools ─────────────────────────────────────────────

@mcp.tool()
async def calculate_indicators(
    symbol: str,
    timeframe: str = "1h",
    indicators: Optional[str] = None,
    period: int = 14,
    limit: int = 100,
) -> str:
    """Calculate technical indicators. Available: ema, sma, vwap, rsi, atr, macd, bollinger_bands, volume_delta, cvd, momentum, roc."""
    try:
        klines = await _market.get_klines(
            symbol=symbol, interval=timeframe, limit=limit,
        )
        if not klines:
            return _to_json({"error": "No kline data available"})

        ind_list = (
            [name.strip().lower() for name in indicators.split(",")]
            if indicators
            else list(INDICATOR_MAP.keys())
        )

        result = calculate_indicators(
            symbol=symbol, timeframe=timeframe,
            opens=[k.open for k in klines],
            highs=[k.high for k in klines],
            lows=[k.low for k in klines],
            closes=[k.close for k in klines],
            volumes=[k.volume for k in klines],
            indicators=ind_list, period=period,
        )
        return _to_json(result)
    except Exception as e:
        return _to_json({"error": str(e)})


@mcp.tool()
async def get_scalping_metrics(symbol: str) -> str:
    """Get comprehensive scalping snapshot: spread, imbalance, buy/sell delta, volume spike, ATR, RSI, VWAP distance, funding rate, OI."""
    try:
        ticker = await _market.get_ticker(symbol)
        book = await _market.get_orderbook(symbol, depth=20)
        trades = await _market.get_recent_trades(symbol, limit=500)
        klines = await _market.get_klines(symbol, interval="1m", limit=100)
        oi = await _market.get_open_interest(symbol)
        fr = await _market.get_funding_rate(symbol)

        if klines:
            closes = [k.close for k in klines]
            highs = [k.high for k in klines]
            lows = [k.low for k in klines]
            volumes = [k.volume for k in klines]

            ind_result = calculate_indicators(
                symbol=symbol, timeframe="1m",
                opens=[k.open for k in klines],
                highs=highs, lows=lows, closes=closes,
                volumes=volumes,
                indicators=["rsi", "atr", "vwap", "volume_delta"],
                period=14,
            )

            avg_volume = sum(v for v in volumes[:-5]) / max(len(volumes) - 5, 1)
            last_volume = volumes[-1] if volumes else 0
            volume_spike = last_volume / avg_volume if avg_volume > 0 else 1.0

            atr_val = ind_result.get("atr") if isinstance(ind_result, dict) else None
            rsi_val = ind_result.get("rsi") if isinstance(ind_result, dict) else None
            vwap_val = ind_result.get("vwap") if isinstance(ind_result, dict) else closes[-1]
        else:
            atr_val = None
            rsi_val = None
            vwap_val = None
            volume_spike = 1.0

        last_close = closes[-1] if klines else 0
        vwap_distance = (
            (last_close - vwap_val) / vwap_val * 100
            if isinstance(vwap_val, (int, float)) and vwap_val and vwap_val > 0
            else 0.0
        )

        taker_buy = 0.0
        taker_sell = 0.0
        for t in trades:
            vol = t.price * t.quantity
            if t.is_buyer_maker:
                taker_sell += vol
            else:
                taker_buy += vol

        metrics = {
            "symbol": symbol.upper(),
            "spread": ticker.spread,
            "spread_percent": ticker.spread_percent,
            "orderbook_imbalance": book.imbalance,
            "buy_sell_delta": round(taker_buy - taker_sell, 2),
            "volume_spike": round(volume_spike, 2),
            "atr": atr_val,
            "rsi": rsi_val,
            "vwap": vwap_val if isinstance(vwap_val, (int, float)) else None,
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


# ─── Entry Point ─────────────────────────────────────────────────────────────

def main() -> None:
    """Start the BingX MCP server."""
    parser = argparse.ArgumentParser(description="BingX MCP Server")
    parser.add_argument("--sse", action="store_true", help="Use SSE transport instead of stdio")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind SSE server (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Port for SSE server (default: 8000)")
    args = parser.parse_args()

    api_key = os.getenv("BINGX_API_KEY", "")
    if not api_key:
        logger.warning("BINGX_API_KEY not set! Set in .env file or environment.")

    # Apply host/port settings at runtime
    mcp.settings.host = args.host
    mcp.settings.port = args.port

    transport = "sse" if args.sse else "stdio"
    logger.info(f"Starting BingX MCP Server v1.0.0 (transport={transport})")
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
