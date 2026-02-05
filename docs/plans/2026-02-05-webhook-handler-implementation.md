# Webhook Handler Service - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a webhook handler service that receives GitHub issue webhooks, calls Open WebUI for AI analysis, and posts the response as a comment.

**Architecture:** New standalone FastAPI service (`webhook-handler/`) that validates GitHub webhook signatures, parses issue payloads, calls Open WebUI's `/api/chat/completions` endpoint, and posts the AI response back to GitHub as a comment.

**Tech Stack:** Python 3.11, FastAPI, httpx (async HTTP), pydantic, uvicorn

---

## Task 1: Create Project Structure

**Files:**
- Create: `webhook-handler/`
- Create: `webhook-handler/requirements.txt`
- Create: `webhook-handler/config.py`
- Create: `webhook-handler/handlers/__init__.py`
- Create: `webhook-handler/clients/__init__.py`

**Step 1: Create directory structure**

```bash
mkdir -p webhook-handler/handlers webhook-handler/clients
```

**Step 2: Create requirements.txt**

Create `webhook-handler/requirements.txt`:
```
fastapi==0.109.0
uvicorn==0.27.0
httpx==0.26.0
pydantic==2.5.3
pydantic-settings==2.1.0
python-dotenv==1.0.0
```

**Step 3: Create config.py**

Create `webhook-handler/config.py`:
```python
"""Configuration management for webhook handler."""
import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Service
    port: int = 8086
    debug: bool = False

    # GitHub
    github_webhook_secret: str = ""
    github_token: str = ""

    # Open WebUI
    openwebui_url: str = "http://open-webui:8080"
    openwebui_api_key: str = ""

    # AI Settings
    ai_model: str = "gpt-4-turbo"
    ai_system_prompt: str = "You are a helpful AI assistant that analyzes GitHub issues and suggests solutions. Be concise and actionable."

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
```

**Step 4: Create __init__.py files**

Create `webhook-handler/handlers/__init__.py`:
```python
"""Webhook handlers package."""
```

Create `webhook-handler/clients/__init__.py`:
```python
"""API clients package."""
```

**Step 5: Commit**

```bash
git add webhook-handler/
git commit -m "feat(webhook): create project structure and config"
```

---

## Task 2: Create Open WebUI Client

**Files:**
- Create: `webhook-handler/clients/openwebui.py`

**Step 1: Create the client**

Create `webhook-handler/clients/openwebui.py`:
```python
"""Open WebUI API client for chat completions."""
import httpx
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class OpenWebUIClient:
    """Client for Open WebUI /api/chat/completions endpoint."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = 60.0  # 60 second timeout for AI responses

    async def chat_completion(
        self,
        messages: list[dict],
        model: str = "gpt-4-turbo",
        stream: bool = False
    ) -> Optional[str]:
        """
        Send a chat completion request to Open WebUI.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use for completion
            stream: Whether to stream response (not supported yet)

        Returns:
            The assistant's response text, or None on error
        """
        url = f"{self.base_url}/api/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()

                data = response.json()
                # Extract response from OpenAI-compatible format
                if "choices" in data and len(data["choices"]) > 0:
                    return data["choices"][0]["message"]["content"]

                logger.error(f"Unexpected response format: {data}")
                return None

        except httpx.TimeoutException:
            logger.error(f"Timeout calling Open WebUI at {url}")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from Open WebUI: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Error calling Open WebUI: {e}")
            return None

    async def analyze_github_issue(
        self,
        title: str,
        body: str,
        labels: list[str],
        model: str = "gpt-4-turbo",
        system_prompt: str = ""
    ) -> Optional[str]:
        """
        Analyze a GitHub issue and return AI suggestions.

        Args:
            title: Issue title
            body: Issue body/description
            labels: List of label names
            model: Model to use
            system_prompt: System prompt for the AI

        Returns:
            AI analysis text, or None on error
        """
        if not system_prompt:
            system_prompt = (
                "You are a helpful AI assistant that analyzes GitHub issues "
                "and suggests solutions. Be concise and actionable."
            )

        labels_str = ", ".join(labels) if labels else "none"

        user_prompt = f"""Analyze this GitHub issue and suggest a solution:

**Title:** {title}

**Description:**
{body or "No description provided."}

**Labels:** {labels_str}

Please provide:
1. Brief summary of the issue
2. Possible root causes
3. Suggested solution steps
4. Related files to check (if applicable)"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        return await self.chat_completion(messages, model=model)
```

**Step 2: Commit**

```bash
git add webhook-handler/clients/openwebui.py
git commit -m "feat(webhook): add Open WebUI API client"
```

