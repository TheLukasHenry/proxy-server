# Open WebUI v0.8.3 Upgrade Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Upgrade Open WebUI from v0.7.2 to v0.8.3 on the live Hetzner server, then enable Skills, Channels, and Analytics.

**Architecture:** The upgrade is a Docker image swap (`:main` → `:v0.8.3`) with database migration. v0.8.0 introduces schema changes to the `chat_message` table. After upgrade, we enable new features (Channels, Skills) and create starter content. The MCP Proxy connection (`TOOL_SERVER_CONNECTIONS`) and all pipe functions must be verified post-migration.

**Tech Stack:** Docker Compose, PostgreSQL (pgvector), Open WebUI v0.8.3, SSH to Hetzner VPS (46.224.193.25)

**Server:** `root@46.224.193.25`
**Compose file:** `docker-compose.unified.yml`
**Working dir on server:** `/root/proxy-server`

---

### Task 1: Pre-Upgrade Inventory

**Purpose:** Document current state so we can verify nothing was lost after upgrade.

**Step 1: Check current Open WebUI version**

```bash
ssh root@46.224.193.25 "docker exec open-webui python -c \"import importlib.metadata; print(importlib.metadata.version('open-webui'))\" 2>/dev/null || docker exec open-webui cat /app/package.json 2>/dev/null | head -5 || echo 'v0.7.2 (from browser)'"
```

Expected: v0.7.2 or similar

**Step 2: Count existing chats and functions in database**

```bash
ssh root@46.224.193.25 "docker exec postgres psql -U openwebui -d openwebui -c \"SELECT 'chats' as table_name, count(*) FROM chat UNION ALL SELECT 'functions', count(*) FROM function UNION ALL SELECT 'users', count(*) FROM public.\\\"user\\\" ORDER BY table_name;\""
```

Save output — these counts must match after upgrade.

**Step 3: List installed pipe functions**

```bash
ssh root@46.224.193.25 "docker exec postgres psql -U openwebui -d openwebui -c \"SELECT id, name, type, is_active FROM function ORDER BY name;\""
```

Expected: `webhook_automation` (pipe), plus any reporting tools.

**Step 4: Verify MCP Proxy tools work (baseline)**

```bash
ssh root@46.224.193.25 "docker exec webhook-handler python -c \"import urllib.request; r=urllib.request.urlopen('http://localhost:8086/health'); print(r.read().decode())\""
```

Expected: `{"status":"ok"}`

---

### Task 2: Backup Database and Volumes

**Purpose:** Create full rollback capability before any changes.

**Step 1: Create backup directory**

```bash
ssh root@46.224.193.25 "mkdir -p /root/backups/2026-02-20"
```

**Step 2: SQL dump of entire database (most reliable rollback)**

```bash
ssh root@46.224.193.25 "docker exec postgres pg_dump -U openwebui openwebui > /root/backups/2026-02-20/openwebui-full.sql"
```

**Step 3: Verify SQL dump is not empty**

```bash
ssh root@46.224.193.25 "wc -l /root/backups/2026-02-20/openwebui-full.sql"
```

Expected: Thousands of lines (not 0).

**Step 4: Backup Docker volumes**

```bash
ssh root@46.224.193.25 "docker run --rm -v proxy-server_postgres-data:/data -v /root/backups/2026-02-20:/backup alpine tar czf /backup/postgres-data.tar.gz -C / data"
```

```bash
ssh root@46.224.193.25 "docker run --rm -v proxy-server_open-webui-data:/data -v /root/backups/2026-02-20:/backup alpine tar czf /backup/open-webui-data.tar.gz -C / data"
```

**Step 5: Verify backups exist**

```bash
ssh root@46.224.193.25 "ls -lh /root/backups/2026-02-20/"
```

Expected: 3 files (openwebui-full.sql, postgres-data.tar.gz, open-webui-data.tar.gz)

**Step 6: Commit the intent**

No code changes yet — this is just backup verification.

---

### Task 3: Pin Image Tag and Deploy

