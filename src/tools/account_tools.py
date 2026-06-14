"""MCP tools for account operations (balance, positions)."""

import json
from typing import Optional

from mcp.server.fastmcp import FastMCP

from src.api.client import BingXClient
from src.services.account import AccountService

mcp = FastMCP("bingx-account", include_fastmcp_meta=False)
_client = BingXClient()
_service = AccountService(_client)


@mcp.tool()
async def get_balance() -> str:
    """Get account balance information.

    Returns total balance, available balance, unrealized PnL,
    margin balance, and per-asset breakdown.
    """
    try:
        balance = await _service.get_balance()
        result = {
            "total_balance_usdt": balance.total_balance,
            "available_balance_usdt": balance.available_balance,
            "unrealized_pnl_usdt": balance.unrealized_pnl,
            "margin_balance_usdt": balance.margin_balance,
            "assets": [
                {
                    "asset": a.asset,
                    "balance": a.balance,
                    "available": a.available_balance,
                    "equity": a.equity,
                }
                for a in balance.assets
            ],
        }
        return json.dumps(result, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2, ensure_ascii=False)


@mcp.tool()
async def get_positions(symbol: Optional[str] = None) -> str:
    """Get current open positions.

    Args:
        symbol: Trading pair to filter by (e.g. BTC-USDT). Optional.

    Returns position details: symbol, side, leverage, entry price,
    mark price, liquidation price, unrealized PnL, quantity.
    """
    try:
        positions = await _service.get_positions(symbol)
        result = [
            {
                "symbol": p.symbol,
                "position_side": p.position_side,
                "leverage": p.leverage,
                "entry_price": p.entry_price,
                "mark_price": p.mark_price,
                "liquidation_price": p.liquidation_price,
                "unrealized_pnl": p.unrealized_profit,
                "quantity": p.position_amt,
                "margin": p.margin,
                "notional": p.notional,
                "isolated": p.isolated,
            }
            for p in positions
        ]
        return json.dumps(result, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2, ensure_ascii=False)
