"""GitHub webhook event handler."""
from typing import Any, Optional
import logging

from clients.openwebui import OpenWebUIClient
from clients.github import GitHubClient
from clients.n8n import N8NClient

logger = logging.getLogger(__name__)


class GitHubWebhookHandler:
    """Handler for GitHub webhook events."""

    def __init__(
        self,
        openwebui_client: OpenWebUIClient,
        github_client: GitHubClient,
        n8n_client: Optional[N8NClient] = None,
        ai_model: str = "gpt-4-turbo",
        ai_system_prompt: str = ""
    ):
        self.openwebui = openwebui_client
        self.github = github_client
        self.n8n = n8n_client
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
        logger.info(f"Push analysis complete for {branch}: {analysis[:200]}...")

        result = {
            "success": True,
            "message": "Push analyzed",
            "branch": branch,
            "commit_count": len(commits),
            "analysis_preview": analysis[:500]
        }

        # Forward to n8n workflow for additional processing
        if self.n8n:
            try:
                logger.info(f"Forwarding push event to n8n github-push workflow")
                n8n_result = await self.n8n.trigger_workflow(
                    webhook_path="github-push",
                    payload=payload
                )
                if n8n_result:
                    result["n8n_result"] = n8n_result
                    logger.info("n8n workflow completed successfully")
                else:
                    result["n8n_result"] = None
                    logger.warning("n8n workflow returned no result (workflow may not be deployed)")
            except Exception as e:
                logger.error(f"Failed to forward to n8n: {e}")
                result["n8n_error"] = str(e)

        return result
