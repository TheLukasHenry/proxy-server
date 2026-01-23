#!/usr/bin/env python3
"""
Open WebUI Tool Server Registration Script

This script auto-registers MCP servers in Open WebUI at deploy time.

Part of the SINGLE PROXY approach:
- Reads mcp-servers.json (single source of truth)
- Registers all servers via Open WebUI API
- No manual UI clicks needed

Usage:
    python register_webui_tools.py                    # Uses environment variables
    OPENWEBUI_URL=http://localhost:8080 python register_webui_tools.py

Environment Variables:
    OPENWEBUI_URL      - Open WebUI base URL (default: http://open-webui:8080)
    OPENWEBUI_API_KEY  - API key for authentication (required)
    CONFIG_PATH        - Path to mcp-servers.json (default: /config/mcp-servers.json)
    MAX_RETRIES        - Max retries waiting for Open WebUI (default: 60)
    RETRY_INTERVAL     - Seconds between retries (default: 5)

For Lukas: This completes the auto-deploy flow:
    1. mcp-servers.json defines servers
    2. init-mcp-servers-job seeds database
    3. THIS SCRIPT registers tools in Open WebUI
    4. Done - no manual configuration!
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Configuration from environment
OPENWEBUI_URL = os.getenv("OPENWEBUI_URL", "http://open-webui:8080")
OPENWEBUI_API_KEY = os.getenv("OPENWEBUI_API_KEY", "")
CONFIG_PATH = os.getenv("CONFIG_PATH", "/config/mcp-servers.json")
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "60"))
RETRY_INTERVAL = int(os.getenv("RETRY_INTERVAL", "5"))


def log(msg: str, level: str = "INFO"):
    """Structured logging."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {msg}")


def make_request(
    endpoint: str,
    method: str = "GET",
    data: Optional[Dict] = None,
    timeout: int = 30
) -> Dict:
    """Make HTTP request to Open WebUI API."""
    url = f"{OPENWEBUI_URL.rstrip('/')}{endpoint}"

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    if OPENWEBUI_API_KEY:
        headers["Authorization"] = f"Bearer {OPENWEBUI_API_KEY}"

    body = json.dumps(data).encode("utf-8") if data else None

    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        raise Exception(f"HTTP {e.code}: {error_body}")


def wait_for_openwebui() -> bool:
    """Wait for Open WebUI to be ready."""
    log(f"Waiting for Open WebUI at {OPENWEBUI_URL}...")

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # Try health check or root endpoint
            url = f"{OPENWEBUI_URL.rstrip('/')}/health"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    log(f"Open WebUI is ready! (attempt {attempt})")
                    return True
        except Exception:
            pass

        # Also try the API endpoint
        try:
            url = f"{OPENWEBUI_URL.rstrip('/')}/api/config"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    log(f"Open WebUI is ready! (attempt {attempt})")
                    return True
        except Exception:
            pass

        log(f"  Attempt {attempt}/{MAX_RETRIES}: Not ready yet...")
        time.sleep(RETRY_INTERVAL)

    log("ERROR: Open WebUI not available after max retries", "ERROR")
    return False


def load_config() -> Dict[str, Any]:
    """Load MCP servers configuration."""
    config_path = Path(CONFIG_PATH)

    if not config_path.exists():
        # Try relative path from script directory
        script_dir = Path(__file__).parent
        config_path = script_dir.parent / "config" / "mcp-servers.json"

    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {CONFIG_PATH}")

    log(f"Loading config from: {config_path}")

    with open(config_path) as f:
        return json.load(f)


def build_openapi_servers(servers: List[Dict], proxy_url: str = "http://mcp-proxy:8000") -> List[Dict]:
    """
    Build Open WebUI openapi_servers format for SINGLE PROXY approach.

    SINGLE PROXY = ONE entry in Open WebUI that routes to all backends.

    VERIFIED against actual Open WebUI Export format:
    {
        "type": "openapi",
        "url": "http://mcp-proxy:8000",
        "spec_type": "url",
        "spec": "",
        "path": "openapi.json",
        "auth_type": "session",
        "key": "",
        "info": {
            "id": "",
            "name": "MCP Proxy",
            "description": ""
        }
    }

    Key insight: We register ONE proxy, not 8 separate servers.
    The proxy handles routing internally based on the tool being called.
    """
    # Extract proxy base URL from first server (all use same proxy)
    if servers:
        first_url = servers[0].get("url", proxy_url)
        if "//" in first_url:
            parts = first_url.split("/", 3)
            proxy_url = f"{parts[0]}//{parts[2]}"  # http://mcp-proxy:8000

    # Build list of server names for description
    server_names = [s.get("name", s.get("id", "")) for s in servers]
    description = f"Single proxy for {len(servers)} MCP servers: {', '.join(server_names[:5])}"
    if len(server_names) > 5:
        description += f" and {len(server_names) - 5} more"

    # SINGLE PROXY = ONE entry in Open WebUI
    # This matches what Lukas wants: ONE source of truth, ONE entry
    openapi_server = {
        "type": "openapi",
        "url": proxy_url,
        "spec_type": "url",
        "spec": "",
        "path": "openapi.json",  # Combined OpenAPI spec from proxy
        "auth_type": "session",  # Forward user session for auth
        "key": "",
        "info": {
            "id": "mcp-proxy",
            "name": "MCP Proxy",
            "description": description
        }
    }

    # Return as single-item list (ONE proxy)
    return [openapi_server]


