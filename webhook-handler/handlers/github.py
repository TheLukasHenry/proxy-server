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
