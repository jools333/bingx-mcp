"""Pydantic models for market data."""

from typing import Optional

from pydantic import BaseModel, Field


class TickerData(BaseModel):
    """24-hour ticker price change statistics."""

    symbol: str = Field(description="Trading pair")
    last_price: float = Field(alias="lastPrice", default=0.0, description="Last traded price")
    price_change: float = Field(alias="priceChange", default=0.0, description="Price change")
    price_change_percent: float = Field(alias="priceChangePercent", default=0.0, description="Price change percent")
    high_price: float = Field(alias="highPrice", default=0.0, description="24h highest price")
    low_price: float = Field(alias="lowPrice", default=0.0, description="24h lowest price")
    volume: float = Field(default=0.0, description="24h trading volume in base asset")
    quote_volume: float = Field(alias="quoteVolume", default=0.0, description="24h trading volume in quote asset")
    open_price: float = Field(alias="openPrice", default=0.0, description="24h opening price")
    open_time: int = Field(alias="openTime", default=0, description="Opening time (ms)")
    close_time: int = Field(alias="closeTime", default=0, description="Closing time (ms)")


class SimpleTicker(BaseModel):
    """Simplified ticker with bid/ask/spread."""

    symbol: str = Field(description="Trading pair")
    last_price: float = Field(default=0.0, description="Last traded price")
    bid_price: float = Field(default=0.0, description="Best bid price")
    ask_price: float = Field(default=0.0, description="Best ask price")
    spread: float = Field(default=0.0, description="Bid-ask spread (absolute)")
    spread_percent: float = Field(default=0.0, description="Bid-ask spread (percent)")


class BookTicker(BaseModel):
    """Best bid/ask price and quantity."""

    symbol: str = Field(description="Trading pair")
    bid_price: float = Field(alias="bid_price", default=0.0, description="Best bid price")
    bid_qty: float = Field(alias="bid_qty", default=0.0, description="Best bid quantity")
    ask_price: float = Field(alias="ask_price", default=0.0, description="Best ask price")
    ask_qty: float = Field(alias="ask_qty", default=0.0, description="Best ask quantity")


class OrderBookLevel(BaseModel):
    """A single order book level."""

    price: float = Field(description="Price level")
    quantity: float = Field(description="Quantity at this price level")


class OrderBook(BaseModel):
    """Order book depth data."""

    symbol: str = Field(description="Trading pair")
    bids: list[OrderBookLevel] = Field(default_factory=list, description="Bid levels")
    asks: list[OrderBookLevel] = Field(default_factory=list, description="Ask levels")
    bid_volume: float = Field(default=0.0, description="Total bid volume in quote asset")
    ask_volume: float = Field(default=0.0, description="Total ask volume in quote asset")
    imbalance: float = Field(default=0.0, description="Order book imbalance ratio")


class Kline(BaseModel):
    """OHLCV candlestick data."""

    open_time: int = Field(description="Candle open time (ms)")
    open: float = Field(description="Open price")
    high: float = Field(description="High price")
    low: float = Field(description="Low price")
    close: float = Field(description="Close price")
    volume: float = Field(description="Volume in base asset")
    close_time: int = Field(description="Candle close time (ms)")
    quote_volume: float = Field(default=0.0, description="Volume in quote asset")
    trades: int = Field(default=0, description="Number of trades")


class RecentTrade(BaseModel):
    """Recent public trade."""

    id: str | int = Field(default="", description="Trade ID")
    price: float = Field(default=0.0, description="Trade price")
    quantity: float = Field(alias="qty", default=0.0, description="Trade quantity")
    time: int = Field(default=0, description="Trade timestamp (ms)")
    is_buyer_maker: bool = Field(alias="isBuyerMaker", default=False, description="True if buyer is maker")
    quote_qty: str = Field(alias="quoteQty", default="0", description="Trade amount in quote asset")


class OpenInterestData(BaseModel):
    """Open interest information."""

    symbol: str = Field(description="Trading pair")
    open_interest: str = Field(alias="openInterest", default="0", description="Open interest amount")
    timestamp: int = Field(default=0, description="Timestamp (ms)")


class FundingRateData(BaseModel):
    """Funding rate information."""

    symbol: str = Field(description="Trading pair")
    mark_price: str = Field(alias="markPrice", default="0", description="Mark price")
    index_price: str = Field(alias="indexPrice", default="0", description="Index price")
    funding_rate: str = Field(alias="lastFundingRate", default="0", description="Last funding rate")
    next_funding_time: int = Field(alias="nextFundingTime", default=0, description="Next funding time (ms)")
    interest_rate: str = Field(alias="interestRate", default="0", description="Interest rate")
    time: int = Field(default=0, description="Timestamp (ms)")


class LongShortRatio(BaseModel):
    """Long/short account ratio data."""

    symbol: str = Field(description="Trading pair")
    long_ratio: float = Field(default=0.0, description="Long account ratio")
    short_ratio: float = Field(default=0.0, description="Short account ratio")
    long_short_ratio: float = Field(default=0.0, description="Long/Short ratio")
    timestamp: int = Field(default=0, description="Timestamp (ms)")


class TakerFlow(BaseModel):
    """Taker buy/sell volume data."""

    symbol: str = Field(description="Trading pair")
    taker_buy_volume: float = Field(default=0.0, description="Taker buy volume")
    taker_sell_volume: float = Field(default=0.0, description="Taker sell volume")
    delta: float = Field(default=0.0, description="Buy - Sell delta")
    timestamp: int = Field(default=0, description="Timestamp (ms)")
