"""
Kiro Async API Client

Handles async communication with AWS CodeWhisperer API for usage limits.
"""

from typing import Any

import aiohttp


class AsyncKiroAPI:
    """Async client for Kiro (AWS CodeWhisperer) API operations."""

    KIRO_ENDPOINT_TEMPLATE = "https://codewhisperer.{region}.amazonaws.com/getUsageLimits"
    DEFAULT_REGION = "us-east-1"
    DEFAULT_TIMEOUT = 30

    def __init__(self, timeout: int = DEFAULT_TIMEOUT):
        """Initialize the async Kiro API client.

        Args:
            timeout: Request timeout in seconds.
        """
        self.timeout = timeout

    async def query_usage(
        self, session: aiohttp.ClientSession, access_token: str, region: str = "us-east-1"
    ) -> dict[str, Any]:
        """Query Kiro usage limits from AWS CodeWhisperer API.

        Args:
            session: aiohttp client session.
            access_token: Valid Kiro access token.
            region: AWS region (e.g., 'us-east-1'). Defaults to 'us-east-1'.

        Returns:
            Usage limits response dictionary. Contains 'error' key if request failed.
        """
        region = region or self.DEFAULT_REGION
        endpoint = self.KIRO_ENDPOINT_TEMPLATE.format(region=region)
        url = f"{endpoint}?isEmailRequired=true&origin=AI_EDITOR&resourceType=AGENTIC_REQUEST"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "amz-sdk-request": "attempt=1; max=1",
            "x-amzn-kiro-agent-mode": "vibe",
            "x-amz-user-agent": "aws-sdk-js/1.0.0 KiroIDE-0.8.140-BalanceQuery",
            "User-Agent": "aws-sdk-js/1.0.0 ua/2.1 os/windows lang/python api/codewhispererruntime#1.0.0 m/E KiroIDE-0.8.140-BalanceQuery",
            "Connection": "close",
        }

        try:
            async with session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as resp:
                resp.raise_for_status()
                return await resp.json()
        except (aiohttp.ClientError, TimeoutError) as e:
            return {"error": str(e)}
