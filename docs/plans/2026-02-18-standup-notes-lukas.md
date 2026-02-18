# Standup Notes — Lukas & Jacint

**Date:** 2026-02-18
**Source:** Two standup meetings (structured notes + voice transcript)

---

## Meeting 1: Automation Progress & Team Dynamics

### Meeting Purpose
Sync on automation progress and discuss team dynamics.

### Key Takeaways
- **Automation Progress:** Jacint's N8N workflow is near completion; Lukas praised the clean, self-directed integration into the admin portal and API gateway.
- **Team Fit:** Joner departed due to a mismatch with the team's self-managing culture, which prioritizes autonomy over step-by-step SOPs.

### Topics

#### Automation Progress & Next Steps
- Jacint's N8N workflow is near completion; only the webhook URL remains.
- **Praise:** Lukas commended the clean, self-directed integration into the admin portal and API gateway.
- **Next Task:** Research and build new automations.
- **Trigger Methods:** Explore different ways to trigger workflows.
- **Tool:** Investigate the N8N MCP server for AI-assisted workflow creation.
- **Inspiration:** Join the OpenWebUI Discord for community ideas.
- **Example Workflow:** Automate the "end of day" report by having an AI summarize daily work from a chat command.

### Next Steps
**Jacint:**
- Finalize the N8N workflow by adding the webhook URL.
- Document the automation architecture (API Gateway, Caddy, N8N) in the docs.
- Research and build new automations, exploring N8N MCP and the OpenWebUI Discord.

**Lukas:**
- Review Jacint's latest PRs.

### Action Items
- Research automation triggers; build more automations
- Review Jacint's latest PR re: architecture docs
- Join OpenWebUI Discord managers

---

## Meeting 2: AIUI Automation Progress & Next Steps

### Meeting Purpose
Reviewing AIUI automation progress and defining next steps.

### Key Takeaways
- **Webhooks are Live-Only:** AIUI webhooks (/webhook/) must be tested on the live server, not localhost, because they are designed for external triggers.
- **AI-Powered Workflow Generation:** The new N8N MCP server enables AIUI to build complex N8N workflows from natural language prompts, such as "document emails in Google Sheets."
- **Deployment Approved:** The new webhook and N8N MCP features are approved for deployment to the live server.
- **Next Trigger:** The next development focus is adding a slash mention trigger (e.g., /mention AIUI) from chat apps like Discord or Slack to initiate workflows.

### Topics

#### Webhook Implementation & Testing
- **Problem:** Initial confusion over testing the new webhook architecture, which directs traffic to the live server.
- **Clarification:** Webhooks (/webhook/) are designed for external triggers and must be tested live. This is standard for AIUI.
- **Current Triggers:** GitHub (e.g., Pull Request events), Other external events (e.g., mentions)
- **Significance:** This architecture enables AIUI to act as a central automation hub, reacting to events across different platforms.

#### N8N MCP Server Integration
- **New Feature:** An N8N MCP (Multi-Cloud Platform) server is integrated, allowing AIUI to generate N8N workflows from natural language.
- **Example Use Case:** A prompt like "document emails in Google Sheets" would trigger the MCP to build the corresponding N8N workflow.
- **Workflow Capabilities:**
  - Triggers: GitHub PRs, email subjects, etc.
  - Actions: Accessing code (via File System MCP), sending deployment notes, documenting in Google Drive.
- **Status:** Lukas confirmed this functionality works well in local tests.

### Next Steps
**Jacint:**
- Push the new webhook and N8N MCP features to the live server via a PR.
- Send updated environment variables (including BASE_URL and proxy settings) to Lukas via WhatsApp to enable local testing.

**Lukas:**
- Test the new features locally using the provided environment variables.

### Next Development Focus:
- Implement a slash mention trigger (e.g., /mention AIUI) from chat apps (Discord, Slack) to initiate workflows.
- Build example N8N workflows using the new MCP server to explore its capabilities.

### Action Items
- Push AIUI webhook changes to live; send PR to Lukas
- Send AIUI env vars to Lukas via WhatsApp (base URL, proxy); then Lukas tests locally

---

## Voice Transcript Highlights (Meeting 2)

Key quotes from Lukas:

> "I like that it's part of the AIUI project, the webhooks, and in there you can store whatever actions, whatever situations on the other websites would trigger some logic in here."

> "So right now, you can ask in AIUI to build you an N8N workflow, and locally, when you're running AIUI, it does that."

> "If you would ask it, like, whenever I get email that says this in subject line, make that as a trigger to document that email in Google Sheets... I think it should be able to build the N8N workflow in AIUI this way."

> "Next, I think it would be cool to have some mention... Discord, Slack, Google Chat... you do slash mention, whatever, AIUI, you would call it. And that thing would trigger the workflow here."

> "If you feel like building some N8N workflows with the MCP server, I think that would be fun too. Just saying what you like to automate and how."

> "Building N8N workflows straight from AI UI, that's pretty cool. And you have it connected already to the MCP servers. So theoretically, it should be able to use those as well in the workflows."

> "You should do something like, if you get the GitHub PR, it should be able to get the code with file systems and send some file of updated deployment notes and document updated."
