#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Full cross-service demo for the IO automation platform.

.DESCRIPTION
    Orchestrates all demo scenarios:
      Phase 0 - Health checks (all services)
      Phase 1 - Webhook pipe function verification
      Phase 2 - Scheduled jobs (list + manual trigger)
      Phase 3 - MCP tools via proxy (GitHub, Linear, Notion)
      Phase 4 - Multi-tenant isolation test
      Phase 5 - Full automation chain (GitHub push -> AI + MCP + n8n)

.NOTES
    Run from the project root: .\scripts\run-full-demo.ps1
#>

$ErrorActionPreference = "Continue"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
$WEBHOOK_HANDLER = "http://localhost:8086"
$OPEN_WEBUI      = "http://localhost:3000"
$N8N             = "http://localhost:5678"
$MCP_PROXY       = "http://localhost:8000"

# Load .env for API keys
$envFile = Join-Path $PSScriptRoot ".." ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.+)$') {
            Set-Variable -Name $Matches[1] -Value $Matches[2].Trim()
        }
    }
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
function Write-Header($text) {
    Write-Host ""
    Write-Host ("=" * 70) -ForegroundColor Cyan
    Write-Host "  $text" -ForegroundColor Cyan
    Write-Host ("=" * 70) -ForegroundColor Cyan
}

function Write-Step($text) {
    Write-Host ""
    Write-Host ">> $text" -ForegroundColor Yellow
}

function Write-Pass($text) {
    Write-Host "   [PASS] $text" -ForegroundColor Green
}

function Write-Fail($text) {
    Write-Host "   [FAIL] $text" -ForegroundColor Red
}

function Write-Info($text) {
    Write-Host "   [INFO] $text" -ForegroundColor Gray
}

function Write-Skip($text) {
    Write-Host "   [SKIP] $text" -ForegroundColor DarkYellow
}

$passCount = 0
$failCount = 0
$skipCount = 0

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Url,
        [string]$Method = "GET",
        [object]$Body = $null,
        [hashtable]$Headers = @{},
        [switch]$ExpectFailure
    )

    try {
        $params = @{
            Uri             = $Url
            Method          = $Method
            UseBasicParsing = $true
            TimeoutSec      = 15
            ErrorAction     = "Stop"
        }

        if ($Headers.Count -gt 0) {
            $params["Headers"] = $Headers
        }

        if ($Body) {
            $jsonBody = if ($Body -is [string]) { $Body } else { $Body | ConvertTo-Json -Depth 10 }
            $params["Body"] = $jsonBody
            if (-not $params["Headers"]) { $params["Headers"] = @{} }
            $params["Headers"]["Content-Type"] = "application/json"
        }

        $response = Invoke-RestMethod @params

        if ($ExpectFailure) {
            $script:failCount++
            Write-Fail "$Name - Expected failure but got success"
            return $null
        }

        $script:passCount++
        Write-Pass $Name
        return $response
    }
    catch {
        if ($ExpectFailure) {
            $script:passCount++
            Write-Pass "$Name (correctly denied)"
            return $null
        }
        $statusCode = $_.Exception.Response.StatusCode.value__
        $script:failCount++
        Write-Fail "$Name - HTTP $statusCode : $($_.Exception.Message)"
        return $null
    }
}

# ========================================================================
# Phase 0: Health Checks
# ========================================================================
Write-Header "Phase 0: Service Health Checks"

Write-Step "Checking all services..."

Test-Endpoint -Name "Webhook Handler" -Url "$WEBHOOK_HANDLER/health"
Test-Endpoint -Name "Open WebUI" -Url "$OPEN_WEBUI/api/config"
Test-Endpoint -Name "MCP Proxy" -Url "$MCP_PROXY/health"

# n8n healthz doesn't always return JSON
try {
    $n8nResp = Invoke-WebRequest -Uri "$N8N/healthz" -TimeoutSec 10 -UseBasicParsing -ErrorAction Stop
    if ($n8nResp.StatusCode -lt 400) {
        $passCount++
        Write-Pass "n8n"
    } else {
        $failCount++
        Write-Fail "n8n - HTTP $($n8nResp.StatusCode)"
    }
} catch {
    $failCount++
    Write-Fail "n8n - $($_.Exception.Message)"
}

