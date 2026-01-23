# Open WebUI Custom Toolkit Development Guide

**Source:** https://docs.openwebui.com/features/plugin/tools/development
**Scraped:** 2026-01-22

## Overview

Creating custom toolkits in Open WebUI involves defining tools in a single Python file with metadata and a `Tools` class structure. The framework supports async functions, customizable settings, and rich event emission capabilities.

## Core Structure

### Top-Level Docstring Metadata

Every toolkit requires documentation specifying:

```python
"""title: Tool Name
author: Your Name
author_url: https://website.com
git_url: https://github.com/username/repo.git
description: Brief tool description
required_open_webui_version: 0.4.0
requirements: package1, package2
version: 0.4.0
licence: MIT"""
```

### Tools Class Architecture

The `Tools` class serves as the container, with optional nested `Valves` and `UserValves` classes for configuration:

```python
class Tools:
    def __init__(self):
        self.valves = self.Valves()

    class Valves(BaseModel):
        api_key: str = Field("", description="API credentials")

    async def tool_method(self, param: str) -> str:
        """Tool implementation with type hints"""
        return result
```

## Essential Requirements

### Type Hints Mandate

"Each tool must have type hints for arguments." These generate JSON schemas for model integration. Complex nested types like `list[tuple[str, int]]` are supported.

### Async Functions Priority

"Tool methods should generally be defined as `async` to ensure compatibility with future Open WebUI versions." Synchronous functions risk blocking execution in future releases.

## Optional Method Arguments

Tools can request injected parameters:

| Parameter | Purpose |
|-----------|---------|
| `__event_emitter__` | Emit real-time UI updates |
| `__event_call__` | User interaction events |
| `__user__` | User context and UserValves |
| `__metadata__` | Chat session metadata |
| `__messages__` | Previous message history |
| `__files__` | Attached files from user |
| `__model__` | Active model information |
| `__oauth_token__` | Secure OAuth token access |

### OAuth Token Implementation

```python
async def secure_api_call(self, __oauth_token__: Optional[dict] = None) -> str:
    if not __oauth_token__ or "access_token" not in __oauth_token__:
        return "Error: OAuth authentication required"
    token = __oauth_token__["access_token"]
    # Use token for authenticated requests
```

## Event Emitters: Critical Compatibility Notice

Event behavior differs drastically between function calling modes:

- **Default Mode**: Full event support
- **Native Mode (Agentic)**: Limited—many events break due to content snapshot overwriting

### Function Calling Modes

Configure via Admin Panel or per-request in chat advanced parameters:
- `function_calling = "default"` — Traditional approach, full event compatibility
- `function_calling = "native"` — Model-native tool calling, reduced latency, limited events

### Compatibility Matrix Summary

| Event Type | Default | Native | Status |
|-----------|---------|--------|--------|
| `status` | ✅ | ✅ | Fully compatible |
| `message` | ✅ | ❌ | Incompatible |
| `citation` | ✅ | ✅ | Fully compatible |
| `replace` | ✅ | ❌ | Incompatible |
| `notification` | ✅ | ✅ | Fully compatible |

### Status Events (Universal)

Status updates work identically across both modes:

```python
await __event_emitter__({
    "type": "status",
    "data": {
        "description": "Processing step 1...",
        "done": False,
        "hidden": False
    }
})
```

Use for progress tracking, multi-step workflows, and real-time feedback.

### Message Events (Default Mode Only)

⚠️ **Warning**: These break in Native Mode—content gets overwritten by completion snapshots.

```python
await __event_emitter__({
    "type": "message",
    "data": {"content": "Progressive streaming content"}
})
```

Replacement alternative for Native Mode compliance:

```python
await __event_emitter__({
    "type": "replace",
    "data": {"content": "Complete replacement text"}
})
```

### Citation Events (Universal)

Essential for source attribution across all modes:

```python
class Tools:
    def __init__(self):
        self.citation = False  # Required to enable custom citations

async def research(self, topic: str, __event_emitter__=None) -> str:
    await __event_emitter__({
        "type": "citation",
        "data": {
            "document": ["Source content"],
            "metadata": [{
                "date_accessed": datetime.now().isoformat(),
                "source": "Title",
                "author": "Name",
                "url": "https://source.com"
            }],
            "source": {"name": "Title", "url": "https://source.com"}
        }
    })
```

## Built-in System Tools (Native Mode)

When Native/Agentic Mode is enabled, these tools auto-inject:

### Search & Web
- `search_web` — Public web search (requires `ENABLE_WEB_SEARCH`)
- `fetch_url` — Extract text from URLs

### Knowledge Base
- `list_knowledge_bases` — Enumerate accessible bases
- `query_knowledge_bases` — Vector/semantic search
- `view_knowledge_file` — Full file content retrieval

