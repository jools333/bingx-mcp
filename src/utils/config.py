"""Application configuration loaded from environment variables."""

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    """Immutable configuration loaded from environment variables."""

    api_key: str = field(default_factory=lambda: os.getenv("BINGX_API_KEY", ""))
    secret_key: str = field(default_factory=lambda: os.getenv("BINGX_SECRET_KEY", ""))
    env: str = field(default_factory=lambda: os.getenv("BINGX_ENV", "prod-live"))

    @property
    def base_urls(self) -> list[str]:
        """Return base URLs for the configured environment."""
        urls = {
            "prod-live": ["https://open-api.bingx.com", "https://open-api.bingx.pro"],
            "prod-vst": ["https://open-api-vst.bingx.com", "https://open-api-vst.bingx.pro"],
        }
        return urls.get(self.env, urls["prod-live"])

    @property
    def is_configured(self) -> bool:
        """Check if API credentials are properly configured."""
        return bool(self.api_key and self.secret_key)

    @property
    def is_demo(self) -> bool:
        """Check if running in demo/VST environment."""
        return self.env == "prod-vst"


config = Config()
