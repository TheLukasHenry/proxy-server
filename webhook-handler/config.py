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

    # MCP Proxy
    mcp_proxy_url: str = "http://mcp-proxy:8000"
    mcp_user_email: str = "webhook-handler@system"
    mcp_user_groups: str = "MCP-Admin"

    # n8n
    n8n_url: str = "http://n8n:5678"
    n8n_api_key: str = ""

    # Slack
    slack_bot_token: str = ""
    slack_signing_secret: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
