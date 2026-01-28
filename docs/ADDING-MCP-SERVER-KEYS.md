# How to Add a New MCP Server API Key

## Quick Steps

1. **Add the key to `.env`** on Hetzner:
   ```bash
   ssh root@46.224.193.25
   nano /root/IO/.env
   # Add: NEW_KEY=your-api-key-here
   ```

2. **Restart MCP Proxy** (picks up new env vars):
   ```bash
   cd /root/IO
   docker compose -f docker-compose.hetzner-unified.yml restart mcp-proxy
   ```

3. **Refresh tool cache** (loads tools from newly enabled server):
   ```bash
   curl -X POST http://localhost:8000/refresh
   ```

4. **Verify** tools appear:
   ```bash
   curl -s http://localhost:8000/health | python3 -m json.tool
   ```

## How Auto-Enable Works

Each MCP server in `tenants.py` has an auto-enable condition:

```python
enabled=bool(os.getenv("API_KEY_NAME"))
```

When the env var is set and non-empty, the server enables automatically.
When the env var is missing or empty, the server disables and its tools don't appear.

No code changes needed — just set the env var and restart.

## Available Servers and Their Keys

### Currently Enabled (have API keys)
| Server | Env Var | Tools |
|---|---|---|
| Filesystem | (no key needed) | 14 tools |
| ClickUp | `CLICKUP_API_TOKEN` | 177+ tools |
| Excel Creator | (no key needed) | 2 tools |
| Dashboard | (no key needed) | 2 tools |

### Waiting for API Keys
| Server | Env Var | How to Get |
|---|---|---|
| GitHub | `GITHUB_TOKEN` | [github.com/settings/tokens](https://github.com/settings/tokens) — Classic PAT with `repo`, `read:org` scopes |
| Trello | `TRELLO_API_KEY` + `TRELLO_API_TOKEN` | [trello.com/power-ups/admin](https://trello.com/power-ups/admin) |
| SonarQube | `SONARQUBE_TOKEN` + `SONARQUBE_URL` | [sonarcloud.io](https://sonarcloud.io) — My Account > Security |

### Remote Servers (auto-enable when key is added)
| Server | Env Var | Endpoint |
|---|---|---|
| Linear | `LINEAR_API_KEY` | mcp.linear.app |
| Notion | `NOTION_API_KEY` | mcp.notion.com |
| HubSpot | `HUBSPOT_API_KEY` | mcp.hubspot.com |
| Pulumi | `PULUMI_ACCESS_TOKEN` | mcp.ai.pulumi.com |
| GitLab | `GITLAB_TOKEN` | gitlab.com/api/v4/mcp |
| Sentry | `SENTRY_AUTH_TOKEN` | mcp.sentry.dev |
| Atlassian | `ATLASSIAN_API_KEY` | mcp.atlassian.com |

### Disabled (need setup beyond API keys)
| Server | Why Disabled |
|---|---|
| Datadog | Requires access request from Datadog |
| Grafana | Requires Grafana Cloud setup |
| Snowflake | Requires tenant-specific URL |
| Slack | Official endpoint coming Q1 2026 |
| Snyk | Requires Snyk setup |

## Adding a Completely New Server

If you want to add a server that's not in the list above:

1. Add the server config to `mcp-proxy/tenants.py` in the appropriate tier
2. Add the env var to `.env` and `docker-compose.hetzner-unified.yml`
3. If it needs a container (STDIO servers), add the container to docker-compose
4. Add the group-tenant mapping to `mcp-proxy/config/mcp-servers.json`
5. Rebuild: `docker compose -f docker-compose.hetzner-unified.yml up -d --build mcp-proxy`
6. Re-seed: `docker compose -f docker-compose.hetzner-unified.yml run --rm db-init`
7. Refresh: `curl -X POST http://localhost:8000/refresh`
