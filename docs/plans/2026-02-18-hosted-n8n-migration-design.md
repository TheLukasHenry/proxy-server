# Hosted n8n Migration Design

**Date:** 2026-02-18
**Status:** Approved
**Scope:** Connect MCP tools to Lukas's hosted n8n, remove local n8n from live server

## Context

The live server (Hetzner 46.224.193.25) runs a local n8n container for two purposes:
1. MCP tools (mcp-n8n wraps n8n-mcp via mcpo) - lets AIUI build workflows from chat
2. PR review automation (webhook-handler forwards GitHub events to n8n)

Lukas has a hosted n8n at `n8n.srv1041674.hstgr.cloud`. We're migrating MCP tools to use it.

## Architecture

### Before
```
Open WebUI -> mcp-proxy -> mcp-n8n:8000 -> n8n:5678 (local container)
```

### After
```
Open WebUI -> mcp-proxy -> mcp-n8n:8000 -> n8n.srv1041674.hstgr.cloud (hosted)
```

The mcp-n8n container stays (it wraps the n8n-mcp npm tool with mcpo). Only its target changes.

## Changes

### docker-compose.unified.yml

mcp-n8n service:
- `N8N_API_URL`: `http://n8n:5678` -> `${N8N_API_URL:-https://n8n.srv1041674.hstgr.cloud}`
- Remove `depends_on: n8n`

### Server .env (Hetzner)

```bash
N8N_API_KEY=<hosted-n8n-api-key>
N8N_API_URL=https://n8n.srv1041674.hstgr.cloud
```

### Local .env

Same changes for local dev consistency.

## What stays the same

- mcp-n8n container (still wraps n8n-mcp with mcpo on port 8000)
- mcp-proxy routing (/n8n -> mcp-n8n:8000)
- Open WebUI MCP tool connection
- webhook-handler PR automation (stays on local n8n until separate migration)

## Deployment

1. Update local files (docker-compose, .env)
2. SCP docker-compose to Hetzner, update server .env
3. Rebuild mcp-n8n + restart mcp-proxy
4. Test: ask AIUI to list n8n workflows
5. Test: ask AIUI to create a simple workflow, verify on hosted n8n
6. Commit and create PR

## Out of scope (future)

- Migrating PR review automation workflow to hosted n8n
- Removing local n8n container from docker-compose entirely
- Slash mention trigger from Discord/Slack (next feature per standup)
