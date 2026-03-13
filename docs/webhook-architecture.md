# WEBHOOK ARCHITECTURE - Complete Explanation

**Last Updated:** 2026-02-19

## What is a Webhook?

**Normal API:** You ask for data -> Server responds
```
YOU  --------->  SERVER
     "Give me data"

YOU  <---------  SERVER
     "Here's data"
```

**Webhook (Reverse):** Server tells YOU when something happens
```
GITHUB  --------->  YOUR SERVER
        "Hey! Someone created a PR!"
```

**Simple analogy:**
- **Normal API** = You call a restaurant to ask if your table is ready
- **Webhook** = Restaurant calls YOU when your table is ready

---

## All Webhook Endpoints

The webhook-handler service runs on port 8086 and handles events from multiple sources.

| Endpoint | Source | What It Does |
|---|---|---|
| `/webhook/github` | GitHub | Receives push/PR/issue events, triggers n8n workflows for AI review |
| `/webhook/slack` | Slack Events API | Receives @mentions and DMs, sends AI responses back |
| `/webhook/slack/commands` | Slack Slash Commands | Handles `/aiui ask\|workflow\|status` commands |
| `/webhook/discord` | Discord Interactions | Handles `/aiui` slash commands from Discord |
| `/webhook/n8n/{path}` | Any (forwarding) | Forwards JSON payload to an n8n workflow webhook node |
| `/webhook/mcp/{server}/{tool}` | Any | Executes an MCP tool directly (e.g., create GitHub issue) |
| `/webhook/automation` | Any | AI + MCP tool execution via pipe function |
| `/webhook/generic` | Any | Send any JSON, get AI analysis back |

---

## Flow 1: GitHub PR -> AI Code Review

This is the main automation flow. When someone creates a PR, the AI reviews the code and posts a comment.

```
  STEP 1: Developer creates a Pull Request on GitHub

  +-----------------------------------------+
  |         GITHUB.COM                       |
  |                                          |
  |   Developer creates PR #42              |
  |   Title: "Add user auth"                |
  |   Changed files: auth.py, tests.py      |
  +------------------+-----------------------+
                     |
                     | GitHub sends POST request automatically
                     | to YOUR webhook URL
                     v
  +-----------------------------------------+
  |   STEP 2: Caddy receives request         |
  |                                          |
  |   URL: https://ai-ui.coolestdomain.win   |
  |        /webhook/github                   |
  |                                          |
  |   Routes to -> webhook-handler:8086      |
  +------------------+-----------------------+
                     |
                     v
  +-----------------------------------------+
  |   STEP 3: webhook-handler/main.py        |
  |                                          |
  |   1. Verify HMAC-SHA256 signature        |
  |   2. Parse JSON payload                  |
  |   3. Check event type = "pull_request"   |
  |   4. Forward to n8n workflow             |
  +------------------+-----------------------+
                     |
                     v
  +-----------------------------------------+
  |   STEP 4: n8n "PR Review Automation"     |
  |   (6-node workflow on hosted n8n)        |
  |                                          |
  |   1. Receive webhook data                |
  |   2. Extract PR details (title, diff)    |
  |   3. Send to AI via HTTP Request         |
  |   4. AI analyzes code changes            |
  |   5. Post review comment on GitHub PR    |
  |   6. Notify Slack channel                |
  +------------------------------------------+

  RESULT: PR has AI review comment + Slack notification!
```

---

## Flow 2: Slash Commands (/aiui)

Users can interact with the system from Slack or Discord using `/aiui` commands.

