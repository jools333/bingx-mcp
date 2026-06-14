# AGENTS.md

## Environment & setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill BINGX_API_KEY + BINGX_SECRET_KEY
```

Optional: set `BINGX_ENV=prod-vst` in `.env` to use the demo/VST environment (no real funds, different base URLs).

## Running

```bash
python main.py            # stdio transport (Claude Desktop, Cursor)
python main.py --sse      # SSE transport at http://0.0.0.0:8000/sse
python main.py --sse --port 9000
```

## Architecture

Single-file MCP server (`main.py`) using FastMCP. All 18 tools are registered on one `FastMCP` instance via `@mcp.tool()` decorators. The file is ~430 lines — tools are grouped under section comments.

**Services** under `src/services/` wrap the raw HTTP client and return Pydantic models. Tools in `main.py` call services and serialize results to JSON strings (MCP convention).

**API client** (`src/api/client.py`) handles:
- HMAC-SHA256 hex signature (key → `X-BX-APIKEY` header, all params sorted, signed with secret)
- Domain fallback: `open-api.bingx.com` → `open-api.bingx.pro`
- Rate limiting (default 5 req/s per endpoint category)
- Retry via `src/utils/retry.py` (3 attempts, exponential backoff with jitter)
- POST sends form-encoded body, not JSON; GET/DELETE append signed query to URL

## No test/lint/typecheck commands exist

This is a new project. The only verification performed was:
```bash
python -c "from src.services.indicators import calculate_indicators; ..."
python -c "from main import mcp; ..."
```

When making changes, verify imports still work and indicator calculations produce expected values.

## Key quirks

- **`get_long_short_ratio` and `get_taker_flow` are not direct API endpoints.** They are calculated client-side from recent trade data (buyer-maker logic). BingX does not expose these natively.
- **Signature is hex, not base64.** Some old BingX docs mention base64 — ignore them. The current API uses hex-encoded HMAC-SHA256.
- **`BINGX_ENV` controls both REST and WebSocket base URLs.** Switching to `prod-vst` changes all endpoints.
- **`INDICATOR_MAP` format** in `src/services/indicators.py`: each entry is `(function, [required_fields], needs_period: bool)`. Adding a new indicator requires following this exact tuple format.
- **All tools return JSON strings**, not dicts. The `_to_json()` helper recursively serializes Pydantic models via `model_dump()`.
- **`dotenv.load_dotenv()` fires in two places**: `src/utils/config.py` (module-level import) and `main.py`. The config singleton is frozen (`@dataclass(frozen=True)`).
