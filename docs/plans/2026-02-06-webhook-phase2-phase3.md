# Webhook Phase 2 & Phase 3 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend the webhook-handler service from GitHub-issues-only to support extended GitHub events (PRs, comments, push), MCP tool execution via webhook, n8n workflow integration, Slack integration, scheduled triggers, and a generic webhook endpoint.

**Architecture:** The webhook-handler is a FastAPI service (`webhook-handler/`) that receives webhooks, routes them to event-specific handlers, calls Open WebUI for AI analysis, and posts responses back to the source. New phases add more event types, more trigger sources (Slack, cron, generic), and new output targets (MCP Proxy direct calls, n8n workflows). Each phase is additive — new files and new handler methods only, no modification to existing working code paths.

**Tech Stack:** Python 3.11, FastAPI, httpx, pydantic-settings, APScheduler (Phase 2D), Docker Compose

---

## Existing Code Map (DO NOT MODIFY unless specified)

```
webhook-handler/
├── main.py              # FastAPI app, /webhook/github endpoint, lifespan init
├── config.py            # Settings(BaseSettings) — port, tokens, URLs, ai_model
├── Dockerfile           # Python 3.11-slim, port 8086
├── requirements.txt     # fastapi, uvicorn, httpx, pydantic, pydantic-settings, python-dotenv
├── handlers/
│   ├── __init__.py
│   └── github.py        # GitHubWebhookHandler.handle_event() → _handle_issue_event() → _analyze_and_comment()
└── clients/
    ├── __init__.py
    ├── openwebui.py     # OpenWebUIClient.chat_completion(), .analyze_github_issue()
    └── github.py        # GitHubClient.post_issue_comment(), .format_ai_response(), verify_github_signature()
```

**Deployed at:** Hetzner 46.224.193.25, port 8086, Caddy routes `/webhook/*`, Docker network `backend`

**Docker Compose:** `docker-compose.unified.yml` — webhook-handler service on `backend` network, depends on `open-webui`

**MCP Proxy:** Accepts `POST /{server_id}/{tool_path}` with `X-User-Email` + `X-User-Groups` headers (when `API_GATEWAY_MODE=true`). Returns JSON response from the tool server.

---

## PHASE 2A: Extended GitHub Events

**Priority:** HIGH | **Effort:** LOW
**What:** Handle pull_request, issue_comment, and push events in addition to existing issues.

---

### Task 1: Add PR analysis method to OpenWebUI client

**Files:**
- Modify: `webhook-handler/clients/openwebui.py:68-117` (add new method after `analyze_github_issue`)

**Step 1: Add `analyze_pull_request()` method**

Add this method to the `OpenWebUIClient` class in `webhook-handler/clients/openwebui.py`, after the existing `analyze_github_issue` method (after line 117):

```python
    async def analyze_pull_request(
        self,
        title: str,
        body: str,
        diff_summary: str,
        labels: list[str],
        model: str = "gpt-4-turbo",
        system_prompt: str = ""
    ) -> Optional[str]:
        """
        Analyze a GitHub pull request and return AI review.

        Args:
            title: PR title
            body: PR body/description
            diff_summary: Summary of files changed
            labels: List of label names
            model: Model to use
            system_prompt: System prompt for the AI

        Returns:
            AI review text, or None on error
        """
        if not system_prompt:
            system_prompt = (
                "You are a helpful AI code reviewer. Review pull requests "
                "and provide constructive feedback. Be concise and actionable."
            )

        labels_str = ", ".join(labels) if labels else "none"

        user_prompt = f"""Review this GitHub pull request:

**Title:** {title}

**Description:**
{body or "No description provided."}

**Files Changed:**
{diff_summary or "No diff summary available."}

**Labels:** {labels_str}

Please provide:
1. Brief summary of the changes
2. Potential issues or concerns
3. Suggestions for improvement
4. Overall assessment"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        return await self.chat_completion(messages, model=model)

    async def analyze_comment(
        self,
        context_title: str,
        context_body: str,
        comment_body: str,
        comment_author: str,
        model: str = "gpt-4-turbo",
        system_prompt: str = ""
    ) -> Optional[str]:
        """
        Analyze a GitHub comment (on issue or PR) and return AI response.

        Args:
            context_title: Title of the issue/PR being commented on
            context_body: Body of the issue/PR
            comment_body: The comment text
            comment_author: Who wrote the comment
            model: Model to use
            system_prompt: System prompt for the AI

        Returns:
            AI response text, or None on error
        """
        if not system_prompt:
            system_prompt = (
                "You are a helpful AI assistant responding to GitHub comments. "
                "Be concise, helpful, and actionable."
            )

        user_prompt = f"""Respond to this GitHub comment:

**Context (Issue/PR Title):** {context_title}

**Context (Issue/PR Body):**
{context_body or "No description provided."}

**Comment by {comment_author}:**
{comment_body}

Please provide a helpful response."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        return await self.chat_completion(messages, model=model)

    async def analyze_push(
        self,
        commits: list[dict],
        branch: str,
        pusher: str,
        model: str = "gpt-4-turbo",
        system_prompt: str = ""
    ) -> Optional[str]:
        """
        Analyze a GitHub push event and return AI summary.

        Args:
            commits: List of commit dicts with 'message', 'author', 'url'
            branch: Branch name
            pusher: Who pushed
            model: Model to use
            system_prompt: System prompt for the AI

        Returns:
            AI summary text, or None on error
        """
        if not system_prompt:
            system_prompt = (
                "You are a helpful AI assistant that analyzes git push events. "
                "Summarize changes and detect patterns. Be concise."
            )

        commits_text = ""
        for c in commits[:10]:  # Limit to 10 commits
            msg = c.get("message", "No message")
            author = c.get("author", {}).get("name", "Unknown")
            commits_text += f"- {author}: {msg}\n"

        user_prompt = f"""Analyze this push event:

**Branch:** {branch}
**Pushed by:** {pusher}

**Commits ({len(commits)}):**
{commits_text}

Please provide:
1. Summary of changes
2. Any patterns detected (bug fixes, features, refactoring)
3. Any concerns"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        return await self.chat_completion(messages, model=model)
```

**Step 2: Verify no syntax errors**

Run: `cd "C:\Users\alama\Desktop\Lukas Work\IO\webhook-handler" && python -c "from clients.openwebui import OpenWebUIClient; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add webhook-handler/clients/openwebui.py
git commit -m "feat(webhook): add PR, comment, and push analysis methods to OpenWebUI client"
```

---

### Task 2: Add PR comment method to GitHub client

**Files:**
- Modify: `webhook-handler/clients/github.py:86-103` (add new method after `post_issue_comment`)

**Step 1: Add `post_pr_review_comment()` and `get_pr_diff()` methods**

Add these methods to the `GitHubClient` class in `webhook-handler/clients/github.py`, after the existing `format_ai_response` method (after line 102):

