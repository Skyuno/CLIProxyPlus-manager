"""
Kiro Usage Formatter

Formats and displays Kiro usage information.
"""

from datetime import datetime
from typing import Any


class UsageFormatter:
    """Formats Kiro usage data for display."""
    
    @staticmethod
    def format_summary(usage: dict[str, Any]) -> dict[str, Any]:
        """Extract summary information from usage response.
        
        Args:
            usage: Raw usage response from Kiro API.
        
        Returns:
            Formatted summary dictionary.
        """
        if "error" in usage:
            return {"error": usage["error"]}
        
        breakdown_list = usage.get("usageBreakdownList", [])
        user_info = usage.get("userInfo", {})
        subscription_info = usage.get("subscriptionInfo", {})
        
        total_limit = 0.0
        total_usage = 0.0
        details = []
        
        for item in breakdown_list:
            limit = item.get("usageLimitWithPrecision", item.get("usageLimit", 0)) or 0
            current = item.get("currentUsageWithPrecision", item.get("currentUsage", 0)) or 0
            resource_type = item.get("resourceType", "UNKNOWN")
            display_name = item.get("displayName", resource_type)
            
            total_limit += limit
            total_usage += current
            
            details.append({
                "type": resource_type,
                "name": display_name,
                "used": current,
                "limit": limit,
                "remaining": max(0, limit - current),
            })
        
        percentage = (total_usage / total_limit * 100) if total_limit > 0 else 0
        
        # Next reset time
        next_reset = usage.get("nextDateReset")
        reset_str = ""
        if next_reset:
            try:
                reset_dt = datetime.fromtimestamp(next_reset / 1000)
                reset_str = reset_dt.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, OSError):
                reset_str = str(next_reset)
        
        return {
            "email": user_info.get("email", ""),
            "subscription": subscription_info.get("subscriptionTitle", ""),
            "total_used": round(total_usage, 2),
            "total_limit": round(total_limit, 2),
            "remaining": round(max(0, total_limit - total_usage), 2),
            "percentage": round(percentage, 2),
            "next_reset": reset_str,
            "details": details,
        }
    
    @staticmethod
    def print_summary(name: str, summary: dict[str, Any]) -> None:
        """Print formatted usage summary to console.
        
        Args:
            name: Display name for the account.
            summary: Formatted summary dictionary.
        """
        if "error" in summary:
            print(f"  ❌ Error: {summary['error']}")
            return
        
        email = summary.get("email", "N/A")
        subscription = summary.get("subscription", "Free")
        used = summary.get("total_used", 0)
        limit = summary.get("total_limit", 0)
        remaining = summary.get("remaining", 0)
        percentage = summary.get("percentage", 0)
        reset_time = summary.get("next_reset", "N/A")
        
        # Progress bar
        bar_width = 30
        filled = int(bar_width * percentage / 100)
        bar = "█" * filled + "░" * (bar_width - filled)
        
        print(f"  📧 Email: {email}")
        print(f"  📦 Plan: {subscription}")
        print(f"  📊 Usage: {used:.2f} / {limit:.2f} ({percentage:.1f}%)")
        print(f"  [{bar}]")
        print(f"  💰 Remaining: {remaining:.2f}")
        print(f"  🔄 Reset: {reset_time}")
