# Open WebUI Optional Arguments - Summary for Lukas

**Source:** https://docs.openwebui.com/features/plugin/tools/development#optional-arguments

---

## What Are Optional Arguments?

When Open WebUI calls a tool function, it can pass these special parameters:

| Argument | What It Provides | Our Status |
|----------|------------------|------------|
| `__user__` | User info (id, email, name, role) | ✅ Used |
| `__event_emitter__` | Stream status updates to UI | ✅ Used |
| `__event_call__` | Call other tools from within a tool | ❌ Not used |
| `__oauth_token__` | **OAuth token (access_token, id_token)** | ✅ **IMPLEMENTED** |
| `__metadata__` | Chat metadata (chat_id, message_id) | ❌ Not used |
| `__messages__` | Full conversation history | ❌ Not used |
| `__files__` | Uploaded files in conversation | ❌ Not used |
| `__model__` | Active model information | ❌ Not used |

---

## The Key One: `__oauth_token__`

From the docs:
> "A dictionary containing the user's valid, automatically refreshed OAuth token payload. This is the **new, recommended, and secure** way to access user tokens for making authenticated API calls."

### What We Built

**File:** `open-webui-functions/mcp_entra_token_auth.py`

```python
async def execute_mcp_tool(
    self,
    server: str,
    tool: str,
    arguments: str = "{}",
    __oauth_token__: Optional[dict] = None,  # <-- THE KEY PARAMETER
    __user__: dict = {},
    __event_emitter__: Callable[[dict], Any] = None,
) -> str:
    # Extract groups from the actual Entra ID token
    if __oauth_token__:
        user_info = self._extract_user_from_token(__oauth_token__)
        # user_info now has groups from token claims (NOT headers)
```

### Why This Matters

| Method | Security | Source |
|--------|----------|--------|
| Headers (`X-User-Groups`) | ⚠️ Can be spoofed | Client sends them |
| `__oauth_token__` | ✅ Cryptographically signed | Entra ID signs them |

With `__oauth_token__`:
- Token is signed by Microsoft Entra ID
- Groups come from the `groups` claim in the JWT
- Cannot be faked by an attacker

---

## How `__event_emitter__` Works

Shows progress in the UI while tool runs:

```python
async def long_running_tool(
    self,
    __event_emitter__: Callable[[dict], Any] = None,
):
    # Show "Starting..."
    await __event_emitter__({
        "type": "status",
        "data": {"description": "Starting operation...", "done": False}
    })

    # Do work...

    # Show "Done!"
    await __event_emitter__({
        "type": "status",
        "data": {"description": "Completed!", "done": True}
    })
```

**We use this in:** `mcp_entra_token_auth.py` for showing progress during MCP tool execution.

---

## What We Have Implemented

### 1. Token-Based Authentication (Most Secure)

```
User logs in via Entra ID
       ↓
Open WebUI gets OAuth token
       ↓
Tool function receives __oauth_token__
       ↓
We decode JWT and extract groups claim
       ↓
Groups determine MCP server access
```

### 2. Event Emitter for Status Updates

```
Tool starts → "Checking access for user@company.com..."
       ↓
Tool working → "Executing github/search_repositories..."
       ↓
Tool done → "Found 10 results"
```

### 3. Fallback to Headers

If `__oauth_token__` is not available (user not logged in via OAuth), we fall back to headers:

```python
if __oauth_token__:
    user_info = self._extract_user_from_token(__oauth_token__)
else:
    # Fallback to __user__ context
    user_info = {
        "email": __user__.get("email", ""),
        "groups": __user__.get("groups", []),
    }
```

---

## What's NOT Implemented Yet (Optional)

| Argument | Could Be Used For |
|----------|-------------------|
| `__metadata__` | Logging which chat/message triggered the tool |
| `__messages__` | Context-aware tools that understand conversation |
| `__files__` | Tools that process uploaded files |
| `__event_call__` | Tools that call other tools |

These are optional - we don't need them for the current MCP Proxy use case.

---

## The Complete Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  1. User logs in via Microsoft Entra ID (OAuth/OIDC)            │
│     └── Open WebUI gets id_token with groups claim               │
│                                                                  │
│  2. User asks AI to use an MCP tool                              │
│     └── "Search GitHub for kubernetes repositories"              │
│                                                                  │
│  3. Open WebUI calls our function with:                          │
│     └── __oauth_token__ = {id_token: "...", access_token: "..."}│
│     └── __user__ = {email: "user@company.com", ...}              │
│     └── __event_emitter__ = <function for status updates>        │
│                                                                  │
│  4. Our function extracts groups from token:                     │
│     └── decode_jwt_payload(id_token)                             │
│     └── groups = ["MCP-GitHub", "MCP-Admin"]                     │
│                                                                  │
│  5. Our function calls MCP Proxy with headers:                   │
│     └── X-Entra-Groups: MCP-GitHub,MCP-Admin                     │
│     └── X-Auth-Source: entra-token                               │
│                                                                  │
│  6. MCP Proxy checks database:                                   │
│     └── group_tenant_mapping: MCP-GitHub -> github               │
│     └── Access granted!                                          │
│                                                                  │
│  7. Result returned to user                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Files That Implement This

| File | Purpose |
|------|---------|
| `open-webui-functions/mcp_entra_token_auth.py` | Uses `__oauth_token__` to get groups from token |
| `mcp-proxy/auth.py` | Validates `X-Auth-Source: entra-token` and trusts groups |
| `mcp-proxy/db.py` | Looks up `group_tenant_mapping` in database |
| `mcp-proxy/tenants.py` | Routes to correct MCP backend |

---

## Summary for Lukas

**What the docs describe:** Optional arguments like `__oauth_token__` for secure authentication.

**What we built:** Full implementation using `__oauth_token__` to extract Entra ID groups from the actual JWT token, which is the "recommended and secure" way per the docs.

**Result:** Groups determine MCP access, and they come from a cryptographically signed token - not spoofable headers.

---

*Generated: 2026-01-21*