```python
    async def get_pr_files(
        self,
        owner: str,
        repo: str,
        pr_number: int
    ) -> Optional[str]:
        """
        Get a summary of files changed in a PR.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number

        Returns:
            Summary string of changed files, or None on error
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/files"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()

                files = response.json()
                summary_lines = []
                for f in files[:30]:  # Limit to 30 files
                    filename = f.get("filename", "unknown")
                    status = f.get("status", "modified")
                    additions = f.get("additions", 0)
                    deletions = f.get("deletions", 0)
                    summary_lines.append(
                        f"- {filename} ({status}: +{additions}/-{deletions})"
                    )

                return "\n".join(summary_lines) if summary_lines else "No files changed"

        except Exception as e:
            logger.error(f"Error getting PR files: {e}")
            return None
```

**Step 2: Verify no syntax errors**

Run: `cd "C:\Users\alama\Desktop\Lukas Work\IO\webhook-handler" && python -c "from clients.github import GitHubClient; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add webhook-handler/clients/github.py
git commit -m "feat(webhook): add get_pr_files method to GitHub client"
```

---

### Task 3: Add PR, comment, and push handlers to GitHubWebhookHandler

**Files:**
- Modify: `webhook-handler/handlers/github.py` (add new handler methods and update `handle_event`)

**Step 1: Update `handle_event()` to route new event types**

In `webhook-handler/handlers/github.py`, replace the `handle_event` method body (lines 41-47) to add new event routing:

```python
    async def handle_event(
        self,
        event_type: str,
        payload: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Handle a GitHub webhook event.

        Args:
            event_type: GitHub event type (e.g., 'issues', 'pull_request')
            payload: Webhook payload

        Returns:
            Result dict with success status and details
        """
        if event_type == "issues":
            return await self._handle_issue_event(payload)
        elif event_type == "pull_request":
            return await self._handle_pull_request_event(payload)
        elif event_type == "issue_comment":
            return await self._handle_comment_event(payload)
        elif event_type == "push":
            return await self._handle_push_event(payload)
        elif event_type == "ping":
            return {"success": True, "message": "Pong!"}
        else:
            logger.info(f"Ignoring unsupported event type: {event_type}")
            return {"success": True, "message": f"Event type '{event_type}' not handled"}
```

**Step 2: Add `_handle_pull_request_event()` method**

Add after `_analyze_and_comment()` (after line 111):

```python
    async def _handle_pull_request_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Handle pull request events (opened, synchronize)."""
        action = payload.get("action")

        if action not in ("opened", "synchronize"):
            logger.info(f"Ignoring PR action: {action}")
            return {"success": True, "message": f"PR action '{action}' not handled"}

        pr = payload.get("pull_request", {})
        repo = payload.get("repository", {})

        pr_number = pr.get("number")
        title = pr.get("title", "")
        body = pr.get("body", "")
        labels = [label.get("name", "") for label in pr.get("labels", [])]

        repo_full_name = repo.get("full_name", "")
        if "/" not in repo_full_name:
            logger.error(f"Invalid repository name: {repo_full_name}")
            return {"success": False, "error": "Invalid repository name"}

        owner, repo_name = repo_full_name.split("/", 1)

        logger.info(f"Analyzing PR #{pr_number}: {title} (action: {action})")

        # Get PR file changes summary
        diff_summary = await self.github.get_pr_files(
            owner=owner,
            repo=repo_name,
            pr_number=pr_number
        )

        # Get AI analysis
        analysis = await self.openwebui.analyze_pull_request(
            title=title,
            body=body,
            diff_summary=diff_summary or "Could not retrieve file changes",
            labels=labels,
            model=self.ai_model,
            system_prompt=self.ai_system_prompt
        )

        if not analysis:
            logger.error("Failed to get AI analysis for PR")
            return {"success": False, "error": "Failed to get AI analysis"}

        # Post comment on PR (uses same issues API)
        comment_body = self.github.format_ai_response(analysis)
        comment_id = await self.github.post_issue_comment(
            owner=owner,
            repo=repo_name,
            issue_number=pr_number,
            body=comment_body
        )

        if not comment_id:
            logger.error("Failed to post PR comment")
            return {"success": False, "error": "Failed to post comment"}

        logger.info(f"Successfully posted comment {comment_id} on PR #{pr_number}")
        return {
            "success": True,
            "message": "PR analyzed, comment posted",
            "pr_number": pr_number,
            "comment_id": comment_id
        }

    async def _handle_comment_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Handle issue_comment events (created)."""
        action = payload.get("action")

        if action != "created":
            logger.info(f"Ignoring comment action: {action}")
            return {"success": True, "message": f"Comment action '{action}' not handled"}

        comment = payload.get("comment", {})
        issue = payload.get("issue", {})
        repo = payload.get("repository", {})

        # Skip bot comments to avoid infinite loops
        comment_author = comment.get("user", {}).get("login", "")
        if comment.get("user", {}).get("type") == "Bot":
            logger.info(f"Ignoring bot comment from {comment_author}")
            return {"success": True, "message": "Skipped bot comment"}

        comment_body_text = comment.get("body", "")
        issue_number = issue.get("number")
        issue_title = issue.get("title", "")
        issue_body = issue.get("body", "")

        repo_full_name = repo.get("full_name", "")
        if "/" not in repo_full_name:
            logger.error(f"Invalid repository name: {repo_full_name}")
            return {"success": False, "error": "Invalid repository name"}

        owner, repo_name = repo_full_name.split("/", 1)

        logger.info(f"Analyzing comment by {comment_author} on #{issue_number}")

        # Get AI response
        analysis = await self.openwebui.analyze_comment(
            context_title=issue_title,
            context_body=issue_body,
            comment_body=comment_body_text,
            comment_author=comment_author,
            model=self.ai_model,
            system_prompt=self.ai_system_prompt
        )

        if not analysis:
            logger.error("Failed to get AI analysis for comment")
            return {"success": False, "error": "Failed to get AI analysis"}

        # Post reply
        reply_body = self.github.format_ai_response(analysis)
        comment_id = await self.github.post_issue_comment(
            owner=owner,
            repo=repo_name,
            issue_number=issue_number,
            body=reply_body
        )

        if not comment_id:
            logger.error("Failed to post reply comment")
            return {"success": False, "error": "Failed to post comment"}

        logger.info(f"Successfully posted reply {comment_id} on #{issue_number}")
        return {
            "success": True,
            "message": "Comment analyzed, reply posted",
            "issue_number": issue_number,
            "comment_id": comment_id
        }

    async def _handle_push_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Handle push events — summarize commits."""
        ref = payload.get("ref", "")
        branch = ref.replace("refs/heads/", "") if ref.startswith("refs/heads/") else ref
        pusher = payload.get("pusher", {}).get("name", "unknown")
        commits = payload.get("commits", [])
        repo = payload.get("repository", {})

        if not commits:
            logger.info("Push event with no commits, ignoring")
            return {"success": True, "message": "No commits in push"}

        repo_full_name = repo.get("full_name", "")
        if "/" not in repo_full_name:
            logger.error(f"Invalid repository name: {repo_full_name}")
            return {"success": False, "error": "Invalid repository name"}

        owner, repo_name = repo_full_name.split("/", 1)

        logger.info(f"Analyzing push to {branch} by {pusher} ({len(commits)} commits)")

        # Get AI analysis
        analysis = await self.openwebui.analyze_push(
            commits=commits,
            branch=branch,
            pusher=pusher,
            model=self.ai_model,
            system_prompt=self.ai_system_prompt
        )

        if not analysis:
            logger.error("Failed to get AI analysis for push")
            return {"success": False, "error": "Failed to get AI analysis"}

        # For push events, we log the analysis but don't post anywhere by default
        # (no single issue/PR to comment on). Could be extended to post to Slack, etc.
        logger.info(f"Push analysis complete for {branch}: {analysis[:200]}...")
        return {
            "success": True,
            "message": "Push analyzed",
            "branch": branch,
            "commit_count": len(commits),
            "analysis_preview": analysis[:500]
        }
```

