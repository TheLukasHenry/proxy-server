# Hosted n8n Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Connect the MCP n8n tools to Lukas's hosted n8n at `n8n.srv1041674.hstgr.cloud` instead of the local n8n container.

**Architecture:** The `mcp-n8n` container stays as-is (mcpo wrapping n8n-mcp). We change its `N8N_API_URL` env var from `http://n8n:5678` (local) to the hosted n8n URL, and update the API key. The local `n8n` container is kept in docker-compose for local dev but stopped on the live server.

**Tech Stack:** Docker Compose, n8n REST API, mcpo, n8n-mcp

---

### Task 1: Update docker-compose.unified.yml

**Files:**
- Modify: `docker-compose.unified.yml:440` (N8N_API_URL)
- Modify: `docker-compose.unified.yml:446-447` (depends_on)

**Step 1: Change mcp-n8n N8N_API_URL to use env var with hosted default**

In `docker-compose.unified.yml` line 440, change:
```yaml
# Before:
      - N8N_API_URL=http://n8n:5678

# After:
      - N8N_API_URL=${N8N_API_URL:-https://n8n.srv1041674.hstgr.cloud}
```

**Step 2: Remove depends_on n8n from mcp-n8n**

In `docker-compose.unified.yml` lines 446-447, remove:
```yaml
    depends_on:
      - n8n
```

**Step 3: Commit**

```bash
git add docker-compose.unified.yml
git commit -m "feat: point mcp-n8n at hosted n8n instead of local container"
```

---

### Task 2: Update local .env with hosted n8n credentials

**Files:**
- Modify: `.env:85-90` (N8N section)

**Step 1: Update the N8N section in .env**

Replace lines 85-90 with:
```bash
# =============================================================================
# N8N (Hosted: n8n.srv1041674.hstgr.cloud)
# =============================================================================
N8N_USER=admin
N8N_PASSWORD=admin123
N8N_API_URL=https://n8n.srv1041674.hstgr.cloud
N8N_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmMjdmMjI2NC1hZDNhLTQ1OWUtODlkYy05M2Y5MGMzODI5YTIiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzcxMzg4NDI1LCJleHAiOjE3NzM5NjEyMDB9.IsejHHCngQ-qoD8m41tqpANKpTntF_H_XBYtXKBrsOw
```

**Step 2: Do NOT commit .env** (contains secrets, should be in .gitignore)

---

### Task 3: Deploy to live server

**Step 1: SCP updated docker-compose to server**

```bash
scp docker-compose.unified.yml root@46.224.193.25:/root/proxy-server/docker-compose.unified.yml
```

**Step 2: SSH in and update server .env**

```bash
ssh root@46.224.193.25
cd /root/proxy-server

# Update N8N_API_KEY with hosted n8n key
sed -i 's|^N8N_API_KEY=.*|N8N_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmMjdmMjI2NC1hZDNhLTQ1OWUtODlkYy05M2Y5MGMzODI5YTIiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzcxMzg4NDI1LCJleHAiOjE3NzM5NjEyMDB9.IsejHHCngQ-qoD8m41tqpANKpTntF_H_XBYtXKBrsOw|' .env

# Add N8N_API_URL if not present
grep -q 'N8N_API_URL' .env || echo 'N8N_API_URL=https://n8n.srv1041674.hstgr.cloud' >> .env
```

**Step 3: Rebuild mcp-n8n and restart mcp-proxy**

```bash
docker compose -f docker-compose.unified.yml up -d --build mcp-n8n
docker compose -f docker-compose.unified.yml restart mcp-proxy
```

**Step 4: Verify mcp-n8n can reach hosted n8n**

```bash
# Check mcp-n8n logs for connection errors
docker logs mcp-n8n --tail 20

# Test the n8n API directly from server
curl -s -H "Authorization: Bearer <API_KEY>" https://n8n.srv1041674.hstgr.cloud/api/v1/workflows | head -c 200
```

Expected: JSON response with workflows list (or empty array).

---

### Task 4: Test MCP tools via Open WebUI

**Step 1: Open AIUI in browser**

Navigate to `https://ai-ui.coolestdomain.win`

**Step 2: Start a new chat and test n8n MCP tools**

Ask: "List all n8n workflows"

Expected: The AI uses the n8n MCP tools to call the hosted n8n API and returns a list of workflows.

**Step 3: Test workflow creation**

Ask: "Create a simple n8n workflow that triggers on a webhook and returns hello world"

Expected: A workflow is created on the hosted n8n at `n8n.srv1041674.hstgr.cloud`.

**Step 4: Verify on hosted n8n**

Check `n8n.srv1041674.hstgr.cloud` to confirm the workflow appears there.

---

### Task 5: Commit and create PR

**Step 1: Commit docker-compose changes**

```bash
git add docker-compose.unified.yml
git commit -m "feat: connect mcp-n8n to hosted n8n at srv1041674.hstgr.cloud"
```

**Step 2: Push and create PR**

```bash
git push ai-ui fix/mcp-network-split
gh pr create --title "feat: hosted n8n + webhook automation + rate limit fixes" --body "..."
```

**Step 3: Send Lukas the env vars via WhatsApp**

Key vars he needs:
- `N8N_API_URL=https://n8n.srv1041674.hstgr.cloud`
- `N8N_API_KEY=<the hosted key>`
- `MCP_API_KEY=mcp-secret-key-hetzner-2026`
- Any other new vars from recent changes
