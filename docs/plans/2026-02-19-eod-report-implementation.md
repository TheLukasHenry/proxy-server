# End-of-Day Report Command — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add `/aiui report` command and scheduled cron that generates AI-summarized daily reports from GitHub commits, n8n executions, and service health, posting to both command reply and Slack channel.

**Architecture:** Extend CommandRouter with a `report` subcommand. Add `get_commits_since()` to GitHubClient and `get_recent_executions()` to N8NClient. Wire scheduler to post health/EOD reports to Slack. All data gathering runs in parallel via `asyncio.gather()`, then feeds into an AI prompt for summarization.

**Tech Stack:** Python 3.11, FastAPI, httpx, APScheduler, existing OpenWebUI/GitHub/n8n/Slack clients

**Design doc:** `docs/plans/2026-02-19-eod-report-design.md`

---

### Task 1: Add config settings

**Files:**
- Modify: `webhook-handler/config.py:35-46`

**Step 1: Add new settings to the Settings class**

In `webhook-handler/config.py`, add these two fields after the `discord_bot_token` field (line 45):

```python
    # Report
    report_github_repo: str = "TheLukasHenry/proxy-server"
    report_slack_channel: str = ""
```

**Step 2: Verify config loads**

Run: `cd webhook-handler && python -c "from config import Settings; s = Settings(); print(s.report_github_repo, s.report_slack_channel)"`

Expected: `TheLukasHenry/proxy-server ` (empty string for channel)

**Step 3: Commit**

```bash
git add webhook-handler/config.py
git commit -m "feat: add report config settings (REPORT_GITHUB_REPO, REPORT_SLACK_CHANNEL)"
```

---

### Task 2: Add `get_commits_since()` to GitHubClient

**Files:**
- Modify: `webhook-handler/clients/github.py:103-148` (add after `get_pr_files`)

**Step 1: Add the method**

Add this method to the `GitHubClient` class at the end of the file (after `get_pr_files`):

```python
    async def get_commits_since(
        self,
        owner: str,
        repo: str,
        since: str,
        until: str = "",
        max_count: int = 50,
    ) -> list[dict]:
        """
        Get commits from a repo since a given ISO timestamp.

        Args:
            owner: Repository owner
            repo: Repository name
            since: ISO 8601 timestamp (e.g., '2026-02-19T00:00:00Z')
            until: Optional ISO 8601 upper bound
            max_count: Maximum commits to return

        Returns:
            List of {sha, author, message, date} dicts, or empty list on error
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/commits"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        params = {"since": since, "per_page": min(max_count, 100)}
        if until:
            params["until"] = until

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                commits = response.json()

            return [
                {
                    "sha": c["sha"][:7],
                    "author": c.get("commit", {}).get("author", {}).get("name", "unknown"),
                    "message": c.get("commit", {}).get("message", "").split("\n")[0],
                    "date": c.get("commit", {}).get("author", {}).get("date", ""),
                }
                for c in commits[:max_count]
            ]

        except Exception as e:
            logger.error(f"Error fetching commits for {owner}/{repo}: {e}")
            return []
```

**Step 2: Verify syntax**

Run: `cd webhook-handler && python -c "from clients.github import GitHubClient; print('OK')"`

Expected: `OK`

**Step 3: Commit**

```bash
git add webhook-handler/clients/github.py
git commit -m "feat: add GitHubClient.get_commits_since() for daily reports"
```

---

### Task 3: Add `get_recent_executions()` to N8NClient

**Files:**
- Modify: `webhook-handler/clients/n8n.py:63-104` (add after `trigger_workflow_by_id`)

**Step 1: Add the method**

Add this method to the `N8NClient` class at the end of the file:

