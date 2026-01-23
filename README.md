# MCP Proxy Gateway

A multi-tenant MCP (Model Context Protocol) proxy gateway that provides unified URL routing for all MCP servers with enterprise-grade authentication and access control.

## Features

- **Unified URL Routing**: Hierarchical routing (`/{server}/{tool}`) for all MCP servers
- **Multi-Tenant Support**: Database-backed tenant access control
- **Authentication**: JWT validation, Entra ID integration, API Gateway mode
- **70+ MCP Server Integrations**: GitHub, Linear, Notion, Jira, and more
- **Server Tiers**:
  - HTTP: Direct connection (Linear, Notion, Sentry)
  - SSE: Server-Sent Events via mcpo proxy (Atlassian, Asana)
  - stdio: Standard I/O via mcpo proxy (SonarQube, databases)
  - Local: In-cluster Kubernetes containers

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL database
- Docker (optional)

### Installation

```bash
# Clone the repository
git clone https://github.com/TheLukasHenry/proxy-server.git
cd proxy-server

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run the server
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### Docker

```bash
docker build -t mcp-proxy .
docker run -p 8000:8000 -e DATABASE_URL=... mcp-proxy
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://...` |
| `WEBUI_SECRET_KEY` | Open WebUI JWT secret for validation | Required |
| `API_GATEWAY_MODE` | Trust API Gateway headers | `false` |
| `MCP_API_KEY` | Internal API key for MCP servers | `test-key` |
| `DEBUG` | Enable debug logging | `false` |

### MCP Server Credentials

Each MCP server may require its own API key:

- `GITHUB_TOKEN` - GitHub Personal Access Token
- `LINEAR_API_KEY` - Linear API key
- `NOTION_API_KEY` - Notion integration token
- `ATLASSIAN_TOKEN` - Atlassian API token
- And more (see `tenants.py`)

## API Endpoints

### Server Discovery

```
GET /servers          - List all available MCP servers
GET /{server}         - List tools for a specific server
```

### Tool Execution

```
POST /{server}/{tool} - Execute a tool (preferred format)
POST /{server}_{tool} - Legacy format (deprecated)
```

### Examples

```bash
# List all servers
curl http://localhost:8000/servers

# List GitHub tools
curl http://localhost:8000/github

# Search repositories
curl -X POST http://localhost:8000/github/search_repositories \
  -H "Content-Type: application/json" \
  -d '{"query": "mcp"}'
```

## Authentication

### JWT Validation (Default)

The proxy validates JWT tokens from Open WebUI using `WEBUI_SECRET_KEY`. This ensures requests are authenticated before trusting user headers.

### API Gateway Mode

When `API_GATEWAY_MODE=true`, the proxy trusts headers set by an upstream API gateway (Traefik, Azure APIM, etc.) that has already validated the user.

Headers:
- `X-User-Email` - User's email address
- `X-User-Groups` - Comma-separated list of groups
- `X-User-Admin` - Admin status (true/false)

### Entra ID Integration

For Microsoft Entra ID (Azure AD) integration, the proxy can extract groups from Entra ID tokens for fine-grained access control.

## Access Control

Access control is managed via PostgreSQL tables:

### User-Tenant Access

```sql
-- Grant user access to a server
INSERT INTO user_tenant_access (user_email, tenant_id, access_level)
VALUES ('user@company.com', 'github', 'read');
```

### Group-Tenant Mapping

```sql
-- Map a group to a server
INSERT INTO group_tenant_mapping (group_name, tenant_id)
VALUES ('MCP-GitHub', 'github');
```

### MCP-Admin Group

Users in the `MCP-Admin` group have access to ALL servers.

## Project Structure

```
proxy-server/
├── main.py           # FastAPI application and routing
├── auth.py           # Authentication module (JWT, Entra ID)
├── tenants.py        # Server/tenant configuration
├── db.py             # Database access layer
├── mcp_server.py     # FastMCP native MCP support
├── tools.py          # Tool utilities
├── token_validator.py # Token validation helpers
├── config/           # Server configurations
├── scripts/          # Utility scripts
├── Dockerfile        # Container image
├── docker-compose.yml
├── requirements.txt
└── start.sh          # Startup script
```

## License

MIT License
