# Research: Auto-Deploy MCP Servers at Deploy Time

**Date:** January 19, 2026
**Purpose:** Research how to automatically configure MCP servers at Kubernetes deploy time
**Context:** Lukas wants arguments for using a single proxy server approach

---

## The Goal

```
BEFORE (Manual):
Admin → Open WebUI → Add Tool → Fill form → Save → Repeat 70x 😫

AFTER (Automated):
kubectl apply → All 70 MCP servers auto-configured ✅
```

---

## The Problem: Two Permission Systems

Currently there are TWO separate systems managing MCP permissions:

### System 1: Open WebUI Native Permissions
- Admin Panel → Groups → Checkboxes
- Controls: Models, Knowledge, Direct MCP connections
- Storage: Open WebUI's internal database

### System 2: MCP Proxy Permissions (Our Custom)
- Database: `group_tenant_mapping` table
- Controls: Which MCP servers user can access via proxy
- Storage: PostgreSQL

**These are NOT synced automatically.**

---

## Lukas's Question

> "Looking into if it's possible to get those tenant-group mappings before/during deploy time in order to build that array would be very cool. We'd also need to get the tenant's secrets before/during."

---

## Solution Options

### Solution 1: Pre-Seed Open WebUI Database (Direct SQL)

```
Init Container → PostgreSQL (INSERT) → Open WebUI (reads DB)
```

**Pros:** Direct, fast, no API needed
**Cons:** Need to know Open WebUI's exact table schema (may change between versions)

### Solution 2: Open WebUI API at Startup (Recommended)

```
Init Container → Open WebUI REST API → Config Saved
```

**Pros:** Uses official API, version-safe
**Cons:** Need to wait for Open WebUI to start first

### Solution 3: ConfigMap with MCP Server Array (Best for GitOps)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mcp-servers-config
data:
  mcp-servers.json: |
    {
      "tools": [
        {
          "id": "github-mcp",
          "name": "GitHub MCP",
          "url": "http://mcp-proxy:8000/github",
          "meta": {"tenant_id": "github"}
        }
      ],
      "group_mappings": [
        {"group": "MCP-Admin", "tools": ["*"]},
        {"group": "MCP-GitHub", "tools": ["github-mcp"]}
      ]
    }
```

**Pros:** Version controlled, GitOps friendly
**Cons:** Need mechanism to import into Open WebUI

### Solution 4: Python Init Script (Most Flexible)

```python
# Seeds BOTH systems at deploy time
def deploy():
    seed_group_tenant_mapping()  # Our proxy permissions
    import_to_open_webui()       # Open WebUI permissions
```

**Pros:** Full control, handles both systems
**Cons:** More code to maintain

### Solution 5: Helm Values + Post-Install Hook

```yaml
mcpServers:
  - id: github
    name: GitHub MCP
    groups: [MCP-Admin, MCP-GitHub]
    secrets:
      GITHUB_TOKEN: "{{ .Values.secrets.githubToken }}"
```

**Pros:** Best for production, Helm native
**Cons:** Requires Helm setup

---

## Recommended Architecture

```
1. DEFINE (Git Repository)
   └── kubernetes/mcp-servers-config.yaml (ConfigMap)
       - All 70 MCP server definitions
       - Group→Tenant mappings

2. SECRETS (Kubernetes Secrets)
   └── kubernetes/mcp-secrets.yaml
       - API keys for each tenant

3. DEPLOY (kubectl apply)
   └── Init Job runs:
       a) Seeds group_tenant_mapping table
       b) Waits for Open WebUI
       c) Imports MCP servers via API

4. READY
   └── All 70 MCP servers configured, no manual clicks!
```

---

## Arguments FOR Single Proxy Server (Option B)

### Argument 1: Single Source of Truth
```
Single Proxy:  group_tenant_mapping → ONE place to manage
Mixed Approach: group_tenant_mapping + Open WebUI checkboxes → TWO places, can desync
```

### Argument 2: Easier Automation
```
Single Proxy:  Deploy script seeds ONE database table
Mixed Approach: Deploy script must update TWO systems and keep them in sync
```

### Argument 3: Consistent Audit Trail
```
Single Proxy:  All access goes through proxy → ONE log to audit
Mixed Approach: Some through proxy, some direct → scattered logs
```

### Argument 4: Simpler Debugging
```
Single Proxy:  User can't access? Check group_tenant_mapping
Mixed Approach: User can't access? Check proxy DB AND Open WebUI checkboxes
```

### Argument 5: Multi-Tenant Isolation
```
Single Proxy:  Proxy enforces tenant boundaries at network level
Mixed Approach: Open WebUI's native permissions may not have same isolation guarantees
```

### Argument 6: Secret Management
```
Single Proxy:  All API keys in ONE place (mcp-secrets)
Mixed Approach: Some keys in proxy, some in Open WebUI → scattered secrets
```

### Argument 7: Scalability
```
Single Proxy:  Add new MCP server = add to proxy config + one DB row
Mixed Approach: Add to proxy + add to Open WebUI + configure checkboxes
```

---

## What We Need to Research

| Item | Action |
|------|--------|
| 1 | Get Open WebUI's exact JSON format for tool import/export |
| 2 | Find Open WebUI API endpoints for tool management |
| 3 | Check if Open WebUI has env var for pre-loading tools |
| 4 | Verify database table schema for direct seeding |

---

## Next Steps

1. Export one MCP server from Open WebUI to get JSON format
2. Test API endpoint for importing tools
3. Build proof-of-concept init script
4. Demo single proxy approach with auto-deploy

---

*Generated: January 19, 2026*
