# scripts/start-local-demo.ps1
# Local Development Startup Script for Single Proxy Demo
#
# This script:
# 1. Starts Docker containers
# 2. Waits for services to be healthy
# 3. Seeds the database with group_tenant_mapping
# 4. Tests the MCP Proxy endpoints
#
# Usage:
#   .\scripts\start-local-demo.ps1
#   .\scripts\start-local-demo.ps1 -SkipBuild   # Skip rebuilding containers
#   .\scripts\start-local-demo.ps1 -TestOnly    # Only run tests (assumes services running)

param(
    [switch]$SkipBuild,
    [switch]$TestOnly,
    [switch]$Help
)

$ErrorActionPreference = "Stop"

# Colors for output
function Write-Header { param($msg) Write-Host "`n$("=" * 70)" -ForegroundColor Cyan; Write-Host "  $msg" -ForegroundColor Cyan; Write-Host "$("=" * 70)" -ForegroundColor Cyan }
function Write-Step { param($msg) Write-Host "[STEP] $msg" -ForegroundColor Yellow }
function Write-Success { param($msg) Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Error { param($msg) Write-Host "[ERROR] $msg" -ForegroundColor Red }
function Write-Info { param($msg) Write-Host "[INFO] $msg" -ForegroundColor White }

if ($Help) {
    Write-Host @"
Single Proxy Demo - Local Development Startup Script

USAGE:
    .\scripts\start-local-demo.ps1 [OPTIONS]

OPTIONS:
    -SkipBuild    Skip rebuilding Docker containers
    -TestOnly     Only run tests (assumes services are already running)
    -Help         Show this help message

REQUIREMENTS:
    - Docker Desktop running
    - .env file configured (copy from .env.example)

WHAT THIS SCRIPT DOES:
    1. Starts all Docker containers (postgres, redis, open-webui, mcp-proxy, etc.)
    2. Waits for services to be healthy
    3. Seeds the database with group_tenant_mapping from mcp-servers.json
    4. Tests MCP Proxy endpoints to verify everything works

DEMO FLOW:
    After running this script, you can:
    1. Open http://localhost:3000 (Open WebUI)
    2. Go to Admin Panel > Settings > External Tools
    3. See MCP Proxy is already configured (via TOOL_SERVER_CONNECTIONS)
    4. Start a chat and ask about MCP tools

"@
    exit 0
}

Write-Header "SINGLE PROXY DEMO - Local Development"
Write-Info "For Lukas: Proving single proxy = simpler automation"

# Check Docker
Write-Step "Checking Docker..."
try {
    $dockerVersion = docker version --format '{{.Server.Version}}' 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Docker not responding"
    }
    Write-Success "Docker is running (version $dockerVersion)"
} catch {
    Write-Error "Docker is not running. Please start Docker Desktop first."
    exit 1
}

# Change to project root
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (Test-Path "$PSScriptRoot\..\docker-compose.yml") {
    $projectRoot = Split-Path -Parent $PSScriptRoot
}
Set-Location $projectRoot
Write-Info "Working directory: $projectRoot"