**Purpose:** Change Open WebUI from `:main` to `:v0.8.3` and restart.

**Files:**
- Modify: `docker-compose.unified.yml:216`

**Step 1: Update image tag locally**

In `docker-compose.unified.yml`, line 216, change:

```yaml
# FROM:
image: ghcr.io/open-webui/open-webui:main

# TO:
image: ghcr.io/open-webui/open-webui:v0.8.3
```

**Step 2: Deploy the change to server**

```bash
scp docker-compose.unified.yml root@46.224.193.25:/root/proxy-server/docker-compose.unified.yml
```

**Step 3: Pull new image and restart only open-webui**

```bash
ssh root@46.224.193.25 "cd /root/proxy-server && docker compose -f docker-compose.unified.yml pull open-webui && docker compose -f docker-compose.unified.yml up -d open-webui"
```

**Step 4: Monitor migration logs (CRITICAL — watch for errors)**

```bash
ssh root@46.224.193.25 "docker compose -f docker-compose.unified.yml logs -f open-webui 2>&1 | head -100"
```

Watch for:
- `Running migrations` messages
- `chat_message` table migration progress
- Any ERROR messages
- `Application startup complete` = success

**Step 5: Wait for startup and verify health**

```bash
ssh root@46.224.193.25 "sleep 30 && docker exec open-webui curl -sf http://localhost:8080/health || echo 'FAILED'"
```

Expected: Health check passes.

**Step 6: Commit the image tag change**

```bash
git add docker-compose.unified.yml
git commit -m "chore: pin Open WebUI to v0.8.3 (upgrade from v0.7.2)"
```

---

### Task 4: Post-Upgrade Verification

**Purpose:** Confirm nothing broke — chats, functions, MCP tools all still work.

**Step 1: Verify chat and function counts match pre-upgrade**

```bash
ssh root@46.224.193.25 "docker exec postgres psql -U openwebui -d openwebui -c \"SELECT 'chats' as table_name, count(*) FROM chat UNION ALL SELECT 'functions', count(*) FROM function UNION ALL SELECT 'users', count(*) FROM public.\\\"user\\\" ORDER BY table_name;\""
```

Compare with Task 1 Step 2 output — counts must match.

**Step 2: Verify pipe functions survived**

```bash
ssh root@46.224.193.25 "docker exec postgres psql -U openwebui -d openwebui -c \"SELECT id, name, type, is_active FROM function ORDER BY name;\""
```

If `webhook_automation` is missing, re-install:

```bash
ssh root@46.224.193.25 "cd /root/proxy-server && docker compose -f docker-compose.unified.yml exec webhook-handler python /app/scripts/install_webhook_pipe.py"
```

**Step 3: Test MCP tools via chat (browser)**

Navigate to `https://ai-ui.coolestdomain.win`, clear browser cache (Ctrl+F5), start a new chat with gpt-5, type:

```
List all MCP servers available
```

Expected: AI uses MCP Proxy tools and returns server list.

**Step 4: Test webhook-handler integration**

```bash
ssh root@46.224.193.25 "docker exec webhook-handler python -c \"
import urllib.request, json
req = urllib.request.Request('http://localhost:8086/webhook/generic', data=json.dumps({'data':'ping','prompt':'Reply: OK'}).encode(), headers={'Content-Type':'application/json'}, method='POST')
r = urllib.request.urlopen(req, timeout=30)
print(r.read().decode()[:200])
\""
```

Expected: AI responds (not 429 quota error).

**Step 5: Verify version in browser**

Check the footer of Open WebUI — should show `v0.8.3` (previously showed `v0.7.2`).

---

### Task 5: Enable Channels Feature

**Purpose:** Turn on the Channels feature in Open WebUI admin settings.

**Step 1: Navigate to admin settings**

In browser at `https://ai-ui.coolestdomain.win`:
1. Click user avatar (bottom-left) → Admin Panel
2. Go to Settings → General
3. Find "Channels" or "Channels (Beta)" toggle → Enable it
4. Save

**Step 2: Create #general channel**

