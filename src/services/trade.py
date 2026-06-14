"""Trade service for BingX perpetual futures.

Handles order creation, cancellation, history queries, and leverage management.
"""

from typing import Any, Optional

from loguru import logger

from src.api.client import BingXClient
from src.models.trade import OrderInfo


class TradeService:
    """Service for BingX perpetual futures trading operations."""

    def __init__(self, client: BingXClient | None = None) -> None:
        """Initialize the trade service.

        Args:
            client: BingX API client instance.
        """
        self._client = client or BingXClient()

    async def create_order(
        self,
        symbol: str,
        side: str,
        position_side: str,
        type: str,
        quantity: Optional[float] = None,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: str = "GTC",
        reduce_only: bool = False,
        working_type: str = "CONTRACT_PRICE",
        client_order_id: str = "",
        close_position: bool = False,
    ) -> dict[str, Any]:
        """Create a new order.

        Args:
            symbol: Trading pair (e.g. BTC-USDT).
            side: BUY or SELL.
            position_side: LONG or SHORT.
            type: MARKET, LIMIT, STOP_MARKET, STOP, TAKE_PROFIT_MARKET, TAKE_PROFIT.
            quantity: Order quantity in coins.
            price: Limit price (required for LIMIT, STOP, TAKE_PROFIT).
            stop_price: Trigger price (required for STOP_MARKET, STOP, TAKE_PROFIT_MARKET, TAKE_PROFIT).
            time_in_force: GTC, IOC, FOK, PostOnly.
            reduce_only: Whether the order only reduces position.
            working_type: MARK_PRICE or CONTRACT_PRICE.
            client_order_id: Custom client order ID.
            close_position: If True, close the entire position (hedge mode).

        Returns:
            Full order response from the exchange.
        """
        params: dict[str, Any] = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "positionSide": position_side.upper(),
            "type": type.upper(),
        }

        if close_position:
            params["closePosition"] = "true"
        elif quantity is not None:
            params["quantity"] = quantity

        if price is not None:
            params["price"] = price

        if stop_price is not None:
            params["stopPrice"] = stop_price

        if type.upper() == "LIMIT":
            params["timeInForce"] = time_in_force

        if reduce_only:
            params["reduceOnly"] = "true"

        if type.upper() in ("STOP_MARKET", "STOP", "TAKE_PROFIT_MARKET", "TAKE_PROFIT"):
            params["workingType"] = working_type

        if client_order_id:
            params["clientOrderId"] = client_order_id

        data = await self._client.post("/openApi/swap/v2/trade/order", params)
        logger.info(f"Order created: {data}")
        return data

    async def cancel_order(self, symbol: str, order_id: int) -> dict[str, Any]:
        """Cancel an open order.

        Args:
            symbol: Trading pair.
            order_id: Order ID to cancel.

        Returns:
            Cancellation response.
        """
        params = {
            "symbol": symbol.upper(),
            "orderId": order_id,
        }
        data = await self._client.delete("/openApi/swap/v2/trade/order", params)
        logger.info(f"Order cancelled: orderId={order_id}")
        return data

    async def cancel_all_orders(self, symbol: str) -> dict[str, Any]:
        """Cancel all open orders for a symbol.

        Args:
            symbol: Trading pair.

        Returns:
            Cancellation response.
        """
        params = {"symbol": symbol.upper()}
        data = await self._client.delete("/openApi/swap/v2/trade/allOpenOrders", params)
        logger.info(f"All orders cancelled for {symbol}")
        return data

    async def get_open_orders(self, symbol: Optional[str] = None) -> list[OrderInfo]:
        """Get all currently open orders.

        Args:
            symbol: Trading pair to filter by (optional).

        Returns:
            List of open orders.
        """
        params = {"symbol": symbol.upper()} if symbol else {}
        data = await self._client.get("/openApi/swap/v2/trade/openOrders", params if params else None)

        if isinstance(data, list):
            return [OrderInfo.model_validate(item) for item in data]
        return []

    async def get_order_history(
        self,
        symbol: Optional[str] = None,
        order_id: Optional[int] = None,
        limit: int = 100,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> list[OrderInfo]:
        """Get order history (all orders including filled and cancelled).

        Args:
            symbol: Trading pair filter.
            order_id: Specific order ID to query.
            limit: Max number of orders (default 100, max 500).
            start_time: Start time in milliseconds.
            end_time: End time in milliseconds.

        Returns:
            List of historical orders.
        """
        params: dict[str, Any] = {"limit": min(limit, 500)}

        if symbol:
            params["symbol"] = symbol.upper()
        if order_id:
            params["orderId"] = order_id
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time

        data = await self._client.get("/openApi/swap/v2/trade/allOrders", params)

        if isinstance(data, list):
            return [OrderInfo.model_validate(item) for item in data]
        return []

    async def set_leverage(
        self, symbol: str, leverage: int, side: str = "LONG"
    ) -> dict[str, Any]:
        """Set leverage for a trading pair.

        Args:
            symbol: Trading pair.
            leverage: Leverage multiplier (1-125).
            side: LONG or SHORT.

        Returns:
            Response with updated leverage info.
        """
        params = {
            "symbol": symbol.upper(),
            "leverage": leverage,
            "side": side.upper(),
        }
        data = await self._client.post("/openApi/swap/v2/trade/leverage", params)
        logger.info(f"Leverage set: {symbol} {leverage}x {side}")
        return data

    async def close_position(self, symbol: str, position_id: str | None = None) -> dict[str, Any]:
        """Close an open position by positionId.

        Args:
            symbol: Trading pair.
            position_id: Position ID from get_positions. If None, closes all positions.

        Returns:
            Close position response.
        """
        params: dict[str, Any] = {"symbol": symbol.upper()}
        if position_id:
            params["positionId"] = position_id
            data = await self._client.post("/openApi/swap/v1/trade/closePosition", params)
        else:
            data = await self._client.post("/openApi/swap/v2/trade/closeAllPositions", params)
        logger.info(f"Position closed: {symbol} positionId={position_id}")
        return data
        """Get current leverage for a symbol.

        Args:
            symbol: Trading pair.

        Returns:
            Current leverage settings.
        """
        params = {"symbol": symbol.upper()}
        return await self._client.get("/openApi/swap/v2/trade/leverage", params)
