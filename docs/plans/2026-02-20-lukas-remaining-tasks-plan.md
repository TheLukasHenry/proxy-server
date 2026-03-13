# Lukas Remaining Tasks (A–H) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the 8 remaining features Lukas requested: Skills for non-technical users, Slack/Discord configuration, czlonkowski n8n-mcp upgrade, PR→deployment notes, health→Slack, n8n workflow templates, email→automation pipeline, and bidirectional n8n MCP trigger.

**Architecture:** All tasks extend the existing webhook-handler, Open WebUI Skills, and n8n integrations. No new services — only configuration changes, new Skills, new n8n workflows, and minor code additions to existing files.

**Tech Stack:** FastAPI (webhook-handler), Open WebUI Skills (browser UI), n8n workflows (hosted at `n8n.srv1041674.hstgr.cloud`), Docker Compose

**Server:** `root@46.224.193.25`
**Working dir on server:** `/root/proxy-server`

---

### Task A: Wrap MCPs in Skills for Non-Technical Users

**Purpose:** Create Skills that teach the AI when/how to use MCP tools so non-technical users (product owners, stakeholders) can self-serve. This is Lukas's "big vision" — an engineer builds a Skill once, anyone invokes it from a channel.

**Step 1: Create "Code Quality Check" Skill (browser)**

Navigate to `https://ai-ui.coolestdomain.win/workspace/skills` → New Skill

- Name: `Code Quality Check`
- Description: `Runs SonarQube analysis and explains findings in business terms`
- Instructions:

```
When asked about code quality, technical debt, or code health:

1. If a specific repository or project is mentioned, use SonarQube MCP tools:
   - `sonarqube_get_projects` to list available projects
   - `sonarqube_get_issues` to fetch current issues with severity ratings
   - `sonarqube_get_measures` to get metrics (coverage, duplications, complexity)

2. Translate technical findings into business language:
   - CRITICAL bugs → "Production risk: these could cause outages"
   - Major code smells → "Maintenance cost: these slow down future development"
   - Low coverage → "Testing gap: changes here are risky without tests"

3. Present as a report:
   - HEALTH SCORE: Overall project health (A-F rating)
   - CRITICAL ISSUES: Must fix now (count + descriptions)
   - WARNINGS: Should fix soon (count + top 3)
   - TRENDS: Getting better or worse vs last scan
   - RECOMMENDATION: One paragraph on where to focus

4. If asked to compare projects, create a side-by-side table.
```

**Step 2: Create "ClickUp Task Manager" Skill (browser)**

- Name: `ClickUp Task Manager`
- Description: `Manages ClickUp tasks, tracks deadlines, and reports overdue items`
- Instructions:

```
When asked about tasks, project management, or ClickUp:

1. Use ClickUp MCP tools to gather data:
   - `clickup_get_workspaces` to find the right workspace
   - `clickup_get_spaces` to list spaces in the workspace
   - `clickup_get_lists` to find task lists
   - `clickup_get_tasks` to fetch tasks with status, assignee, due date

2. For task creation:
   - `clickup_create_task` with name, description, assignee, due date, priority
   - Always confirm the task was created by returning its ID and URL

3. For status reports, present as:
   - OVERDUE: Tasks past due date (sorted by days overdue)
   - IN PROGRESS: Currently being worked on
   - UPCOMING: Due in the next 7 days
   - BLOCKED: Tasks with blockers or dependencies

4. If asked "what should I work on next?", prioritize by: overdue first, then highest priority, then earliest due date.
```

**Step 3: Create "n8n Workflow Manager" Skill (browser)**

- Name: `n8n Workflow Manager`
- Description: `Manages n8n automation workflows — list, create, execute, and monitor`
- Instructions:

```
When asked about workflows, automation, or n8n:

1. To list workflows:
   - Use `n8n_list_workflows` to show all workflows with status (active/inactive)
   - Include node count and last execution time if available

2. To check execution history:
   - Use `n8n_get_executions` to show recent runs
   - Flag any failed executions with error details

3. To create a new workflow:
   - Use `n8n_create_workflow` with a descriptive name
   - Ask the user what trigger they want (webhook, schedule, event)
   - Ask what actions they need (send email, post to Slack, update spreadsheet)
   - Build the workflow step by step

4. To execute a workflow manually:
   - Use `n8n_execute_workflow` with the workflow ID
   - Report back the execution status and any output

5. Present workflow status as:
   - ACTIVE: Running workflows with last success time
   - INACTIVE: Paused workflows
   - FAILED: Workflows with recent failures (show error)
   - SUGGESTED: Recommend workflows based on what the user is trying to do
```

