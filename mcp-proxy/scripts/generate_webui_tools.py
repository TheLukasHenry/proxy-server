#!/usr/bin/env python3
"""
Open WebUI Tool Configuration Generator

Reads mcp-servers.json and generates the JSON format that
Open WebUI uses for external tool import.

This demonstrates the Single Proxy approach:
- ONE source of truth (mcp-servers.json)
- Can generate configs for ANY system from this file
- No need to manually configure Open WebUI UI

Usage:
    python generate_webui_tools.py              # Output to stdout
    python generate_webui_tools.py --save       # Save to webui-tools-export.json
    python generate_webui_tools.py --pretty     # Pretty print output

The generated JSON can be imported into Open WebUI via:
    Admin Settings -> External Tools -> Import
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Find config file relative to this script
SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR.parent / "config" / "mcp-servers.json"
OUTPUT_PATH = SCRIPT_DIR.parent / "config" / "webui-tools-export.json"


def generate_webui_tool(server: dict) -> dict:
    """
    Convert our server definition to Open WebUI external tool format.

    Open WebUI expects:
    {
        "id": "unique-id",
        "name": "Display Name",
        "type": "openapi",
        "url": "http://server:port",
        "meta": {...},
        "auth_type": "none" | "bearer",
        "auth_key": ""
    }
    """
    return {
        "id": server["id"],
        "name": server["name"],
        "type": "openapi",  # All go through our OpenAPI-compatible proxy
        "url": server["url"],
        "meta": {
            "description": server.get("description", ""),
            "tier": server.get("tier", "http"),
            "groups": server.get("groups", []),
            "generated_by": "single-proxy-auto-deploy",
            "generated_at": datetime.now().isoformat()
        },
        # Auth is handled by proxy via headers, not by Open WebUI
        "auth_type": "none",
        "auth_key": ""
    }


def generate_group_permissions(config: dict) -> dict:
    """
    Generate a summary of group permissions for documentation.

    This helps admins understand which groups have access to what.
    """
    servers = config.get("servers", [])
    special_groups = config.get("special_groups", {})

    # Build group -> servers mapping
    group_permissions = {}

    for server in servers:
        server_id = server["id"]
        for group in server.get("groups", []):
            if group not in group_permissions:
                group_permissions[group] = []
            group_permissions[group].append(server_id)

    return {
        "group_permissions": group_permissions,
        "special_groups": special_groups,
        "summary": {
            "total_groups": len(group_permissions),
            "total_servers": len(servers)
        }
    }


def generate_webui_export(config: dict) -> dict:
    """
    Generate complete Open WebUI export format.

    This includes:
    - tools: Array of tool configurations for import
    - metadata: Information about the export
    - permissions: Group permission summary (for documentation)
    """
    servers = config.get("servers", [])

    return {
        "version": "1.0",
        "format": "open-webui-tools-export",
        "metadata": {
            "exported_at": datetime.now().isoformat(),
            "source": "mcp-servers.json",
            "generator": "single-proxy-auto-deploy",
            "description": "Auto-generated from single proxy configuration",
            "note": "DO NOT EDIT MANUALLY - Regenerate from mcp-servers.json"
        },
        "tools": [generate_webui_tool(s) for s in servers],
        "permissions": generate_group_permissions(config)
    }


def main():
    """Main generator function."""
    # Parse arguments
    save_file = "--save" in sys.argv or "-s" in sys.argv
    pretty = "--pretty" in sys.argv or "-p" in sys.argv

    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        print("\nOptions:")
        print("  --save, -s     Save to webui-tools-export.json")
        print("  --pretty, -p   Pretty print JSON output")
        print("  --help, -h     Show this help message")
        return

    # Load config
    if not CONFIG_PATH.exists():
        print(f"ERROR: Config file not found: {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)

    with open(CONFIG_PATH) as f:
        config = json.load(f)

    # Generate export
    export = generate_webui_export(config)

    # Output
    indent = 2 if pretty else None

    if save_file:
        with open(OUTPUT_PATH, "w") as f:
            json.dump(export, f, indent=2)
        print(f"Saved to: {OUTPUT_PATH}")
        print(f"Tools: {len(export['tools'])}")
        print(f"Groups: {export['permissions']['summary']['total_groups']}")
        print("\nImport this file in Open WebUI:")
        print("  Admin Settings -> External Tools -> Import")
    else:
        print(json.dumps(export, indent=indent))


if __name__ == "__main__":
    main()
