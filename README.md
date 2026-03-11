# Loom Bug Tracker

A Python pipeline that automatically scans Slack for bug reports, extracts bugs using Claude, creates Basecamp to-dos, and notifies the team. Designed to run hourly via cron or Claude Code skill.

## What It Does

1. Scans `#bugs-and-feedback` Slack channel for unprocessed messages
2. Pulls Loom transcripts from any Loom URLs found in messages
3. Extracts bugs using Claude AI (title, description, reporter, severity)
4. Creates one Basecamp to-do per bug, assigned to Vinod and Virgil
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
| `scripts/main.py` | Orchestrator. Runs the full pipeline end-to-end. |
| `scripts/scan_slack.py` | Reads `#bugs-and-feedback`, filters out processed messages, extracts Loom URLs. |
| `scripts/loom_transcript.py` | Fetches Loom video transcripts from public share pages. |
| `scripts/extract_bugs.py` | Sends message/transcript to Claude API. Returns structured bugs with title, description, reporter, severity (Critical/High/Medium/Low). |
| `scripts/basecamp_todos.py` | Creates Basecamp to-dos, posts thread replies to reporters, DMs team summary. |

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
- `slack_channel_id` — The `#bugs-and-feedback` channel ID
- `slack_virgil_id`, `slack_vinod_id`, `slack_victor_id` — Slack user IDs for DM notifications
- `basecamp_account_id`, `basecamp_project_id`, `basecamp_todolist_id` — Basecamp project details
- `basecamp_oauth_token` — Basecamp OAuth token
- `basecamp_vinod_id`, `basecamp_virgil_id` — Basecamp person IDs for to-do assignment
- `anthropic_api_key` — Claude API key for bug extraction
- `report_output_path` — Local path for markdown bug reports

### 3. Run

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
