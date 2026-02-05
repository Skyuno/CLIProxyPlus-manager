#!/usr/bin/env python3
"""
Kiro Usage Monitor

Monitors Kiro usage every minute, calculates consumption rate,
and estimates time until credits are depleted.

Usage:
    python scripts/usage_monitor.py [--interval SECONDS]

Configuration:
    Edit .env file or use environment variables:
    - CLIPROXY_URL: Base URL of CLIProxyAPIPlus server
    - CLIPROXY_KEY: Management API key
"""

import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from CLIProxyPlus_manager.panel import PanelClient, PanelConfig
from CLIProxyPlus_manager.kiro import KiroAPI, UsageFormatter


class UsageSnapshot:
    """Represents a snapshot of usage at a specific time."""
    
    def __init__(self, timestamp: datetime, total_remaining: float, account_details: list[dict]):
        self.timestamp = timestamp
        self.total_remaining = total_remaining
        self.account_details = account_details


class KiroUsageMonitor:
    """Monitors Kiro usage and calculates consumption statistics."""
    
    def __init__(self, panel: PanelClient, kiro_api: KiroAPI, formatter: UsageFormatter):
        self.panel = panel
        self.kiro_api = kiro_api
        self.formatter = formatter
        self.history: list[UsageSnapshot] = []
    
    def query_all_accounts(self) -> tuple[float, list[dict]]:
        """Query usage for all Kiro accounts.
        
        Returns:
            Tuple of (total_remaining, account_details_list)
        """
        kiro_files = self.panel.list_kiro_files()
        
        if not kiro_files:
            return 0.0, []
        
        total_remaining = 0.0
        account_details = []
        
        for file_info in kiro_files:
            filename = file_info.get("name", "")
            email = file_info.get("email", filename)
            status = file_info.get("status", "")
            
            if status == "disabled":
                continue
            
            auth_data = self.panel.download_auth_file(filename)
            if not auth_data:
                continue
            
            access_token = auth_data.get("access_token", "")
            if not access_token:
                continue
            
            region = auth_data.get("region", "us-east-1")
            usage = self.kiro_api.query_usage(access_token, region=region)
            summary = self.formatter.format_summary(usage)
            
            if "error" not in summary:
                remaining = summary.get("remaining", 0)
                total_remaining += remaining
                account_details.append({
                    "email": email,
                    "remaining": remaining,
                    "used": summary.get("total_used", 0),
                    "limit": summary.get("total_limit", 0),
                    "percentage": summary.get("percentage", 0),
                    "next_reset": summary.get("next_reset", ""),
                })
        
        return total_remaining, account_details
    
    def take_snapshot(self) -> UsageSnapshot:
        """Take a snapshot of current usage."""
        total_remaining, account_details = self.query_all_accounts()
        snapshot = UsageSnapshot(
            timestamp=datetime.now(),
            total_remaining=total_remaining,
            account_details=account_details,
        )
        self.history.append(snapshot)
        return snapshot
    
    def calculate_rate(self) -> dict[str, Any]:
        """Calculate consumption rate based on history.
        
        Returns:
            Dictionary with rate statistics.
        """
        if len(self.history) < 2:
            return {
                "rate_per_minute": 0,
                "rate_per_hour": 0,
                "time_until_empty": None,
                "samples": len(self.history),
            }
        
        # Use all available history points
        first = self.history[0]
        last = self.history[-1]
        
        duration_seconds = (last.timestamp - first.timestamp).total_seconds()
        if duration_seconds <= 0:
            return {
                "rate_per_minute": 0,
                "rate_per_hour": 0,
                "time_until_empty": None,
                "samples": len(self.history),
            }
        
        # Calculate consumption (positive means credits are being used)
        consumption = first.total_remaining - last.total_remaining
        rate_per_second = consumption / duration_seconds
        rate_per_minute = rate_per_second * 60
        rate_per_hour = rate_per_second * 3600
        
        # Estimate time until empty
        time_until_empty = None
        if rate_per_second > 0 and last.total_remaining > 0:
            seconds_until_empty = last.total_remaining / rate_per_second
            time_until_empty = timedelta(seconds=int(seconds_until_empty))
        
        return {
            "rate_per_minute": round(rate_per_minute, 4),
            "rate_per_hour": round(rate_per_hour, 2),
            "time_until_empty": time_until_empty,
            "samples": len(self.history),
            "monitoring_duration": str(timedelta(seconds=int(duration_seconds))),
        }