---

## Task 3: Create GitHub Client

**Files:**
- Create: `webhook-handler/clients/github.py`

**Step 1: Create the client**

Create `webhook-handler/clients/github.py`:
```python
"""GitHub API client for posting comments."""
import httpx
import hmac
import hashlib
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def verify_github_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify GitHub webhook signature.

    Args:
        payload: Raw request body bytes
        signature: X-Hub-Signature-256 header value
        secret: Webhook secret configured in GitHub

    Returns:
        True if signature is valid, False otherwise
    """
    if not signature or not secret:
        return False

    expected = 'sha256=' + hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


class GitHubClient:
    """Client for GitHub API operations."""

    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://api.github.com"
        self.timeout = 30.0

    async def post_issue_comment(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        body: str
    ) -> Optional[int]:
        """
        Post a comment on a GitHub issue.

        Args:
            owner: Repository owner (user or org)
            repo: Repository name
            issue_number: Issue number
            body: Comment body (markdown supported)

        Returns:
            Comment ID if successful, None on error
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}/comments"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        payload = {"body": body}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()

                data = response.json()
                comment_id = data.get("id")
                logger.info(f"Posted comment {comment_id} on {owner}/{repo}#{issue_number}")
                return comment_id

        except httpx.HTTPStatusError as e:
            logger.error(f"GitHub API error: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Error posting GitHub comment: {e}")
            return None

    def format_ai_response(self, analysis: str) -> str:
        """
        Format AI analysis as a GitHub comment.

        Args:
            analysis: Raw AI analysis text

        Returns:
            Formatted markdown comment
        """
        return f"""🤖 **AI Analysis**

{analysis}

---
*Generated by Open WebUI AI Assistant*"""
```

**Step 2: Commit**

```bash
git add webhook-handler/clients/github.py
git commit -m "feat(webhook): add GitHub API client with signature verification"
```

---

## Task 4: Create GitHub Webhook Handler

**Files:**
- Create: `webhook-handler/handlers/github.py`

**Step 1: Create the handler**

Create `webhook-handler/handlers/github.py`:
```python
"""GitHub webhook event handler."""
from typing import Any, Optional
import logging

from clients.openwebui import OpenWebUIClient
from clients.github import GitHubClient

logger = logging.getLogger(__name__)


class GitHubWebhookHandler:
    """Handler for GitHub webhook events."""

    def __init__(
        self,
        openwebui_client: OpenWebUIClient,
        github_client: GitHubClient,
        ai_model: str = "gpt-4-turbo",
        ai_system_prompt: str = ""
    ):
        self.openwebui = openwebui_client
        self.github = github_client
        self.ai_model = ai_model
        self.ai_system_prompt = ai_system_prompt

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
        elif event_type == "ping":
            return {"success": True, "message": "Pong!"}
        else:
            logger.info(f"Ignoring unsupported event type: {event_type}")
            return {"success": True, "message": f"Event type '{event_type}' not handled"}

    async def _handle_issue_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Handle issue events (opened, edited, etc.)."""
        action = payload.get("action")

        if action != "opened":
            logger.info(f"Ignoring issue action: {action}")
            return {"success": True, "message": f"Action '{action}' not handled"}

        return await self._analyze_and_comment(payload)

    async def _analyze_and_comment(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Analyze an issue and post AI comment."""
        # Extract issue details
        issue = payload.get("issue", {})
        repo = payload.get("repository", {})

        issue_number = issue.get("number")
        title = issue.get("title", "")
        body = issue.get("body", "")
        labels = [label.get("name", "") for label in issue.get("labels", [])]

        repo_full_name = repo.get("full_name", "")
        if "/" in repo_full_name:
            owner, repo_name = repo_full_name.split("/", 1)
        else:
            logger.error(f"Invalid repository name: {repo_full_name}")
            return {"success": False, "error": "Invalid repository name"}

        logger.info(f"Analyzing issue #{issue_number}: {title}")

        # Get AI analysis
        analysis = await self.openwebui.analyze_github_issue(
            title=title,
            body=body,
            labels=labels,
            model=self.ai_model,
            system_prompt=self.ai_system_prompt
        )

        if not analysis:
            logger.error("Failed to get AI analysis")
            return {"success": False, "error": "Failed to get AI analysis"}

        # Format and post comment
        comment_body = self.github.format_ai_response(analysis)
        comment_id = await self.github.post_issue_comment(
            owner=owner,
            repo=repo_name,
            issue_number=issue_number,
            body=comment_body
        )

        if not comment_id:
            logger.error("Failed to post GitHub comment")
            return {"success": False, "error": "Failed to post comment"}

        logger.info(f"Successfully posted comment {comment_id} on issue #{issue_number}")
        return {
            "success": True,
            "message": "Issue analyzed, comment posted",
            "issue_number": issue_number,
            "comment_id": comment_id
        }
```

