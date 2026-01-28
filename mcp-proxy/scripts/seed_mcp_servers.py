#!/usr/bin/env python3
"""
MCP Servers Database Seeder

Reads mcp-servers.json and seeds the group_tenant_mapping table.

This demonstrates the SINGLE PROXY approach:
- ONE JSON file defines everything
- ONE database table controls ALL permissions
- ONE deploy script sets it all up

Usage:
    python seed_mcp_servers.py                    # Uses default DATABASE_URL
    DATABASE_URL=postgresql://... python seed_mcp_servers.py

Arguments for Lukas (Single Proxy Benefits):
1. Single Source of Truth - mcp-servers.json
2. One Database Table - group_tenant_mapping
3. Easy Automation - This one script does everything
4. No Sync Issues - No mismatch between systems
"""

import json
import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

# Try to import asyncpg, provide helpful error if missing
try:
    import asyncpg
except ImportError:
    print("ERROR: asyncpg not installed. Run: pip install asyncpg")
    sys.exit(1)

# Configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://openwebui:localdevpassword@localhost:5432/openwebui"
)

# Find config file relative to this script
SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR.parent / "config" / "mcp-servers.json"


def log(msg: str, level: str = "INFO"):
    """Structured logging."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {msg}")


async def create_tables(conn: asyncpg.Connection) -> bool:
    """Create required tables if they don't exist."""
    log("Creating tables if not exist...")

    try:
        # Create mcp_proxy schema
        await conn.execute("CREATE SCHEMA IF NOT EXISTS mcp_proxy")

        # Create group_tenant_mapping table in mcp_proxy schema
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS mcp_proxy.group_tenant_mapping (
                group_name VARCHAR(255) NOT NULL,
                tenant_id VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                PRIMARY KEY (group_name, tenant_id)
            )
        """)

        # Create index for faster lookups
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_group_tenant_mapping_group
            ON mcp_proxy.group_tenant_mapping(group_name)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_group_tenant_mapping_tenant
            ON mcp_proxy.group_tenant_mapping(tenant_id)
        """)

        log("Tables and indexes created/verified", "SUCCESS")
        return True

    except Exception as e:
        log(f"Error creating tables: {e}", "ERROR")
        return False


async def clear_existing_mappings(conn: asyncpg.Connection) -> int:
    """Clear existing mappings (optional - for clean redeploy)."""
    result = await conn.execute("DELETE FROM mcp_proxy.group_tenant_mapping")
    count = int(result.split()[-1]) if result else 0
    log(f"Cleared {count} existing mappings")
    return count


async def seed_group_mappings(conn: asyncpg.Connection, servers: list, clear_first: bool = False) -> int:
    """
    Seed group_tenant_mapping table from server definitions.

    Args:
        conn: Database connection
        servers: List of server configs from mcp-servers.json
        clear_first: If True, clear existing mappings first

    Returns:
        Number of mappings inserted
    """
    if clear_first:
        await clear_existing_mappings(conn)

    count = 0
    errors = 0

    for server in servers:
        server_id = server.get("id")
        server_name = server.get("name", server_id)
        groups = server.get("groups", [])

        if not server_id:
            log(f"Skipping server without ID: {server}", "WARN")
            continue

        if not groups:
            log(f"Server {server_id} has no groups defined", "WARN")
            continue

        for group in groups:
            try:
                await conn.execute("""
                    INSERT INTO mcp_proxy.group_tenant_mapping (group_name, tenant_id)
                    VALUES ($1, $2)
                    ON CONFLICT (group_name, tenant_id)
                    DO NOTHING
                """, group, server_id)
                count += 1
                log(f"  {group:25} -> {server_id}")
            except Exception as e:
                log(f"Error inserting {group} -> {server_id}: {e}", "ERROR")
                errors += 1

    log(f"Inserted/updated {count} mappings ({errors} errors)", "SUCCESS" if errors == 0 else "WARN")
    return count


