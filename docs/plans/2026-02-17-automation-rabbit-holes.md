# Automation Rabbit Holes — Research for Lukas

**Date:** 2026-02-17
**Context:** Lukas wants to know what automation features to explore next.

Each topic covers: what it is, how it integrates, effort, and value.

---

## 1. n8n MCP Server

**What:** An MCP server that lets Claude (or any LLM) create, edit, activate, and manage n8n workflows programmatically. Packages like `@nerdondon/n8n-mcp-server` expose n8n's API as MCP tools.

**Integration:** Add as a new STDIO or LOCAL server in `tenants.py`. Deploy via mcpo wrapper (same pattern as GitHub/Notion MCP servers). The LLM could then say "create a workflow that triggers on Slack messages and posts to Linear."

**Effort:** Medium (1-2 days). Container setup is straightforward (proven pattern). Main work is testing the n8n API tool coverage.

**Value:** High. Enables AI-driven workflow creation — users describe what they want in chat, the LLM builds and deploys the n8n workflow automatically.

---

## 2. More n8n Workflow Templates

**What:** Pre-built n8n workflows for common automation patterns.

**Templates to build:**
- **GitHub PR → SonarQube scan → comment results** — On PR open, trigger SonarQube analysis, post quality gate results as PR comment
- **Scheduled daily report** — Every noon: collect metrics from all services, generate Excel report, post summary to Slack
- **Jira issue → Slack notification** — New Jira issues auto-posted to relevant Slack channels based on project/priority
- **Weekly digest** — Summarize all GitHub activity, n8n executions, and MCP usage into a weekly email/Slack message

**Integration:** Deploy via `scripts/deploy-n8n-github-workflow.ps1` pattern (already exists). Each template is a JSON workflow imported via n8n API.

**Effort:** Small per template (2-4 hours each). The deployment mechanism already exists.

**Value:** Medium-High. Each template saves hours of manual work per week. The daily report template is highest value for Lukas.

---

## 3. Microsoft Teams Webhook (Phase 2C)

**What:** Add a Teams incoming webhook handler to `webhook-handler`, similar to the existing Slack handler. Receives Teams messages and can trigger workflows.

**Integration:** Add `/webhook/teams` endpoint in webhook-handler. Two options:
- **Simple:** Use Teams Incoming Webhook connector (just HTTP POST to/from a URL). Effort: small.
- **Full:** Use Microsoft Bot Framework for rich interactions (cards, buttons, threads). Effort: large.

**Effort:** Medium (2-3 days for simple, 1-2 weeks for full Bot Framework).

**Value:** Medium. Depends on whether the team uses Teams. If they do, it's high value since most enterprise communication happens there.

---

## 4. Discord Webhook (Phase 3D)

**What:** Add a Discord webhook handler. Discord webhooks are simpler than Slack/Teams — just HTTP POST to a webhook URL.

**Integration:** Add `/webhook/discord` endpoint in webhook-handler. Discord's API is straightforward:
- Incoming: Discord sends JSON with message content
- Outgoing: POST to Discord webhook URL with embed objects

**Effort:** Small (1 day). Discord's webhook format is the simplest of all chat platforms.

**Value:** Low-Medium. Useful if the team uses Discord for dev communication. Good for side-project/community notifications.

---

## 5. Two-Way Slack

**What:** Upgrade the current one-way Slack integration (webhook receives events) to full two-way interaction:
- **Slash commands:** `/mcp search repos node` — users invoke MCP tools directly from Slack
- **Interactive buttons:** Approve/deny actions, select options from dropdowns
- **Thread replies:** Bot responds in threads with tool results

**Integration:** Requires Slack App Manifest update to register slash commands and interactivity URL. Add new endpoints in webhook-handler:
- `POST /webhook/slack/commands` — Handle slash commands
- `POST /webhook/slack/interactions` — Handle button clicks and selections

**Effort:** Large (1-2 weeks). Slash command handling is moderate, but interactive components (buttons, modals) require managing Slack's callback protocol and state management.

**Value:** High. Users can interact with MCP tools without leaving Slack. This is the "ChatOps" vision — everything from Slack.

---

## 6. Workflow Marketplace in Admin Portal

**What:** Extend the admin portal (`/mcp-admin`) to show available n8n workflows, let admins enable/disable them, trigger test runs, and view execution history.

**Integration:** Add new admin portal pages:
- **Workflow catalog** — List all n8n workflows with status, last run, success rate
- **Enable/disable** — Toggle workflows on/off without opening n8n
- **Test run** — Trigger a workflow with sample data, show results inline
- **Execution log** — Show recent executions with success/failure, duration, errors

Requires new API endpoints in webhook-handler or mcp-proxy that call n8n's API.

**Effort:** Large (2-3 weeks). UI work for admin portal, API integration with n8n execution API, execution log storage.

**Value:** High for operations. Gives Lukas and admins visibility into all automations from one place without needing to open n8n directly.

---

## Priority Recommendation

| Priority | Topic | Effort | Value | Why |
|----------|-------|--------|-------|-----|
| 1 | n8n workflow templates | Small | High | Quick wins, immediate productivity gains |
| 2 | n8n MCP Server | Medium | High | AI-driven workflow creation is a differentiator |
| 3 | Two-way Slack | Large | High | ChatOps vision, biggest UX improvement |
| 4 | Teams webhook | Medium | Medium | Enterprise requirement, depends on team usage |
| 5 | Workflow marketplace | Large | High | Operations visibility, but can wait |
| 6 | Discord webhook | Small | Low | Nice-to-have, lowest priority |
