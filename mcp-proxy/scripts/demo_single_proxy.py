#!/usr/bin/env python3
"""
================================================================================
SINGLE PROXY AUTO-DEPLOY DEMO
================================================================================

This script demonstrates the complete single proxy workflow for Lukas.

It shows how with a SINGLE PROXY approach:
1. ONE JSON file (mcp-servers.json) defines ALL servers and permissions
2. ONE database table (group_tenant_mapping) controls ALL access
3. ONE deploy script configures EVERYTHING automatically

No manual UI clicks. No sync issues. No permission mismatches.

Usage:
    python demo_single_proxy.py              # Run full demo (no DB)
    python demo_single_proxy.py --with-db    # Run with actual database

================================================================================
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Configuration
SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR.parent / "config" / "mcp-servers.json"

# Check if terminal supports colors
USE_COLORS = sys.stdout.isatty() and os.environ.get("TERM") != "dumb"

# Colors for terminal output
class Colors:
    HEADER = '\033[95m' if USE_COLORS else ''
    BLUE = '\033[94m' if USE_COLORS else ''
    CYAN = '\033[96m' if USE_COLORS else ''
    GREEN = '\033[92m' if USE_COLORS else ''
    YELLOW = '\033[93m' if USE_COLORS else ''
    RED = '\033[91m' if USE_COLORS else ''
    BOLD = '\033[1m' if USE_COLORS else ''
    UNDERLINE = '\033[4m' if USE_COLORS else ''
    END = '\033[0m' if USE_COLORS else ''

def c(text: str, color: str) -> str:
    """Colorize text for terminal."""
    if USE_COLORS:
        return f"{color}{text}{Colors.END}"
    return text


def print_header(text: str):
    """Print a section header."""
    print("\n" + "=" * 70)
    print(c(f"  {text}", Colors.BOLD + Colors.CYAN))
    print("=" * 70)


def print_subheader(text: str):
    """Print a subsection header."""
    print("\n" + "-" * 70)
    print(c(f"  {text}", Colors.BOLD))
    print("-" * 70)


def print_success(text: str):
    """Print success message."""
    print(c(f"  [OK] {text}", Colors.GREEN))


def print_info(text: str):
    """Print info message."""
    print(c(f"  [i] {text}", Colors.BLUE))


def print_table_row(col1: str, col2: str, col3: str = ""):
    """Print a table row."""
    if col3:
        print(f"  | {col1:20} | {col2:25} | {col3:15} |")
    else:
        print(f"  | {col1:25} | {col2:40} |")


def load_config() -> Dict[str, Any]:
    """Load MCP servers configuration."""
    if not CONFIG_PATH.exists():
        print(c(f"  ❌ Config not found: {CONFIG_PATH}", Colors.RED))
        print(c("     Creating demo config...", Colors.YELLOW))

        demo_config = {
            "version": "1.0",
            "description": "Demo configuration",
            "servers": [
                {"id": "github", "name": "GitHub", "url": "http://mcp-proxy:8000/github",
                 "groups": ["MCP-Admin", "MCP-GitHub", "Tenant-Google", "Tenant-Microsoft"]},
                {"id": "linear", "name": "Linear", "url": "http://mcp-proxy:8000/linear",
                 "groups": ["MCP-Admin", "Tenant-Google"]},
                {"id": "notion", "name": "Notion", "url": "http://mcp-proxy:8000/notion",
                 "groups": ["MCP-Admin", "Tenant-Google", "Tenant-AcmeCorp"]},
                {"id": "filesystem", "name": "Filesystem", "url": "http://mcp-proxy:8000/filesystem",
                 "groups": ["MCP-Admin", "MCP-Filesystem", "Tenant-Google", "Tenant-Microsoft", "Tenant-AcmeCorp"]},
                {"id": "atlassian", "name": "Atlassian", "url": "http://mcp-proxy:8000/atlassian",
                 "groups": ["MCP-Admin", "Tenant-Google", "Tenant-Microsoft"]},
            ]
        }

        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            json.dump(demo_config, f, indent=2)

    with open(CONFIG_PATH) as f:
        return json.load(f)


def demo_step1_load_config(config: Dict) -> List[Dict]:
    """Step 1: Load and display config."""
    print_header("STEP 1: Load Single Source of Truth")

    servers = config.get("servers", [])

    print_info(f"Config file: {CONFIG_PATH}")
    print_info(f"Servers defined: {len(servers)}")

    print("\n  Servers in config:")
    print("  " + "-" * 50)
    for s in servers:
        groups_count = len(s.get("groups", []))
        print(f"  | {s['id']:15} | {s['name']:20} | {groups_count} groups |")
    print("  " + "-" * 50)

    print_success("Config loaded from ONE file")

    return servers


def demo_step2_extract_mappings(servers: List[Dict]) -> List[Dict]:
    """Step 2: Extract group->tenant mappings."""
    print_header("STEP 2: Extract Group→Tenant Mappings")

    mappings = []

    for server in servers:
        server_id = server["id"]
        for group in server.get("groups", []):
            mappings.append({
                "group_name": group,
                "tenant_id": server_id
            })

    # Display unique groups
    unique_groups = sorted(set(m["group_name"] for m in mappings))
    unique_servers = sorted(set(m["tenant_id"] for m in mappings))

    print_info(f"Total mappings: {len(mappings)}")
    print_info(f"Unique groups: {len(unique_groups)}")
    print_info(f"Unique servers: {len(unique_servers)}")

    print("\n  SQL that would be executed:")
    print("  " + "-" * 60)
    print(c("  INSERT INTO group_tenant_mapping (group_name, tenant_id)", Colors.CYAN))
    print(c("  VALUES", Colors.CYAN))
    for i, m in enumerate(mappings[:5]):
        comma = "," if i < min(4, len(mappings) - 1) else ";"
        print(f"    ('{m['group_name']}', '{m['tenant_id']}'){comma}")
    if len(mappings) > 5:
        print(f"    -- ... and {len(mappings) - 5} more rows")
    print("  " + "-" * 60)

    print_success(f"Extracted {len(mappings)} mappings for ONE database table")

    return mappings


def demo_step3_generate_webui_export(servers: List[Dict]) -> Dict:
    """Step 3: Generate Open WebUI import JSON."""
    print_header("STEP 3: Generate Open WebUI Tool Import")

    tools = []
    for s in servers:
        tools.append({
            "id": s["id"],
            "name": s["name"],
            "type": "openapi",
            "url": s["url"],
            "auth_type": "none"  # Proxy handles auth
        })

    export = {
        "version": "1.0",
        "exported_at": datetime.now().isoformat(),
        "source": "mcp-servers.json (single proxy)",
        "tools": tools
    }

    print_info("Generated Open WebUI import format:")
    print("\n" + json.dumps(export["tools"][0], indent=2))
    if len(tools) > 1:
        print(f"\n  ... and {len(tools) - 1} more tools")

    print_success(f"Generated import JSON for {len(tools)} tools")
    print_info("This can be imported via: Admin Settings → External Tools → Import")

    return export


def demo_step4_show_arguments():
    """Step 4: Show arguments for single proxy."""
    print_header("STEP 4: Arguments for Single Proxy Approach")

    arguments = [
        ("Single Source of Truth",
         "mcp-servers.json defines ALL servers and permissions",
         "Version controlled, reviewable, auditable"),

        ("One Database Table",
         "group_tenant_mapping controls ALL access",
         "Simple queries, easy debugging"),

        ("Easy Automation",
         "One script seeds everything at deploy time",
         "kubectl apply → Done"),

        ("No Sync Issues",
         "No mismatch between Open WebUI and proxy",
         "One system = consistent behavior"),

        ("Simple Debugging",
         "Permission denied? Check one table",
         "SELECT * FROM group_tenant_mapping WHERE group_name = ?"),

        ("Audit Trail",
         "All requests go through proxy",
         "One log location, complete visibility"),

        ("Tenant Isolation",
         "Proxy enforces boundaries at network level",
         "Tenants can't bypass permissions"),
    ]

    for title, desc, detail in arguments:
        print(f"\n  {c('[OK]', Colors.GREEN)} {c(title, Colors.BOLD)}")
        print(f"       {desc}")
        print(f"       {c(detail, Colors.CYAN)}")


def demo_step5_show_comparison():
    """Step 5: Show comparison with mixed approach."""
    print_header("STEP 5: Single Proxy vs Mixed Approach")

    print("""
    +----------------------+------------------------+-------------------------+
    | Aspect               | Single Proxy [OK]      | Mixed Approach [X]      |
    +----------------------+------------------------+-------------------------+
    | Permission Systems   | 1 (database table)     | 2 (proxy + WebUI)       |
    +----------------------+------------------------+-------------------------+
    | Config Files         | 1 (mcp-servers.json)   | Multiple locations      |
    +----------------------+------------------------+-------------------------+
    | Deploy Automation    | 1 script               | Complex sync logic      |
    +----------------------+------------------------+-------------------------+
    | Add New Server       | Add to JSON + 1 row    | JSON + UI + checkboxes  |
    +----------------------+------------------------+-------------------------+
    | Debug Permissions    | Query 1 table          | Check 2 systems         |
    +----------------------+------------------------+-------------------------+
    | Audit Log            | 1 location (proxy)     | Scattered across systems|
    +----------------------+------------------------+-------------------------+
    | Secret Management    | 1 secrets file         | Multiple places         |
    +----------------------+------------------------+-------------------------+
    | Risk of Desync       | None                   | High                    |
    +----------------------+------------------------+-------------------------+
    """)


def demo_step6_deployment_flow():
    """Step 6: Show the deployment flow."""
    print_header("STEP 6: Deploy-Time Flow (IMPROVED)")

    print("""
    +---------------------------------------------------------------------+
    |              SINGLE PROXY DEPLOY FLOW (PRE-DEPLOY CONFIG)            |
    +---------------------------------------------------------------------+
    |                                                                      |
    |  1. Developer commits mcp-servers.json                               |
    |     +-- Defines all servers + group permissions                      |
    |                          |                                           |
    |                          v                                           |
    |  2. kubectl apply / helm install                                     |
    |     +-- TOOL_SERVER_CONNECTIONS env var -> Open WebUI config         |
    |     +-- (Configured BEFORE Open WebUI starts!)                       |
    |                          |                                           |
    |                          v                                           |
    |  3. Init Job: seed_mcp_servers.py                                    |
    |     +-- Seeds group_tenant_mapping table (PERMISSIONS)               |
    |                          |                                           |
    |                          v                                           |
    |  4. Open WebUI + MCP Proxy start                                     |
    |     +-- Open WebUI already has tool configured (from env var)        |
    |     +-- MCP Proxy reads permissions from database                    |
    |                          |                                           |
    |                          v                                           |
    |  5. DONE! All MCP servers configured                                 |
    |     +-- Database seeded + Open WebUI configured                      |
    |     +-- No manual UI clicks needed!                                  |
    |     +-- No API calls needed!                                         |
    |                                                                      |
    +---------------------------------------------------------------------+

    KEY DISCOVERY: TOOL_SERVER_CONNECTIONS environment variable
    +---------------------------------------------------------------------+
    |  This env var configures Open WebUI tools AT STARTUP, not after!    |
    |                                                                      |
    |  env:                                                                |
    |    - name: TOOL_SERVER_CONNECTIONS                                   |
    |      value: '[{"type":"openapi","url":"http://mcp-proxy:8000",...}]' |
    |                                                                      |
    |  Result: Open WebUI starts with MCP Proxy already configured        |
    +---------------------------------------------------------------------+
    """)


def main():
    """Run the complete demo."""
    print("\n")
    print(c("+======================================================================+", Colors.CYAN))
    print(c("|                                                                      |", Colors.CYAN))
    print(c("|   SINGLE PROXY AUTO-DEPLOY DEMO                                      |", Colors.CYAN))
    print(c("|                                                                      |", Colors.CYAN))
    print(c("|   For Lukas: Demonstrating why single proxy = simpler automation     |", Colors.CYAN))
    print(c("|                                                                      |", Colors.CYAN))
    print(c("+======================================================================+", Colors.CYAN))

    # Load config
    config = load_config()

    # Step 1: Load config
    servers = demo_step1_load_config(config)

    # Step 2: Extract mappings
    mappings = demo_step2_extract_mappings(servers)

    # Step 3: Generate WebUI export
    export = demo_step3_generate_webui_export(servers)

    # Step 4: Show arguments
    demo_step4_show_arguments()

    # Step 5: Show comparison
    demo_step5_show_comparison()

    # Step 6: Show deployment flow
    demo_step6_deployment_flow()

    # Summary
    print_header("SUMMARY")

    print(f"""
    {c('This demo proves:', Colors.BOLD)}

    With SINGLE PROXY approach:
    * Define servers ONCE in mcp-servers.json
    * Configure Open WebUI via TOOL_SERVER_CONNECTIONS env var (PRE-DEPLOY!)
    * Seed database at deploy time (permissions)
    * All controlled from ONE config file

    Result: {c('kubectl apply -> Everything configured automatically', Colors.GREEN)}

    {c('KEY DISCOVERY:', Colors.BOLD + Colors.CYAN)}

    TOOL_SERVER_CONNECTIONS environment variable lets us configure
    Open WebUI tools BEFORE it starts - not after via API!

    {c('For Lukas to argue:', Colors.BOLD)}

    "With single proxy, I define servers once in mcp-servers.json.
    The Helm chart has TOOL_SERVER_CONNECTIONS env var that configures
    Open WebUI at startup. An init job seeds the database permissions.

    No manual UI clicks. No API calls. No sync issues. ONE source of truth."
    """)

    print("=" * 70)
    print(c("  DEMO COMPLETE", Colors.BOLD + Colors.GREEN))
    print("=" * 70 + "\n")


if __name__ == "__main__":
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        sys.exit(0)

    main()
