from urllib.parse import quote
from typing import Optional


def include_user_info_headers(headers, user, groups: Optional[list] = None):
    """
    Add user information headers to the request.

    Args:
        headers: Existing headers dict
        user: User model with name, id, email, role
        groups: Optional list of group names (for MCP server filtering)

    Returns:
        Updated headers dict with X-OpenWebUI-User-* headers
    """
    result = {
        **headers,
        "X-OpenWebUI-User-Name": quote(user.name, safe=" "),
        "X-OpenWebUI-User-Id": user.id,
        "X-OpenWebUI-User-Email": user.email,
        "X-OpenWebUI-User-Role": user.role,
    }

    # Add groups header if groups provided
    if groups:
        group_names = [g.name if hasattr(g, 'name') else str(g) for g in groups]
        result["X-OpenWebUI-User-Groups"] = ",".join(group_names)

    return result
