"""Shared Pydantic models used across the application."""

from pydantic import BaseModel, Field, field_validator


class BingXResponse(BaseModel):
    """Generic BingX API response wrapper."""

    code: int = Field(default=0, description="Response status code (0 = success)")
    msg: str = Field(default="", description="Response message")


class SymbolInfo(BaseModel):
    """Trading pair symbol information."""

    symbol: str = Field(description="Trading pair in BASE-QUOTE format (e.g. BTC-USDT)")
    base_asset: str = Field(default="", description="Base asset")
    quote_asset: str = Field(default="", description="Quote asset")

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """Validate symbol format."""
        import re

        if not re.match(r"^[A-Z0-9]+-[A-Z]+$", v):
            raise ValueError(f"Invalid symbol format: {v}. Expected BASE-QUOTE (e.g. BTC-USDT)")
        return v.upper()


class KlineInterval(BaseModel):
    """Valid kline/candlestick intervals."""

    value: str

    @field_validator("value")
    @classmethod
    def validate_interval(cls, v: str) -> str:
        valid = {"1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"}
        if v not in valid:
            raise ValueError(f"Invalid interval: {v}. Must be one of {sorted(valid)}")
        return v
