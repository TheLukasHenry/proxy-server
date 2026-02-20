# Webhook-Driven PR Automation — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** When a PR is opened on GitHub, automatically trigger an n8n workflow that performs AI code review, posts the review as a GitHub PR comment, and sends a Slack notification — fully event-driven, no human prompt required.

**Architecture:** webhook-handler validates GitHub HMAC signature and forwards a normalized payload to n8n. n8n orchestrates everything: fetches PR diff from GitHub API, calls Open WebUI for AI review, posts review as GitHub comment, sends Slack notification.

**Tech Stack:** Python/FastAPI (webhook-handler), n8n (workflow JSON), GitHub API, Open WebUI chat completions API, Slack API

**Design Doc:** `docs/plans/2026-02-17-webhook-driven-pr-automation-design.md`

---

### Task 1: Create the n8n PR Review Workflow JSON

**Files:**
- Create: `n8n-workflows/pr-review-automation.json`
- Reference: `n8n-workflows/github-push-processor.json` (existing pattern to follow)

**Step 1: Create the workflow JSON file**

Create `n8n-workflows/pr-review-automation.json` with 5 nodes. Follow the exact same JSON structure as the existing `github-push-processor.json`.

The workflow nodes:

**Node 1 — Webhook Trigger:**
- Type: `n8n-nodes-base.webhook`, typeVersion 2
- Path: `pr-review`
- Method: POST
- Response mode: `responseNode` (so the last node sends the HTTP response)
- Position: [220, 300]

**Node 2 — Fetch PR Diff:**
- Type: `n8n-nodes-base.httpRequest`, typeVersion 4.2
- Method: GET
- URL: `https://api.github.com/repos/{{ $json.body.repo }}/pulls/{{ $json.body.pr_number }}/files`
- Headers:
  - `Authorization`: `Bearer {{ $env.GITHUB_TOKEN }}`  (n8n env variable)
  - `Accept`: `application/vnd.github+json`
  - `X-GitHub-Api-Version`: `2022-11-28`
- Position: [440, 300]

**Node 3 — AI Code Review:**
- Type: `n8n-nodes-base.httpRequest`, typeVersion 4.2
- Method: POST
- URL: `http://open-webui:8080/api/chat/completions`
- Headers:
  - `Authorization`: `Bearer {{ $env.OPENWEBUI_API_KEY }}`  (n8n env variable)
  - `Content-Type`: `application/json`
- Body (JSON): Build a chat completions request with:
  - model: `gpt-4-turbo`
  - messages:
    - system: "You are a senior code reviewer. Review this pull request diff. Focus on: bugs, security issues, performance concerns, code style, and suggestions. Be concise. Format as markdown."
    - user: Compose from data: PR title (`$('Webhook').item.json.body.title`), author, base→head branches, and the diff files from the previous node (`$json` from Fetch PR Diff — format as a summary of filenames + patches, limited to 8000 chars to avoid token limits)
- Position: [660, 300]

**Node 4 — Post GitHub Comment:**
- Type: `n8n-nodes-base.httpRequest`, typeVersion 4.2
- Method: POST
- URL: `https://api.github.com/repos/{{ $('Webhook').item.json.body.repo }}/issues/{{ $('Webhook').item.json.body.pr_number }}/comments`
- Headers:
  - `Authorization`: `Bearer {{ $env.GITHUB_TOKEN }}`
  - `Accept`: `application/vnd.github+json`
- Body: `{"body": "🤖 **AI Code Review**\n\n{{ ai_review_content }}\n\n---\n*Automated review by n8n + Open WebUI*"}`
  - Extract `ai_review_content` from the AI node response: `$json.choices[0].message.content`
- Position: [880, 300]

**Node 5 — Slack Notification:**
- Type: `n8n-nodes-base.httpRequest`, typeVersion 4.2
- Method: POST
- URL: `https://slack.com/api/chat.postMessage`
- Headers:
  - `Authorization`: `Bearer {{ $env.SLACK_BOT_TOKEN }}`
  - `Content-Type`: `application/json`
