"""Account service for BingX perpetual futures.

Handles balance queries, position tracking, and account-related operations.
"""

from typing import Optional

from loguru import logger

from src.api.client import BingXClient
from src.models.account import AccountBalance, AssetBalance, Position


class AccountService:
    """Service for BingX perpetual futures account data."""

    def __init__(self, client: BingXClient | None = None) -> None:
        """Initialize the account service.

        Args:
            client: BingX API client instance.
        """
        self._client = client or BingXClient()

    async def get_balance(self) -> AccountBalance:
        """Get account balance information.

        The v3 balance endpoint returns a list of per-asset account data.
        We aggregate fields across all assets.

        Returns:
            Account balance with total, available, unrealized PnL, and per-asset breakdown.
        """
        data = await self._client.get("/openApi/swap/v3/user/balance")

        if isinstance(data, dict):
            items = [data]
        elif isinstance(data, list):
            items = data
        else:
            items = []

        total_balance = 0.0
        total_available = 0.0
        total_unrealized = 0.0
        total_equity = 0.0
        assets: list[AssetBalance] = []

        for a in items:
            asset_bal = AssetBalance.model_validate(a)
            total_balance += asset_bal.balance
            total_available += asset_bal.available_balance
            total_unrealized += asset_bal.cross_un_pnl
            total_equity += asset_bal.equity
            assets.append(asset_bal)

        return AccountBalance(
            total_balance=round(total_balance, 4),
            available_balance=round(total_available, 4),
            unrealized_pnl=round(total_unrealized, 4),
            margin_balance=round(total_equity, 4),
            assets=assets,
        )

    async def get_positions(self, symbol: Optional[str] = None) -> list[Position]:
        """Get open positions.

        Args:
            symbol: Trading pair to filter by (optional).

        Returns:
            List of open positions.
        """
        params = {"symbol": symbol.upper()} if symbol else {}
        data = await self._client.get("/openApi/swap/v2/user/positions", params if params else None)

        if isinstance(data, list):
            return [Position.model_validate(item) for item in data]

        positions = []
        for item in data if isinstance(data, list) else [data]:
            try:
                positions.append(Position.model_validate(item))
            except Exception as e:
                logger.warning(f"Failed to parse position: {e}")
        return positions
