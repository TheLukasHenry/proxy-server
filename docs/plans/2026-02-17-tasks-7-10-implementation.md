# Tasks #7-10 + Local-to-Production Hardening — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete Lukas's 4 meeting action items (n8n webhook route, api-gateway clarity, architecture docs, automation research) and harden the codebase for Hetzner VPS deployment.

**Architecture:** Add Caddy route for n8n, parameterize hardcoded URLs, archive unused files, write comprehensive docs.

**Tech Stack:** Caddy, Docker Compose, PowerShell/Bash scripts, Markdown documentation

---

## Task 1: Add n8n Route to Caddyfile

**Files:**
- Modify: `Caddyfile:97-104` (add new route block after webhook handler)

**Step 1: Add `/n8n/*` route block**

In `Caddyfile`, insert a new block between the webhook handler section (line 104) and the static assets section (line 106):

```caddy
	# ---------------------------------------------------------------------------
	# n8n Workflow Engine (external webhook triggers)
	# ---------------------------------------------------------------------------
	handle /n8n/* {
		uri strip_prefix /n8n
		reverse_proxy n8n:5678
	}
```

This goes AFTER the `/webhook/*` block and BEFORE the `/_app/*` static assets block.

**Step 2: Verify Caddyfile syntax**

Run: `docker run --rm -v "$(pwd)/Caddyfile:/etc/caddy/Caddyfile:ro" caddy:2-alpine caddy fmt /etc/caddy/Caddyfile`

Expected: No errors. File contents printed to stdout.

**Step 3: Commit**

```bash
git add Caddyfile
git commit -m "feat: add /n8n/* route in Caddy for external workflow triggers"
```

---

## Task 2: Parameterize n8n WEBHOOK_URL in Docker Compose

**Files:**
- Modify: `docker-compose.unified.yml:141`
- Modify: `.env.example` (append)
- Modify: `.env.hetzner.example` (append)

**Step 1: Replace hardcoded WEBHOOK_URL**

In `docker-compose.unified.yml`, change line 141 from:

```yaml
      - WEBHOOK_URL=https://ai-ui.coolestdomain.win/n8n/
```

To:

```yaml
      - WEBHOOK_URL=${N8N_WEBHOOK_URL:-https://ai-ui.coolestdomain.win/n8n/}
```

**Step 2: Add N8N_WEBHOOK_URL to .env.example**

Append to `.env.example` after the `AI_MODEL` line (line 163):

```
# =============================================================================
# n8n Workflow Engine
# =============================================================================

# External webhook URL for n8n (used for n8n to generate correct webhook URLs)
N8N_WEBHOOK_URL=https://ai-ui.coolestdomain.win/n8n/

# n8n basic auth credentials
N8N_USER=admin
N8N_PASSWORD=your-n8n-password
```

**Step 3: Add variables to .env.hetzner.example**

Append to `.env.hetzner.example` after the `LINEAR_API_KEY` line (line 114):

```

# =============================================================================
# N8N WORKFLOW ENGINE
# =============================================================================
N8N_WEBHOOK_URL=https://ai-ui.coolestdomain.win/n8n/
N8N_USER=admin
N8N_PASSWORD=

# =============================================================================
# NOTION MCP SERVER
# =============================================================================
NOTION_API_KEY=
```

**Step 4: Commit**

```bash
git add docker-compose.unified.yml .env.example .env.hetzner.example
git commit -m "fix: parameterize n8n WEBHOOK_URL via .env instead of hardcoding"
```

---

## Task 3: Add BASE_URL to Key Scripts

**Files:**
- Modify: `scripts/run-full-demo.ps1:24-27`
- Modify: `scripts/verify-lukas-requirements.ps1:14` (and all localhost refs)
- Modify: `scripts/deploy-n8n-github-workflow.ps1:12`
- Modify: `scripts/start-local-demo.ps1` (add BASE_URL param)
- Modify: `scripts/start-local-demo.sh` (add BASE_URL var)

**Step 1: Update run-full-demo.ps1**

Replace lines 24-27:

```powershell
$WEBHOOK_HANDLER = "http://localhost:8086"
$OPEN_WEBUI      = "http://localhost:3000"
$N8N             = "http://localhost:5678"
$MCP_PROXY       = "http://localhost:8000"
```

With:

```powershell
# Base URLs — override with env vars for production (e.g., on Hetzner VPS)
$WEBHOOK_HANDLER = if ($env:WEBHOOK_HANDLER_URL) { $env:WEBHOOK_HANDLER_URL } else { "http://localhost:8086" }
$OPEN_WEBUI      = if ($env:OPEN_WEBUI_URL)      { $env:OPEN_WEBUI_URL }      else { "http://localhost:3000" }
$N8N             = if ($env:N8N_URL)              { $env:N8N_URL }              else { "http://localhost:5678" }
$MCP_PROXY       = if ($env:MCP_PROXY_URL)        { $env:MCP_PROXY_URL }        else { "http://localhost:8000" }
```

