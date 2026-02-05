# Webhook Handler Service - MVP Design

## Date: February 5, 2026
## Status: Design Phase

---

## 1. Overview

A new standalone service that receives external webhooks and routes them to Open WebUI's backend, starting with GitHub issue analysis.

**Goal:** When a GitHub issue is created → AI analyzes it → Posts solution as comment

**Lukas's Vision:** "Most other AI systems don't have it, where it's only the other way - only you can trigger them from chat to somewhere else. If there is an issue raised in GitHub, it can trigger some logic in WebUI and analyze the issue and suggest solution."

---

## 2. MVP Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Architecture | Smart Router Service | Single entry point, flexible routing |
| Service Type | New standalone (`webhook-handler/`) | Clean separation from api-gateway |
| First Trigger | GitHub Webhooks | Best documented, clear use case |
| GitHub Events | `issues.opened` only | Simplest MVP, proves concept |
| Response | Comment on issue | Visible, matches Lukas's example |
| Backend Target | `/api/chat/completions` | Reliable, avoids MCP API issues |

---

## 3. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         GitHub                                   │
│                    (issues.opened event)                         │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
              ┌─────────────────────────┐
              │   webhook-handler/      │  ← NEW SERVICE
              │   Port: 8086            │
              │                         │
              │   POST /webhook/github  │
              │   - Validate signature  │
              │   - Parse issue payload │
              │   - Build AI prompt     │
              └────────────┬────────────┘
                           ▼
              ┌─────────────────────────┐
              │     Open WebUI          │
              │ /api/chat/completions   │
              │   - AI analyzes issue   │
              │   - Returns suggestion  │
              └────────────┬────────────┘
                           ▼
              ┌─────────────────────────┐
              │   webhook-handler/      │
              │   - Format response     │
              │   - POST to GitHub API  │
              │   - Add comment         │
              └─────────────────────────┘
```

---

## 4. File Structure

```
webhook-handler/
├── Dockerfile
├── requirements.txt
├── main.py              # FastAPI app, routes
├── handlers/
│   ├── __init__.py
│   └── github.py        # GitHub webhook handler
├── clients/
│   ├── __init__.py
│   ├── openwebui.py     # Open WebUI API client
│   └── github.py        # GitHub API client (for posting comments)
└── config.py            # Environment variables
```

---

## 5. Data Flow

### 5.1 Incoming Webhook (GitHub → Service)

**GitHub POST payload:**
```json
{
  "action": "opened",
  "issue": {
    "number": 123,
    "title": "Bug: Login not working",
    "body": "When I try to login with Microsoft account...",
    "user": { "login": "username" },
    "labels": [{ "name": "bug" }],
    "html_url": "https://github.com/org/repo/issues/123"
  },
  "repository": {
    "full_name": "org/repo"
  }
}
```

### 5.2 AI Request (Service → Open WebUI)

**POST /api/chat/completions:**
```json
{
  "model": "gpt-4-turbo",
  "messages": [
    {
      "role": "system",
      "content": "You are a helpful AI assistant that analyzes GitHub issues and suggests solutions. Be concise and actionable."
    },
    {
      "role": "user",
      "content": "Analyze this GitHub issue and suggest a solution:\n\nTitle: Bug: Login not working\n\nDescription:\nWhen I try to login with Microsoft account...\n\nLabels: bug\n\nProvide:\n1. Brief summary of the issue\n2. Possible root causes\n3. Suggested solution steps\n4. Related files to check (if applicable)"
    }
  ],
  "stream": false
}
```

### 5.3 Response (Service → GitHub)

**POST /repos/{owner}/{repo}/issues/{issue_number}/comments:**
```json
{
  "body": "🤖 **AI Analysis**\n\n**Summary:** This appears to be an authentication issue...\n\n**Possible Causes:**\n1. ...\n\n**Suggested Solution:**\n1. ...\n\n---\n*Generated by Open WebUI AI Assistant*"
}
```

---

## 6. API Endpoints

### 6.1 Webhook Endpoint

```
POST /webhook/github
```

**Headers:**
- `X-Hub-Signature-256`: GitHub HMAC signature for validation
- `X-GitHub-Event`: Event type (e.g., `issues`)
- `X-GitHub-Delivery`: Unique delivery ID

**Response:**
```json
{
  "success": true,
  "message": "Issue analyzed, comment posted",
  "issue_number": 123,
  "comment_id": 456
}
```

### 6.2 Health Endpoint

```
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "webhook-handler",
  "version": "1.0.0"
}
```

---

## 7. Configuration

### 7.1 Environment Variables

```bash
# Service
PORT=8086
DEBUG=false

