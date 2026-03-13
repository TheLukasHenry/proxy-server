# Design: Tasks #7-10 + Local-to-Production Readiness

**Date:** 2026-02-17
**Context:** Lukas meeting feedback — finish webhook, clarify api-gateway, write docs, explore automations
**Goal:** Complete all 4 tasks AND harden the codebase so local development works identically on Hetzner VPS

---

## Task #7: n8n Webhook Route in Caddy

### Problem
n8n workflows need to be triggerable via external URLs (e.g., GitHub webhook settings). Currently the `WEBHOOK_URL` in docker-compose is hardcoded to `https://ai-ui.coolestdomain.win/n8n/`, but there's no Caddy route to actually proxy `/n8n/*` to the n8n service.

### Solution
Add `/n8n/*` route in Caddyfile that strips the prefix and proxies to `n8n:5678`. Parameterize the `WEBHOOK_URL` via `.env`.

### Changes
1. **Caddyfile** — Add before the catch-all:
   ```
   handle /n8n/* {
       uri strip_prefix /n8n
       reverse_proxy n8n:5678
   }
   ```
2. **docker-compose.unified.yml** — Parameterize:
   ```yaml
   - WEBHOOK_URL=${N8N_WEBHOOK_URL:-https://ai-ui.coolestdomain.win/n8n/}
   ```
3. **.env.example** / **.env.hetzner.example** — Add `N8N_WEBHOOK_URL`

### Flow
```
External POST https://ai-ui.coolestdomain.win/n8n/webhook/github-push
  -> Caddy strips /n8n prefix
  -> n8n:5678/webhook/github-push
  -> n8n workflow executes
  -> response returned
```

---

## Task #8: Clarify API Gateway Folder

### Problem
Lukas asked "are we using Speakeasy instead?" — they are NOT the same thing:
- **API Gateway** (`api-gateway/`) = Auth layer: JWT validation, rate limiting, user group lookup, header injection. Caddy routes nearly ALL traffic through it. **CRITICAL INFRASTRUCTURE.**
- **Speakeasy** = Meta-tools pattern inside `mcp-proxy/` that reduces 200+ tools to 3 for LLM token savings.

### Solution
Create `api-gateway/README.md` explaining its role. Do NOT rename or delete.

### README Contents
- What it does (4 responsibilities)
- Request flow diagram
- How it differs from Speakeasy
- Configuration env vars
- Health check endpoints

---

## Task #9: Architecture Documentation

### Problem
Lukas wants documentation explaining "how to use the API gateway with Caddy and with the n8n workflow."

### Solution
Write `docs/architecture-guide.md` — comprehensive but concise.

### Sections
1. **System Overview** — ASCII diagram of full stack
2. **Caddy** — Route table, TLS, static assets bypass
3. **API Gateway** — JWT, rate limiting, header injection, backend routing
4. **MCP Proxy** — Server tiers (HTTP, MCP_HTTP, SSE, STDIO, LOCAL), multi-tenancy, Speakeasy
5. **Webhook Handler + n8n** — Event flows, signature verification, workflow triggering
6. **Admin Portal** — Access control, management API
7. **Security Layers** — TLS, JWT, rate limits, HMAC, group-based access
8. **Local vs Production** — What changes between environments

---

## Task #10: Automation Rabbit Holes

### Problem
Lukas wants research on next automation features to explore.

### Solution
Write `docs/plans/2026-02-17-automation-rabbit-holes.md` with researched options.

### Topics
1. **n8n MCP Server** — Create/manage n8n workflows from Claude Code or chat UI
2. **More n8n workflow templates** — Jira→Slack, scheduled reports, PR→SonarQube
3. **Microsoft Teams webhook** (Phase 2C from roadmap)
4. **Discord webhook** (Phase 3D from roadmap)
5. **Two-way Slack** — Slash commands, interactive buttons
6. **Workflow marketplace** — Admin portal shows/manages n8n workflows

---

## Local-to-Production Hardening

### Critical Issues Found

| Severity | Issue | Fix |
|----------|-------|-----|
| CRITICAL | `WEBHOOK_URL` hardcoded in docker-compose | Parameterize via `.env` |
| HIGH | Scripts use `localhost:XXXX` URLs | Add `BASE_URL` env var to key scripts |
| MEDIUM | `traefik/` folder unused (replaced by Caddy) | Move to `archive/` |
| MEDIUM | `mcp_proxy_bridge_k8s.py` is legacy | Move to `archive/` |
| MEDIUM | `docker-compose.local-test.yml` missing services | Move to `archive/` |
| LOW | Caddyfile HTTPS block commented out | Parameterize with domain variable |
| LOW | `.env.hetzner.example` missing new vars | Add `N8N_WEBHOOK_URL`, `MCP_NOTION_URL` |

### Files to Archive
- `traefik/` → `archive/traefik/`
- `open-webui-functions/mcp_proxy_bridge_k8s.py` → `archive/`
- `docker-compose.local-test.yml` → `archive/`

### Scripts to Parameterize (add `BASE_URL`)
- `scripts/run-full-demo.ps1`
- `scripts/verify-lukas-requirements.ps1`
- `scripts/deploy-n8n-github-workflow.ps1`
- `scripts/start-local-demo.ps1`
- `scripts/start-local-demo.sh`
- `scripts/seed_mcp_servers.py`

---

## Implementation Order

1. Task #7 (n8n route) — 3 file changes, quick
2. Local-to-production hardening — parameterize + archive
3. Task #8 (api-gateway README) — 1 new file
4. Task #9 (architecture docs) — 1 new file, comprehensive
5. Task #10 (rabbit holes research) — 1 new file, research doc