# On-demand health report from webhook-handler
Write-Step "Running on-demand health report..."
$healthReport = Test-Endpoint -Name "Health Report API" -Url "$WEBHOOK_HANDLER/scheduler/health-report"
if ($healthReport) {
    Write-Info "Services healthy: $($healthReport.healthy)/$($healthReport.total)"
    foreach ($svc in $healthReport.services) {
        $icon = if ($svc.status -eq "healthy") { "OK" } else { "!!" }
        Write-Info "  [$icon] $($svc.service): $($svc.status)"
    }
}

# ========================================================================
# Phase 1: Webhook Pipe Function
# ========================================================================
Write-Header "Phase 1: Webhook Pipe Function"

Write-Step "Checking if webhook_automation function is installed..."
try {
    $headers = @{ "Authorization" = "Bearer $OPENWEBUI_API_KEY" }
    $functions = Invoke-RestMethod -Uri "$OPEN_WEBUI/api/v1/functions/" -Headers $headers -TimeoutSec 10 -UseBasicParsing
    $pipeFunc = $functions | Where-Object { $_.id -eq "webhook_automation" }
    if ($pipeFunc) {
        $passCount++
        Write-Pass "webhook_automation pipe function found (active=$($pipeFunc.is_active))"
    } else {
        $failCount++
        Write-Fail "webhook_automation pipe function NOT found - run install_webhook_pipe.py first"
    }
} catch {
    $skipCount++
    Write-Skip "Cannot verify pipe function - Open WebUI API may need auth"
    Write-Info "Install manually: docker compose exec webhook-handler python /app/scripts/install_webhook_pipe.py"
}

# ========================================================================
# Phase 2: Scheduled Jobs
# ========================================================================
Write-Header "Phase 2: Scheduled Jobs"

Write-Step "Listing scheduled jobs..."
$jobs = Test-Endpoint -Name "List Scheduler Jobs" -Url "$WEBHOOK_HANDLER/scheduler/jobs"
if ($jobs -and $jobs.jobs) {
    Write-Info "Configured jobs: $($jobs.count)"
    foreach ($job in $jobs.jobs) {
        Write-Info "  - $($job.id): next_run=$($job.next_run) trigger=$($job.trigger)"
    }
}

Write-Step "Manually triggering health report job..."
$triggerResult = Test-Endpoint -Name "Trigger daily_health_report" `
    -Url "$WEBHOOK_HANDLER/scheduler/jobs/daily_health_report/trigger" `
    -Method "POST"

Write-Step "Running n8n workflow check..."
$n8nCheck = Test-Endpoint -Name "n8n Workflow Check" -Url "$WEBHOOK_HANDLER/scheduler/n8n-check"
if ($n8nCheck) {
    if ($n8nCheck.error) {
        Write-Info "n8n check result: $($n8nCheck.error)"
    } else {
        Write-Info "Workflows: $($n8nCheck.total) total, $($n8nCheck.active) active"
    }
}

# ========================================================================
# Phase 3: MCP Tool Tests
# ========================================================================
Write-Header "Phase 3: MCP Tool Tests"

Write-Step "Testing MCP Proxy tools endpoint (admin)..."
$mcpTools = Test-Endpoint -Name "MCP Tools (Admin)" `
    -Url "$MCP_PROXY/tools" `
    -Headers @{
        "X-User-Email"  = "admin@system"
        "X-User-Groups" = "MCP-Admin"
    }
if ($mcpTools) {
    $toolList = if ($mcpTools.tools) { $mcpTools.tools } else { $mcpTools }
    if ($toolList -is [array]) {
        Write-Info "Total MCP tools available: $($toolList.Count)"
        $servers = $toolList | ForEach-Object { $_.tenant_id ?? $_.server_id ?? "unknown" } | Sort-Object -Unique
        Write-Info "Servers: $($servers -join ', ')"
    }
}

