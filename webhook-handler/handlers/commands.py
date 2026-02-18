"""Shared command router for slash commands (Slack & Discord)."""
import asyncio
import httpx
from dataclasses import dataclass, field
from typing import Callable, Awaitable, Optional, Any
import logging

from clients.openwebui import OpenWebUIClient
from clients.n8n import N8NClient
from config import settings

logger = logging.getLogger(__name__)


@dataclass
class CommandContext:
    """Platform-agnostic command context."""
    user_id: str
    user_name: str
    channel_id: str
    raw_text: str
    subcommand: str
    arguments: str
    platform: str  # "slack" or "discord"
    respond: Callable[[str], Awaitable[None]]
    metadata: dict = field(default_factory=dict)


# Health endpoints to check for the status command
SERVICE_ENDPOINTS = {
    "open-webui": f"{settings.openwebui_url}/api/config",
    "mcp-proxy": f"{settings.mcp_proxy_url}/health",
    "n8n": f"{settings.n8n_url}/healthz",
    "webhook-handler": "http://localhost:8086/health",
}


class CommandRouter:
    """Platform-agnostic command dispatcher for /aiui commands."""

    def __init__(
        self,
        openwebui_client: OpenWebUIClient,
        n8n_client: N8NClient,
        ai_model: str = "gpt-4-turbo",
    ):
        self.openwebui = openwebui_client
        self.n8n = n8n_client
        self.ai_model = ai_model

    @staticmethod
    def parse_command(text: str) -> tuple[str, str]:
        """
        Parse command text into (subcommand, arguments).

        Examples:
            "ask what is MCP" -> ("ask", "what is MCP")
            "workflow pr-review" -> ("workflow", "pr-review")
            "status" -> ("status", "")
            "" -> ("status", "")
            "what is MCP" -> ("ask", "what is MCP")
        """
        text = text.strip()
        if not text:
            return ("status", "")

        parts = text.split(None, 1)
        subcommand = parts[0].lower()
        arguments = parts[1] if len(parts) > 1 else ""

        known_commands = {"ask", "workflow", "status", "help"}
        if subcommand in known_commands:
            return (subcommand, arguments)

        # Unknown subcommand — treat entire text as an ask query
        return ("ask", text)

    async def execute(self, ctx: CommandContext) -> None:
        """Dispatch a command to the appropriate handler."""
        try:
            if ctx.subcommand == "ask":
                await self._handle_ask(ctx)
            elif ctx.subcommand == "workflow":
                await self._handle_workflow(ctx)
            elif ctx.subcommand == "status":
                await self._handle_status(ctx)
            elif ctx.subcommand == "help":
                await self._handle_help(ctx)
            else:
                await ctx.respond(f"Unknown command: `{ctx.subcommand}`. Try `/aiui help`.")
        except Exception as e:
            logger.error(f"Command error ({ctx.subcommand}): {e}", exc_info=True)
            await ctx.respond(f"Error processing command: {e}")

    async def _handle_ask(self, ctx: CommandContext) -> None:
        """Send a question to the AI and return the response."""
        if not ctx.arguments:
            await ctx.respond("Usage: `/aiui ask <question>`")
            return

        logger.info(f"[{ctx.platform}] ask from {ctx.user_name}: {ctx.arguments[:80]}")

        messages = [
            {"role": "system", "content": (
                "You are a helpful AI assistant responding to a slash command. "
                "Be concise and actionable."
            )},
            {"role": "user", "content": ctx.arguments},
        ]

        response = await self.openwebui.chat_completion(
            messages=messages,
            model=self.ai_model,
        )

        if not response:
            await ctx.respond("Failed to get AI response. The AI service may be unavailable.")
            return

        # Truncate to platform limits (Slack 3000, Discord 2000)
        limit = 2000 if ctx.platform == "discord" else 3000
        if len(response) > limit:
            response = response[: limit - 20] + "\n\n... (truncated)"

        await ctx.respond(response)

    async def _handle_workflow(self, ctx: CommandContext) -> None:
        """Trigger an n8n workflow by name."""
        if not ctx.arguments:
            await ctx.respond("Usage: `/aiui workflow <name>` — triggers an n8n webhook workflow.")
            return

        workflow_name = ctx.arguments.strip()
        logger.info(f"[{ctx.platform}] workflow trigger from {ctx.user_name}: {workflow_name}")

        result = await self.n8n.trigger_workflow(
            webhook_path=workflow_name,
            payload={
                "triggered_by": ctx.user_name,
                "platform": ctx.platform,
                "channel": ctx.channel_id,
            },
        )

        if result is not None:
            summary = str(result)[:500]
            await ctx.respond(f"Workflow `{workflow_name}` triggered successfully.\n```\n{summary}\n```")
        else:
            await ctx.respond(f"Failed to trigger workflow `{workflow_name}`. Check the workflow name and n8n status.")

    async def _handle_status(self, ctx: CommandContext) -> None:
        """Check service health and report status."""
        logger.info(f"[{ctx.platform}] status check from {ctx.user_name}")

        lines = ["*Service Status*\n"]
        for name, url in SERVICE_ENDPOINTS.items():
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(url)
                    if resp.status_code < 400:
                        lines.append(f"  {name}: healthy ({resp.status_code})")
                    else:
                        lines.append(f"  {name}: unhealthy ({resp.status_code})")
            except Exception:
                lines.append(f"  {name}: unreachable")

        await ctx.respond("\n".join(lines))

    async def _handle_help(self, ctx: CommandContext) -> None:
        """Show available commands."""
        help_text = (
            "*Available Commands*\n"
            "`/aiui ask <question>` — Ask the AI a question\n"
            "`/aiui workflow <name>` — Trigger an n8n workflow\n"
            "`/aiui status` — Check service health\n"
            "`/aiui help` — Show this help message"
        )
        await ctx.respond(help_text)
