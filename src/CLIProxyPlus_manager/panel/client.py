"""
CLIProxyPlus Panel API Client

Provides methods for interacting with the CLIProxyPlus management API.
"""

from typing import Any

import requests

from .config import PanelConfig


class PanelClient:
    """Client for CLIProxyPlus management API operations."""
    
    def __init__(self, config: PanelConfig | None = None):
        """Initialize the panel client.
        
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
    
    def list_auth_files(self) -> list[dict[str, Any]]:
        """Fetch list of auth files from management API.
        
        Returns:
            List of auth file metadata dictionaries.
        """
        url = f"{self.config.base_url}/v0/management/auth-files"
        
        try:
            resp = requests.get(
                url, 
                headers=self._get_auth_headers(), 
                timeout=self.config.timeout
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("files", [])
        except requests.RequestException as e:
            print(f"❌ Failed to list auth files: {e}")
            return []
    
    def download_auth_file(self, filename: str) -> dict[str, Any] | None:
        """Download auth file content from management API.
        
        Args:
            filename: Name of the auth file to download.
        
        Returns:
            Auth file content as dictionary, or None if failed.
        """
        url = f"{self.config.base_url}/v0/management/auth-files/download"
        params = {"name": filename}
        
        try:
            resp = requests.get(
                url, 
                headers=self._get_auth_headers(), 
                params=params, 
                timeout=self.config.timeout
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            print(f"❌ Failed to download {filename}: {e}")
            return None
    
    def list_kiro_files(self) -> list[dict[str, Any]]:
        """Fetch only Kiro auth files from management API.
        
        Returns:
            List of Kiro auth file metadata dictionaries.
        """
        files = self.list_auth_files()
        return [f for f in files if f.get("provider", "").lower() == "kiro"]
