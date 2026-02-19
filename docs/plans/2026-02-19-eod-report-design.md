# End-of-Day Report Command — Design

**Date:** 2026-02-19
**Status:** Approved
**Approach:** A — CommandRouter extension (all-in-one)

---

## Overview

Add a `/aiui report` slash command and a scheduled cron job that generates a daily activity summary from GitHub commits, n8n workflow executions, and service health data. The raw data is sent to the LLM for a human-readable AI summary, then delivered to both the command invoker and a configured Slack channel.

Also wires up the existing `daily_health_report()` to post to Slack (Task 3).

---

## Data Sources

### 1. GitHub Commits
- **API:** `GET /repos/{owner}/{repo}/commits?since={today_00:00Z}&until={now}`
- **Repo:** `REPORT_GITHUB_REPO` env var (default: `TheLukasHenry/proxy-server`)
- **Extracts:** short SHA, author name, first line of commit message, timestamp
- **Cap:** 50 commits max
- **Fallback:** If `GITHUB_TOKEN` is not set, skip with "GitHub data unavailable"

### 2. n8n Workflow Executions
- **API:** `GET /api/v1/executions?limit=50` (filter to today client-side)
- **Extracts:** workflow name, status (success/error/running), started/finished timestamps
- **Requires:** `N8N_API_KEY` (already configured)
- **Fallback:** If API key not set, skip with "n8n data unavailable"

### 3. Service Health
- **Reuse:** Existing `_check_service_health()` from `scheduler.py`
- **Services:** Open WebUI, MCP Proxy, n8n, webhook-handler
- **Returns:** service name, status (healthy/unhealthy/unreachable), status code

---

## AI Summarization

**System prompt:**
```
You are a concise daily report generator for a software team.
Summarize the day's activity from GitHub commits, n8n workflow executions,
and service health data. Be brief — bullet points, not paragraphs.
Highlight anything notable: failures, large changes, unusual patterns.
```

**User message template:**
```
Generate an end-of-day report for {date}.

## GitHub Commits ({count})
{commit_list}

## n8n Workflow Executions ({count})
{execution_list}

## Service Health
{health_results}
```

**Edge cases:**
- No commits → "No commits today" in data, AI notes it
- n8n API key missing → skip section, note unavailable
- GitHub token missing → skip section, note unavailable
- AI fails → fall back to raw structured data as plain text

---

## Delivery

### Slash Command (`/aiui report`)
1. `CommandRouter._handle_report(ctx)` gathers all 3 data sources in parallel via `asyncio.gather()`
2. Builds prompt, sends to AI via `openwebui_client.chat_completion()`
3. Posts AI summary to `ctx.respond()` (visible to command invoker)
4. If `REPORT_SLACK_CHANNEL` + `slack_client` configured, also posts to that channel

### Scheduled Cron (5:30 PM daily)
- Calls same gather + AI logic
- Posts to `REPORT_SLACK_CHANNEL` only (no command reply)

### Health Report -> Slack (Task 3)
- `daily_health_report()` gets optional `slack_client` param
- After logging, if slack_client + channel configured, posts health summary to Slack

---

## New Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `REPORT_GITHUB_REPO` | `TheLukasHenry/proxy-server` | GitHub repo for commit data |
| `REPORT_SLACK_CHANNEL` | (empty) | Slack channel ID for report posting |

---

## Files Changed

| File | Change |
|---|---|
| `config.py` | Add `report_github_repo` and `report_slack_channel` settings |
| `clients/github.py` | Add `get_commits_since(owner, repo, since)` method |
| `clients/n8n.py` | Add `get_recent_executions(limit)` method |
| `handlers/commands.py` | Add `report` to known_commands, add `_handle_report()` (~80 lines) |
| `scheduler.py` | Wire slack_client into `daily_health_report()`, add `daily_eod_report` cron job |
| `main.py` | Pass slack_client to scheduler functions, register EOD cron job |
| `docker-compose.unified.yml` | Add 2 new env vars to webhook-handler service |

---

## Flow Diagram

```
/aiui report (Slack or Discord)
  -> CommandRouter._handle_report()
  -> asyncio.gather(github_commits, n8n_executions, health_checks)
  -> build prompt -> AI summary
  -> respond to user + post to #daily-report channel

Cron (5:30 PM daily)
  -> same gather + AI logic
  -> post to #daily-report channel only

Cron (12:00 PM daily — existing)
  -> daily_health_report()
  -> log results + post to #daily-report channel (NEW)
```
