# WEBHOOK ARCHITECTURE - Complete Explanation

## What is a Webhook?

**Normal API:** You ask for data → Server responds
```
YOU  ───────►  SERVER
     "Give me data"

YOU  ◄───────  SERVER
     "Here's data"
```

**Webhook (Reverse):** Server tells YOU when something happens
```
GITHUB  ───────►  YOUR SERVER
        "Hey! Someone created an issue!"
```

**Simple analogy:**
- **Normal API** = You call a restaurant to ask if your table is ready
- **Webhook** = Restaurant calls YOU when your table is ready

---

## Our Webhook System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   STEP 1: Someone creates an issue on GitHub                                │
│                                                                             │
│   ┌──────────────────────────────────────────┐                              │
│   │         GITHUB.COM                        │                              │
│   │                                           │                              │
│   │   User clicks "New Issue"                 │                              │
│   │   Title: "Login button broken"            │                              │
│   │   Body: "When I click login..."           │                              │
│   │                                           │                              │
│   └──────────────────┬───────────────────────┘                              │
│                      │                                                       │
│                      │ GitHub sends POST request automatically               │
│                      │ to YOUR webhook URL                                   │
│                      ▼                                                       │
│   ┌──────────────────────────────────────────┐                              │
│   │   STEP 2: Caddy receives request          │                              │
│   │                                           │                              │
│   │   URL: https://ai-ui.coolestdomain.win    │                              │
│   │        /webhook/github                    │                              │
│   │                                           │                              │
│   │   Routes to → webhook-handler:8086        │                              │
│   └──────────────────┬───────────────────────┘                              │
│                      │                                                       │
│                      ▼                                                       │
│   ┌──────────────────────────────────────────┐                              │
│   │   STEP 3: webhook-handler/main.py         │                              │
│   │                                           │                              │
│   │   1. Verify signature (is it real GitHub?)│                              │
│   │   2. Parse JSON payload                   │                              │
│   │   3. Check event type = "issues"          │                              │
│   │   4. Check action = "opened"              │                              │
│   │                                           │                              │
│   └──────────────────┬───────────────────────┘                              │
│                      │                                                       │
│                      ▼                                                       │
│   ┌──────────────────────────────────────────┐                              │
│   │   STEP 4: handlers/github.py              │                              │
│   │                                           │                              │
│   │   Extract from payload:                   │                              │
│   │   - issue_number: 123                     │                              │
│   │   - title: "Login button broken"          │                              │
│   │   - body: "When I click login..."         │                              │
│   │   - repo: "TheLukasHenry/proxy-server"    │                              │
│   │                                           │                              │
│   └──────────────────┬───────────────────────┘                              │
│                      │                                                       │
│                      ▼                                                       │
│   ┌──────────────────────────────────────────┐                              │
│   │   STEP 5: clients/openwebui.py            │                              │
│   │                                           │                              │
│   │   Call Open WebUI AI:                     │                              │
│   │   POST http://open-webui:8080             │                              │
│   │        /api/chat/completions              │                              │
│   │                                           │                              │
│   │   {                                       │                              │
│   │     "model": "gpt-5",                     │                              │
│   │     "messages": [                         │                              │
│   │       {"role": "system", "content":       │                              │
│   │        "You analyze GitHub issues..."},   │                              │
│   │       {"role": "user", "content":         │                              │
│   │        "Analyze: Login button broken..."}  │                              │
│   │     ]                                     │                              │
│   │   }                                       │                              │
│   │                                           │                              │
│   │   AI Response: "This appears to be a      │                              │
│   │   CSS issue. Check the button styles..."  │                              │
│   │                                           │                              │
│   └──────────────────┬───────────────────────┘                              │
│                      │                                                       │
│                      ▼                                                       │
│   ┌──────────────────────────────────────────┐                              │
│   │   STEP 6: clients/github.py               │                              │
│   │                                           │                              │
│   │   Post comment to GitHub:                 │                              │
│   │   POST https://api.github.com/repos/      │                              │
│   │        TheLukasHenry/proxy-server/        │                              │
│   │        issues/123/comments                │                              │
│   │                                           │                              │
│   │   {                                       │                              │
│   │     "body": "🤖 **AI Analysis**\n\n       │                              │
│   │      This appears to be a CSS issue..."   │                              │
│   │   }                                       │                              │
│   │                                           │                              │
│   └──────────────────────────────────────────┘                              │
│                                                                             │
│   RESULT: GitHub issue now has AI comment!                                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## File Structure & Purpose

