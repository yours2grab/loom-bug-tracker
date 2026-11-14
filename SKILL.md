---
name: loom-bug-tracker
description: Hourly bug tracker. Scans #bugs-and-feedback in Slack, pulls Loom transcripts, extracts bugs with Claude, creates Basecamp to-dos assigned to Vinod and Virgil, notifies the team via Slack DM.
---

# Loom Bug Tracker

Run the full bug tracking pipeline by executing:

```bash
cd ~/.claude/skills/loom-bug-tracker && python scripts/main.py
```

The script will:
1. Scan #bugs-and-feedback for unprocessed Slack messages
2. Pull Loom transcripts via Loom API (for any Loom URLs found)
3. Extract bugs using Claude — title, description, reporter, severity (Critical/High/Medium/Low)
4. Create one Basecamp to-do per bug, assigned to Vinod and Virgil
5. Thread reply to the original reporter: "Got it — logged in Basecamp. We're on it. 🐛"
6. DM Virgil, Vinod, and Victor with a run summary
7. Save a markdown report to Product/Bug Reports/
8. Log processed message timestamps to avoid duplicates

If there are no new messages, it exits silently.

## Config

All credentials live in `config/config.json`. Fill in all fields before running.

## Required packages

```bash
pip install requests anthropic
```
