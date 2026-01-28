# Progressive Disclosure / Smart Tool Selection — Research Report

## Date: 2026-01-27 | US-008

## Problem Statement

Our MCP Proxy aggregates 200+ tools from multiple MCP servers behind a single OpenAPI endpoint. When Open WebUI fetches `/openapi.json`, all tool schemas are sent to the LLM, consuming 200,000-400,000+ tokens — potentially exceeding context windows and degrading tool selection accuracy. We need a way to intelligently reduce the tool count sent to the LLM per request.

**Current state**: 232 tools cached, ~7 MCP servers active. With all planned servers enabled, this could reach 500+ tools.

---

## Executive Summary

Research across LangChain, LlamaIndex, MCP protocol proposals, and production systems converges on one clear winner for our architecture: **Speakeasy-style Dynamic Toolsets** — replace all tools with 3 meta-tools (`search_tools`, `describe_tools`, `call_tool`) that let the LLM discover tools on demand. This achieves **96-99% token reduction** with **100% success rate** in benchmarks up to 400 tools.

Additionally, Open WebUI has a **Filter Function** mechanism (inlet hooks) that can modify `body["tool_ids"]` per-request — and there's an existing **AutoTool Filter** that does exactly this using a lightweight LLM call. This provides a **second implementation path** that works entirely within Open WebUI, complementing the proxy-level approach.

For our architecture specifically, the recommended implementation is a **three-layer hybrid**:
1. **Layer 1 — Proxy** (done): Group-based tenant filtering via `generate_dynamic_openapi_filtered()`
2. **Layer 2 — Proxy**: Embedding-based semantic search via pgvector (already in our stack)
3. **Layer 3 — Open WebUI**: AutoTool-style inlet filter for per-query tool selection
4. **Layer 4 — Proxy** (optimal): Tool Search meta-tools for LLM-driven discovery

**Top recommendation**: Start with Layer 2 (pgvector embeddings in proxy) + Layer 3 (AutoTool filter in Open WebUI). Layer 4 is the endgame but Layers 2+3 get us 80% of the value faster.

---

## Approaches Evaluated

### 1. Speakeasy-Style Dynamic Toolsets (RECOMMENDED)

**What it is**: Instead of exposing all 200+ tools, expose only 3 meta-tools:
- `search_tools(query)` — semantic search over all tool descriptions
- `describe_tools(tool_names[])` — returns full schemas for selected tools only
- `call_tool(name, args)` — executes a previously discovered tool

**Benchmarks** (Claude Sonnet 4, tested 40-400 tools):

| Toolset Size | Static Tokens | Dynamic Tokens | Reduction |
|---|---|---|---|
| 40 tools | 43,300 | 1,600 | 96% |
| 100 tools | 105,000 | 1,800 | 98% |
| 200 tools | 205,000 (exceeds context) | 2,000 | 99% |
| 400 tools | 405,100 (impossible) | 2,500 | 99.4% |

- **100% success rate** across all sizes for simple and complex tasks
- Complex multi-tool workflows: 90.7% total token reduction

**Fit for our architecture**: EXCELLENT — can implement directly in our FastAPI proxy's existing `mcp_server.py` MCP endpoint or as OpenAPI endpoints in `main.py`.

