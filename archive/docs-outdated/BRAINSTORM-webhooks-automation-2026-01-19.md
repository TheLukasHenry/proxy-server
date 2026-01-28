# Brainstorm: Webhooks & Automatic Deployment

**Date:** January 19, 2026
**Purpose:** Analyze Open WebUI webhooks and design automation for deployment

---

## Part 1: Open WebUI Webhook Capabilities

### Three Types of Webhooks

| Type | Purpose | Trigger | Direction |
|------|---------|---------|-----------|
| **Admin Webhook** | Monitor system events | New user registration | Outgoing (WebUI → External) |
| **User Webhook** | Notify when chat done | Response complete | Outgoing (WebUI → External) |
| **Channel Webhook** | Receive external messages | External POST | Incoming (External → WebUI) |

### Event Types (28+ available)

```
Category: auth
├── auth.user.signup      (new user registered)
├── auth.user.login       (user logged in)
└── auth.user.deleted     (user deleted)

Category: chat
├── chat.created          (new chat started)
├── chat.message          (message sent)
├── chat.response         (model response complete)
└── chat.deleted          (chat deleted)

Category: admin
├── admin.user.created    (admin created user)
├── admin.user.deleted    (admin deleted user)
└── admin.settings.updated (settings changed)

Category: system
├── system.startup        (server started)
└── system.shutdown       (server stopping)

Category: tool
├── tool.executed         (MCP tool executed)
└── tool.error            (tool execution failed)

Category: function
├── function.called       (function invoked)
└── function.error        (function failed)
```

### Configuration Methods

**Method 1: Environment Variable**
```env
WEBHOOK_URL=https://your-webhook-endpoint.com/webhook
ENABLE_USER_WEBHOOKS=True
```

**Method 2: Admin Panel**
```
Admin Panel → Settings → General → Webhook URL
```

**Method 3: Per-User (Settings)**
```
User Settings → Account → Notification Webhook
```

**Method 4: Channel Webhooks (Incoming)**
```
Channel Settings → Edit → Webhooks → New Webhook
URL: {WEBUI_API_BASE_URL}/channels/webhooks/{webhook_id}/{token}
```

---

## Part 2: Automation Use Cases

### Use Case 1: Deployment Notification

**When:** Code pushed to GitHub → Kubernetes deploys → Notify team

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   GitHub    │────▶│  GitHub     │────▶│   Azure     │────▶│ Open WebUI  │
│   Push      │     │  Actions    │     │    AKS      │     │  Channel    │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                           │                    │
                           ▼                    ▼
                    Build & Push          kubectl apply
                    Docker Image          to AKS cluster
```

**Implementation:**
```yaml
# .github/workflows/deploy.yml
name: Deploy to AKS
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Build & Push Docker
        run: |
          docker build -t acr.azurecr.io/mcp-proxy:${{ github.sha }}
          docker push acr.azurecr.io/mcp-proxy:${{ github.sha }}

      - name: Deploy to AKS
        run: |
          kubectl set image deployment/mcp-proxy \
            mcp-proxy=acr.azurecr.io/mcp-proxy:${{ github.sha }}

      - name: Notify Open WebUI Channel
        run: |
          curl -X POST "${{ secrets.OPENWEBUI_CHANNEL_WEBHOOK }}" \
            -H "Content-Type: application/json" \
            -d '{"content": "✅ Deployed mcp-proxy:${{ github.sha }} to AKS"}'
```

### Use Case 2: Tool Execution Audit

**When:** MCP tool executed → Log to external audit system

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   User      │────▶│  MCP Proxy  │────▶│   Webhook   │
│  executes   │     │  tool.exec  │     │  Endpoint   │
│   tool      │     │   event     │     │ (audit log) │
└─────────────┘     └─────────────┘     └─────────────┘
```

**Webhook Payload:**
```json
{
  "event": "tool.executed",
  "timestamp": "2026-01-19T10:30:00Z",
  "user": {
    "email": "user@company.com",
    "groups": ["MCP-GitHub", "Tenant-Google"]
  },
  "tool": {
    "server": "github",
    "name": "create_issue",
    "args": {"repo": "company/project", "title": "Bug fix"}
  },
  "result": {
    "success": true,
    "duration_ms": 1250
  }
}
```