### Image Generation
- `generate_image` — Create images from prompts
- `edit_image` — Modify existing images

### Memory & Personalization
- `search_memories` — User memory lookup
- `add_memory` — Store user facts
- `replace_memory_content` — Update existing memories

### Notes
- `search_notes` — Query user notes
- `view_note` — Retrieve full note content
- `write_note` — Create new notes
- `replace_note_content` — Update note content

### Chat & Channels
- `search_chats` — Text search across chat history
- `view_chat` — Retrieve full chat transcripts
- `search_channels` — Find public/accessible channels
- `search_channel_messages` — Search within channels

### Time
- `get_current_timestamp` — UTC Unix time and ISO date
- `calculate_timestamp` — Relative timestamp calculations

⚠️ "Quality Models Required for Agentic Behavior"—frontier models like GPT-5, Claude 4.5+, or Gemini 3+ work best; small local models often struggle.

## Valves and UserValves Configuration

### Valves (System-Level Settings)

```python
class Valves(BaseModel):
    api_key: str = Field("", description="Your API key")
    timeout: int = Field(30, description="Request timeout in seconds")
    debug_mode: bool = Field(False, description="Enable debug logging")
```

### UserValves (Per-User Customization)

```python
class UserValves(BaseModel):
    personal_api_key: str = Field("", description="User's custom API key")
    preferences: str = Field("default", description="User preferences")
```

Access via: `__user__["valves"]` for UserValves, `self.valves` for Valves.

## Rich UI Element Embedding

Tools can return interactive HTML content embedded as iframes:

```python
from fastapi.responses import HTMLResponse

def visualization_tool(self, data: str) -> HTMLResponse:
    html = """
    <!DOCTYPE html>
    <html>
    <body>
        <div id="chart"></div>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <script>
            Plotly.newPlot('chart', [{y: [1,2,3], type: 'scatter'}]);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(
        content=html,
        headers={"Content-Disposition": "inline"}
    )
```

For external tools with CORS, expose the header:

```javascript
res.set({
    'Content-Disposition': 'inline',
    'Access-Control-Expose-Headers': 'Content-Disposition'
})
```

Supports auto-resizing iframes, cross-origin messaging, and configurable sandbox restrictions.

## External Package Management

Specify dependencies in metadata; `pip install` executes upon save:

```python
"""
requirements: pandas>=1.5.0,numpy,requests
"""
```

⚠️ **Critical**: Non-deterministic installation order with conflicting versions across multiple tools. "The only robust solution to this problem is to use an OpenAPI tool server."

## Mode-Adaptive Tool Pattern

For tools supporting both function calling modes:

```python
async def adaptive_tool(
    self,
    query: str,
    __event_emitter__=None,
    __metadata__=None
) -> str:
    mode = __metadata__.get("params", {}).get("function_calling", "default") \
        if __metadata__ else "default"
    is_native = (mode == "native")

    # Status works everywhere
    await __event_emitter__({
        "type": "status",
        "data": {"description": f"Mode: {mode}", "done": False}
    })

    if is_native:
        # Use only compatible events
        result = "Native mode execution"
    else:
        # Full event capability
        await __event_emitter__({
            "type": "message",
            "data": {"content": "Streaming supported"}
        })
        result = "Default mode with streaming"

    return result
```

## Best Practices

1. **Always use async functions** for future-proofing
2. **Include comprehensive type hints** for schema generation
3. **Disable auto-citations** (`self.citation = False`) when implementing custom citations
4. **Test in both function calling modes** for broad compatibility
5. **Prefer status events** for universal compatibility
6. **Document mode requirements** in docstrings
7. **Handle missing `__event_emitter__`** gracefully
8. **Use OAuth tokens** instead of cookie scraping for authentication

---

## Key Takeaways for Lukas (Excel & Graph Tools)

### For Excel Creation:
1. The MCP Excel tool is an **external OpenAPI tool server** (the recommended approach)
2. To use it, the model needs to support **function calling**
3. Select a capable model like `gpt-4o` or `gpt-4-turbo` (not `gpt-4-0613` which is older)

### For Graph/Visualization:
Use the **HTMLResponse** pattern to return interactive charts:

```python
from fastapi.responses import HTMLResponse

def create_chart(self, data: str) -> HTMLResponse:
    html = """
    <!DOCTYPE html>
    <html>
    <body>
        <div id="chart"></div>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <script>
            Plotly.newPlot('chart', [{y: [1,2,3], type: 'scatter'}]);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html, headers={"Content-Disposition": "inline"})
```

### Why Tools Might Not Work:
1. **Model doesn't support function calling** - Use gpt-4o, gpt-4-turbo, or newer
2. **Function calling mode** - Check Advanced Params → Function Calling setting
3. **Tools not enabled for model** - Configure in Admin → Models
