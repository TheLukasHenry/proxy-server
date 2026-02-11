# Design: Local Testing, n8n Integration & Multi-Tenancy Verification

**Date:** 2026-02-11
**Status:** Draft
**Author:** Jacinto (with Claude)

## Problem

Phase 3C (Webhook Automation Pipe) is deployed on live with MCP tool support. Three things remain:

1. n8n integration is implemented locally but not tested or deployed
2. Lukas provided Linear and Notion API keys to test multi-tenancy
3. Need a demo-ready flow showing AI reasoning + MCP tools + n8n workflows + tenant isolation

## Architecture Overview

```
User/Webhook → POST /webhook/automation
  → webhook-handler wraps payload
    → Open WebUI routes to Pipe Function (webhook_automation.webhook-automation)
      → Phase 1: Fetch MCP tools + n8n workflows
      → Phase 2: LLM plans actions (mcp/n8n)
      → Phase 3: Execute tools & workflows
      → Phase 4: LLM summarizes results
    → Response returned
```

Multi-tenancy layer:
```
User → Entra ID groups → group_tenant_mapping → tenant_server_keys
  → MCP Proxy filters tools by user's group membership
  → Each tenant can have different API keys for the same server
```

## Workstream 1: Local n8n Testing

### Approach

Run full stack locally via `docker-compose.unified.yml`. Create a hello-world n8n workflow, then test the automation pipe end-to-end.

### Steps

1. Add n8n API key to `.env` (n8n generates one on first admin login)
2. Start stack: `docker compose -f docker-compose.unified.yml up -d`
3. Access n8n at `localhost:5678`, create hello-world webhook workflow
4. Update pipe function on Open WebUI with n8n-integrated version
5. Test: `POST /webhook/automation` with instructions to trigger n8n

### Hello World Workflow (for Jonah)

Three nodes:
- **Webhook** node: POST trigger at path `/hello-world`
- **Set** node: `{"message": "Hello from n8n!", "workflow": "hello-world", "timestamp": "{{$now}}"}`
- **Respond to Webhook** node: Returns JSON

### Validation Criteria

- Pipe function lists n8n workflows in Phase 1
- LLM correctly plans an n8n action when asked to "trigger the hello world workflow"
- n8n workflow executes and returns response
- Response appears in final summary

## Workstream 2: Multi-Tenancy with Linear & Notion

### Approach

Use Lukas's API keys as Tenant A (MCP-Admin group). Create "Tenant B" with different group mapping in the database to prove isolation.

### API Keys

| Service | Key | Tenant |
|---------|-----|--------|
| Linear | `${LINEAR_API_KEY}` | A (MCP-Admin) |
| Notion | `${NOTION_API_KEY}` | A (MCP-Admin) |
| Linear | (create new or use env fallback) | B (Test-Tenant) |
| Notion | (create new or use env fallback) | B (Test-Tenant) |

### Database Setup

```sql
-- Tenant A: MCP-Admin gets Linear + Notion
INSERT INTO group_tenant_mapping (group_id, tenant_id)
SELECT g.id, t.id FROM groups g, tenants t
WHERE g.name = 'MCP-Admin' AND t.server_id IN ('linear', 'notion');

-- Tenant B: Test group with limited or no access
INSERT INTO groups (name, description) VALUES ('Test-Tenant', 'Multi-tenancy test group');
-- No Linear/Notion mapping → proves isolation
```

### Validation Criteria

- User in MCP-Admin group sees Linear + Notion tools via MCP Proxy
- User in Test-Tenant group does NOT see Linear + Notion tools
- API keys are loaded from `tenant_server_keys` table, not just `.env`
- Pipe function only offers tools the current user has access to

## Workstream 3: Demo Flow

### Scenario: "GitHub Issue Triage"

1. GitHub webhook fires with new issue payload
2. Automation pipe receives it with instructions: "Analyze this issue, check Linear for related tasks, and notify the team via n8n"
3. LLM plans 3 actions:
   - `mcp: github/get_repository` — Get repo context
   - `mcp: linear/list_issues` — Search for related Linear tasks
   - `n8n: notify-team` — Trigger notification workflow
4. All execute, LLM produces summary
5. Response shows AI reasoning + real tool data + workflow confirmation

### Simpler Demo (for initial testing)

```bash
curl -X POST http://localhost:8086/webhook/automation \
  -H "Content-Type: application/json" \
  -d '{"event":"test","message":"Hello from local testing"}' \
  -G --data-urlencode "source=manual" \
  --data-urlencode "instructions=List all available MCP tools and n8n workflows, then trigger the hello-world workflow"
```

## Risks

| Risk | Mitigation |
|------|------------|
| n8n API key not configured | Pipe gracefully skips n8n if no workflows found |
| Pipe function calls itself (recursion) | `AI_MODEL` valve set to real model, never pipe name |
| Linear/Notion rate limits | httpx timeout + error handling in pipe |
| Docker networking differs local vs server | Use service names (n8n:5678) not localhost |
| Webhook path extraction from n8n nodes | Regex fallback + manual path support |

## Decision Log

- **n8n testing:** Full Docker Compose locally (not mocks)
- **Multi-tenancy:** Database-backed tenant isolation (not just .env switching)
- **Demo:** Start with hello-world, build up to cross-service scenario