async def verify_mappings(conn: asyncpg.Connection) -> dict:
    """Verify and summarize the seeded mappings."""
    log("Verifying mappings...")

    # Count total
    total = await conn.fetchval("SELECT COUNT(*) FROM mcp_proxy.group_tenant_mapping")

    # Count by group
    groups = await conn.fetch("""
        SELECT group_name, COUNT(*) as server_count
        FROM mcp_proxy.group_tenant_mapping
        GROUP BY group_name
        ORDER BY server_count DESC
    """)

    # Count by server
    servers = await conn.fetch("""
        SELECT tenant_id, COUNT(*) as group_count
        FROM mcp_proxy.group_tenant_mapping
        GROUP BY tenant_id
        ORDER BY group_count DESC
    """)

    return {
        "total_mappings": total,
        "groups": {r["group_name"]: r["server_count"] for r in groups},
        "servers": {r["tenant_id"]: r["group_count"] for r in servers}
    }


async def main(clear_first: bool = False):
    """Main seeder function."""
    print("\n" + "=" * 70)
    print("  MCP SERVERS DATABASE SEEDER - Single Proxy Demo")
    print("  For Lukas: Proving single proxy = simpler automation")
    print("=" * 70)

    # Step 1: Load config
    log(f"Loading config from: {CONFIG_PATH}")

    if not CONFIG_PATH.exists():
        log(f"Config file not found: {CONFIG_PATH}", "ERROR")
        log("Run this script from mcp-proxy directory or set CONFIG_PATH", "ERROR")
        sys.exit(1)

    with open(CONFIG_PATH) as f:
        config = json.load(f)

    servers = config.get("servers", [])
    log(f"Found {len(servers)} servers in config")

    # Step 2: Connect to database
    log(f"Connecting to database...")
    log(f"  URL: {DATABASE_URL[:50]}..." if len(DATABASE_URL) > 50 else f"  URL: {DATABASE_URL}")

    try:
        conn = await asyncpg.connect(DATABASE_URL)
        log("Database connected", "SUCCESS")
    except Exception as e:
        log(f"Failed to connect to database: {e}", "ERROR")
        log("Make sure PostgreSQL is running and DATABASE_URL is correct", "ERROR")
        sys.exit(1)

    try:
        # Step 3: Create tables
        print("\n" + "-" * 70)
        if not await create_tables(conn):
            sys.exit(1)

        # Step 4: Seed mappings
        print("\n" + "-" * 70)
        log("Seeding group_tenant_mapping table...")
        count = await seed_group_mappings(conn, servers, clear_first=clear_first)

        # Step 5: Verify
        print("\n" + "-" * 70)
        stats = await verify_mappings(conn)

        print("\n" + "-" * 70)
        log("SUMMARY:")
        log(f"  Total mappings: {stats['total_mappings']}")
        log(f"  Groups: {len(stats['groups'])}")
        for group, count in list(stats['groups'].items())[:5]:
            log(f"    - {group}: {count} servers")
        if len(stats['groups']) > 5:
            log(f"    ... and {len(stats['groups']) - 5} more groups")

        log(f"  Servers: {len(stats['servers'])}")
        for server, count in list(stats['servers'].items())[:5]:
            log(f"    - {server}: {count} groups")
        if len(stats['servers']) > 5:
            log(f"    ... and {len(stats['servers']) - 5} more servers")

    finally:
        await conn.close()
        log("Database connection closed")

    print("\n" + "=" * 70)
    print("  SEEDING COMPLETE!")
    print("=" * 70)
    print("\n  This demonstrates the Single Proxy approach:")
    print("  1. ONE JSON file (mcp-servers.json) defines everything")
    print("  2. ONE database table (group_tenant_mapping) controls permissions")
    print("  3. ONE script (this one) seeds everything at deploy time")
    print("\n  No manual UI clicks. No sync issues. Simple automation.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    # Parse arguments
    clear_first = "--clear" in sys.argv or "-c" in sys.argv

    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        print("\nOptions:")
        print("  --clear, -c    Clear existing mappings before seeding")
        print("  --help, -h     Show this help message")
        sys.exit(0)

    asyncio.run(main(clear_first=clear_first))
