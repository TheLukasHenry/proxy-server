# Phase 3C Deployment Guide — Live Server (Hetzner)

> **Date:** 2026-02-11
> **Server:** 46.224.193.25 (ai-ui.coolestdomain.win)
> **Branch:** `fix/mcp-network-split`

## What Was Implemented Today

1. **Webhook Automation Pipe Function** (`open-webui-functions/webhook_pipe.py`)
   - AI reasoning + MCP tool execution + n8n workflow triggering in a single request
   - 4-phase pipeline: fetch tools/workflows → plan actions → execute → summarize
   - Registers as model `webhook_automation.webhook-automation` in Open WebUI

2. **Automation Webhook Handler** (`webhook-handler/handlers/automation.py`)
   - New endpoint `POST /webhook/automation?source=...&instructions=...`
   - Delegates to the pipe function via Open WebUI chat completions API

3. **Multi-tenancy with Linear & Notion**
   - API keys added to `.env` and `docker-compose.unified.yml`
   - Tenant isolation verified: groups only see tools they're authorized for

4. **n8n Integration**
   - Pipe function discovers n8n workflows and triggers them via webhook
   - Hello-world workflow tested end-to-end

5. **Database Schema Sync**
   - Added missing tables: `api_analytics`, `tenant_server_endpoints`
   - Added missing views: `user_server_access`, `group_summary`
   - Local schema now matches live

---

## Deployment Steps

### Step 1: SSH into the Server

```bash
ssh root@46.224.193.25
cd /opt/mcp-proxy
```

### Step 2: Pull Latest Code

```bash
git fetch origin fix/mcp-network-split
git checkout fix/mcp-network-split
git pull origin fix/mcp-network-split
```

### Step 3: Update `.env` on Live Server

Add these new variables to `/opt/mcp-proxy/.env`:

```bash
# Linear API Key
LINEAR_API_KEY=<your-linear-api-key>

# Notion API Key
NOTION_API_KEY=<your-notion-api-key>

# n8n Configuration
N8N_USER=admin
N8N_PASSWORD=<choose-a-secure-password>
# N8N_API_KEY — set after first n8n login (Settings → API → Create API Key)
N8N_API_KEY=

# AI Model (update if needed)
AI_MODEL=gpt-5
```

> **Important:** The OPENWEBUI_API_KEY on live should remain the live server's admin API key, NOT the local one. Each environment has its own user/JWT.

### Step 4: Rebuild and Restart Docker Services

```bash
docker compose -f docker-compose.unified.yml down
docker compose -f docker-compose.unified.yml up -d --build
```

Wait for all services to be healthy:

```bash
docker compose -f docker-compose.unified.yml ps
```

Expected: `open-webui`, `mcp-proxy`, `postgres`, `caddy`, `webhook-handler`, `n8n` all running.

### Step 5: Configure n8n (First Time Only)

1. Open `https://ai-ui.coolestdomain.win/n8n/` in browser
2. Create admin account with the credentials from `.env`
3. Go to **Settings → API → Create API Key**
4. Copy the API key and update `.env`:
   ```
   N8N_API_KEY=<paste-key-here>
   ```
5. Restart webhook-handler to pick up the new key:
   ```bash
   docker compose -f docker-compose.unified.yml restart webhook-handler
   ```

### Step 6: Install the Pipe Function in Open WebUI

1. Log into Open WebUI at `https://ai-ui.coolestdomain.win`
2. Go to **Admin Panel → Workspace → Functions**
3. Click **+ Add Function** (or **Create new function**)
4. Set:
   - **Function ID:** `webhook_automation`
   - **Function Name:** `Webhook Automation`
5. Paste the entire contents of `open-webui-functions/webhook_pipe.py`
6. Click **Save**
7. Toggle the function **Active** and **Global** (so all users can access it)

### Step 7: Configure Pipe Function Valves

1. In the Functions list, click the **gear icon** on "Webhook Automation"
2. Set these Valve values:

