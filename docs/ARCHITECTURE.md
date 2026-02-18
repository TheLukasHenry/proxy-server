# Architecture Overview

**Last Updated:** 2026-02-18
**Canonical Reference:** [`docs/architecture-guide.md`](./architecture-guide.md)

> This file is a quick-reference summary. For the full architecture documentation (Caddy routes, API Gateway auth flow, MCP Proxy multi-tenancy, webhook handler endpoints, security layers, etc.), see the **[Architecture Guide](./architecture-guide.md)**.

## Stack Summary

Multi-tenant AI platform with MCP tool integration.
**Deployment:** Docker Compose on Hetzner VPS at `ai-ui.coolestdomain.win` (NOT Kubernetes)
**Compose file:** `docker-compose.unified.yml`

## Traffic Flow

```
Browser → Cloudflare → Caddy (port 80) → API Gateway (8080) → Backend services
                              ↓
                   Bypasses for: webhooks, n8n, static assets, WebSocket
```

## Services (15 containers)

| Service | Role |
|---|---|
| Caddy | Reverse proxy, TLS termination |
| API Gateway | JWT validation, rate limiting, header injection |
| Open WebUI | AI chat interface |
| MCP Proxy | Multi-tenant tool orchestration (30+ tools) |
| Admin Portal | User/group management UI |
| Webhook Handler | External event processing (GitHub, Slack, Discord, n8n) |
| n8n | Workflow automation engine |
| PostgreSQL | Database (pgvector-enabled) |
| Redis | Sessions and cache |
| MCP GitHub, Filesystem, ClickUp, Trello, SonarQube, Excel, Dashboard, Notion, n8n | Tool servers |

## Key Files

```
IO/
├── docker-compose.unified.yml    # Production stack definition
├── Caddyfile                     # Reverse proxy routing rules
├── .env                          # Credentials (DO NOT commit)
├── .env.example                  # Environment template
├── api-gateway/main.py           # JWT validation, rate limiting
├── mcp-proxy/main.py             # Multi-tenant tool gateway
├── webhook-handler/main.py       # Event processing (14 endpoints)
│   ├── handlers/commands.py      # Shared CommandRouter (Slack + Discord)
│   ├── handlers/github.py        # GitHub event handler
│   ├── handlers/slack.py         # Slack Events API handler
│   ├── handlers/slack_commands.py# Slack slash commands
│   ├── handlers/discord_commands.py # Discord slash commands
│   ├── clients/                  # HTTP clients (OpenWebUI, GitHub, Slack, Discord, n8n, MCP)
│   └── scheduler.py              # APScheduler cron jobs
└── docs/architecture-guide.md    # Full architecture documentation
```

## Authentication

```
Browser → Caddy → API Gateway (JWT HS256 validation) → injects X-User-Email, X-User-Groups, X-User-Admin headers → backends
```

Webhooks bypass the API Gateway and use their own signature verification (GitHub HMAC-SHA256, Slack HMAC, Discord Ed25519).
