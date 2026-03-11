"""
listener.py — Real-time Slack Socket Mode listener for #bugs-and-feedback
Triggers the bug pipeline instantly when someone posts a message.
"""
import json
import os
import sys
import re
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

import loom_transcript
import extract_bugs
import basecamp_todos
import scan_slack

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../config/config.json")
PROCESSED_LOG = os.path.join(os.path.dirname(__file__), "../data/processed_messages.txt")


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def is_processed(ts):
    if not os.path.exists(PROCESSED_LOG):
        return False
    with open(PROCESSED_LOG, "r") as f:
        return ts in {line.strip() for line in f if line.strip()}


def mark_processed(ts):
    with open(PROCESSED_LOG, "a") as f:
        f.write(ts + "\n")


def save_report(cfg, bugs):
    output_dir = cfg["report_output_path"]
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    path = os.path.join(output_dir, f"{timestamp}.md")
    lines = [f"# Bug Report — {timestamp}\n"]
    for i, bug in enumerate(bugs, 1):
        lines.append(f"## {i}. {bug['title']}")
        lines.append(f"**Reporter:** {bug['reporter']}")
        lines.append(f"**Severity:** {bug['severity']}")
        lines.append(f"\n{bug['description']}\n")
        lines.append(f"**Source:** {bug['source_url']}\n")
    with open(path, "w") as f:
        f.write("\n".join(lines))
    print(f"  Report saved: {path}")


def process_message(cfg, event):
    """Process a single Slack message through the bug pipeline."""
    ts = event.get("ts", "")
    user_id = event.get("user", "")
    text = event.get("text", "")
    channel = event.get("channel", "")

    # Only process messages from our channel
    if channel != cfg["slack_channel_id"]:
        return

    # Skip bot messages, subtypes (joins, etc), already processed
    if event.get("subtype") or event.get("bot_id"):
        return
    if is_processed(ts):
        return

    reporter = scan_slack.resolve_username(user_id, cfg["slack_token"])
    print(f"\n{'='*50}")
    print(f"New message from {reporter} at {datetime.now().strftime('%H:%M:%S')}")
    print(f"  Text: {text[:100]}...")

    permalink = scan_slack.get_message_permalink(
        cfg["slack_token"], cfg["slack_channel_id"], ts
    )

    # Extract Loom URLs
    loom_urls = [word for word in text.split() if "loom.com/share/" in word]

    all_bugs = []

    if loom_urls:
        for url in loom_urls:
            print(f"  Fetching Loom transcript: {url}")
            transcript = loom_transcript.get_transcript(url, cfg.get("loom_api_key", ""))
            content = transcript if transcript else text
            bugs = extract_bugs.extract_bugs(
                content, reporter, permalink, loom_url=url,
                api_key=cfg["anthropic_api_key"]
            )
            print(f"  Extracted {len(bugs)} bug(s) from Loom.")
            all_bugs.extend(bugs)
    else:
        bugs = extract_bugs.extract_bugs(
            text, reporter, permalink, api_key=cfg["anthropic_api_key"]
        )
        print(f"  Extracted {len(bugs)} bug(s) from text.")
        all_bugs.extend(bugs)

    if all_bugs:
        # Reply to reporter
        basecamp_todos.post_reporter_reply(cfg, cfg["slack_channel_id"], ts, reporter)

        # Create Basecamp to-dos
        for bug in all_bugs:
            url = basecamp_todos.create_todo(bug, cfg)
            print(f"  Created: {bug['title']} ({bug['severity']}) → {url}")

        # Save report
        save_report(cfg, all_bugs)

        # Notify team
        basecamp_todos.notify_team(cfg, len(all_bugs), [reporter])
        print(f"  Team notified. {len(all_bugs)} bug(s) logged.")
    else:
        print("  No bugs extracted from this message.")

    mark_processed(ts)


def main():
    cfg = load_config()

    app_token = cfg.get("slack_app_token", "")
    bot_token = cfg["slack_token"]

    if not app_token:
        print("ERROR: slack_app_token not set in config.json")
        sys.exit(1)

    try:
        from slack_sdk.socket_mode import SocketModeClient
        from slack_sdk.socket_mode.request import SocketModeRequest
        from slack_sdk.socket_mode.response import SocketModeResponse
        from slack_sdk.web import WebClient
    except ImportError:
        print("Installing slack_sdk...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "slack_sdk"])
        from slack_sdk.socket_mode import SocketModeClient
        from slack_sdk.socket_mode.request import SocketModeRequest
        from slack_sdk.socket_mode.response import SocketModeResponse
        from slack_sdk.web import WebClient

    web_client = WebClient(token=bot_token)
    socket_client = SocketModeClient(app_token=app_token, web_client=web_client)

    def handle_event(client: SocketModeClient, req: SocketModeRequest):
        # Acknowledge immediately
        client.send_socket_mode_response(SocketModeResponse(envelope_id=req.envelope_id))

        if req.type == "events_api":
            event = req.payload.get("event", {})
            if event.get("type") == "message":
                try:
                    process_message(cfg, event)
                except Exception as e:
                    print(f"  ERROR processing message: {e}")

    socket_client.socket_mode_request_listeners.append(handle_event)

    print(f"Bug Tracker listening on #bugs-and-feedback...")
    print(f"Channel: {cfg['slack_channel_id']}")
    print(f"Press Ctrl+C to stop.\n")

    socket_client.connect()

    # Keep alive
    import time
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down.")
        socket_client.close()


if __name__ == "__main__":
    main()