```
  SLACK                                      DISCORD
  +------------------+                       +------------------+
  | User types:      |                       | User types:      |
  | /aiui ask what   |                       | /aiui ask what   |
  |   is MCP?        |                       |   is MCP?        |
  +--------+---------+                       +--------+---------+
           |                                          |
           | form-encoded POST                        | JSON POST
           | /webhook/slack/commands                   | /webhook/discord
           v                                          v
  +--------+---------+                       +--------+---------+
  | Verify Slack     |                       | Verify Ed25519   |
  | HMAC signature   |                       | signature        |
  +--------+---------+                       +--------+---------+
           |                                          |
           +------------------+  +--------------------+
                              |  |
                              v  v
                    +---------+--+---------+
                    |   CommandRouter       |
                    |   (shared, platform-  |
                    |    agnostic)          |
                    |                      |
                    |   Subcommands:       |
                    |   - ask <question>   |
                    |   - workflow <name>  |
                    |   - report           |
                    |   - status           |
                    |   - help             |
                    +----------+-----------+
                               |
                    +----------+-----------+
                    |                      |
                    v                      v
          +--------+-------+    +---------+-------+
          | "ask" command  |    | "workflow" cmd   |
          | -> Open WebUI  |    | -> n8n workflow  |
          |    AI chat     |    |    trigger       |
          +--------+-------+    +---------+-------+
                   |                      |
                   v                      v
          Reply sent back via      Workflow result
          response_url (Slack)     sent back to user
          or edit_original (Discord)
```

**Available commands:**
- `/aiui ask <question>` -- Ask the AI anything
- `/aiui workflow <name>` -- Trigger an n8n workflow
- `/aiui report` -- Generate end-of-day activity report (GitHub commits, n8n executions, health)
- `/aiui status` -- Check health of all services
- `/aiui help` -- Show available commands

---

## Flow 3: Scheduled Jobs (Cron)

APScheduler runs background tasks on a schedule:

| Job | When | What |
|---|---|---|
| `daily_health_report` | Every day at noon | Checks health of Open WebUI, MCP Proxy, n8n, webhook-handler; posts to Slack if configured |
| `hourly_n8n_check` | Every hour | Lists all n8n workflows and their active/inactive status |

You can also trigger these manually:
- `GET /scheduler/health-report` -- Run health check now
- `GET /scheduler/n8n-check` -- Run n8n check now
- `POST /scheduler/jobs/{job_id}/trigger` -- Trigger any job

---

## File Structure & Purpose

```
webhook-handler/
|
+-- main.py                    <- ENTRY POINT
|   |                             FastAPI app, 14 endpoints
|   |                             Initializes all clients on startup
|
+-- config.py                  <- SETTINGS
|   |                             Loads from .env (21 variables)
|   |                             GitHub, Slack, Discord, n8n, MCP, AI
|
+-- handlers/
|   +-- commands.py            <- COMMAND ROUTER (shared by Slack + Discord)
|   |                             parse_command() -> (subcommand, arguments)
|   |                             Subcommands: ask, workflow, status, help
|   |
|   +-- github.py              <- GITHUB EVENT HANDLER
|   |                             PR events -> n8n workflow trigger
|   |                             Issue events -> AI analysis + comment
|   |
|   +-- slack.py               <- SLACK EVENTS HANDLER
|   |                             @mentions -> AI response
|   |                             DMs -> AI response
|   |
|   +-- slack_commands.py      <- SLACK SLASH COMMANDS
|   |                             /aiui -> ACK + background processing
|   |                             Posts result to response_url
|   |
|   +-- discord_commands.py    <- DISCORD SLASH COMMANDS
|   |                             /aiui -> deferred response
|   |                             Edits original message with result
|   |
|   +-- mcp.py                 <- MCP TOOL EXECUTOR
|   |                             Direct tool execution via webhook
|   |
|   +-- automation.py          <- AUTOMATION PIPE
|   |                             AI + MCP tools via pipe function
|   |
|   +-- generic.py             <- GENERIC HANDLER
|                                 Any JSON -> AI analysis
|
+-- clients/
|   +-- openwebui.py           <- TALKS TO AI (chat completions)
|   +-- github.py              <- TALKS TO GITHUB (comments, PRs)
|   +-- slack.py               <- TALKS TO SLACK (messages, response_url)
|   +-- discord.py             <- TALKS TO DISCORD (followup, edit)
|   +-- n8n.py                 <- TALKS TO N8N (trigger workflows, list)
|   +-- mcp_proxy.py           <- TALKS TO MCP PROXY (execute tools)
|
+-- scheduler.py               <- CRON JOBS (APScheduler)
|                                 daily_health_report, hourly_n8n_check
|
+-- Dockerfile                 <- CONTAINER (Python 3.11, port 8086)
+-- requirements.txt           <- DEPENDENCIES (fastapi, httpx, PyNaCl, etc.)
```