- Body: JSON with `channel` (use `#automation` or a configurable channel ID) and `text` containing:
  - PR title, author, repo, link
  - A short excerpt of the AI review (first 500 chars)
- Position: [1100, 300]

**Node 6 — Respond to Webhook:**
- Type: `n8n-nodes-base.respondToWebhook`, typeVersion 1.1
- Response code: 200
- Position: [1320, 300]

**Connections:** Linear chain: Webhook → Fetch PR Diff → AI Code Review → Post GitHub Comment → Slack Notification → Respond to Webhook

**Important n8n JSON details (copy from github-push-processor.json):**
- `settings.executionOrder`: `"v1"`
- All nodes need `onError: "continueRegularOutput"` in the top level of each node object
- The webhook node needs `webhookId` set to `"pr-review"`

**Step 2: Validate the workflow JSON is syntactically correct**

```bash
cd "C:\Users\alama\Desktop\Lukas Work\IO"
python -c "import json; json.load(open('n8n-workflows/pr-review-automation.json')); print('Valid JSON')"
```

Expected: `Valid JSON`

**Step 3: Commit**

```bash
git add n8n-workflows/pr-review-automation.json
git commit -m "feat: add n8n PR review automation workflow

5-node pipeline: Webhook → Fetch PR Diff → AI Review → GitHub Comment → Slack"
```

---

### Task 2: Refactor webhook-handler to delegate PR events to n8n

**Files:**
- Modify: `webhook-handler/handlers/github.py` (lines 122-187 — `_handle_pull_request_event` method)

**Step 1: Refactor `_handle_pull_request_event` to forward to n8n**

Replace the existing `_handle_pull_request_event` method (lines 122-187) with a slim version that only extracts data and forwards to n8n. Remove all the OpenWebUI + GitHub comment logic from this method — n8n handles that now.

New implementation:

```python
async def _handle_pull_request_event(self, payload: dict[str, Any]) -> dict[str, Any]:
    """Handle pull request events — forward to n8n for automated review."""
    action = payload.get("action")

    if action not in ("opened", "synchronize"):
        logger.info(f"Ignoring PR action: {action}")
        return {"success": True, "message": f"PR action '{action}' not handled"}

    pr = payload.get("pull_request", {})
    repo = payload.get("repository", {})
    repo_full_name = repo.get("full_name", "")

    if "/" not in repo_full_name:
        logger.error(f"Invalid repository name: {repo_full_name}")
        return {"success": False, "error": "Invalid repository name"}

    pr_number = pr.get("number")
    title = pr.get("title", "")
    logger.info(f"Forwarding PR #{pr_number}: {title} (action: {action}) to n8n")

    # Build normalized payload for n8n workflow
    n8n_payload = {
        "repo": repo_full_name,
        "pr_number": pr_number,
        "action": action,
        "title": title,
        "author": pr.get("user", {}).get("login", "unknown"),
        "diff_url": pr.get("diff_url", ""),
        "html_url": pr.get("html_url", ""),
        "base_branch": pr.get("base", {}).get("ref", ""),
        "head_branch": pr.get("head", {}).get("ref", ""),
        "body": pr.get("body", "") or "",
    }

    # Forward to n8n (fire-and-forget style, but we await for logging)
    if self.n8n:
        try:
            n8n_result = await self.n8n.trigger_workflow("pr-review", n8n_payload)
            if n8n_result:
                logger.info(f"n8n pr-review workflow completed for PR #{pr_number}")
                return {
                    "success": True,
                    "message": "PR forwarded to n8n for automated review",
                    "pr_number": pr_number,
                    "n8n_result": n8n_result,
                }
            else:
                logger.warning(f"n8n pr-review returned no result for PR #{pr_number}")
                return {
                    "success": True,
                    "message": "PR forwarded to n8n (no response — workflow may not be active)",
                    "pr_number": pr_number,
                }
        except Exception as e:
            logger.error(f"Failed to forward PR #{pr_number} to n8n: {e}")
            return {
                "success": False,
                "error": f"Failed to trigger n8n workflow: {e}",
                "pr_number": pr_number,
            }
    else:
        logger.warning("n8n client not configured, cannot forward PR event")
        return {
            "success": False,
            "error": "n8n client not configured",
            "pr_number": pr_number,
        }
```

