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

    async def post_to_response_url(
        self,
        response_url: str,
        text: str,
        response_type: str = "ephemeral",
        replace_original: bool = False,
    ) -> bool:
        """
        Post to a Slack response_url (slash command / interaction callback).

        The response_url is pre-authenticated — no Bearer token needed.

        Args:
            response_url: Slack-provided callback URL
            text: Message text
            response_type: "ephemeral" (visible to invoker) or "in_channel"
            replace_original: Whether to replace the original message

        Returns:
            True if successful
        """
        payload = {
            "text": text,
            "response_type": response_type,
            "replace_original": replace_original,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(response_url, json=payload)
                if response.status_code == 200:
                    logger.info(f"Posted to response_url ({response_type})")
                    return True
                else:
                    logger.error(f"response_url error: {response.status_code} {response.text}")
                    return False
        except Exception as e:
            logger.error(f"Error posting to response_url: {e}")
            return False

    def format_ai_response(self, analysis: str) -> str:
        """Format AI analysis for Slack (uses mrkdwn)."""
        return f":robot_face: *AI Analysis*\n\n{analysis}"
