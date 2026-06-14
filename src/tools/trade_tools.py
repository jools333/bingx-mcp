"""MCP tools for trading operations (orders, leverage)."""

import json
from typing import Optional

from mcp.server.fastmcp import FastMCP

from src.api.client import BingXClient
from src.services.trade import TradeService

mcp = FastMCP("bingx-trade", include_fastmcp_meta=False)
_client = BingXClient()
_service = TradeService(_client)


@mcp.tool()
async def get_open_orders(symbol: Optional[str] = None) -> str:
    """Get currently open orders.

    Args:
        symbol: Trading pair filter (e.g. BTC-USDT). Optional.

    Returns list of open orders with order ID, status, type, price, quantity.
    """
    try:
        orders = await _service.get_open_orders(symbol)
        result = [
            {
                "order_id": o.order_id,
                "symbol": o.symbol,
                "side": o.side,
                "position_side": o.position_side,
                "type": o.type,
                "price": o.price,
                "stop_price": o.stop_price,
                "orig_quantity": o.orig_quantity,
                "executed_quantity": o.executed_quantity,
                "status": o.status,
                "reduce_only": o.reduce_only,
                "avg_price": o.avg_price,
                "time": o.time,
            }
            for o in orders
        ]
        return json.dumps(result, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2, ensure_ascii=False)


@mcp.tool()
async def get_order_history(
    symbol: Optional[str] = None,
    limit: int = 100,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
) -> str:
    """Get historical order list.

    Args:
        symbol: Trading pair filter. Optional.
        limit: Max orders to return (default 100, max 500).
        start_time: Start time in ms. Optional.
        end_time: End time in ms. Optional.

    Returns list of historical orders.
    """
    try:
        orders = await _service.get_order_history(
            symbol=symbol,
            limit=limit,
            start_time=start_time,
            end_time=end_time,
        )
        result = [
            {
                "order_id": o.order_id,
                "symbol": o.symbol,
                "side": o.side,
                "position_side": o.position_side,
                "type": o.type,
                "price": o.price,
                "stop_price": o.stop_price,
                "orig_quantity": o.orig_quantity,
                "executed_quantity": o.executed_quantity,
                "status": o.status,
                "avg_price": o.avg_price,
                "cum_quote": o.cum_quote,
                "profit": o.profit,
                "time": o.time,
            }
            for o in orders
        ]
        return json.dumps(result, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2, ensure_ascii=False)


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
    leverage: Optional[int] = None,
) -> str:
    """Create a new order on BingX perpetual futures.

    Order types supported:
    - MARKET: Execute immediately at market price
    - LIMIT: Execute at specified price (requires price)
    - STOP_MARKET: Stop-loss market (requires stop_price)
    - STOP: Stop-loss limit (requires stop_price and price)
    - TAKE_PROFIT_MARKET: Take-profit market (requires stop_price)
    - TAKE_PROFIT: Take-profit limit (requires stop_price and price)

    Args:
        symbol: Trading pair (e.g. BTC-USDT).
        side: BUY or SELL.
        type: Order type (MARKET, LIMIT, STOP_MARKET, STOP,
              TAKE_PROFIT_MARKET, TAKE_PROFIT).
        quantity: Order quantity in coins.
        price: Limit price (for LIMIT, STOP, TAKE_PROFIT types).
        stop_price: Trigger price (for STOP_*, TAKE_PROFIT_* types).
        position_side: LONG or SHORT (default LONG).
        reduce_only: Whether order only reduces position.
        leverage: Optional leverage override.

    Returns full exchange response with order details.
    """
    try:
        result = await _service.create_order(
            symbol=symbol,
            side=side,
            position_side=position_side,
            type=type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
            reduce_only=reduce_only,
        )
        return json.dumps(result, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2, ensure_ascii=False)


@mcp.tool()
async def cancel_order(symbol: str, order_id: int) -> str:
    """Cancel an open order.

    Args:
        symbol: Trading pair (e.g. BTC-USDT).
        order_id: Order ID to cancel.

    Returns cancellation confirmation.
    """
    try:
        result = await _service.cancel_order(symbol, order_id)
        return json.dumps(result, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2, ensure_ascii=False)


@mcp.tool()
async def cancel_all_orders(symbol: str) -> str:
    """Cancel all open orders for a symbol.

    Args:
        symbol: Trading pair (e.g. BTC-USDT).

    Returns cancellation confirmation.
    """
    try:
        result = await _service.cancel_all_orders(symbol)
        return json.dumps(result, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2, ensure_ascii=False)


@mcp.tool()
async def set_leverage(symbol: str, leverage: int, side: str = "LONG") -> str:
    """Set leverage for a trading pair.

    Args:
        symbol: Trading pair (e.g. BTC-USDT).
        leverage: Leverage multiplier (1-125).
        side: LONG or SHORT (default LONG).

    Returns updated leverage confirmation.
    """
    try:
        result = await _service.set_leverage(symbol, leverage, side)
        return json.dumps(result, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2, ensure_ascii=False)
