# n8n Unification Design — Fix Split-Brain

**Date:** 2026-02-18
**Status:** Approved
**Scope:** Unify webhook-handler and MCP tools on a single hosted n8n instance

## Context

After migrating MCP tools to Lukas's hosted n8n (`n8n.srv1041674.hstgr.cloud`), we have a split-brain problem:

- **MCP tools** (mcp-n8n container) → hosted n8n (0 workflows)
- **Webhook-handler** (PR review, push events) → local n8n container (`http://n8n:5678`, has 2 workflows)

Lukas noticed the split and asked: *"Is this using webhook or automation?"* The answer is both — but on different n8n instances, which is confusing.

### What's Working Today

| Feature | Trigger | n8n Instance | Status |
|---------|---------|-------------|--------|
| PR Review Automation | GitHub webhook (auto) | Local n8n | Working — PR #10 has AI review comments |
| Push Event Processing | GitHub webhook (auto) | Local n8n | Working — logs show analysis |
| MCP Workflow Creation | Chat prompt (manual) | Hosted n8n | Working — 0 workflows on empty instance |
| Hourly n8n Check | Scheduler (cron) | N/A | Failing — "N8N_API_KEY not set" in webhook-handler |

## Architecture

### Before (Split-Brain)
```
webhook-handler ──► local n8n (http://n8n:5678)       ← has PR review + push workflows
mcp-n8n         ──► hosted n8n (n8n.srv1041674...)     ← empty
```

### After (Unified)
```
webhook-handler ──► hosted n8n (n8n.srv1041674...)     ← all workflows here
mcp-n8n         ──► hosted n8n (n8n.srv1041674...)     ← same instance
local n8n       ──► STOPPED (kept in compose for dev)
```

## Changes

### docker-compose.unified.yml

**webhook-handler service:**
- `N8N_URL=http://n8n:5678` → `N8N_URL=${N8N_API_URL:-https://n8n.srv1041674.hstgr.cloud}`
- Ensure `N8N_API_KEY=${N8N_API_KEY:-}` is passed through

### Hosted n8n

- Import `n8n-workflows/pr-review-automation.json`
- Import `n8n-workflows/github-push-processor.json`
- Set environment variables on hosted n8n: `GITHUB_TOKEN`, `OPENWEBUI_API_KEY`
  - Alternative: Hardcode tokens in workflow JSON if hosted n8n doesn't support env vars
- Activate both workflows

### Live Server

- Stop local n8n: `docker stop n8n`
- SCP updated docker-compose, rebuild webhook-handler
- Verify webhook-handler logs show hosted n8n URL

## Data Flow (After)

```
GitHub PR opened
  → webhook fires to ai-ui.coolestdomain.win/webhook/github
  → Caddy → webhook-handler (validates HMAC)
  → webhook-handler forwards to hosted n8n /webhook/pr-review
  → n8n fetches PR diff from GitHub API
  → n8n sends diff to Open WebUI (gpt-5) for review
  → n8n posts review comment on GitHub PR
```

Open WebUI user asks "create an n8n workflow":
  → mcp-proxy → mcp-n8n → hosted n8n API
  → Workflow created on same instance as PR review

## Testing

1. Import workflows to hosted n8n
2. Deploy updated webhook-handler
3. Push a commit to trigger PR sync event
4. Verify AI review comment appears on GitHub
5. Verify hosted n8n execution history shows workflow ran
6. Verify Open WebUI MCP tools see the imported workflows

## Rollback

Change `N8N_URL` back to `http://n8n:5678`, restart webhook-handler, start local n8n.

## Out of Scope (Future)

- Slack/Discord slash mention triggers
- More workflow templates (end-of-day report, Jira→Slack)
- Workflow marketplace in admin portal
- Removing local n8n from docker-compose entirely