**Step 4: Create "File & Document Manager" Skill (browser)**

- Name: `File & Document Manager`
- Description: `Reads, searches, and manages files on the server using filesystem tools`
- Instructions:

```
When asked to find files, read documents, or manage server files:

1. Use Filesystem MCP tools:
   - `filesystem_list_directory` to browse directories
   - `filesystem_read_file` to read file contents
   - `filesystem_search_files` to find files by name or pattern
   - `filesystem_write_file` to create or update files (ask for confirmation first)

2. For document searches:
   - Ask what type of file (config, log, code, docs)
   - Search in the most likely directories first
   - Present results with file path, size, and last modified date

3. For log analysis:
   - Read the most recent entries
   - Highlight errors and warnings
   - Summarize patterns (e.g., "12 timeout errors in the last hour")

4. Safety rules:
   - NEVER write to files without explicit user confirmation
   - NEVER delete files — only suggest deletion
   - NEVER read .env files or files likely containing secrets
   - Always show the full file path so the user knows what they're accessing
```

**Step 5: Create "GitHub Operations" Skill (browser)**

- Name: `GitHub Operations`
- Description: `Manages GitHub repos, PRs, issues, and code using GitHub MCP tools`
- Instructions:

```
When asked about GitHub, repositories, pull requests, or issues:

1. For repository information:
   - `github_get_repository` for repo details (stars, forks, language)
   - `github_list_branches` to show active branches
   - `github_list_commits` for recent commit history

2. For pull requests:
   - `github_list_pull_requests` to show open PRs
   - `github_get_pull_request` for specific PR details
   - `github_get_pull_request_files` to see what changed
   - When reviewing, check for: large PRs (>500 lines), missing descriptions, no tests

3. For issues:
   - `github_list_issues` to show open issues
   - `github_create_issue` to create new issues (always include labels)
   - `github_search_issues` to find specific topics

4. For code:
   - `github_get_file_contents` to read specific files
   - `github_search_code` to find code patterns across the repo

5. Always include links to the GitHub web UI for items you reference.
```

**Step 6: Verify all Skills are active**

Navigate to `https://ai-ui.coolestdomain.win/workspace/skills` and confirm all 8 Skills are listed and enabled:
1. PR Security Review (created in Task 6 of upgrade)
2. Daily Report Builder (created in Task 6 of upgrade)
3. Project Status (created in Task 6 of upgrade)
4. Code Quality Check (new)
5. ClickUp Task Manager (new)
6. n8n Workflow Manager (new)
7. File & Document Manager (new)
8. GitHub Operations (new)

**Step 7: Test with a non-technical prompt**

Start a new chat with gpt-5, type:
```
What pull requests are open right now on TheLukasHenry/proxy-server?
```
Expected: AI uses the GitHub Operations Skill context + GitHub MCP tools to fetch and display open PRs.

---

### Task B: Configure Slack App + Discord App

**Purpose:** Activate the dormant slash command endpoints. This requires Lukas to create the apps, but we prepare the server-side `.env` and document exact steps.

**Step 1: Create `.env` additions documentation**

Create a file `docs/setup-slack-discord.md` with the exact configuration steps Lukas needs:

For Slack:
1. Go to `api.slack.com/apps` → existing or new app
2. Slash Commands → Create: Command = `/aiui`, URL = `https://ai-ui.coolestdomain.win/webhook/slack/commands`, Description = "AI assistant and workflow trigger", Hint = `[ask|workflow|status|report] [text]`
3. OAuth & Permissions → add `commands` scope → reinstall to workspace
4. Copy: Signing Secret → `SLACK_SIGNING_SECRET`, Bot Token → `SLACK_BOT_TOKEN`
5. Choose a channel for reports → copy Channel ID → `REPORT_SLACK_CHANNEL`

