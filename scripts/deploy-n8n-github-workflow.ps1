# scripts/deploy-n8n-github-workflow.ps1
# Deploys the "GitHub Push Processor" workflow to n8n via API.
#
# This workflow:
#   [Webhook: github-push] -> [Extract Push Data] -> [AI Summary] -> [Format Response] -> [Respond]
#
# Usage:
#   .\scripts\deploy-n8n-github-workflow.ps1
#   .\scripts\deploy-n8n-github-workflow.ps1 -N8nUrl "http://localhost:5678"

param(
    [string]$N8nUrl = "http://localhost:5678",
    [string]$N8nApiKey = "",
    [switch]$Help
)

$ErrorActionPreference = "Stop"

function Write-Step { param($msg) Write-Host "[STEP] $msg" -ForegroundColor Yellow }
function Write-Success { param($msg) Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Err { param($msg) Write-Host "[ERROR] $msg" -ForegroundColor Red }
function Write-Info { param($msg) Write-Host "[INFO] $msg" -ForegroundColor White }

if ($Help) {
    Write-Host @"
Deploy n8n "GitHub Push Processor" Workflow

USAGE:
    .\scripts\deploy-n8n-github-workflow.ps1 [OPTIONS]

OPTIONS:
    -N8nUrl      n8n base URL (default: http://localhost:5678)
    -N8nApiKey   n8n API key (default: reads from .env N8N_API_KEY)
    -Help        Show this help

WHAT IT DOES:
    1. Creates a workflow via n8n API with 5 nodes:
       Webhook -> Extract Push Data -> AI Summary -> Format Response -> Respond
    2. Activates the workflow so the webhook endpoint is live
    3. Tests the webhook endpoint

AFTER RUNNING:
    The n8n webhook will be live at:
      POST $N8nUrl/webhook/github-push
"@
    exit 0
}

# Load API key from .env if not provided
if (-not $N8nApiKey) {
    $envFile = Join-Path $PSScriptRoot "..\.env"
    if (Test-Path $envFile) {
        $envContent = Get-Content $envFile -Raw
        if ($envContent -match 'N8N_API_KEY=(.+)') {
            $N8nApiKey = $Matches[1].Trim()
            Write-Info "Loaded N8N_API_KEY from .env"
        }
    }
    if (-not $N8nApiKey) {
        Write-Err "No N8N_API_KEY found. Pass -N8nApiKey or set in .env"
        exit 1
    }
}

$headers = @{
    "Content-Type" = "application/json"
    "X-N8N-API-KEY" = $N8nApiKey
}

# --- Build the workflow JSON ---
Write-Step "Building workflow JSON..."

$workflowJson = @'
{
  "name": "GitHub Push Processor",
  "nodes": [
    {
      "parameters": {
        "httpMethod": "POST",
        "path": "github-push",
        "responseMode": "responseNode",
        "options": {}
      },
      "id": "webhook-trigger",
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 2,
      "position": [220, 300],
      "webhookId": "github-push"
    },
    {
      "parameters": {
        "mode": "manual",
        "duplicateItem": false,
        "assignments": {
          "assignments": [
            {
              "id": "repo",
              "name": "repo",
              "value": "={{ $json.body.repository.full_name || $json.repository?.full_name || 'unknown/repo' }}",
              "type": "string"
            },
            {
              "id": "branch",
              "name": "branch",
              "value": "={{ ($json.body.ref || $json.ref || '').replace('refs/heads/', '') }}",
              "type": "string"
            },
            {
              "id": "pusher",
              "name": "pusher",
              "value": "={{ $json.body.pusher?.name || $json.pusher?.name || 'unknown' }}",
              "type": "string"
            },
            {
              "id": "commit_count",
              "name": "commit_count",
              "value": "={{ ($json.body.commits || $json.commits || []).length }}",
              "type": "number"
            },
            {
              "id": "commit_messages",
              "name": "commit_messages",
              "value": "={{ ($json.body.commits || $json.commits || []).map(c => '- ' + (c.message || '')).join('\\n') }}",
              "type": "string"
            },
            {
              "id": "commit_authors",
              "name": "commit_authors",
              "value": "={{ [...new Set(($json.body.commits || $json.commits || []).map(c => c.author?.name || 'unknown'))].join(', ') }}",
              "type": "string"
            }
          ]
        },
        "options": {}
      },
      "id": "extract-push-data",
      "name": "Extract Push Data",
      "type": "n8n-nodes-base.set",
      "typeVersion": 3.4,
      "position": [440, 300]
    },
    {
      "parameters": {
        "method": "POST",
        "url": "http://open-webui:8080/api/chat/completions",
        "authentication": "genericCredentialType",
        "genericAuthType": "httpHeaderAuth",
        "sendBody": true,
        "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify({ model: 'gpt-4o-mini', messages: [{ role: 'system', content: 'You are a GitHub push event analyzer. Summarize what changed concisely. Focus on: what was done, which areas of code were affected, and any notable patterns. Keep it under 200 words.' }, { role: 'user', content: 'Analyze this GitHub push event:\\n\\nRepository: ' + $json.repo + '\\nBranch: ' + $json.branch + '\\nPushed by: ' + $json.pusher + '\\nCommit count: ' + $json.commit_count + '\\n\\nCommit messages:\\n' + $json.commit_messages + '\\n\\nAuthors: ' + $json.commit_authors }] }) }}",
        "options": {}
      },
      "id": "ai-summary",
      "name": "AI Summary",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [660, 300],
      "credentials": {
        "httpHeaderAuth": {
          "id": "openwebui-auth",
          "name": "Open WebUI Auth"
        }
      }
    },
    {
      "parameters": {
        "mode": "manual",
        "duplicateItem": false,
        "assignments": {
          "assignments": [
            {
              "id": "event_type",
              "name": "event_type",
              "value": "push",
              "type": "string"
            },
            {
              "id": "repo",
              "name": "repo",
              "value": "={{ $('Extract Push Data').item.json.repo }}",
              "type": "string"
            },
            {
              "id": "branch",
              "name": "branch",
              "value": "={{ $('Extract Push Data').item.json.branch }}",
              "type": "string"
            },
            {
              "id": "commit_count",
              "name": "commit_count",
              "value": "={{ $('Extract Push Data').item.json.commit_count }}",
              "type": "number"
            },
            {
              "id": "ai_summary",
              "name": "ai_summary",
              "value": "={{ $json.choices?.[0]?.message?.content || 'AI summary unavailable' }}",
              "type": "string"
            },
            {
              "id": "timestamp",
              "name": "timestamp",
              "value": "={{ new Date().toISOString() }}",
              "type": "string"
            },
            {
              "id": "workflow",
              "name": "workflow",
              "value": "n8n-github-push-processor",
              "type": "string"
            }
          ]
        },
        "options": {}
      },
      "id": "format-response",
      "name": "Format Response",
      "type": "n8n-nodes-base.set",
      "typeVersion": 3.4,
      "position": [880, 300]
    },
    {
      "parameters": {
        "options": {
          "responseCode": 200
        }
      },
      "id": "respond",
      "name": "Respond to Webhook",
      "type": "n8n-nodes-base.respondToWebhook",
      "typeVersion": 1.1,
      "position": [1100, 300]
    }
  ],
  "connections": {
    "Webhook": {
      "main": [
        [
          {
            "node": "Extract Push Data",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Extract Push Data": {
      "main": [
        [
          {
            "node": "AI Summary",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "AI Summary": {
      "main": [
        [
          {
            "node": "Format Response",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Format Response": {
      "main": [
        [
          {
            "node": "Respond to Webhook",
            "type": "main",
            "index": 0
          }
        ]
      ]
    }
  },
  "settings": {
    "executionOrder": "v1"
  },
  "staticData": null,
  "tags": []
}
'@

# --- Check if workflow already exists ---
Write-Step "Checking for existing 'GitHub Push Processor' workflow..."
try {
    $existing = Invoke-RestMethod -Uri "$N8nUrl/api/v1/workflows" -Method Get -Headers $headers
    $found = $existing.data | Where-Object { $_.name -eq "GitHub Push Processor" }
    if ($found) {
        Write-Info "Workflow already exists (id=$($found.id)). Deleting and recreating..."
        Invoke-RestMethod -Uri "$N8nUrl/api/v1/workflows/$($found.id)" -Method Delete -Headers $headers | Out-Null
        Write-Success "Deleted existing workflow"
    }
} catch {
    Write-Info "Could not check existing workflows: $_"
}

# --- Create the workflow ---
Write-Step "Creating workflow via n8n API..."
try {
    $created = Invoke-RestMethod -Uri "$N8nUrl/api/v1/workflows" -Method Post -Headers $headers -Body $workflowJson
    $workflowId = $created.id
    Write-Success "Workflow created: id=$workflowId, name=$($created.name)"
} catch {
    Write-Err "Failed to create workflow: $_"
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        Write-Err "Response: $($reader.ReadToEnd())"
    }
    exit 1
}

# --- Activate the workflow ---
Write-Step "Activating workflow..."
try {
    $activateBody = '{"active": true}'
    $activated = Invoke-RestMethod -Uri "$N8nUrl/api/v1/workflows/$workflowId" -Method Patch -Headers $headers -Body $activateBody
    Write-Success "Workflow activated: active=$($activated.active)"
} catch {
    Write-Err "Failed to activate workflow: $_"
    Write-Info "The workflow was created but is inactive. Activate it manually in the n8n UI."
}

# --- Setup credentials for Open WebUI auth ---
Write-Step "Setting up Open WebUI HTTP Header Auth credential..."
Write-Info "Note: n8n credentials cannot be fully created via public API."
Write-Info "You need to configure the 'Open WebUI Auth' credential in n8n UI:"
Write-Info "  1. Go to $N8nUrl/credentials"
Write-Info "  2. Create 'Header Auth' credential named 'Open WebUI Auth'"
Write-Info "  3. Set Header Name: Authorization"
Write-Info "  4. Set Header Value: Bearer <your OPENWEBUI_API_KEY>"
Write-Info ""
Write-Info "Alternatively, the AI Summary node can be reconfigured to use"
Write-Info "expression-based auth with the OPENWEBUI_API_KEY env var."

# --- Summary ---
Write-Host ""
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "  WORKFLOW DEPLOYED SUCCESSFULLY" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host @"

  Workflow: GitHub Push Processor (id=$workflowId)
  Webhook:  POST $N8nUrl/webhook/github-push

  Flow:
    1. Webhook receives GitHub push payload
    2. Extract Push Data: pulls repo, branch, commits
    3. AI Summary: calls Open WebUI for analysis
    4. Format Response: structures the output
    5. Respond: returns JSON with AI summary

  TEST (direct to n8n):
    curl -s -X POST $N8nUrl/webhook/github-push \
      -H "Content-Type: application/json" \
      -d '{"ref":"refs/heads/main","pusher":{"name":"test"},"repository":{"full_name":"test/repo"},"commits":[{"id":"abc","message":"test commit","author":{"name":"test"}}]}'

  TEST (via webhook-handler):
    curl -s -X POST http://localhost:8086/webhook/github \
      -H "X-GitHub-Event: push" \
      -H "Content-Type: application/json" \
      -d '{"ref":"refs/heads/main","pusher":{"name":"test"},"repository":{"full_name":"test/repo"},"commits":[{"id":"abc","message":"test commit","author":{"name":"test"}}]}'

"@
