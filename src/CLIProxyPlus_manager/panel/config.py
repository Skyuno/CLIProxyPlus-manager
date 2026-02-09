"""
CLIProxyPlus Panel Configuration

Handles configuration loading from config.yaml file.
Supports multiple panel configurations.
"""

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class PanelConfig:
    """Configuration for a single CLIProxyPlus panel connection."""

    name: str = "default"
    base_url: str = "http://127.0.0.1:8080"
    management_key: str = "your-management-key-here"
    timeout: int = 30

    def __str__(self) -> str:
        return f"{self.name} ({self.base_url})"


@dataclass
class AppConfig:
    """Application-level configuration containing global settings and all panels."""

    timeout: int = 30
    panels: list[PanelConfig] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, config_path: Path | None = None) -> "AppConfig":
        """Load configuration from a YAML file.

        Args:
            config_path: Path to config.yaml file.
                         If None, looks for config.yaml in project root.

        Returns:
            AppConfig instance with loaded values.

        Raises:
            FileNotFoundError: If config file does not exist.
            ValueError: If config file is invalid.
        """
        if config_path is None:
            config_path = Path(__file__).resolve().parents[3] / "config.yaml"

        if not config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {config_path}\n"
                f"Please copy config.example.yaml to config.yaml and fill in your values."
            )

        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data:
            raise ValueError(f"Configuration file is empty: {config_path}")

        # Parse global settings
        global_cfg = data.get("global", {})
        global_timeout = global_cfg.get("timeout", 30)

        # Parse panels
        panels_data = data.get("panels", [])
        if not panels_data:
            raise ValueError(
                f"No panels configured in {config_path}\n"
                f"Please add at least one panel to the 'panels' section."
            )

        panels = []
        for idx, panel_data in enumerate(panels_data):
            if not isinstance(panel_data, dict):
                raise ValueError(f"Invalid panel configuration at index {idx}")

            panels.append(PanelConfig(
                name=panel_data.get("name", f"Panel {idx + 1}"),
                base_url=panel_data.get("url", "http://127.0.0.1:8080").rstrip("/"),
                management_key=panel_data.get("key", "your-management-key-here"),
                timeout=panel_data.get("timeout", global_timeout),
            ))

        return cls(
            timeout=global_timeout,
            panels=panels,
        )