For Discord:
1. Go to `discord.com/developers` → New Application
2. Note Application ID → `DISCORD_APPLICATION_ID`, Public Key → `DISCORD_PUBLIC_KEY`
3. Bot → Create Bot → Copy Token → `DISCORD_BOT_TOKEN`
4. General Information → Interactions Endpoint URL = `https://ai-ui.coolestdomain.win/webhook/discord`
5. OAuth2 → URL Generator → scope `applications.commands` → invite bot to server

**Step 2: Set env vars on server (after Lukas provides values)**

```bash
ssh root@46.224.193.25 "cat >> /root/proxy-server/.env << 'EOF'
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...
REPORT_SLACK_CHANNEL=C...
DISCORD_APPLICATION_ID=...
DISCORD_PUBLIC_KEY=...
DISCORD_BOT_TOKEN=...
EOF"
```

**Step 3: Restart webhook-handler to pick up new env vars**

```bash
ssh root@46.224.193.25 "cd /root/proxy-server && docker compose -f docker-compose.unified.yml up -d --build webhook-handler"
```

**Step 4: Register Discord slash command (one-time)**

```bash
curl -X POST "https://discord.com/api/v10/applications/{APP_ID}/commands" \
  -H "Authorization: Bot {BOT_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "aiui",
    "description": "AI assistant and workflow trigger",
    "options": [{
      "name": "command",
      "description": "Subcommand: ask, workflow, status, report",
      "type": 3,
      "required": true
    }]
  }'
```

**Step 5: Verify both endpoints respond**

```bash
# Slack (should return 401 or process command, NOT 503)
curl -s -X POST https://ai-ui.coolestdomain.win/webhook/slack/commands
# Discord (should return PONG for type 1, NOT 503)
curl -s -X POST https://ai-ui.coolestdomain.win/webhook/discord -H "Content-Type: application/json" -d '{"type": 1}'
```

**Step 6: Commit setup docs**

```bash
git add docs/setup-slack-discord.md
git commit -m "docs: add Slack and Discord app configuration guide"
```

---

### Task C: Deploy czlonkowski/n8n-mcp (Better n8n MCP Server)

**Purpose:** Replace or supplement the current `leonardsellem/n8n-mcp-server` with the more powerful `czlonkowski/n8n-mcp` (13.7k stars). This one can create n8n workflows from natural language using a pre-built SQLite database of all 1,084 n8n nodes.

**Files:**
- Modify: `docker-compose.unified.yml` (add new service)
- Modify: MCP Proxy server list (add new server)

**Step 1: Add czlonkowski/n8n-mcp service to docker-compose**

In `docker-compose.unified.yml`, after the existing `mcp-n8n` service, add:

```yaml
  mcp-n8n-builder:
    image: mcp/n8n
    build:
      context: ./mcp-servers/n8n-builder
      dockerfile: Dockerfile
    container_name: mcp-n8n-builder
    restart: unless-stopped
    environment:
      - N8N_BASE_URL=https://n8n.srv1041674.hstgr.cloud
      - N8N_API_KEY=${N8N_API_KEY:-}
    networks:
      - backend
```

**Step 2: Create Dockerfile for czlonkowski/n8n-mcp**

Create `mcp-servers/n8n-builder/Dockerfile`:

```dockerfile
FROM node:20-slim
RUN npm install -g @anthropic/n8n-mcp@latest
EXPOSE 8000
CMD ["npx", "-y", "mcpo", "--port", "8000", "--", "npx", "-y", "@anthropic/n8n-mcp"]
```

Note: Check actual package name — may be `czlonkowski/n8n-mcp` on npm or need to be cloned from GitHub.

**Step 3: Add to MCP Proxy server registry**

SSH to server and add the new server to the MCP Proxy's server list in PostgreSQL:

```bash
ssh root@46.224.193.25 "docker exec postgres psql -U openwebui -d openwebui -c \"
INSERT INTO mcp_proxy.servers (id, name, url, description, enabled)
VALUES ('n8n-builder', 'n8n Workflow Builder', 'http://mcp-n8n-builder:8000', 'Create n8n workflows from natural language (czlonkowski/n8n-mcp)', true)
ON CONFLICT (id) DO UPDATE SET url = EXCLUDED.url, description = EXCLUDED.description;
\""
```

**Step 4: Deploy**

