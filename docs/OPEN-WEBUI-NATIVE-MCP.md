# Open WebUI Native MCP Servers — Proxy vs Direct

## Overview

Open WebUI v0.7+ supports two types of tool server connections:

| Type | Format | Use Case |
|---|---|---|
| `"openapi"` | OpenAPI/REST | Our MCP Proxy (multi-tenant, group-based filtering) |
| `"mcp"` | Streamable HTTP | Direct connection to remote MCP servers |

## Which Servers Go Through Proxy vs Direct

### Through Proxy (`type: "openapi"`) — Group-Based Access Control

These servers route through our MCP Proxy for multi-tenant isolation:

| Server | Why Proxy | Transport |
|---|---|---|
| GitHub (local) | Per-tenant PAT, group filtering | Local container |
| Filesystem | Group filtering | Local container |
| ClickUp | Per-tenant token, group filtering | STDIO via mcpo |
| Trello | Per-tenant token, group filtering | STDIO via mcpo |
| SonarQube | Per-tenant token, group filtering | STDIO via mcpo |
| Excel Creator | Group filtering | Local container |
| Dashboard | Group filtering | Local container |

### Direct Connection (`type: "mcp"`) — All Users See These

These remote MCP servers support Streamable HTTP and can connect directly:

| Server | Endpoint | Auth | Status |
|---|---|---|---|
| Notion | `https://mcp.notion.com/mcp` | OAuth 2.1 | Ready |
| Linear | `https://mcp.linear.app/mcp` | OAuth 2.1 | Ready |
| Sentry | `https://mcp.sentry.dev/mcp` | OAuth 2.1 | Ready |
| HubSpot | `https://mcp.hubspot.com/` | OAuth 2.1 | Ready |
| Atlassian | `https://mcp.atlassian.com/v1/mcp` | OAuth 2.1 | Uncertain (SSE confirmed, Streamable HTTP unconfirmed) |

## Key Decision: Why Not All Direct?

**Direct connections bypass our proxy's group-based access control.**

When a server is connected directly via `type: "mcp"`, our MCP Proxy's JWT auth, group membership check, and tenant filtering are NOT invoked. All users with access to the tool server see all tools from that server.

Open WebUI v0.7.0+ has its own access control (`config.access_control` with `group_ids` and `user_ids`), but this is Open WebUI's group system, not our Entra ID group mapping.

**Recommendation**: Use direct connections only for servers that ALL users should have access to (organization-wide tools). Use the proxy for servers that need per-group/per-tenant isolation.

## JSON Format for Native MCP Connections

```json
{
  "type": "mcp",
  "url": "https://mcp.notion.com/mcp",
  "auth_type": "oauth_2.1",
  "key": "",
  "config": { "enable": true },
  "info": {
    "id": "notion",
    "name": "Notion",
    "description": "Notion workspace integration"
  }
}
```

### Auth Types
- `"none"` — No authentication
- `"bearer"` — Static API key/token (set in `key` field)
- `"oauth_2.1"` — OAuth flow (user authenticates in browser)
- `"session"` — Uses Open WebUI JWT session cookie

## Prerequisites

1. **`WEBUI_SECRET_KEY` must be fixed** — Without it, OAuth tokens are encrypted with a random key that changes on container restart, breaking all OAuth MCP connections.

2. **OAuth startup errors are expected** — On v0.7.2, booting with MCP OAuth connections shows decryption errors. The connections may need re-registration via the Admin UI after restart.

## Limitations

- Only **Streamable HTTP** transport is supported natively. SSE and stdio servers must go through MCPO proxy.
- `TOOL_SERVER_CONNECTIONS` JSON format may evolve in future versions.
- GitHub Issue #20500 reports 400 errors with some Streamable HTTP configurations.
- Atlassian's Streamable HTTP endpoint is not officially confirmed yet.

## Current Deployment Configuration

Our `TOOL_SERVER_CONNECTIONS` currently has only the proxy. To add native MCP servers, we would extend it. However, since all our current servers benefit from proxy-level access control, we keep them through the proxy for now.

When Lukas provides OAuth credentials for Notion/Linear/Sentry, we can add them as direct connections alongside the proxy.
