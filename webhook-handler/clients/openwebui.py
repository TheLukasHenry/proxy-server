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
