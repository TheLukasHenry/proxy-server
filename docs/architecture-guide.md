# Architecture Guide

**Last Updated:** 2026-02-20

## 1. System Overview

```
                          +------------------+
                          |   Browser / API   |
                          +--------+---------+
                                   |
                                   v
                          +--------+---------+
                          |  Caddy (port 80)  |
                          |  Reverse Proxy     |
                          +---+----+------+---+
                              |    |      |
          +-------------------+    |      +--------------------+
          |                        |                           |
          v                        v                           v
  +-------+--------+    +---------+---------+    +------------+--------+
  | Webhook Handler |    |   API Gateway     |    | Static / WebSocket  |
  |   (port 8086)   |    |   (port 8080)     |    | bypass -> Open WebUI|
  +---+----+--------+    +----+----+----+----+    +-----------+---------+
      |    |                   |    |    |
      |    |                   |    |    +-------------------+
      |    |                   |    |                        |
      v    v                   v    v                        v
  +---+--+ +--+--+    +-------+--+ +-------+------+   +-----+------+
  | n8n  | | MCP |    |MCP Proxy | | Open WebUI   |   |Admin Portal|
  | 5678 | |Proxy|    | (8000)   | | (8080)       |   | (8080)     |
  +------+ +-----+    +----+-----+ +--------------+   +------------+
                            |
              +------+------+------+------+
              |      |      |      |      |
              v      v      v      v      v
           github filesys clickup excel  ...
           (8000) (8001)  (8000)  (8000)
```

### Services and Ports

| Service              | Container Name       | Internal Port | Exposed Port   | Role                                 |
|----------------------|----------------------|---------------|----------------|--------------------------------------|
| Caddy                | `caddy`              | 80, 443       | 80, 443        | Reverse proxy, TLS termination       |
| API Gateway          | `api-gateway`        | 8080          | 8085           | JWT validation, rate limiting        |
| MCP Proxy            | `mcp-proxy`          | 8000          | --             | Multi-tenant tool orchestration      |
| Open WebUI           | `open-webui`         | 8080          | 127.0.0.1:3000 | AI chat interface (v0.8.3)           |
| Admin Portal         | `admin-portal`       | 8080          | --             | User/group management UI             |
| Webhook Handler      | `webhook-handler`    | 8086          | 8086           | External event ingestion             |
| n8n                  | `n8n`                | 5678          | 5678           | Workflow automation engine           |
| PostgreSQL           | `postgres`           | 5432          | --             | Database (pgvector-enabled)          |
| Redis                | `redis`              | 6379          | --             | Sessions and cache                   |
| MCP Filesystem       | `mcp-filesystem`     | 8001          | --             | File access tools (via mcpo)         |
| MCP GitHub           | `mcp-github`         | 8000          | --             | GitHub repo/issue/PR tools           |
| MCP ClickUp          | `mcp-clickup`        | 8000          | --             | ClickUp task management (via mcpo)   |
| MCP Trello           | `mcp-trello`         | 8000          | --             | Trello boards (via mcpo)             |
| MCP SonarQube        | `mcp-sonarqube`      | 8000          | --             | Code quality analysis (via mcpo)     |
| MCP Excel            | `mcp-excel`          | 8000          | --             | Spreadsheet generation               |
| MCP Dashboard        | `mcp-dashboard`      | 8000          | --             | Executive dashboard generation       |
| MCP Notion           | `mcp-notion`         | 8000          | --             | Notion workspace access              |
| MCP n8n              | `mcp-n8n`            | 8000          | --             | n8n workflow management (via mcpo)   |

The stack is a self-hosted AI platform built on Open WebUI (v0.8.3), extended with MCP (Model Context Protocol) tool servers for enterprise integrations. All browser traffic enters through Caddy, which routes authenticated paths through the API Gateway for JWT validation and rate limiting before reaching backend services. The MCP Proxy unifies 30+ tool servers behind a single OpenAPI endpoint with multi-tenant access control, while the Webhook Handler processes external events from GitHub, Slack, and n8n workflows. PostgreSQL (with pgvector) serves as the shared database for Open WebUI, user-group mappings, and API analytics. Redis provides session management and caching.

### Open WebUI v0.8.3 Features

Upgraded from v0.7.2 on 2026-02-20. Key new capabilities:

