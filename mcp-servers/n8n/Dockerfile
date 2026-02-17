# mcp-servers/n8n/Dockerfile
# n8n MCP Server with mcpo HTTP wrapper
# AI-driven n8n workflow creation, management, and execution (20 tools)
# Source: https://github.com/czlonkowski/n8n-mcp
FROM node:20-slim

RUN apt-get update && apt-get install -y python3 python3-pip curl --no-install-recommends \
    && pip3 install --break-system-packages mcpo \
    && npm install -g n8n-mcp \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

EXPOSE 8000

CMD ["sh", "-c", "mcpo --host 0.0.0.0 --port 8000 --api-key \"$MCP_API_KEY\" -- npx n8n-mcp"]
