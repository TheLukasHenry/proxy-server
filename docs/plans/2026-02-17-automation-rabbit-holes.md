# Automation Rabbit Holes — Research for Lukas

**Date:** 2026-02-17
**Context:** Lukas wants to know what automation features to explore next.
**Method:** Each topic was researched via web search, npm registry, GitHub, and official docs.

Each topic covers: what it is, real packages/tools found, how it integrates, gotchas, effort, and value.

---

## 1. n8n MCP Server

**What:** An MCP server that lets Claude (or any LLM) create, edit, activate, and manage n8n workflows programmatically via MCP tools.

### Packages Found

| Package | GitHub Stars | Tools | Size | Best For |
|---------|-------------|-------|------|----------|
| [czlonkowski/n8n-mcp](https://github.com/czlonkowski/n8n-mcp) | **13,544** | ~20 | 78MB (SQLite docs DB) | Full docs + live API — knows all 1,084 n8n nodes |
| [leonardsellem/n8n-mcp-server](https://github.com/leonardsellem/n8n-mcp-server) | **1,561** | 12 | Lightweight | Pure API wrapper — workflow CRUD + execution mgmt |
| [salacoste/mcp-n8n-workflow-builder](https://github.com/salacoste/mcp-n8n-workflow-builder) | 208 | 17 | Medium | Multi-instance support, credential + tag management |

> **Note:** The package `@nerdondon/n8n-mcp-server` does not exist on npm or GitHub. The closest match (`nerding-io/n8n-nodes-mcp`, 2,982 stars) is the **opposite direction** — it makes n8n an MCP *client*, not a server.

### Recommendation: leonardsellem/n8n-mcp-server

Best fit for our system because it's lightweight, pure API wrapper (no 78MB SQLite bloat), and provides the 12 most useful tools:

**Workflow tools:** `workflow_list`, `workflow_get`, `workflow_create`, `workflow_update`, `workflow_delete`, `workflow_activate`, `workflow_deactivate`
**Execution tools:** `execution_run`, `run_webhook`, `execution_get`, `execution_list`, `execution_stop`
**MCP Resources:** `n8n://workflows/list`, `n8n://workflow/{id}`, `n8n://executions/{workflowId}`

### Integration

Deploy as a Docker container with mcpo (same pattern as GitHub/Notion MCP servers):

```yaml
# docker-compose.unified.yml
mcp-n8n:
  build: ./mcp-servers/n8n
  container_name: mcp-n8n
  restart: unless-stopped
  environment:
    - N8N_API_URL=http://n8n:5678/api/v1
    - N8N_API_KEY=${N8N_API_KEY}
    - N8N_WEBHOOK_USERNAME=${N8N_USER:-admin}
    - N8N_WEBHOOK_PASSWORD=${N8N_PASSWORD:-}
    - MCP_API_KEY=${MCP_API_KEY:-mcp-secret-key}
  networks:
    - backend
  depends_on:
    - n8n
```

Add to `mcp-servers.json`:
```json
{
  "id": "n8n",
  "name": "n8n Workflow MCP",
  "url": "http://mcp-n8n:8000",
  "type": "openapi",
  "description": "n8n workflow automation - create, manage, execute workflows",
  "tier": "local",
  "groups": ["MCP-Admin"],
  "api_key_env": "MCP_API_KEY"
}
```

### Gotchas
- Requires enabling n8n API access (`N8N_PUBLIC_API_DISABLED=false`) and generating an API key
- The n8n API never returns credential secret values — MCP tools can't read existing passwords
- All n8n MCP servers are stdio-only — all require mcpo wrapper for HTTP access
- `execution_run` uses the API key, but `run_webhook` uses separate basic auth credentials

**Effort:** Small-Medium (half a day). The mcpo container pattern is proven.
**Value:** High. AI-driven workflow creation — users describe what they want in chat, the LLM builds and deploys it.

---

## 2. More n8n Workflow Templates

### Template-by-Template Research

#### A. Jira → Slack Notifications (EASIEST — start here)

**n8n nodes:** Jira Trigger (native, 30+ event types, JQL filtering) + Slack (native)
**Existing templates:** 6+ exact matches on [n8n.io/workflows](https://n8n.io/workflows):
- [Automate Incident Response with Jira, Slack, Google Sheets & Drive](https://n8n.io/workflows/9826)
- [AI-powered Bug Triage with OpenAI, Jira and Slack](https://n8n.io/workflows/11697)
- [Track Jira Epic Health with Automated Risk Alerts via Slack](https://n8n.io/workflows/9832)

**Known bug:** Jira Trigger creates **duplicate webhooks** in Jira on every n8n restart ([#24433](https://github.com/n8n-io/n8n/issues/24433)). Workaround: use a raw Webhook node + manually configure the Jira webhook.

**Effort:** 1-3 hours. Can be done in under 1 hour using an existing template.

#### B. Scheduled Daily Report (Excel + Slack/Email)

**n8n nodes:** Schedule Trigger (cron), Convert to File (XLSX — core node, replaced Spreadsheet File in v1.21.0+), Slack, Send Email — all native and production-stable.
**Existing templates:** 4+ close matches:
- [Daily Cash Flow Reports with Google Sheets, Slack & Email](https://n8n.io/workflows/10109)
- [Track Employee Attendance with Analytics, Email Reports & Slack Alerts](https://n8n.io/workflows/10106)

**Limitation:** Convert to File does **not** support charts, formulas, conditional formatting, or pivot tables. For advanced Excel features, use a Code node with `exceljs` library.

**Effort:** 2-4 hours.

#### C. Weekly Digest / Multi-Source Summary

**n8n nodes:** Schedule Trigger, Summarize (pivot-table aggregation), Aggregate (reshape), Merge (combine streams) — all core nodes. Optional: LangChain Summarization Chain for AI summaries.
**Existing templates:** 6+ close matches:
- [Daily News Digest & Weekly Trends with AI Filtering, Slack & Google Sheets](https://n8n.io/workflows/10977)
- [Weekly AI News Digest with Perplexity AI and Gmail Newsletter](https://n8n.io/workflows/4412)
- [Analyze Weekly Notes with GPT-4 for Actionable Tasks & Summaries](https://n8n.io/workflows/8119)

**Main challenge:** Data normalization — each source (GitHub, Jira, n8n) returns different schemas. Need Code nodes to normalize before merging.

**Effort:** 4-8 hours (basic), 8-16 hours (with AI summarization and rich formatting).

#### D. GitHub PR → SonarQube → PR Comment (HARDEST)

**n8n nodes:** **No native SonarQube node exists.** Must use Webhook + HTTP Request + Code nodes.
**Existing templates:** 0 exact matches. 1 structural reference: [Automated PR Code Reviews with GitHub, GPT-4](https://n8n.io/workflows/3804).

**Architecture:**
```
SonarQube Webhook (analysis complete)
  → n8n Webhook Node (receives POST)
  → Code Node (parse quality gate status, conditions, metrics)
  → IF Node (pass/fail branch)
  → HTTP Request Node (POST to GitHub API: create PR comment)
```

**Key challenge:** SonarQube webhooks fire on *analysis completion*, not PR creation. Must pass PR number through scanner (`sonar.analysis.prNumber=123`) so the n8n workflow can post to the correct PR. HMAC signature verification (`X-Sonar-Webhook-HMAC-SHA256`) must be handled manually in a Code node.

**Effort:** 4-8 hours.

### Template Priority

| Template | Effort | n8n Node Support | Templates Available |
|----------|--------|-----------------|-------------------|
| Jira → Slack | 1-3 hrs | Both native | 6+ exact |
| Daily Excel Report | 2-4 hrs | All core nodes | 4+ close |
| Weekly Digest | 4-8 hrs | All core nodes | 6+ close |
| SonarQube → PR Comment | 4-8 hrs | No SonarQube node | 0 exact |

**Value:** Medium-High. Start with Jira→Slack (trivial), then Daily Report.

---

## 3. Microsoft Teams Webhook (Phase 2C)

### Critical Update: Office 365 Connectors Are Dead

Microsoft **deprecated Office 365 Connectors** (the old "Incoming Webhook" connector). Timeline:
- New connector creation blocked: **August 2024**
- Existing connectors stop working: **March 31, 2026**

The replacement is **Power Automate Workflows** using the "When a Teams webhook request is received" trigger. This gives you a POST URL similar to the old connectors, but it's a Power Automate endpoint.

### Sending TO Teams (Easy)

POST Adaptive Card JSON to the Power Automate Workflow URL. No authentication needed on your side — the URL itself is the secret.

```json
{
  "type": "message",
  "attachments": [{
    "contentType": "application/vnd.microsoft.card.adaptive",
    "content": {
      "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
      "type": "AdaptiveCard",
      "version": "1.4",
      "body": [
        {"type": "TextBlock", "text": "GitHub Push Event", "size": "Large", "weight": "Bolder"},
        {"type": "TextBlock", "text": "3 commits pushed to main by @lukas", "wrap": true}
      ]
    }
  }]
}
```

> **Use Adaptive Card version 1.4** — version 1.5 does not work correctly in Teams.

**Effort:** 1-2 hours. Add a `TeamsClient` with one `send_adaptive_card()` method.

### Receiving FROM Teams (Medium)

Use **Teams Outgoing Webhooks** — users @mention the webhook name, Teams POSTs to your callback URL.

**Auth:** HMAC-SHA256 with **base64-encoded key** (different from GitHub's hex format). Header: `Authorization: HMAC <base64hash>`.

```python
import hmac, hashlib, base64

def verify_teams_signature(body: bytes, auth_header: str, security_token: str) -> bool:
    if not auth_header or not auth_header.startswith("HMAC "):
        return False
    provided_hmac = auth_header[5:]
    key_bytes = base64.b64decode(security_token)
    computed = hmac.new(key_bytes, body, hashlib.sha256).digest()
    return hmac.compare_digest(provided_hmac, base64.b64encode(computed).decode())
```

### Gotchas
- **5-second response timeout** — for AI processing, respond immediately with "Processing..." and push results back via Workflow URL
- **Public channels only** — Outgoing Webhooks cannot receive from private channels or DMs
- **No retry on failure** — if your endpoint is down, Teams does not retry
- **Interactive card actions are limited** — only `openURL` works with outgoing webhooks. Full interactivity requires Bot Framework (Azure subscription, complex)

**Effort:** Send-only: 1-2 hours. Send + Receive: 3-4 hours (mirrors Slack handler pattern). Full Bot Framework: 1-2 weeks (not recommended unless needed).
**Value:** Medium. Enterprise teams using Teams get notifications without opening another tool.

---

## 4. Discord Webhook (Phase 3D)

### Sending TO Discord (Easiest of All Platforms)

POST JSON to webhook URL. No authentication, no special setup.

```json
{
  "username": "IO Platform",
  "content": "New deployment completed",
  "embeds": [{
    "title": "GitHub Push Event",
    "description": "3 commits pushed to main",
    "color": 5814783,
    "fields": [
      {"name": "Repository", "value": "TheLukasHenry/proxy-server", "inline": true},
      {"name": "Branch", "value": "main", "inline": true}
    ],
    "timestamp": "2026-02-17T10:30:00.000Z"
  }]
}
```

**Rate limits:** 30 requests / 60 seconds per webhook. Returns `429` with `Retry-After` header.

**Effort:** 1 hour. Add `DiscordClient` with `send_embed()` method.

### Receiving FROM Discord (Medium — Different Auth Model)

Two options:
- **Application Webhook Events** — limited event set (app lifecycle only, NOT channel messages)
- **Interactions Endpoint** — slash commands, buttons, modals without WebSocket

> **You cannot receive channel messages via webhooks.** That requires a Gateway bot (WebSocket), which doesn't fit the webhook handler architecture.

**Auth:** Discord uses **Ed25519 signatures** (not HMAC!). Requires `PyNaCl` library.

```python
from nacl.signing import VerifyKey

def verify_discord_signature(body: bytes, signature: str, timestamp: str, public_key: str) -> bool:
    try:
        verify_key = VerifyKey(bytes.fromhex(public_key))
        verify_key.verify(timestamp.encode() + body, bytes.fromhex(signature))
        return True
    except Exception:
        return False
```

### Gotchas
- **Ed25519, not HMAC** — needs `PyNaCl` dependency (~1.5MB)
- **3-second response deadline** — must send deferred response (type 5) for slow operations
- **Discord periodically sends invalid signatures** to test your endpoint — if verification fails, they disable it
- **30 req/60s rate limit** is relatively tight for high-volume systems

**Effort:** Send-only: 1 hour. Slash commands: 4-6 hours (different auth model, deferred response pattern).
**Value:** Low-Medium. Useful for dev/community notifications, but lowest business priority.

---

## 5. Two-Way Slack

### What's Actually Needed

Two new FastAPI endpoints + Slack App Manifest update:

```python
# New endpoints in webhook-handler/main.py

@app.post("/webhook/slack/commands")    # Slash commands (form-encoded, NOT JSON!)
async def slack_slash_command(request: Request):
    form_data = await request.form()
    command = form_data.get("command")       # "/mcp"
    text = form_data.get("text")             # "search repos node"
    response_url = form_data.get("response_url")
    # ACK immediately (< 3 seconds!) then process in background
    asyncio.create_task(_process_command(command, text, response_url))
    return {"response_type": "ephemeral", "text": "Processing..."}

@app.post("/webhook/slack/interactions") # Button clicks, modal submissions
async def slack_interactions(request: Request):
    form_data = await request.form()
    payload = json.loads(form_data.get("payload", "{}"))
    # Route by payload["type"]: "block_actions", "view_submission", etc.
```

### Slack App Manifest Changes

```yaml
features:
  slash_commands:
    - command: /mcp
      description: Execute MCP tools
      usage_hint: "[server] [tool] [args...]"
      url: https://your-domain.com/webhook/slack/commands
    - command: /n8n
      description: Trigger n8n workflows
      usage_hint: "[workflow-name]"
      url: https://your-domain.com/webhook/slack/commands

oauth_config:
  scopes:
    bot:
      - commands              # NEW: required for slash commands

settings:
  interactivity:
    is_enabled: true          # NEW: enable interactive components
    request_url: https://your-domain.com/webhook/slack/interactions
```

### The 3-Second Rule (Critical)

All slash commands must ACK within 3 seconds or the user sees `operation_timeout`. Pattern:
1. Return `200` with "Processing..." immediately
2. Use `asyncio.create_task()` for actual MCP/AI work
3. POST results back to `response_url` (valid 30 min, max 5 responses)

### ChatOps Flow Example

```
User: /mcp search repos node
  → Slack POST → /webhook/slack/commands
  → ACK "Searching..." (< 3 sec)
  → Background: parse command → call MCP Proxy → format Block Kit result
  → POST to response_url with buttons: [View Details] [Run Again]
  → User clicks [View Details]
  → Slack POST → /webhook/slack/interactions
  → Handle block_action, maybe open modal
```

Reference implementation: [slack-mcp-client](https://github.com/tuannvm/slack-mcp-client) — Slack bot bridging to MCP servers.

### Why Easier Than Expected

We already have `SlackClient` with `post_message()` and `verify_slack_signature()`, `SlackWebhookHandler` for Events API, and MCP proxy + n8n client integrations. That covers ~60% of the work.

### Gotchas
- Slash commands send `application/x-www-form-urlencoded`, NOT JSON
- `trigger_id` for modals expires in 3 seconds
- **May 2025 rate limit change:** Non-Marketplace apps created after May 29, 2025 face restricted `conversations.history` limits (1 req/min, max 15 objects). Does NOT affect posting messages or handling commands.
- Block Kit `text` blocks max at 3000 characters — truncate or paginate MCP tool output
- Use **HTTP mode** (not Socket Mode) — fits existing FastAPI architecture perfectly

**Effort:** 2-3 dev days (17-23 hours). Not "1-2 weeks" — existing code covers the hard parts.
**Value:** High. Full ChatOps — users invoke MCP tools and trigger workflows without leaving Slack.

---

## 6. Workflow Marketplace in Admin Portal

### What Exists Today

**No mature open-source solution.** Options found:
- [n8nDash](https://github.com/SolomonChrist/n8nDash) — early-stage touchscreen-ready frontend for non-technical users. Under heavy development.
- n8n's own [template library](https://n8n.io/workflows/) (8,300+ templates) — not self-hostable
- [haveworkflow.com](https://haveworkflow.com/marketplace/n8n-templates/) — commercial, not open-source

**Bottom line:** Must build a custom page on top of the n8n REST API.

### n8n API Coverage

All endpoints under `/api/v1`, authenticated via `X-N8N-API-KEY`:

| Resource | Operations |
|----------|-----------|
| Workflows | List, Get, Create, Update, Delete, Activate, Deactivate, Execute, Transfer, Version history |
| Executions | List (filter by status: success/error/waiting/running), Get, Delete, Retry |
| Credentials | List (metadata only — secrets never exposed), Create, Update, Delete, Schema |
| Tags | Full CRUD |

**Computing stats yourself:** The API returns raw execution records (status, startedAt, stoppedAt). You compute success rate, avg duration, failure trends. n8n's built-in Insights dashboard is NOT exposed via the public API.

### What to Build

Extend `webhook-handler/clients/n8n.py` with new methods:

```python
async def list_workflows(self) -> list[dict]:
    """GET /api/v1/workflows"""

async def activate_workflow(self, workflow_id: str) -> dict:
    """POST /api/v1/workflows/{id}/activate"""

async def deactivate_workflow(self, workflow_id: str) -> dict:
    """POST /api/v1/workflows/{id}/deactivate"""

async def list_executions(self, workflow_id: str = None, status: str = None) -> list[dict]:
    """GET /api/v1/executions?workflowId=X&status=Y"""
```

Then add admin API routes:
```
GET  /api/admin/workflows          — list with execution stats
POST /api/admin/workflows/{id}/toggle  — activate/deactivate
POST /api/admin/workflows/{id}/trigger — execute with test data
```

Frontend: minimal catalog page with workflow cards, status badges, toggle switches, execution sparklines, quick-trigger buttons.

**Effort:** 3-5 dev days (backend API: 1 day, frontend page: 2-3 days, polish: 1 day).
**Value:** High for operations. Single pane of glass for all automations without opening n8n directly.

---

## Updated Priority Recommendation

| Priority | Topic | Effort | Value | Key Research Insight |
|----------|-------|--------|-------|---------------------|
| **1** | n8n workflow templates | 1-3 hrs each | High | Rich template ecosystem — Jira→Slack has 6+ ready-made templates |
| **2** | n8n MCP Server | Half day | High | leonardsellem package (1.5k stars) wraps cleanly with mcpo |
| **3** | Two-way Slack | 2-3 dev days | High | Easier than expected — existing code covers 60% of the work |
| **4** | Teams webhook (send first) | 2-3 hrs | Medium | Old connectors die March 2026 — must use Power Automate Workflows |
| **5** | Discord webhook (send first) | 1-2 hrs | Low | Easiest platform but lowest business value |
| **6** | Workflow marketplace | 3-5 dev days | High | No open-source to adopt — must build custom on n8n API |

### Quick Win Path (can be done in 1 day)

1. Deploy Jira→Slack template from existing n8n.io library (1 hour)
2. Add `DiscordClient.send_embed()` for notifications (1 hour)
3. Add `TeamsClient.send_adaptive_card()` for notifications (1-2 hours)
4. Deploy leonardsellem/n8n-mcp-server with mcpo (half day)

### Full ChatOps Path (1-2 weeks)

1. Quick wins above (1 day)
2. Two-way Slack: slash commands + interactive buttons (2-3 days)
3. Teams outgoing webhook handler (3-4 hours)
4. Remaining n8n templates: daily report, weekly digest, SonarQube (2-3 days)
5. Workflow marketplace admin page (3-5 days)