**Key changes:**
- Removed: `self.openwebui.analyze_pull_request()` call
- Removed: `self.github.get_pr_files()` call
- Removed: `self.github.post_issue_comment()` call
- Added: `self.n8n.trigger_workflow("pr-review", n8n_payload)` with proper error handling
- The method still validates the action and repo name before forwarding

**Step 2: Verify the webhook-handler still imports cleanly**

```bash
cd "C:\Users\alama\Desktop\Lukas Work\IO\webhook-handler"
python -c "from handlers.github import GitHubWebhookHandler; print('Import OK')"
```

Expected: `Import OK` (no syntax errors)

**Step 3: Commit**

```bash
git add webhook-handler/handlers/github.py
git commit -m "refactor: delegate PR review to n8n instead of handling in-process

webhook-handler now only validates HMAC + forwards to n8n pr-review workflow.
n8n handles: fetch diff, AI review, GitHub comment, Slack notification."
```

---

### Task 3: Add n8n environment variables for secrets

**Files:**
- Modify: `docker-compose.unified.yml` — n8n service environment section
- Modify: `.env.example` — document the new variables

**Step 1: Add environment variables to n8n service in docker-compose.unified.yml**

Find the `n8n` service in `docker-compose.unified.yml`. Add these environment variables so n8n workflows can access secrets via `$env.VARIABLE_NAME`:

```yaml
    environment:
      # ... existing variables ...
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - OPENWEBUI_API_KEY=${OPENWEBUI_API_KEY}
      - SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN}
```

These are the secrets the n8n workflow needs:
- `GITHUB_TOKEN` — to fetch PR diffs and post comments via GitHub API
- `OPENWEBUI_API_KEY` — to call Open WebUI chat completions for AI review
- `SLACK_BOT_TOKEN` — to post messages to Slack

**Step 2: Add Slack channel config to .env.example**

Add a new variable under the n8n section:

```
# Slack channel for n8n automation notifications
SLACK_AUTOMATION_CHANNEL=#automation
```

**Step 3: Commit**

```bash
git add docker-compose.unified.yml .env.example
git commit -m "feat: pass GitHub/OpenWebUI/Slack secrets to n8n for workflow use"
```

---

### Task 4: Configure GitHub webhook on TheLukasHenry/proxy-server

**Files:** None (GitHub UI configuration)

**Step 1: Get the webhook secret from .env**

```bash
cd "C:\Users\alama\Desktop\Lukas Work\IO"
grep GITHUB_WEBHOOK_SECRET .env
```

Note the secret value.

**Step 2: Configure the webhook in GitHub**

1. Go to https://github.com/TheLukasHenry/proxy-server/settings/hooks
2. Click "Add webhook"
3. Fill in:
   - **Payload URL:** `https://ai-ui.coolestdomain.win/webhook/github`
   - **Content type:** `application/json`
   - **Secret:** (the value from Step 1)
   - **SSL verification:** Enable
4. Under "Which events would you like to trigger this webhook?":
   - Select "Let me select individual events"
   - Check: **Pull requests**
   - Check: **Pushes** (already handled by existing github-push workflow)
   - Uncheck everything else
5. Make sure "Active" is checked
6. Click "Add webhook"

**Step 3: Verify the webhook delivered a ping**

After adding, GitHub sends a `ping` event. Check the webhook's "Recent Deliveries" tab:
- Should show a delivery with response code `200`
- Response body should contain `"message": "Pong!"`

This confirms the full chain works: GitHub → Caddy → webhook-handler.

---

### Task 5: Deploy and activate the n8n workflow

**Step 1: Deploy the updated services**

```bash
cd "C:\Users\alama\Desktop\Lukas Work\IO"
docker compose -f docker-compose.unified.yml up -d webhook-handler n8n
```

