# n8n Unification Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Unify webhook-handler and MCP tools on a single hosted n8n instance, eliminating the split-brain problem.

**Architecture:** Point webhook-handler at hosted n8n (`n8n.srv1041674.hstgr.cloud`) instead of local container. Update n8n workflow JSONs to use external URLs (hosted n8n can't reach Docker-internal `http://open-webui:8080`). Import workflows to hosted n8n, deploy, and verify end-to-end.

**Tech Stack:** Docker Compose, n8n REST API, FastAPI (webhook-handler), Caddy reverse proxy

---

### Task 1: Update n8n workflow JSONs for external URLs

The current workflow JSONs reference `http://open-webui:8080` (Docker internal). Hosted n8n is outside the Docker network and must use the external URL `https://ai-ui.coolestdomain.win`.

**Files:**
- Modify: `n8n-workflows/pr-review-automation.json:52-53`
- Modify: `n8n-workflows/github-push-processor.json:73-79`

**Step 1: Update PR Review Automation — AI Code Review node URL**

In `n8n-workflows/pr-review-automation.json` line 52, change:
```json
"url": "http://open-webui:8080/api/chat/completions",
```
to:
```json
"url": "https://ai-ui.coolestdomain.win/api/chat/completions",
```

**Step 2: Update GitHub Push Processor — AI Summary node URL**

In `n8n-workflows/github-push-processor.json` line 73, change:
```json
"url": "http://open-webui:8080/api/chat/completions",
```
to:
```json
"url": "https://ai-ui.coolestdomain.win/api/chat/completions",
```

**Step 3: Update GitHub Push Processor — remove hardcoded API key**

In `n8n-workflows/github-push-processor.json` line 79, the Authorization header has a hardcoded JWT. Change:
```json
"value": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6ImI3OTRiYmQ1LTE1MWMtNGQ3MC1iMmNiLThmZDZiMWJlODUxZCIsImV4cCI6MTc3MTkyMjM2MiwianRpIjoiMDg2OWM0ZDAtMjg3MS00Njg0LThmNzgtM2I3MWUwYTgwMjBkIn0.rwisATi4mdCSK3vZQEPV3YIvxQrkA3ra4H6L8CejlOM"
```
to:
```json
"value": "=Bearer {{ $env.OPENWEBUI_API_KEY }}"
```

**Step 4: Commit**

```bash
git add n8n-workflows/pr-review-automation.json n8n-workflows/github-push-processor.json
git commit -m "fix: use external URLs in n8n workflows for hosted n8n compatibility"
```

---

### Task 2: Update docker-compose webhook-handler n8n config

**Files:**
- Modify: `docker-compose.unified.yml:111` (N8N_URL)
- Modify: `docker-compose.unified.yml:117-119` (depends_on)

**Step 1: Change webhook-handler N8N_URL to use env var with hosted default**

In `docker-compose.unified.yml` line 111, change:
```yaml
      - N8N_URL=http://n8n:5678
```
to:
```yaml
      - N8N_URL=${N8N_API_URL:-https://n8n.srv1041674.hstgr.cloud}
```

This reuses the same `N8N_API_URL` env var that mcp-n8n already uses.

**Step 2: Remove depends_on n8n from webhook-handler**

In `docker-compose.unified.yml` lines 117-119, change:
```yaml
    depends_on:
      - open-webui
      - n8n
```
to:
```yaml
    depends_on:
      - open-webui
```

**Step 3: Commit**

```bash
git add docker-compose.unified.yml
git commit -m "fix: point webhook-handler at hosted n8n, remove local n8n dependency"
```

---

### Task 3: Import workflows to hosted n8n via API

**Prerequisites:** Hosted n8n must have environment variables set for `GITHUB_TOKEN`, `OPENWEBUI_API_KEY`, and `SLACK_BOT_TOKEN`. If the hosted n8n doesn't support env var injection, the workflow JSONs already contain the external URL and we can hardcode the API key as a last resort.

**Step 1: Check if hosted n8n API is reachable**

```bash
curl -s -H "X-N8N-API-KEY: $N8N_API_KEY" \
  https://n8n.srv1041674.hstgr.cloud/api/v1/workflows | head -c 200
```

Expected: JSON response (possibly empty array `{"data":[]}`)

**Step 2: Import PR Review Automation workflow**

```bash
curl -s -X POST \
  -H "X-N8N-API-KEY: $N8N_API_KEY" \
  -H "Content-Type: application/json" \
  -d @n8n-workflows/pr-review-automation.json \
  https://n8n.srv1041674.hstgr.cloud/api/v1/workflows
```

Note the returned workflow `id` (e.g., `"id": "abc123"`).

**Step 3: Activate the PR Review workflow**

```bash
curl -s -X PATCH \
  -H "X-N8N-API-KEY: $N8N_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"active": true}' \
  https://n8n.srv1041674.hstgr.cloud/api/v1/workflows/<WORKFLOW_ID>
```

Expected: `"active": true` in response.

**Step 4: Import GitHub Push Processor workflow**

```bash
curl -s -X POST \
  -H "X-N8N-API-KEY: $N8N_API_KEY" \
  -H "Content-Type: application/json" \
  -d @n8n-workflows/github-push-processor.json \
  https://n8n.srv1041674.hstgr.cloud/api/v1/workflows
```

**Step 5: Activate the Push Processor workflow**

```bash
curl -s -X PATCH \
  -H "X-N8N-API-KEY: $N8N_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"active": true}' \
  https://n8n.srv1041674.hstgr.cloud/api/v1/workflows/<WORKFLOW_ID>
```

**Step 6: Verify both workflows are listed and active**

```bash
curl -s -H "X-N8N-API-KEY: $N8N_API_KEY" \
  https://n8n.srv1041674.hstgr.cloud/api/v1/workflows \
  | python3 -c "import sys,json; [print(f'{w[\"id\"]} | {w[\"name\"]} | active={w[\"active\"]}') for w in json.load(sys.stdin).get('data',[])]"
```

Expected: Two workflows listed, both active.

---

### Task 4: Check hosted n8n environment variables

The PR review workflow uses `{{ $env.GITHUB_TOKEN }}` and `{{ $env.OPENWEBUI_API_KEY }}`. These must be available on the hosted n8n.

**Step 1: Check if hosted n8n has env var support**

SSH into the hosted n8n server or check the n8n admin UI at `https://n8n.srv1041674.hstgr.cloud` for Settings → Environment Variables.

If the hosted n8n is managed (Hetzner Apps / Docker), check the Docker config for env var injection.

**Step 2a: If env vars are supported**

Set these environment variables on the hosted n8n:
```
GITHUB_TOKEN=<from server .env>
OPENWEBUI_API_KEY=<from server .env>
SLACK_BOT_TOKEN=<if configured>
```

**Step 2b: If env vars are NOT supported (fallback)**

Update the workflow JSONs to hardcode the tokens directly instead of using `{{ $env.GITHUB_TOKEN }}`. This is less secure but functional.

In `pr-review-automation.json`, replace:
```json
"value": "=Bearer {{ $env.GITHUB_TOKEN }}"
```
with:
```json
"value": "Bearer <GITHUB_TOKEN from server .env>"
```

Do the same for `OPENWEBUI_API_KEY`. Then re-import (Task 3).

---

### Task 5: Deploy to live server

**Step 1: SCP updated docker-compose to server**

```bash
scp docker-compose.unified.yml root@46.224.193.25:/root/proxy-server/docker-compose.unified.yml
```

**Step 2: Rebuild and restart webhook-handler**

```bash
ssh root@46.224.193.25 "cd /root/proxy-server && docker compose -f docker-compose.unified.yml up -d --build webhook-handler"
```

**Step 3: Stop the local n8n container**

```bash
ssh root@46.224.193.25 "docker stop n8n"
```

**Step 4: Verify webhook-handler is using hosted n8n URL**

```bash
ssh root@46.224.193.25 "docker logs webhook-handler --tail 10 2>&1 | grep -i n8n"
```

Expected: `n8n URL: https://n8n.srv1041674.hstgr.cloud`

---

### Task 6: End-to-end test

**Step 1: Test webhook-handler → hosted n8n PR review**

Push a trivial commit to the branch to trigger a PR sync event:

```bash
git commit --allow-empty -m "test: trigger webhook for n8n unification verification"
git push proxy-server fix/mcp-network-split
```

**Step 2: Verify AI review comment appears on PR #10**

```bash
gh api repos/TheLukasHenry/proxy-server/issues/10/comments --jq '.[-1].body' | head -10
```

Expected: A new AI review comment (the 3rd one, timestamped after deployment).

**Step 3: Verify hosted n8n execution history**

```bash
curl -s -H "X-N8N-API-KEY: $N8N_API_KEY" \
  "https://n8n.srv1041674.hstgr.cloud/api/v1/executions?limit=5" \
  | python3 -c "import sys,json; [print(f'{e[\"id\"]} | {e[\"workflowId\"]} | {e[\"status\"]} | {e.get(\"startedAt\",\"\")}') for e in json.load(sys.stdin).get('data',[])]"
```

Expected: Recent execution(s) with status "success".

**Step 4: Test MCP tools see the workflows**

Open `https://ai-ui.coolestdomain.win`, start a new chat, enable MCP Proxy tool, and ask:
"List all n8n workflows"

Expected: Shows the 2 imported workflows (PR Review Automation, GitHub Push Processor).

**Step 5: Verify local n8n is stopped**

```bash
ssh root@46.224.193.25 "docker ps | grep n8n"
```

Expected: Only `mcp-n8n` appears. No `n8n` container.

---

### Task 7: Commit and push final state

**Step 1: Commit any remaining changes**

```bash
git add -A
git status
# Only commit if there are changes
git commit -m "feat: unify n8n — webhook-handler + MCP tools on hosted instance"
```

**Step 2: Push to remote**

```bash
git push proxy-server fix/mcp-network-split
```

**Step 3: Update PR description**

Update PR #10 body to mention the n8n unification.
