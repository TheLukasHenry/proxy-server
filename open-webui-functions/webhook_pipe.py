"""
Webhook Automation Pipe Function for Open WebUI

Combines AI reasoning with MCP tool execution and n8n workflow triggering.
When the webhook handler receives an automation request, it calls this pipe
function as a "model" via /api/chat/completions. The pipe analyzes the payload
with AI, decides which MCP tools or n8n workflows to invoke, executes them,
and returns a unified response.

Installation:
1. Go to Open WebUI Admin Panel -> Workspace -> Functions -> Add Function
2. Paste this code, save and enable
3. Configure Valves (API URL, API key, MCP Proxy URL, n8n URL, real model name)
4. Select "Webhook Automation" model in chat to test

Data flow:
  External trigger -> POST /webhook/automation
    -> webhook-handler wraps payload in message
      -> OpenWebUIClient.chat_completion(model="webhook_automation.webhook-automation")
        -> This Pipe Function
          -> Phase 1: Fetch available MCP tools + n8n workflows
          -> Phase 2: Call real LLM to decide what to invoke
          -> Phase 3: Execute MCP tools and/or trigger n8n workflows
          -> Phase 4: Call real LLM to summarize results
        -> Returns combined AI + tool + workflow response
"""

import json
import re
import httpx
from typing import List, Optional, Callable, Any, Union
from pydantic import BaseModel, Field


