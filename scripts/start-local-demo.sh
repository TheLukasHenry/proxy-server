#!/bin/bash
# scripts/start-local-demo.sh
# Local Development Startup Script for Single Proxy Demo
#
# This script:
# 1. Starts Docker containers
# 2. Waits for services to be healthy
# 3. Seeds the database with group_tenant_mapping
# 4. Tests the MCP Proxy endpoints
#
# Usage:
#   ./scripts/start-local-demo.sh
#   ./scripts/start-local-demo.sh --skip-build   # Skip rebuilding containers
#   ./scripts/start-local-demo.sh --test-only    # Only run tests

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

header() { echo -e "\n${CYAN}======================================================================${NC}"; echo -e "${CYAN}  $1${NC}"; echo -e "${CYAN}======================================================================${NC}"; }
step() { echo -e "${YELLOW}[STEP]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }
info() { echo -e "[INFO] $1"; }

# Base URLs — override for production
BASE_URL="${BASE_URL:-http://localhost}"
MCP_PROXY_URL="${MCP_PROXY_URL:-${BASE_URL}:8000}"
OPEN_WEBUI_URL="${OPEN_WEBUI_URL:-${BASE_URL}:3000}"

SKIP_BUILD=false
TEST_ONLY=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-build) SKIP_BUILD=true; shift ;;
        --test-only) TEST_ONLY=true; shift ;;
        --help|-h)
            cat << EOF
Single Proxy Demo - Local Development Startup Script

USAGE:
    ./scripts/start-local-demo.sh [OPTIONS]

OPTIONS:
    --skip-build    Skip rebuilding Docker containers
    --test-only     Only run tests (assumes services are already running)
    --help, -h      Show this help message

REQUIREMENTS:
    - Docker running
    - .env file configured (copy from .env.example)

WHAT THIS SCRIPT DOES:
    1. Starts all Docker containers
    2. Waits for services to be healthy
    3. Seeds the database with group_tenant_mapping
    4. Tests MCP Proxy endpoints

EOF
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

header "SINGLE PROXY DEMO - Local Development"
info "For Lukas: Proving single proxy = simpler automation"

# Check Docker
step "Checking Docker..."
if ! docker version > /dev/null 2>&1; then
    error "Docker is not running. Please start Docker first."
    exit 1
fi
success "Docker is running"

# Change to project root
cd "$(dirname "$0")/.."
info "Working directory: $(pwd)"

if [ "$TEST_ONLY" = false ]; then
    # Check .env file
    step "Checking .env file..."
    if [ ! -f ".env" ]; then
        info "Creating .env from .env.example..."
        cp .env.example .env
        success "Created .env file - please configure it with your API keys"
    else
        success ".env file exists"
    fi

    # Start containers
    header "Starting Docker Containers"

    if [ "$SKIP_BUILD" = true ]; then
        step "Starting containers (skip build)..."
        docker-compose up -d
    else
        step "Building and starting containers..."
        docker-compose up -d --build
    fi
    success "Containers started"

    # Wait for PostgreSQL
    step "Waiting for PostgreSQL to be healthy..."
    max_attempts=30
    for i in $(seq 1 $max_attempts); do
        status=$(docker inspect --format='{{.State.Health.Status}}' postgres 2>/dev/null || echo "not running")
        if [ "$status" = "healthy" ]; then
            success "PostgreSQL is healthy"
            break
        fi
        info "  Attempt $i/$max_attempts - PostgreSQL status: $status"
        sleep 2
    done

    # Wait for MCP Proxy
    step "Waiting for MCP Proxy to be ready..."
    for i in $(seq 1 $max_attempts); do
        if curl -s $MCP_PROXY_URL/health > /dev/null 2>&1; then
            success "MCP Proxy is ready"
            break
        fi
        info "  Attempt $i/$max_attempts - MCP Proxy not ready yet..."
        sleep 3
    done

    # Check database seeding
    step "Checking database seeding..."
    if docker logs db-init 2>&1 | grep -q "SEEDING COMPLETE"; then
        success "Database seeded successfully"
    else
        info "Running database seeder manually..."
        docker exec mcp-proxy python /app/scripts/seed_mcp_servers.py --clear
    fi
fi

# Test endpoints
header "Testing MCP Proxy Endpoints"

# Test 1: Health check
step "Test 1: Health check..."
health=$(curl -s $MCP_PROXY_URL/health)
if echo "$health" | grep -q "healthy"; then
    success "Health check passed"
    echo "  $health"
else
    error "Health check failed"
fi

# Test 2: List servers
step "Test 2: List servers..."
servers=$(curl -s $MCP_PROXY_URL/servers)
total=$(echo "$servers" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total_servers', 0))" 2>/dev/null || echo "0")
success "Found $total servers"

# Test 3: OpenAPI spec
step "Test 3: OpenAPI spec..."
openapi=$(curl -s $MCP_PROXY_URL/openapi.json)
if echo "$openapi" | grep -q "paths"; then
    success "OpenAPI spec available"
else
    error "OpenAPI spec not available"
fi

# Test 4: GitHub tools
step "Test 4: GitHub tools..."
github=$(curl -s $MCP_PROXY_URL/github 2>/dev/null)
if echo "$github" | grep -q "tool_count"; then
    tools=$(echo "$github" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_count', 0))" 2>/dev/null || echo "0")
    success "GitHub: $tools tools available"
else
    info "GitHub MCP not available (may need GITHUB_TOKEN)"
fi

# Test 5: Filesystem tools
step "Test 5: Filesystem tools..."
fs=$(curl -s $MCP_PROXY_URL/filesystem 2>/dev/null)
if echo "$fs" | grep -q "tool_count"; then
    tools=$(echo "$fs" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_count', 0))" 2>/dev/null || echo "0")
    success "Filesystem: $tools tools available"
else
    info "Filesystem MCP not available"
fi

# Summary
header "DEMO READY!"
cat << EOF

  SINGLE PROXY AUTO-DEPLOY - SUCCESS!

  Open WebUI:     $OPEN_WEBUI_URL
  MCP Proxy:      $MCP_PROXY_URL

  What's configured:
  1. TOOL_SERVER_CONNECTIONS env var -> MCP Proxy pre-configured
  2. Database seeded -> group_tenant_mapping table populated
  3. MCP Servers running -> GitHub and Filesystem tools available

  DEMO STEPS:
  1. Open $OPEN_WEBUI_URL
  2. Go to Admin Panel > Settings > External Tools
  3. See "MCP Proxy" is already configured!
  4. Start a chat and ask: "What MCP tools do you have?"

  For Lukas:
  "With single proxy, I edit ONE config file (mcp-servers.json),
  run docker-compose up, and both the database permissions AND
  Open WebUI tool configuration are set up automatically.
  No manual UI clicks. No sync issues. One source of truth."

EOF
