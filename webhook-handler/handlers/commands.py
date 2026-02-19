"""Shared command router for slash commands (Slack & Discord)."""
import asyncio
import httpx
from dataclasses import dataclass, field
from datetime import datetime, timezone
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
        slack_client=None,
    ):
        self.openwebui = openwebui_client
        self.n8n = n8n_client
        self.ai_model = ai_model
        self._slack_client = slack_client

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

        known_commands = {"ask", "workflow", "status", "help", "report"}
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
            elif ctx.subcommand == "report":
                await self._handle_report(ctx)
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
            "`/aiui report` — Generate end-of-day activity report\n"
            "`/aiui status` — Check service health\n"
            "`/aiui help` — Show this help message"
        )
        await ctx.respond(help_text)

    async def _handle_report(self, ctx: CommandContext) -> None:
        """Generate an end-of-day report with AI summary."""
        logger.info(f"[{ctx.platform}] report from {ctx.user_name}")
        await ctx.respond("Generating report... (gathering data from GitHub, n8n, and services)")

        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

        # Gather data from all sources in parallel
        commits, executions, health = await asyncio.gather(
            self._gather_github_commits(today_start),
            self._gather_n8n_executions(today_start),
            self._gather_health(),
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
        if settings.report_slack_channel and self._slack_client:
            try:
                await self._slack_client.post_message(
                    channel=settings.report_slack_channel,
                    text=response,
                )
            except Exception as e:
                logger.error(f"Failed to post report to Slack channel: {e}")

    async def _gather_github_commits(self, since: str) -> Optional[list[dict]]:
        """Fetch today's commits. Returns None if not configured."""
        from clients.github import GitHubClient

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
        return [e for e in all_execs if e.get("started", "") >= since]

    async def _gather_health(self) -> list[dict]:
        """Check health of all services."""
        results = []
        for name, url in SERVICE_ENDPOINTS.items():
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(url)
                    status = "healthy" if resp.status_code < 400 else "unhealthy"
            except Exception:
                status = "unreachable"
            results.append({"service": name, "status": status})
        return results
