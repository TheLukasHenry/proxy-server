# Webhook-Driven PR Automation Design

**Date:** 2026-02-17
**Status:** Approved
**Approach:** A — Pure n8n Workflow

## Problem

The client expects event-driven automation where GitHub PR events automatically trigger workflows without human prompts. The current demo showed prompt-driven queries (user types in Open WebUI → AI fetches data), which is not webhook automation.

## Goal

When a PR is opened on `TheLukasHenry/proxy-server`, the system automatically:
1. Performs an AI code review
2. Posts the review as a GitHub PR comment
3. Sends a Slack notification to `#automation`

No human prompt required. Fully event-driven.

## Architecture

```
GitHub (PR opened)
  │
  ▼ POST https://ai-ui.coolestdomain.win/webhook/github
  │
Caddy (:80)
  │ /webhook/* → webhook-handler:8086 (bypasses API Gateway)
  ▼
webhook-handler:8086
  │ 1. Verify HMAC-SHA256 signature
  │ 2. Parse X-GitHub-Event: pull_request
  │ 3. Extract: repo, pr_number, action, title, author, diff_url
  │ 4. Forward to n8n (fire-and-forget, return 200 to GitHub)
  ▼ POST n8n:5678/webhook/pr-review
  │
n8n Workflow: "PR Review Automation"
  │
  ├─ Node 1: Webhook Trigger (POST /webhook/pr-review)
  ├─ Node 2: HTTP Request — Fetch PR diff from GitHub API
  ├─ Node 3: HTTP Request — AI code review via Open WebUI
  ├─ Node 4: HTTP Request — Post review as GitHub PR comment
  └─ Node 5: HTTP Request — Post summary to Slack #automation
```

## Design Decisions

### webhook-handler validates, n8n orchestrates

- webhook-handler ONLY validates the HMAC signature and forwards the normalized payload to n8n
- n8n does ALL the work: fetch diff, AI review, GitHub comment, Slack message
- No duplicate processing between webhook-handler and n8n
- The existing `_handle_pull_request` logic in webhook-handler is refactored to delegate to n8n instead of doing AI review + comment itself

### Why n8n (not pure Python)

- Client specifically wants to see webhook-driven n8n automation
- n8n provides visual workflow editor — great for demos and client trust
- Execution history is visible (each node, data flow, timing)
- Non-developers can modify the workflow (add Slack channels, change AI prompt, etc.)

### Why keep webhook-handler as entry point (not direct n8n webhook)

- n8n cannot natively verify GitHub HMAC-SHA256 signatures
- webhook-handler provides consistent auth/validation layer for all external webhooks
- Single external URL for all GitHub events (handler routes to different n8n workflows per event type)

## Component Changes

### A. webhook-handler/handlers/github.py

Refactor `_handle_pull_request()`:
- Remove: AI review via Open WebUI, posting GitHub comment (n8n does this now)
- Keep: HMAC verification, payload extraction
- Add: Forward to n8n `pr-review` workflow with normalized payload

```python
async def _handle_pull_request(self, payload, delivery_id):
    action = payload.get("action")
    if action not in ("opened", "synchronize"):
        return {"status": "ignored", "reason": f"PR action '{action}' not handled"}

    pr = payload["pull_request"]
    repo = payload["repository"]["full_name"]

    n8n_payload = {
        "repo": repo,
        "pr_number": pr["number"],
        "action": action,
        "title": pr["title"],
        "author": pr["user"]["login"],
        "diff_url": pr["diff_url"],
        "html_url": pr["html_url"],
        "base_branch": pr["base"]["ref"],
        "head_branch": pr["head"]["ref"],
        "body": pr.get("body", ""),
    }

    await self.n8n_client.trigger_workflow("pr-review", n8n_payload)
    return {"status": "forwarded_to_n8n", "workflow": "pr-review"}
```

### B. n8n Workflow: PR Review Automation

5-node workflow saved as `n8n-workflows/pr-review-automation.json`:

| Node | Type | Config |
|---|---|---|
| Webhook Trigger | webhook | `POST /webhook/pr-review`, responds immediately |
| Fetch PR Diff | httpRequest | `GET https://api.github.com/repos/{{repo}}/pulls/{{pr_number}}/files` with Bearer GITHUB_TOKEN |
| AI Code Review | httpRequest | `POST` Open WebUI `/api/chat/completions` with system prompt + diff as user message |
| Post GitHub Comment | httpRequest | `POST https://api.github.com/repos/{{repo}}/issues/{{pr_number}}/comments` with review body |
| Slack Notification | httpRequest | `POST https://slack.com/api/chat.postMessage` to #automation with PR summary + review excerpt |

### C. GitHub Webhook Configuration

On `TheLukasHenry/proxy-server` Settings → Webhooks:
- **Payload URL:** `https://ai-ui.coolestdomain.win/webhook/github`
- **Content type:** `application/json`
- **Secret:** Value of `GITHUB_WEBHOOK_SECRET` from `.env`
- **Events:** Pull requests, Pushes

### D. No changes needed

- Caddy (already routes `/webhook/*` to webhook-handler)
- Docker Compose (all services already running)
- MCP Proxy (not involved in this flow)
- API Gateway (webhook traffic bypasses it)

## Error Handling

- webhook-handler returns 200 to GitHub immediately after forwarding (fire-and-forget)
- n8n workflow uses `onError: "continueRegularOutput"` on all nodes
- If n8n trigger fails, webhook-handler logs the error but doesn't block
- Optional: add an Error Trigger node in n8n to post failures to Slack

## Security

- HMAC-SHA256 verification stays in webhook-handler (n8n can't do this natively)
- GITHUB_TOKEN used by n8n to fetch diffs and post comments
- OPENWEBUI_API_KEY used by n8n to call chat completions
- SLACK_BOT_TOKEN used by n8n to post messages
- All secrets passed as n8n credentials or environment variables

## Demo Impact

1. Developer opens a PR — no other action needed
2. Within 10-30 seconds:
   - AI review comment appears on the GitHub PR
   - Slack notification appears in #automation
3. Client opens n8n UI → sees the workflow, execution history, data flowing through each node
4. This proves: webhook-driven, event-triggered, no human prompt required
