"""
main.py — Loom Bug Tracker orchestrator
Runs the full pipeline: scan Slack → extract bugs → create Basecamp to-dos → notify
"""
import json
import os
import sys
from datetime import datetime

# Add scripts dir to path
sys.path.insert(0, os.path.dirname(__file__))

import scan_slack
import loom_transcript
import extract_bugs
import basecamp_todos

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../config/config.json")
PROCESSED_LOG = os.path.join(os.path.dirname(__file__), "../data/processed_messages.txt")


def load_config():
    with open(CONFIG_PATH) as f:
        cfg = json.load(f)
    missing = [k for k, v in cfg.items() if not v and k not in ("report_output_path", "loom_api_key")]
    if missing:
        raise ValueError(f"Missing config values: {', '.join(missing)}")
    return cfg


def save_report(cfg, all_bugs, messages):
    output_dir = cfg["report_output_path"]
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d-%H")
    path = os.path.join(output_dir, f"{timestamp}.md")

    lines = [f"# Bug Report — {timestamp}\n"]
    for i, bug in enumerate(all_bugs, 1):
        lines.append(f"## {i}. {bug['title']}")
        lines.append(f"**Reporter:** {bug['reporter']}")
        lines.append(f"**Severity:** {bug['severity']}")
        lines.append(f"\n{bug['description']}\n")
        lines.append(f"**Source:** {bug['source_url']}\n")

    with open(path, "w") as f:
        f.write("\n".join(lines))

    print(f"Report saved: {path}")


def mark_processed(timestamps):
    with open(PROCESSED_LOG, "a") as f:
        for ts in timestamps:
            f.write(ts + "\n")


def run():
    print("Loading config...")
    cfg = load_config()

    print("Scanning #bugs-and-feedback...")
    messages = scan_slack.get_unprocessed_messages(
        cfg["slack_token"], cfg["slack_channel_id"]
    )

    if not messages:
        print("No new messages. Done.")
        return

    print(f"Found {len(messages)} unprocessed message(s).")

    all_bugs = []
    processed_ts = []
    reporters_this_run = []

    for msg in messages:
        ts = msg["ts"]
        reporter = msg["reporter"]
        text = msg["text"]
        loom_urls = msg["loom_urls"]

        print(f"\nProcessing message from {reporter} (ts={ts})")

        # Get permalink for source reference
        permalink = scan_slack.get_message_permalink(
            cfg["slack_token"], cfg["slack_channel_id"], ts
        )

        if loom_urls:
            for url in loom_urls:
                print(f"  Fetching Loom transcript: {url}")
                transcript = loom_transcript.get_transcript(url, cfg["loom_api_key"])
                if transcript:
                    content = transcript
                    source = url
                else:
                    print(f"  Transcript unavailable, using message text.")
                    content = text
                    source = permalink

                bugs = extract_bugs.extract_bugs(content, reporter, permalink, loom_url=url, api_key=cfg["anthropic_api_key"])
                print(f"  Extracted {len(bugs)} bug(s) from Loom.")
                all_bugs.extend(bugs)
        else:
            bugs = extract_bugs.extract_bugs(text, reporter, permalink, api_key=cfg["anthropic_api_key"])
            print(f"  Extracted {len(bugs)} bug(s) from text.")
            all_bugs.extend(bugs)

        if bugs:
            reporters_this_run.append(reporter)
            # Reply to reporter in thread
            basecamp_todos.post_reporter_reply(
                cfg, cfg["slack_channel_id"], ts, reporter
            )

        processed_ts.append(ts)

    if not all_bugs:
        print("\nNo bugs extracted. Done.")
        mark_processed(processed_ts)
        return

    print(f"\nCreating {len(all_bugs)} Basecamp to-do(s)...")
    for bug in all_bugs:
        url = basecamp_todos.create_todo(bug, cfg)
        print(f"  Created: {bug['title']} ({bug['severity']}) → {url}")

    print("Saving report...")
    save_report(cfg, all_bugs, messages)

    print("Notifying team via Slack DM...")
    basecamp_todos.notify_team(cfg, len(all_bugs), reporters_this_run)

    mark_processed(processed_ts)
    print(f"\nDone. {len(all_bugs)} bug(s) logged.")


if __name__ == "__main__":
    run()
