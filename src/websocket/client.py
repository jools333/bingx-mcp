"""WebSocket client for BingX real-time market data streams.

Supports:
- Ticker stream
- Trade stream
- Order book depth stream (partial)
- Kline/candlestick stream

Features:
- Automatic reconnection with exponential backoff
- Heartbeat/ping-pong
- Backoff retry
"""

import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from typing import Any, Optional

from loguru import logger
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException
from websockets.asyncio.client import ClientConnection

from src.utils.config import config


WS_BASE_URL = "wss://open-api-ws.bingx.com"
WS_VST_URL = "wss://open-api-ws-vst.bingx.com"


class BingXWebSocket:
    """BingX WebSocket client for real-time market data.

    Handles connection lifecycle, automatic reconnection, and message distribution
    to registered callbacks.
    """

    SUBSCRIBE_TOPICS = {
        "ticker": "{symbol}@ticker",
        "trades": "{symbol}@trade",
        "depth": "{symbol}@depth",
        "kline": "{symbol}@kline_{interval}",
    }

    def __init__(
        self,
        symbol: str,
        streams: list[str] | None = None,
        intervals: dict[str, str] | None = None,
        on_message: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    ) -> None:
        """Initialize the WebSocket client.

        Args:
            symbol: Trading pair (e.g. BTC-USDT).
            streams: List of stream types to subscribe to
                     (e.g. ["ticker", "trades", "depth", "kline"]).
            intervals: Additional intervals for kline stream
                       (e.g. {"kline": "1m"}).
            on_message: Async callback for received messages.
        """
        self.symbol = symbol.upper()
        self.streams = streams or ["ticker"]
        self.intervals = intervals or {}
        self._on_message = on_message
        self._ws: ClientConnection | None = None
        self._running = False
        self._reconnect_delay = 1.0
        self._max_reconnect_delay = 60.0
        self._id_counter = 0

        self._callbacks: dict[str, list[Callable[[dict[str, Any]], Awaitable[None]]]] = {}
        for stream in self.streams:
            self._callbacks[stream] = []

    def add_callback(
        self,
        stream: str,
        callback: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        """Register a callback for a specific stream type.

        Args:
            stream: Stream type (ticker, trades, depth, kline).
            callback: Async function to call with parsed message data.
        """
        if stream not in self._callbacks:
            self._callbacks[stream] = []
        self._callbacks[stream].append(callback)

    def _get_ws_url(self) -> str:
        """Get the WebSocket URL for the configured environment."""
        return {
            "prod-live": f"{WS_BASE_URL}/ws",
            "prod-vst": f"{WS_VST_URL}/ws",
        }.get(config.env, f"{WS_BASE_URL}/ws")

    def _build_subscription_id(self, stream: str, extra: str = "") -> str:
        """Generate a unique subscription request ID."""
        self._id_counter += 1
        return f"sub_{stream}_{extra}_{self._id_counter}"

    def _make_subscribe_payload(self, stream: str) -> dict[str, Any]:
        """Build a subscription request payload for a given stream.

        Args:
            stream: Stream type (ticker, trades, depth, kline).

        Returns:
            Subscription request dict.
        """
        if stream == "kline":
            interval = self.intervals.get("kline", "1m")
            topic = self.SUBSCRIBE_TOPICS["kline"].format(symbol=self.symbol, interval=interval)
        else:
            topic = self.SUBSCRIBE_TOPICS[stream].format(symbol=self.symbol)

        return {
            "id": self._build_subscription_id(stream, topic),
            "dataType": topic,
            "data": {},
        }

    async def _send_subscriptions(self) -> None:
        """Send subscription requests for all configured streams."""
        if not self._ws:
            return

        for stream in self.streams:
            payload = self._make_subscribe_payload(stream)
            await self._ws.send(json.dumps(payload))
            logger.info(f"Subscribed to {stream} stream for {self.symbol}")

    async def _handle_message(self, raw: str) -> None:
        """Parse and dispatch an incoming WebSocket message.

        Args:
            raw: Raw JSON message string.
        """
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse WS message: {raw[:100]}")
            return

        # Handle subscription confirmations
        if "id" in data and "code" in data:
            if data.get("code") == 0:
                logger.info(f"Subscription confirmed: {data.get('id')}")
            else:
                logger.error(f"Subscription failed: {data}")
            return

        # Dispatch to registered callbacks
        data_type = data.get("dataType", data.get("e", ""))

        for stream in self.streams:
            topic_prefix = self.SUBSCRIBE_TOPICS[stream].split("{")[0]
            if topic_prefix in data_type or stream in data_type:
                for cb in self._callbacks.get(stream, []):
                    try:
                        await cb(data)
                    except Exception as e:
                        logger.error(f"Callback error for {stream}: {e}")

        if self._on_message:
            try:
                await self._on_message(data)
            except Exception as e:
                logger.error(f"Global callback error: {e}")

    async def connect(self) -> None:
        """Establish WebSocket connection and start message loop."""
        self._running = True
        url = self._get_ws_url()

        while self._running:
            try:
                logger.info(f"Connecting WebSocket to {url}")
                async with websockets.connect(url) as ws:
                    self._ws = ws
                    self._reconnect_delay = 1.0

                    await self._send_subscriptions()

                    while self._running:
                        try:
                            message = await asyncio.wait_for(ws.recv(), timeout=3600)
                            await self._handle_message(message)
                        except asyncio.TimeoutError:
                            await ws.ping()
                            logger.debug("WebSocket heartbeat sent")
                        except ConnectionClosed as e:
                            logger.warning(f"WebSocket closed: {e}")
                            break

            except (WebSocketException, OSError) as e:
                if not self._running:
                    break
                logger.error(f"WebSocket error: {e}. Reconnecting...")
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(
                    self._reconnect_delay * 2, self._max_reconnect_delay
                )

        logger.info("WebSocket connection loop ended")

    async def disconnect(self) -> None:
        """Gracefully close the WebSocket connection."""
        self._running = False
        if self._ws:
            await self._ws.close()
            self._ws = None

    async def start(self) -> None:
        """Start the WebSocket client (convenience wrapper)."""
        await self.connect()
