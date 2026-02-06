# Webhook System Roadmap: Phase 2 & Phase 3

## Date: February 5, 2026
## Status: Phase 1 Complete | Phase 2 & 3 Planned

---

## Current State (Phase 1 - COMPLETE)

| Feature | Status | Details |
|---------|--------|---------|
| Chat completions | ✅ Working | `/api/chat/completions` via Open WebUI |
| GitHub Issues webhook | ✅ Working | AI analyzes & comments on new issues |
| Signature verification | ✅ Working | HMAC-SHA256 |
| Deployed on Hetzner | ✅ Working | Port 8086, Caddy routed, Cloudflare accessible |

### Current Architecture

```
GitHub Issue Opened
       ↓
POST https://ai-ui.coolestdomain.win/webhook/github
       ↓
Caddy → webhook-handler (port 8086)
       ↓
handlers/github.py → extracts title, body, labels
       ↓
clients/openwebui.py → POST /api/chat/completions (gpt-5)
       ↓
AI returns analysis
       ↓
clients/github.py → POST comment to GitHub issue
       ↓
✅ Issue now has AI comment (~47s end-to-end)
```

### Current Files

```
webhook-handler/
├── main.py              # FastAPI entry, signature verification, routing
├── config.py            # Environment configuration loader
├── Dockerfile           # Python 3.11 container
├── requirements.txt     # fastapi, httpx, pydantic-settings
├── handlers/
│   ├── __init__.py
│   └── github.py        # Issue event handler → AI analysis → comment
└── clients/
    ├── __init__.py
    ├── openwebui.py     # Calls /api/chat/completions
    └── github.py        # Posts comments to GitHub API
```

---

## What Lukas Wants vs What We Have

| Feature | Current State | Target |
|---------|--------------|--------|
| Chat completions | ✅ Working | ✅ |
| n8n workflows | ❌ | Webhook → n8n → AI |
| WebUI Pipelines | ❌ | Trigger pipeline functions |
| MCP Tools | ❌ | Call tools via webhook |
| Pipe Functions | ❌ | Execute custom functions |

| Trigger Source | Implemented |
|----------------|-------------|
| GitHub Issues | ✅ |
| GitHub PRs, comments | ❌ |
| Slack @mentions | ❌ |
| Microsoft Teams | ❌ |
| Discord | ❌ |
| Scheduled (cron) | ❌ |
| Generic webhook | ❌ |

---

## PHASE 2: Multi-Source Triggers & Extended GitHub Events

### Phase 2A: Extended GitHub Events

**Priority:** HIGH | **Effort:** LOW (extend existing code)

**Tasks:**
- Pull Request events (opened, synchronize, merged)
  - AI reviews PR diff, suggests improvements
- Issue comments (created)
  - AI responds to @mentions in comments
- PR reviews (submitted)
  - AI summarizes review feedback
- Push events
  - AI analyzes commit messages, detects patterns

**Files to modify:**
- `handlers/github.py` — add `_handle_pull_request_event()`, `_handle_comment_event()`, `_handle_push_event()`
- `clients/openwebui.py` — add `analyze_pull_request()`, `analyze_comment()`

**GitHub Webhook Config Update:**
- Add events: `pull_request`, `issue_comment`, `pull_request_review`, `push`

---

### Phase 2B: Slack Integration

**Priority:** MEDIUM | **Effort:** MEDIUM

**Architecture:**
```
Slack @mention
    ↓
Slack Events API
    ↓
POST /webhook/slack
    ↓
handlers/slack.py → parse event
    ↓
clients/openwebui.py → AI analysis
    ↓
clients/slack.py → post response to Slack channel
```

**Tasks:**
- `POST /webhook/slack` endpoint in `main.py`
- Slack Events API verification (challenge response)
- Handle `app_mention` events (@bot triggers)
- Handle `message` events (DM to bot)
- Post AI response back to Slack channel

**New files:**
- `handlers/slack.py`
- `clients/slack.py`

**Requirements:**
- Slack App created in workspace
- Bot token with `chat:write`, `app_mentions:read` scopes
- Event subscriptions URL pointed to `/webhook/slack`

---

### Phase 2C: Microsoft Teams Integration

**Priority:** MEDIUM | **Effort:** HIGH (Bot Framework complexity)

**Architecture:**
```
Teams @mention or message
    ↓
Teams Bot Framework
    ↓
POST /webhook/teams
    ↓
handlers/teams.py → parse activity
    ↓
clients/openwebui.py → AI analysis
    ↓
clients/teams.py → post adaptive card response
```

