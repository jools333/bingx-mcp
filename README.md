# BingX MCP Server

Production-ready MCP (Model Context Protocol) server for the BingX cryptocurrency exchange. Enables LLM agents to access BingX market data and execute trades through the official BingX API.

## Features

- **Market Data**: Ticker, OHLCV/candles, order book depth, recent trades, funding rate, open interest
- **Account**: Balance, open positions, PnL
- **Trading**: Create/cancel orders, order history, leverage management
- **Scalping Metrics**: Spread, orderbook imbalance, buy/sell delta, volume spike, ATR, RSI, VWAP
- **Technical Indicators**: EMA, SMA, VWAP, RSI, ATR, MACD, Bollinger Bands, Volume Delta, CVD, Momentum, ROC
- **WebSocket Client**: Real-time streams with auto-reconnect
- **Security**: HMAC-SHA256 signature, rate limiting, retry logic, structured logging

## Architecture

```
bingx-mcp2/
├── src/
│   ├── api/
│   │   └── client.py          # HTTP client with HMAC-SHA256 auth
│   ├── services/
│   │   ├── market.py          # Market data service
│   │   ├── account.py         # Account/balance service
│   │   ├── trade.py           # Trading operations service
│   │   └── indicators.py      # Technical indicator calculations
│   ├── tools/
│   │   ├── account_tools.py   # Balance, positions MCP tools
│   │   ├── trade_tools.py     # Order, leverage MCP tools
│   │   ├── market_tools.py    # Ticker, klines, orderbook MCP tools
│   │   └── scalping_tools.py  # Indicators, scalping metrics MCP tools
│   ├── models/
│   │   ├── common.py          # Shared models
│   │   ├── market.py          # Market data Pydantic models
│   │   ├── account.py         # Account Pydantic models
│   │   └── trade.py           # Trade Pydantic models
│   ├── utils/
│   │   ├── config.py          # Environment configuration
│   │   ├── logging.py         # Loguru structured logging
│   │   ├── ratelimit.py       # Token-bucket rate limiter
│   │   └── retry.py           # Exponential backoff retry
│   └── websocket/
│       └── client.py          # WebSocket client with auto-reconnect
├── main.py                    # Entry point
├── requirements.txt
├── .env.example
└── README.md
```

## Installation

### Prerequisites

- Python 3.12+
- BingX API Key and Secret Key

### Setup

```bash
# Clone the repository
git clone <repo-url> bingx-mcp2
cd bingx-mcp2

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env with your credentials
```

### Environment Variables

Create a `.env` file:

```env
BINGX_API_KEY=your_bingx_api_key
BINGX_SECRET_KEY=your_bingx_secret_key
BINGX_ENV=prod-live       # or 'prod-vst' for demo environment
```

### Getting API Keys

