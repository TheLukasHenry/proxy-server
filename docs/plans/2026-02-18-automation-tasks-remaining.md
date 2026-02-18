# Automation Tasks Remaining

**Date:** 2026-02-18
**Status:** Backlog
**Context:** Features not yet built, identified after completing slash commands, MCP Proxy verification, and n8n unification.

---

## What's NOT Yet Built

### 1. End-of-Day Report Command
- **Priority:** HIGH
- **Effort:** 2-4 hrs
- **Notes:** Lukas specifically asked for this — `/aiui report` that summarizes daily activity from GitHub commits, n8n executions, and optionally posts to Slack

### 2. More n8n Workflow Templates
- **Priority:** MEDIUM
- **Effort:** 1-8 hrs each
- **Notes:** Jira→Slack (1hr), Daily Excel Report (2-4hrs), Weekly Digest (4-8hrs)

### 3. Health Report → Slack Posting
- **Priority:** MEDIUM
- **Effort:** 1-2 hrs
- **Notes:** `daily_health_report()` only logs — doesn't post to Slack yet

### 4. Microsoft Teams Integration
- **Priority:** LOW
- **Effort:** 3-4 hrs
- **Notes:** Send-only is easy; receive uses Power Automate (old connectors die March 2026)

### 5. Workflow Marketplace in Admin Portal
- **Priority:** LOW
- **Effort:** 3-5 days
- **Notes:** Custom page on n8n REST API — no open-source solution

### 6. Interactive Slack Buttons (Phase 2)
- **Priority:** LOW
- **Effort:** 2-3 days
- **Notes:** `/webhook/slack/interactions` for block_actions, modals

### 7. More CommandRouter Subcommands
- **Priority:** LOW
- **Effort:** 1-2 hrs
- **Notes:** `report`, `workflows` (list all), custom commands

---

## Next Phase — Lukas's New Direction (from 2026-02-18 voice notes)

> After the current automation tasks are done, Lukas wants to shift focus to Open WebUI's new capabilities.

### 8. Upgrade Open WebUI to v0.8.3
- **Priority:** HIGH (next after current tasks)
- **Effort:** 2-4 hrs (upgrade + regression testing)
- **Notes:** Currently on v0.7.2. The v0.8.3 release introduces **Skills** and **Channels** — two features Lukas is very excited about. This upgrade is a prerequisite for tasks 9-11 below.

### 9. Research & Build Open WebUI Skills
- **Priority:** HIGH
- **Effort:** Research 2-4 hrs, build 1-2 days
- **Notes:** Lukas sees Skills as better than raw MCP tools — more concise, better context, more flexible. His specific idea: **wrap existing MCP servers in Skills** so the AI gets richer context about when/how to use them. He compared it to how skills work in Claude Code and wants "something close to it" in Open WebUI. This solves the problem of gpt-5 not knowing how to invoke MCP tools without hand-holding.
- **Example use cases Lukas described:**
  - A product owner asks "Is this latest PR secure?" → a Skill triggers, fetches PR data, runs security analysis, reports back
  - A software engineer builds a custom report Skill once → non-technical people can just run it anytime

### 10. Explore Open WebUI Channels Feature
- **Priority:** MEDIUM
- **Effort:** Research 2-3 hrs, configure 2-4 hrs
- **Notes:** Open WebUI 0.8.3 has built-in Slack/Discord-like **Channels** in the left sidebar (above chats). Lukas wants this explored for multi-tenant use:
  - Different channels for different tenants
  - Users can tag bots with slash commands inside channels
  - Users can message each other
  - Bots trigger skills/automations from within channels
  - Could potentially replace or complement the external Slack/Discord integration we built

### 11. Wrap MCPs in Skills for Non-Technical Users
- **Priority:** MEDIUM
- **Effort:** 3-5 days
- **Notes:** The big vision — connect Skills + Channels + Bots + Automations so non-technical users (product owners, stakeholders) can self-serve. A software engineer builds a Skill once, and anyone can invoke it from a channel. Lukas described this as "really strong for people" and the key to making AIUI accessible beyond developers.

---

## Priority Timeline

| When | What |
|------|------|
| **Done** | Slash commands, MCP Proxy, n8n unification, PR automation |
| **Now** | Send updated `.env` to Lukas via WhatsApp, he tests live |
| **Next** | Tasks 1-3 (end-of-day report, n8n templates, health→Slack) |
| **After that** | Task 8 (upgrade to v0.8.3) |
| **Then** | Tasks 9-11 (Skills, Channels, MCP-in-Skills) |
| **Backlog** | Tasks 4-7 (Teams, marketplace, interactive Slack, more subcommands) |

---

## Key Architecture Insight

The system has **three automation patterns**:

1. **Event-driven (webhooks):** GitHub/Slack/Discord → webhook-handler → n8n → actions (fully automatic)
2. **Chat-driven (slash commands):** User types `/aiui ask|workflow|status` → CommandRouter → AI/n8n (user-initiated)
3. **Scheduled (cron):** APScheduler → health checks / n8n monitoring (time-based)

Lukas's vision is all three working together — the "end-of-day report" could be triggered by a slash command (`/aiui report`) OR scheduled as a cron job, pulling data from GitHub commits + n8n executions and posting a summary to Slack.
