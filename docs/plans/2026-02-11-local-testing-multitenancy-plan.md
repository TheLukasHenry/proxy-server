# Local Testing, n8n Integration & Multi-Tenancy Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Verify n8n integration locally, set up multi-tenancy with Linear/Notion API keys, and prepare a demo-ready flow for Lukas.

**Architecture:** The webhook automation pipe function (running inside Open WebUI) combines AI reasoning with MCP tool execution and n8n workflow triggering. Multi-tenancy is enforced via database-backed group-to-tenant mappings in the `mcp_proxy` schema. n8n runs as a Docker service triggered via webhook URLs.

**Tech Stack:** Docker Compose, FastAPI, Open WebUI Pipe Functions, PostgreSQL, n8n, httpx

---

### Task 1: Add Missing Environment Variables to .env

**Files:**
- Modify: `.env` (lines 41-43 and end of file)

**Step 1: Add Linear API key to .env**

Add after line 42 (`NOTION_API_KEY=`):

```env
NOTION_API_KEY=<your-notion-api-key>
```

Replace the empty `NOTION_API_KEY=` line with the value above.

And add Linear:

```env
LINEAR_API_KEY=<your-linear-api-key>
```

**Step 2: Add n8n environment variables**

Add at the end of `.env`:

```env
# =============================================================================
# N8N
# =============================================================================
N8N_USER=admin
N8N_PASSWORD=admin123
# N8N_API_KEY will be set after first login (n8n generates it in Settings > API)
N8N_API_KEY=
```

**Step 3: Verify .env has all required vars**

Run: `grep -E "^(LINEAR_API_KEY|NOTION_API_KEY|N8N_USER|N8N_PASSWORD|N8N_API_KEY)" .env`

Expected: All 5 variables present with values (except N8N_API_KEY which starts empty).

---

### Task 2: Add Linear/Notion API Keys to docker-compose.unified.yml

**Files:**
- Modify: `docker-compose.unified.yml` (mcp-proxy service, around line 174)

**Step 1: Add LINEAR_API_KEY and NOTION_API_KEY to mcp-proxy environment**

Add after `SONARQUBE_URL` line (around line 179) in the mcp-proxy service:

```yaml
      - LINEAR_API_KEY=${LINEAR_API_KEY:-}
      - NOTION_API_KEY=${NOTION_API_KEY:-}
```

**Step 2: Verify the docker-compose change**

Run: `grep -A2 "LINEAR_API_KEY\|NOTION_API_KEY" docker-compose.unified.yml`

Expected: Both variables appear in the mcp-proxy service environment section.

**Step 3: Commit**

```bash
git add .env docker-compose.unified.yml
git commit -m "config: add Linear, Notion, and n8n env vars for local testing"
```

---

### Task 3: Start Docker Stack Locally

**Step 1: Build and start all services**

Run: `docker compose -f docker-compose.unified.yml up -d --build`

This starts: postgres, redis, open-webui, mcp-proxy, webhook-handler, n8n, api-gateway, caddy, and all MCP server containers.

**Step 2: Verify all services are healthy**

Run: `docker compose -f docker-compose.unified.yml ps`

Expected: All containers show "Up" or "healthy" status.

**Step 3: Verify Linear and Notion are enabled in mcp-proxy**

Run: `docker logs mcp-proxy 2>&1 | grep -i "linear\|notion"`

Expected: Log lines showing Linear and Notion servers are enabled (since API keys are now set).

**Step 4: Verify n8n is accessible**

Run: `curl -s http://localhost:5678 | head -20`

Expected: n8n web UI HTML response (may redirect to setup page on first run).

---

### Task 4: Configure n8n and Get API Key

**Step 1: Access n8n UI**

Open browser: `http://localhost:5678`

First-time setup: Create admin account with email/password. The N8N_BASIC_AUTH credentials from .env protect the UI.

**Step 2: Generate n8n API key**

In n8n UI:
1. Go to Settings (gear icon, bottom left)
2. Click "API" section
3. Click "Create API Key"
4. Copy the generated key

**Step 3: Update .env with n8n API key**

Replace the empty `N8N_API_KEY=` with the generated key:

```env
N8N_API_KEY=<paste-key-here>
```

**Step 4: Restart webhook-handler to pick up new key**

Run: `docker compose -f docker-compose.unified.yml restart webhook-handler`

**Step 5: Verify webhook-handler sees the n8n key**

Run: `docker logs webhook-handler 2>&1 | grep "n8n"`

Expected: `n8n URL: http://n8n:5678` (no error about missing key).

---

### Task 5: Create n8n Hello World Workflow

**Step 1: Create workflow in n8n UI**

In n8n UI at `http://localhost:5678`:

1. Click "Add Workflow"
2. Name it: "Hello World"
3. Add node: **Webhook** (trigger)
   - HTTP Method: POST
   - Path: `hello-world`
   - Response Mode: "Last Node"
4. Add node: **Set** (connected to Webhook)
   - Set fields:
     - `message` = `Hello from n8n!`
     - `workflow` = `hello-world`
     - `timestamp` = `{{ $now.toISO() }}`
     - `source` = `{{ $json.source || "unknown" }}`
5. Add node: **Respond to Webhook** (connected to Set)
   - Response body: From previous node
6. **Activate** the workflow (toggle in top-right)

**Step 2: Test the workflow directly**

Run:
```bash
curl -X POST http://localhost:5678/webhook/hello-world \
  -H "Content-Type: application/json" \
  -d '{"source": "test", "message": "direct test"}'
```

Expected: JSON response with `message: "Hello from n8n!"`, `workflow: "hello-world"`, and a timestamp.

**Step 3: Test via webhook-handler's n8n endpoint**

Run:
```bash
curl -X POST http://localhost:8086/webhook/n8n/hello-world \
  -H "Content-Type: application/json" \
  -d '{"source": "webhook-handler-test"}'
```

Expected: `{"success": true, "result": {...}}` with the n8n response nested inside.

---

### Task 6: Install Pipe Function in Open WebUI

**Step 1: Access Open WebUI admin**

Open browser: `http://localhost:3000`

Log in with admin credentials.

**Step 2: Install the pipe function**

Option A — via UI:
1. Admin Panel -> Workspace -> Functions -> Add Function
2. Set ID: `webhook_automation`
3. Set Name: `Webhook Automation`
4. Paste contents of `open-webui-functions/webhook_pipe.py`
5. Save and Enable

Option B — via API:
```bash
curl -X POST http://localhost:3000/api/v1/functions/create \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENWEBUI_API_KEY" \
  -d '{
    "id": "webhook_automation",
    "name": "Webhook Automation",
    "type": "pipe",
    "content": "<paste webhook_pipe.py contents here>",
    "meta": {
      "description": "AI reasoning + MCP tools + n8n workflows"
    }
  }'
```

**Step 3: Configure Valves**

Set these Valve values (via UI: Functions -> webhook_automation -> gear icon):

| Valve | Value |
|-------|-------|
| OPENWEBUI_API_URL | `http://localhost:8080` |
| OPENWEBUI_API_KEY | (same as OPENWEBUI_API_KEY from .env) |
| AI_MODEL | `gpt-5` |
| MCP_PROXY_URL | `http://mcp-proxy:8000` |
| MCP_USER_EMAIL | `webhook-handler@system` |
| MCP_USER_GROUPS | `MCP-Admin` |
| N8N_URL | `http://n8n:5678` |
| N8N_API_KEY | (same key from Task 4) |
| TIMEOUT_SECONDS | `90` |
| MAX_TOOL_CALLS | `5` |

**Step 4: Verify model registration**

Run:
```bash
curl -s http://localhost:3000/api/models \
  -H "Authorization: Bearer $OPENWEBUI_API_KEY" | python -m json.tool | grep -i "webhook"
```

Expected: Model with ID containing `webhook_automation` or `webhook-automation` appears.

---

### Task 7: Test Automation Pipe — MCP Tools Only

**Step 1: Test listing available tools**

Run:
```bash
curl -X POST http://localhost:8086/webhook/automation \
  -H "Content-Type: application/json" \
  -d '{"event":"test"}' \
  -G --data-urlencode "source=manual" \
  --data-urlencode "instructions=List all available MCP tools. Just list the server names and tool counts."
```

Expected: Response includes a list of MCP servers (github, filesystem, clickup, trello, sonarqube, linear, notion, excel, dashboard) with tool counts.

**Step 2: Test executing an MCP tool**

Run:
```bash
curl -X POST http://localhost:8086/webhook/automation \
  -H "Content-Type: application/json" \
  -d '{"event":"test"}' \
  -G --data-urlencode "source=manual" \
  --data-urlencode "instructions=Use the GitHub MCP tool to get my profile (get_me)"
```

Expected: Response includes GitHub profile data (username, repos, etc).

**Step 3: Test Linear MCP tool**

Run:
```bash
curl -X POST http://localhost:8086/webhook/automation \
  -H "Content-Type: application/json" \
  -d '{"event":"test"}' \
  -G --data-urlencode "source=manual" \
  --data-urlencode "instructions=Use the Linear MCP tool to list my teams or get my profile"
```

Expected: Response includes Linear data (teams, user info). This confirms the Linear API key is working through the MCP proxy.

**Step 4: Test Notion MCP tool**

