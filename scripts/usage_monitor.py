#!/usr/bin/env python3
"""
Kiro Usage Monitor

Monitors Kiro usage every minute, calculates consumption rate,
and estimates time until credits are depleted. Supports multiple panels.
Uses async I/O for concurrent querying across panels and accounts.

Usage:
    python scripts/usage_monitor.py [--interval SECONDS]
    python scripts/usage_monitor.py --panel P1
    python scripts/usage_monitor.py --panel P1 --panel P2 -i 30

Configuration:
    Edit config.yaml to configure panels.
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import aiohttp

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from CLIProxyPlus_manager.panel import AppConfig, AsyncPanelClient, PanelConfig
from CLIProxyPlus_manager.kiro import AsyncKiroAPI, UsageFormatter


class UsageSnapshot:
    """Represents a snapshot of usage at a specific time."""

    def __init__(self, timestamp: datetime, total_remaining: float,
                 panel_details: list[dict]):
        self.timestamp = timestamp
        self.total_remaining = total_remaining
        self.panel_details = panel_details


async def query_single_account(
    panel_client: AsyncPanelClient,
    kiro_api: AsyncKiroAPI,
    formatter: UsageFormatter,
    session: aiohttp.ClientSession,
    file_info: dict,
) -> dict | None:
    """Query usage for a single Kiro account.

    Returns:
        Account detail dict, or None if failed/disabled.
    """
    filename = file_info.get("name", "")
    email = file_info.get("email", filename)
    status = file_info.get("status", "")

    if status == "disabled":
        return None

    auth_data = await panel_client.download_auth_file(session, filename)
    if not auth_data:
        return None

    access_token = auth_data.get("access_token", "")
    if not access_token:
        return None

    region = auth_data.get("region", "us-east-1")
    usage = await kiro_api.query_usage(session, access_token, region=region)
    summary = formatter.format_summary(usage)

    if "error" in summary:
        return None

    return {
        "email": email,
        "remaining": summary.get("remaining", 0),
        "used": summary.get("total_used", 0),
        "limit": summary.get("total_limit", 0),
        "percentage": summary.get("percentage", 0),
        "next_reset": summary.get("next_reset", ""),
    }


async def query_panel(
    panel_config: PanelConfig,
    kiro_api: AsyncKiroAPI,
    formatter: UsageFormatter,
    session: aiohttp.ClientSession,
) -> dict:
    """Query all Kiro accounts for a single panel concurrently.

    Returns:
        Panel detail dict with accounts list.
    """
    panel_client = AsyncPanelClient(panel_config)
    kiro_files = await panel_client.list_kiro_files(session)

    if not kiro_files:
        return {
            "panel_name": panel_config.name,
            "panel_url": panel_config.base_url,
            "remaining": 0.0,
            "accounts": [],
        }

    # Query all accounts concurrently
    tasks = [
        query_single_account(panel_client, kiro_api, formatter, session, fi)
        for fi in kiro_files
    ]
    results = await asyncio.gather(*tasks)

    accounts = [r for r in results if r is not None]
    total_remaining = sum(a["remaining"] for a in accounts)

    return {
        "panel_name": panel_config.name,
        "panel_url": panel_config.base_url,
        "remaining": total_remaining,
        "accounts": accounts,
    }


def _calc_rate_from_remaining(
    first_remaining: float,
    last_remaining: float,
    duration_seconds: float,
) -> dict[str, Any]:
    """Calculate consumption rate between two remaining values.

    Returns:
        Dict with rate_per_hour and time_until_empty.
    """
    if duration_seconds <= 0:
        return {"rate_per_hour": 0.0, "time_until_empty": None}

    consumption = first_remaining - last_remaining
    rate_per_second = consumption / duration_seconds
    rate_per_hour = rate_per_second * 3600

    time_until_empty = None
    if rate_per_second > 0 and last_remaining > 0:
        seconds_until_empty = last_remaining / rate_per_second
        time_until_empty = timedelta(seconds=int(seconds_until_empty))

    return {
        "rate_per_hour": round(rate_per_hour, 2),
        "time_until_empty": time_until_empty,
    }


class KiroUsageMonitor:
    """Monitors Kiro usage across multiple panels and calculates consumption statistics."""

    def __init__(self, panel_configs: list[PanelConfig], kiro_api: AsyncKiroAPI,
                 formatter: UsageFormatter):
        self.panel_configs = panel_configs
        self.kiro_api = kiro_api
        self.formatter = formatter
        self.history: list[UsageSnapshot] = []

    async def take_snapshot(self, session: aiohttp.ClientSession) -> UsageSnapshot:
        """Take a snapshot of current usage across all panels concurrently."""
        tasks = [
            query_panel(pc, self.kiro_api, self.formatter, session)
            for pc in self.panel_configs
        ]
        panel_details = list(await asyncio.gather(*tasks))

        total_remaining = sum(pd["remaining"] for pd in panel_details)

        snapshot = UsageSnapshot(
            timestamp=datetime.now(),
            total_remaining=total_remaining,
            panel_details=panel_details,
        )

        # Detect account count changes and reset history
        if self.history:
            prev_count = sum(
                len(pd["accounts"]) for pd in self.history[-1].panel_details
            )
            curr_count = sum(
                len(pd["accounts"]) for pd in panel_details
            )
            if prev_count != curr_count:
                print(f"⚠️ 账号数量变化 ({prev_count} -> {curr_count})，重置历史记录")
                self.history.clear()

        self.history.append(snapshot)
        return snapshot

    def calculate_rate(self) -> dict[str, Any]:
        """Calculate consumption rate based on history, both total and per-panel.

        Returns:
            Dictionary with total and per-panel rate statistics.
        """
        samples = len(self.history)

        if samples < 2:
            return {
                "rate_per_hour": 0,
                "time_until_empty": None,
                "samples": samples,
                "panels": {},
            }

        first = self.history[0]
        last = self.history[-1]

        duration_seconds = (last.timestamp - first.timestamp).total_seconds()
        if duration_seconds <= 0:
            return {
                "rate_per_hour": 0,
                "time_until_empty": None,
                "samples": samples,
                "panels": {},
            }

        # Total rate
        total_rate = _calc_rate_from_remaining(
            first.total_remaining, last.total_remaining, duration_seconds
        )

        # Per-panel rate: match by panel_name
        first_panels = {pd["panel_name"]: pd for pd in first.panel_details}
        last_panels = {pd["panel_name"]: pd for pd in last.panel_details}

        panel_rates = {}
        for panel_name in last_panels:
            fp = first_panels.get(panel_name)
            lp = last_panels[panel_name]
            if fp is not None:
                panel_rates[panel_name] = _calc_rate_from_remaining(
                    fp["remaining"], lp["remaining"], duration_seconds
                )
            else:
                panel_rates[panel_name] = {"rate_per_hour": 0.0, "time_until_empty": None}

        return {
            "rate_per_hour": total_rate["rate_per_hour"],
            "time_until_empty": total_rate["time_until_empty"],
            "samples": samples,
            "monitoring_duration": str(timedelta(seconds=int(duration_seconds))),
            "panels": panel_rates,
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


def format_rate_short(rate_per_hour: float, time_until_empty: timedelta | None) -> str:
    """Format rate info into a compact string."""
    eta_str = format_timedelta(time_until_empty)
    return f"📈 {rate_per_hour:.2f}/h | ⏱️ {eta_str}"


def print_status(snapshot: UsageSnapshot, rate_info: dict[str, Any],
                 multi_panel: bool) -> None:
    """Print current status to console."""
    now = snapshot.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    has_rate = rate_info.get("samples", 0) >= 2
    panel_rates = rate_info.get("panels", {})

    # Header line: total
    print(f"\n[{now}] 💰 总剩余: {snapshot.total_remaining:.2f}", end="")
    if has_rate:
        print(f" | {format_rate_short(rate_info['rate_per_hour'], rate_info['time_until_empty'])}")
    else:
        print(f" | 采样中 ({rate_info.get('samples', 0)}/2)...")

    # Per-panel details
    for pd in snapshot.panel_details:
        panel_name = pd["panel_name"]

        if multi_panel:
            panel_remaining = pd["remaining"]
            line = f"  📡 [{panel_name}] 剩余: {panel_remaining:.2f}"
            if has_rate and panel_name in panel_rates:
                pr = panel_rates[panel_name]
                line += f" | {format_rate_short(pr['rate_per_hour'], pr['time_until_empty'])}"
            print(line)

        for acc in pd["accounts"]:
            email = acc.get("email", "Unknown")[:30]
            used = acc.get("used", 0)
            limit = acc.get("limit", 0)
            percentage = acc.get("percentage", 0)
            bar_width = 15
            filled = int(bar_width * percentage / 100)
            bar = "█" * filled + "░" * (bar_width - filled)
            prefix = "    " if multi_panel else "  "
            print(f"{prefix}[{bar}] {percentage:5.1f}% | {used:7.2f}/{limit:.0f} | {email}")


def save_history(monitor: KiroUsageMonitor, output_dir: Path) -> None:
    """Save monitoring history to JSON file."""
    history_data = []
    for snap in monitor.history:
        history_data.append({
            "timestamp": snap.timestamp.isoformat(),
            "total_remaining": snap.total_remaining,
            "panel_details": snap.panel_details,
        })

    output_file = output_dir / "kiro_usage_history.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(history_data, f, ensure_ascii=False, indent=2)


async def run_monitor(selected_panels: list[PanelConfig], app_config: AppConfig,
                      interval: int) -> None:
    """Main async monitoring loop."""
    multi_panel = len(selected_panels) > 1

    kiro_api = AsyncKiroAPI(timeout=app_config.timeout)
    formatter = UsageFormatter()

    monitor = KiroUsageMonitor(selected_panels, kiro_api, formatter)

    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)

    print(f"📡 Panels: {', '.join(str(p) for p in selected_panels)}")
    print("📋 正在获取初始数据...")

    try:
        async with aiohttp.ClientSession() as session:
            while True:
                snapshot = await monitor.take_snapshot(session)

                has_data = any(pd["accounts"] for pd in snapshot.panel_details)
                if not has_data:
                    print("❌ 未能获取任何 Kiro 账户数据")
                    print(f"   {interval} 秒后重试...")
                    await asyncio.sleep(interval)
                    continue

                rate_info = monitor.calculate_rate()
                print_status(snapshot, rate_info, multi_panel)
                save_history(monitor, output_dir)

                print(f"\n⏳ 下次刷新: ", end="", flush=True)
                for remaining in range(interval, 0, -1):
                    print(f"\r⏳ 下次刷新: {remaining} 秒  ", end="", flush=True)
                    await asyncio.sleep(1)
                clear_line()

    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n\n👋 监控已停止")

        save_history(monitor, output_dir)
        print(f"💾 历史记录已保存到: {output_dir / 'kiro_usage_history.json'}")

        if len(monitor.history) >= 2:
            rate_info = monitor.calculate_rate()
            panel_rates = rate_info.get("panels", {})
            print(f"\n📊 最终统计:")
            print(f"   总采样点: {rate_info.get('samples', 0)}")
            print(f"   监控时长: {rate_info.get('monitoring_duration', 'N/A')}")
            print(f"   总计每小时消耗: {rate_info.get('rate_per_hour', 0):.2f}")
            if multi_panel:
                for name, pr in panel_rates.items():
                    print(f"   [{name}] 每小时消耗: {pr['rate_per_hour']:.2f}")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Kiro Usage Monitor")
    parser.add_argument(
        "--interval", "-i",
        type=int,
        default=60,
        help="Monitoring interval in seconds (default: 60)",
    )
    parser.add_argument(
        "--panel", "-p",
        action="append",
        dest="panels",
        help="Panel name(s) to monitor. If not specified, monitors all panels.",
    )
    args = parser.parse_args()

    interval = args.interval

    print("=" * 70)
    print("🔍 Kiro 用量监控工具 (Async)")
    print("=" * 70)
    print(f"⏰ 监控间隔: {interval} 秒")
    print("📌 按 Ctrl+C 停止监控")
    print()

    # Load configuration
    config_path = Path(__file__).parent.parent / "config.yaml"
    try:
        app_config = AppConfig.from_yaml(config_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"❌ {e}")
        sys.exit(1)

    # Filter panels if specified
    if args.panels:
        panel_names = {name.lower() for name in args.panels}
        selected_panels = [p for p in app_config.panels if p.name.lower() in panel_names]
        not_found = panel_names - {p.name.lower() for p in selected_panels}
        if not_found:
            print(f"⚠️  Panel(s) not found: {', '.join(not_found)}")
            print(f"   Available panels: {', '.join(p.name for p in app_config.panels)}")
        if not selected_panels:
            sys.exit(1)
    else:
        selected_panels = app_config.panels

    try:
        asyncio.run(run_monitor(selected_panels, app_config, interval))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
