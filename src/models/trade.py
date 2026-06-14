"""Pydantic models for trade/order data."""

from typing import Optional

from pydantic import BaseModel, Field


class OrderInfo(BaseModel):
    """Order data as returned by BingX API."""

    symbol: str = Field(description="Trading pair")
    order_id: int = Field(alias="orderId", default=0, description="System order ID")
    client_order_id: str = Field(alias="clientOrderId", default="", description="Client-specified order ID")
    side: str = Field(default="", description="BUY or SELL")
    position_side: str = Field(alias="positionSide", default="", description="LONG or SHORT")
    type: str = Field(default="", description="Order type (MARKET, LIMIT, etc.)")
    orig_quantity: str = Field(alias="origQty", default="0", description="Original order quantity")
    executed_quantity: str = Field(alias="executedQty", default="0", description="Filled quantity")
    price: str = Field(default="0", description="Order price")
    stop_price: str = Field(alias="stopPrice", default="0", description="Stop/trigger price")
    status: str = Field(default="", description="Order status")
    working_type: str = Field(alias="workingType", default="", description="Working type")
    reduce_only: bool = Field(alias="reduceOnly", default=False, description="Reduce only flag")
    time: int = Field(default=0, description="Order creation time (ms)")
    update_time: int = Field(alias="updateTime", default=0, description="Last update time (ms)")
    avg_price: str = Field(alias="avgPrice", default="0", description="Average fill price")
    cum_quote: str = Field(alias="cumQuote", default="0", description="Cumulative quote asset transacted")
    profit: str = Field(default="0", description="Realized PnL")


class OrderRequest(BaseModel):
    """Parameters for creating an order."""

    symbol: str = Field(description="Trading pair (e.g. BTC-USDT)")
    side: str = Field(description="Order side: BUY or SELL")
    position_side: str = Field(default="LONG", alias="positionSide", description="LONG or SHORT")
    type: str = Field(description="Order type: MARKET, LIMIT, STOP_MARKET, STOP, TAKE_PROFIT_MARKET, TAKE_PROFIT")
    quantity: Optional[float] = Field(default=None, description="Order quantity in coins")
    price: Optional[float] = Field(default=None, description="Limit price (required for LIMIT orders)")
    stop_price: Optional[float] = Field(alias="stopPrice", default=None, description="Trigger price")
    time_in_force: str = Field(alias="timeInForce", default="GTC", description="GTC, IOC, FOK, PostOnly")
    reduce_only: bool = Field(alias="reduceOnly", default=False, description="Reduce position only")
    working_type: str = Field(alias="workingType", default="CONTRACT_PRICE", description="MARK_PRICE or CONTRACT_PRICE")
    client_order_id: str = Field(alias="clientOrderId", default="", description="Custom order ID")


class CancelOrderRequest(BaseModel):
    """Parameters for canceling an order."""

    symbol: str = Field(description="Trading pair")
    order_id: int = Field(alias="orderId", description="Order ID to cancel")


class SetLeverageRequest(BaseModel):
    """Parameters for setting leverage."""

    symbol: str = Field(description="Trading pair")
    leverage: int = Field(description="Leverage multiplier (1-125)", ge=1, le=125)
    side: str = Field(default="LONG", description="LONG or SHORT")