| Feature | Description |
|---------|-------------|
| **Skills** | Reusable AI instruction sets injected before LLM processing. Teach AI when/how to use MCP tools. Managed at `/workspace/skills`. |
| **Channels** | Persistent topic-based chat rooms (Slack/Discord-like). Support `@model-name` mentions. Managed in sidebar. |
| **Analytics** | Built-in admin dashboard for model usage, token counts, and user activity. At `/admin/analytics`. |
| **Notes** | Personal note-taking feature integrated into the sidebar. |
| **Prompt Version Control** | History, comparison, and rollback for prompts. |

**Active Skills:** PR Security Review, Daily Report Builder, Project Status
**Active Channels:** #general (public), #dev-notifications (public)

---

## 2. Caddy (Reverse Proxy)

### Full Route Table

| Route                       | Target                  | Through Gateway? | Purpose                                    |
|-----------------------------|-------------------------|------------------|--------------------------------------------|
| `/health`                   | Static `200 OK`         | No               | Caddy health check                         |
| `/caddy/health`             | Static `200 Caddy OK`   | No               | Caddy-specific health check                |
| `/gateway/*`                | `api-gateway:8080`      | Direct to GW     | Gateway health + stats endpoints           |
| `/mcp/*`                    | `api-gateway:8080`      | Yes              | MCP tool endpoints (auth required)         |
| `/servers*`                 | `api-gateway:8080`      | Yes              | URI rewritten to `/mcp/servers`            |
| `/meta/*`                   | `api-gateway:8080`      | Yes              | URI rewritten to `/mcp/meta/*`             |
| `/openapi.json`             | `api-gateway:8080`      | Yes              | URI rewritten to `/mcp/openapi.json`       |
| `/mcp-admin`, `/mcp-admin/*`| `api-gateway:8080`      | Yes              | Admin portal (admin-only)                  |
| `/admin/*`                  | `api-gateway:8080`      | Yes              | Admin API routes                           |
| `/portal*`                  | `api-gateway:8080`      | Yes              | Redirects to `/mcp-admin`                  |
| `/webhook/*`                | `webhook-handler:8086`  | No               | External webhooks (GitHub, Slack, n8n)     |
| `/n8n/*`                    | `n8n:5678`              | No               | n8n UI and webhook triggers (prefix stripped) |
| `/_app/*`                   | `open-webui:8080`       | No               | Static assets bypass                       |
| `/static/*`                 | `open-webui:8080`       | No               | Static assets bypass                       |
| `/favicon*`                 | `open-webui:8080`       | No               | Favicon bypass                             |
| `/manifest.json`            | `open-webui:8080`       | No               | PWA manifest bypass                        |
| `/ws/*`                     | `open-webui:8080`       | No               | WebSocket connections                      |
| `/*` (catch-all)            | `api-gateway:8080`      | Yes              | All other routes -> Open WebUI via gateway |

### Gateway vs Bypass

Routes that **bypass the gateway** (go directly to backends):
- Health checks (`/health`, `/caddy/health`)
- Static assets (`/_app/*`, `/static/*`, `/favicon*`, `/manifest.json`) -- avoids unnecessary rate limit consumption
- WebSocket (`/ws/*`) -- long-lived connections incompatible with the gateway's request forwarding
- Webhook Handler (`/webhook/*`) -- uses its own HMAC signature verification
- n8n (`/n8n/*`) -- has its own basic auth

Routes that **go through the gateway** (JWT validated, rate limited, headers injected):
- MCP endpoints (`/mcp/*`, `/servers*`, `/meta/*`, `/openapi.json`)
- Admin portal (`/mcp-admin*`, `/admin/*`, `/portal*`)
- Open WebUI catch-all (`/*`)

---

## 3. API Gateway

**File:** `api-gateway/main.py` (FastAPI on port 8080)

### JWT Validation Flow

```
Request arrives
    |
    +-- Check Authorization: Bearer <token> header
    |       (API / programmatic requests)
    |
    +-- Fallback: Check 'token' cookie
    |       (Browser requests via Open WebUI session)
    |
    v
jwt.decode(token, WEBUI_SECRET_KEY, algorithms=["HS256"])
    |
    +-- Extract email from claims (email or preferred_username)
    |       If neither present, lookup email by user ID from "user" table
    |
    v
Lookup groups from mcp_proxy.user_group_membership
    WHERE user_email = <email>
    |
    v
Check admin status from "user" table
    WHERE email = <email> AND role = 'admin'
```