**Step 3: Verify no syntax errors**

Run: `cd "C:\Users\alama\Desktop\Lukas Work\IO\webhook-handler" && python -c "from handlers.github import GitHubWebhookHandler; print('OK')"`
Expected: `OK`

**Step 4: Commit**

```bash
git add webhook-handler/handlers/github.py
git commit -m "feat(webhook): add PR, comment, and push event handlers"
```

---

### Task 4: Update GitHub webhook configuration to receive new events

**Step 1: Update webhook via GitHub API**

The existing webhook on `TheLukasHenry/proxy-server` only receives `issues` and `ping` events. Update it to also receive `pull_request`, `issue_comment`, and `push`:

```bash
# List existing webhooks to find the ID
curl -s -H "Authorization: Bearer $GITHUB_TOKEN" \
  "https://api.github.com/repos/TheLukasHenry/proxy-server/hooks" | python -m json.tool

# Update the webhook (replace HOOK_ID with the actual ID from above)
curl -s -X PATCH \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/TheLukasHenry/proxy-server/hooks/HOOK_ID" \
  -d '{"events": ["issues", "pull_request", "issue_comment", "push"]}'
```

**Step 2: Verify webhook config**

Check at: `https://github.com/TheLukasHenry/proxy-server/settings/hooks`

Events should now list: Issues, Pull requests, Issue comments, Pushes

**Step 3: No commit needed (GitHub-side config only)**

---

### Task 5: Deploy and test Phase 2A

**Step 1: Rebuild and deploy webhook-handler**

```bash
ssh root@46.224.193.25 "cd /opt/proxy-server && docker compose -f docker-compose.unified.yml build webhook-handler && docker compose -f docker-compose.unified.yml up -d webhook-handler"
```

**Step 2: Test health endpoint**

```bash
curl -s https://ai-ui.coolestdomain.win/webhook/health
```
Expected: `{"status":"healthy","service":"webhook-handler","version":"1.0.0"}`

**Step 3: Test with a PR (manual test)**

Create a test PR on `TheLukasHenry/proxy-server` and verify the AI analysis comment appears.

**Step 4: Commit (if any deployment config changes)**

```bash
git add -A
git commit -m "chore: deploy Phase 2A extended GitHub events"
```

---

## PHASE 3B: MCP Tools via Webhook

**Priority:** HIGH | **Effort:** MEDIUM
**What:** Call MCP Proxy tools directly from webhook events, bypassing Open WebUI API limitations.

---

### Task 6: Add MCP Proxy config to Settings

**Files:**
- Modify: `webhook-handler/config.py` (add MCP Proxy settings)

**Step 1: Add MCP Proxy environment variables**

In `webhook-handler/config.py`, add these fields to the `Settings` class (after line 24, before `class Config`):

```python
    # MCP Proxy
    mcp_proxy_url: str = "http://mcp-proxy:8000"
    mcp_user_email: str = "webhook-handler@system"
    mcp_user_groups: str = "MCP-Admin"
```

**Step 2: Verify no syntax errors**

Run: `cd "C:\Users\alama\Desktop\Lukas Work\IO\webhook-handler" && python -c "from config import settings; print(settings.mcp_proxy_url)"`
Expected: `http://mcp-proxy:8000`

**Step 3: Commit**

```bash
git add webhook-handler/config.py
git commit -m "feat(webhook): add MCP Proxy config settings"
```

---

### Task 7: Create MCP Proxy client

**Files:**
- Create: `webhook-handler/clients/mcp_proxy.py`

**Step 1: Create the MCP Proxy client**

Create `webhook-handler/clients/mcp_proxy.py`:

```python
"""MCP Proxy client for executing MCP tools directly."""
import httpx
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


class MCPProxyClient:
    """Client for calling MCP Proxy tool endpoints directly."""

    def __init__(self, base_url: str, user_email: str, user_groups: str):
        self.base_url = base_url.rstrip("/")
        self.user_email = user_email
        self.user_groups = user_groups
        self.timeout = 30.0

    async def execute_tool(
        self,
        server_id: str,
        tool_name: str,
        arguments: dict[str, Any] = None
    ) -> Optional[dict[str, Any]]:
        """
        Execute an MCP tool via the MCP Proxy.

        Args:
            server_id: MCP server ID (e.g., 'github', 'jira', 'linear')
            tool_name: Tool name (e.g., 'get_me', 'create_issue')
            arguments: Tool arguments dict

        Returns:
            Tool response dict, or None on error
        """
        url = f"{self.base_url}/{server_id}/{tool_name}"
        headers = {
            "X-User-Email": self.user_email,
            "X-User-Groups": self.user_groups,
            "Content-Type": "application/json"
        }
        body = arguments or {}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=body, headers=headers)
                response.raise_for_status()

                result = response.json()
                logger.info(f"MCP tool {server_id}/{tool_name} executed successfully")
                return result

        except httpx.HTTPStatusError as e:
            logger.error(
                f"MCP Proxy error for {server_id}/{tool_name}: "
                f"{e.response.status_code} - {e.response.text}"
            )
            return None
        except httpx.TimeoutException:
            logger.error(f"Timeout calling MCP Proxy for {server_id}/{tool_name}")
            return None
        except Exception as e:
            logger.error(f"Error calling MCP Proxy: {e}")
            return None

    async def list_tools(self, server_id: str) -> Optional[list[dict]]:
        """
        List available tools for an MCP server.

        Args:
            server_id: MCP server ID

        Returns:
            List of tool dicts, or None on error
        """
        url = f"{self.base_url}/tools"
        headers = {
            "X-User-Email": self.user_email,
            "X-User-Groups": self.user_groups
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()

                all_tools = response.json()
                # Filter to specified server
                server_tools = [
                    t for t in all_tools
                    if t.get("server_id") == server_id
                ]
                return server_tools

        except Exception as e:
            logger.error(f"Error listing MCP tools: {e}")
            return None
```