**Tasks:**
- `POST /webhook/teams` endpoint in `main.py`
- Bot Framework authentication (Azure AD)
- Handle @mention in channels
- Handle direct messages
- Post adaptive cards with AI response

**New files:**
- `handlers/teams.py`
- `clients/teams.py`

**Requirements:**
- Azure Bot registration
- Teams app manifest
- Azure AD app for auth

---

### Phase 2D: Scheduled Triggers (Cron)

**Priority:** MEDIUM | **Effort:** LOW

**Architecture:**
```
APScheduler (inside webhook-handler)
    ↓
Trigger at configured time (e.g., 8 AM daily)
    ↓
clients/openwebui.py → AI generates report
    ↓
clients/slack.py or clients/github.py → post output
```

**Tasks:**
- Add APScheduler to webhook-handler
- Daily standup summary (8 AM)
- Weekly report generation
- Configurable schedules via env or database
- Output to Slack/Teams/Email/GitHub

**New files:**
- `scheduler.py`

**New dependencies:**
- `apscheduler`

---

### Phase 2E: Generic Webhook Endpoint

**Priority:** LOW | **Effort:** LOW

**Architecture:**
```
Any external service
    ↓
POST /webhook/generic
    ↓
handlers/generic.py → parse JSON, apply prompt template
    ↓
clients/openwebui.py → AI analysis
    ↓
POST response to callback URL
```

**Tasks:**
- `POST /webhook/generic` endpoint in `main.py`
- Accept any JSON payload
- Configurable prompt template per source
- Callback URL for response delivery
- API key authentication

**New files:**
- `handlers/generic.py`

---

## PHASE 3: Advanced Integrations (Lukas's Vision)

### Phase 3A: n8n Workflow Integration

**Priority:** HIGH | **Effort:** MEDIUM

**Architecture:**
```
Webhook → webhook-handler → n8n workflow → Open WebUI → Response

Example complex flow:
GitHub Issue → webhook-handler → n8n →
    ├── Step 1: AI analyzes issue
    ├── Step 2: Create Jira ticket
    ├── Step 3: Assign to team member
    └── Step 4: Notify Slack channel
```

**Tasks:**
- Deploy n8n container alongside existing stack
- Create n8n trigger node (receives from webhook-handler)
- n8n calls Open WebUI `/api/chat/completions`
- n8n handles complex multi-step workflows
- Webhook-handler routes to n8n for complex workflows

**New files:**
- `clients/n8n.py` — trigger n8n workflows via API
- `n8n/` — workflow JSON exports for version control

**Docker Compose addition:**
```yaml
n8n:
  image: n8nio/n8n
  ports:
    - "5678:5678"
  environment:
    - N8N_BASIC_AUTH_ACTIVE=true
    - N8N_BASIC_AUTH_USER=admin
    - N8N_BASIC_AUTH_PASSWORD=${N8N_PASSWORD}
  volumes:
    - n8n_data:/home/node/.n8n
  networks:
    - internal
```

---

### Phase 3B: MCP Tools via Webhook

**Priority:** HIGH | **Effort:** MEDIUM