class Pipe:
    """Webhook Automation — AI reasoning + MCP tools + n8n workflows."""

    class Valves(BaseModel):
        """Configuration for the Webhook Automation pipe."""
        OPENWEBUI_API_URL: str = Field(
            default="http://localhost:8080",
            description="Open WebUI API URL (self-reference for internal LLM calls)"
        )
        OPENWEBUI_API_KEY: str = Field(
            default="",
            description="Admin API key for internal LLM calls"
        )
        AI_MODEL: str = Field(
            default="gpt-4-turbo",
            description="Real model for AI reasoning (must NOT be this pipe's own model name)"
        )
        MCP_PROXY_URL: str = Field(
            default="http://mcp-proxy:8000",
            description="MCP Proxy Gateway URL"
        )
        MCP_USER_EMAIL: str = Field(
            default="webhook-handler@system",
            description="X-User-Email header for MCP Proxy auth"
        )
        MCP_USER_GROUPS: str = Field(
            default="MCP-Admin",
            description="X-User-Groups header for MCP Proxy auth"
        )
        N8N_URL: str = Field(
            default="http://n8n:5678",
            description="n8n base URL for workflow API and webhook triggers"
        )
        N8N_API_KEY: str = Field(
            default="",
            description="n8n API key (required to list workflows)"
        )
        TIMEOUT_SECONDS: int = Field(
            default=90,
            description="Overall timeout for HTTP requests (seconds)"
        )
        MAX_TOOL_CALLS: int = Field(
            default=5,
            description="Maximum number of MCP tool / n8n workflow calls per request"
        )

    def __init__(self):
        self.valves = self.Valves()

    def pipes(self) -> List[dict]:
        """Register this pipe as a selectable model in Open WebUI."""
        return [{"id": "webhook-automation", "name": "Webhook Automation"}]

    async def pipe(
        self,
        body: dict,
        __user__: dict = None,
        __event_emitter__: Callable[[dict], Any] = None,
    ) -> Union[str, dict]:
        """
        Main entry point. Called by Open WebUI when this pipe is used as a model.

        Phases:
        1. Parse the incoming payload from the last user message
        2. Fetch available MCP tools and n8n workflows
        3. Ask the real LLM which actions to take
        4. Execute MCP tools and/or trigger n8n workflows
        5. Ask the real LLM to produce a final summary
        """
        await self._emit(
            __event_emitter__, "status",
            "Analyzing automation request...", done=False
        )

        # --- Extract the user message (last message in the conversation) ---
        messages = body.get("messages", [])
        if not messages:
            return "No messages provided."

        user_message = messages[-1].get("content", "")

        # Try to parse as JSON payload (from webhook handler)
        payload = None
        try:
            payload = json.loads(user_message)
        except (json.JSONDecodeError, TypeError):
            pass

        # If it's not JSON, treat the raw text as the payload
        if payload is None:
            payload = {"raw_message": user_message}

        source = payload.get("source", "unknown")
        instructions = payload.get("instructions", "")
        event_data = payload.get("payload", payload)

        # --- Phase 1: Fetch available MCP tools + n8n workflows ---
        await self._emit(
            __event_emitter__, "status",
            "Fetching available tools and workflows...", done=False
        )
        tools = await self._fetch_tools()
        tools_description = self._format_tools(tools) if tools else "No MCP tools available."

        workflows = await self._fetch_n8n_workflows()
        workflows_description = self._format_workflows(workflows)

        # --- Phase 2: Ask LLM to plan actions ---
        await self._emit(
            __event_emitter__, "status",
            "Planning execution...", done=False
        )

        planning_prompt = self._build_planning_prompt(
            source=source,
            instructions=instructions,
            event_data=event_data,
            tools_description=tools_description,
            workflows_description=workflows_description,
        )

        planning_messages = [
            {
                "role": "system",
                "content": (
                    "You are an automation assistant. You receive webhook payloads "
                    "and decide which MCP tools to call and/or which n8n workflows "
                    "to trigger. Always respond with a JSON array of action objects, "
                    "or an empty array if no actions are needed.\n\n"
                    "Two action types are supported:\n\n"
                    "MCP tool call:\n"
                    '  {"type": "mcp", "server_id": "...", "tool_name": "...", "arguments": {...}}\n\n'
                    "n8n workflow trigger:\n"
                    '  {"type": "n8n", "webhook_path": "...", "payload": {...}}\n\n'
                    "Respond ONLY with the JSON array, no other text."
                )
            },
            {"role": "user", "content": planning_prompt}
        ]

        plan_response = await self._call_llm(planning_messages)
        if not plan_response:
            return "Failed to get AI planning response. Check Valves configuration."

        actions = self._parse_actions(plan_response)

        # --- Phase 3: Execute actions ---
        action_results = []
        if actions:
            await self._emit(
                __event_emitter__, "status",
                f"Executing {len(actions)} action(s)...", done=False
            )

            for i, action in enumerate(actions[: self.valves.MAX_TOOL_CALLS]):
                action_type = action.get("type", "mcp")

                if action_type == "n8n":
                    # --- n8n workflow trigger ---
                    webhook_path = action.get("webhook_path", "")
                    n8n_payload = action.get("payload", {})

                    if not webhook_path:
                        action_results.append({
                            "type": "n8n",
                            "workflow": webhook_path,
                            "error": "Missing webhook_path"
                        })
                        continue

                    await self._emit(
                        __event_emitter__, "status",
                        f"Triggering n8n workflow '{webhook_path}' ({i+1}/{len(actions)})...",
                        done=False
                    )

                    result = await self._trigger_n8n_workflow(webhook_path, n8n_payload)
                    action_results.append({
                        "type": "n8n",
                        "workflow": webhook_path,
                        "payload": n8n_payload,
                        "result": result,
                    })

                else:
                    # --- MCP tool call (default) ---
                    server_id = action.get("server_id", "")
                    tool_name = action.get("tool_name", "")
                    arguments = action.get("arguments", {})

                    if not server_id or not tool_name:
                        action_results.append({
                            "type": "mcp",
                            "tool": f"{server_id}/{tool_name}",
                            "error": "Missing server_id or tool_name"
                        })
                        continue

                    await self._emit(
                        __event_emitter__, "status",
                        f"Running {server_id}/{tool_name} ({i+1}/{len(actions)})...",
                        done=False
                    )

                    result = await self._execute_tool(server_id, tool_name, arguments)
                    action_results.append({
                        "type": "mcp",
                        "tool": f"{server_id}/{tool_name}",
                        "arguments": arguments,
                        "result": result,
                    })

        # --- Phase 4: Summarize with LLM ---
        await self._emit(
            __event_emitter__, "status",
            "Generating summary...", done=False
        )

        summary_prompt = self._build_summary_prompt(
            source=source,
            instructions=instructions,
            event_data=event_data,
            actions=actions,
            action_results=action_results,
        )

        summary_messages = [
            {
                "role": "system",
                "content": (
                    "You are an automation assistant. Summarize the results of "
                    "webhook processing, tool execution, and workflow triggers. "
                    "Be concise and actionable. "
                    "If tools or workflows returned data, highlight the key information."
                )
            },
            {"role": "user", "content": summary_prompt}
        ]

        summary = await self._call_llm(summary_messages)
        if not summary:
            summary = "Failed to generate summary."

        await self._emit(__event_emitter__, "status", "Done", done=True)

        return summary

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _emit(
        self,
        emitter: Optional[Callable],
        event_type: str,
        description: str,
        done: bool = False,
    ):
        """Emit a status event to the UI if an emitter is available."""
        if emitter:
            await emitter({
                "type": event_type,
                "data": {"description": description, "done": done}
            })

    async def _call_llm(self, messages: List[dict]) -> Optional[str]:
        """
        Call Open WebUI /api/chat/completions with the real AI model.

        IMPORTANT: Uses self.valves.AI_MODEL (e.g. gpt-4-turbo), never the
        pipe's own model name, to prevent infinite recursion.
        """
        url = f"{self.valves.OPENWEBUI_API_URL}/api/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.valves.OPENWEBUI_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.valves.AI_MODEL,
            "messages": messages,
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(timeout=self.valves.TIMEOUT_SECONDS) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                if "choices" in data and len(data["choices"]) > 0:
                    return data["choices"][0]["message"]["content"]
                return None
        except Exception as e:
            return f"[LLM Error: {e}]"

    # --- MCP ---

    async def _fetch_tools(self) -> Optional[List[dict]]:
        """Fetch all available MCP tools from the proxy."""
        url = f"{self.valves.MCP_PROXY_URL}/tools"
        headers = {
            "X-User-Email": self.valves.MCP_USER_EMAIL,
            "X-User-Groups": self.valves.MCP_USER_GROUPS,
        }

        try:
            async with httpx.AsyncClient(timeout=self.valves.TIMEOUT_SECONDS) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.json()
        except Exception:
            return None

    async def _execute_tool(
        self, server_id: str, tool_name: str, arguments: dict
    ) -> Any:
        """Execute a single MCP tool via the proxy."""
        # Try tool_name as-is first, then strip server prefix
        candidates = [tool_name]
        prefix = f"{server_id}_"
        if tool_name.startswith(prefix):
            candidates.append(tool_name[len(prefix):])

        headers = {
            "X-User-Email": self.valves.MCP_USER_EMAIL,
            "X-User-Groups": self.valves.MCP_USER_GROUPS,
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.valves.TIMEOUT_SECONDS) as client:
                for name in candidates:
                    url = f"{self.valves.MCP_PROXY_URL}/{server_id}/{name}"
                    response = await client.post(url, json=arguments, headers=headers)
                    if response.status_code == 404 and name != candidates[-1]:
                        continue
                    response.raise_for_status()
                    return response.json()
        except Exception as e:
            return {"error": str(e)}

    # --- n8n ---

    async def _fetch_n8n_workflows(self) -> List[dict]:
        """
        Fetch active n8n workflows via the n8n API.

        Returns a list of workflow dicts with id, name, and webhook paths.
        Requires N8N_API_KEY to be set.
        """
        if not self.valves.N8N_API_KEY:
            return []

        url = f"{self.valves.N8N_URL}/api/v1/workflows"
        headers = {
            "X-N8N-API-KEY": self.valves.N8N_API_KEY,
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.valves.TIMEOUT_SECONDS) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                workflows = data.get("data", data) if isinstance(data, dict) else data
                if not isinstance(workflows, list):
                    return []
                # Only return active workflows
                return [w for w in workflows if w.get("active", False)]
        except Exception:
            return []

    async def _trigger_n8n_workflow(
        self, webhook_path: str, payload: dict
    ) -> Any:
        """Trigger an n8n workflow via its webhook URL."""
        url = f"{self.valves.N8N_URL}/webhook/{webhook_path}"
        headers = {"Content-Type": "application/json"}

        try:
            async with httpx.AsyncClient(timeout=self.valves.TIMEOUT_SECONDS) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                # n8n may return text or JSON
                try:
                    return response.json()
                except Exception:
                    return {"response": response.text}
        except Exception as e:
            return {"error": str(e)}

    # --- Parsing ---

    def _parse_actions(self, ai_response: str) -> List[dict]:
        """Extract a JSON array of action objects from the AI response."""
        # Try to parse the entire response as JSON first
        try:
            parsed = json.loads(ai_response.strip())
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass

        # Fall back to extracting JSON array from markdown code blocks or inline
        patterns = [
            r"```(?:json)?\s*(\[.*?\])\s*```",
            r"(\[[\s\S]*?\{[\s\S]*?\"(?:server_id|type|webhook_path)\"[\s\S]*?\}\s*\])",
        ]
        for pattern in patterns:
            match = re.search(pattern, ai_response, re.DOTALL)
            if match:
                try:
                    parsed = json.loads(match.group(1))
                    if isinstance(parsed, list):
                        return parsed
                except (json.JSONDecodeError, TypeError):
                    continue

        return []

    # --- Formatting ---

    def _format_tools(self, tools: Any) -> str:
        """Format MCP tool list into a readable string for the LLM prompt."""
        if isinstance(tools, dict) and "tools" in tools:
            tools = tools["tools"]

        if not isinstance(tools, list):
            return "No tools available."

        lines = []
        for tool in tools:
            name = tool.get("name", tool.get("tool_name", "unknown"))
            # MCP Proxy returns tenant_id as the server identifier
            server = tool.get("tenant_id", tool.get("server_id", "unknown"))
            desc = tool.get("description", "No description")
            params = tool.get("parameters", tool.get("inputSchema", {}))
            if params is None:
                params = {}
            props = params.get("properties", {}) if isinstance(params, dict) else {}
            param_names = list(props.keys()) if props else []
            param_str = f" (params: {', '.join(param_names)})" if param_names else ""
            lines.append(f"- server_id={server}, tool_name={name}: {desc}{param_str}")

        return "\n".join(lines) if lines else "No tools available."

    def _format_workflows(self, workflows: List[dict]) -> str:
        """Format n8n workflows into a readable string for the LLM prompt."""
        if not workflows:
            return "No n8n workflows available."

        lines = []
        for wf in workflows:
            wf_id = wf.get("id", "unknown")
            name = wf.get("name", "Unnamed workflow")
            # Try to extract webhook paths from the workflow nodes
            webhook_path = self._extract_webhook_path(wf)
            if webhook_path:
                lines.append(
                    f"- webhook_path={webhook_path}, name={name} (id={wf_id})"
                )
            else:
                lines.append(
                    f"- name={name} (id={wf_id}) [no webhook trigger — cannot be called externally]"
                )

        return "\n".join(lines) if lines else "No n8n workflows available."

    def _extract_webhook_path(self, workflow: dict) -> Optional[str]:
        """Extract the webhook path from an n8n workflow's nodes."""
        nodes = workflow.get("nodes", [])
        for node in nodes:
            node_type = node.get("type", "")
            # n8n webhook node types
            if "webhook" in node_type.lower():
                params = node.get("parameters", {})
                path = params.get("path", "")
                if path:
                    return path
                # Some webhook nodes use "options.path"
                options = params.get("options", {})
                if isinstance(options, dict):
                    path = options.get("path", "")
                    if path:
                        return path
        return None

    # --- Prompt building ---

    def _build_planning_prompt(
        self,
        source: str,
        instructions: str,
        event_data: Any,
        tools_description: str,
        workflows_description: str,
    ) -> str:
        """Build the prompt that asks the LLM which actions to take."""
        event_str = json.dumps(event_data, indent=2, default=str)[:4000]

        parts = [
            f"Source: {source}",
            f"\nPayload:\n```json\n{event_str}\n```",
            f"\nAvailable MCP Tools:\n{tools_description}",
            f"\nAvailable n8n Workflows:\n{workflows_description}",
        ]

        if instructions:
            parts.append(f"\nUser Instructions: {instructions}")

        parts.append(
            "\nBased on the payload and instructions, which actions should be taken? "
            "You can call MCP tools and/or trigger n8n workflows. "
            "Respond with a JSON array of action objects. "
            "Use an empty array [] if no actions are needed."
        )

        return "\n".join(parts)

    def _build_summary_prompt(
        self,
        source: str,
        instructions: str,
        event_data: Any,
        actions: List[dict],
        action_results: List[dict],
    ) -> str:
        """Build the prompt for the final summary."""
        event_str = json.dumps(event_data, indent=2, default=str)[:2000]
        results_str = json.dumps(action_results, indent=2, default=str)[:4000]

        parts = [
            f"Source: {source}",
            f"\nOriginal Payload:\n```json\n{event_str}\n```",
        ]

        if instructions:
            parts.append(f"\nUser Instructions: {instructions}")

        if actions:
            mcp_count = sum(1 for a in actions if a.get("type", "mcp") == "mcp")
            n8n_count = sum(1 for a in actions if a.get("type") == "n8n")
            parts.append(f"\nActions Taken: {len(actions)} total ({mcp_count} MCP tools, {n8n_count} n8n workflows)")
            parts.append(f"\nResults:\n```json\n{results_str}\n```")
        else:
            parts.append("\nNo actions were taken.")

        parts.append(
            "\nProvide a concise summary of what happened and the key results. "
            "If tools or workflows returned data, highlight the important information."
        )

        return "\n".join(parts)
