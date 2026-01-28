#!/bin/bash
# =============================================================================
# MCP Proxy Schema Health Check
# =============================================================================
# Verifies that the mcp_proxy schema exists and has the expected tables/data.
# Run before and after Open WebUI updates to confirm our tables are untouched.
#
# Usage:
#   bash scripts/check-mcp-schema.sh                    # Default: connects via docker exec
#   PGHOST=localhost PGUSER=openwebui bash scripts/check-mcp-schema.sh  # Direct connection
# =============================================================================

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASS=0
FAIL=0

check() {
    local description="$1"
    local query="$2"
    local expected="$3"

    result=$(docker exec postgres psql -U openwebui -d openwebui -t -A -c "$query" 2>/dev/null || echo "ERROR")

    if [ "$expected" = "notempty" ]; then
        if [ -n "$result" ] && [ "$result" != "0" ] && [ "$result" != "ERROR" ]; then
            echo -e "  ${GREEN}PASS${NC} $description (result: $result)"
            PASS=$((PASS + 1))
        else
            echo -e "  ${RED}FAIL${NC} $description (result: $result)"
            FAIL=$((FAIL + 1))
        fi
    elif [ "$result" = "$expected" ]; then
        echo -e "  ${GREEN}PASS${NC} $description"
        PASS=$((PASS + 1))
    else
        echo -e "  ${RED}FAIL${NC} $description (expected: $expected, got: $result)"
        FAIL=$((FAIL + 1))
    fi
}

echo ""
echo "========================================"
echo "  MCP Proxy Schema Health Check"
echo "========================================"
echo ""

echo "1. Schema Exists"
check "mcp_proxy schema exists" \
    "SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'mcp_proxy'" \
    "mcp_proxy"

echo ""
echo "2. Tables Exist"
check "user_group_membership table exists" \
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'mcp_proxy' AND table_name = 'user_group_membership'" \
    "1"
check "group_tenant_mapping table exists" \
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'mcp_proxy' AND table_name = 'group_tenant_mapping'" \
    "1"
check "user_admin_status table exists" \
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'mcp_proxy' AND table_name = 'user_admin_status'" \
    "1"

echo ""
echo "3. Tables Have Data"
check "user_group_membership has rows" \
    "SELECT COUNT(*) FROM mcp_proxy.user_group_membership" \
    "notempty"
check "group_tenant_mapping has rows" \
    "SELECT COUNT(*) FROM mcp_proxy.group_tenant_mapping" \
    "notempty"

echo ""
echo "4. Cross-Schema Access"
check "Can read public.user table" \
    "SELECT COUNT(*) FROM public.\"user\"" \
    "notempty"

echo ""
echo "5. Old Public Tables Removed"
old_tables=$(docker exec postgres psql -U openwebui -d openwebui -t -A -c \
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ('user_group_membership', 'group_tenant_mapping', 'user_admin_status')" 2>/dev/null || echo "ERROR")

if [ "$old_tables" = "0" ]; then
    echo -e "  ${GREEN}PASS${NC} No old tables in public schema"
    PASS=$((PASS + 1))
elif [ "$old_tables" = "ERROR" ]; then
    echo -e "  ${YELLOW}SKIP${NC} Could not check (connection error)"
else
    echo -e "  ${YELLOW}WARN${NC} $old_tables old tables still in public schema (run migrate-to-mcp-schema.sql)"
fi

echo ""
echo "========================================"
echo -e "  Results: ${GREEN}${PASS} passed${NC}, ${RED}${FAIL} failed${NC}"
echo "========================================"

if [ $FAIL -gt 0 ]; then
    echo -e "  ${RED}Schema check FAILED. Review the issues above.${NC}"
    exit 1
else
    echo -e "  ${GREEN}All checks passed. Schema is healthy.${NC}"
    exit 0
fi