1. In the left sidebar, find the Channels section (should appear after enabling)
2. Click "+" or "Create Channel"
3. Name: `general`
4. Description: `Team discussion — use @gpt-5 to ask AI questions`
5. Access: Public

**Step 3: Create #dev-notifications channel**

1. Create another channel
2. Name: `dev-notifications`
3. Description: `CI/CD alerts and automated notifications`
4. Access: Public

**Step 4: Test @model mention in #general**

1. Open the `#general` channel
2. Type: `@gpt-5 What is the current time?`
3. Expected: GPT-5 responds in the channel

---

### Task 6: Verify Skills Feature

**Purpose:** Confirm Skills UI is accessible and create the first Skill.

**Step 1: Navigate to Skills workspace**

In browser: go to `https://ai-ui.coolestdomain.win/workspace/skills`

If the page loads with a Skills management interface, the feature is working.

**Step 2: Create "PR Security Review" Skill**

1. Click "Create Skill" (or equivalent button)
2. Name: `PR Security Review`
3. Description: `Guides the AI through reviewing a pull request for security issues`
4. Content/Instructions:

```
When asked about PR security, code review, or to review a pull request:

1. Use the GitHub MCP tools to fetch PR details:
   - `github_get_pull_request` to get title, description, author, and branch info
   - `github_get_pull_request_files` to see which files changed and the actual diff

2. Analyze the diff for common security issues:
   - SQL injection (unsanitized user input in queries)
   - XSS (unescaped user content in HTML/templates)
   - Hardcoded secrets (API keys, passwords, tokens in code)
   - Insecure dependencies (known vulnerable packages)
   - Missing input validation at system boundaries
   - Unsafe deserialization

3. If SonarQube MCP tools are available, also use:
   - `sonarqube_get_issues` for automated code quality findings

4. Present findings in a structured format:
   - CRITICAL: Must fix before merge
   - WARNING: Should fix, potential risk
   - INFO: Suggestions for improvement
   - APPROVED: If no issues found, explicitly state the PR looks good

5. Always mention which files you reviewed and which you could not access.
```

**Step 3: Create "Daily Report Builder" Skill**

1. Create another Skill
2. Name: `Daily Report Builder`
3. Description: `Helps generate end-of-day reports from GitHub, n8n, and service health data`
4. Content/Instructions:

```
When asked for a daily report, status update, or end-of-day summary:

1. Gather data from available sources:
   - Use `github_list_commits` or `github_search_commits` to find today's commits
   - Use n8n MCP tools to check workflow execution status
   - Check service health by asking about system status

2. Structure the report as:
   - SUMMARY: 2-3 sentence overview of the day
   - COMPLETED: List of completed work (from commits and executions)
   - IN PROGRESS: Any ongoing workflows or open PRs
   - ISSUES: Any failures, errors, or concerns found
   - NEXT STEPS: Recommendations for tomorrow

3. If asked for a spreadsheet, use the Excel Creator tool to generate a downloadable file.
4. If asked for a dashboard, use the Executive Dashboard tool for visualizations.
5. Keep the tone professional but concise. Focus on outcomes, not process.
```

**Step 4: Create "Project Status" Skill**

1. Create another Skill
2. Name: `Project Status`
3. Description: `Aggregates project status from GitHub issues, PRs, and task trackers`
4. Content/Instructions:

```
When asked about project status, what's happening, or progress:

1. Check GitHub for recent activity:
   - Open pull requests (use `github_list_pull_requests`)
   - Recent issues (use `github_list_issues`)
   - Recent commits (use `github_list_commits`)

2. If ClickUp is available, check:
   - Task status in relevant lists
   - Overdue tasks
   - Recently completed tasks

3. If n8n is available, check:
   - Active workflows and their recent execution status
   - Any failed executions

4. Present as a status dashboard:
   - OPEN PRs: [count] — list titles
   - OPEN ISSUES: [count] — list titles
   - RECENT ACTIVITY: Last 5 commits with authors
   - AUTOMATION: Workflow status (active/inactive/failed)

5. Highlight anything that needs attention (failed builds, stale PRs, overdue tasks).
```