```bash
scp -r mcp-servers/n8n-builder root@46.224.193.25:/root/proxy-server/mcp-servers/n8n-builder
scp docker-compose.unified.yml root@46.224.193.25:/root/proxy-server/docker-compose.unified.yml
ssh root@46.224.193.25 "cd /root/proxy-server && docker compose -f docker-compose.unified.yml up -d --build mcp-n8n-builder"
```

**Step 5: Verify the new server appears in MCP Proxy**

```bash
ssh root@46.224.193.25 "curl -s http://localhost:8000/tools | python3 -m json.tool | grep n8n-builder"
```

**Step 6: Test from Open WebUI chat**

Start a new chat with gpt-5:
```
Using the n8n workflow builder, create a workflow that sends a daily summary email at 9 AM
```

**Step 7: Commit**

```bash
git add docker-compose.unified.yml mcp-servers/n8n-builder/
git commit -m "feat: add czlonkowski/n8n-mcp workflow builder service"
```

---

### Task D: GitHub PR → Deployment Notes Automation

**Purpose:** When a PR is merged, automatically generate deployment notes documenting what changed. Lukas said: "If you get the GitHub PR, it should be able to get the code with file systems and send some file of updated deployment notes."

**Files:**
- Modify: `webhook-handler/handlers/github.py` — add `_handle_pr_merged()` method
- Modify: `webhook-handler/clients/github.py` — add `get_pr_details()` method
- Modify: `webhook-handler/clients/openwebui.py` — add `generate_deployment_notes()` method

**Step 1: Add `get_pr_details()` to `clients/github.py`**

```python
async def get_pr_details(self, owner: str, repo: str, pr_number: int) -> Optional[dict]:
    """Fetch full PR details including title, body, files changed, and merge commit."""
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {"Authorization": f"token {self.token}", "Accept": "application/vnd.github.v3+json"}
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            pr = resp.json()

            # Also fetch changed files
            files_url = f"{url}/files"
            files_resp = await client.get(files_url, headers=headers)
            files_resp.raise_for_status()
            files = files_resp.json()

            return {
                "number": pr["number"],
                "title": pr["title"],
                "body": pr.get("body", ""),
                "author": pr["user"]["login"],
                "branch": pr["head"]["ref"],
                "base": pr["base"]["ref"],
                "merged_at": pr.get("merged_at", ""),
                "files_changed": [{"filename": f["filename"], "status": f["status"], "additions": f["additions"], "deletions": f["deletions"]} for f in files],
                "total_changes": sum(f["additions"] + f["deletions"] for f in files),
            }
    except Exception as e:
        logger.error(f"Failed to fetch PR details: {e}")
        return None
```

**Step 2: Add `generate_deployment_notes()` to `clients/openwebui.py`**

```python
async def generate_deployment_notes(self, pr_details: dict) -> Optional[str]:
    """Generate deployment notes from PR details using AI."""
    prompt = f"""Generate concise deployment notes for this merged pull request:

PR #{pr_details['number']}: {pr_details['title']}
Author: {pr_details['author']}
Branch: {pr_details['branch']} → {pr_details['base']}
Merged: {pr_details['merged_at']}
Files Changed: {pr_details['total_changes']} lines across {len(pr_details['files_changed'])} files

Changed files:
{chr(10).join(f"- {f['filename']} ({f['status']}: +{f['additions']}/-{f['deletions']})" for f in pr_details['files_changed'])}

Description:
{pr_details.get('body', 'No description provided.')}

Format the deployment notes as:
## Deployment Notes — PR #{pr_details['number']}
**Date:** [merge date]
**What Changed:** [1-2 sentence summary]
**Files Modified:** [bullet list of key files]
**Impact:** [what users/systems are affected]
**Rollback:** [how to revert if needed]
**Testing:** [what was tested or needs testing]"""

    return await self.chat_completion(
        messages=[{"role": "user", "content": prompt}],
        model=self.default_model if hasattr(self, 'default_model') else "gpt-4-turbo",
    )
```

**Step 3: Add `_handle_pr_merged()` to `handlers/github.py`**

In `_handle_pull_request_event()`, add handling for the `closed` action when `merged` is True:

```python
async def _handle_pull_request_event(self, payload: dict):
    action = payload.get("action", "")
    pr = payload.get("pull_request", {})

    # Existing logic for opened/synchronized...
    if action in ("opened", "synchronize"):
        # ... existing n8n forwarding code ...
        pass

    # NEW: Handle merged PRs
    if action == "closed" and pr.get("merged", False):
        await self._handle_pr_merged(payload)

async def _handle_pr_merged(self, payload: dict):
    """Generate and post deployment notes when a PR is merged."""
    pr = payload.get("pull_request", {})
    repo = payload.get("repository", {})
    owner = repo.get("owner", {}).get("login", "")
    repo_name = repo.get("name", "")
    pr_number = pr.get("number")

    logger.info(f"PR #{pr_number} merged in {owner}/{repo_name}, generating deployment notes")

    # Fetch full PR details
    pr_details = await self.github.get_pr_details(owner, repo_name, pr_number)
    if not pr_details:
        logger.error(f"Could not fetch PR #{pr_number} details")
        return

    # Generate deployment notes via AI
    notes = await self.openwebui.generate_deployment_notes(pr_details)
    if not notes:
        logger.error(f"Could not generate deployment notes for PR #{pr_number}")
        return

    # Post as a comment on the PR
    await self.github.post_issue_comment(owner, repo_name, pr_number, notes)
    logger.info(f"Deployment notes posted to PR #{pr_number}")
```

**Step 4: Deploy to server**

```bash
scp -r webhook-handler/ root@46.224.193.25:/root/proxy-server/webhook-handler/
ssh root@46.224.193.25 "cd /root/proxy-server && docker compose -f docker-compose.unified.yml up -d --build webhook-handler"
```

**Step 5: Test by merging a test PR**

Create a small test PR on `TheLukasHenry/proxy-server`, merge it, and verify deployment notes are posted as a comment.

**Step 6: Commit**

```bash
git add webhook-handler/handlers/github.py webhook-handler/clients/github.py webhook-handler/clients/openwebui.py
git commit -m "feat: auto-generate deployment notes on PR merge"
```

---

### Task E: Health Report → Slack Posting

**Purpose:** Make `daily_health_report()` actually post to Slack instead of just logging. Currently it has the Slack code but requires `REPORT_SLACK_CHANNEL` to be set.

**Files:**
- Modify: `webhook-handler/main.py` — fix on-demand health report route to pass slack_client
- Modify: `webhook-handler/scheduler.py` — deduplicate SERVICE_ENDPOINTS

**Step 1: Fix on-demand health report to pass slack_client**

In `webhook-handler/main.py`, find the `/scheduler/health-report` endpoint and update it to pass the slack client:

```python
# Current (broken — never posts to Slack):
@app.get("/scheduler/health-report")
async def get_health_report():
    results = await daily_health_report()
    return {"healthy": ..., "total": ..., "services": results}

# Fixed:
@app.get("/scheduler/health-report")
async def get_health_report():
    results = await daily_health_report(
        slack_client=slack_client,
        slack_channel=settings.report_slack_channel
    )
    return {"healthy": sum(1 for r in results if r["status"] == "healthy"), "total": len(results), "services": results}
```

**Step 2: Deduplicate SERVICE_ENDPOINTS**

Create a shared constant. In `webhook-handler/config.py`, add at the bottom:

```python
def get_service_endpoints():
    """Single source of truth for health check endpoints."""
    return {
        "open-webui": f"{settings.openwebui_url}/api/config",
        "mcp-proxy": f"{settings.mcp_proxy_url}/health",
        "n8n": f"{settings.n8n_url}/healthz",
        "webhook-handler": "http://localhost:8086/health",
    }
```

Then update `scheduler.py` and `handlers/commands.py` to import from config instead of defining their own.

**Step 3: Deploy and test**

```bash
scp -r webhook-handler/ root@46.224.193.25:/root/proxy-server/webhook-handler/
ssh root@46.224.193.25 "cd /root/proxy-server && docker compose -f docker-compose.unified.yml up -d --build webhook-handler"
```

Test (after Slack is configured in Task B):
```bash
ssh root@46.224.193.25 "curl -s http://localhost:8086/scheduler/health-report"
```

**Step 4: Commit**

```bash
git add webhook-handler/main.py webhook-handler/config.py webhook-handler/scheduler.py webhook-handler/handlers/commands.py
git commit -m "fix: health report posts to Slack, deduplicate SERVICE_ENDPOINTS"
```

