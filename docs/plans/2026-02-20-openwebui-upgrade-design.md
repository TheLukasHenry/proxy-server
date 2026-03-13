# Open WebUI v0.8.3 Upgrade + Post-Upgrade Setup

**Date:** 2026-02-20
**Status:** Approved
**Priority:** HIGH — gatekeeper for Skills, Channels, Analytics

---

## Context

The AIUI platform currently runs Open WebUI v0.7.2. Lukas's Phase 2 vision requires Skills (teaching AI when/how to use MCP tools), Channels (built-in team chat with @model mentions), and Analytics. All of these were introduced in v0.8.0+.

There are no intermediate versions between v0.7.2 and v0.8.0 — it's a direct jump.

---

## What v0.8.3 Unlocks

| Feature | What It Does | Value |
|---------|-------------|-------|
| **Skills** | Reusable AI instruction sets injected before LLM processing | Teaches AI WHEN/HOW to use MCP tools without hand-holding |
| **Channels** | Persistent topic-based chat rooms (Slack/Discord-like) | Non-technical users get familiar chat interface with @model mentions |
| **Analytics Dashboard** | Model usage, tokens, user activity | Built-in admin monitoring |
| **Open Responses Protocol** | Extended thinking, streaming reasoning | Better AI reasoning |
| **Message Queuing** | Keep typing while model generates | UX improvement |
| **Prompt Version Control** | History, comparison, rollback | Better prompt management |
| **MCP Improvements** | Custom SSL certs, user identity forwarding | Better multi-tenant MCP |
| **Per-model tool toggles** | Enable/disable tools per model | Finer control |
| **34% faster auth** | Authentication speed improvement | Performance |

---

## Breaking Changes

- **Database schema changes** — `chat_message` table migration can be slow
- Multi-worker deployments must update ALL instances simultaneously
- Disabled features now return 403 via API (could affect webhook-handler)
- Admin evaluations page moved to `/admin/evaluations/feedback`

---

## Design — 3 Phases

### Phase 1: Backup & Upgrade (~1-2 hours)

1. SSH into server
2. Stop all services
3. Backup PostgreSQL (SQL dump + volume tarball)
4. Backup Open WebUI data volume
5. Pin image tag from `:main` to `:v0.8.3` in docker-compose.unified.yml
6. Start services, monitor migration logs
7. Verify health endpoints, MCP tools, pipe functions survive

### Phase 2: Post-Upgrade Verification (~30-60 min)

1. Clear browser cache
2. Enable Channels feature in admin settings
3. Verify Skills UI at `/workspace/skills`
4. Check Analytics dashboard
5. Re-install pipe functions if needed (webhook_automation, reporting tools)
6. Test end-to-end: chat with MCP tools, `/aiui report` via webhook

### Phase 3: Initial Skills & Channels Setup (~2-4 hours)

1. Create 3 starter Skills:
   - **PR Security Review** — teaches AI to fetch PR data + run code quality analysis
   - **Daily Report Builder** — teaches AI to gather GitHub + n8n + health data
   - **Project Status** — teaches AI to check GitHub issues + ClickUp tasks
2. Create 2 starter Channels:
   - **#general** — team discussion with `@gpt-5` enabled
   - **#dev-notifications** — webhook channel for CI/CD alerts
3. Configure channel webhooks for GitHub push notifications

---

## Rollback Strategy

If upgrade fails:
1. Stop services
2. Restore PostgreSQL from SQL dump
3. Restore Open WebUI volume from tarball
4. Revert image tag to `v0.7.2` (or old `:main` digest)
5. Restart

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| DB migration slow (chat_message table) | Do during low-usage hours, monitor logs |
| Pipe functions break after schema change | Re-install via existing scripts (`install_webhook_pipe.py`) |
| v0.8.3 changes API response format | Test webhook-handler integration after upgrade |
| Channels feature is beta | Start with just 2 channels, expand if stable |
| Skills can't wrap MCP directly | Skills inject instructions (context), MCP tools handle execution — this still achieves Lukas's goal |

---

## Existing Pipe Functions to Verify Post-Upgrade

| Function | Type | File |
|----------|------|------|
| `webhook_automation.webhook-automation` | Pipe | `open-webui-functions/webhook_pipe.py` |
| Excel Creator | Tool | `open-webui-functions/reporting/excel_creator.py` |
| Executive Dashboard | Tool | `open-webui-functions/reporting/executive_dashboard.py` |
| Visualize Data | Action | `open-webui-functions/reporting/visualize_data_action.py` |
| MCP Proxy Bridge | Tool | `open-webui-functions/mcp_proxy_bridge.py` |

---

## Post-Upgrade: Skill Design Examples

**PR Security Review Skill:**
```
When asked about PR security or code review:
1. Use `github_get_pull_request` to fetch PR details (title, description, changed files)
2. Use `github_get_pull_request_files` to get the actual diff
3. Analyze the diff for: SQL injection, XSS, hardcoded secrets, insecure dependencies
4. If SonarQube is available, use `sonarqube_get_issues` for automated findings
5. Present findings in a structured format with severity ratings
```

**Daily Report Builder Skill:**
```
When asked for a daily report or status update:
1. Use `github_list_commits` for today's commits on the configured repo
2. Use `n8n_list_workflows` to check automation status
3. Use health check endpoints to verify service status
4. Summarize findings: what was built, what's running, what needs attention
5. If asked for a spreadsheet, use `excel_create_spreadsheet` to generate a downloadable file
```

---

## Success Criteria

- [ ] Open WebUI responds on v0.8.3
- [ ] All existing chats preserved
- [ ] MCP Proxy tools still work (test in chat)
- [ ] Webhook automation pipe function works
- [ ] Skills UI accessible at `/workspace/skills`
- [ ] Channels feature toggleable in admin settings
- [ ] Analytics dashboard visible in admin panel
- [ ] At least 1 Skill created and tested
- [ ] At least 1 Channel created with @model mention working
