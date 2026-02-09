"""
CLIProxyPlus Panel Async API Client

Provides async methods for interacting with the CLIProxyPlus management API.
"""

from typing import Any

import aiohttp

from .config import PanelConfig


class AsyncPanelClient:
    """Async client for CLIProxyPlus management API operations."""

    def __init__(self, config: PanelConfig | None = None):
        """Initialize the async panel client.

        Args:
            config: PanelConfig instance. If None, uses default configuration.
        """
        self.config = config or PanelConfig()

    def _get_auth_headers(self) -> dict[str, str]:
        """Get headers for management API authentication."""
        return {
            "Authorization": f"Bearer {self.config.management_key}",
            "Content-Type": "application/json",
        }

    async def list_auth_files(self, session: aiohttp.ClientSession) -> list[dict[str, Any]]:
        """Fetch list of auth files from management API.

        Args:
            session: aiohttp client session.

        Returns:
            List of auth file metadata dictionaries.
        """
        url = f"{self.config.base_url}/v0/management/auth-files"

        try:
            async with session.get(
                url,
                headers=self._get_auth_headers(),
                timeout=aiohttp.ClientTimeout(total=self.config.timeout),
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data.get("files", [])
        except (aiohttp.ClientError, TimeoutError) as e:
            print(f"❌ Failed to list auth files from {self.config.name}: {e}")
            return []

    async def download_auth_file(
        self, session: aiohttp.ClientSession, filename: str
    ) -> dict[str, Any] | None:
        """Download auth file content from management API.

        Args:
            session: aiohttp client session.
            filename: Name of the auth file to download.

        Returns:
            Auth file content as dictionary, or None if failed.
        """
        url = f"{self.config.base_url}/v0/management/auth-files/download"
        params = {"name": filename}

        try:
            async with session.get(
                url,
                headers=self._get_auth_headers(),
                params=params,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout),
            ) as resp:
                resp.raise_for_status()
                return await resp.json()
        except (aiohttp.ClientError, TimeoutError) as e:
            print(f"❌ Failed to download {filename} from {self.config.name}: {e}")
            return None

    async def list_kiro_files(self, session: aiohttp.ClientSession) -> list[dict[str, Any]]:
        """Fetch only Kiro auth files from management API.

        Args:
            session: aiohttp client session.

        Returns:
            List of Kiro auth file metadata dictionaries.
        """
        files = await self.list_auth_files(session)
        return [f for f in files if f.get("provider", "").lower() == "kiro"]