def clear_line():
    """Clear the current console line."""
    print("\r" + " " * 80 + "\r", end="", flush=True)


def format_timedelta(td: timedelta | None) -> str:
    """Format timedelta for display."""
    if td is None:
        return "∞ (无消耗或数据不足)"
    
    total_seconds = int(td.total_seconds())
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    
    parts = []
    if days > 0:
        parts.append(f"{days}天")
    if hours > 0:
        parts.append(f"{hours}小时")
    if minutes > 0 or not parts:
        parts.append(f"{minutes}分钟")
    
    return " ".join(parts)


def print_status(snapshot: UsageSnapshot, rate_info: dict[str, Any]) -> None:
    """Print current status to console."""
    now = snapshot.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"\n[{now}] 💰 总剩余: {snapshot.total_remaining:.2f}", end="")
    
    # Rate info on same line if available
    if rate_info.get('samples', 0) >= 2:
        rate_h = rate_info.get('rate_per_hour', 0)
        time_until_empty = rate_info.get('time_until_empty')
        eta_str = format_timedelta(time_until_empty)
        print(f" | 📈 {rate_h:.2f}/h | ⏱️ {eta_str}")
    else:
        print(f" | 采样中 ({rate_info.get('samples', 0)}/2)...")
    
    # Compact per-account details
    for acc in snapshot.account_details:
        email = acc.get("email", "Unknown")[:30]
        remaining = acc.get("remaining", 0)
        percentage = acc.get("percentage", 0)
        bar_width = 15
        filled = int(bar_width * percentage / 100)
        bar = "█" * filled + "░" * (bar_width - filled)
        print(f"  [{bar}] {percentage:5.1f}% | {remaining:7.2f} | {email}")


def save_history(monitor: KiroUsageMonitor, output_dir: Path) -> None:
    """Save monitoring history to JSON file."""
    history_data = []
    for snap in monitor.history:
        history_data.append({
            "timestamp": snap.timestamp.isoformat(),
            "total_remaining": snap.total_remaining,
            "account_details": snap.account_details,
        })
    
    output_file = output_dir / "kiro_usage_history.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(history_data, f, ensure_ascii=False, indent=2)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Kiro Usage Monitor")
    parser.add_argument(
        "--interval", "-i",
        type=int,
        default=60,
        help="Monitoring interval in seconds (default: 60)"
    )
    args = parser.parse_args()
    
    interval = args.interval
    
    print("=" * 70)
    print("🔍 Kiro 用量监控工具")
    print("=" * 70)
    print(f"⏰ 监控间隔: {interval} 秒")
    print("📌 按 Ctrl+C 停止监控")
    print()
    
    # Initialize clients
    config = PanelConfig.from_env(Path(__file__).parent.parent / ".env")
    panel = PanelClient(config)
    kiro_api = KiroAPI(timeout=config.timeout)
    formatter = UsageFormatter()
    
    monitor = KiroUsageMonitor(panel, kiro_api, formatter)
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)
    
    print(f"🌐 服务器: {config.base_url}")
    print("📋 正在获取初始数据...")
    
    try:
        while True:
            # Take snapshot
            snapshot = monitor.take_snapshot()
            
            if not snapshot.account_details:
                print("❌ 未能获取任何 Kiro 账户数据")
                print(f"   {interval} 秒后重试...")
                time.sleep(interval)
                continue
            
            # Calculate rate
            rate_info = monitor.calculate_rate()
            
            # Print status
            print_status(snapshot, rate_info)
            
            # Save history
            save_history(monitor, output_dir)
            
            # Wait for next interval with countdown
            print(f"\n⏳ 下次刷新: ", end="", flush=True)
            for remaining in range(interval, 0, -1):
                print(f"\r⏳ 下次刷新: {remaining} 秒  ", end="", flush=True)
                time.sleep(1)
            clear_line()
            
    except KeyboardInterrupt:
        print("\n\n👋 监控已停止")
        
        # Save final history
        save_history(monitor, output_dir)
        print(f"💾 历史记录已保存到: {output_dir / 'kiro_usage_history.json'}")
        
        # Print final statistics
        if len(monitor.history) >= 2:
            rate_info = monitor.calculate_rate()
            print(f"\n📊 最终统计:")
            print(f"   总采样点: {rate_info.get('samples', 0)}")
            print(f"   监控时长: {rate_info.get('monitoring_duration', 'N/A')}")
            print(f"   平均每小时消耗: {rate_info.get('rate_per_hour', 0):.2f}")


if __name__ == "__main__":
    main()
