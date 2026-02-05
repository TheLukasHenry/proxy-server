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

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