**Step 2: Verify no syntax errors**

Run: `cd "C:\Users\alama\Desktop\Lukas Work\IO\webhook-handler" && python -c "from clients.mcp_proxy import MCPProxyClient; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add webhook-handler/clients/mcp_proxy.py
git commit -m "feat(webhook): add MCP Proxy client for direct tool execution"
```

---

### Task 8: Create MCP webhook handler

**Files:**
- Create: `webhook-handler/handlers/mcp.py`

**Step 1: Create the MCP handler**

Create `webhook-handler/handlers/mcp.py`:

```python
"""MCP webhook handler — execute MCP tools via webhook triggers."""
from typing import Any, Optional
import logging

from clients.mcp_proxy import MCPProxyClient

logger = logging.getLogger(__name__)


class MCPWebhookHandler:
    """Handler for MCP tool execution via webhooks."""

    def __init__(self, mcp_client: MCPProxyClient):
        self.mcp = mcp_client

    async def handle_tool_request(
        self,
        server_id: str,
        tool_name: str,
        arguments: dict[str, Any] = None
    ) -> dict[str, Any]:
        """
        Execute an MCP tool and return the result.

        Args:
            server_id: MCP server ID (e.g., 'github', 'jira')
            tool_name: Tool name to execute
            arguments: Tool arguments

        Returns:
            Result dict with success status and tool output
        """
        logger.info(f"Executing MCP tool: {server_id}/{tool_name}")

        result = await self.mcp.execute_tool(
            server_id=server_id,
            tool_name=tool_name,
            arguments=arguments or {}
        )

        if result is None:
            logger.error(f"MCP tool execution failed: {server_id}/{tool_name}")
            return {
                "success": False,
                "error": f"Failed to execute {server_id}/{tool_name}"
            }

        logger.info(f"MCP tool {server_id}/{tool_name} completed successfully")
        return {
            "success": True,
            "message": f"Tool {server_id}/{tool_name} executed",
            "result": result
        }
```

**Step 2: Verify no syntax errors**

Run: `cd "C:\Users\alama\Desktop\Lukas Work\IO\webhook-handler" && python -c "from handlers.mcp import MCPWebhookHandler; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add webhook-handler/handlers/mcp.py
git commit -m "feat(webhook): add MCP webhook handler for tool execution"
```

---

### Task 9: Add MCP webhook endpoint to main.py

**Files:**
- Modify: `webhook-handler/main.py` (add MCP imports, init, and endpoint)

**Step 1: Add imports**

In `webhook-handler/main.py`, add after line 11 (after the `GitHubWebhookHandler` import):

```python
from clients.mcp_proxy import MCPProxyClient
from handlers.mcp import MCPWebhookHandler
```

**Step 2: Add global variable**

After line 23 (after `github_handler` global), add:

```python
mcp_handler: Optional[MCPWebhookHandler] = None
```

**Step 3: Initialize MCP client in lifespan**

In the `lifespan()` function, after the `github_handler` initialization (after line 45), add:

```python
    global mcp_handler

    mcp_client = MCPProxyClient(
        base_url=settings.mcp_proxy_url,
        user_email=settings.mcp_user_email,
        user_groups=settings.mcp_user_groups
    )

    mcp_handler = MCPWebhookHandler(mcp_client=mcp_client)
    logger.info(f"MCP Proxy URL: {settings.mcp_proxy_url}")
```

**Step 4: Add the MCP webhook endpoint**

After the `github_webhook` endpoint (after line 113), add:

```python
@app.post("/webhook/mcp/{server_id}/{tool_name}")
async def mcp_webhook(
    request: Request,
    server_id: str,
    tool_name: str
):
    """
    Execute an MCP tool directly via webhook.

    POST /webhook/mcp/{server_id}/{tool_name}
    Body: JSON with tool arguments
    """
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    logger.info(f"MCP webhook: {server_id}/{tool_name}")

    result = await mcp_handler.handle_tool_request(
        server_id=server_id,
        tool_name=tool_name,
        arguments=payload
    )

    if result.get("success"):
        return JSONResponse(content=result, status_code=200)
    else:
        return JSONResponse(content=result, status_code=500)
```

**Step 5: Verify no syntax errors**

Run: `cd "C:\Users\alama\Desktop\Lukas Work\IO\webhook-handler" && python -c "from main import app; print('OK')"`
Expected: `OK`

**Step 6: Commit**

```bash
git add webhook-handler/main.py
git commit -m "feat(webhook): add MCP tool endpoint POST /webhook/mcp/{server_id}/{tool_name}"
```

---

### Task 10: Add MCP Proxy env vars to Docker Compose

**Files:**
- Modify: `docker-compose.unified.yml` (add MCP env vars to webhook-handler service)

**Step 1: Add environment variables**

In `docker-compose.unified.yml`, add these lines to the `webhook-handler` service `environment` section (after the `AI_MODEL` line):

```yaml
    - MCP_PROXY_URL=http://mcp-proxy:8000
    - MCP_USER_EMAIL=webhook-handler@system
    - MCP_USER_GROUPS=MCP-Admin
```

**Step 2: Add network for MCP Proxy access**

The webhook-handler is on the `backend` network, but MCP Proxy is on both `backend` and `internal`. Since they share `backend`, connectivity should work. Verify by checking:

```bash
ssh root@46.224.193.25 "docker network inspect proxy-server_backend | grep -A2 mcp-proxy"
```

If MCP Proxy is NOT on `backend`, add `internal` network to webhook-handler:

```yaml
  networks:
    - backend
    - internal
```

**Step 3: Commit**

```bash
git add docker-compose.unified.yml
git commit -m "feat(webhook): add MCP Proxy env vars to webhook-handler Docker config"
```

---

### Task 11: Deploy and test Phase 3B

**Step 1: Rebuild and deploy**

```bash
ssh root@46.224.193.25 "cd /opt/proxy-server && docker compose -f docker-compose.unified.yml build webhook-handler && docker compose -f docker-compose.unified.yml up -d webhook-handler"
```

**Step 2: Test MCP tool execution via webhook**

```bash
# Test: Call github/get_me through the webhook MCP endpoint
curl -s -X POST \
  https://ai-ui.coolestdomain.win/webhook/mcp/github/get_me \
  -H "Content-Type: application/json" \
  -d '{}'
```

Expected: JSON response with GitHub user info (TheLukasHenry)

**Step 3: Commit if any fixes needed**

---

## PHASE 3A: n8n Workflow Integration