### Rate Limiting Rules

| Type        | Key Pattern     | Limit (per 60s)           | Config Env Var          |
|-------------|-----------------|---------------------------|-------------------------|
| Per user    | `user:<email>`  | `RATE_LIMIT_PER_MINUTE`   | Default: 100            |
| Per IP      | `ip:<client_ip>`| `RATE_LIMIT_PER_IP`       | Default: 1000           |

- Static assets (`/_app/*`, `/static/*`, `/favicon*`, `/manifest.json`) are **exempt** from rate limiting even if they reach the gateway.
- Rate limiter uses an in-memory sliding window (list of timestamps per key) with a 60-second background cleanup task.
- When a limit is exceeded, the gateway returns `429 Too Many Requests` with a `Retry-After: 60` header.

### Header Injection

The gateway injects these headers on every forwarded request:

| Header               | Value                                      |
|----------------------|--------------------------------------------|
| `X-User-Email`       | User's email or empty string               |
| `X-User-Groups`      | Comma-separated group names or empty string|
| `X-User-Admin`       | `"true"` or `"false"`                      |
| `X-User-Name`        | Local part of email (before `@`)           |
| `X-Gateway-Validated`| `"true"` (always set)                      |

### Backend Routing Table

The gateway's catch-all route determines the backend based on the request path:

| Path Pattern                                       | Backend                | Backend Path Transformation                     |
|----------------------------------------------------|------------------------|--------------------------------------------------|
| `/mcp-admin` or `/mcp-admin/`                      | MCP Proxy (`8000`)     | `/portal`                                        |
| `/mcp-admin/api/*`                                 | MCP Proxy              | `/admin/*` (strip `/mcp-admin`)                  |
| `/mcp-admin/*`                                     | MCP Proxy              | `/portal/*` (strip `/mcp-admin`)                 |
| `/admin/users`, `/admin/groups`, `/admin/servers`, `/admin/endpoints`, `/admin/tenant-keys`, `/admin/analytics` | MCP Proxy | Pass-through |
| `/admin/users/{id}` (not `/admin/users/overview`)  | MCP Proxy              | Pass-through                                     |
| `/admin/groups/*`                                  | MCP Proxy              | Pass-through                                     |
| `/mcp/*`                                           | MCP Proxy              | Strip `/mcp` prefix                              |
| `/portal*`                                         | Redirect `301`         | -> `/mcp-admin`                                  |
| `/servers*`, `/meta*`, `/openapi*`                 | MCP Proxy              | Pass-through                                     |
| Everything else                                    | Open WebUI (`8080`)    | Pass-through                                     |

### API Analytics

When `ENABLE_API_ANALYTICS=true`, the gateway logs every request to `mcp_proxy.api_analytics`:

```
(user_email, method, endpoint, status_code, response_time_ms, user_agent, client_ip)
```

---

## 4. MCP Proxy

**File:** `mcp-proxy/main.py` (FastAPI on port 8000)

### Server Tiers

Defined in `mcp-proxy/tenants.py` as the `ServerTier` enum:

| Tier       | Enum Value  | Protocol                    | Example Servers                        | How It Connects                                  |
|------------|-------------|-----------------------------|----------------------------------------|--------------------------------------------------|
| HTTP       | `http`      | REST / OpenAPI              | HubSpot, Pulumi, GitLab, Sentry       | Direct HTTPS to vendor's remote endpoint         |
| MCP_HTTP   | `mcp_http`  | JSON-RPC + Streamable HTTP  | Linear                                 | JSON-RPC `tools/list` and `tools/call` over HTTP |
| SSE        | `sse`       | Server-Sent Events          | Atlassian (Jira/Confluence), Asana     | SSE connection, often via mcpo proxy             |
| STDIO      | `stdio`     | stdio (stdin/stdout)        | ClickUp, Trello, SonarQube            | mcpo wraps stdio server as HTTP                  |
| LOCAL      | `local`     | HTTP (in-cluster container) | GitHub, Filesystem, Excel, Dashboard, Notion | Direct HTTP to container on Docker network |