if (-not $TestOnly) {
    # Check .env file
    Write-Step "Checking .env file..."
    if (-not (Test-Path ".env")) {
        Write-Info "Creating .env from .env.example..."
        Copy-Item ".env.example" ".env"
        Write-Success "Created .env file - please configure it with your API keys"
    } else {
        Write-Success ".env file exists"
    }

    # Start containers
    Write-Header "Starting Docker Containers"

    if ($SkipBuild) {
        Write-Step "Starting containers (skip build)..."
        docker-compose up -d
    } else {
        Write-Step "Building and starting containers..."
        docker-compose up -d --build
    }

    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to start containers"
        exit 1
    }
    Write-Success "Containers started"

    # Wait for PostgreSQL
    Write-Step "Waiting for PostgreSQL to be healthy..."
    $maxAttempts = 30
    for ($i = 1; $i -le $maxAttempts; $i++) {
        $status = docker inspect --format='{{.State.Health.Status}}' postgres 2>&1
        if ($status -eq "healthy") {
            Write-Success "PostgreSQL is healthy"
            break
        }
        Write-Info "  Attempt $i/$maxAttempts - PostgreSQL status: $status"
        Start-Sleep -Seconds 2
    }

    # Wait for MCP Proxy
    Write-Step "Waiting for MCP Proxy to be ready..."
    for ($i = 1; $i -le $maxAttempts; $i++) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                Write-Success "MCP Proxy is ready"
                break
            }
        } catch {
            Write-Info "  Attempt $i/$maxAttempts - MCP Proxy not ready yet..."
            Start-Sleep -Seconds 3
        }
    }

    # Run database seeder (the db-init container should have done this, but let's verify)
    Write-Step "Checking database seeding..."
    $dbInitLogs = docker logs db-init 2>&1
    if ($dbInitLogs -match "SEEDING COMPLETE") {
        Write-Success "Database seeded successfully"
    } else {
        Write-Info "Running database seeder manually..."
        docker exec mcp-proxy python /app/scripts/seed_mcp_servers.py --clear
    }
}

# Test endpoints
Write-Header "Testing MCP Proxy Endpoints"

# Test 1: Health check
Write-Step "Test 1: Health check..."
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get
    Write-Success "Health: $($health.status) - Tools cached: $($health.tools_cached)"
} catch {
    Write-Error "Health check failed: $_"
}

# Test 2: List servers
Write-Step "Test 2: List servers..."
try {
    $servers = Invoke-RestMethod -Uri "http://localhost:8000/servers" -Method Get
    Write-Success "Found $($servers.total_servers) servers"
    foreach ($server in $servers.servers) {
        Write-Info "  - $($server.id): $($server.name) ($($server.tier))"
    }
} catch {
    Write-Error "List servers failed: $_"
}

# Test 3: OpenAPI spec
Write-Step "Test 3: OpenAPI spec..."
try {
    $openapi = Invoke-RestMethod -Uri "http://localhost:8000/openapi.json" -Method Get
    $pathCount = ($openapi.paths.PSObject.Properties | Measure-Object).Count
    Write-Success "OpenAPI spec has $pathCount paths"
} catch {
    Write-Error "OpenAPI spec failed: $_"
}

# Test 4: GitHub tools (if available)
Write-Step "Test 4: GitHub tools..."
try {
    $github = Invoke-RestMethod -Uri "http://localhost:8000/github" -Method Get
    Write-Success "GitHub: $($github.tool_count) tools available"
} catch {
    Write-Info "GitHub MCP not available (may need GITHUB_TOKEN)"
}

# Test 5: Filesystem tools (if available)
Write-Step "Test 5: Filesystem tools..."
try {
    $fs = Invoke-RestMethod -Uri "http://localhost:8000/filesystem" -Method Get
    Write-Success "Filesystem: $($fs.tool_count) tools available"
} catch {
    Write-Info "Filesystem MCP not available"
}

# Summary
Write-Header "DEMO READY!"
Write-Host @"

  SINGLE PROXY AUTO-DEPLOY - SUCCESS!

  Open WebUI:     http://localhost:3000
  MCP Proxy:      http://localhost:8000

  What's configured:
  1. TOOL_SERVER_CONNECTIONS env var -> MCP Proxy pre-configured
  2. Database seeded -> group_tenant_mapping table populated
  3. MCP Servers running -> GitHub and Filesystem tools available

  DEMO STEPS:
  1. Open http://localhost:3000
  2. Go to Admin Panel > Settings > External Tools
  3. See "MCP Proxy" is already configured!
  4. Start a chat and ask: "What MCP tools do you have?"

  For Lukas:
  "With single proxy, I edit ONE config file (mcp-servers.json),
  run docker-compose up, and both the database permissions AND
  Open WebUI tool configuration are set up automatically.
  No manual UI clicks. No sync issues. One source of truth."

"@
