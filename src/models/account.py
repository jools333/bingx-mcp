"""Pydantic models for account data."""

from typing import Optional

from pydantic import BaseModel, Field


class AssetBalance(BaseModel):
    """Balance of a single asset."""

    asset: str = Field(default="", description="Asset name")
    balance: float = Field(default=0.0, description="Total balance")
    available_balance: float = Field(alias="availableMargin", default=0.0, description="Available balance")
    cross_wallet_balance: float = Field(alias="balance", default=0.0, description="Cross wallet balance")
    cross_un_pnl: float = Field(alias="unrealizedProfit", default=0.0, description="Cross unrealized PnL")
    equity: float = Field(default=0.0, description="Equity")


class AccountBalance(BaseModel):
    """Full account balance."""

    total_balance: float = Field(alias="balance", default=0.0, description="Total balance in USDT")
    available_balance: float = Field(alias="availableBalance", default=0.0, description="Available balance")
    unrealized_pnl: float = Field(alias="unrealizedProfit", default=0.0, description="Total unrealized PnL")
    margin_balance: float = Field(alias="equity", default=0.0, description="Margin balance (equity)")
    assets: list[AssetBalance] = Field(default_factory=list, description="Per-asset balances")


class Position(BaseModel):
    """Open position data."""

    symbol: str = Field(description="Trading pair")
    position_side: str = Field(alias="positionSide", default="", description="LONG or SHORT")
    leverage: int = Field(default=1, description="Leverage")
    entry_price: float = Field(alias="avgPrice", default=0.0, description="Average entry price")
    mark_price: float = Field(alias="markPrice", default=0.0, description="Current mark price")
    liquidation_price: float = Field(alias="liquidationPrice", default=0.0, description="Estimated liquidation price")
    unrealized_profit: float = Field(alias="unrealizedProfit", default=0.0, description="Unrealized PnL")
    position_amt: float = Field(alias="positionAmt", default=0.0, description="Position amount (coins)")
    margin: float = Field(default=0.0, description="Position margin")
    initial_margin: float = Field(alias="initialMargin", default=0.0, description="Initial margin")
    maint_margin: float = Field(alias="maintMargin", default=0.0, description="Maintenance margin")
    notional: str = Field(alias="positionValue", default="0", description="Notional value")
    update_time: int = Field(alias="updateTime", default=0, description="Last update timestamp")
    isolated: bool = Field(default=False, description="Whether position is isolated")
    position_id: str = Field(alias="positionId", default="", description="Position ID")