This restarts:
- `webhook-handler` with the refactored PR handler code
- `n8n` with the new environment variables (GITHUB_TOKEN, OPENWEBUI_API_KEY, SLACK_BOT_TOKEN)

**Step 2: Import the workflow into n8n**

Option A — Via n8n UI:
1. Open `https://ai-ui.coolestdomain.win/n8n/`
2. Click "Add workflow" → "Import from file"
3. Upload `n8n-workflows/pr-review-automation.json`
4. Review the workflow in the editor — verify all 5 nodes are present and connected
5. Click "Activate" (toggle in top right)

Option B — Via n8n API (can use the mcp-n8n tools from Open WebUI chat):
```
POST /api/v1/workflows
X-N8N-API-KEY: {N8N_API_KEY}
Body: contents of pr-review-automation.json
```
Then activate:
```
PATCH /api/v1/workflows/{id}
Body: {"active": true}
```

**Step 3: Verify the webhook endpoint exists in n8n**

After activation, n8n should be listening on:
`POST http://n8n:5678/webhook/pr-review` (internal)
`POST https://ai-ui.coolestdomain.win/n8n/webhook/pr-review` (external, via Caddy)

Test with curl:
```bash
curl -X POST http://localhost:5678/webhook/pr-review \
  -H "Content-Type: application/json" \
  -d '{"repo":"TheLukasHenry/proxy-server","pr_number":1,"action":"opened","title":"Test PR","author":"test","diff_url":"","html_url":"","base_branch":"main","head_branch":"test","body":"Test body"}'
```

Expected: 200 response with workflow execution results.

---

### Task 6: End-to-end test with a real PR

**Step 1: Create a test branch and PR**

```bash
cd /tmp
git clone https://github.com/TheLukasHenry/proxy-server.git test-pr-automation
cd test-pr-automation
git checkout -b test/webhook-automation
echo "# Webhook automation test $(date)" >> test-webhook.md
git add test-webhook.md
git commit -m "test: verify webhook-driven PR automation"
git push origin test/webhook-automation
```

Then create a PR via GitHub UI or CLI:
```bash
gh pr create --title "test: verify webhook-driven PR automation" --body "This PR tests the automated review pipeline."
```

**Step 2: Watch the automation happen**

Within 10-30 seconds, verify:

1. **GitHub PR comment** — An AI review comment should appear on the PR
   - Check: https://github.com/TheLukasHenry/proxy-server/pull/{number}
   - Should see a comment starting with "🤖 **AI Code Review**"

2. **Slack notification** — A message should appear in #automation
   - Should contain: PR title, author, repo link, review excerpt

3. **n8n execution history** — Open n8n UI and check:
   - The "PR Review Automation" workflow should show a successful execution
   - Each node should show green checkmarks
   - Click each node to see the data that flowed through

**Step 3: Clean up**

```bash
gh pr close {number} --delete-branch
```

**Step 4: Document success**

Take a screenshot of:
1. The GitHub PR with the AI review comment
2. The Slack #automation message
3. The n8n execution history showing all nodes

This is your demo material for the client.

---

### Task 7: Commit all changes and create PR

**Step 1: Final commit with any remaining changes**

```bash
git add -A
git status
```

Review and commit any loose changes.

**Step 2: Create a PR for review**

```bash
gh pr create \
  --title "feat: webhook-driven PR review automation via n8n" \
  --body "## Summary
- n8n workflow: webhook trigger → fetch PR diff → AI review → GitHub comment → Slack notification
- Refactored webhook-handler to delegate PR reviews to n8n (was doing it in-process)
- Added GitHub/OpenWebUI/Slack secrets to n8n environment
- Configured GitHub webhook on TheLukasHenry/proxy-server

## Test plan
- [ ] Open a test PR on proxy-server
- [ ] Verify AI review comment appears on PR within 30s
- [ ] Verify Slack notification in #automation
- [ ] Verify n8n execution history shows all nodes green
- [ ] Close test PR and clean up"
```
