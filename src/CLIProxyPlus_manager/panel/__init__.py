"""
CLIProxyPlus Panel Client Module

This module provides utilities for interacting with the CLIProxyPlus management API.
"""

from .client import PanelClient
from .config import PanelConfig

__all__ = ["PanelClient", "PanelConfig"]