---

### Task F: More n8n Workflow Templates

**Purpose:** Create useful n8n workflow templates that Lukas mentioned: Jira→Slack, Daily Excel Report, Weekly Digest.

**Step 1: Create Jira→Slack Alert Workflow**

On `https://n8n.srv1041674.hstgr.cloud`:

1. New Workflow → Name: "Jira → Slack Alerts"
2. Add nodes:
   - **Webhook** trigger (receives Jira webhook POST)
   - **IF** node: Check `body.webhookEvent` contains `issue_created` or `issue_updated`
   - **Set** node: Extract `issue.key`, `issue.fields.summary`, `issue.fields.priority.name`, `issue.fields.assignee.displayName`
   - **HTTP Request** (Slack): POST to Slack webhook URL with formatted message:
     ```
     🎫 *[JIRA-123] Bug title*
     Priority: High | Assignee: John
     Status: In Progress → Done
     ```
3. Activate workflow
4. Configure Jira webhook: `https://ai-ui.coolestdomain.win/n8n/webhook/jira-alerts`

**Step 2: Create Daily Excel Report Workflow**

1. New Workflow → Name: "Daily Excel Report"
2. Add nodes:
   - **Schedule Trigger**: Every day at 6 PM
   - **HTTP Request** (GitHub): GET `/repos/TheLukasHenry/proxy-server/commits?since={today}`
   - **HTTP Request** (n8n API): GET `/api/v1/executions?limit=50`
   - **HTTP Request** (Health): GET `http://webhook-handler:8086/scheduler/health-report`
   - **Code** node: Combine data into structured rows
   - **Spreadsheet File** node: Generate .xlsx with sheets: Commits, Executions, Health
   - **Send Email** or **Slack**: Attach the file and send
3. Activate workflow

**Step 3: Create Weekly Digest Workflow**

1. New Workflow → Name: "Weekly Digest"
2. Add nodes:
   - **Schedule Trigger**: Every Friday at 5 PM
   - **HTTP Request** (GitHub): GET commits + PRs from last 7 days
   - **HTTP Request** (n8n): GET all executions from last 7 days
   - **HTTP Request** (Health): Average health over the week
   - **OpenAI** node: Summarize all data into a weekly narrative
   - **Slack** or **Email**: Post the digest
3. Activate workflow

**Step 4: Verify all workflows show in MCP**

From Open WebUI chat:
```
List all active n8n workflows
```

Expected: Shows the 3 new workflows alongside the existing PR Review and Push Processor workflows.

---

### Task G: Email-to-Automation Pipeline

**Purpose:** Lukas said: "Whenever I get email that says this in subject line, make that as a trigger to document that email in Google Sheets." Build this as an n8n workflow + a Skill.

**Step 1: Create "Email to Google Sheets" n8n Workflow**

On `https://n8n.srv1041674.hstgr.cloud`:

1. New Workflow → Name: "Email → Google Sheets Logger"
2. Add nodes:
   - **Email Trigger (IMAP)**: Connect to Lukas's email (or a shared inbox)
     - Host: IMAP server
     - Credentials: Email + App Password
     - Filter: Subject contains configurable keyword
   - **IF** node: Check subject line matches rules
   - **Set** node: Extract sender, subject, date, body preview (first 200 chars)
   - **Google Sheets** node: Append row to configured spreadsheet
     - Columns: Date | From | Subject | Preview | Status
   - **Slack** notification (optional): "New email logged: [subject]"
3. Activate workflow

**Step 2: Create "Email Automation" Skill (browser)**

Navigate to `https://ai-ui.coolestdomain.win/workspace/skills` → New Skill

- Name: `Email Automation`
- Description: `Sets up email-triggered automations via n8n workflows`
- Instructions:

```
When asked about email automation, email triggers, or email-to-spreadsheet:

1. Explain available email automation capabilities:
   - Email → Google Sheets logging (already configured)
   - Email → ClickUp task creation
   - Email → Slack notification
   - Custom email rules based on subject, sender, or body content

2. To check existing email automations:
   - Use `n8n_list_workflows` to find email-related workflows
   - Use `n8n_get_executions` to check recent email processing

3. To set up a new email rule:
   - Ask: What emails should trigger the automation? (subject line filter, sender, etc.)
   - Ask: What should happen? (log to sheets, create task, notify Slack, etc.)
   - Use `n8n_create_workflow` to build the automation
   - Provide the user with the workflow ID and confirm it's active

4. For troubleshooting:
   - Check n8n execution logs for failed email processing
   - Verify IMAP credentials are still valid
   - Check Google Sheets API quota
```