**TIER1_SERVERS** (HTTP/MCP_HTTP) connect to external SaaS endpoints -- they auto-enable when their API key env var is set.

**LOCAL_SERVERS** run as containers inside the Docker Compose network and are wrapped with mcpo (a tool that converts stdio/SSE MCP servers to HTTP+OpenAPI).

### Tool Cache and Refresh

On startup (unless `SKIP_CACHE_REFRESH=true`), the proxy fetches tools from all enabled servers:

1. **MCP_HTTP servers** -- calls `tools/list` via JSON-RPC, converts each tool's `inputSchema` to OpenAPI `requestBody` format.
2. **HTTP/SSE/STDIO/LOCAL servers** -- fetches `/openapi.json` from the server, extracts all POST endpoints as tools.
3. Stores results in `TOOLS_CACHE` (dict keyed by `{server_id}_{tool_name}`).
4. Generates pgvector embeddings for semantic search (used by meta-tools).
5. Retry logic: up to `CACHE_REFRESH_RETRIES` (default 3) attempts with `CACHE_REFRESH_DELAY` (default 5s) between retries.
6. Manual refresh available via `POST /refresh`.

### OpenAPI Generation

The proxy generates a dynamic OpenAPI 3.1.0 spec at `GET /openapi.json`:

- Filters tools by the requesting user's group-based access (reads `X-User-Email` and `X-User-Groups` headers).
- In **standard mode**: every cached tool becomes a `POST /{server_id}/{tool_name}` endpoint plus a deprecated `POST /{server_id}_{tool_name}` legacy endpoint.
- In **meta-tools mode** (`META_TOOLS_MODE=true`): only 3 endpoints are advertised (see Speakeasy section below).
- Merges component schemas from all upstream OpenAPI specs.

### Multi-Tenancy: Group-Based Access Control

Access control is stored in PostgreSQL:

| Table                                  | Purpose                             |
|----------------------------------------|-------------------------------------|
| `mcp_proxy.user_group_membership`      | Maps user emails to group names     |
| `mcp_proxy.group_tenant_mapping`       | Maps group names to server/tenant IDs |
| `mcp_proxy.user_tenant_access`         | Direct user-to-server access grants |

Access check priority:
1. **MCP-Admin group** -- grants access to ALL servers (superuser).
2. **Group-based** -- user's groups are resolved to server IDs via `group_tenant_mapping`.
3. **Direct user mapping** -- checked in `user_tenant_access` table.

Tenant-specific API keys (`mcp_proxy.tenant_api_keys`) allow different groups to use different credentials for the same server. Tenant-specific endpoint overrides (`mcp_proxy.tenant_endpoint_overrides`) allow routing a group's requests to a different container (data isolation).

### Speakeasy Meta-Tools

When `META_TOOLS_MODE=true`, the OpenAPI spec exposes only 3 endpoints instead of 200+ individual tools:

| Endpoint                 | Purpose                                               |
|--------------------------|-------------------------------------------------------|
| `POST /meta/search_tools`  | Semantic search across all tools by natural language query. Uses pgvector embeddings with keyword fallback. Returns ranked results with tool names and descriptions. |
| `POST /meta/describe_tools`| Returns full parameter schemas for a list of tool names. Enables lazy loading -- only fetch schemas the LLM needs. |
| `POST /meta/call_tool`     | Executes any tool by its qualified name (e.g., `clickup_create_task`) with provided arguments. Routes to the correct backend based on server tier. |

**Workflow:** `search_tools` -> `describe_tools` -> `call_tool`. This reduces token usage by 96-99% compared to listing all tools in the OpenAPI spec.

### URL Structure

```
GET  /servers                        -- List all servers (filtered by user access)
GET  /{server_id}                    -- List tools for a server
POST /{server_id}/{tool_name}        -- Execute a tool (preferred)
POST /{server_id}_{tool_name}        -- Legacy flat format (deprecated)
```

---

## 5. Webhook Handler + n8n

**File:** `webhook-handler/main.py` (FastAPI on port 8086)

### Endpoints

