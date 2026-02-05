#!/usr/bin/env python3
"""
Kiro Balance Query Tool

A Python script to query usage/balance information for Kiro authentication files
from CLIProxyAPIPlus management API.

Usage:
    python scripts/usage_query.py

Configuration:
    Edit .env file or use environment variables:
    - CLIPROXY_URL: Base URL of CLIProxyAPIPlus server
    - CLIPROXY_KEY: Management API key
"""

import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from CLIProxyPlus_manager.panel import PanelClient, PanelConfig
from CLIProxyPlus_manager.kiro import KiroAPI, UsageFormatter


def main() -> None:
    """Main entry point."""
    print("=" * 60)
    print("🔍 Kiro Balance Query Tool")
    print("=" * 60)
    
    # Initialize clients
    config = PanelConfig.from_env(Path(__file__).parent.parent / ".env")
    panel = PanelClient(config)
    kiro_api = KiroAPI(timeout=config.timeout)
    formatter = UsageFormatter()
    
    print(f"Server: {config.base_url}")
    print()
    
    # Step 1: List all Kiro auth files
    print("📋 Fetching auth files...")
    kiro_files = panel.list_kiro_files()
    
    if not kiro_files:
        all_files = panel.list_auth_files()
        if not all_files:
            print("❌ No auth files found or failed to connect.")
        else:
            print("⚠️  No Kiro auth files found.")
            print(f"   Found {len(all_files)} auth file(s) of other types.")
        sys.exit(1 if not all_files else 0)
    
    print(f"✅ Found {len(kiro_files)} Kiro auth file(s)")
    print()
    
    # Step 2: Query usage for each Kiro file
    results = []
    
    for idx, file_info in enumerate(kiro_files, 1):
        filename = file_info.get("name", "")
        email = file_info.get("email", filename)
        status = file_info.get("status", "")
        
        print(f"[{idx}/{len(kiro_files)}] 📄 {email}")
        
        if status == "disabled":
            print("  ⏸️  Skipped (disabled)")
            print()
            continue
        
        # Download full auth file to get access_token
        auth_data = panel.download_auth_file(filename)
        if not auth_data:
            print()
            continue
        
        access_token = auth_data.get("access_token", "")
        if not access_token:
            print("  ❌ No access_token in auth file")
            print()
            continue
        
        # Get region from auth file (default to us-east-1)
        region = auth_data.get("region", "us-east-1")
        
        # Query Kiro API
        usage = kiro_api.query_usage(access_token, region=region)
        summary = formatter.format_summary(usage)
        
        formatter.print_summary(email, summary)
        print()
        
        results.append({
            "filename": filename,
            "email": email,
            "summary": summary,
            "raw_response": usage,
        })
    
    # Step 3: Print final summary
    print("=" * 60)
    print("📊 Summary")
    print("=" * 60)
    
    total_remaining = 0
    for r in results:
        s = r.get("summary", {})
        if "error" not in s:
            remaining = s.get("remaining", 0)
            total_remaining += remaining
            email = r.get("email", "")
            print(f"  {email}: {remaining:.2f} remaining")
    
    print()
    print(f"🎯 Total Remaining Credits: {total_remaining:.2f}")
    print()
    
    # Optional: Save full results to JSON
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "kiro_balance_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"💾 Full results saved to: {output_file}")
    input()


if __name__ == "__main__":
    main()