```
webhook-handler/
│
├── main.py                 ← ENTRY POINT
│   │                         - FastAPI app
│   │                         - /health endpoint (GET)
│   │                         - /webhook/github endpoint (POST)
│   │                         - Verifies GitHub signature
│   │
├── config.py               ← SETTINGS
│   │                         - Loads from .env file
│   │                         - GITHUB_TOKEN
│   │                         - GITHUB_WEBHOOK_SECRET
│   │                         - OPENWEBUI_API_KEY
│   │                         - AI_MODEL (gpt-5)
│   │
├── handlers/
│   └── github.py           ← EVENT HANDLER
│       │                     - Receives "issues.opened" event
│       │                     - Extracts title, body, labels
│       │                     - Calls OpenWebUI for AI analysis
│       │                     - Calls GitHub to post comment
│       │
├── clients/
│   ├── openwebui.py        ← TALKS TO AI
│   │   │                     - POST /api/chat/completions
│   │   │                     - Sends issue details
│   │   │                     - Returns AI analysis
│   │   │
│   └── github.py           ← TALKS TO GITHUB
│       │                     - Verifies webhook signatures
│       │                     - Posts comments on issues
│       │
├── Dockerfile              ← CONTAINER
│   │                         - Python 3.11
│   │                         - Runs on port 8086
│   │
└── requirements.txt        ← DEPENDENCIES
                              - fastapi
                              - httpx
                              - pydantic-settings
```

---

## Data Flow (What Gets Sent Where)

### 1. GitHub → Webhook Handler
```json
{
  "action": "opened",
  "issue": {
    "number": 123,
    "title": "Login button broken",
    "body": "When I click login, nothing happens",
    "labels": [{"name": "bug"}]
  },
  "repository": {
    "full_name": "TheLukasHenry/proxy-server"
  }
}
```

### 2. Webhook Handler → Open WebUI
```json
{
  "model": "gpt-5",
  "messages": [
    {
      "role": "system",
      "content": "You analyze GitHub issues and suggest solutions."
    },
    {
      "role": "user",
      "content": "Analyze this issue:\n\nTitle: Login button broken\n\nDescription: When I click login..."
    }
  ]
}
```

### 3. Open WebUI → Webhook Handler
```json
{
  "choices": [{
    "message": {
      "content": "This appears to be a JavaScript event binding issue..."
    }
  }]
}
```

### 4. Webhook Handler → GitHub
```json
{
  "body": "🤖 **AI Analysis**\n\nThis appears to be a JavaScript event binding issue...\n\n---\n*Generated by Open WebUI AI Assistant*"
}
```

---

## Required Environment Variables

| Variable | Purpose | Where Used |
|----------|---------|------------|
| `GITHUB_WEBHOOK_SECRET` | Verify request is really from GitHub | `main.py` signature check |
| `GITHUB_TOKEN` | Post comments to GitHub | `clients/github.py` API calls |
| `OPENWEBUI_API_KEY` | Authenticate with Open WebUI | `clients/openwebui.py` API calls |
| `AI_MODEL` | Which AI model to use | `handlers/github.py` → gpt-5 |

---

## Docker Compose Configuration

```yaml
webhook-handler:
  build: ./webhook-handler
  container_name: webhook-handler
  restart: unless-stopped
  ports:
    - "8086:8086"
  environment:
    - PORT=8086
    - DEBUG=${DEBUG:-false}
    - GITHUB_WEBHOOK_SECRET=${GITHUB_WEBHOOK_SECRET:-}
    - GITHUB_TOKEN=${GITHUB_TOKEN:-}
    - OPENWEBUI_URL=http://open-webui:8080
    - OPENWEBUI_API_KEY=${OPENWEBUI_API_KEY:-}
    - AI_MODEL=${AI_MODEL:-gpt-5}
  networks:
    - backend
  depends_on:
    - open-webui
```

---

## Caddy Route Configuration

```
handle /webhook/* {
    reverse_proxy webhook-handler:8086 {
        header_down Cache-Control "no-store, no-cache, must-revalidate"
    }
}
```

---

## Security: Signature Verification

GitHub signs every webhook request with HMAC-SHA256. We verify it to ensure the request is legitimate.

```python
def verify_github_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected = 'sha256=' + hmac.new(
        secret.encode(),      # GITHUB_WEBHOOK_SECRET from .env
        payload,              # Raw request body
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, signature)
```

---

## Why This is Powerful

**Traditional AI (one-way):**
```
Human → AI → Response shown to human only
```

**Your Webhook System (two-way):**
```
External Event (GitHub) → AI → Action (posts comment back)
```

This means your AI can:
- Automatically respond to GitHub issues
- Analyze bugs when they're reported
- Suggest solutions without human intervention
- Be triggered by ANY external system (Slack, Teams, etc.)

**Lukas's vision:** "Most AI systems only let you trigger them. This lets external events trigger the AI and take action."

---

## Setup Checklist

- [ ] Merge PR #3 to main branch
- [ ] Deploy to Hetzner server
- [ ] Generate `OPENWEBUI_API_KEY` from Open WebUI Settings
- [ ] Configure GitHub webhook in repository settings:
  - URL: `https://ai-ui.coolestdomain.win/webhook/github`
  - Secret: Same as `GITHUB_WEBHOOK_SECRET` in `.env`
  - Events: Select "Issues"
- [ ] Create test issue to verify it works

---

## Future Enhancements

1. **More GitHub Events:** Pull requests, comments, reviews
2. **More Platforms:** Slack, Microsoft Teams, Discord
3. **More Actions:** Create issues, assign labels, trigger workflows
4. **Scheduled Triggers:** Daily reports, weekly summaries