| Valve | Value |
|-------|-------|
| `OPENWEBUI_API_URL` | `http://localhost:8080` |
| `OPENWEBUI_API_KEY` | *(paste live admin API key)* |
| `AI_MODEL` | `gpt-5` |
| `MCP_PROXY_URL` | `http://mcp-proxy:8000` |
| `MCP_USER_EMAIL` | `admin@example.com` |
| `MCP_USER_GROUPS` | `Tenant-Google` |
| `N8N_URL` | `http://n8n:5678` |
| `N8N_API_KEY` | *(paste n8n API key from Step 5)* |
| `TIMEOUT_SECONDS` | `90` |
| `MAX_TOOL_CALLS` | `5` |

> **Note:** `MCP_USER_GROUPS` controls which MCP tools the pipe function can see. Use `Tenant-Google` for access to all tools including Linear and Notion, or adjust per tenant.

### Step 8: Verify Deployment

**Test 1: Check model is registered**
```bash
curl -s https://ai-ui.coolestdomain.win/api/models \
  -H "Authorization: Bearer <ADMIN_API_KEY>" | python3 -c "
import sys,json
models = json.load(sys.stdin)
names = [m.get('name','') for m in models.get('data',[])]
print('webhook-automation found!' if 'Webhook Automation' in names else 'NOT FOUND')
"
```

**Test 2: Basic automation endpoint**
```bash
curl -X POST https://ai-ui.coolestdomain.win/webhook/automation \
  -H "Content-Type: application/json" \
  -d '{"event":"test","message":"Hello from deployment test"}' \
  -G --data-urlencode "source=manual" \
  --data-urlencode "instructions=Just say hello and confirm you are working"
```

Expected: JSON response with `"success": true` and AI-generated response.

**Test 3: MCP tool execution**
```bash
curl -X POST https://ai-ui.coolestdomain.win/webhook/automation \
  -H "Content-Type: application/json" \
  -d '{"event":"test"}' \
  -G --data-urlencode "source=manual" \
  --data-urlencode "instructions=Search GitHub for mcp-proxy repositories"
```

Expected: AI response with GitHub search results from the MCP tool.

**Test 4: n8n workflow (after creating a workflow)**
```bash
curl -X POST https://ai-ui.coolestdomain.win/webhook/automation \
  -H "Content-Type: application/json" \
  -d '{"event":"test"}' \
  -G --data-urlencode "source=manual" \
  --data-urlencode "instructions=Trigger the hello-world n8n workflow"
```

**Test 5: Multi-tenant access control**
```bash
# Should return tools for Tenant-Google (includes Linear, Notion)
curl -s http://mcp-proxy:8000/tools \
  -H "X-User-Email: admin@example.com" \
  -H "X-User-Groups: Tenant-Google"

# Should NOT include Linear/Notion for Tenant-Microsoft
curl -s http://mcp-proxy:8000/tools \
  -H "X-User-Email: admin@example.com" \
  -H "X-User-Groups: Tenant-Microsoft"
```

---

## Files Changed (Summary)

| File | Change | Description |
|------|--------|-------------|
| `open-webui-functions/webhook_pipe.py` | NEW | Pipe function — AI + MCP + n8n |
| `webhook-handler/handlers/automation.py` | NEW | Automation endpoint handler |
| `webhook-handler/main.py` | MODIFIED | Added `/webhook/automation` endpoint |
| `webhook-handler/config.py` | MODIFIED | Added `automation_pipe_model` |
| `webhook-handler/clients/openwebui.py` | MODIFIED | Timeout 60s → 120s |
| `docker-compose.unified.yml` | MODIFIED | Added LINEAR/NOTION env vars |

---

## Rollback

If something goes wrong:

```bash
# Revert to the previous working commit
git checkout main
docker compose -f docker-compose.unified.yml down
docker compose -f docker-compose.unified.yml up -d --build
```

The pipe function can be disabled in Open WebUI Admin → Functions without restarting any containers.

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Pipe function returns 401 | Wrong OPENWEBUI_API_KEY in Valves | Update Valve with correct live admin API key |
| Automation endpoint times out | Pipe function takes too long | Check AI_MODEL availability; timeout is 120s |
| n8n workflows not found | N8N_API_KEY not set | Complete Step 5 and restart webhook-handler |
| Linear/Notion tools not appearing | Missing env vars | Verify LINEAR_API_KEY and NOTION_API_KEY in .env, rebuild mcp-proxy |
| MCP proxy 403 on tool call | Tenant not authorized | Check group_tenant_mapping in database |
