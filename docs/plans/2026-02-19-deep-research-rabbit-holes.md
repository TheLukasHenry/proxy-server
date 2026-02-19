# Deep Research: Automation Rabbit Holes

**Date:** 2026-02-19
**Purpose:** Deep-dive research for Lukas on all automation rabbit holes — n8n ecosystem, Open WebUI v0.8.x, and chat platform integrations.

---

## TABLE OF CONTENTS

1. [n8n Ecosystem](#1-n8n-ecosystem)
2. [Open WebUI v0.8.x Upgrade](#2-open-webui-v08x-upgrade)
3. [Chat Platform Integrations](#3-chat-platform-integrations)
4. [Recommendations & Priority](#4-recommendations--priority)

---

# 1. N8N ECOSYSTEM

## 1.1 n8n MCP Servers — Full Landscape (Feb 2026)

The n8n MCP ecosystem has **exploded**. There are now 7+ MCP server projects plus n8n's own built-in MCP nodes.

### Tier 1: The Dominant Player

**[czlonkowski/n8n-mcp](https://github.com/czlonkowski/n8n-mcp)** — 13,700 stars
- Ships with a pre-built SQLite database of all 1,084 n8n nodes (537 core + 547 community)
- Tools: Smart Node Search, Essential Properties, Real-World Examples (2,646 pre-extracted configs), Config Validation, AI Workflow Validation
- **Can CREATE workflows from natural language** — Claude says "Build a workflow that monitors RSS and posts to Discord" and gets working JSON
- Also has companion [czlonkowski/n8n-skills](https://github.com/czlonkowski/n8n-skills) — 7 Claude Code skills for building production-ready n8n workflows
- **Gotcha:** README warns "NEVER edit production workflows directly with AI!" Always copy and test first

### Tier 2: Operational / API-First

| Package | Stars | Tools | Best For |
|---------|-------|-------|----------|
| [leonardsellem/n8n-mcp-server](https://github.com/leonardsellem/n8n-mcp-server) | 1,600 | 12 | Pure API wrapper — workflow CRUD + execution management |
| [salacoste/mcp-n8n-workflow-builder](https://github.com/salacoste/mcp-n8n-workflow-builder) | 208 | 17 | Multi-instance support (dev/staging/prod routing) |
| [illuminaresolutions/n8n-mcp-server](https://github.com/illuminaresolutions/n8n-mcp-server) | 78 | many | Enterprise features — project management, security audits |

### The OTHER Direction: n8n AS an MCP Client

**[nerding-io/n8n-nodes-mcp](https://github.com/nerding-io/n8n-nodes-mcp)** — 3,000 stars, 522 forks
- Makes n8n an MCP CLIENT — your n8n workflows can call external MCP servers
- Supports STDIO, HTTP Streamable, SSE connections
- Can be used as a tool within n8n AI Agents (requires `N8N_COMMUNITY_PACKAGES_ALLOW_TOOL_USAGE=true`)
- **Note:** n8n has since added official built-in MCP nodes (see below)

### n8n Built-in MCP Nodes (Official — v1.88.0+)

n8n now has **three official MCP nodes**:

| Node | Direction | What It Does |
|------|-----------|-------------|
| **MCP Client Tool** | n8n -> MCP servers | Connects n8n AI Agents to external MCP servers. SSE + auth (Bearer, header, OAuth2) |
| **MCP Server Trigger** | External -> n8n | Turns any n8n workflow INTO an MCP server. Claude Desktop/Cursor can discover and call it |
| **MCP Client Node** | n8n -> MCP servers | Core node for MCP client operations |

**This is huge:** n8n can now both CONSUME MCP servers AND EXPOSE its own workflows as MCP servers. Bidirectional bridge between n8n and the AI agent ecosystem.

### Which MCP Server to Use?

| Scenario | Recommendation |
|----------|---------------|
| Have Claude Code build n8n workflows | czlonkowski/n8n-mcp (13.7k stars) |
| Programmatically manage workflows from chat | leonardsellem/n8n-mcp-server (1.6k stars) — already deployed as `mcp-n8n` |
| Manage multiple n8n instances | salacoste/mcp-n8n-workflow-builder |
| Make n8n consume external MCP servers | Use official built-in MCP Client Tool node |
| Expose n8n workflows to external AI agents | Use official built-in MCP Server Trigger node |

---

## 1.2 n8n Workflow Templates

### Scale
- **8,344 workflow templates** in the community library
- **5,648 AI-specific templates** (largest and fastest-growing category)
- n8n has **175,000 GitHub stars** and **400+ integrations**

### Specific Templates Found

**Jira -> Slack (6+ templates):**
- [Real-time Error Detection with Slack Alerts and Jira Ticket Creation](https://n8n.io/workflows/6644)
- [AI-powered Bug Triage with OpenAI, Jira and Slack](https://n8n.io/workflows/11697)
- [Track Jira Epic Health with Automated Risk Alerts via Slack](https://n8n.io/workflows/9832)
- [Real-time Uptime Alerts to Jira with Smart Slack On-Call Routing](https://n8n.io/workflows/12060)

**Daily/Weekly Reports (4+ templates):**
- [Generate Multi-Period Financial Reports from Google Sheets with AI Analysis](https://n8n.io/workflows/6679)
- [Create Multi-Sheet Excel Workbooks by Merging Datasets](https://n8n.io/workflows/7955)
- [Synchronize Excel/Google Sheets with Postgres (bi-directional)](https://n8n.io/workflows/8457)

**GitHub PR Code Review (5+ templates):**
- [Automated PR Code Reviews with GitHub, GPT-4, Google Sheets Best Practices](https://n8n.io/workflows/3804) (most mature)
- [Automatic Jest Test Generation for GitHub PRs with Dual AI Review](https://n8n.io/workflows/4013)
- [Automate GitHub PR Linting with Google Gemini AI and Auto-Fix PRs](https://n8n.io/workflows/4073)
- [Review GitHub PRs and Label Them Using OpenAI GPT-4o-mini and Slack](https://n8n.io/workflows/11967)

**SonarQube:** No native SonarQube node exists. No pre-built templates. Must build custom with Webhook + HTTP Request nodes.

---

## 1.3 n8n Workflow Marketplace / Admin Dashboards

### Self-Hosted Template Library — IT'S POSSIBLE

n8n supports custom template servers via `N8N_TEMPLATES_HOST`:

1. Set `N8N_TEMPLATES_HOST` to your custom API URL (default: `https://api.n8n.io`)
2. Implement these endpoints with the same data schema:
   - `GET /templates/categories`
   - `GET /templates/search`
   - `GET /templates/collections`
   - `GET /templates/workflows/{id}`
   - `GET /health`
3. Your n8n instance shows YOUR curated templates instead of the public library

### Open Source Dashboards

- [SolomonChrist/n8nDash](https://github.com/SolomonChrist/n8nDash) — MVP, touchscreen-ready for non-technical users
- n8nDash Pro v1.2.0 — enterprise-grade dashboards inside WordPress
- A community member built a [Coda-based dashboard](https://community.n8n.io/t/theres-finally-a-nice-dashboard-for-your-n8n-instance-built-in-coda/16449)

---

## 1.4 n8n Latest Features (2025-2026)

### Current Version: n8n 2.8.3 (Feb 13, 2026), 2.9.0 beta

### n8n 2.0 (December 2025) — Hardening Release
- **Publish/Save paradigm** — Save preserves edits without changing production; Publish pushes live
- **Task runners enabled by default** — Code nodes run in isolated environments
- **Environment variables blocked** from Code nodes by default
- **SQLite 10x faster** with pooling driver
- **Pyodide Python removed** — only native Python via task runners
- **Breaking:** Deprecated nodes removed, arbitrary command execution disabled by default

### AI/LLM Integration — 70+ AI Nodes
- **LLM providers:** OpenAI, Anthropic Claude, Google Gemini, HuggingFace, Cohere, Mistral, Ollama
- **AI Agent node:** LangChain-powered orchestration with tool use
- **Specialized:** Text Classifier, Sentiment Analysis, Information Extractor, Summarization Chain
- **Vector stores:** Pinecone, Qdrant, Weaviate, Chroma (for RAG)
- **Human-in-the-Loop:** Explicit human approval before AI executes specific tools

### Self-Hosted AI Starter Kit
[n8n-io/self-hosted-ai-starter-kit](https://github.com/n8n-io/self-hosted-ai-starter-kit) — official Docker Compose: n8n + Ollama + Qdrant + PostgreSQL

---

# 2. OPEN WEBUI v0.8.x UPGRADE

## 2.1 Skills Feature (NEW in v0.8.0)

### What Are Skills?

Skills are **reusable AI instruction sets** — pre-written context/instructions that can be attached to models or referenced inline. Think: structured, reusable prompt packages.

**Skills are NOT executable code.** They inject context BEFORE the LLM processes. Tools are what the LLM CALLS during generation.

| Concept | What It Does | Who Invokes It |
|---------|-------------|----------------|
| **Skills** | Inject reusable instructions/context | User (via `$` command) or auto-attached to models |
| **Tools** | Give LLMs callable functions | LLM decides when to call them |
| **Functions** | Extend the platform (Pipes, Filters, Actions) | Platform invokes automatically |
| **Pipes** | Custom model integrations / agent workflows | Appear as selectable models |

### How to Use
- **Create:** Admin navigates to `/workspace/skills`
- **In chat:** Type `$` to get a popup of available Skills, select one to inject
- **Auto-attach:** Skills can be attached to specific models (always included as context)
- **User-selected** (via `$`) injects full content. **Model-attached** shows only name/description (lightweight)

### Can Skills Wrap MCP Servers?

**No, not directly.** Skills are context injection, not executable tool wrappers. [GitHub discussion #19951](https://github.com/open-webui/open-webui/discussions/19951) explicitly rejected MCP as "heavier-weight" compared to Skills. However, a Skill CAN include instructions telling the LLM how to use a specific MCP Tool.

**Lukas's vision of "wrapping MCPs in Skills"** would work like this:
- Create a Skill with detailed instructions about WHEN and HOW to use specific MCP tools
- Attach the Skill to a model
- The model gets rich context about the tools, making it smarter about when to invoke them
- The actual execution still goes through MCP Tools, but the Skill provides the "wisdom"

### Community Status
The feature is 1 week old. The ecosystem is nascent. Admin can control skills sharing per-group (added in v0.8.2).

---

## 2.2 Channels Feature

### What Are Channels?

Persistent, topic-based chat rooms similar to Discord/Slack. Introduced v0.5.0 (beta), enhanced since.

- **Standard channels:** Public or private topic-based rooms
- **Group channels:** Membership-based, users explicitly join
- **Direct Messages:** Private 1-on-1 or multi-user

### How AI Participates
- Type `@model-name` in a channel (e.g., `@gpt-5`) to trigger a response
- AI responses visible to all channel members
- **Multiple models** can be invoked in the same channel
- Models with function calling can autonomously search channels, read messages, search knowledge bases

### Multi-Tenant Support
- Group-based channel access control
- Public vs private visibility
- Write access vs read-only permissions
- `USER_PERMISSIONS_FEATURES_CHANNELS` env var for admin control

### Channel Webhooks
External services can post messages into channels:
- Channel managers can create webhooks without admin privileges
- No authentication required for posting
- Useful for CI/CD, monitoring, notifications

### Bot Support
- [open-webui/bot](https://github.com/open-webui/bot) — experimental, 118 stars, "not production-ready"
- Bots must be externally hosted (separate from Open WebUI)
- Built-in native bot support is **planned but not yet implemented**

---

## 2.3 Full Changelog: v0.7.2 -> v0.8.3

**No versions between v0.7.2 and v0.8.0.** Direct jump.

### v0.8.0 (Feb 12, 2026) — MAJOR
- Analytics Dashboard (model usage, tokens, user activity)
- Skills (experimental)
- Open Responses Protocol (extended thinking, streaming reasoning)
- Redesigned Access Control (multi-group, per-user sharing)
- Message Queuing (keep typing while model generates)
- Prompt Version Control (history, comparison, rollback)
- Native Function Calling Code Execution
- Async Web Search with live citations
- MCP custom SSL certificates
- User identity forwarding to MCP/tool servers
- Per-model built-in tool toggles
- 34% faster authentication

### v0.8.1 (Feb 14) / v0.8.2 (Feb 16) / v0.8.3 (Feb 17)
- Responses API endpoint for vLLM
- Skills sharing permissions per-group
- Chat toggles for built-in tools per-conversation
- Model editing from selector dropdown
- Various bug fixes

### Breaking Changes
- **Database schema changes** — backup before upgrading
- Multi-worker deployments must update ALL instances simultaneously
- Chat message table migration can take significant time with large datasets
- Admin evaluations page moved to `/admin/evaluations/feedback`
- Disabled features now return 403 via API

---

## 2.4 MCP Integration — Two Approaches

### A. Native MCP (HTTP Streamable only)
- Added v0.6.31
- Admin Panel > Settings > External Tools > Add Connection
- **Only works with HTTP Streamable transport** — most community MCP servers use stdio, NOT supported

### B. MCPO Proxy (All transports) — RECOMMENDED
- [mcpo](https://github.com/open-webui/mcpo) — official Open WebUI MCP proxy
- Converts ANY MCP server (stdio, SSE, HTTP Streamable) to OpenAPI HTTP endpoints
- Uses same config format as Claude Desktop (`mcpServers` JSON)
- **This is what we already use** via the `mcp-proxy` service

### v0.8.0 MCP Improvements
- Custom SSL certificates via `AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL`
- User identity and chat context forwarding to MCP/tool servers
- OAuth 2.1 authentication verification fixed

---

## 2.5 Upgrade Guide: v0.7.2 -> v0.8.3

### Pre-Upgrade
1. **Back up database** (critical — schema changes in v0.8.0)
2. **Back up Docker volumes**
3. **Plan maintenance window** — chat_message migration can be slow
4. Set `UVICORN_WORKERS=1` for migration

### Steps
```bash
# 1. Backup
docker compose -f docker-compose.unified.yml stop
cp -r /path/to/data /path/to/data-backup-$(date +%Y%m%d)

# 2. Update image tag to v0.8.3 in docker-compose.unified.yml

# 3. Start (single worker for migration)
docker compose -f docker-compose.unified.yml up -d

# 4. Monitor logs
docker compose -f docker-compose.unified.yml logs -f open-webui

# 5. After migration completes, restore multi-worker if desired
```

### Post-Upgrade
1. Clear browser cache (Ctrl+F5)
2. Enable Channels: Settings > General > toggle "Channels (Beta)"
3. Access Skills at `/workspace/skills`
4. Check Analytics dashboard in admin panel

---

# 3. CHAT PLATFORM INTEGRATIONS

## 3.1 Slack — Deep Dive

### Rate Limit Changes (May 2025)
- Non-Marketplace commercially-distributed apps: `conversations.history` limited to **1 req/min, 15 objects max**
- **Internal/custom apps (like ours) are EXEMPT** — retain 50+ RPM, 1,000 objects
- Mark app as "internal" (not distributed) in Slack app config to be safe
- Existing installations of unlisted distributed apps downgraded **March 3, 2026** (2 weeks from now)

### Block Kit Interactive Components
Next level after plain text responses. Add buttons, modals, dropdowns to slash command responses:
- Response with blocks -> include buttons/menus
- User clicks button -> Slack sends `block_actions` to `/webhook/slack/interactions` (new endpoint needed)
- Button opens modal -> `views.open` API -> `view_submission` payload back
- **Limits:** 50 blocks per message, 100 blocks in modals

### Slack Agents & Assistants API (GA)
New first-party framework for AI bots in Slack's dedicated AI sidebar panel:
- `assistant_thread_started`, `assistant_thread_context_changed` events
- `assistant.threads.setStatus` (thinking indicator)
- `assistant.threads.setSuggestedPrompts` (clickable suggestions)
- Your bot appears alongside Slack AI and Agentforce in the unified AI panel
- Requires Slack plans that support the AI panel

### Slack MCP Server — JUST WENT GA (Feb 17, 2026)
- Official Slack MCP Server lets AI agents search conversations, send messages, create canvases
- Real-Time Search (RTS) API for secure data access without storing customer data
- Partners already integrated: Guru, Manus, Perplexity, Moveworks
- Relevant if your AI needs to read Slack channel history for context

### tuannvm/slack-mcp-client (v2.8.3)
Production-ready Go project bridging Slack to MCP servers:
- LLM providers: OpenAI GPT-4.1, Anthropic Claude 4.5, Ollama
- MCP transports: HTTP, SSE, stdio
- Thread-context awareness, LangChain agent mode, Kubernetes Helm chart

### Socket Mode vs HTTP Mode
HTTP mode is correct for our system. We have a public Caddy proxy, Socket Mode would add unnecessary WebSocket complexity.

---

## 3.2 Discord — Deep Dive

### Interaction Types Beyond Slash Commands
We currently handle types 1 (PING) and 2 (APPLICATION_COMMAND). Discord supports more:

| Type | Name | What It Does |
|------|------|-------------|
| 3 | MESSAGE_COMPONENT | Button clicks, select menus |
| 4 | APPLICATION_COMMAND_AUTOCOMPLETE | Autocomplete suggestions |
| 5 | MODAL_SUBMIT | Modal form submissions |

Adding buttons to responses is straightforward — include `components` array in the edit_original payload.

### Rate Limits
- Global: 50 requests/second per bot
- Invalid requests: 10,000 per 10 minutes per IP (then temp-banned)
- Interaction responses: must respond within 3 seconds
- Deferred followups: 15-minute token validity

### Bot Verification
Required to join 100+ servers. Not an issue for internal use (single server).

### Discord MCP Projects
- [SaseQ/discord-mcp](https://github.com/SaseQ/discord-mcp) — MCP server for Discord (messages, channels, threads, reactions)
- Docker MCP Toolkit for Claude Desktop + Discord integration

---

## 3.3 Microsoft Teams — Deep Dive

### Office 365 Connector Deprecation — FINAL TIMELINE

| Date | Event |
|------|-------|
| Aug 2024 | New connector creation blocked |
| Jan 2025 | Existing connector owners must update URLs |
| Dec 2025 | Bot Framework SDK LTS ends |
| Mar 2026 | Extended deadline for migration |
| **Apr 30, 2026** | **FINAL deadline** (most recent extension) |

**Replacement:** Power Automate Workflows with "When a Teams webhook request is received" trigger. **Only** officially supported way to send webhook notifications into Teams.

### Bot Framework SDK — DEPRECATED (Dec 31, 2025)

**Two replacement SDKs:**

1. **[Microsoft 365 Agents SDK](https://learn.microsoft.com/en-us/microsoft-365/agents-sdk/agents-sdk-overview)** (GA — C#, JS, Python)
   - Build agents for Teams, M365 Copilot, Copilot Studio, web chat, Slack, Facebook
   - Supports MCP and Agent-to-Agent (A2A) communication natively
   - Python package: `microsoft-agents-activity`

2. **[Teams SDK](https://github.com/microsoft/teams-sdk)** (GA JS/C#, Python preview)
   - Simplified Teams-specific SDK with MCP + A2A support

### Simplest Path to Teams Integration

| Method | Effort | Direction | What It Does |
|--------|--------|-----------|-------------|
| Power Automate webhook | 1-2 hrs | Send only | POST Adaptive Card JSON to webhook URL |
| Outgoing Webhook | 3-4 hrs | Bidirectional | @mention -> HTTP POST to your endpoint -> respond |
| Microsoft 365 Agents SDK bot | 1-2 weeks | Full bidirectional | Slash commands, Adaptive Cards, proactive messaging, Copilot |

### Adaptive Cards Version Support

| Version | Status in Teams |
|---------|----------------|
| v1.2 | Full (mobile + desktop) |
| v1.3 | Full desktop, limited mobile |
| v1.4 | Supported for bot-sent cards (RECOMMENDED) |
| v1.5 | Supported but rendering issues reported |
| v1.6 | Not yet supported |

---

## 3.4 Cross-Platform Patterns

### Our Architecture is Already Good
The `CommandRouter` + `CommandContext` pattern is the same "platform adapter" pattern used by enterprise ChatOps systems. The key abstraction — a `respond` callable hiding platform specifics — is correct.

### Unified Bot Frameworks

| Framework | Language | Platforms | Assessment |
|-----------|----------|-----------|-----------|
| Microsoft 365 Agents SDK | C#, JS, Python | Teams, Slack, Facebook, Web | Best for Teams-heavy orgs |
| Botpress | JS/TS | Slack, Teams, Messenger, Telegram | AGPL license concern |
| Rasa | Python | Slack, WhatsApp, Messenger | ML-focused, heavy |
| Errbot | Python | Slack, Discord, XMPP, Telegram | Lightweight but slow development |

**Recommendation:** Continue extending our CommandRouter rather than adopting a framework. It's lighter and fits our webhook-handler architecture better.

### Scaling Consideration
Currently using `asyncio.create_task()` for async processing. Works for single-instance. For horizontal scaling, would need Redis + worker queue. Add a semaphore for safety:

```python
_task_semaphore = asyncio.Semaphore(20)  # max 20 concurrent commands

async def _guarded_execute(router, ctx):
    async with _task_semaphore:
        await router.execute(ctx)
```

---

## 3.5 Webhook Security Best Practices

### Signature Methods Comparison

| Platform | Method | Key Type |
|----------|--------|----------|
| GitHub | HMAC-SHA256 | Shared secret |
| Slack | HMAC-SHA256 (v0 format) | Shared signing secret |
| Discord | Ed25519 | Public key (asymmetric) |
| Teams | HMAC-SHA256 | Base64-encoded shared token |

### Replay Attack Prevention
- Slack: 5-minute timestamp window (already implemented)
- Discord: Timestamp in signed payload (implicit freshness)
- **Add idempotency:** Store processed event IDs in Redis with 30-min TTL, reject duplicates

---

# 4. RECOMMENDATIONS & PRIORITY

## What Changed From Previous Research

| Topic | Previous Finding | New Finding |
|-------|-----------------|-------------|
| n8n MCP | Recommended leonardsellem (1.6k stars) | czlonkowski (13.7k stars) is far more powerful — creates workflows from natural language |
| n8n MCP nodes | Community package only | n8n has OFFICIAL built-in MCP nodes now (bidirectional) |
| n8n version | Assumed recent | Now at v2.8.3 with major 2.0 hardening release |
| Open WebUI Skills | Unknown | Skills are context injection, NOT code execution. Can guide MCP usage but not wrap it |
| Open WebUI Channels | Unknown | Working feature with @model mentions, webhooks, group access control |
| Open WebUI bots | Unknown | Experimental, not production-ready. External hosting required |
| Slack MCP | tuannvm project | Official Slack MCP Server went GA Feb 17, 2026 |
| Teams connectors | Deprecated March 2026 | Extended to April 30, 2026. Two new SDKs replace Bot Framework |
| Bot Framework | Still active | LTS ended Dec 31, 2025. Replaced by M365 Agents SDK + Teams SDK |

## Updated Priority Timeline

| Priority | Task | Effort | Value | New Insight |
|----------|------|--------|-------|-------------|
| **1** | Upgrade Open WebUI to v0.8.3 | 2-4 hrs | HIGH | Unlocks Skills, Channels, Analytics, better MCP |
| **2** | Create Skills for MCP guidance | 1-2 days | HIGH | Skills = instructions teaching LLM WHEN/HOW to use tools |
| **3** | Set up Channels + @model mentions | 2-4 hrs | HIGH | Built-in team collaboration without external Slack/Discord |
| **4** | Add Block Kit / interactive buttons | 1-2 days | MEDIUM | Richer Slack responses (buttons, modals) |
| **5** | Deploy czlonkowski/n8n-mcp for Claude Code | Half day | HIGH | Create n8n workflows from natural language |
| **6** | Use n8n MCP Server Trigger | 1-2 days | HIGH | Expose n8n workflows as MCP tools for any AI agent |
| **7** | Explore Slack Agents & Assistants API | 1-2 days | MEDIUM | Appear in Slack's AI sidebar panel |
| **8** | Teams Power Automate webhook (send only) | 1-2 hrs | MEDIUM | Quick notifications to Teams |
| **9** | Self-hosted n8n template library | 3-5 days | MEDIUM | Curated team-specific templates |
| **10** | Teams Outgoing Webhook (bidirectional) | 3-4 hrs | LOW | @mention -> AI response in Teams |

## Key Sources

- [czlonkowski/n8n-mcp](https://github.com/czlonkowski/n8n-mcp) (13.7k stars)
- [n8n Workflow Templates](https://n8n.io/workflows/) (8,344 templates)
- [n8n MCP Server Trigger Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-langchain.mcptrigger/)
- [Open WebUI v0.8.0 Release](https://github.com/open-webui/open-webui/releases/tag/v0.8.0)
- [Open WebUI Channels Docs](https://docs.openwebui.com/features/ai-knowledge/channels/)
- [Open WebUI Skills PR #21312](https://github.com/open-webui/open-webui/pull/21312)
- [mcpo (MCP Proxy)](https://github.com/open-webui/mcpo)
- [Slack MCP GA Announcement](https://docs.slack.dev/changelog/2026/02/17/slack-mcp/)
- [Slack Agents & Assistants](https://docs.slack.dev/ai/)
- [Microsoft 365 Agents SDK](https://learn.microsoft.com/en-us/microsoft-365/agents-sdk/agents-sdk-overview)
- [Teams SDK](https://github.com/microsoft/teams-sdk)
- [n8n 2.0 Blog](https://blog.n8n.io/introducing-n8n-2-0/)
