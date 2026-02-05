"""
CLIProxyPlus Panel Configuration

Handles configuration loading from environment variables and .env files.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class PanelConfig:
    """Configuration for CLIProxyPlus panel connection."""
    
    base_url: str = field(default_factory=lambda: os.getenv("CLIPROXY_URL", "http://127.0.0.1:8080"))
    management_key: str = field(default_factory=lambda: os.getenv("CLIPROXY_KEY", "your-management-key-here"))
    timeout: int = 30
    
    @classmethod
    def from_env(cls, env_path: Path | None = None) -> "PanelConfig":
        """Load configuration from environment variables.
        
        Args:
            env_path: Optional path to .env file. If None, looks for .env in current directory.
        
        Returns:
            PanelConfig instance with loaded values.
        """
        if env_path:
            load_dotenv(env_path)
        else:
            load_dotenv()
        
        return cls(
            base_url=os.getenv("CLIPROXY_URL", "http://127.0.0.1:8080"),
            management_key=os.getenv("CLIPROXY_KEY", "your-management-key-here"),
            timeout=int(os.getenv("CLIPROXY_TIMEOUT", "30")),
        )