# GitHub
GITHUB_WEBHOOK_SECRET=your-webhook-secret
GITHUB_TOKEN=ghp_xxxxx  # For posting comments

# Open WebUI
OPENWEBUI_URL=http://open-webui:8080
OPENWEBUI_API_KEY=your-api-key

# AI Settings
AI_MODEL=gpt-4-turbo
AI_SYSTEM_PROMPT="You are a helpful AI assistant..."
```

### 7.2 Docker Compose Addition

```yaml
webhook-handler:
  build: ./webhook-handler
  container_name: webhook-handler
  restart: unless-stopped
  ports:
    - "8086:8086"
  environment:
    - PORT=8086
    - GITHUB_WEBHOOK_SECRET=${GITHUB_WEBHOOK_SECRET}
    - GITHUB_TOKEN=${GITHUB_TOKEN}
    - OPENWEBUI_URL=http://open-webui:8080
    - OPENWEBUI_API_KEY=${OPENWEBUI_API_KEY}
    - AI_MODEL=gpt-4-turbo
  networks:
    - backend
  depends_on:
    - open-webui
```

---

## 8. Security

### 8.1 Webhook Signature Validation

```python
import hmac
import hashlib

def verify_github_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify GitHub webhook signature."""
    expected = 'sha256=' + hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

### 8.2 Rate Limiting

- Limit webhook processing to 10 requests/minute per repository
- Queue webhooks if Open WebUI is slow to respond

---

## 9. Error Handling

| Error | Handling |
|-------|----------|
| Invalid signature | Return 401, log attempt |
| Open WebUI timeout | Retry 3x with exponential backoff |
| GitHub API error | Log error, don't retry |
| Unsupported event | Return 200 (acknowledge), ignore |

---

## 10. Future Enhancements (Post-MVP)

### Phase 2: More Triggers
- Slack Events API
- Microsoft Teams
- Discord
- Scheduled (cron)

### Phase 3: More Backends
- n8n workflows
- MCP Tools (via Pipe Functions)
- WebUI Pipelines

### Phase 4: Smart Routing
- Payload-based routing to different backends
- Admin UI for configuring routes

---

## 11. Testing Plan

### 11.1 Local Testing
1. Run service locally
2. Use `ngrok` to expose webhook URL
3. Configure GitHub webhook to point to ngrok URL
4. Create test issue, verify comment posted

### 11.2 Integration Testing
```bash
# Simulate GitHub webhook
curl -X POST http://localhost:8086/webhook/github \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: issues" \
  -H "X-Hub-Signature-256: sha256=..." \
  -d '{"action": "opened", "issue": {...}}'
```

---

## 12. Success Criteria

- [ ] GitHub issue created → AI comment posted within 30 seconds
- [ ] Webhook signature validation working
- [ ] Error handling for Open WebUI timeouts
- [ ] Deployed to Hetzner VPS
- [ ] Caddy configured to route `/webhook/*` to service

---

## 13. Open Questions

1. Should we filter issues by label? (e.g., only analyze issues with `ai-help` label)
2. Should we limit to specific repositories?
3. What model should be default? (gpt-4-turbo vs gpt-4o)
4. Should responses include a "feedback" mechanism?

---

## 14. Additional Tasks (From Lukas)

**Bug Report:** Microsoft login not working for `lherajt@gmail.com`
- User can't call Trello/GitHub from proxy server
- Need to check which MCP servers the account has permissions for
- **Action:** Investigate and fix before webhook implementation