```python
    async def get_recent_executions(
        self,
        limit: int = 50,
    ) -> list[dict]:
        """
        Get recent workflow executions via the n8n API.

        Args:
            limit: Maximum executions to return

        Returns:
            List of {id, workflow_name, status, started, finished} dicts,
            or empty list on error
        """
        if not self.api_key:
            logger.warning("n8n API key not set — cannot fetch executions")
            return []

        url = f"{self.base_url}/api/v1/executions"
        headers = {
            "X-N8N-API-KEY": self.api_key,
            "Accept": "application/json",
        }
        params = {"limit": limit}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()

            executions = data.get("data", data) if isinstance(data, dict) else data
            if not isinstance(executions, list):
                executions = []

            return [
                {
                    "id": ex.get("id"),
                    "workflow_name": ex.get("workflowData", {}).get("name", "unknown"),
                    "status": ex.get("status", "unknown"),
                    "started": ex.get("startedAt", ""),
                    "finished": ex.get("stoppedAt", ""),
                }
                for ex in executions
            ]

        except Exception as e:
            logger.error(f"Error fetching n8n executions: {e}")
            return []
```

**Step 2: Verify syntax**

Run: `cd webhook-handler && python -c "from clients.n8n import N8NClient; print('OK')"`

Expected: `OK`

**Step 3: Commit**

```bash
git add webhook-handler/clients/n8n.py
git commit -m "feat: add N8NClient.get_recent_executions() for daily reports"
```

---

### Task 4: Add `report` subcommand to CommandRouter

**Files:**
- Modify: `webhook-handler/handlers/commands.py`

**Step 1: Add imports**

At the top of `commands.py`, add `from datetime import datetime, timezone` after the existing imports.

**Step 2: Update `known_commands` set**

In `parse_command()` (line 71), change:
```python
        known_commands = {"ask", "workflow", "status", "help"}
```
to:
```python
        known_commands = {"ask", "workflow", "status", "help", "report"}
```

**Step 3: Add dispatch in `execute()`**

In the `execute()` method, add a new elif before the `else` branch:
```python
            elif ctx.subcommand == "report":
                await self._handle_report(ctx)
```

**Step 4: Add `_handle_report` method**

Add this method after `_handle_status`:

```python
    async def _handle_report(self, ctx: CommandContext) -> None:
        """Generate an end-of-day report with AI summary."""
        from clients.github import GitHubClient
        from config import settings

        logger.info(f"[{ctx.platform}] report from {ctx.user_name}")
        await ctx.respond("Generating report... (gathering data from GitHub, n8n, and services)")

        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

        # Gather data from all sources in parallel
        github_task = self._gather_github_commits(today_start)
        n8n_task = self._gather_n8n_executions(today_start)
        health_task = self._gather_health()

        commits, executions, health = await asyncio.gather(
            github_task, n8n_task, health_task
        )

        # Build prompt
        date_str = now.strftime("%B %d, %Y")
        sections = [f"Generate an end-of-day report for {date_str}.\n"]

        if commits is not None:
            commit_lines = [f"- `{c['sha']}` {c['author']}: {c['message']}" for c in commits]
            sections.append(f"## GitHub Commits ({len(commits)})\n" + ("\n".join(commit_lines) if commit_lines else "No commits today."))
        else:
            sections.append("## GitHub Commits\nGitHub data unavailable (no token configured).")

        if executions is not None:
            exec_lines = [f"- {e['workflow_name']}: {e['status']} (started {e['started']})" for e in executions]
            sections.append(f"## n8n Executions ({len(executions)})\n" + ("\n".join(exec_lines) if exec_lines else "No executions today."))
        else:
            sections.append("## n8n Executions\nn8n data unavailable (no API key configured).")

        health_lines = [f"- {h['service']}: {h['status']}" for h in health]
        sections.append(f"## Service Health\n" + "\n".join(health_lines))

        prompt_text = "\n\n".join(sections)

        # Get AI summary
        messages = [
            {"role": "system", "content": (
                "You are a concise daily report generator for a software team. "
                "Summarize the day's activity from GitHub commits, n8n workflow executions, "
                "and service health data. Be brief — bullet points, not paragraphs. "
                "Highlight anything notable: failures, large changes, unusual patterns."
            )},
            {"role": "user", "content": prompt_text},
        ]

        response = await self.openwebui.chat_completion(
            messages=messages,
            model=self.ai_model,
        )

        if not response:
            # Fallback to raw data
            response = f"*Daily Report — {date_str}*\n(AI summary unavailable)\n\n{prompt_text}"

        # Truncate for platform limits
        limit = 2000 if ctx.platform == "discord" else 3000
        if len(response) > limit:
            response = response[:limit - 20] + "\n\n... (truncated)"

        await ctx.respond(response)

        # Also post to Slack channel if configured
        if settings.report_slack_channel and hasattr(self, '_slack_client') and self._slack_client:
            await self._slack_client.post_message(
                channel=settings.report_slack_channel,
                text=response,
            )

    async def _gather_github_commits(self, since: str) -> Optional[list[dict]]:
        """Fetch today's commits. Returns None if not configured."""
        from clients.github import GitHubClient
        from config import settings

        if not settings.github_token:
            return None

        client = GitHubClient(token=settings.github_token)
        parts = settings.report_github_repo.split("/", 1)
        if len(parts) != 2:
            logger.error(f"Invalid REPORT_GITHUB_REPO: {settings.report_github_repo}")
            return []
        return await client.get_commits_since(owner=parts[0], repo=parts[1], since=since)

    async def _gather_n8n_executions(self, since: str) -> Optional[list[dict]]:
        """Fetch today's n8n executions. Returns None if not configured."""
        if not self.n8n.api_key:
            return None

        all_execs = await self.n8n.get_recent_executions(limit=50)
        # Filter to today only
        today_execs = [
            e for e in all_execs
            if e.get("started", "") >= since
        ]
        return today_execs

    async def _gather_health(self) -> list[dict]:
        """Check health of all services."""
        import httpx as _httpx

        results = []
        for name, url in SERVICE_ENDPOINTS.items():
            try:
                async with _httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(url)
                    status = "healthy" if resp.status_code < 400 else "unhealthy"
            except Exception:
                status = "unreachable"
            results.append({"service": name, "status": status})
        return results
```

