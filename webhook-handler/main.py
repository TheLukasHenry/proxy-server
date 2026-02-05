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