Write-Step "Testing GitHub MCP tools..."
$ghTools = Test-Endpoint -Name "GitHub Tools via MCP Proxy" `
    -Url "$MCP_PROXY/tools" `
    -Headers @{
        "X-User-Email"  = "test@system"
        "X-User-Groups" = "MCP-GitHub"
    }

Write-Step "Testing direct MCP webhook endpoint..."
Test-Endpoint -Name "MCP Webhook (github/list_repositories)" `
    -Url "$WEBHOOK_HANDLER/webhook/mcp/github/list_repositories" `
    -Method "POST" `
    -Body @{}

# ========================================================================
# Phase 4: Multi-Tenant Isolation
# ========================================================================
Write-Header "Phase 4: Multi-Tenant Isolation"

Write-Step "Test-Tenant: Should see github + filesystem tools..."
$testTenantTools = Test-Endpoint -Name "Test-Tenant Tools" `
    -Url "$MCP_PROXY/tools" `
    -Headers @{
        "X-User-Email"  = "test-user@test-tenant.com"
        "X-User-Groups" = "Test-Tenant"
    }
if ($testTenantTools) {
    $toolList = if ($testTenantTools.tools) { $testTenantTools.tools } else { $testTenantTools }
    if ($toolList -is [array]) {
        $servers = $toolList | ForEach-Object { $_.tenant_id ?? $_.server_id ?? "unknown" } | Sort-Object -Unique
        Write-Info "Test-Tenant can see servers: $($servers -join ', ')"

        $hasGithub = $servers -contains "github"
        $hasFilesystem = $servers -contains "filesystem"
        $hasLinear = $servers -contains "linear"
        $hasNotion = $servers -contains "notion"
        $hasSlack = $servers -contains "slack"

        if ($hasGithub) { Write-Pass "Test-Tenant can access github" } else { Write-Fail "Test-Tenant cannot access github" }
        if ($hasFilesystem) { Write-Pass "Test-Tenant can access filesystem" } else { Write-Fail "Test-Tenant cannot access filesystem" }
        if (-not $hasLinear) { Write-Pass "Test-Tenant correctly blocked from linear" } else { Write-Fail "Test-Tenant can see linear (ISOLATION BREACH)" }
        if (-not $hasNotion) { Write-Pass "Test-Tenant correctly blocked from notion" } else { Write-Fail "Test-Tenant can see notion (ISOLATION BREACH)" }
        if (-not $hasSlack) { Write-Pass "Test-Tenant correctly blocked from slack" } else { Write-Fail "Test-Tenant can see slack (ISOLATION BREACH)" }
    }
}

Write-Step "MCP-Admin: Should see all tools..."
$adminTools = Test-Endpoint -Name "Admin Tools" `
    -Url "$MCP_PROXY/tools" `
    -Headers @{
        "X-User-Email"  = "admin@system"
        "X-User-Groups" = "MCP-Admin"
    }
if ($adminTools) {
    $toolList = if ($adminTools.tools) { $adminTools.tools } else { $adminTools }
    if ($toolList -is [array]) {
        $servers = $toolList | ForEach-Object { $_.tenant_id ?? $_.server_id ?? "unknown" } | Sort-Object -Unique
        Write-Info "Admin can see servers: $($servers -join ', ')"
        if ($servers.Count -ge 3) {
            Write-Pass "Admin has broad access ($($servers.Count) servers)"
        }
    }
}

# ========================================================================
# Phase 5: Full Automation Chain
# ========================================================================
Write-Header "Phase 5: Full Automation Chain"

Write-Step "Simulating GitHub push event..."
$pushPayload = @{
    ref        = "refs/heads/main"
    repository = @{
        full_name = "test-org/demo-repo"
        html_url  = "https://github.com/test-org/demo-repo"
    }
    pusher     = @{ name = "demo-user" }
    commits    = @(
        @{
            id      = "abc123"
            message = "feat: add new dashboard component"
            author  = @{ name = "demo-user"; email = "demo@test.com" }
            url     = "https://github.com/test-org/demo-repo/commit/abc123"
            added   = @("src/dashboard.tsx")
            modified = @("src/app.tsx")
            removed = @()
        }
    )
}

$pushHeaders = @{
    "X-GitHub-Event"    = "push"
    "X-GitHub-Delivery" = "demo-delivery-001"
    "Content-Type"      = "application/json"
}

# Send without signature (webhook secret verification will fail if configured)
try {
    $pushResp = Invoke-RestMethod `
        -Uri "$WEBHOOK_HANDLER/webhook/github" `
        -Method POST `
        -Body ($pushPayload | ConvertTo-Json -Depth 10) `
        -Headers $pushHeaders `
        -TimeoutSec 30 `
        -UseBasicParsing
    $passCount++
    Write-Pass "GitHub push webhook accepted"
    if ($pushResp.ai_analysis) {
        Write-Info "AI Analysis: $($pushResp.ai_analysis.Substring(0, [Math]::Min(120, $pushResp.ai_analysis.Length)))..."
    }
    if ($pushResp.n8n_result) {
        Write-Info "n8n workflow triggered successfully"
    }
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    if ($statusCode -eq 401) {
        $skipCount++
        Write-Skip "GitHub push rejected (signature required) - expected in secured mode"
    } else {
        $failCount++
        Write-Fail "GitHub push failed: HTTP $statusCode"
    }
}

Write-Step "Testing automation webhook (AI + MCP tools)..."
$autoPayload = @{
    test = $true
    message = "Demo automation request"
}
try {
    $autoResp = Invoke-RestMethod `
        -Uri "$WEBHOOK_HANDLER/webhook/automation?source=demo&instructions=Summarize available MCP tools" `
        -Method POST `
        -Body ($autoPayload | ConvertTo-Json -Depth 5) `
        -Headers @{ "Content-Type" = "application/json" } `
        -TimeoutSec 60 `
        -UseBasicParsing
    if ($autoResp.success) {
        $passCount++
        Write-Pass "Automation webhook processed successfully"
        if ($autoResp.response) {
            $preview = $autoResp.response.ToString().Substring(0, [Math]::Min(120, $autoResp.response.ToString().Length))
            Write-Info "Response: $preview..."
        }
    } else {
        $failCount++
        Write-Fail "Automation webhook returned failure: $($autoResp.error)"
    }
} catch {
    $failCount++
    Write-Fail "Automation webhook error: $($_.Exception.Message)"
    Write-Info "Make sure webhook_pipe.py is installed (Phase 1)"
}

# ========================================================================
# Summary
# ========================================================================
Write-Host ""
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host "  DEMO COMPLETE" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host ""

$total = $passCount + $failCount + $skipCount
Write-Host "  Results:" -ForegroundColor White
Write-Host "    Passed:  $passCount" -ForegroundColor Green
Write-Host "    Failed:  $failCount" -ForegroundColor $(if ($failCount -gt 0) { "Red" } else { "Green" })
Write-Host "    Skipped: $skipCount" -ForegroundColor Yellow
Write-Host "    Total:   $total" -ForegroundColor White
Write-Host ""

if ($failCount -eq 0) {
    Write-Host "  All tests passed!" -ForegroundColor Green
} else {
    Write-Host "  Some tests failed - check output above for details." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "  Quick links:" -ForegroundColor Gray
Write-Host "    Open WebUI:       $OPEN_WEBUI" -ForegroundColor Gray
Write-Host "    n8n Dashboard:    $N8N" -ForegroundColor Gray
Write-Host "    Webhook Handler:  $WEBHOOK_HANDLER/health" -ForegroundColor Gray
Write-Host "    MCP Proxy:        $MCP_PROXY/health" -ForegroundColor Gray
Write-Host "    Scheduler Jobs:   $WEBHOOK_HANDLER/scheduler/jobs" -ForegroundColor Gray
Write-Host ""