**Step 5: Add `_slack_client` attribute to `__init__`**

Update the `CommandRouter.__init__` to accept an optional slack_client:

```python
    def __init__(
        self,
        openwebui_client: OpenWebUIClient,
        n8n_client: N8NClient,
        ai_model: str = "gpt-4-turbo",
        slack_client=None,
    ):
        self.openwebui = openwebui_client
        self.n8n = n8n_client
        self.ai_model = ai_model
        self._slack_client = slack_client
```

**Step 6: Update help text**

In `_handle_help`, add the report line:

```python
            "`/aiui report` — Generate end-of-day activity report\n"
```

**Step 7: Verify syntax**

Run: `cd webhook-handler && python -c "from handlers.commands import CommandRouter; print('OK')"`

Expected: `OK`

**Step 8: Commit**

```bash
git add webhook-handler/handlers/commands.py
git commit -m "feat: add /aiui report command with AI-summarized daily reports"
```

---

### Task 5: Wire slack_client into CommandRouter in main.py

**Files:**
- Modify: `webhook-handler/main.py:94-99`

**Step 1: Pass slack_client to CommandRouter**

In `main.py` inside the `lifespan()` function, the `CommandRouter` is created at line 95. Change:

```python
    command_router = CommandRouter(
        openwebui_client=openwebui_client,
        n8n_client=n8n_client,
        ai_model=settings.ai_model,
    )
```

to:

```python
    command_router = CommandRouter(
        openwebui_client=openwebui_client,
        n8n_client=n8n_client,
        ai_model=settings.ai_model,
        slack_client=slack_client,
    )
```

Note: `slack_client` is initialized AFTER the CommandRouter currently. Move the CommandRouter creation to AFTER the Slack client initialization block (after line 116). The Slack client block creates `slack_client` only if `settings.slack_bot_token` is set, so `slack_client` may still be `None` — that's fine, the CommandRouter handles it.

**Step 2: Verify syntax**

Run: `cd webhook-handler && python -c "from main import app; print('OK')"`

Expected: `OK`

**Step 3: Commit**

```bash
git add webhook-handler/main.py
git commit -m "feat: wire slack_client into CommandRouter for report Slack posting"
```