**Problem:** MCP tools do NOT work via Open WebUI API (known issue #15472)

**Solution:** Call MCP Proxy directly, bypass Open WebUI for tool execution

**Architecture:**
```
Webhook → webhook-handler → MCP Proxy → Tool executes → Response

Example:
GitHub issue labeled "create-jira"
    ↓
webhook-handler detects label
    ↓
clients/mcp_proxy.py → POST /jira/create_issue
    ↓
Jira ticket created
    ↓
AI + tool result posted back to GitHub
```

**Tasks:**
- Add MCP Proxy client to webhook-handler
- `POST /webhook/mcp/{tool_name}` endpoint
- Route specific triggers to specific MCP tools
- Combine AI analysis + tool execution

**New files:**
- `clients/mcp_proxy.py`
- `handlers/mcp.py`

**Environment variables:**
```
MCP_PROXY_URL=http://mcp-proxy:8000
MCP_USER_EMAIL=webhook-handler@system
MCP_USER_GROUPS=MCP-Admin
```

---

### Phase 3C: WebUI Pipelines & Pipe Functions

**Priority:** MEDIUM | **Effort:** HIGH

**What are Pipe Functions?**
Custom Python code that runs INSIDE Open WebUI. Unlike API calls, Pipe Functions CAN execute MCP tools because they run in the same process.

**Architecture:**
```
Webhook → Open WebUI Pipe Function → MCP tools work! → Response

Example:
POST /api/chat/completions with pipe function model
    ↓
Pipe Function receives webhook payload
    ↓
Calls MCP tools internally (works inside WebUI)
    ↓
Returns combined AI + tool response
```

**Tasks:**
- Create custom Pipe Function in Open WebUI
  - Receives webhook payload, executes tools, returns response
- Webhook-handler calls Pipe Function via special model name
- Pipe Function has access to MCP tools (works internally)
- Complex automation: AI decides which tools to call

**New files:**
- `open-webui-functions/webhook_pipe.py`
- `clients/openwebui.py` — add pipe function caller method

---

### Phase 3D: Discord Integration

**Priority:** LOW | **Effort:** MEDIUM

**Architecture:**
```
Discord @mention or slash command
    ↓
Discord Bot
    ↓
POST /webhook/discord
    ↓
handlers/discord.py → parse interaction
    ↓
clients/openwebui.py → AI analysis
    ↓
clients/discord.py → embed response
```

**Tasks:**
- Discord bot registration
- `POST /webhook/discord` endpoint
- Handle @mentions and slash commands
- Embed responses with rich formatting

**New files:**
- `handlers/discord.py`
- `clients/discord.py`

**Requirements:**
- Discord application created
- Bot token with message intents
- Slash commands registered

---

## Priority Order (Recommended Implementation)

| # | Feature | Priority | Effort | Dependency |
|---|---------|----------|--------|------------|
| 1 | Extended GitHub Events (2A) | HIGH | LOW | None |
| 2 | MCP Tools via Webhook (3B) | HIGH | MEDIUM | None |
| 3 | n8n Integration (3A) | HIGH | MEDIUM | Deploy n8n |
| 4 | Slack Integration (2B) | MEDIUM | MEDIUM | Slack app setup |
| 5 | Scheduled Triggers (2D) | MEDIUM | LOW | None |
| 6 | Pipe Functions (3C) | MEDIUM | HIGH | Open WebUI config |
| 7 | Microsoft Teams (2C) | MEDIUM | HIGH | Azure AD setup |
| 8 | Generic Webhook (2E) | LOW | LOW | None |
| 9 | Discord (3D) | LOW | MEDIUM | Discord bot setup |

---

## Target Architecture (Phase 2 & 3 Complete)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         TRIGGER SOURCES                                 │
├───────────┬──────────┬──────────┬──────────┬──────────┬────────────────┤
│  GitHub   │  Slack   │  Teams   │ Discord  │  Cron    │  Generic HTTP  │
└─────┬─────┴────┬─────┴────┬─────┴────┬─────┴────┬─────┴───────┬────────┘
      └──────────┴──────────┴────┬─────┴──────────┴─────────────┘
                                 ▼
                ┌────────────────────────────────┐
                │    Webhook Handler Service      │
                │    - Validate signatures        │
                │    - Parse payloads             │
                │    - Route to correct handler   │
                │    - Rate limiting              │
                │    - Queue management           │
                └──────┬────────────┬─────────────┘
                       │            │
           ┌───────────┘            └───────────┐
           ▼                                    ▼
┌─────────────────────┐              ┌─────────────────────┐
│   Open WebUI API    │              │    n8n Workflows    │
│ /api/chat/completions│             │  Complex multi-step │
│   Pipe Functions    │              │  orchestration      │
└──────────┬──────────┘              └──────────┬──────────┘
           │                                    │
           └────────────┬───────────────────────┘
                        ▼
              ┌─────────────────────┐
              │     MCP Proxy       │
              │  GitHub, Jira,      │
              │  Linear, Trello,    │
              │  Filesystem, etc.   │
              └──────────┬──────────┘
                         ▼
               Response back to source
               (GitHub comment, Slack msg,
                Teams card, Discord embed)
```

---

## Known Limitations

1. **MCP Tools via API** — Still broken in Open WebUI. Workaround: direct MCP Proxy calls or Pipe Functions
2. **Streaming** — Channel webhooks don't support streaming responses
3. **Rate Limits** — GitHub: 10 req/s, Slack: depends on tier, Open WebUI: configurable
4. **Auth Complexity** — Each source has different auth (signatures, OAuth, Bot Framework)

---

## References

- [Open WebUI API Docs](https://docs.openwebui.com/getting-started/api-endpoints/)
- [Open WebUI Webhooks](https://docs.openwebui.com/features/interface/webhooks/)
- [Open WebUI Pipe Functions](https://docs.openwebui.com/features/plugin/functions/pipe/)
- [MCP Tools API Issue #15472](https://github.com/open-webui/open-webui/discussions/15472)
- [n8n + Open WebUI Integration](https://www.pondhouse-data.com/blog/integrating-n8n-with-open-webui)
- [Research: Webhook Deep Dive](./research-webhook-openwebui-deep-dive.md)
- [Webhook Architecture Doc](./webhook-architecture.md)