1. Log in to [BingX](https://bingx.com)
2. Navigate to **API Management** under your user menu
3. Click **Create API**
4. Set permissions: enable **Perpetual Futures Trading** (at minimum)
5. Save the API Key and Secret Key securely

## Usage

### Starting the Server

**Stdio transport** (default, for Claude Desktop / Cursor):

```bash
python main.py
```

**SSE transport** (for HTTP-based clients, OpenAI Agents SDK):

```bash
python main.py --sse --host 0.0.0.0 --port 8000
```

### MCP Tools Reference

| Tool | Description | Auth |
|------|-------------|------|
| `get_balance` | Total/available balance, unrealized PnL, per-asset | Yes |
| `get_positions` | Open positions with entry price, mark price, liq price | Yes |
| `get_open_orders` | Currently open orders | Yes |
| `get_order_history` | Historical orders with time/count filters | Yes |
| `create_order` | Create MARKET/LIMIT/STOP/TAKE_PROFIT orders | Yes |
| `cancel_order` | Cancel order by ID | Yes |
| `cancel_all_orders` | Cancel all open orders for a symbol | Yes |
| `set_leverage` | Set leverage (1-125x) | Yes |
| `get_ticker` | Last price, bid, ask, spread | No |
| `get_klines` | OHLCV candlestick data (all intervals) | No |
| `get_orderbook` | Order book depth with imbalance | No |
| `get_recent_trades` | Recent public trades | No |
| `get_open_interest` | Open interest | No |
| `get_funding_rate` | Funding rate, mark price, index price | No |
| `get_long_short_ratio` | Long/short ratio from trades | No |
| `get_taker_flow` | Taker buy/sell volume delta | No |
| `calculate_indicators` | EMA, SMA, RSI, MACD, BB, VWAP, ATR, etc. | No |
| `get_scalping_metrics` | Comprehensive scalping snapshot | No |

### Order Types Supported

```python
# Market order
create_order(symbol="BTC-USDT", side="BUY", type="MARKET", quantity=0.01)

# Limit order
create_order(symbol="BTC-USDT", side="SELL", type="LIMIT", quantity=0.01, price=100000)

# Stop-loss market
create_order(symbol="BTC-USDT", side="SELL", type="STOP_MARKET", quantity=0.01, stop_price=95000)

# Stop-loss limit
create_order(symbol="BTC-USDT", side="SELL", type="STOP", quantity=0.01, price=94900, stop_price=95000)

# Take-profit market
create_order(symbol="BTC-USDT", side="SELL", type="TAKE_PROFIT_MARKET", quantity=0.01, stop_price=105000)

# Take-profit limit
create_order(symbol="BTC-USDT", side="SELL", type="TAKE_PROFIT", quantity=0.01, price=105100, stop_price=105000)
```

## Claude Desktop Integration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "bingx": {
      "command": "python",
      "args": ["/absolute/path/to/bingx-mcp2/main.py"],
      "env": {
        "BINGX_API_KEY": "your_api_key",
        "BINGX_SECRET_KEY": "your_secret_key"
      }
    }
  }
}
```

## Cursor Integration

Add to Cursor's MCP configuration (`~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "bingx": {
      "command": "python",
      "args": ["/absolute/path/to/bingx-mcp2/main.py"],
      "env": {
        "BINGX_API_KEY": "your_api_key",
        "BINGX_SECRET_KEY": "your_secret_key"
      }
    }
  }
}
```

## OpenAI Agents SDK Integration

Run the server in SSE mode:

```bash
python main.py --sse --port 8000
```

Then connect in your agent:

```python
from agents import Agent, Runner
from agents.mcp import MCPServerSse

async def main():
    async with MCPServerSse(
        name="bingx",
        params={
            "url": "http://localhost:8000/sse",
        },
    ) as server:
        agent = Agent(
            name="trading_agent",
            instructions="You are a crypto trading assistant with access to BingX market data.",
            mcp_servers=[server],
        )
        result = await Runner.run(agent, "What's the current BTC price and order book imbalance?")
        print(result.final_output)
```

## Technical Details

### API Endpoints Used

Based on the [official BingX API documentation](https://bingx-api.github.io/docs):

| Category | Endpoint | Method |
|----------|----------|--------|
| Market | `/openApi/swap/v2/quote/ticker` | GET |
| Market | `/openApi/swap/v2/quote/bookTicker` | GET |
| Market | `/openApi/swap/v2/quote/depth` | GET |
| Market | `/openApi/swap/v2/quote/trades` | GET |
| Market | `/openApi/swap/v3/quote/klines` | GET |
| Market | `/openApi/swap/v2/quote/openInterest` | GET |
| Market | `/openApi/swap/v2/quote/premiumIndex` | GET |
| Account | `/openApi/swap/v3/user/balance` | GET |
| Account | `/openApi/swap/v2/user/positions` | GET |
| Trade | `/openApi/swap/v2/trade/order` | POST |
| Trade | `/openApi/swap/v2/trade/order` | DELETE |
| Trade | `/openApi/swap/v2/trade/openOrders` | GET |
| Trade | `/openApi/swap/v2/trade/allOrders` | GET |
| Trade | `/openApi/swap/v2/trade/allOpenOrders` | DELETE |
| Trade | `/openApi/swap/v2/trade/leverage` | POST |

### Authentication

Requests are signed using HMAC-SHA256:

1. Parameters are sorted alphabetically
2. Query string is built: `param1=value1&param2=value2&...&timestamp=...`
3. HMAC-SHA256 signature is computed with the secret key and hex-encoded
4. Signature is appended: `querystring&signature=...`

### Rate Limiting

The client enforces BingX API rate limits:
- Market data: 500 requests/10 seconds per IP
- Account/Trade: 5-10 requests/second

### Error Handling

- Automatic retry with exponential backoff (max 3 attempts)
- Domain fallback (bingx.com -> bingx.pro)
- Structured logging to stderr and rotating log files
- All errors returned as JSON with descriptive messages

## License

MIT
