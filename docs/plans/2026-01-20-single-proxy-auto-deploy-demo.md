# Single Proxy Auto-Deploy Demo - Research Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a demo showing how to auto-configure ALL MCP servers through a single proxy at deploy time, using the `group_tenant_mapping` database as the source of truth.

**Architecture:** At deploy time, read MCP server definitions from a ConfigMap, seed the `group_tenant_mapping` table, and generate the Open WebUI tool configuration JSON. This proves the single proxy approach is simpler and more automatable than mixed approaches.

**Tech Stack:** Python, PostgreSQL, Kubernetes ConfigMap, JSON

---

## Context: What Lukas Wants to Prove

Lukas wants arguments for the **single proxy approach** (Option B):

| Single Proxy ✅ | Mixed Approach ❌ |
|-----------------|-------------------|
| One database table | Two permission systems |
| One deploy script | Complex sync logic |
| One audit log | Scattered logs |
| Easy debugging | "Is it proxy or WebUI?" |

**This demo shows:** With single proxy, you define servers ONCE and deploy automatically.

---

## Task 1: Create MCP Servers Definition File

**Files:**
- Create: `mcp-proxy/config/mcp-servers.json`

**Step 1: Create the JSON definition file**

This file defines ALL MCP servers that will route through our proxy:

```json
{
  "version": "1.0",
  "description": "MCP Servers - Single Proxy Configuration",
  "servers": [
    {
      "id": "github",
      "name": "GitHub MCP",
      "url": "http://mcp-proxy:8000/github",
      "type": "openapi",
      "description": "GitHub operations via MCP Proxy",
      "groups": ["MCP-Admin", "MCP-GitHub", "Tenant-Google", "Tenant-Microsoft"]
    },
    {
      "id": "linear",
      "name": "Linear MCP",
      "url": "http://mcp-proxy:8000/linear",
      "type": "openapi",
      "description": "Linear issue tracking via MCP Proxy",
      "groups": ["MCP-Admin", "Tenant-Google"]
    },
    {
      "id": "notion",
      "name": "Notion MCP",
      "url": "http://mcp-proxy:8000/notion",
      "type": "openapi",
      "description": "Notion knowledge base via MCP Proxy",
      "groups": ["MCP-Admin", "Tenant-Google", "Tenant-AcmeCorp"]
    },
    {
      "id": "filesystem",
      "name": "Filesystem MCP",
      "url": "http://mcp-proxy:8000/filesystem",
      "type": "openapi",
      "description": "Filesystem operations via MCP Proxy",
      "groups": ["MCP-Admin", "MCP-Filesystem", "Tenant-Google", "Tenant-Microsoft", "Tenant-AcmeCorp"]
    },
    {
      "id": "atlassian",
      "name": "Atlassian MCP",
      "url": "http://mcp-proxy:8000/atlassian",
      "type": "openapi",
      "description": "Jira/Confluence via MCP Proxy",
      "groups": ["MCP-Admin", "Tenant-Google", "Tenant-Microsoft"]
    }
  ],
  "special_groups": {
    "MCP-Admin": {
      "description": "Full access to ALL servers",
      "access": "*"
    }
  }
}
```

**Step 2: Verify JSON is valid**

Run: `python -m json.tool mcp-proxy/config/mcp-servers.json`
Expected: Pretty-printed JSON with no errors

**Step 3: Commit**

```bash
git add mcp-proxy/config/mcp-servers.json
git commit -m "feat: add MCP servers definition for auto-deploy demo"
```

---

## Task 2: Create Database Seeder Script

**Files:**
- Create: `mcp-proxy/scripts/seed_mcp_servers.py`

**Step 1: Write the seeder script**