---

## Security: Signature Verification

Every external webhook is verified before processing:

**GitHub** -- HMAC-SHA256:
```
Header: X-Hub-Signature-256
Secret: GITHUB_WEBHOOK_SECRET
Algorithm: sha256=HMAC(secret, body)
```

**Slack** -- HMAC-SHA256 (v0 format):
```
Headers: X-Slack-Request-Timestamp, X-Slack-Signature
Secret: SLACK_SIGNING_SECRET
Algorithm: v0=HMAC(secret, "v0:{timestamp}:{body}")
Used by: /webhook/slack AND /webhook/slack/commands
```

**Discord** -- Ed25519:
```
Headers: X-Signature-Ed25519, X-Signature-Timestamp
Secret: DISCORD_PUBLIC_KEY
Algorithm: Ed25519 verify(public_key, timestamp+body, signature)
Library: PyNaCl
```

---

## Required Environment Variables

| Variable | Purpose | Used By |
|---|---|---|
| `GITHUB_WEBHOOK_SECRET` | Verify GitHub webhook signatures | `/webhook/github` |
| `GITHUB_TOKEN` | Post comments/reviews on GitHub | GitHub client |
| `OPENWEBUI_API_KEY` | Authenticate with Open WebUI | AI chat completions |
| `AI_MODEL` | Which AI model to use (default: gpt-4-turbo) | All AI handlers |
| `SLACK_BOT_TOKEN` | Send messages to Slack | Slack client |
| `SLACK_SIGNING_SECRET` | Verify Slack webhook signatures | `/webhook/slack`, `/webhook/slack/commands` |
| `DISCORD_APPLICATION_ID` | Discord app identifier | Discord client |
| `DISCORD_PUBLIC_KEY` | Verify Discord signatures | `/webhook/discord` |
| `DISCORD_BOT_TOKEN` | Send messages to Discord | Discord client |
| `N8N_URL` | n8n base URL (default: hosted instance) | n8n client |
| `N8N_API_KEY` | n8n API authentication | n8n workflow listing, `/aiui report` |
| `MCP_PROXY_URL` | MCP Proxy base URL | MCP tool execution |
| `REPORT_GITHUB_REPO` | GitHub repo for daily report (e.g. `owner/repo`) | `/aiui report` |
| `REPORT_SLACK_CHANNEL` | Slack channel ID to post reports to | `/aiui report`, scheduled reports |

---

## n8n Integration

The system uses a **hosted n8n instance** at `n8n.srv1041674.hstgr.cloud` (not the local Docker container) for workflow execution.

**Active workflows:**

| Workflow | Nodes | Trigger | What It Does |
|---|---|---|---|
| PR Review Automation | 6 | Webhook | PR data -> AI code review -> GitHub comment -> Slack notification |
| GitHub Push Processor | 5 | Webhook | Push data -> commit summary -> Slack notification |

**MCP n8n server** (`mcp-n8n` container) provides ~20 tools for managing n8n from chat: list workflows, create/activate/deactivate workflows, execute workflows, etc.

---

## Why This is Powerful

**Traditional AI (one-way):**
```
Human -> AI -> Response shown to human only
```

**This Webhook System (three-way):**
```
External Event (GitHub/Slack/Discord) -> AI -> Action (comment, notify, trigger workflow)
Slash Command (user-initiated)        -> AI -> Response + action
Scheduled Job (time-based)            -> AI -> Report + notification
```

This means the AI can:
- Automatically review PRs when they're created
- Respond to questions from Slack or Discord
- Trigger n8n workflows from chat commands
- Check system health on a schedule
- Execute any MCP tool via webhook
- Be extended with new handlers without changing the core
