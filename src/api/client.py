"""HTTP API client for BingX with HMAC-SHA256 signature authentication.

Signature generation follows the official BingX API documentation:
1. Sort all parameters alphabetically (excluding 'signature').
2. Build query string: param1=value1&param2=value2&...&timestamp=...
3. Sign with HMAC-SHA256 using the secret key, encode as hex.
4. Append &signature=... to the query string.
5. For GET/DELETE: append query string to URL.
6. For POST: send as form-encoded body.
"""

import hashlib
import hmac
import time
from collections.abc import Mapping
from typing import Any

import httpx
from loguru import logger

from src.utils.config import config
from src.utils.ratelimit import rate_limiter
from src.utils.retry import retry

DEFAULT_TIMEOUT = 15.0


class BingXClient:
    """Async HTTP client for the BingX API.

    Handles signature generation, request execution, rate limiting,
    retry logic, and domain fallback.
    """

    def __init__(
        self,
        api_key: str | None = None,
        secret_key: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize the BingX API client.

        Args:
            api_key: BingX API key. Defaults to BINGX_API_KEY env var.
            secret_key: BingX secret key. Defaults to BINGX_SECRET_KEY env var.
            timeout: Request timeout in seconds.
        """
        self.api_key = api_key or config.api_key
        self.secret_key = secret_key or config.secret_key
        self.base_urls = config.base_urls
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the httpx async client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _generate_signature(self, params: dict[str, Any]) -> str:
        """Generate HMAC-SHA256 signature for the request.

        Based on the official BingX AI Skills reference implementation:
        - Sort parameters alphabetically
        - Build query string (excluding signature)
        - HMAC-SHA256 with secret key, hex encoded

        Args:
            params: Request parameters dict (must include 'timestamp').

        Returns:
            Hex-encoded HMAC-SHA256 signature string.
        """
        sorted_keys = sorted(params.keys())
        query_string = "&".join(f"{k}={params[k]}" for k in sorted_keys)

        signature = hmac.new(
            self.secret_key.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return f"{query_string}&signature={signature}"

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a signed API request with retry and domain fallback.

        Args:
            method: HTTP method (GET, POST, DELETE).
            path: API endpoint path (e.g. /openApi/swap/v2/quote/ticker).
            params: Request parameters (timestamp is added automatically).

        Returns:
            Parsed JSON response data from the 'data' field.

        Raises:
            ValueError: If credentials are not configured.
            RuntimeError: If the API returns an error code.
            httpx.HTTPError: On network errors after all retries.
        """
        if not self.api_key or not self.secret_key:
            raise ValueError(
                "API credentials not configured. "
                "Set BINGX_API_KEY and BINGX_SECRET_KEY environment variables."
            )

        if params is None:
            params = {}
        params["timestamp"] = int(time.time() * 1000)

        signed_query = self._generate_signature(params)
        client = await self._get_client()

        last_error: Exception | None = None

        for base_url in self.base_urls:
            try:
                await rate_limiter.acquire("api")

                headers = {
                    "X-BX-APIKEY": self.api_key,
                    "X-SOURCE-KEY": "BX-AI-SKILL",
                }

                if method.upper() in ("POST",):
                    headers["Content-Type"] = "application/x-www-form-urlencoded"
                    url = f"{base_url}{path}"
                    response = await client.post(
                        url,
                        content=signed_query,
                        headers=headers,
                    )
                else:
                    url = f"{base_url}{path}?{signed_query}"
                    response = await client.request(method.upper(), url, headers=headers)

                json_data = response.json()

                if json_data.get("code") != 0:
                    error_code = json_data.get("code", "unknown")
                    error_msg = json_data.get("msg", "Unknown error")
                    raise RuntimeError(f"BingX API error [{error_code}]: {error_msg}")

                return json_data.get("data", json_data)

            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(f"Timeout connecting to {base_url}: {e}")
            except httpx.NetworkError as e:
                last_error = e
                logger.warning(f"Network error connecting to {base_url}: {e}")
            except RuntimeError:
                raise

        raise last_error or RuntimeError("All base URLs exhausted")

    async def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute a signed GET request.

        Args:
            path: API endpoint path.
            params: Query parameters.

        Returns:
            Parsed JSON response data.
        """
        async def _do() -> dict[str, Any]:
            return await self._request("GET", path, params)

        return await retry(_do)

    async def post(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute a signed POST request.

        Args:
            path: API endpoint path.
            params: Request body parameters.

        Returns:
            Parsed JSON response data.
        """
        async def _do() -> dict[str, Any]:
            return await self._request("POST", path, params)

        return await retry(_do)

    async def delete(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute a signed DELETE request.

        Args:
            path: API endpoint path.
            params: Query parameters.

        Returns:
            Parsed JSON response data.
        """
        async def _do() -> dict[str, Any]:
            return await self._request("DELETE", path, params)

        return await retry(_do)
