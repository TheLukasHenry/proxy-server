# Visualize Data Function Status

**Date:** January 23, 2026
**Status:** In Progress

## Summary

Two versions of Visualize Data function exist:

### 1. Custom Version (v0.2.1) - WORKING
- **Location:** Already installed in Open WebUI
- **ID:** `visualize_data`
- **How it works:** Extracts markdown tables from last assistant message, renders as Plotly.js charts
- **Pros:** Works out of the box, no API configuration needed
- **Cons:** Only works with markdown tables, doesn't use AI to analyze data

### 2. Community Version (Visualize Data R3) - REQUIRES SETUP
- **Source:** https://openwebui.com/f/saulcutter/visualize
- **Author:** Omar EL HACHIMI (revised by saulcutter)
- **How it works:** Uses LLM (Claude via Bedrock) to analyze conversation and generate appropriate charts
- **Requires:**
  - `OPENIA_KEY` - API key for OpenAI-compatible interface (e.g., LiteLLM)
  - `OPENIA_URL` - URL of OpenAI-compatible API server
  - Model: `bedrock/anthropic.claude-3-sonnet-20240229-v1:0` (hardcoded)
- **Pros:** Smart analysis, works with any data format
- **Cons:** Requires API configuration, external LLM calls

## Current Task

Trying to import the community version into Open WebUI.

### Steps Done:
1. Fixed custom v0.2.1 with DOM timing issue (chart now renders)
2. Tried "Import From Link" but it loaded HTML instead of Python code
3. Saved community version code to: `temp/visualize_data_r3.py`

### Next Steps:
1. Click "New Function" in Open WebUI
2. Paste the Python code from `temp/visualize_data_r3.py`
3. Set function ID: `visualize_data_r3`
4. Set function name: `Visualize Data R3`
5. Save the function
6. Configure the API valves (OPENIA_KEY, OPENIA_URL)

## Important Note

The community version will NOT work until API keys are configured. If Lukas doesn't have:
- An OpenAI-compatible API endpoint (like LiteLLM)
- Access to AWS Bedrock with Claude 3 Sonnet

Then the custom v0.2.1 version is the better choice for immediate use.

## Files Reference
- Custom version: `open-webui-functions/reporting/visualize_data_action.py`
- Community version: `temp/visualize_data_r3.py`