**Priority:** HIGH | **Effort:** MEDIUM
**What:** Deploy n8n and allow webhook-handler to trigger n8n workflows for complex multi-step automations.

---

### Task 12: Add n8n config to Settings

**Files:**
- Modify: `webhook-handler/config.py`

**Step 1: Add n8n settings**

In `webhook-handler/config.py`, add after the MCP Proxy settings:

```python
    # n8n
    n8n_url: str = "http://n8n:5678"
    n8n_api_key: str = ""
```

**Step 2: Commit**

```bash
git add webhook-handler/config.py
git commit -m "feat(webhook): add n8n config settings"
```

---

### Task 13: Create n8n client

**Files:**
- Create: `webhook-handler/clients/n8n.py`

**Step 1: Create the n8n client**

Create `webhook-handler/clients/n8n.py`:

```python
"""n8n workflow automation client."""
import httpx
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


class N8NClient:
    """Client for triggering n8n workflows via webhook nodes."""

    def __init__(self, base_url: str, api_key: str = ""):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = 60.0  # n8n workflows can be slow

    async def trigger_workflow(
        self,
        webhook_path: str,
        payload: dict[str, Any] = None
    ) -> Optional[dict[str, Any]]:
        """
        Trigger an n8n workflow via its webhook node.

        n8n webhook URLs follow the pattern:
        {base_url}/webhook/{webhook_path}

        Args:
            webhook_path: The webhook path configured in n8n (e.g., 'github-issue')
            payload: JSON payload to send to the workflow

        Returns:
            Workflow response dict, or None on error
        """
        url = f"{self.base_url}/webhook/{webhook_path}"
        headers = {"Content-Type": "application/json"}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    json=payload or {},
                    headers=headers
                )
                response.raise_for_status()

                result = response.json()
                logger.info(f"n8n workflow triggered: {webhook_path}")
                return result

        except httpx.HTTPStatusError as e:
            logger.error(
                f"n8n error for {webhook_path}: "
                f"{e.response.status_code} - {e.response.text}"
            )
            return None
        except httpx.TimeoutException:
            logger.error(f"Timeout triggering n8n workflow: {webhook_path}")
            return None
        except Exception as e:
            logger.error(f"Error triggering n8n workflow: {e}")
            return None

    async def trigger_workflow_by_id(
        self,
        workflow_id: str,
        payload: dict[str, Any] = None
    ) -> Optional[dict[str, Any]]:
        """
        Trigger an n8n workflow via the API (requires API key).

        Args:
            workflow_id: n8n workflow ID
            payload: JSON payload

        Returns:
            Execution result dict, or None on error
        """
        if not self.api_key:
            logger.error("n8n API key required for workflow-by-id execution")
            return None

        url = f"{self.base_url}/api/v1/workflows/{workflow_id}/execute"
        headers = {
            "Content-Type": "application/json",
            "X-N8N-API-KEY": self.api_key
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    json={"data": payload or {}},
                    headers=headers
                )
                response.raise_for_status()

                result = response.json()
                logger.info(f"n8n workflow {workflow_id} executed via API")
                return result

        except Exception as e:
            logger.error(f"Error executing n8n workflow {workflow_id}: {e}")
            return None
```

**Step 2: Verify no syntax errors**

Run: `cd "C:\Users\alama\Desktop\Lukas Work\IO\webhook-handler" && python -c "from clients.n8n import N8NClient; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add webhook-handler/clients/n8n.py
git commit -m "feat(webhook): add n8n workflow client"
```

---

### Task 14: Add n8n webhook endpoint to main.py

**Files:**
- Modify: `webhook-handler/main.py`

**Step 1: Add imports**

Add after the MCP imports:

```python
from clients.n8n import N8NClient
```

**Step 2: Add global variable**

After the `mcp_handler` global:

```python
n8n_client: Optional[N8NClient] = None
```

**Step 3: Initialize in lifespan**

After the `mcp_handler` initialization, add:

```python
    global n8n_client

    n8n_client = N8NClient(
        base_url=settings.n8n_url,
        api_key=settings.n8n_api_key
    )
    logger.info(f"n8n URL: {settings.n8n_url}")
```

**Step 4: Add n8n webhook endpoint**

After the MCP webhook endpoint, add:

```python
@app.post("/webhook/n8n/{workflow_path:path}")
async def n8n_webhook(
    request: Request,
    workflow_path: str
):
    """
    Forward a webhook payload to an n8n workflow.

    POST /webhook/n8n/{workflow_path}
    Body: JSON payload forwarded to n8n webhook node
    """
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    logger.info(f"n8n webhook forward: {workflow_path}")

    result = await n8n_client.trigger_workflow(
        webhook_path=workflow_path,
        payload=payload
    )

    if result is not None:
        return JSONResponse(content={"success": True, "result": result}, status_code=200)
    else:
        return JSONResponse(
            content={"success": False, "error": f"Failed to trigger n8n workflow: {workflow_path}"},
            status_code=500
        )
```

**Step 5: Verify no syntax errors**

Run: `cd "C:\Users\alama\Desktop\Lukas Work\IO\webhook-handler" && python -c "from main import app; print('OK')"`
Expected: `OK`

**Step 6: Commit**

```bash
git add webhook-handler/main.py
git commit -m "feat(webhook): add n8n workflow forwarding endpoint"
```

---

### Task 15: Add n8n service to Docker Compose

**Files:**
- Modify: `docker-compose.unified.yml`

**Step 1: Add n8n service**

Add this service definition to `docker-compose.unified.yml` (in the services section):

```yaml
  n8n:
    image: n8nio/n8n:latest
    container_name: n8n
    restart: unless-stopped
    ports:
      - "5678:5678"
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=${N8N_USER:-admin}
      - N8N_BASIC_AUTH_PASSWORD=${N8N_PASSWORD:-}
      - N8N_HOST=0.0.0.0
      - N8N_PORT=5678
      - N8N_PROTOCOL=https
      - WEBHOOK_URL=https://ai-ui.coolestdomain.win/n8n/
    volumes:
      - n8n_data:/home/node/.n8n
    networks:
      - backend
```

**Step 2: Add the n8n_data volume**

In the `volumes:` section of `docker-compose.unified.yml`, add:

```yaml
  n8n_data:
```

**Step 3: Add n8n env vars to webhook-handler service**

In the webhook-handler `environment` section, add:

```yaml
    - N8N_URL=http://n8n:5678
    - N8N_API_KEY=${N8N_API_KEY:-}
```

**Step 4: Commit**

```bash
git add docker-compose.unified.yml
git commit -m "feat(webhook): add n8n service to Docker Compose"
```

---

## PHASE 2B: Slack Integration

**Priority:** MEDIUM | **Effort:** MEDIUM
**What:** Receive Slack events (@mentions, DMs), analyze with AI, respond to Slack channel.

