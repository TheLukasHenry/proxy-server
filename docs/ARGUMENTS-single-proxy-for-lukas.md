# Arguments for Single Proxy Approach

> **For Lukas**: Use these talking points to argue for the single proxy architecture.

---

## Executive Summary

**Single Proxy = ONE source of truth, ZERO manual configuration, FULL audit trail.**

With single proxy:
- Define servers ONCE in `mcp-servers.json`
- Configure Open WebUI at deploy time via `TOOL_SERVER_CONNECTIONS` environment variable
- Seed database permissions via Kubernetes Job
- **Result: `kubectl apply` → Everything configured automatically**

---

## The Core Argument

### Before (Mixed Approach)
```
Developer → Manual UI clicks → Open WebUI tools
Developer → Manual UI clicks → Open WebUI permissions
Developer → Config file → Proxy permissions
Result: 3 places to configure, potential for desync
```

### After (Single Proxy)
```
Developer → mcp-servers.json → Auto-deploy
Result: 1 file to edit, everything syncs automatically
```

---

## Technical Evidence

### 1. Pre-Deploy Configuration (What You Asked For)

**Your question:** "Can we get tenant-group mappings before/during deploy time to build that array?"

**Answer: YES.**

Open WebUI supports `TOOL_SERVER_CONNECTIONS` environment variable:
```yaml
env:
  - name: TOOL_SERVER_CONNECTIONS
    value: '[{"type":"openapi","url":"http://mcp-proxy:8000",...}]'
```

This configures the MCP Proxy **BEFORE** Open WebUI starts. No API calls needed.

### 2. Verified JSON Format

We exported the actual format from Open WebUI's Export button:
```json
{
  "type": "openapi",
  "url": "http://mcp-proxy:8000",
  "spec_type": "url",
  "path": "openapi.json",
  "auth_type": "session",
  "info": {
    "name": "MCP Proxy",
    "description": "..."
  }
}
```

Our implementation matches this **exactly**.

### 3. Single Source of Truth

`mcp-servers.json` defines:
- Which servers exist
- Which groups can access each server
- Server descriptions and metadata

From this ONE file:
- Database is seeded (permissions)
- Open WebUI is configured (via env var)
- No manual steps required

---

## Comparison Table

| Aspect | Single Proxy | Mixed Approach |
|--------|--------------|----------------|
| **Permission Systems** | 1 (database) | 2 (proxy + WebUI) |
| **Config Files** | 1 (`mcp-servers.json`) | Multiple |
| **Deploy Automation** | Yes (env var + job) | Complex sync |
| **Add New Server** | Edit JSON, redeploy | JSON + UI + checkboxes |
| **Debug Permissions** | `SELECT * FROM group_tenant_mapping` | Check 2 systems |
| **Audit Log** | 1 location (proxy logs) | Scattered |
| **Risk of Desync** | None | High |

---

## Deploy Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    SINGLE PROXY DEPLOY                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Developer edits mcp-servers.json                         │
│     └── Defines all servers + group permissions              │
│                                                              │
│  2. kubectl apply / helm install                             │
│     └── TOOL_SERVER_CONNECTIONS env var → Open WebUI config  │
│     └── Init Job → Seeds group_tenant_mapping table          │
│                                                              │
│  3. DONE - No manual UI clicks!                              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Answers to Objections

### "But we need per-user tool permissions in Open WebUI"

**Response:** The proxy handles this. When a user calls an MCP tool:
1. Open WebUI forwards the request with user's session
2. Proxy checks `group_tenant_mapping` for user's groups
3. If allowed → route to backend
4. If denied → return 403

The permission check happens at the proxy, not in Open WebUI.

### "What if someone adds tools manually in Open WebUI?"

**Response:** Two options:
1. Use `ENABLE_PERSISTENT_CONFIG=false` to ignore UI changes
2. Accept that admins can add tools, but our automated ones are always consistent

### "How do we add a new MCP server?"

**Response:**
1. Add to `mcp-servers.json` (with groups)
2. Add API key to `secrets-template.yaml`
3. Redeploy

That's it. ONE file change + secret. No UI clicks.

---

## What We Built

| Component | Purpose |
|-----------|---------|
| `mcp-servers.json` | Single source of truth |
| `values-production.yaml` | Has `TOOL_SERVER_CONNECTIONS` for pre-deploy |
| `init-mcp-servers-job.yaml` | Seeds database at deploy time |
| `register_webui_tools.py` | Fallback API registration (optional) |
| `demo_single_proxy.py` | Demo script to show the flow |

---

## The One-Liner for Meetings

> "With single proxy, I edit ONE config file, run `kubectl apply`, and both the database permissions AND Open WebUI tool configuration are set up automatically. No manual UI clicks. No sync issues. One source of truth."

---

## Files Changed

- `kubernetes/values-production.yaml` - Added `TOOL_SERVER_CONNECTIONS`
- `mcp-proxy/config/mcp-servers.json` - Single source of truth
- `mcp-proxy/scripts/register_webui_tools.py` - Fixed to match actual export format
- `kubernetes/init-mcp-servers-job.yaml` - Seeds database

---

*Generated: 2026-01-20*
*For: Lukas - Single Proxy Architecture Arguments*