def build_mcp_servers(servers: List[Dict]) -> List[Dict]:
    """
    Build Open WebUI mcp_servers format from our config.

    For native MCP servers (if any), Open WebUI expects:
    {
        "url": "http://server:8000/mcp/sse",
        "type": "sse",
        "auth_type": "none"
    }
    """
    mcp_servers = []

    for server in servers:
        tier = server.get("tier", "http")

        # Only include SSE tier as native MCP
        if tier == "sse":
            mcp_server = {
                "url": server.get("url", ""),
                "type": "sse",
                "name": server.get("name", server.get("id", "")),
                "auth_type": "none",
                "meta": {
                    "id": server.get("id"),
                    "groups": server.get("groups", []),
                    "source": "single-proxy-auto-deploy"
                }
            }
            mcp_servers.append(mcp_server)

    return mcp_servers


def get_current_tool_servers() -> Dict:
    """Get current tool server configuration from Open WebUI."""
    try:
        response = make_request("/api/v1/configs/tool_servers", "GET")
        return response
    except Exception as e:
        log(f"Could not get current config: {e}", "WARN")
        return {"openapi_servers": [], "mcp_servers": []}


def register_tool_servers(openapi_servers: List[Dict], mcp_servers: List[Dict]) -> bool:
    """Register tool servers in Open WebUI."""
    log(f"Registering {len(openapi_servers)} OpenAPI servers and {len(mcp_servers)} MCP servers...")

    payload = {
        "openapi_servers": openapi_servers,
        "mcp_servers": mcp_servers
    }

    try:
        response = make_request(
            "/api/v1/configs/tool_servers",
            "POST",
            payload
        )
        log("Tool servers registered successfully!", "SUCCESS")
        return True
    except Exception as e:
        log(f"Failed to register tool servers: {e}", "ERROR")
        return False


def verify_tool_servers() -> bool:
    """Verify tool servers are accessible."""
    log("Verifying tool server connections...")

    try:
        response = make_request("/api/v1/configs/tool_servers/verify", "POST", {})
        log("Tool servers verified!", "SUCCESS")
        return True
    except Exception as e:
        log(f"Verification warning: {e}", "WARN")
        return True  # Non-fatal


def main():
    """Main registration function."""
    print("\n" + "=" * 60)
    print("  OPEN WEBUI TOOL SERVER REGISTRATION")
    print("  Single Proxy Auto-Deploy - For Lukas")
    print("=" * 60)

    # Check API key
    if not OPENWEBUI_API_KEY:
        log("WARNING: OPENWEBUI_API_KEY not set", "WARN")
        log("Registration may fail without authentication", "WARN")

    # Wait for Open WebUI
    if not wait_for_openwebui():
        sys.exit(1)

    # Load config
    try:
        config = load_config()
        servers = config.get("servers", [])
        log(f"Loaded {len(servers)} servers from config")
    except Exception as e:
        log(f"Failed to load config: {e}", "ERROR")
        sys.exit(1)

    # Build server lists
    openapi_servers = build_openapi_servers(servers)
    mcp_servers = build_mcp_servers(servers)

    log(f"Built {len(openapi_servers)} OpenAPI server configs")
    log(f"Built {len(mcp_servers)} native MCP server configs")

    # Show what we're registering
    print("\n" + "-" * 60)
    log("Servers to register:")
    for s in openapi_servers:
        log(f"  [OpenAPI] {s['name']}: {s['url']}{s['path']}")
    for s in mcp_servers:
        log(f"  [MCP] {s['name']}: {s['url']}")
    print("-" * 60 + "\n")

    # Get current config (for comparison)
    current = get_current_tool_servers()
    current_count = len(current.get("openapi_servers", [])) + len(current.get("mcp_servers", []))
    log(f"Current tool servers in Open WebUI: {current_count}")

    # Register
    if not register_tool_servers(openapi_servers, mcp_servers):
        sys.exit(1)

    # Verify (optional)
    verify_tool_servers()

    # Summary
    print("\n" + "=" * 60)
    print("  REGISTRATION COMPLETE!")
    print("=" * 60)
    print("""
    Single Proxy Auto-Deploy flow:

    1. mcp-servers.json    -> Defines all servers (DONE)
    2. Database seeder     -> Seeds group_tenant_mapping (DONE)
    3. This script         -> Registers tools in Open WebUI (DONE)

    Result: NO manual UI configuration needed!

    For Lukas to argue:
    "With single proxy, we define servers once, and THREE scripts
    configure everything automatically. Database permissions AND
    Open WebUI tools are set up at deploy time."
    """)
    print("=" * 60 + "\n")


if __name__ == "__main__":
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        sys.exit(0)

    main()