**Step 3: Test the workflow**

Send a test email with the configured subject keyword and verify it appears in Google Sheets.

---

### Task H: n8n MCP Server Trigger (Bidirectional)

**Purpose:** Expose n8n workflows AS MCP tools so any AI agent can discover and call them. Uses n8n's built-in MCP Server Trigger node.

**Step 1: Create an n8n workflow with MCP Server Trigger**

On `https://n8n.srv1041674.hstgr.cloud`:

1. New Workflow → Name: "MCP: Service Health Check"
2. Add nodes:
   - **MCP Server Trigger** (this makes the workflow discoverable as an MCP tool)
     - Tool Name: `check_service_health`
     - Tool Description: `Check the health status of all AIUI platform services`
     - Input Schema: `{}` (no required inputs)
   - **HTTP Request**: GET `http://webhook-handler:8086/scheduler/health-report`
   - **Set** node: Format the response into a clean summary
   - **Respond to MCP** node: Return the formatted result
3. Activate workflow

**Step 2: Create a second MCP-exposed workflow**

1. New Workflow → Name: "MCP: Trigger Deployment"
2. Add nodes:
   - **MCP Server Trigger**
     - Tool Name: `get_deployment_status`
     - Tool Description: `Get the current deployment status and recent changes`
     - Input Schema: `{"repo": {"type": "string", "description": "Repository name"}}`
   - **HTTP Request** (GitHub): GET latest commits and deployment status
   - **Set** node: Format response
   - **Respond to MCP** node: Return result
3. Activate workflow

**Step 3: Register the n8n MCP Server endpoint with MCP Proxy**

The n8n MCP Server Trigger creates an SSE endpoint. Register it with the MCP Proxy:

```bash
ssh root@46.224.193.25 "docker exec postgres psql -U openwebui -d openwebui -c \"
INSERT INTO mcp_proxy.servers (id, name, url, description, enabled)
VALUES ('n8n-mcp-trigger', 'n8n Workflow Tools', 'http://n8n:5678/mcp', 'n8n workflows exposed as MCP tools via MCP Server Trigger', true)
ON CONFLICT (id) DO UPDATE SET url = EXCLUDED.url, description = EXCLUDED.description;
\""
```

Note: The exact URL path for the MCP Server Trigger endpoint depends on n8n's implementation. Check n8n docs for the correct SSE/Streamable HTTP URL.

**Step 4: Restart MCP Proxy to pick up new server**

```bash
ssh root@46.224.193.25 "cd /root/proxy-server && docker compose -f docker-compose.unified.yml restart mcp-proxy"
```

**Step 5: Test from Open WebUI**

Start a new chat:
```
Check the health of all AIUI services
```

Expected: AI discovers the `check_service_health` tool from the n8n MCP Server Trigger and uses it.

---

## Execution Order

| Order | Task | Effort | Dependencies |
|-------|------|--------|-------------|
| 1 | **E** Health Report → Slack | 1-2 hrs | None (code-only) |
| 2 | **D** PR → Deployment Notes | 2-3 hrs | None (code-only) |
| 3 | **A** Wrap MCPs in Skills | 1-2 hrs | None (browser-only) |
| 4 | **B** Configure Slack + Discord | 30 min + Lukas | Lukas creates apps |
| 5 | **F** n8n Workflow Templates | 2-4 hrs | n8n access |
| 6 | **C** Deploy czlonkowski/n8n-mcp | 2-3 hrs | Docker build |
| 7 | **G** Email-to-Automation | 2-4 hrs | n8n + email credentials |
| 8 | **H** n8n MCP Server Trigger | 2-3 hrs | n8n MCP node support |

**Total estimated: 12-20 hours**

---

## Rollback

All code changes are in webhook-handler (just rebuild previous image). All Skills can be toggled off or deleted from the UI. All n8n workflows can be deactivated. The MCP Proxy server registry entries can be deleted from PostgreSQL.
