# Token Refresh Guide for Hetzner Deployment

## Status (2026-01-27)

### Working Tools (200 OK)
- **ClickUp** - Lukas's workspace found (ID: 9017796800)
- **Filesystem** - File listing works (test.txt in /data)
- **Excel Creator** - Spreadsheet generation works
- **Dashboard** - Dashboard generation works

### Failing Tools (Need Fresh Tokens from Lukas)

#### 1. GitHub - 401 Bad Credentials
The GitHub Personal Access Token (PAT) has expired.

**What Lukas needs to do:**
1. Go to https://github.com/settings/tokens
2. Generate a new **classic** Personal Access Token
3. Select scopes: `repo`, `read:org`, `read:user`, `user:email`
4. Copy the token (starts with `ghp_`)

**Where to update on Hetzner:**
```bash
ssh root@46.224.193.25
nano /root/IO/.env
# Update: GITHUB_TOKEN=ghp_YOUR_NEW_TOKEN
docker compose -f docker-compose.hetzner-unified.yml up -d --build mcp-github mcp-proxy
```

#### 2. Trello - 401 Unauthorized
The Trello API key and token are invalid or expired.

**What Lukas needs to do:**
1. Go to https://trello.com/power-ups/admin
2. Get the API Key
3. Then generate a Token by visiting:
   `https://trello.com/1/authorize?expiration=never&scope=read,write&response_type=token&key=YOUR_API_KEY`
4. Note both the API Key and the Token

**Where to update on Hetzner:**
```bash
ssh root@46.224.193.25
nano /root/IO/.env
# Update:
# TRELLO_API_KEY=your_api_key
# TRELLO_API_TOKEN=your_token
docker compose -f docker-compose.hetzner-unified.yml up -d --build mcp-trello mcp-proxy
```

#### 3. SonarQube - 400 Bad Request
The SonarQube server needs an organization ID for SonarCloud.

**What Lukas needs to do:**
1. Log into https://sonarcloud.io
2. Go to My Account > Organizations
3. Copy the organization key (e.g., `lukasherajt`)

**Where to update on Hetzner:**
```bash
ssh root@46.224.193.25
nano /root/IO/.env
# Update:
# SONARQUBE_TOKEN=your_token
# SONARQUBE_URL=https://sonarcloud.io
# SONARQUBE_ORG=your_org_key    (add this new variable)
docker compose -f docker-compose.hetzner-unified.yml up -d --build mcp-sonarqube mcp-proxy
```

### Disabled Tools (No API Keys - Expected)
These servers auto-disable because no API keys are configured in `.env`:
- Linear, Notion, HubSpot, Pulumi, GitLab, Sentry, Atlassian

To enable any of these, add the corresponding API key to `.env` and rebuild.

## After Updating Tokens

After updating any tokens in `.env`, rebuild the affected containers:

```bash
cd /root/IO

# Rebuild and restart affected services
docker compose -f docker-compose.hetzner-unified.yml up -d --build

# Verify MCP Proxy picked up the new tools
curl -s http://localhost:8000/health | python3 -m json.tool

# Trigger a tool cache refresh
curl -X POST http://localhost:8000/refresh

# Test specific tools
# GitHub:
curl -s -X POST http://localhost:8000/github/get_me \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT" \
  -d '{}'

# Trello:
curl -s -X POST http://localhost:8000/trello/get_boards \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT" \
  -d '{}'
```

## End-to-End Verified (2026-01-27)

The full flow has been verified working:
1. Open WebUI (gpt-4o) sends JWT to MCP Proxy
2. MCP Proxy validates JWT, looks up user identity from DB
3. MCP Proxy routes tool call to correct backend MCP server
4. Backend MCP server executes and returns data
5. Open WebUI displays the tool result to the user

Tested tools via browser:
- `filesystem_list_directory` -> returned `[FILE] test.txt`
- ClickUp `get_workspaces` -> returned "Lukas Herajt's Workspace" (ID: 9017796800)
