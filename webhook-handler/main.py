"""Webhook Handler Service - Main FastAPI Application."""
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from typing import Optional

from config import settings
from clients.openwebui import OpenWebUIClient
from clients.github import GitHubClient, verify_github_signature
from clients.mcp_proxy import MCPProxyClient
from clients.n8n import N8NClient
from clients.slack import SlackClient, verify_slack_signature
from handlers.github import GitHubWebhookHandler
from handlers.mcp import MCPWebhookHandler
from handlers.slack import SlackWebhookHandler
from handlers.generic import GenericWebhookHandler
from handlers.automation import AutomationWebhookHandler
from scheduler import init_scheduler, start_scheduler, shutdown_scheduler, list_jobs

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
mcp_handler: Optional[MCPWebhookHandler] = None
n8n_client: Optional[N8NClient] = None
slack_client: Optional[SlackClient] = None
slack_handler: Optional[SlackWebhookHandler] = None
generic_handler: Optional[GenericWebhookHandler] = None
automation_handler: Optional[AutomationWebhookHandler] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize clients on startup."""
    global openwebui_client, github_client, github_handler
    global mcp_handler, n8n_client
    global slack_client, slack_handler, generic_handler, automation_handler

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

    # MCP Proxy client
    mcp_client = MCPProxyClient(
        base_url=settings.mcp_proxy_url,
        user_email=settings.mcp_user_email,
        user_groups=settings.mcp_user_groups
    )
    mcp_handler = MCPWebhookHandler(mcp_client=mcp_client)
    logger.info(f"MCP Proxy URL: {settings.mcp_proxy_url}")

    # n8n client
    n8n_client = N8NClient(
        base_url=settings.n8n_url,
        api_key=settings.n8n_api_key
    )
    logger.info(f"n8n URL: {settings.n8n_url}")

    # Slack client (only if configured)
    if settings.slack_bot_token:
        slack_client = SlackClient(bot_token=settings.slack_bot_token)
        slack_handler = SlackWebhookHandler(
            openwebui_client=openwebui_client,
            slack_client=slack_client,
            ai_model=settings.ai_model,
            ai_system_prompt=settings.ai_system_prompt
        )
        logger.info("Slack integration enabled")
    else:
        logger.info("Slack integration disabled (no SLACK_BOT_TOKEN)")

    # Generic handler
    generic_handler = GenericWebhookHandler(
        openwebui_client=openwebui_client,
        ai_model=settings.ai_model
    )

    # Automation handler (delegates to pipe function)
    automation_handler = AutomationWebhookHandler(
        openwebui_client=openwebui_client,
        pipe_model=settings.automation_pipe_model
    )
    logger.info(f"Automation pipe model: {settings.automation_pipe_model}")

    # Scheduler
    init_scheduler()
    start_scheduler()

    logger.info(f"Webhook handler ready on port {settings.port}")
    logger.info(f"Open WebUI URL: {settings.openwebui_url}")

    yield

    shutdown_scheduler()
    logger.info("Shutting down webhook handler...")


app = FastAPI(
    title="Webhook Handler Service",
    description="Receives webhooks and triggers Open WebUI AI analysis",
    version="2.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "webhook-handler",
        "version": "2.0.0"
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


@app.post("/webhook/automation")
async def automation_webhook(request: Request):
    """
    Handle automation webhook payloads.

    Combines AI reasoning with MCP tool execution via the Webhook Automation
    pipe function running inside Open WebUI.

    Optional query params:
    - source: Origin identifier (e.g., "github", "slack", "manual")
    - instructions: Natural-language instructions for the AI
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    source = request.query_params.get("source", "webhook")
    instructions = request.query_params.get("instructions", "")

    result = await automation_handler.handle_request(
        payload=payload,
        source=source,
        instructions=instructions,
    )

    if result.get("success"):
        return JSONResponse(content=result, status_code=200)
    else:
        return JSONResponse(content=result, status_code=500)


@app.get("/webhook/scheduler/jobs")
async def scheduler_jobs():
    """List all scheduled jobs."""
    return {"jobs": list_jobs()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.debug
    )
