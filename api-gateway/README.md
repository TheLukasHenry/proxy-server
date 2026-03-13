# API Gateway

Centralized authentication, rate limiting, and request routing layer.

## What It Does

1. **JWT Validation** — Validates Open WebUI session tokens from `Authorization: Bearer` header or `token` cookie
2. **User Group Lookup** — Queries PostgreSQL (`mcp_proxy.user_group_membership`) for group-based access control
3. **Rate Limiting** — Per-user (100/min) and per-IP (1000/min) rate limiting
4. **Header Injection** — Adds `X-User-Email`, `X-User-Groups`, `X-User-Admin`, `X-Gateway-Validated` headers for downstream services

## Request Flow

```
Browser/API Client
       |
       v
    Caddy (:80/:443)
       |
       v
  API Gateway (:8080)      <-- THIS SERVICE
    |  Validates JWT
    |  Looks up user groups
    |  Applies rate limits
    |  Injects X-User-* headers
    |
    +---> MCP Proxy (:8000)     [/mcp/*, /admin/*, /mcp-admin]
    +---> Open WebUI (:8080)    [everything else]
```

## NOT the Same as Speakeasy

- **API Gateway** = Auth + routing layer (sits between Caddy and backends)
- **Speakeasy** = Meta-tools pattern inside MCP Proxy that reduces 200+ tools to 3 for LLM token savings

These operate at completely different layers of the stack.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `WEBUI_SECRET_KEY` | (required) | JWT signing key (same as Open WebUI) |
| `DATABASE_URL` | (required) | PostgreSQL connection string |
| `RATE_LIMIT_PER_MINUTE` | `100` | Rate limit per authenticated user |
| `RATE_LIMIT_PER_IP` | `1000` | Rate limit per IP (unauthenticated) |
| `RATE_LIMIT_ENABLED` | `true` | Enable/disable rate limiting |
| `ENABLE_API_ANALYTICS` | `true` | Log requests to `mcp_proxy.api_analytics` |
| `MCP_PROXY_URL` | `http://mcp-proxy:8000` | Backend MCP Proxy URL |
| `OPEN_WEBUI_URL` | `http://open-webui:8080` | Backend Open WebUI URL |
| `DEBUG` | `false` | Verbose logging |

## Health Check

```
GET /gateway/health  — Gateway health + DB status
GET /gateway/stats   — Rate limiter statistics
```

## Backend Routing

| Path Pattern | Backend | Description |
|-------------|---------|-------------|
| `/mcp/*` | MCP Proxy | Tool endpoints (strips `/mcp` prefix) |
| `/mcp-admin` | MCP Proxy `/portal` | Admin Portal UI |
| `/mcp-admin/api/*` | MCP Proxy `/admin/*` | Admin API |
| `/admin/users`, `/admin/groups`, `/admin/servers` | MCP Proxy | Management API |
| `/*` (default) | Open WebUI | Chat interface + WebUI admin |
