#!/usr/bin/env python3
"""
Kiro Balance Query Tool

A Python script to query usage/balance information for Kiro authentication files
from CLIProxyAPIPlus management API. Supports querying multiple panels concurrently.

Usage:
    python scripts/usage_query.py
    python scripts/usage_query.py --panel P1
    python scripts/usage_query.py --panel P1 --panel P2

Configuration:
    Edit config.yaml to configure panels.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

import aiohttp

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from CLIProxyPlus_manager.panel import AppConfig, AsyncPanelClient, PanelConfig
from CLIProxyPlus_manager.kiro import AsyncKiroAPI, UsageFormatter


async def query_single_account(
    panel_client: AsyncPanelClient,
    kiro_api: AsyncKiroAPI,
    formatter: UsageFormatter,
    session: aiohttp.ClientSession,
    file_info: dict,
    panel_name: str,
) -> dict | None:
    """Query usage for a single Kiro account.

    Returns:
        Result dict, or None if failed/disabled.
    """
    filename = file_info.get("name", "")
    email = file_info.get("email", filename)
    status = file_info.get("status", "")

    if status == "disabled":
        return {"skipped": True, "email": email, "reason": "disabled"}

    auth_data = await panel_client.download_auth_file(session, filename)
    if not auth_data:
        return None

    access_token = auth_data.get("access_token", "")
    if not access_token:
        return None

    region = auth_data.get("region", "us-east-1")
    usage = await kiro_api.query_usage(session, access_token, region=region)
    summary = formatter.format_summary(usage)

    return {
        "panel": panel_name,
        "filename": filename,
        "email": email,
        "summary": summary,
        "raw_response": usage,
    }


async def query_panel(
    panel_config: PanelConfig,
    kiro_api: AsyncKiroAPI,
    formatter: UsageFormatter,
    session: aiohttp.ClientSession,
) -> list[dict]:
    """Query all Kiro accounts for a single panel concurrently.

    Returns:
        List of result dicts.
    """
    panel_client = AsyncPanelClient(panel_config)
    kiro_files = await panel_client.list_kiro_files(session)

    if not kiro_files:
        all_files = await panel_client.list_auth_files(session)
        if not all_files:
            print(f"  ❌ No auth files found or failed to connect.")
        else:
            print(f"  ⚠️  No Kiro auth files found.")
            print(f"     Found {len(all_files)} auth file(s) of other types.")
        return []

    print(f"  ✅ Found {len(kiro_files)} Kiro auth file(s)")

    # Query all accounts concurrently
    tasks = [
        query_single_account(
            panel_client, kiro_api, formatter, session, fi, panel_config.name
        )
        for fi in kiro_files
    ]
    raw_results = await asyncio.gather(*tasks)

    results = []
    for r in raw_results:
        if r is None:
            continue
        if r.get("skipped"):
            print(f"  ⏸️  {r['email']} (disabled)")
            continue
        results.append(r)

    return results


async def run_query(selected_panels: list[PanelConfig], app_config: AppConfig) -> None:
    """Main async query logic."""
    kiro_api = AsyncKiroAPI(timeout=app_config.timeout)
    formatter = UsageFormatter()

    print(f"📡 Panels: {', '.join(str(p) for p in selected_panels)}")
    print()

    # Query all panels concurrently
    async with aiohttp.ClientSession() as session:
        all_panel_results = await asyncio.gather(*[
            query_panel(pc, kiro_api, formatter, session)
            for pc in selected_panels
        ])

    # Display results per panel
    all_results = []
    for panel_config, panel_results in zip(selected_panels, all_panel_results):
        if len(selected_panels) > 1:
            print("-" * 60)
        print(f"🌐 [{panel_config.name}] {panel_config.base_url}")
        print()

        for idx, r in enumerate(panel_results, 1):
            email = r.get("email", "")
            summary = r.get("summary", {})
            print(f"  [{idx}/{len(panel_results)}] 📄 {email}")
            formatter.print_summary(email, summary)
            print()

        all_results.extend(panel_results)

    # Print final summary
    print("=" * 60)
    print("📊 Summary")
    print("=" * 60)

    total_remaining = 0
    current_panel = None
    for r in all_results:
        s = r.get("summary", {})
        if "error" not in s:
            panel_name = r.get("panel", "")
            if len(selected_panels) > 1 and panel_name != current_panel:
                current_panel = panel_name
                print(f"  [{panel_name}]")
            remaining = s.get("remaining", 0)
            total_remaining += remaining
            email = r.get("email", "")
            print(f"    {email}: {remaining:.2f} remaining")

    print()
    print(f"🎯 Total Remaining Credits: {total_remaining:.2f}")
    print()

    # Save full results to JSON
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "kiro_balance_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"💾 Full results saved to: {output_file}")
    input()


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Kiro Balance Query Tool")
    parser.add_argument(
        "--panel", "-p",
        action="append",
        dest="panels",
        help="Panel name(s) to query. If not specified, queries all panels.",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("🔍 Kiro Balance Query Tool (Async)")
    print("=" * 60)

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

    asyncio.run(run_query(selected_panels, app_config))


if __name__ == "__main__":
    main()