**Prerequisite:** Slack App must be created in the workspace with `chat:write`, `app_mentions:read` scopes and Event Subscriptions URL pointing to `/webhook/slack`.

---

### Task 16: Add Slack config to Settings

**Files:**
- Modify: `webhook-handler/config.py`

**Step 1: Add Slack settings**

```python
    # Slack
    slack_bot_token: str = ""
    slack_signing_secret: str = ""
```

**Step 2: Commit**

```bash
git add webhook-handler/config.py
git commit -m "feat(webhook): add Slack config settings"
```

---

### Task 17: Create Slack client

**Files:**
- Create: `webhook-handler/clients/slack.py`

**Step 1: Create the Slack client**

Create `webhook-handler/clients/slack.py`:

```python
"""Slack API client for posting messages."""
import httpx
import hmac
import hashlib
import time
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def verify_slack_signature(
    body: bytes,
    timestamp: str,
    signature: str,
    signing_secret: str
) -> bool:
    """
    Verify Slack request signature.

    Args:
        body: Raw request body bytes
        timestamp: X-Slack-Request-Timestamp header
        signature: X-Slack-Signature header
        signing_secret: Slack app signing secret

    Returns:
        True if signature is valid
    """
    if not timestamp or not signature or not signing_secret:
        return False

    # Check timestamp freshness (5 minutes)
    try:
        if abs(time.time() - int(timestamp)) > 300:
            return False
    except ValueError:
        return False

    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    expected = "v0=" + hmac.new(
        signing_secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


class SlackClient:
    """Client for Slack API operations."""

    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.base_url = "https://slack.com/api"
        self.timeout = 30.0

    async def post_message(
        self,
        channel: str,
        text: str,
        thread_ts: Optional[str] = None
    ) -> Optional[str]:
        """
        Post a message to a Slack channel.

        Args:
            channel: Channel ID
            text: Message text (supports markdown)
            thread_ts: Thread timestamp to reply in thread

        Returns:
            Message timestamp if successful, None on error
        """
        url = f"{self.base_url}/chat.postMessage"
        headers = {
            "Authorization": f"Bearer {self.bot_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "channel": channel,
            "text": text
        }
        if thread_ts:
            payload["thread_ts"] = thread_ts

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                data = response.json()

                if data.get("ok"):
                    ts = data.get("ts")
                    logger.info(f"Posted Slack message to {channel}: {ts}")
                    return ts
                else:
                    logger.error(f"Slack API error: {data.get('error')}")
                    return None

        except Exception as e:
            logger.error(f"Error posting Slack message: {e}")
            return None

    def format_ai_response(self, analysis: str) -> str:
        """Format AI analysis for Slack (uses mrkdwn)."""
        return f":robot_face: *AI Analysis*\n\n{analysis}"
```

**Step 2: Verify no syntax errors**

Run: `cd "C:\Users\alama\Desktop\Lukas Work\IO\webhook-handler" && python -c "from clients.slack import SlackClient; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add webhook-handler/clients/slack.py
git commit -m "feat(webhook): add Slack client with signature verification"
```

---

### Task 18: Create Slack webhook handler

**Files:**
- Create: `webhook-handler/handlers/slack.py`

**Step 1: Create the Slack handler**

Create `webhook-handler/handlers/slack.py`:

```python
"""Slack webhook event handler."""
from typing import Any, Optional
import logging

from clients.openwebui import OpenWebUIClient
from clients.slack import SlackClient

logger = logging.getLogger(__name__)


class SlackWebhookHandler:
    """Handler for Slack Events API."""

    def __init__(
        self,
        openwebui_client: OpenWebUIClient,
        slack_client: SlackClient,
        ai_model: str = "gpt-4-turbo",
        ai_system_prompt: str = ""
    ):
        self.openwebui = openwebui_client
        self.slack = slack_client
        self.ai_model = ai_model
        self.ai_system_prompt = ai_system_prompt

    async def handle_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Handle a Slack Events API payload.

        Args:
            payload: Slack event payload

        Returns:
            Result dict with success status
        """
        event_type = payload.get("type")

        # Handle URL verification challenge
        if event_type == "url_verification":
            challenge = payload.get("challenge", "")
            return {"challenge": challenge}

        # Handle event callbacks
        if event_type == "event_callback":
            event = payload.get("event", {})
            return await self._handle_event_callback(event)

        logger.info(f"Ignoring Slack event type: {event_type}")
        return {"success": True, "message": f"Event type '{event_type}' not handled"}

    async def _handle_event_callback(self, event: dict[str, Any]) -> dict[str, Any]:
        """Route event callbacks by type."""
        event_type = event.get("type")

        if event_type == "app_mention":
            return await self._handle_mention(event)
        elif event_type == "message" and event.get("channel_type") == "im":
            return await self._handle_direct_message(event)
        else:
            logger.info(f"Ignoring Slack event: {event_type}")
            return {"success": True, "message": f"Slack event '{event_type}' not handled"}

    async def _handle_mention(self, event: dict[str, Any]) -> dict[str, Any]:
        """Handle @mention in a channel."""
        text = event.get("text", "")
        channel = event.get("channel", "")
        thread_ts = event.get("thread_ts") or event.get("ts")
        user = event.get("user", "unknown")

        # Skip bot messages
        if event.get("bot_id"):
            return {"success": True, "message": "Skipped bot message"}

        # Remove the @mention from the text
        # Slack format: <@U1234> some message
        import re
        clean_text = re.sub(r"<@[A-Z0-9]+>", "", text).strip()

        logger.info(f"Slack mention from {user} in {channel}: {clean_text[:100]}")

        system_prompt = self.ai_system_prompt or (
            "You are a helpful AI assistant responding in Slack. "
            "Be concise and use Slack markdown formatting."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": clean_text}
        ]

        analysis = await self.openwebui.chat_completion(
            messages=messages,
            model=self.ai_model
        )

        if not analysis:
            return {"success": False, "error": "Failed to get AI response"}

        response_text = self.slack.format_ai_response(analysis)
        ts = await self.slack.post_message(
            channel=channel,
            text=response_text,
            thread_ts=thread_ts
        )

        if not ts:
            return {"success": False, "error": "Failed to post Slack message"}

        return {"success": True, "message": "Mention handled, response posted"}

    async def _handle_direct_message(self, event: dict[str, Any]) -> dict[str, Any]:
        """Handle direct message to bot."""
        text = event.get("text", "")
        channel = event.get("channel", "")
        user = event.get("user", "unknown")

        # Skip bot messages
        if event.get("bot_id"):
            return {"success": True, "message": "Skipped bot message"}

        logger.info(f"Slack DM from {user}: {text[:100]}")

        system_prompt = self.ai_system_prompt or (
            "You are a helpful AI assistant responding to direct messages in Slack. "
            "Be concise and helpful."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]

        analysis = await self.openwebui.chat_completion(
            messages=messages,
            model=self.ai_model
        )

        if not analysis:
            return {"success": False, "error": "Failed to get AI response"}

        response_text = self.slack.format_ai_response(analysis)
        await self.slack.post_message(channel=channel, text=response_text)

        return {"success": True, "message": "DM handled, response sent"}
```