**Step 2: Update verify-lukas-requirements.ps1**

Add at the top (after line 1):

```powershell
# Base URLs — override for production
$BASE = if ($env:BASE_URL) { $env:BASE_URL.TrimEnd('/') } else { "http://localhost" }
$WEBHOOK_HANDLER = "${BASE}:8086"
$MCP_PROXY = "${BASE}:8000"
```

Then replace all hardcoded `http://localhost:8086` with `$WEBHOOK_HANDLER` and `http://localhost:8000` with `$MCP_PROXY` throughout the file.

**Step 3: Update deploy-n8n-github-workflow.ps1**

Line 12 already accepts `-N8nUrl` as a parameter with default `http://localhost:5678`. Change the default to read from env:

```powershell
[string]$N8nUrl = $(if ($env:N8N_URL) { $env:N8N_URL } else { "http://localhost:5678" }),
```

**Step 4: Update start-local-demo.sh**

Add after line 29 (after color definitions):

```bash
# Base URLs — override for production
BASE_URL="${BASE_URL:-http://localhost}"
WEBHOOK_HANDLER="${WEBHOOK_HANDLER_URL:-${BASE_URL}:8086}"
MCP_PROXY="${MCP_PROXY_URL:-${BASE_URL}:8000}"
OPEN_WEBUI="${OPEN_WEBUI_URL:-${BASE_URL}:3000}"
```

Then replace hardcoded `http://localhost:XXXX` references with these variables.

**Step 5: Commit**

```bash
git add scripts/
git commit -m "fix: parameterize localhost URLs in scripts for production portability"
```

---

## Task 4: Archive Unused Files

**Files:**
- Move: `traefik/` → `archive/traefik/`
- Move: `open-webui-functions/mcp_proxy_bridge_k8s.py` → `archive/`
- Move: `docker-compose.local-test.yml` → `archive/`

**Step 1: Move files**

```bash
mkdir -p archive/traefik
mv traefik/* archive/traefik/
rmdir traefik
mv open-webui-functions/mcp_proxy_bridge_k8s.py archive/
mv docker-compose.local-test.yml archive/
```

**Step 2: Verify nothing references these files**

Run: `grep -r "traefik" docker-compose*.yml Caddyfile` — should return nothing.
Run: `grep -r "local-test" *.md scripts/` — note any docs that reference it and update them.
Run: `grep -r "mcp_proxy_bridge_k8s" .` — should return nothing active.

**Step 3: Commit**

```bash
git add -A
git commit -m "chore: archive unused traefik config, k8s bridge, and local-test compose"
```

---

## Task 5: Create api-gateway/README.md

**Files:**
- Create: `api-gateway/README.md`

**Step 1: Write README**