**Sources**: [Speakeasy Dynamic Toolsets](https://www.speakeasy.com/blog/100x-token-reduction-dynamic-toolsets), [Dynamic Toolsets v2](https://www.speakeasy.com/blog/how-we-reduced-token-usage-by-100x-dynamic-toolsets-v2)

---

### 2. Embedding-Based Semantic Search (pgvector)

**What it is**: Pre-compute vector embeddings for each tool's name + description. At request time, embed the user's query and find top-K similar tools via cosine similarity.

**Key findings**:
- **ScaleMCP** (May 2025, 5,000 MCP servers, ~140K queries): Recall@5 = 0.94 with TDWA embeddings + reranking
- **Portkey mcp-tool-filter**: Reduces 1,000+ tools to 10-20 in <10ms with local embeddings
- **Recommended model**: `all-MiniLM-L6-v2` (22M params, 384-dim, 14K sentences/sec on CPU)
- **Recommended K**: 15-25 tools for a 200-tool corpus, with similarity threshold cutoff

**Latency**:

| Component | Local Embedding | API Embedding (OpenAI) |
|---|---|---|
| Embed query | 1-5ms | 200-500ms |
| Vector search (pgvector, 200 tools) | 1-5ms | 1-5ms |
| **Total** | **2-10ms** | **200-500ms** |

**pgvector implementation** (we already have `pgvector/pgvector:pg16`):

```sql
CREATE TABLE mcp_proxy.tool_embeddings (
    tool_id VARCHAR(255) PRIMARY KEY,
    server_id VARCHAR(255) NOT NULL,
    tool_name VARCHAR(255),
    description TEXT,
    embedding vector(384),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX ON mcp_proxy.tool_embeddings USING ivfflat (embedding vector_cosine_ops);
```

Query combines tenant access control + semantic filtering:
```sql
SELECT tool_id, tool_name, description,
       1 - (embedding <=> $1) as similarity
FROM mcp_proxy.tool_embeddings
WHERE server_id = ANY($2)  -- user's allowed servers
ORDER BY embedding <=> $1
LIMIT 20;
```

**Dependencies**: `sentence-transformers` or `fastembed` (lighter, no PyTorch), `pgvector` Python package

**Sources**: [ScaleMCP (arXiv:2505.06416)](https://arxiv.org/abs/2505.06416), [Portkey mcp-tool-filter](https://github.com/Portkey-AI/mcp-tool-filter)

---

### 3. BM25/TF-IDF Keyword Matching

**What it is**: Tokenize tool names/descriptions, build a BM25 index. Score user queries against the index. Zero API calls, pure CPU.

**Accuracy vs embeddings**:

| Metric | BM25/TF-IDF | Embeddings | Hybrid |
|---|---|---|---|
| Recall@5 | 0.50-0.70 | 0.75-0.85 | 0.85-0.94 |
| Handles synonyms | Poor | Good | Good |
| Exact term matching | Excellent | Moderate | Excellent |

**Key limitation**: If user says "create a spreadsheet" but tool is called `excel_generate_workbook`, BM25 misses it. Embeddings handle this semantic gap.

**Latency**: <1ms for 200 tools. Zero external dependencies.

**Libraries**: `rank_bm25` (simple), `bm25s` (100x faster)

**Best use**: Baseline/fallback, or first stage in a hybrid pipeline.

---

### 4. Category/Tag-Based Routing

**What it is**: Pre-assign tools to categories (we already have server-level grouping in `tenants.py`). Detect category from query keywords, return only matching tools.

**Our existing categories** (from `tenants.py`):
- Issue Tracking: linear, clickup, trello, asana
- Source Control: github, gitlab, bitbucket
- Code Quality: sonarqube
- File Storage: filesystem
- Reporting: excel-creator, dashboard

**Accuracy**: 60-75% for single-category queries, poor for multi-category ("find the Jira bug and check SonarQube analysis").

**Best use**: Coarse first-pass filter combined with semantic search.

---

### 5. LangChain `langgraph-bigtool`

**What it is**: Dedicated library for large toolsets. Creates a tool registry, indexes descriptions in a vector store, builds a StateGraph with built-in `retrieve_tools` node.

```bash
pip install langgraph-bigtool
```

**Assessment**:
- Maturity: v0.0.3 (March 2025), actively maintained by LangChain team
- Requires adopting LangGraph agent framework
- Good if we were building from scratch with LangChain
- **Not recommended for us**: Requires framework adoption that doesn't fit our existing FastAPI proxy

**Sources**: [langgraph-bigtool GitHub](https://github.com/langchain-ai/langgraph-bigtool)

---

### 6. LlamaIndex `ObjectIndex`

**What it is**: First-class tool retrieval via `ObjectIndex` and `ObjectRetriever`. Indexes tool objects using any LlamaIndex index type (VectorStoreIndex, etc.).

```python
obj_index = ObjectIndex.from_objects(all_tools, index_cls=VectorStoreIndex)
obj_retriever = obj_index.as_retriever(similarity_top_k=3)
agent = OpenAIAgent.from_tools(tool_retriever=obj_retriever)
```

**Assessment**:
- Mature, part of core LlamaIndex since v0.10+
- Supports 50+ vector stores including pgvector
- Same tradeoff as LangChain: requires framework adoption
- **Not recommended for us**: Same reason as LangChain

---

### 7. Two-Stage Model Selection

**What it is**: A cheap/fast model (GPT-4o-mini, Haiku) selects relevant tools, then the main model uses only those.

**Cost**: ~$0.0003-$0.001 per query for the selection step (sending 200 tool names to mini model)

**Latency**: +200-500ms for the cheap model call

**Assessment**: Viable but adds API dependency and latency. Better as a fallback for ambiguous queries where embedding search isn't confident enough.

---

### 8. ToolLLM / Gorilla / NexusRaven

**What they are**: Specialized models for API/function calling accuracy.

**Assessment**: These solve function-calling accuracy (generating correct API call syntax), NOT tool selection/filtering from large sets. **Not applicable to our problem.**

---

### 9. MCP Protocol Native

**Current state**: No built-in tool filtering in the MCP spec. Tool annotations (hints like `readOnlyHint`, `destructiveHint`) exist but aren't for selection.

**Proposals in progress**:
- [Discussion #532](https://github.com/orgs/modelcontextprotocol/discussions/532): Hierarchical Tool Management (categories, discover, load/unload)
- [SEP #1888](https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1888): Progressive Disclosure Extension (lazy-loading descriptions)
- [HuggingFace prototype](https://huggingface.co/spaces/MCP-1st-Birthday/mcp-extension-progressive-disclosure): Claims 96% token reduction

**Assessment**: Monitor these proposals but don't wait — implement at proxy level now.

---

### 10. Open WebUI Architecture & Filter Functions (KEY FINDING)

#### Spec Fetching Behavior
Open WebUI fetches `/openapi.json` **per-session** (not per-message). The spec defines what tools are available for the entire conversation. Our existing `generate_dynamic_openapi_filtered()` correctly filters by tenant/user permissions at this level.

#### Filter Functions — Per-Request Tool Filtering IS Possible

**Critical discovery**: Open WebUI's **Filter Functions** (inlet hooks) CAN modify `body["tool_ids"]` per-request. The `inlet` method receives the full request body before it reaches the LLM:

```python
class Filter:
    async def inlet(self, body: dict, __user__: dict = None, __tools__: dict = None) -> dict:
        # body["tool_ids"] = list of enabled tool IDs
        # body["messages"] = conversation history (includes current query)
        # __tools__ = dict of all available tools with specs and callables

        # Filter to only relevant tools based on user's query
        relevant = select_relevant_tools(body["messages"][-1]["content"], __tools__)
        body["tool_ids"] = relevant
        return body
```

#### AutoTool Filter — Existing Solution

The **AutoTool Filter** ([openwebui.com/f/hub/autotool_filter](https://openwebui.com/f/hub/autotool_filter)) already implements per-query tool selection:

1. Inlet intercepts the request
2. Retrieves all available tools, filters against model's configured `toolIds`
3. Sends user query + tool descriptions to a **lightweight LLM** (e.g., GPT-4o-mini)
4. LLM returns list of matching tool IDs
5. Filter updates `body["tool_ids"]` with only selected tools

**Two versions exist**:
- Official (v0.2.0) by `open-webui` — LLM-based selection
- Community (v4.1) by Sam McLeod, Wes Caldwell, Joshua Jama @ Perplexity — adds optional **semantic similarity matching** with configurable threshold

**Limitations**:
- Only fires on initial request, NOT on tool-call continuation turns ([Issue #18222](https://github.com/open-webui/open-webui/issues/18222))
- Cannot inject tools that aren't already registered — can only select from existing `tool_ids`
- LLM-based version adds 200-500ms latency per request
- Sending 200+ tool descriptions to the selector LLM still needs optimization

#### Open WebUI v0.6.39+ and v0.7.0 Built-in Filtering

- **v0.6.39**: Tool servers support **function name allow/block lists** (admin-level, static)
- **v0.7.0**: Backend **access control checks** ensure users can only access permitted tools

These are static configurations, not per-query dynamic filtering.

#### Three-Layer Architecture (Recommended)

| Layer | Where | What | Granularity |
|---|---|---|---|
| **1. Proxy spec filtering** | `mcp-proxy/main.py` | Tenant/group-based tool access | Per-session |
| **2. Admin allow/block lists** | Open WebUI admin settings | Hide utility/admin-only tools | Static |
| **3. AutoTool inlet filter** | Open WebUI Filter Function | Per-query semantic tool selection | Per-message |

This reduces tools from 200+ → 30-50 (proxy) → 3-10 (inlet filter) before the LLM sees them.

**Sources**: [AutoTool Filter](https://openwebui.com/f/hub/autotool_filter), [Community AutoTool](https://github.com/sammcj/open-webui-pipelines/blob/main/filters/autotool-filter.py), [Filter Docs](https://docs.openwebui.com/features/plugin/functions/filter/), [Issue #18222](https://github.com/open-webui/open-webui/issues/18222)

---

## Comparative Evaluation Matrix

| Criteria | Embeddings (pgvector) | BM25 | Category | Speakeasy Meta-Tools | LangChain/LlamaIndex | Two-Stage LLM |
|---|---|---|---|---|---|---|
| **Implementation Complexity** | Medium | Low | Very Low | Medium | High (framework) | Medium |
| **Latency per Request** | 2-10ms | <1ms | ~0ms | 2-10ms + LLM turn | 2-10ms | +200-500ms |
| **Token Reduction** | 80-90% | 60-80% | 50-70% | **96-99%** | 80-90% | 80-90% |
| **Accuracy (Recall@20)** | 85-90% | 50-70% | 60-75% | **100%** (benchmarked) | 85-90% | 85-95% |
| **Handles Synonyms** | Yes | No | No | Yes | Yes | Yes |
| **Multi-category Queries** | Yes | Partial | Poor | Yes | Yes | Yes |
| **Works with Open WebUI** | Spec-level only | Spec-level only | Spec-level only | **Per-query** | N/A | Per-query |
| **External Dependencies** | fastembed | rank_bm25 | None | fastembed + pgvector | LangChain/LlamaIndex | LLM API |
| **Works Offline** | Yes (local model) | Yes | Yes | Yes (local model) | Yes | No |
| **Maintenance** | Re-embed on change | Rebuild index | Manual | Re-embed on change | Re-embed | None |

---

## Recommended Implementation Plan

### Phase 1: Group-Based Filtering (DONE)
Our proxy already filters tools by tenant/group membership via `generate_dynamic_openapi_filtered()`. This is the baseline — reduces 200+ tools to the user's authorized subset (~30-50).

### Phase 2a: Semantic Search via pgvector (RECOMMENDED NEXT — Proxy Layer)
**Why**: We already have pgvector in PostgreSQL, and this gives us the foundation for all advanced filtering.

1. Add `mcp_proxy.tool_embeddings` table
2. Add `fastembed` to mcp-proxy dependencies (lightweight, no PyTorch)
3. Embed all tools on cache refresh (`refresh_tools_cache()`)
4. Add semantic search function to query tools by user intent
5. Integrate with `generate_dynamic_openapi_filtered()` for spec-level filtering

**Estimated effort**: 2-3 days

### Phase 2b: AutoTool Filter (RECOMMENDED NEXT — Open WebUI Layer)
**Why**: This achieves per-query tool filtering using Open WebUI's existing plugin architecture. No proxy changes needed.

1. Deploy the AutoTool Filter (or community version with semantic matching) as an Open WebUI Function
2. Configure it to use a lightweight model (GPT-4o-mini) for tool selection
3. Set similarity threshold to balance precision vs recall
4. The filter reduces the user's 30-50 authorized tools to 3-10 per query

**Estimated effort**: 1 day (deploy existing filter) or 2-3 days (customize with our semantic search)

**Note**: Phases 2a and 2b are complementary and can be done in parallel:
- 2a reduces the OpenAPI spec (session-level, all conversations)
- 2b reduces per-message (query-level, each turn)

### Phase 3: Tool Search Meta-Tool (ENDGAME)
**Why**: Maximum token reduction (96-99%) and the most robust approach for 200+ tools.

1. Add `search_tools(query, limit=10)` endpoint to MCP proxy
2. Add `describe_tools(tool_names[])` endpoint for lazy schema loading
3. Modify `call_tool` to accept dynamically discovered tools
4. Keep the full OpenAPI spec minimal (only meta-tools visible)
5. LLM discovers and calls tools through the meta-tools

**Estimated effort**: 3-5 days (after Phase 2a foundation)

### Phase 4: Optimizations (Future)
- Cross-encoder reranking for ambiguous queries
- Synthetic query generation per tool (improves retrieval quality per ScaleMCP)
- Hash-based change detection to re-embed only changed tools
- Usage analytics to boost frequently-used tools
- Fix inlet continuation issue ([#18222](https://github.com/open-webui/open-webui/issues/18222)) when Open WebUI patches it

---

## Key Open Source References

| Project | What It Does | Link |
|---|---|---|
| **Portkey mcp-tool-filter** | Embedding-based MCP tool filtering, <10ms | [GitHub](https://github.com/Portkey-AI/mcp-tool-filter) |
| **ScaleMCP** | 5K MCP server tool retrieval research | [arXiv](https://arxiv.org/abs/2505.06416) |
| **langgraph-bigtool** | LangChain's dedicated large-toolset library | [GitHub](https://github.com/langchain-ai/langgraph-bigtool) |
| **Spring AI Tool Search Tool** | Java implementation of meta-tool pattern | [GitHub](https://github.com/spring-ai-community/spring-ai-tool-search-tool) |
| **Speakeasy Dynamic Toolsets** | Benchmarked meta-tool pattern (documented) | [Blog](https://www.speakeasy.com/blog/100x-token-reduction-dynamic-toolsets) |
| **fastembed** | Lightweight Python embeddings (no PyTorch) | [PyPI](https://pypi.org/project/fastembed/) |
| **rank_bm25** | Simple BM25 search in Python | [GitHub](https://github.com/dorianbrown/rank_bm25) |

---

## Decision: Recommended Approach

**Dual-path implementation: pgvector embeddings in proxy + AutoTool filter in Open WebUI.**

### Immediate (Phase 2a + 2b):
1. **Proxy**: Add pgvector-based semantic search to `generate_dynamic_openapi_filtered()` — reduces spec from all-user-tools to contextually-relevant subset
2. **Open WebUI**: Deploy AutoTool Filter (existing plugin) — reduces per-query tools to 3-10 most relevant

### Endgame (Phase 3):
3. **Proxy**: Implement Speakeasy-style meta-tools (`search_tools`, `describe_tools`, `call_tool`) — 96-99% token reduction, 100% success rate

### Why this approach:
1. Uses infrastructure we already have (pgvector in PostgreSQL)
2. Open WebUI's AutoTool Filter is a deploy-and-configure solution (exists today)
3. The proxy meta-tool pattern is the proven endgame (benchmarked at 400 tools)
4. Each phase builds on the previous one — no throwaway work
5. Requires no external framework adoption (pure FastAPI + pgvector + Open WebUI plugins)
6. Adds minimal latency (2-10ms for embedding search, 200-500ms for AutoTool LLM call)

### Reference implementations to adapt:
- `Portkey mcp-tool-filter` — embedding-based MCP tool filtering
- `ScaleMCP` — 5K MCP server tool retrieval with auto-sync
- `AutoTool Filter` — Open WebUI's existing per-query tool selection
- `Speakeasy Dynamic Toolsets` — meta-tool pattern documentation