```python
#!/usr/bin/env python3
"""
MCP Servers Database Seeder

Reads mcp-servers.json and seeds:
1. group_tenant_mapping table (our proxy permissions)

This demonstrates the single proxy approach:
- ONE JSON file defines everything
- ONE database table controls permissions
- ONE deploy script sets it all up
"""

import json
import asyncio
import asyncpg
import os
from pathlib import Path

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://openwebui:localdevpassword@localhost:5432/openwebui"
)

CONFIG_PATH = Path(__file__).parent.parent / "config" / "mcp-servers.json"


async def create_tables(conn: asyncpg.Connection):
    """Create tables if they don't exist."""
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS group_tenant_mapping (
            group_name VARCHAR(255) NOT NULL,
            tenant_id VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            PRIMARY KEY (group_name, tenant_id)
        )
    """)
    print("✅ Tables verified/created")


async def seed_group_mappings(conn: asyncpg.Connection, servers: list):
    """Seed group_tenant_mapping from server definitions."""
    count = 0

    for server in servers:
        server_id = server["id"]
        groups = server.get("groups", [])

        for group in groups:
            await conn.execute("""
                INSERT INTO group_tenant_mapping (group_name, tenant_id)
                VALUES ($1, $2)
                ON CONFLICT (group_name, tenant_id) DO NOTHING
            """, group, server_id)
            count += 1

    print(f"✅ Seeded {count} group→tenant mappings")


async def main():
    """Main seeder function."""
    print("=" * 60)
    print("MCP Servers Database Seeder - Single Proxy Demo")
    print("=" * 60)

    # Load config
    print(f"\n📖 Loading config from: {CONFIG_PATH}")
    with open(CONFIG_PATH) as f:
        config = json.load(f)

    servers = config.get("servers", [])
    print(f"   Found {len(servers)} servers")

    # Connect to database
    print(f"\n🔌 Connecting to database...")
    conn = await asyncpg.connect(DATABASE_URL)

    try:
        # Create tables
        print("\n📋 Creating tables...")
        await create_tables(conn)

        # Seed data
        print("\n🌱 Seeding group_tenant_mapping...")
        await seed_group_mappings(conn, servers)

        # Verify
        print("\n🔍 Verification:")
        rows = await conn.fetch("SELECT * FROM group_tenant_mapping ORDER BY group_name, tenant_id")
        print(f"   Total mappings: {len(rows)}")

        # Show sample
        print("\n📊 Sample mappings:")
        for row in rows[:10]:
            print(f"   {row['group_name']:20} → {row['tenant_id']}")
        if len(rows) > 10:
            print(f"   ... and {len(rows) - 10} more")

    finally:
        await conn.close()

    print("\n" + "=" * 60)
    print("✅ Database seeding complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
```

**Step 2: Run the seeder locally to test**

Run: `cd mcp-proxy && python scripts/seed_mcp_servers.py`

Expected output:
```
============================================================
MCP Servers Database Seeder - Single Proxy Demo
============================================================

📖 Loading config from: .../config/mcp-servers.json
   Found 5 servers

🔌 Connecting to database...

📋 Creating tables...
✅ Tables verified/created

🌱 Seeding group_tenant_mapping...
✅ Seeded 17 group→tenant mappings

🔍 Verification:
   Total mappings: 17

📊 Sample mappings:
   MCP-Admin            → github
   MCP-Admin            → linear
   ...

============================================================
✅ Database seeding complete!
============================================================
```

**Step 3: Commit**

```bash
git add mcp-proxy/scripts/seed_mcp_servers.py
git commit -m "feat: add database seeder for single proxy demo"
```

---

## Task 3: Create Open WebUI Tool Export Generator

**Files:**
- Create: `mcp-proxy/scripts/generate_webui_tools.py`

**Step 1: Write the generator script**

This shows how we can generate Open WebUI's import JSON from our single source of truth:

```python
#!/usr/bin/env python3
"""
Open WebUI Tool Configuration Generator

Reads mcp-servers.json and generates the JSON format
that Open WebUI uses for tool import.

This demonstrates:
- Single source of truth (mcp-servers.json)
- Can generate configs for ANY system from this file
- No need to manually configure Open WebUI UI
"""

import json
from pathlib import Path
from datetime import datetime

CONFIG_PATH = Path(__file__).parent.parent / "config" / "mcp-servers.json"
OUTPUT_PATH = Path(__file__).parent.parent / "config" / "webui-tools-export.json"


def generate_webui_tool(server: dict) -> dict:
    """Convert our server definition to Open WebUI tool format."""
    return {
        "id": server["id"],
        "name": server["name"],
        "type": "openapi",  # All go through our OpenAPI proxy
        "url": server["url"],
        "meta": {
            "description": server.get("description", ""),
            "manifest_info": {
                "contact": {
                    "name": "MCP Proxy",
                    "url": "http://mcp-proxy:8000"
                }
            }
        },
        "auth_type": "none",  # Proxy handles auth via headers
        "auth_key": ""
    }


def generate_webui_export(config: dict) -> dict:
    """Generate full Open WebUI export format."""
    servers = config.get("servers", [])

    return {
        "version": "1.0",
        "exported_at": datetime.now().isoformat(),
        "source": "single-proxy-auto-deploy",
        "tools": [generate_webui_tool(s) for s in servers],
        "note": "Generated from mcp-servers.json - DO NOT EDIT MANUALLY"
    }


def main():
    print("=" * 60)
    print("Open WebUI Tool Configuration Generator")
    print("=" * 60)

    # Load config
    print(f"\n📖 Loading config from: {CONFIG_PATH}")
    with open(CONFIG_PATH) as f:
        config = json.load(f)

    # Generate export
    print("\n🔧 Generating Open WebUI tool export...")
    export = generate_webui_export(config)

    # Save
    print(f"\n💾 Saving to: {OUTPUT_PATH}")
    with open(OUTPUT_PATH, "w") as f:
        json.dump(export, f, indent=2)

    # Show preview
    print("\n📋 Preview of generated export:")
    print("-" * 40)
    print(json.dumps(export["tools"][0], indent=2))
    print("-" * 40)
    print(f"... and {len(export['tools']) - 1} more tools")

    print("\n" + "=" * 60)
    print("✅ Export generated!")
    print(f"   File: {OUTPUT_PATH}")
    print(f"   Tools: {len(export['tools'])}")
    print("\n💡 This file can be imported into Open WebUI via:")
    print("   Admin Settings → External Tools → Import")
    print("=" * 60)


if __name__ == "__main__":
    main()
```

**Step 2: Run the generator**

Run: `cd mcp-proxy && python scripts/generate_webui_tools.py`

Expected: Creates `config/webui-tools-export.json` with importable format

**Step 3: Commit**

```bash
git add mcp-proxy/scripts/generate_webui_tools.py
git commit -m "feat: add Open WebUI tool export generator"
```

---

## Task 4: Create Kubernetes Init Job

**Files:**
- Create: `kubernetes/init-mcp-servers-job.yaml`

**Step 1: Write the Kubernetes Job**

```yaml
# kubernetes/init-mcp-servers-job.yaml
#
# This Job runs at deploy time to:
# 1. Wait for PostgreSQL to be ready
# 2. Seed the group_tenant_mapping table
#
# Demonstrates: Single proxy = ONE deploy step for permissions
apiVersion: batch/v1
kind: Job
metadata:
  name: init-mcp-servers
  namespace: open-webui
  labels:
    app: init-mcp-servers
spec:
  ttlSecondsAfterFinished: 300  # Clean up after 5 minutes
  template:
    metadata:
      labels:
        app: init-mcp-servers
    spec:
      restartPolicy: OnFailure

      # Wait for PostgreSQL to be ready
      initContainers:
        - name: wait-for-postgres
          image: postgres:15-alpine
          command:
            - sh
            - -c
            - |
              echo "Waiting for PostgreSQL..."
              until pg_isready -h postgresql -p 5432 -U openwebui; do
                echo "PostgreSQL not ready, waiting..."
                sleep 2
              done
              echo "PostgreSQL is ready!"
          env:
            - name: PGPASSWORD
              valueFrom:
                secretKeyRef:
                  name: postgresql-secret
                  key: password

      containers:
        - name: seed-database
          image: python:3.11-slim
          command:
            - sh
            - -c
            - |
              pip install asyncpg
              python /scripts/seed_mcp_servers.py
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: postgresql-secret
                  key: database-url
          volumeMounts:
            - name: scripts
              mountPath: /scripts
            - name: config
              mountPath: /app/config

      volumes:
        - name: scripts
          configMap:
            name: mcp-seeder-scripts
        - name: config
          configMap:
            name: mcp-servers-config
---
# ConfigMap with the seeder script
apiVersion: v1
kind: ConfigMap
metadata:
  name: mcp-seeder-scripts
  namespace: open-webui
data:
  seed_mcp_servers.py: |
    # Script content from Task 2 goes here
    # (In production, use separate file or Helm template)
---
# ConfigMap with MCP servers definition
apiVersion: v1
kind: ConfigMap
metadata:
  name: mcp-servers-config
  namespace: open-webui
data:
  mcp-servers.json: |
    {
      "version": "1.0",
      "servers": [
        {"id": "github", "name": "GitHub MCP", "url": "http://mcp-proxy:8000/github", "groups": ["MCP-Admin", "MCP-GitHub"]},
        {"id": "linear", "name": "Linear MCP", "url": "http://mcp-proxy:8000/linear", "groups": ["MCP-Admin"]},
        {"id": "notion", "name": "Notion MCP", "url": "http://mcp-proxy:8000/notion", "groups": ["MCP-Admin"]},
        {"id": "filesystem", "name": "Filesystem MCP", "url": "http://mcp-proxy:8000/filesystem", "groups": ["MCP-Admin", "MCP-Filesystem"]}
      ]
    }
```