```markdown
# API Gateway

Centralized authentication, rate limiting, and request routing layer.

## What It Does

1. **JWT Validation** — Validates Open WebUI session tokens from `Authorization: Bearer` header or `token` cookie
2. **User Group Lookup** — Queries PostgreSQL (`mcp_proxy.user_group_membership`) for group-based access control
3. **Rate Limiting** — Per-user (100/min) and per-IP (1000/min) rate limiting
4. **Header Injection** — Adds `X-User-Email`, `X-User-Groups`, `X-User-Admin`, `X-Gateway-Validated` headers for downstream services

## Request Flow

```
Browser/API Client
       |
       v
    Caddy (:80/:443)
       |
       v
  API Gateway (:8080)      <-- THIS SERVICE
    |  Validates JWT
    |  Looks up user groups
    |  Applies rate limits
    |  Injects X-User-* headers
    |
    +---> MCP Proxy (:8000)     [/mcp/*, /admin/*, /mcp-admin]
    +---> Open WebUI (:8080)    [everything else]
```

## NOT the Same as Speakeasy

- **API Gateway** = Auth + routing layer (sits between Caddy and backends)
- **Speakeasy** = Meta-tools pattern inside MCP Proxy that reduces 200+ tools to 3 for LLM token savings

These operate at completely different layers of the stack.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `WEBUI_SECRET_KEY` | (required) | JWT signing key (same as Open WebUI) |
| `DATABASE_URL` | (required) | PostgreSQL connection string |
| `RATE_LIMIT_PER_MINUTE` | `100` | Rate limit per authenticated user |
| `RATE_LIMIT_PER_IP` | `1000` | Rate limit per IP (unauthenticated) |
| `RATE_LIMIT_ENABLED` | `true` | Enable/disable rate limiting |
| `ENABLE_API_ANALYTICS` | `true` | Log requests to `mcp_proxy.api_analytics` |
| `MCP_PROXY_URL` | `http://mcp-proxy:8000` | Backend MCP Proxy URL |
| `OPEN_WEBUI_URL` | `http://open-webui:8080` | Backend Open WebUI URL |
| `DEBUG` | `false` | Verbose logging |

## Health Check

```
GET /gateway/health  — Gateway health + DB status
GET /gateway/stats   — Rate limiter statistics
```

## Backend Routing

| Path Pattern | Backend | Description |
|-------------|---------|-------------|
| `/mcp/*` | MCP Proxy | Tool endpoints (strips `/mcp` prefix) |
| `/mcp-admin` | MCP Proxy `/portal` | Admin Portal UI |
| `/mcp-admin/api/*` | MCP Proxy `/admin/*` | Admin API |
| `/admin/users`, `/admin/groups`, `/admin/servers` | MCP Proxy | Management API |
| `/*` (default) | Open WebUI | Chat interface + WebUI admin |
```

**Step 2: Commit**

```bash
git add api-gateway/README.md
git commit -m "docs: add api-gateway README clarifying its role vs Speakeasy"
```

---

## Task 6: Write Architecture Guide

**Files:**
- Create: `docs/architecture-guide.md`

**Step 1: Write the architecture doc**

This is the largest task. The doc should cover all 8 sections from the design:

1. **System Overview** with ASCII diagram showing:
   ```
   Browser -> Caddy -> API Gateway -> MCP Proxy / Open WebUI
                  \-> Webhook Handler -> n8n / MCP Proxy / Open WebUI
   ```

2. **Caddy** — Full route table from Caddyfile (health, gateway, mcp, admin, webhooks, n8n, static, ws, default)

3. **API Gateway** — JWT flow, group lookup SQL, rate limiting, header injection, backend routing table

4. **MCP Proxy** — Server tiers (HTTP, MCP_HTTP, SSE, STDIO, LOCAL), tool cache, OpenAPI generation, multi-tenancy, Speakeasy meta-tools

5. **Webhook Handler + n8n** — All endpoints (`/webhook/github`, `/webhook/slack`, `/webhook/n8n/*`, `/webhook/mcp/*`, `/webhook/automation`, `/webhook/generic`), signature verification, n8n workflow triggering, scheduler jobs

6. **Admin Portal** — Access at `/mcp-admin`, admin-only, management API

7. **Security Layers** — TLS (Caddy), JWT (Gateway), rate limits (Gateway), HMAC (Webhook Handler), group-based ACL (MCP Proxy)

8. **Local vs Production** — What changes: Caddyfile HTTPS block, `.env` values, exposed ports, domain config

**Step 2: Commit**

```bash
git add docs/architecture-guide.md
git commit -m "docs: add comprehensive architecture guide (Caddy, Gateway, MCP, n8n)"
```

---

## Task 7: Write Automation Rabbit Holes Research

**Files:**
- Create: `docs/plans/2026-02-17-automation-rabbit-holes.md`

**Step 1: Research and write the doc**

Cover each topic with:
- What it is
- How it would integrate with the current system
- Effort estimate (small/medium/large)
- Value for Lukas

Topics:
1. **n8n MCP Server** — `@nerdondon/n8n-mcp-server` or similar. Would let Claude Code create/manage n8n workflows. Integration: add as a new STDIO or LOCAL server in `tenants.py`. Effort: medium.

2. **More n8n workflow templates** — GitHub PR → SonarQube scan → comment results. Scheduled daily report (Excel + Dashboard). Jira issue → Slack notification. Effort: small per template.

3. **Microsoft Teams webhook** (Phase 2C) — Add Teams handler in webhook-handler, similar to Slack handler. Needs Microsoft Bot Framework or Incoming Webhook connector. Effort: medium.

4. **Discord webhook** (Phase 3D) — Add Discord handler, simpler than Teams (just HTTP POST to webhook URL). Effort: small.

5. **Two-way Slack** — Add slash commands (`/mcp search repos`) and interactive buttons (approve/deny actions). Requires Slack App Manifest update. Effort: large.

6. **Workflow marketplace in Admin Portal** — Admin portal shows available n8n workflows, lets admins enable/disable them, trigger test runs. Effort: large.

**Step 2: Commit**

```bash
git add docs/plans/2026-02-17-automation-rabbit-holes.md
git commit -m "docs: add automation rabbit holes research for Lukas"
```

---

## Summary

| Task | Files Changed | Effort |
|------|--------------|--------|
| 1. n8n Caddy route | `Caddyfile` | 2 min |
| 2. Parameterize WEBHOOK_URL | `docker-compose.unified.yml`, `.env.example`, `.env.hetzner.example` | 5 min |
| 3. BASE_URL in scripts | 5 scripts in `scripts/` | 15 min |
| 4. Archive unused files | Move 3 items to `archive/` | 5 min |
| 5. api-gateway README | `api-gateway/README.md` | 10 min |
| 6. Architecture guide | `docs/architecture-guide.md` | 30 min |
| 7. Rabbit holes research | `docs/plans/2026-02-17-automation-rabbit-holes.md` | 20 min |

Total: ~7 commits, all independent.