### Use Case 3: Access Denied Alert

**When:** User tries to access unauthorized server → Alert security team

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   User      │────▶│  MCP Proxy  │────▶│   Slack     │
│  denied     │     │  403 error  │     │  #security  │
│  access     │     │   event     │     │  channel    │
└─────────────┘     └─────────────┘     └─────────────┘
```

### Use Case 4: Auto-Scale on Load

**When:** High usage detected → Scale Kubernetes pods

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Prometheus │────▶│  Webhook    │────▶│  Azure AKS  │
│  alert rule │     │  receiver   │     │  scale up   │
└─────────────┘     └─────────────┘     └─────────────┘
```

---

## Part 3: Automatic Deployment Architecture

### Option A: GitHub Actions + AKS (Recommended)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    AUTOMATIC DEPLOYMENT PIPELINE                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. TRIGGER (Webhook)                                                    │
│     ├── GitHub Push to main branch                                       │
│     ├── Manual dispatch (workflow_dispatch)                              │
│     └── Scheduled (cron)                                                 │
│                                                                          │
│  2. BUILD (GitHub Actions)                                               │
│     ├── Checkout code                                                    │
│     ├── Run tests                                                        │
│     ├── Build Docker images                                              │
│     │   ├── mcp-proxy                                                    │
│     │   ├── mcp-github                                                   │
│     │   └── mcp-filesystem                                               │
│     └── Push to Azure Container Registry (ACR)                          │
│                                                                          │
│  3. DEPLOY (kubectl / Helm)                                              │
│     ├── Connect to AKS cluster                                           │
│     ├── Apply Kubernetes manifests                                       │
│     ├── Wait for rollout                                                 │
│     └── Run health checks                                                │
│                                                                          │
│  4. NOTIFY (Webhook)                                                     │
│     ├── Post to Open WebUI channel                                       │
│     ├── Post to Slack/Teams                                              │
│     └── Update GitHub deployment status                                  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Option B: Azure DevOps Pipeline

```yaml
# azure-pipelines.yml
trigger:
  branches:
    include:
      - main

stages:
  - stage: Build
    jobs:
      - job: BuildAndPush
        pool:
          vmImage: 'ubuntu-latest'
        steps:
          - task: Docker@2
            inputs:
              command: buildAndPush
              containerRegistry: 'AzureContainerRegistry'
              repository: 'mcp-proxy'

  - stage: Deploy
    jobs:
      - deployment: DeployToAKS
        environment: 'production'
        strategy:
          runOnce:
            deploy:
              steps:
                - task: KubernetesManifest@0
                  inputs:
                    action: deploy
                    kubernetesServiceConnection: 'AKS-Connection'
                    manifests: 'kubernetes/*.yaml'
```

### Option C: GitOps with Flux/ArgoCD

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         GITOPS FLOW                                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  GitHub Repo (source)          GitHub Repo (config)          AKS        │
│  ┌─────────────────┐           ┌─────────────────┐      ┌──────────┐   │
│  │  Application    │──build───▶│  kubernetes/    │◀─────│  Flux/   │   │
│  │  Source Code    │  push     │  manifests      │ sync │  ArgoCD  │   │
│  └─────────────────┘           └─────────────────┘      └──────────┘   │
│                                                                          │
│  Benefits:                                                               │
│  • Git is single source of truth                                         │
│  • Automatic sync when manifests change                                  │
│  • Easy rollback (git revert)                                            │
│  • Audit trail in git history                                            │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Part 4: Implementation Plan

### Step 1: Set Up Azure Container Registry (ACR)

```bash
# Create ACR
az acr create --resource-group io-rg \
  --name iomcpregistry --sku Basic

# Enable admin access
az acr update -n iomcpregistry --admin-enabled true

# Get credentials
az acr credential show -n iomcpregistry
```

### Step 2: Create GitHub Actions Workflow