**Step 2: Verify YAML syntax**

Run: `kubectl apply --dry-run=client -f kubernetes/init-mcp-servers-job.yaml`
Expected: No errors

**Step 3: Commit**

```bash
git add kubernetes/init-mcp-servers-job.yaml
git commit -m "feat: add Kubernetes init job for MCP servers"
```

---

## Task 5: Create Demo Script (All-in-One)

**Files:**
- Create: `mcp-proxy/scripts/demo_single_proxy.py`

**Step 1: Write the demo script**

```python
#!/usr/bin/env python3
"""
Single Proxy Demo Script

This script demonstrates the complete single proxy workflow:
1. Load MCP server definitions from JSON
2. Seed database with group→tenant mappings
3. Generate Open WebUI import file
4. Show the argument: ONE source of truth = simple automation

Run: python demo_single_proxy.py
"""

import json
import asyncio
import os
from pathlib import Path
from datetime import datetime

# Simulated database (for demo without actual PostgreSQL)
DEMO_DB = {
    "group_tenant_mapping": []
}


def load_config():
    """Load MCP servers config."""
    config_path = Path(__file__).parent.parent / "config" / "mcp-servers.json"
    if not config_path.exists():
        print("❌ Config not found. Creating demo config...")
        demo_config = {
            "version": "1.0",
            "servers": [
                {"id": "github", "name": "GitHub", "url": "http://mcp-proxy:8000/github",
                 "groups": ["MCP-Admin", "MCP-GitHub", "Tenant-Google"]},
                {"id": "linear", "name": "Linear", "url": "http://mcp-proxy:8000/linear",
                 "groups": ["MCP-Admin", "Tenant-Google"]},
                {"id": "notion", "name": "Notion", "url": "http://mcp-proxy:8000/notion",
                 "groups": ["MCP-Admin", "Tenant-AcmeCorp"]},
            ]
        }
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            json.dump(demo_config, f, indent=2)

    with open(config_path) as f:
        return json.load(f)


def seed_database(servers):
    """Simulate seeding group_tenant_mapping table."""
    print("\n" + "=" * 60)
    print("STEP 2: Seed Database (group_tenant_mapping)")
    print("=" * 60)

    for server in servers:
        for group in server.get("groups", []):
            mapping = {"group_name": group, "tenant_id": server["id"]}
            DEMO_DB["group_tenant_mapping"].append(mapping)
            print(f"   INSERT: {group:20} → {server['id']}")

    print(f"\n✅ Inserted {len(DEMO_DB['group_tenant_mapping'])} mappings")


def generate_webui_export(servers):
    """Generate Open WebUI tool import JSON."""
    print("\n" + "=" * 60)
    print("STEP 3: Generate Open WebUI Import JSON")
    print("=" * 60)

    tools = []
    for s in servers:
        tools.append({
            "id": s["id"],
            "name": s["name"],
            "type": "openapi",
            "url": s["url"],
            "auth_type": "none"
        })

    export = {
        "version": "1.0",
        "exported_at": datetime.now().isoformat(),
        "tools": tools
    }

    print(json.dumps(export, indent=2))
    return export


def show_arguments():
    """Show the arguments for single proxy approach."""
    print("\n" + "=" * 60)
    print("ARGUMENTS FOR SINGLE PROXY APPROACH")
    print("=" * 60)

    arguments = [
        ("Single Source of Truth", "mcp-servers.json defines EVERYTHING"),
        ("One Database Table", "group_tenant_mapping controls ALL permissions"),
        ("Easy Automation", "One script seeds everything at deploy time"),
        ("No Sync Issues", "No mismatch between Open WebUI and proxy"),
        ("Simple Debugging", "Permission denied? Check one table"),
        ("Audit Trail", "All requests go through proxy → one log"),
        ("Tenant Isolation", "Proxy enforces boundaries at network level"),
    ]

    for title, desc in arguments:
        print(f"\n✅ {title}")
        print(f"   {desc}")


def show_comparison():
    """Show comparison with mixed approach."""
    print("\n" + "=" * 60)
    print("COMPARISON: SINGLE PROXY vs MIXED APPROACH")
    print("=" * 60)

    print("""
    ┌─────────────────────┬──────────────────────┬─────────────────────┐
    │ Aspect              │ Single Proxy ✅      │ Mixed Approach ❌   │
    ├─────────────────────┼──────────────────────┼─────────────────────┤
    │ Permission System   │ 1 table              │ 2 systems           │
    │ Config Files        │ 1 JSON               │ Multiple places     │
    │ Deploy Automation   │ 1 script             │ Complex sync        │
    │ Add New Server      │ Add to JSON + 1 row  │ JSON + UI + sync    │
    │ Debug Permissions   │ Check 1 table        │ Check 2 systems     │
    │ Audit Log           │ 1 location           │ Scattered           │
    │ Secret Management   │ 1 secrets file       │ Multiple places     │
    └─────────────────────┴──────────────────────┴─────────────────────┘
    """)


def main():
    print("\n" + "=" * 60)
    print("🚀 SINGLE PROXY AUTO-DEPLOY DEMO")
    print("=" * 60)

    # Step 1: Load config
    print("\n" + "=" * 60)
    print("STEP 1: Load MCP Servers Config")
    print("=" * 60)
    config = load_config()
    servers = config.get("servers", [])
    print(f"✅ Loaded {len(servers)} servers from mcp-servers.json")
    for s in servers:
        print(f"   - {s['name']} ({s['id']})")

    # Step 2: Seed database
    seed_database(servers)

    # Step 3: Generate Open WebUI export
    generate_webui_export(servers)

    # Step 4: Show arguments
    show_arguments()

    # Step 5: Show comparison
    show_comparison()

    print("\n" + "=" * 60)
    print("✅ DEMO COMPLETE")
    print("=" * 60)
    print("\nThis demo shows: With single proxy, deploy is automated.")
    print("kubectl apply → Database seeded → All MCP servers configured\n")


if __name__ == "__main__":
    main()
```

