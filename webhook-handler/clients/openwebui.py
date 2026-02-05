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
