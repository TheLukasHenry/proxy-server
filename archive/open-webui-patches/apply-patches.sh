#!/bin/bash
# Apply MCP group header forwarding patches to Open WebUI
# This script runs at container startup before the main app

set -e

echo "[PATCH] Applying MCP group header forwarding patches..."

# Patch 1: Replace headers.py with our version that supports groups
echo "[PATCH] Updating headers.py..."
cp /app/patches/headers.py /app/backend/open_webui/utils/headers.py

# Patch 2: Add imports to middleware.py if not already present
MIDDLEWARE="/app/backend/open_webui/utils/middleware.py"

# Check if Groups import exists
if ! grep -q "from open_webui.models.groups import Groups" "$MIDDLEWARE"; then
    echo "[PATCH] Adding Groups import to middleware.py..."
    sed -i '/from open_webui.models.users import UserModel/a from open_webui.models.groups import Groups' "$MIDDLEWARE"
fi

# Check if ENABLE_FORWARD_USER_INFO_HEADERS import exists
if ! grep -q "ENABLE_FORWARD_USER_INFO_HEADERS" "$MIDDLEWARE"; then
    echo "[PATCH] Adding ENABLE_FORWARD_USER_INFO_HEADERS import to middleware.py..."
    sed -i '/from open_webui.env import/a\    ENABLE_FORWARD_USER_INFO_HEADERS,' "$MIDDLEWARE"
fi

# Check if include_user_info_headers import exists
if ! grep -q "from open_webui.utils.headers import include_user_info_headers" "$MIDDLEWARE"; then
    echo "[PATCH] Adding include_user_info_headers import to middleware.py..."
    sed -i '/from open_webui.utils.misc import is_string_allowed/a from open_webui.utils.headers import include_user_info_headers' "$MIDDLEWARE"
fi

# Patch 3: Add group forwarding code before mcp_clients[server_id] = MCPClient()
# Check if our patch is already applied
if ! grep -q "Forward user info including groups to MCP server" "$MIDDLEWARE"; then
    echo "[PATCH] Adding group forwarding code to middleware.py..."

    # Create the patch code
    PATCH_CODE='                    # Forward user info including groups to MCP server\
                    if ENABLE_FORWARD_USER_INFO_HEADERS and user:\
                        try:\
                            user_groups = Groups.get_groups_by_member_id(user.id)\
                            headers = include_user_info_headers(headers, user, user_groups)\
                        except Exception as e:\
                            log.warning(f"Failed to get user groups for MCP headers: {e}")\
                            headers = include_user_info_headers(headers, user)\
\
                    mcp_clients[server_id] = MCPClient()'

    # Replace the mcp_clients line with our patched version
    sed -i "s/                    mcp_clients\[server_id\] = MCPClient()/$PATCH_CODE/" "$MIDDLEWARE"
fi

echo "[PATCH] All patches applied successfully!"
echo "[PATCH] Starting Open WebUI..."

# Execute the original entrypoint
exec "$@"