**Step 2: Run the demo**

Run: `cd mcp-proxy && python scripts/demo_single_proxy.py`

Expected: Full demo output showing the single proxy workflow

**Step 3: Commit**

```bash
git add mcp-proxy/scripts/demo_single_proxy.py
git commit -m "feat: add single proxy demo script for Lukas"
```

---

## Task 6: Update Documentation

**Files:**
- Modify: `docs/RESEARCH-auto-deploy-mcp-servers-2026-01-19.md`

**Step 1: Add demo results to documentation**

Add a section showing the demo output and conclusions.

**Step 2: Commit**

```bash
git add docs/RESEARCH-auto-deploy-mcp-servers-2026-01-19.md
git commit -m "docs: add demo results to auto-deploy research"
```

---

## Summary: What This Demo Proves

| Aspect | Single Proxy Approach |
|--------|----------------------|
| **Config** | ONE JSON file (`mcp-servers.json`) |
| **Permissions** | ONE database table (`group_tenant_mapping`) |
| **Deploy** | ONE script seeds everything |
| **Add Server** | Add to JSON → re-run script |
| **Debugging** | Query ONE table |

**Lukas can argue:**

> "With single proxy, I define servers once in `mcp-servers.json`, run one deploy script, and everything is configured. No manual UI clicks. No sync issues between systems. One database table controls all permissions."

---

## Files Created

```
mcp-proxy/
├── config/
│   ├── mcp-servers.json           # Server definitions
│   └── webui-tools-export.json    # Generated export
├── scripts/
│   ├── seed_mcp_servers.py        # Database seeder
│   ├── generate_webui_tools.py    # Export generator
│   └── demo_single_proxy.py       # All-in-one demo

kubernetes/
└── init-mcp-servers-job.yaml      # Deploy-time init job
```

---

*Plan created: January 20, 2026*