Run:
```bash
curl -X POST http://localhost:8086/webhook/automation \
  -H "Content-Type: application/json" \
  -d '{"event":"test"}' \
  -G --data-urlencode "source=manual" \
  --data-urlencode "instructions=Use the Notion MCP tool to search or list available pages"
```

Expected: Response includes Notion data. This confirms the Notion API key is working.

---

### Task 8: Test Automation Pipe — n8n Integration

**Step 1: Test listing n8n workflows**

Run:
```bash
curl -X POST http://localhost:8086/webhook/automation \
  -H "Content-Type: application/json" \
  -d '{"event":"test"}' \
  -G --data-urlencode "source=manual" \
  --data-urlencode "instructions=List all available n8n workflows"
```

Expected: Response mentions the "Hello World" workflow (and its webhook path).

**Step 2: Test triggering n8n workflow via automation pipe**

Run:
```bash
curl -X POST http://localhost:8086/webhook/automation \
  -H "Content-Type: application/json" \
  -d '{"event":"n8n-test","message":"Testing n8n via automation pipe"}' \
  -G --data-urlencode "source=manual" \
  --data-urlencode "instructions=Trigger the hello-world n8n workflow with the payload data"
```

Expected: Response includes the n8n workflow result (message: "Hello from n8n!", timestamp, etc).

**Step 3: Test combined MCP + n8n action**

Run:
```bash
curl -X POST http://localhost:8086/webhook/automation \
  -H "Content-Type: application/json" \
  -d '{"event":"combined-test"}' \
  -G --data-urlencode "source=manual" \
  --data-urlencode "instructions=First get my GitHub profile using MCP tools, then trigger the hello-world n8n workflow to notify about the result"
```

Expected: Response includes both GitHub profile data AND n8n workflow result, showing the pipe can orchestrate both MCP tools and n8n workflows in a single request.

---

### Task 9: Set Up Multi-Tenancy Test Data

**Step 1: Create a test group and user in the database**

Run this SQL via docker exec:

```bash
docker exec -i postgres psql -U openwebui -d openwebui << 'SQL'
-- Create test tenant group with limited access (only github, filesystem)
INSERT INTO mcp_proxy.group_tenant_mapping (group_name, tenant_id) VALUES
    ('Test-Tenant', 'github'),
    ('Test-Tenant', 'filesystem')
ON CONFLICT (group_name, tenant_id) DO NOTHING;

-- Create a test user in the Test-Tenant group
INSERT INTO mcp_proxy.user_group_membership (user_email, group_name) VALUES
    ('testuser@company.com', 'Test-Tenant')
ON CONFLICT (user_email, group_name) DO NOTHING;

-- Verify: show all groups and their server mappings
SELECT group_name, array_agg(tenant_id ORDER BY tenant_id) as servers
FROM mcp_proxy.group_tenant_mapping
GROUP BY group_name
ORDER BY group_name;
SQL
```

Expected output:
- `MCP-Admin` has all servers (github, filesystem, linear, notion, clickup, trello, sonarqube, excel-creator, dashboard, etc.)
- `Test-Tenant` has only `github` and `filesystem`

**Step 2: Verify MCP-Admin user sees Linear and Notion tools**

Run:
```bash
curl -s http://localhost:8086/webhook/automation \
  -H "Content-Type: application/json" \
  -d '{"test":"admin-tools"}' \
  -G --data-urlencode "source=admin-test" \
  --data-urlencode "instructions=List all available MCP tools with server names" | python -m json.tool
```

Expected: Linear and Notion tools appear (because webhook-handler uses MCP-Admin group headers).

**Step 3: Verify Test-Tenant user does NOT see Linear/Notion**

Test by calling MCP proxy directly with Test-Tenant headers:

```bash
curl -s http://localhost:8000/tools \
  -H "X-User-Email: testuser@company.com" \
  -H "X-User-Groups: Test-Tenant" | python -m json.tool
```

Expected: Only github and filesystem tools appear. Linear and Notion tools are NOT listed. This proves tenant isolation.

**Step 4: Verify MCP-Admin user DOES see Linear/Notion**

```bash
curl -s http://localhost:8000/tools \
  -H "X-User-Email: admin@example.com" \
  -H "X-User-Groups: MCP-Admin" | python -m json.tool
```

Expected: ALL tools appear, including linear and notion.

---

### Task 10: Test Tenant-Specific API Keys (Data Isolation)

**Step 1: Insert a tenant-specific API key in the database**

This demonstrates that different tenants can use different API keys for the same server:

```bash
docker exec -i postgres psql -U openwebui -d openwebui << 'SQL'
-- Insert a tenant-specific API key for Test-Tenant's github access
-- (Using same key for demo, but in production each tenant would have their own)
INSERT INTO mcp_proxy.tenant_server_keys (tenant_id, server_id, key_name, key_value) VALUES
    ('Test-Tenant', 'github', 'GITHUB_TOKEN', '<your-github-pat>')
ON CONFLICT (tenant_id, server_id, key_name) DO UPDATE SET key_value = EXCLUDED.key_value;

-- Verify
SELECT tenant_id, server_id, key_name, LEFT(key_value, 10) || '...' as key_preview
FROM mcp_proxy.tenant_server_keys;
SQL
```

Expected: Row showing `Test-Tenant | github | GITHUB_TOKEN | ghp_RmL5qM...`

**Step 2: Verify the tenant key lookup works**

Run:
```bash
curl -s "http://localhost:8000/github/get_me" \
  -X POST \
  -H "Content-Type: application/json" \
  -H "X-User-Email: testuser@company.com" \
  -H "X-User-Groups: Test-Tenant" \
  -d '{}' | python -m json.tool
```

Expected: Returns GitHub profile data using the Test-Tenant's API key.

---

### Task 11: Demo Run — Full End-to-End Scenario

**Step 1: Cross-service automation demo**

Run:
```bash
curl -X POST http://localhost:8086/webhook/automation \
  -H "Content-Type: application/json" \
  -d '{
    "event": "issue_created",
    "issue": {
      "title": "Login page not loading",
      "body": "Users report 500 errors on /login since last deploy",
      "labels": ["bug", "critical"]
    }
  }' \
  -G --data-urlencode "source=github" \
  --data-urlencode "instructions=Analyze this issue. Check Linear for related tasks. Then trigger the hello-world n8n workflow to acknowledge the issue."
```

Expected: AI response that:
1. Analyzes the issue payload
2. Calls Linear MCP tool to search for related tasks
3. Triggers hello-world n8n workflow
4. Provides a unified summary of all results

**Step 2: Capture the response for demo**

Save the output to a file for the demo:

```bash
curl -s -X POST http://localhost:8086/webhook/automation \
  -H "Content-Type: application/json" \
  -d '{"event":"demo","message":"Full pipeline test"}' \
  -G --data-urlencode "source=demo" \
  --data-urlencode "instructions=Get my GitHub profile, check Linear for any teams, and trigger the hello-world n8n workflow" \
  | python -m json.tool > docs/plans/demo-output.json
```

---

### Task 12: Commit All Changes and Push

**Step 1: Review changes**

Run: `git status && git diff`

Expected: Modified files: `.env`, `docker-compose.unified.yml`. New files: `docs/plans/*.md`

**Step 2: Commit**

```bash
git add docker-compose.unified.yml docs/plans/
git commit -m "feat: add Linear/Notion env vars and implementation plans for local testing"
```

Note: Do NOT commit `.env` (contains secrets). It should be in `.gitignore`.

**Step 3: Push to ai-ui repo**

```bash
git push origin fix/mcp-network-split
```

---

## Troubleshooting

### n8n workflow listing returns empty
- Check that n8n API key is set in `.env` and webhook-handler was restarted
- Check that the Hello World workflow is **activated** in n8n UI
- Check that the pipe function's `N8N_API_KEY` valve is set

### Linear/Notion tools don't appear
- Check `docker logs mcp-proxy` for `linear` and `notion` enabled messages
- Verify `LINEAR_API_KEY` and `NOTION_API_KEY` are in docker-compose.unified.yml mcp-proxy environment
- Verify the keys are correct by testing directly: `curl -H "Authorization: Bearer lin_api_..." https://mcp.linear.app/mcp`

### Pipe function returns "no response"
- Verify model name: check `/api/models` for exact model ID
- Verify the pipe function is enabled in Open WebUI Functions page
- Check that `AI_MODEL` valve is set to a real model (e.g., `gpt-5`), NOT the pipe's own name

### Multi-tenancy not isolating
- Verify `API_GATEWAY_MODE=true` in mcp-proxy environment
- Check that headers `X-User-Email` and `X-User-Groups` are being sent
- Query the database: `SELECT * FROM mcp_proxy.group_tenant_mapping`

---

## Summary

| Task | What | Time Est |
|------|------|----------|
| 1 | Add API keys to .env | 2 min |
| 2 | Update docker-compose for Linear/Notion | 2 min |
| 3 | Start Docker stack locally | 5 min |
| 4 | Configure n8n and get API key | 5 min |
| 5 | Create Hello World workflow in n8n | 5 min |
| 6 | Install pipe function in Open WebUI | 5 min |
| 7 | Test MCP tools (GitHub, Linear, Notion) | 5 min |
| 8 | Test n8n integration via automation pipe | 5 min |
| 9 | Set up multi-tenancy test data | 5 min |
| 10 | Test tenant-specific API keys | 3 min |
| 11 | Run full demo scenario | 5 min |
| 12 | Commit and push | 2 min |