---

### Task 6: Wire health report to Slack + add EOD cron job

**Files:**
- Modify: `webhook-handler/scheduler.py`
- Modify: `webhook-handler/main.py`

**Step 1: Update `daily_health_report()` to accept and use slack_client**

In `scheduler.py`, change the `daily_health_report` function signature and body:

```python
async def daily_health_report(slack_client=None, slack_channel: str = ""):
    """
    Daily health check of all services.

    Runs at noon every day. Checks every registered service endpoint,
    logs the results, and posts to Slack if configured.
    """
    logger.info("=== Daily Health Report ===")
    results = []
    for name, url in SERVICE_ENDPOINTS.items():
        result = await _check_service_health(name, url)
        results.append(result)
        status_emoji = "OK" if result["status"] == "healthy" else "FAIL"
        logger.info(f"  [{status_emoji}] {name}: {result['status']} ({url})")

    healthy = sum(1 for r in results if r["status"] == "healthy")
    total = len(results)
    logger.info(f"=== Health Report: {healthy}/{total} services healthy ===")

    # Post to Slack if configured
    if slack_client and slack_channel:
        lines = [f"*Service Health Report* ({healthy}/{total} healthy)\n"]
        for r in results:
            emoji = "white_check_mark" if r["status"] == "healthy" else "x"
            lines.append(f":{emoji}: {r['service']}: {r['status']}")
        try:
            await slack_client.post_message(channel=slack_channel, text="\n".join(lines))
        except Exception as e:
            logger.error(f"Failed to post health report to Slack: {e}")

    return results
```

**Step 2: Update `register_default_jobs()` to accept slack params**

```python
def register_default_jobs(slack_client=None, slack_channel: str = ""):
    """Register the built-in scheduled jobs."""
    if not scheduler:
        logger.error("Cannot register jobs: scheduler not initialized")
        return

    # Daily health report at noon (12:00)
    add_cron_job(
        func=daily_health_report,
        job_id="daily_health_report",
        cron_expression="0 12 * * *",
        slack_client=slack_client,
        slack_channel=slack_channel,
    )

    # Hourly n8n workflow status check (every hour at :00)
    add_cron_job(
        func=hourly_n8n_workflow_check,
        job_id="hourly_n8n_check",
        cron_expression="0 * * * *",
    )

    job_count = len(scheduler.get_jobs()) if scheduler else 0
    logger.info(f"Registered {job_count} default scheduled jobs")
```

**Step 3: Update main.py to pass slack params to scheduler**

In `main.py`, change the `register_default_jobs()` call (around line 147):

```python
    register_default_jobs(
        slack_client=slack_client,
        slack_channel=settings.report_slack_channel,
    )
```

**Step 4: Verify syntax**

Run: `cd webhook-handler && python -c "from scheduler import daily_health_report, register_default_jobs; print('OK')"`

Expected: `OK`

**Step 5: Commit**

```bash
git add webhook-handler/scheduler.py webhook-handler/main.py
git commit -m "feat: wire health report to Slack, pass slack_client to scheduler"
```

---

### Task 7: Add env vars to docker-compose.unified.yml

**Files:**
- Modify: `docker-compose.unified.yml` (webhook-handler service env block)

**Step 1: Add new env vars**

In the webhook-handler environment section (around line 117, after the DISCORD vars), add:

```yaml
      - REPORT_GITHUB_REPO=${REPORT_GITHUB_REPO:-TheLukasHenry/proxy-server}
      - REPORT_SLACK_CHANNEL=${REPORT_SLACK_CHANNEL:-}
```

**Step 2: Commit**

```bash
git add docker-compose.unified.yml
git commit -m "feat: add REPORT_GITHUB_REPO and REPORT_SLACK_CHANNEL env vars"
```

---

### Task 8: Final integration commit + push

**Step 1: Verify all files are clean**

Run: `git status`

Expected: clean working tree

**Step 2: Push to remote**

```bash
git push proxy-server fix/mcp-network-split
```

**Step 3: Update PR**

Update PR #10 description to include the EOD report feature.