**Step 2: Verify no syntax errors**

Run: `cd "C:\Users\alama\Desktop\Lukas Work\IO\webhook-handler" && python -c "from handlers.slack import SlackWebhookHandler; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add webhook-handler/handlers/slack.py
git commit -m "feat(webhook): add Slack event handler with mention and DM support"
```

---

### Task 19: Add Slack webhook endpoint to main.py

**Files:**
- Modify: `webhook-handler/main.py`

**Step 1: Add imports**

```python
from clients.slack import SlackClient, verify_slack_signature
from handlers.slack import SlackWebhookHandler
```

**Step 2: Add globals**

```python
slack_client: Optional[SlackClient] = None
slack_handler: Optional[SlackWebhookHandler] = None
```

**Step 3: Initialize in lifespan (only if Slack token is configured)**

```python
    global slack_client, slack_handler

    if settings.slack_bot_token:
        slack_client = SlackClient(token=settings.slack_bot_token)
        slack_handler = SlackWebhookHandler(
            openwebui_client=openwebui_client,
            slack_client=slack_client,
            ai_model=settings.ai_model,
            ai_system_prompt=settings.ai_system_prompt
        )
        logger.info("Slack integration enabled")
    else:
        logger.info("Slack integration disabled (no SLACK_BOT_TOKEN)")
```

**Step 4: Add Slack webhook endpoint**

```python
@app.post("/webhook/slack")
async def slack_webhook(
    request: Request,
    x_slack_request_timestamp: str = Header(None, alias="X-Slack-Request-Timestamp"),
    x_slack_signature: str = Header(None, alias="X-Slack-Signature")
):
    """
    Handle Slack Events API webhooks.

    Validates signature, handles url_verification challenge,
    and routes events to the Slack handler.
    """
    if not slack_handler:
        raise HTTPException(status_code=503, detail="Slack integration not configured")

    body = await request.body()

    # Verify signature if signing secret is configured
    if settings.slack_signing_secret:
        if not verify_slack_signature(
            body=body,
            timestamp=x_slack_request_timestamp or "",
            signature=x_slack_signature or "",
            signing_secret=settings.slack_signing_secret
        ):
            raise HTTPException(status_code=401, detail="Invalid Slack signature")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    logger.info(f"Received Slack event: {payload.get('type')}")

    result = await slack_handler.handle_event(payload)

    # URL verification returns the challenge directly
    if "challenge" in result:
        return JSONResponse(content=result, status_code=200)

    if result.get("success"):
        return JSONResponse(content=result, status_code=200)
    else:
        return JSONResponse(content=result, status_code=500)
```

**Step 5: Add Slack env vars to Docker Compose webhook-handler service**

```yaml
    - SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN:-}
    - SLACK_SIGNING_SECRET=${SLACK_SIGNING_SECRET:-}
```

**Step 6: Commit**

```bash
git add webhook-handler/main.py docker-compose.unified.yml
git commit -m "feat(webhook): add Slack webhook endpoint with signature verification"
```

---

## PHASE 2D: Scheduled Triggers (Cron)

**Priority:** MEDIUM | **Effort:** LOW
**What:** Run AI tasks on a schedule (daily standup summary, weekly reports).

---

### Task 20: Add APScheduler dependency

**Files:**
- Modify: `webhook-handler/requirements.txt`

**Step 1: Add APScheduler**

Add to `webhook-handler/requirements.txt`:

```
apscheduler==3.10.4
```

**Step 2: Commit**

```bash
git add webhook-handler/requirements.txt
git commit -m "feat(webhook): add APScheduler dependency for scheduled triggers"
```

---

### Task 21: Create scheduler module

**Files:**
- Create: `webhook-handler/scheduler.py`

**Step 1: Create the scheduler**

Create `webhook-handler/scheduler.py`:

```python
"""Scheduled task manager using APScheduler."""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from typing import Optional, Callable, Any
import logging

logger = logging.getLogger(__name__)

scheduler: Optional[AsyncIOScheduler] = None


def init_scheduler() -> AsyncIOScheduler:
    """Initialize and return the scheduler instance."""
    global scheduler
    scheduler = AsyncIOScheduler()
    logger.info("Scheduler initialized")
    return scheduler


def start_scheduler():
    """Start the scheduler."""
    if scheduler and not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started")


def shutdown_scheduler():
    """Shut down the scheduler."""
    if scheduler and scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler shut down")


def add_cron_job(
    func: Callable,
    job_id: str,
    cron_expression: str,
    **kwargs: Any
):
    """
    Add a cron-based scheduled job.

    Args:
        func: Async function to call
        job_id: Unique job identifier
        cron_expression: Cron expression (e.g., '0 8 * * *' for 8 AM daily)
        **kwargs: Additional arguments passed to func
    """
    if not scheduler:
        logger.error("Scheduler not initialized")
        return

    parts = cron_expression.split()
    if len(parts) == 5:
        trigger = CronTrigger(
            minute=parts[0],
            hour=parts[1],
            day=parts[2],
            month=parts[3],
            day_of_week=parts[4]
        )
    else:
        logger.error(f"Invalid cron expression: {cron_expression}")
        return

    scheduler.add_job(
        func,
        trigger=trigger,
        id=job_id,
        replace_existing=True,
        kwargs=kwargs
    )
    logger.info(f"Scheduled job '{job_id}' with cron: {cron_expression}")


def list_jobs() -> list[dict]:
    """List all scheduled jobs."""
    if not scheduler:
        return []

    return [
        {
            "id": job.id,
            "next_run": str(job.next_run_time),
            "trigger": str(job.trigger)
        }
        for job in scheduler.get_jobs()
    ]
```

**Step 2: Verify no syntax errors**

Run: `cd "C:\Users\alama\Desktop\Lukas Work\IO\webhook-handler" && python -c "from scheduler import init_scheduler; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add webhook-handler/scheduler.py
git commit -m "feat(webhook): add APScheduler module for cron-based tasks"
```

---

### Task 22: Integrate scheduler into main.py lifespan

**Files:**
- Modify: `webhook-handler/main.py`

**Step 1: Add imports**

```python
from scheduler import init_scheduler, start_scheduler, shutdown_scheduler, list_jobs
```

**Step 2: Initialize in lifespan startup (after all client init)**

```python
    # Initialize scheduler
    init_scheduler()
    start_scheduler()
    logger.info("Scheduler started")
```

**Step 3: Shutdown in lifespan teardown (after the `yield`)**

```python
    shutdown_scheduler()
```

**Step 4: Add scheduler status endpoint**