**Step 2: Commit**

```bash
git add webhook-handler/handlers/github.py
git commit -m "feat(webhook): add GitHub webhook event handler"
```

---

## Task 5: Create Main FastAPI Application

**Files:**
- Create: `webhook-handler/main.py`

**Step 1: Create the FastAPI app**

Create `webhook-handler/main.py`:
```python
"""Webhook Handler Service - Main FastAPI Application."""
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from typing import Optional

from config import settings
from clients.openwebui import OpenWebUIClient
from clients.github import GitHubClient, verify_github_signature
from handlers.github import GitHubWebhookHandler

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Global clients (initialized on startup)
openwebui_client: Optional[OpenWebUIClient] = None
github_client: Optional[GitHubClient] = None
github_handler: Optional[GitHubWebhookHandler] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize clients on startup."""
    global openwebui_client, github_client, github_handler

    logger.info("Initializing webhook handler...")

    openwebui_client = OpenWebUIClient(
        base_url=settings.openwebui_url,
        api_key=settings.openwebui_api_key
    )

    github_client = GitHubClient(token=settings.github_token)

    github_handler = GitHubWebhookHandler(
        openwebui_client=openwebui_client,
        github_client=github_client,
        ai_model=settings.ai_model,
        ai_system_prompt=settings.ai_system_prompt
    )

    logger.info(f"Webhook handler ready on port {settings.port}")
    logger.info(f"Open WebUI URL: {settings.openwebui_url}")

    yield

    logger.info("Shutting down webhook handler...")


app = FastAPI(
    title="Webhook Handler Service",
    description="Receives webhooks and triggers Open WebUI AI analysis",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "webhook-handler",
        "version": "1.0.0"
    }


@app.post("/webhook/github")
async def github_webhook(
    request: Request,
    x_github_event: str = Header(..., alias="X-GitHub-Event"),
    x_hub_signature_256: str = Header(None, alias="X-Hub-Signature-256"),
    x_github_delivery: str = Header(None, alias="X-GitHub-Delivery")
):
    """
    Handle GitHub webhook events.

    Validates signature, parses payload, and triggers AI analysis.
    """
    # Get raw body for signature verification
    body = await request.body()

    # Verify signature if secret is configured
    if settings.github_webhook_secret:
        if not x_hub_signature_256:
            logger.warning(f"Missing signature for delivery {x_github_delivery}")
            raise HTTPException(status_code=401, detail="Missing signature")

        if not verify_github_signature(body, x_hub_signature_256, settings.github_webhook_secret):
            logger.warning(f"Invalid signature for delivery {x_github_delivery}")
            raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse JSON payload
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    logger.info(f"Received GitHub event: {x_github_event} (delivery: {x_github_delivery})")

    # Handle the event
    result = await github_handler.handle_event(x_github_event, payload)

    if result.get("success"):
        return JSONResponse(content=result, status_code=200)
    else:
        return JSONResponse(content=result, status_code=500)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.debug
    )
```

**Step 2: Commit**

```bash
git add webhook-handler/main.py
git commit -m "feat(webhook): add main FastAPI application"
```

---

## Task 6: Create Dockerfile

**Files:**
- Create: `webhook-handler/Dockerfile`

**Step 1: Create Dockerfile**

Create `webhook-handler/Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8086

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8086/health || exit 1

# Run the application
CMD ["python", "main.py"]
```

**Step 2: Commit**

```bash
git add webhook-handler/Dockerfile
git commit -m "feat(webhook): add Dockerfile"
```

---

## Task 7: Add to Docker Compose

**Files:**
- Modify: `docker-compose.unified.yml`

**Step 1: Add webhook-handler service**

Add to `docker-compose.unified.yml` after the api-gateway service:

