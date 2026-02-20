# Slack & Discord App Configuration Guide

**Last Updated:** 2026-02-20

This guide covers how to configure the Slack and Discord integrations for the AIUI platform. Both integrations use the `/aiui` slash command with subcommands: `ask`, `workflow`, `status`, `report`, `help`.

---

## Slack App Setup

### 1. Create or Configure the Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Select your existing app or click **Create New App** > **From scratch**
3. App Name: `AIUI Assistant`, Workspace: your workspace

### 2. Add Slash Command

1. In the left sidebar, click **Slash Commands**
2. Click **Create New Command**
3. Fill in:
   - **Command:** `/aiui`
   - **Request URL:** `https://ai-ui.coolestdomain.win/webhook/slack/commands`
   - **Short Description:** `AI assistant and workflow trigger`
   - **Usage Hint:** `[ask|workflow|status|report] [text]`
4. Click **Save**

### 3. Configure OAuth & Permissions

1. In the left sidebar, click **OAuth & Permissions**
2. Under **Scopes** > **Bot Token Scopes**, add:
   - `commands` (for slash commands)
   - `chat:write` (for posting messages to channels)
   - `chat:write.public` (for posting to channels the bot isn't in)
3. Click **Install to Workspace** (or **Reinstall** if updating)
4. Copy the **Bot User OAuth Token** (starts with `xoxb-`)

### 4. Get Signing Secret

1. In the left sidebar, click **Basic Information**
2. Under **App Credentials**, copy the **Signing Secret**

### 5. Choose a Report Channel

1. In Slack, right-click the channel where you want health reports posted
2. Click **View channel details**
3. Copy the **Channel ID** (at the bottom, starts with `C`)

### 6. Set Environment Variables on Server

```bash
ssh root@46.224.193.25 "cat >> /root/proxy-server/.env << 'EOF'
# Slack Integration
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_SIGNING_SECRET=your-signing-secret-here
REPORT_SLACK_CHANNEL=C0123456789
EOF"
```

### 7. Restart Webhook Handler

```bash
ssh root@46.224.193.25 "cd /root/proxy-server && docker compose -f docker-compose.unified.yml up -d --build webhook-handler"
```

### 8. Verify

Check logs for "Slack slash commands enabled":
```bash
ssh root@46.224.193.25 "docker logs webhook-handler --tail 10 2>&1"
```

Then test in Slack: `/aiui status`

---

## Discord App Setup

### 1. Create Discord Application

1. Go to [discord.com/developers/applications](https://discord.com/developers/applications)
2. Click **New Application**
3. Name: `AIUI Assistant`
4. Note the **Application ID** and **Public Key** from the General Information page

### 2. Create Bot

1. In the left sidebar, click **Bot**
2. Click **Add Bot** (if not already created)
3. Copy the **Bot Token** (click "Reset Token" if needed)
4. Under **Privileged Gateway Intents**, enable what you need (Message Content if applicable)

### 3. Set Interactions Endpoint

1. In the left sidebar, click **General Information**
2. Set **Interactions Endpoint URL** to:
   ```
   https://ai-ui.coolestdomain.win/webhook/discord
   ```
3. Discord will send a PING to verify — it should respond with PONG automatically
4. Click **Save Changes**

### 4. Add Bot to Server

1. In the left sidebar, click **OAuth2** > **URL Generator**
2. Select scopes: `bot`, `applications.commands`
3. Select bot permissions: `Send Messages`, `Use Slash Commands`
4. Copy the generated URL and open it in your browser
5. Select the server to add the bot to

### 5. Register the /aiui Slash Command

Run this once to register the command with Discord:

```bash
curl -X POST "https://discord.com/api/v10/applications/YOUR_APP_ID/commands" \
  -H "Authorization: Bot YOUR_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "aiui",
    "description": "AI assistant and workflow trigger",
    "options": [{
      "name": "command",
      "description": "What to do: ask, workflow, status, report, help",
      "type": 3,
      "required": true
    }]
  }'
```

Replace `YOUR_APP_ID` and `YOUR_BOT_TOKEN` with your actual values.

### 6. Set Environment Variables on Server

```bash
ssh root@46.224.193.25 "cat >> /root/proxy-server/.env << 'EOF'
# Discord Integration
DISCORD_APPLICATION_ID=your-application-id
DISCORD_PUBLIC_KEY=your-public-key
DISCORD_BOT_TOKEN=your-bot-token
EOF"
```

### 7. Restart Webhook Handler

```bash
ssh root@46.224.193.25 "cd /root/proxy-server && docker compose -f docker-compose.unified.yml up -d --build webhook-handler"
```

### 8. Verify

Check logs for "Discord slash commands enabled":
```bash
ssh root@46.224.193.25 "docker logs webhook-handler --tail 10 2>&1"
```

Then test in Discord: `/aiui command:status`

---

## Command Reference

| Command | Description | Example |
|---------|-------------|---------|
| `/aiui ask <question>` | Ask the AI a question | `/aiui ask what is MCP?` |
| `/aiui workflow <name>` | Trigger an n8n workflow | `/aiui workflow pr-review` |
| `/aiui status` | Check service health | `/aiui status` |
| `/aiui report` | Generate end-of-day report | `/aiui report` |
| `/aiui help` | Show available commands | `/aiui help` |

---

## Troubleshooting

- **503 "not configured"**: The bot token/signing secret env vars are not set. Check `.env` on the server.
- **401 "Invalid signature"**: The signing secret (Slack) or public key (Discord) doesn't match. Verify the values.
- **Slack command times out**: The webhook handler must ACK within 3 seconds. Check `docker logs webhook-handler` for errors.
- **Discord says "This interaction failed"**: The Ed25519 signature verification may be failing. Ensure `DISCORD_PUBLIC_KEY` is correct.