| Endpoint                                | Method | Purpose                                              |
|-----------------------------------------|--------|------------------------------------------------------|
| `/webhook/github`                       | POST   | GitHub webhook receiver (HMAC-SHA256 verified)       |
| `/webhook/slack`                        | POST   | Slack Events API receiver (@mentions, DMs)           |
| `/webhook/slack/commands`               | POST   | Slack slash commands (`/aiui ask\|workflow\|status`)  |
| `/webhook/discord`                      | POST   | Discord slash commands (Ed25519 verified)             |
| `/webhook/n8n/{workflow_path}`          | POST   | Forward payload to n8n workflow webhook node         |
| `/webhook/mcp/{server_id}/{tool_name}`  | POST   | Execute MCP tool directly via webhook                |
| `/webhook/automation`                   | POST   | AI + MCP + n8n automation pipe (query: `source`, `instructions`) |
| `/webhook/generic`                      | POST   | Generic JSON payload -> AI analysis (query: `prompt`, `model`) |
| `/scheduler/jobs`                       | GET    | List all scheduled APScheduler jobs                  |
| `/scheduler/jobs/{job_id}/trigger`      | POST   | Manually trigger a scheduled job                     |
| `/scheduler/health-report`              | GET    | Run daily health report on demand                    |
| `/scheduler/n8n-check`                  | GET    | Run n8n workflow check on demand                     |

### HMAC Signature Verification

**GitHub:**
- Header: `X-Hub-Signature-256`
- Secret: `GITHUB_WEBHOOK_SECRET` env var
- Algorithm: HMAC-SHA256 of raw request body
- If secret is configured and signature is missing or invalid, returns `401`.

**Slack:**
- Headers: `X-Slack-Request-Timestamp`, `X-Slack-Signature`
- Secret: `SLACK_SIGNING_SECRET` env var
- Algorithm: HMAC-SHA256 of `v0:{timestamp}:{body}`
- Also handles `url_verification` challenge responses.
- Used by both `/webhook/slack` (Events API) and `/webhook/slack/commands` (slash commands).

**Discord:**
- Headers: `X-Signature-Ed25519`, `X-Signature-Timestamp`
- Secret: `DISCORD_PUBLIC_KEY` env var
- Algorithm: Ed25519 signature verification via PyNaCl
- PING (type 1) must return PONG (type 1) or Discord disables the endpoint.

### Slash Commands (CommandRouter)

Both Slack and Discord use a shared `CommandRouter` (`handlers/commands.py`) for platform-agnostic command processing.

**Pattern:** ACK immediately (< 3s) -> process in background via `asyncio.create_task()` -> send result via platform callback.

| Subcommand | Usage | Description |
|---|---|---|
| `ask <question>` | `/aiui ask what is MCP?` | Sends question to AI via Open WebUI, returns response |
| `workflow <name>` | `/aiui workflow pr-review` | Triggers n8n workflow by webhook path name |
| `status` | `/aiui status` | Checks health of all services (Open WebUI, MCP Proxy, n8n, webhook-handler) |
| `report` | `/aiui report` | Generates end-of-day report (GitHub commits, n8n executions, service health) with AI summary |
| `help` | `/aiui help` | Shows available commands |

Unknown subcommands are treated as `ask` queries. Empty text defaults to `status`.

**Slack flow:** Slack sends `application/x-www-form-urlencoded` -> `SlackCommandHandler` extracts `response_url` -> ACK with `{"text": "Processing..."}` -> background task -> result posted to `response_url`.

**Discord flow:** Discord sends JSON -> `DiscordCommandHandler` returns deferred response (type 5) -> background task -> result posted via `PATCH /webhooks/{app_id}/{token}/messages/@original`.

### n8n Workflow Triggering

The webhook handler triggers n8n workflows via `N8NClient`:
- Base URL: `N8N_URL` (default `https://n8n.srv1041674.hstgr.cloud` — the hosted n8n instance)
- The `/webhook/n8n/{workflow_path}` endpoint forwards the JSON payload to the n8n webhook node.
- Both the webhook-handler and the MCP n8n server point to the same hosted n8n instance (no split-brain).
- A local n8n container also runs in Docker Compose for Caddy-routed UI access, but workflow automation targets the hosted instance.

**Active n8n Workflows (on hosted instance):**

