# Step-by-Step Demo Guide for Lukas

> **Your Statement:** "With single proxy, I edit ONE config file, run kubectl apply, and both the database permissions AND Open WebUI tool configuration are set up automatically. No manual UI clicks. No sync issues. One source of truth."

This guide shows you how to prove this statement live.

---

## Quick Start (Local Demo)

```powershell
# Windows
.\scripts\start-local-demo.ps1

# Linux/Mac
./scripts/start-local-demo.sh
```

Then open http://localhost:3000

---

## Demo Overview (5 minutes)

```
BEFORE: Show the config file
DURING: Run docker-compose up OR kubectl apply
AFTER:  Show Open WebUI has the tool configured
PROOF:  The proxy controls permissions, not Open WebUI
```

---

## Step 1: Show the Single Source of Truth (1 min)

**Open the config file and show it:**

```bash
cat mcp-proxy/config/mcp-servers.json
```

**Say:** "This ONE file defines all 8 MCP servers and which groups can access them."

**Point out:**
- 8 servers defined (github, linear, notion, etc.)
- Each server has `groups` array (permissions)
- This is the ONLY place we configure servers

---

## Step 2: Show values-production.yaml (30 sec)

**Open the Helm values:**

```bash
cat kubernetes/values-production.yaml | grep -A5 TOOL_SERVER_CONNECTIONS
```

**Say:** "The Helm chart has `TOOL_SERVER_CONNECTIONS` environment variable. This configures Open WebUI at startup - before it even runs."

---

## Step 3: Deploy (Local or Kubernetes)

### Option A: Local Demo (Recommended for first demo)

```bash
# Windows
.\scripts\start-local-demo.ps1

# Linux/Mac
./scripts/start-local-demo.sh
```

### Option B: Kubernetes Demo

```bash
kubectl apply -f kubernetes/
```

**Say:** "One command. That's it. Database permissions AND Open WebUI configuration are set up automatically."

---

## Step 4: Open Open WebUI and Show the Tool (1 min)

1. **Navigate to:** `http://localhost:30080` (or your URL)
2. **Login** as admin
3. **Go to:** User Menu → Admin Panel → Settings → External Tools

**Say:** "Look - MCP Proxy is already configured. I didn't click anything in the UI. It was configured by the environment variable at startup."

**Show:**
- MCP Proxy is listed
- URL: `http://mcp-proxy:8000`
- Auth: Session (forwards user credentials)

---

## Step 5: Prove Permissions Work (2 min)

### Test 1: Admin User (has access)

1. Start a new chat
2. Ask: "What MCP tools do you have access to?"
3. The AI should list the tools from MCP Proxy

**Say:** "As admin, I have access because my group is in the database."

### Test 2: Show the Database

```bash
# Connect to database and query
psql $DATABASE_URL -c "SELECT * FROM group_tenant_mapping LIMIT 10;"
```

**Say:** "These mappings came from mcp-servers.json. ONE file → database. No manual entry."

---

## Step 6: The Killer Demo - Add a New Server (1 min)

**Say:** "Watch how easy it is to add a new MCP server."

### Step 6a: Edit the config file

```bash
# Add a new server to mcp-servers.json
{
  "id": "new-server",
  "name": "New Server",
  "url": "http://mcp-proxy:8000/new-server",
  "groups": ["MCP-Admin", "Tenant-Google"]
}
```

### Step 6b: Redeploy

```bash
kubectl apply -f kubernetes/
```

### Step 6c: Show it's configured

**Say:** "That's it. I edited ONE file, ran ONE command. The new server is now:
1. In the database (permissions)
2. In Open WebUI (tool configuration)

No UI clicks. No sync issues."

---

## Comparison Slide (for meetings)

| Action | Single Proxy | Mixed Approach |
|--------|--------------|----------------|
| Add new server | Edit JSON + `kubectl apply` | Edit JSON + UI clicks + checkboxes |
| Change permissions | Edit JSON + `kubectl apply` | Edit JSON + UI clicks |
| Debug "access denied" | `SELECT * FROM group_tenant_mapping` | Check 2 systems |
| Audit who has access | Query database | Check multiple places |

---

## The One-Liner to Repeat

> "With single proxy, I edit ONE config file, run `kubectl apply`, and both the database permissions AND Open WebUI tool configuration are set up automatically. No manual UI clicks. No sync issues. One source of truth."

---

## If They Ask Questions

### "What if someone adds tools manually in Open WebUI?"

**Answer:** "Two options:
1. We can set `ENABLE_PERSISTENT_CONFIG=false` to ignore UI changes
2. Or we accept manual additions, but our automated config is always consistent"

### "How do permissions work?"

**Answer:** "When a user calls an MCP tool:
1. Open WebUI forwards the request with user's session
2. Our proxy checks `group_tenant_mapping` for user's Entra ID groups
3. If allowed → route to backend
4. If denied → return 403

The permission check happens at the proxy level."

### "What about secrets/API keys?"

**Answer:** "All in `secrets-template.yaml`. One place for all API keys. Also deployed with `kubectl apply`."

---

## Quick Demo Commands

```bash
# Show config
cat mcp-proxy/config/mcp-servers.json | head -30

# Show TOOL_SERVER_CONNECTIONS in Helm values
grep -A5 TOOL_SERVER_CONNECTIONS kubernetes/values-production.yaml

# Run the demo script
python mcp-proxy/scripts/demo_single_proxy.py

# Query database permissions
psql $DATABASE_URL -c "SELECT group_name, tenant_id FROM group_tenant_mapping ORDER BY tenant_id;"
```

---

*Demo Guide for Lukas - Single Proxy Approach*