---

### Task 7: Test Full Integration

**Purpose:** End-to-end verification that everything works together.

**Step 1: Test Skill-enhanced chat**

1. Start a new chat with gpt-5
2. Type `$` to see the Skills popup
3. Select "PR Security Review"
4. Type: `Review the latest PR on TheLukasHenry/proxy-server`
5. Expected: AI uses GitHub MCP tools to fetch PR data and applies the Skill's analysis framework

**Step 2: Test Channel + MCP tools**

1. Open `#general` channel
2. Type: `@gpt-5 List all active n8n workflows`
3. Expected: AI uses n8n MCP tools within the channel context

**Step 3: Test webhook-handler report**

```bash
ssh root@46.224.193.25 "docker exec webhook-handler python -c \"
import urllib.request, json
req = urllib.request.Request('http://localhost:8086/scheduler/health-report')
r = urllib.request.urlopen(req, timeout=30)
data = json.loads(r.read().decode())
print(f'Healthy: {data[\"healthy\"]}/{data[\"total\"]}')
for s in data['services']:
    print(f'  {s[\"service\"]}: {s[\"status\"]}')
\""
```

Expected: 4/4 healthy (open-webui, mcp-proxy, n8n, webhook-handler)

**Step 4: Verify Analytics dashboard**

1. In browser: Admin Panel → should now show Analytics section
2. Check for model usage stats, user activity

---

### Task 8: Update Documentation

**Purpose:** Record the upgrade in docs.

**Files:**
- Modify: `docs/architecture-guide.md`
- Modify: `docs/ARCHITECTURE.md`

**Step 1: Update Open WebUI version references**

In `docs/architecture-guide.md`, update any references to v0.7.2 to note the upgrade to v0.8.3.

**Step 2: Add Skills and Channels to architecture docs**

Add a new section or update the existing Open WebUI section to mention:
- Skills feature (context injection for MCP tool guidance)
- Channels feature (built-in team chat with @model mentions)
- Analytics dashboard

**Step 3: Update ARCHITECTURE.md date**

Change "Last Updated" to 2026-02-20.

**Step 4: Commit all documentation**

```bash
git add docs/architecture-guide.md docs/ARCHITECTURE.md docs/plans/2026-02-20-openwebui-upgrade-design.md docs/plans/2026-02-20-openwebui-upgrade-plan.md
git commit -m "docs: document Open WebUI v0.8.3 upgrade, Skills, and Channels"
```

---

## Rollback Procedure (if anything goes wrong)

```bash
# 1. Stop everything
ssh root@46.224.193.25 "cd /root/proxy-server && docker compose -f docker-compose.unified.yml stop"

# 2. Restore database from SQL dump
ssh root@46.224.193.25 "docker compose -f docker-compose.unified.yml start postgres && sleep 10 && docker exec -i postgres psql -U openwebui -d postgres -c 'DROP DATABASE openwebui;' && docker exec -i postgres psql -U openwebui -d postgres -c 'CREATE DATABASE openwebui OWNER openwebui;' && docker exec -i postgres psql -U openwebui -d openwebui < /root/backups/2026-02-20/openwebui-full.sql"

# 3. Revert image tag in docker-compose.unified.yml (change v0.8.3 back to main)
# 4. Restart
ssh root@46.224.193.25 "cd /root/proxy-server && docker compose -f docker-compose.unified.yml up -d"
```

---

## Estimated Timeline

| Task | Duration |
|------|----------|
| Task 1: Pre-upgrade inventory | 10 min |
| Task 2: Backup | 15-30 min |
| Task 3: Deploy upgrade | 15-30 min (depends on migration) |
| Task 4: Post-upgrade verification | 15 min |
| Task 5: Enable Channels | 15 min |
| Task 6: Create Skills | 30 min |
| Task 7: Full integration test | 15 min |
| Task 8: Documentation | 15 min |
| **Total** | **2-3 hours** |