```yaml
# .github/workflows/deploy-aks.yml
name: Deploy to Azure AKS

on:
  push:
    branches: [main]
    paths:
      - 'mcp-proxy/**'
      - 'kubernetes/**'

env:
  REGISTRY: iomcpregistry.azurecr.io
  AKS_CLUSTER: io-aks-cluster
  AKS_RESOURCE_GROUP: io-rg

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Azure Login
        uses: azure/login@v2
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: ACR Login
        run: az acr login --name iomcpregistry

      - name: Build & Push MCP Proxy
        run: |
          docker build -t $REGISTRY/mcp-proxy:${{ github.sha }} ./mcp-proxy
          docker push $REGISTRY/mcp-proxy:${{ github.sha }}

      - name: Set AKS Context
        uses: azure/aks-set-context@v3
        with:
          cluster-name: ${{ env.AKS_CLUSTER }}
          resource-group: ${{ env.AKS_RESOURCE_GROUP }}

      - name: Deploy to AKS
        run: |
          kubectl set image deployment/mcp-proxy \
            mcp-proxy=$REGISTRY/mcp-proxy:${{ github.sha }} \
            -n open-webui
          kubectl rollout status deployment/mcp-proxy -n open-webui

      - name: Notify Success
        if: success()
        run: |
          curl -X POST "${{ secrets.WEBHOOK_URL }}" \
            -H "Content-Type: application/json" \
            -d '{"content": "✅ Deployed mcp-proxy to AKS"}'

      - name: Notify Failure
        if: failure()
        run: |
          curl -X POST "${{ secrets.WEBHOOK_URL }}" \
            -H "Content-Type: application/json" \
            -d '{"content": "❌ Failed to deploy mcp-proxy"}'
```

### Step 3: Configure Open WebUI Webhook

```env
# Add to kubernetes/open-webui-configmap.yaml
WEBHOOK_URL=https://hooks.slack.com/services/xxx/yyy/zzz
ENABLE_USER_WEBHOOKS=True
```

### Step 4: Set Up Channel Webhook for CI/CD Notifications

1. Open WebUI → Create channel `#deployments`
2. Channel Settings → Edit → Webhooks → New Webhook
3. Copy webhook URL
4. Add to GitHub Secrets as `OPENWEBUI_CHANNEL_WEBHOOK`

---

## Part 5: Webhook Security

### Best Practices

| Practice | Implementation |
|----------|----------------|
| **Secret Tokens** | Include `?token=xxx` in webhook URL |
| **HTTPS Only** | Never use HTTP for webhooks |
| **IP Allowlist** | Restrict webhook endpoints to known IPs |
| **Rate Limiting** | Limit webhook calls per minute |
| **Signature Verification** | Verify HMAC signature on incoming webhooks |

### Disable User Webhooks (If Needed)

```env
# Prevents users from setting external webhook URLs
ENABLE_USER_WEBHOOKS=False
```

---

## Part 6: Summary - What We Can Do

### Outgoing Webhooks (Open WebUI → External)

| Event | Target | Use Case |
|-------|--------|----------|
| New user signup | Slack | Notify admin of new users |
| Chat response complete | User's phone | Push notification |
| Admin settings changed | Audit log | Compliance tracking |

### Incoming Webhooks (External → Open WebUI)

| Source | Target | Use Case |
|--------|--------|----------|
| GitHub Actions | #deployments channel | Deploy notifications |
| Prometheus alerts | #alerts channel | System alerts |
| CI/CD pipeline | #dev channel | Build status |

### Deployment Automation

| Trigger | Action | Result |
|---------|--------|--------|
| Push to main | GitHub Actions | Auto-deploy to AKS |
| Manual approval | Azure DevOps | Production deploy |
| Config change | Flux/ArgoCD | GitOps sync |

---

## Recommendation

For your setup with **Entra ID + AKS + Open WebUI**:

1. **Use GitHub Actions** for CI/CD (free for public repos)
2. **Set up Channel Webhooks** in Open WebUI for notifications
3. **Configure Admin Webhook** to Slack for user signups
4. **Add WEBHOOK_URL** env var for system events

This gives you:
- Automatic deployment on git push
- Team notifications in Open WebUI
- External notifications to Slack/Teams
- Audit trail for compliance

---

## Sources

- [Open WebUI Webhook Documentation](https://docs.openwebui.com/features/interface/webhooks/)
- [Webhook Enhancements Discussion](https://github.com/open-webui/open-webui/discussions/16428)
- [User Notification Webhooks Discussion](https://github.com/open-webui/open-webui/discussions/19057)

---

*Generated: January 19, 2026*