| Workflow | Trigger | What It Does |
|---|---|---|
| **PR Review Automation** | Webhook (6 nodes) | Receives PR data -> AI code review via HTTP Request -> posts review comment on GitHub PR |
| **GitHub Push Processor** | Webhook (5 nodes) | Receives push data -> formats commit summary -> posts notification to Slack channel |

**MCP n8n Server** (`mcp-n8n` container):
- Provides ~20 tools for managing n8n workflows from chat (list, create, activate, execute, etc.)
- Uses `czlonkowski/n8n-mcp` image wrapped with mcpo
- Connected to hosted n8n via `N8N_API_KEY` and `N8N_API_URL` env vars

### APScheduler Cron Jobs

| Job ID                 | Schedule | Function                       | Description                             |
|------------------------|----------|--------------------------------|-----------------------------------------|
| `daily_health_report`  | Daily    | `daily_health_report()`        | Checks health of all services           |
| `hourly_n8n_check`     | Hourly   | `hourly_n8n_workflow_check()`  | Verifies n8n workflows are operational  |

Jobs are registered via `register_default_jobs()` on startup and can be triggered manually via `POST /scheduler/jobs/{job_id}/trigger`.

---

## 6. Admin Portal

### Access

- **URL:** `/mcp-admin` (served via Caddy -> API Gateway -> MCP Proxy `/portal`)
- **Authentication:** Requires valid Open WebUI session (JWT via cookie)
- **Authorization:** Admin-only. The MCP Proxy checks `is_openwebui_admin(email)` which queries `"user".role = 'admin'` in PostgreSQL.
  - Not logged in: redirects to Open WebUI login (`/`)
  - Logged in, not admin: returns `403 Access Denied`
  - Logged in as admin: serves `static/admin.html`

### Management API

The admin portal frontend calls these API endpoints (routed through the gateway to MCP Proxy):

| Endpoint                  | Method       | Purpose                                    |
|---------------------------|--------------|--------------------------------------------|
| `/admin/users`            | GET          | List all users with their group memberships |
| `/admin/users/{id}`       | PUT/DELETE   | Update or remove user group memberships     |
| `/admin/groups`           | GET          | List all groups with server access mappings |
| `/admin/groups`           | POST         | Create a new group                          |
| `/admin/groups/{id}`      | PUT/DELETE   | Update group server mappings or delete group|
| `/admin/servers`          | GET          | List all configured MCP servers             |
| `/admin/endpoints`        | GET/POST/DELETE | Manage tenant-specific endpoint overrides |
| `/admin/tenant-keys`      | GET/POST/DELETE | Manage tenant-specific API keys           |
| `/admin/analytics`        | GET          | View API usage analytics                    |

---

## 7. Security Layers

```
Layer 1: TLS
    Caddy provides automatic HTTPS via Let's Encrypt (production).
    All traffic is encrypted in transit.

Layer 2: JWT Validation
    API Gateway validates HS256 JWTs signed with WEBUI_SECRET_KEY.
    Tokens come from Authorization header (API) or 'token' cookie (browser).
    Invalid/expired tokens result in empty user context (unauthenticated).

Layer 3: Rate Limiting
    API Gateway enforces per-user (100/min) and per-IP (1000/min) limits.
    Sliding window algorithm with in-memory storage.
    Static assets are exempt.

Layer 4: Signature Verification
    Webhook Handler verifies GitHub (HMAC-SHA256), Slack (v0 HMAC), and Discord (Ed25519) payloads.
    Prevents forged webhook deliveries.

Layer 5: Group-Based ACL
    MCP Proxy enforces group-based access control from PostgreSQL.
    Users only see and can execute tools for servers their groups grant access to.
    MCP-Admin group bypasses all restrictions.
    Tenant-specific API keys provide credential isolation between groups.
```

### Security Summary Table

| Layer                     | Enforced By       | Scope                       | Failure Mode                |
|---------------------------|-------------------|-----------------------------|-----------------------------|
| TLS                       | Caddy             | All traffic                 | Connection refused (prod)   |
| JWT validation            | API Gateway       | All gateway-proxied routes  | Empty user context          |
| Rate limiting             | API Gateway       | Non-static routes           | `429 Too Many Requests`     |
| Signature verification    | Webhook Handler   | `/webhook/github`, `/webhook/slack`, `/webhook/discord` | `401 Unauthorized` |
| Group-based ACL           | MCP Proxy         | All tool endpoints          | `403 Access Denied`         |