```python
@app.get("/webhook/scheduler/jobs")
async def scheduler_jobs():
    """List all scheduled jobs."""
    return {"jobs": list_jobs()}
```

**Step 5: Commit**

```bash
git add webhook-handler/main.py
git commit -m "feat(webhook): integrate scheduler into app lifecycle"
```

---

## PHASE 2E: Generic Webhook Endpoint

**Priority:** LOW | **Effort:** LOW
**What:** Accept any JSON payload, apply a prompt template, return AI analysis.

---

### Task 23: Create generic webhook handler

**Files:**
- Create: `webhook-handler/handlers/generic.py`

**Step 1: Create the generic handler**

Create `webhook-handler/handlers/generic.py`:

```python
"""Generic webhook handler — accepts any JSON and runs AI analysis."""
from typing import Any, Optional
import json
import logging

from clients.openwebui import OpenWebUIClient

logger = logging.getLogger(__name__)


class GenericWebhookHandler:
    """Handler for generic webhook payloads."""

    def __init__(
        self,
        openwebui_client: OpenWebUIClient,
        ai_model: str = "gpt-4-turbo"
    ):
        self.openwebui = openwebui_client
        self.ai_model = ai_model

    async def handle_request(
        self,
        payload: dict[str, Any],
        prompt_template: str = "",
        model: str = ""
    ) -> dict[str, Any]:
        """
        Analyze a generic webhook payload with AI.

        Args:
            payload: Any JSON payload
            prompt_template: Optional custom prompt template.
                             Use {payload} as placeholder for the JSON data.
            model: Optional model override

        Returns:
            Result dict with AI analysis
        """
        model = model or self.ai_model

        payload_str = json.dumps(payload, indent=2, default=str)

        if prompt_template:
            user_prompt = prompt_template.replace("{payload}", payload_str)
        else:
            user_prompt = f"""Analyze this webhook payload and provide insights:

```json
{payload_str}
```

Please provide:
1. What this payload represents
2. Key data points
3. Any suggested actions"""

        messages = [
            {
                "role": "system",
                "content": "You are a helpful AI assistant that analyzes webhook payloads. Be concise."
            },
            {"role": "user", "content": user_prompt}
        ]

        analysis = await self.openwebui.chat_completion(
            messages=messages,
            model=model
        )

        if not analysis:
            return {"success": False, "error": "Failed to get AI analysis"}

        return {
            "success": True,
            "message": "Payload analyzed",
            "analysis": analysis
        }
```

**Step 2: Verify no syntax errors**

Run: `cd "C:\Users\alama\Desktop\Lukas Work\IO\webhook-handler" && python -c "from handlers.generic import GenericWebhookHandler; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add webhook-handler/handlers/generic.py
git commit -m "feat(webhook): add generic webhook handler"
```

---

### Task 24: Add generic webhook endpoint to main.py

**Files:**
- Modify: `webhook-handler/main.py`

**Step 1: Add imports**

```python
from handlers.generic import GenericWebhookHandler
```

**Step 2: Add global and initialize in lifespan**

```python
generic_handler: Optional[GenericWebhookHandler] = None

# In lifespan:
    global generic_handler
    generic_handler = GenericWebhookHandler(
        openwebui_client=openwebui_client,
        ai_model=settings.ai_model
    )
```

**Step 3: Add the endpoint**

```python
@app.post("/webhook/generic")
async def generic_webhook(request: Request):
    """
    Handle generic webhook payloads.

    Accepts any JSON, runs AI analysis, returns result.

    Optional query params:
    - prompt: Custom prompt template (use {payload} placeholder)
    - model: Model override
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    prompt = request.query_params.get("prompt", "")
    model = request.query_params.get("model", "")

    result = await generic_handler.handle_request(
        payload=payload,
        prompt_template=prompt,
        model=model
    )

    if result.get("success"):
        return JSONResponse(content=result, status_code=200)
    else:
        return JSONResponse(content=result, status_code=500)
```

**Step 4: Commit**

```bash
git add webhook-handler/main.py
git commit -m "feat(webhook): add generic webhook endpoint POST /webhook/generic"
```

---

## Final Task 25: Full integration commit and deployment

**Step 1: Review all changes**

```bash
git status
git diff --stat
```

Verify all new files:
- `webhook-handler/clients/mcp_proxy.py`
- `webhook-handler/clients/n8n.py`
- `webhook-handler/clients/slack.py`
- `webhook-handler/handlers/mcp.py`
- `webhook-handler/handlers/slack.py`
- `webhook-handler/handlers/generic.py`
- `webhook-handler/scheduler.py`
- `docs/plans/2026-02-06-webhook-phase2-phase3.md`

Modified files:
- `webhook-handler/main.py` (new endpoints, imports, lifespan init)
- `webhook-handler/config.py` (new settings)
- `webhook-handler/requirements.txt` (apscheduler)
- `webhook-handler/clients/openwebui.py` (new analysis methods)
- `webhook-handler/clients/github.py` (new get_pr_files method)
- `webhook-handler/handlers/github.py` (new event handlers)
- `docker-compose.unified.yml` (n8n service, new env vars)

**Step 2: Final deploy to Hetzner**

```bash
ssh root@46.224.193.25 "cd /opt/proxy-server && git pull && docker compose -f docker-compose.unified.yml build webhook-handler && docker compose -f docker-compose.unified.yml up -d webhook-handler"
```

**Step 3: Smoke tests**

```bash
# Health check
curl -s https://ai-ui.coolestdomain.win/webhook/health

# Scheduler jobs (should be empty)
curl -s https://ai-ui.coolestdomain.win/webhook/scheduler/jobs

# MCP tool test
curl -s -X POST https://ai-ui.coolestdomain.win/webhook/mcp/github/get_me -H "Content-Type: application/json" -d '{}'
```

---

## Summary of New Endpoints

| Endpoint | Method | Phase | Description |
|----------|--------|-------|-------------|
| `/webhook/github` | POST | 1.0 (existing) | GitHub events (issues, PRs, comments, push) |
| `/webhook/mcp/{server_id}/{tool_name}` | POST | 3B | Execute MCP tool directly |
| `/webhook/n8n/{workflow_path}` | POST | 3A | Trigger n8n workflow |
| `/webhook/slack` | POST | 2B | Slack Events API |
| `/webhook/generic` | POST | 2E | Generic JSON → AI analysis |
| `/webhook/scheduler/jobs` | GET | 2D | List scheduled jobs |
| `/health` | GET | 1.0 (existing) | Health check |

## Phases NOT Included (Future)

| Phase | Reason |
|-------|--------|
| **2C: Microsoft Teams** | HIGH effort, needs Azure AD setup — plan separately |
| **3C: WebUI Pipe Functions** | HIGH effort, needs Open WebUI config — plan separately |
| **3D: Discord** | LOW priority — plan separately when needed |
