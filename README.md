# Loom Bug Tracker

A Python pipeline that automatically detects bug reports in Slack, extracts bugs using Claude, creates Basecamp to-dos, and notifies the team. Supports both real-time listening (Socket Mode) and manual/scheduled runs.

## What It Does

1. Scans `#bugs-and-feedback` Slack channel for unprocessed messages
2. Pulls Loom transcripts from any Loom URLs found in messages
3. Extracts bugs using Claude AI (title, description, reporter, severity)
4. Creates one Basecamp to-do per bug, assigned to Virgil, Vinod, and Victor
5. Replies to the original reporter in-thread: "Got it, logged in Basecamp"
6. DMs Virgil, Vinod, and Victor with a run summary
7. Saves a markdown report to the bug reports folder
8. Logs processed message timestamps to avoid duplicates

If there are no new messages, it exits silently.

## Pipeline Architecture

```
Slack #bugs-and-feedback
        │
        ▼
   scan_slack.py ──── Reads unprocessed messages, extracts Loom URLs
        │
        ▼
 loom_transcript.py ── Scrapes transcript from Loom share page
        │
        ▼
  extract_bugs.py ──── Sends content to Claude, extracts structured bugs
        │
        ▼
 basecamp_todos.py ─── Creates to-dos, replies to reporter, DMs team
        │
        ▼
     main.py ────────── Orchestrator, saves report, logs processed messages
```

## Scripts

| File | Purpose |
|------|---------|
| `scripts/listener.py` | **Real-time listener.** Connects via Slack Socket Mode, processes messages instantly when posted. Recommended for production use. |
| `scripts/main.py` | **Batch orchestrator.** Runs the full pipeline on-demand (scans all unprocessed messages). Use for manual/scheduled runs. |
| `scripts/scan_slack.py` | Reads `#bugs-and-feedback`, filters out processed messages, extracts Loom URLs. |
| `scripts/loom_transcript.py` | Fetches Loom video transcripts from public share pages. |
| `scripts/extract_bugs.py` | Sends message/transcript to Claude API. Returns structured bugs with title, description, reporter, severity (Critical/High/Medium/Low). |
| `scripts/basecamp_todos.py` | Creates Basecamp to-dos (assigned to Virgil, Vinod, Victor), posts thread replies to reporters, DMs team summary. |

## Setup

### 1. Install dependencies

```bash
pip install requests anthropic
```

### 2. Configure credentials

Copy the template and fill in your values:

```bash
cp config/config.template.json config/config.json
```

Required fields:
- `slack_token` — Slack bot token with channels:history, chat:write, users:read scopes
- `slack_app_token` — Slack app-level token (xapp-) for Socket Mode
- `slack_channel_id` — The `#bugs-and-feedback` channel ID
- `slack_virgil_id`, `slack_vinod_id`, `slack_victor_id` — Slack user IDs for DM notifications
- `basecamp_account_id`, `basecamp_project_id`, `basecamp_todolist_id` — Basecamp project details
- `basecamp_oauth_token` — Basecamp OAuth token
- `basecamp_vinod_id`, `basecamp_virgil_id`, `basecamp_victor_id` — Basecamp person IDs for to-do assignment
- `anthropic_api_key` — Claude API key for bug extraction
- `report_output_path` — Local path for markdown bug reports

### 3. Run (Real-time Listener)

```bash
cd ~/.claude/skills/loom-bug-tracker
pip install slack_sdk
python scripts/listener.py
```

This connects via Socket Mode and processes messages instantly. Requires `message.channels` event subscription enabled in your Slack app and Socket Mode turned on.

**Run as macOS background service:**

```bash
# Copy the Launch Agent plist to ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.sucana.bug-tracker.plist
```

### 3b. Run (Manual/Batch)

```bash
cd ~/.claude/skills/loom-bug-tracker && python scripts/main.py
```

Or trigger via Claude Code skill:
```
/loom-bug-tracker
```

## Duplicate Prevention

Processed message timestamps are logged in `data/processed_messages.txt`. Each Slack message is only processed once. The file persists across runs.

## Output

Each run generates a markdown report:

```
# Bug Report — 2026-03-07-14

## 1. Login button unresponsive on mobile
**Reporter:** Victor
**Severity:** High

Tapping the login button on iOS Safari does nothing...

**Source:** https://slack.com/archives/...
```

Reports save to the configured `report_output_path`.

## Install as Claude Code Skill

Drop the entire `loom-bug-tracker/` folder into `~/.claude/skills/`.

## Credits

Built by Virgil Brewster at [Sucana](https://sucana.ai) — AI-powered tools for B2B SaaS teams.