---

## 8. Automation Patterns

The system supports three complementary automation patterns:

```
1. EVENT-DRIVEN (webhooks)
   GitHub push/PR  ──►  /webhook/github  ──►  n8n workflow  ──►  AI review + GitHub comment + Slack notification
   Slack @mention   ──►  /webhook/slack   ──►  AI response  ──►  Slack reply

2. CHAT-DRIVEN (slash commands)
   User types /aiui ask|workflow|status  ──►  CommandRouter  ──►  AI response / n8n trigger / health check
   Works from both Slack and Discord (same CommandRouter)

3. SCHEDULED (cron)
   APScheduler  ──►  daily_health_report()   ──►  checks all service endpoints, posts to Slack (noon daily)
   APScheduler  ──►  hourly_n8n_workflow_check() ──►  lists n8n workflows (every hour)

4. REPORTING (slash command + data aggregation)
   /aiui report  ──►  CommandRouter  ──►  gathers GitHub commits + n8n executions + service health  ──►  AI summary  ──►  reply + optional Slack channel post
```

All three patterns can be combined — e.g., the `/aiui report` command pulls today's GitHub commits (via `REPORT_GITHUB_REPO`), n8n workflow executions (via n8n API), and service health checks, then sends the raw data to AI for summarization and posts the result back to the user and optionally to a Slack channel (`REPORT_SLACK_CHANNEL`).

---

## 9. Local vs Production

### What Changes

| Aspect               | Local (Development)                            | Production                                          |
|-----------------------|------------------------------------------------|-----------------------------------------------------|
| **Caddyfile**         | `:80 { ... }` block (plain HTTP)               | `app.example.com { ... }` block (auto-HTTPS via LE) |
| **TLS**               | No TLS, HTTP only                              | Automatic HTTPS with Let's Encrypt certificates     |
| **Exposed ports**     | `80`, `443`, `8085`, `8086`, `5678`, `127.0.0.1:3000` | Only `80` and `443` (all else internal)       |
| **Domain**            | `localhost`                                    | Real domain (e.g., `ai-ui.coolestdomain.win`)       |
| **Caddy log level**   | `INFO`                                         | `warn` (reduce noise)                               |
| **DEBUG env var**      | `true`                                         | `false`                                             |
| **Open WebUI port**   | `127.0.0.1:3000` for direct access             | No direct access, only through Caddy                |

### BASE_URL Environment Variables

These variables must match the deployment domain:

| Variable              | Local Value                    | Production Value                            |
|-----------------------|--------------------------------|---------------------------------------------|
| `WEBUI_URL`           | `http://localhost`             | `https://ai-ui.coolestdomain.win`           |
| `N8N_WEBHOOK_URL`     | `http://localhost/n8n/`        | `https://ai-ui.coolestdomain.win/n8n/`      |
| `MICROSOFT_REDIRECT_URI` | `http://localhost/oauth/microsoft/callback` | `https://ai-ui.coolestdomain.win/oauth/microsoft/callback` |

### N8N_WEBHOOK_URL Parameterization

n8n needs to know its externally reachable webhook URL so it can generate correct callback URLs. This is set via the `WEBHOOK_URL` env var in the n8n container:

```yaml
# docker-compose.unified.yml
n8n:
  environment:
    - WEBHOOK_URL=${N8N_WEBHOOK_URL:-https://ai-ui.coolestdomain.win/n8n/}
```

Caddy strips the `/n8n` prefix (`uri strip_prefix /n8n`) before forwarding to n8n on port 5678, so n8n sees clean paths like `/webhook/my-workflow` while externally the URL is `https://domain/n8n/webhook/my-workflow`.

### Port Lockdown Checklist (Production)

In production, remove or bind to `127.0.0.1` all exposed ports except Caddy:

```yaml
# REMOVE these lines (or bind to 127.0.0.1):
api-gateway:   ports: ["8085:8080"]    # -> remove
webhook-handler: ports: ["8086:8086"]  # -> remove
n8n:           ports: ["5678:5678"]    # -> remove
open-webui:    ports: ["3000:8080"]    # -> already 127.0.0.1 only
```

All services remain accessible through Caddy's reverse proxy routes.