```yaml
  # ==========================================================================
  # Webhook Handler - External event processing
  # ==========================================================================
  webhook-handler:
    build: ./webhook-handler
    container_name: webhook-handler
    restart: unless-stopped
    ports:
      - "8086:8086"
    environment:
      - PORT=8086
      - DEBUG=${DEBUG:-false}
      - GITHUB_WEBHOOK_SECRET=${GITHUB_WEBHOOK_SECRET:-}
      - GITHUB_TOKEN=${GITHUB_TOKEN:-}
      - OPENWEBUI_URL=http://open-webui:8080
      - OPENWEBUI_API_KEY=${OPENWEBUI_API_KEY:-}
      - AI_MODEL=${AI_MODEL:-gpt-4-turbo}
    networks:
      - backend
    depends_on:
      - open-webui
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8086/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

**Step 2: Commit**

```bash
git add docker-compose.unified.yml
git commit -m "feat(webhook): add webhook-handler to docker-compose"
```

---

## Task 8: Update Caddyfile

**Files:**
- Modify: `Caddyfile`

**Step 1: Add webhook route**

Add to `Caddyfile` before the default handler:

```
    # ---------------------------------------------------------------------------
    # Webhook Handler (external webhooks)
    # ---------------------------------------------------------------------------
    handle /webhook/* {
        reverse_proxy localhost:8086 {
            header_down Cache-Control "no-store, no-cache, must-revalidate"
        }
    }
```

**Step 2: Commit**

```bash
git add Caddyfile
git commit -m "feat(webhook): add Caddy route for webhooks"
```

---

## Task 9: Update .env.example

**Files:**
- Modify: `.env.example`

**Step 1: Add webhook environment variables**

Add to `.env.example`:

```bash
# =============================================================================
# Webhook Handler Configuration
# =============================================================================

# GitHub webhook secret (configure same value in GitHub webhook settings)
GITHUB_WEBHOOK_SECRET=your-webhook-secret-here

# GitHub personal access token (for posting comments)
# Required scopes: repo (for private repos) or public_repo (for public only)
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx

# Open WebUI API key (get from Open WebUI Settings > Account)
OPENWEBUI_API_KEY=your-openwebui-api-key

# AI Model to use for analysis
AI_MODEL=gpt-4-turbo
```

**Step 2: Commit**

```bash
git add .env.example
git commit -m "docs: add webhook environment variables to .env.example"
```

---

## Task 10: Test Locally

**Step 1: Build and run locally**

```bash
cd webhook-handler
pip install -r requirements.txt
python main.py
```

**Step 2: Test health endpoint**

```bash
curl http://localhost:8086/health
```

Expected output:
```json
{"status":"healthy","service":"webhook-handler","version":"1.0.0"}
```

**Step 3: Test webhook endpoint (without signature)**

```bash
curl -X POST http://localhost:8086/webhook/github \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: ping" \
  -d '{}'
```

Expected output:
```json
{"success":true,"message":"Pong!"}
```

---

## Task 11: Deploy to Server

**Step 1: Copy files to server**

```bash
scp -r webhook-handler root@46.224.193.25:/root/proxy-server/
scp Caddyfile root@46.224.193.25:/etc/caddy/Caddyfile
scp docker-compose.unified.yml root@46.224.193.25:/root/proxy-server/
```

**Step 2: Build and start on server**

```bash
ssh root@46.224.193.25 "cd /root/proxy-server && docker compose -f docker-compose.unified.yml build webhook-handler && docker compose -f docker-compose.unified.yml up -d webhook-handler"
```

**Step 3: Reload Caddy**

```bash
ssh root@46.224.193.25 "systemctl reload caddy"
```

**Step 4: Verify deployment**

```bash
curl https://ai-ui.coolestdomain.win/webhook/health
```

---

## Task 12: Configure GitHub Webhook

**Step 1: Go to GitHub repository settings**

Navigate to: `Settings > Webhooks > Add webhook`

**Step 2: Configure webhook**

- **Payload URL:** `https://ai-ui.coolestdomain.win/webhook/github`
- **Content type:** `application/json`
- **Secret:** (same as GITHUB_WEBHOOK_SECRET in .env)
- **Events:** Select "Issues" only
- **Active:** Check

**Step 3: Test by creating an issue**

Create a test issue in the repository. Within 30 seconds, an AI-generated comment should appear.

---

## Success Criteria Checklist

- [ ] Service builds and runs locally
- [ ] Health endpoint responds
- [ ] GitHub signature validation works
- [ ] Open WebUI client calls succeed
- [ ] GitHub comment posting works
- [ ] Deployed to Hetzner VPS
- [ ] Caddy routes /webhook/* correctly
- [ ] End-to-end test: issue → AI comment

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| 401 Invalid signature | Check GITHUB_WEBHOOK_SECRET matches GitHub config |
| Timeout from Open WebUI | Check OPENWEBUI_URL is reachable, increase timeout |
| 403 from GitHub API | Check GITHUB_TOKEN has correct permissions |
| No comment posted | Check logs with `docker logs webhook-handler` |
