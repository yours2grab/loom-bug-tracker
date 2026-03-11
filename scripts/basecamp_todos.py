"""
basecamp_todos.py — Create Basecamp to-dos and send Slack notifications
"""
import requests


# Basecamp

def create_todo(bug, config):
    """Create one Basecamp to-do for a single bug object."""
    account_id = config["basecamp_account_id"]
    project_id = config["basecamp_project_id"]
    todolist_id = config["basecamp_todolist_id"]
    token = config["basecamp_oauth_token"]
    vinod_id = config["basecamp_vinod_id"]
    virgil_id = config["basecamp_virgil_id"]

    title = f"Bug: {bug['title']}"
    description = (
        f"<strong>Reporter:</strong> {bug['reporter']}<br>"
        f"<strong>Severity:</strong> {bug['severity']}<br><br>"
        f"<strong>Details:</strong><br>{bug['description']}<br><br>"
        f"<strong>Source:</strong> <a href='{bug['source_url']}'>{bug['source_url']}</a>"
    )

    resp = requests.post(
        f"https://3.basecampapi.com/{account_id}/buckets/{project_id}/todolists/{todolist_id}/todos.json",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "LoomBugTracker (support@sucana.ai)",
        },
        json={
            "content": title,
            "description": description,
            "assignee_ids": [int(vinod_id), int(virgil_id)],
        },
    )
    resp.raise_for_status()
    return resp.json().get("url", "")


# Slack

def post_reporter_reply(config, channel_id, thread_ts, reporter):
    """Reply to the reporter's original Slack message."""
    _slack_post(config["slack_token"], {
        "channel": channel_id,
        "thread_ts": thread_ts,
        "text": f"Got it {reporter} — logged in Basecamp. We're on it. 🐛",
    })


def send_dm(config, user_id, text):
    """Open a DM and send a message."""
    token = config["slack_token"]

    # Open DM channel
    resp = requests.post(
        "https://slack.com/api/conversations.open",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"users": user_id},
    )
    dm_channel = resp.json().get("channel", {}).get("id")
    if not dm_channel:
        return

    _slack_post(token, {"channel": dm_channel, "text": text})


def notify_team(config, bug_count, reporters):
    """DM Virgil, Vinod, and Victor with a run summary."""
    reporter_list = ", ".join(set(reporters))
    text = f"🐛 {bug_count} new bug{'s' if bug_count != 1 else ''} logged from {reporter_list} — Basecamp updated."

    for uid in [config["slack_virgil_id"], config["slack_vinod_id"], config["slack_victor_id"]]:
        send_dm(config, uid, text)


def _slack_post(token, payload):
    requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=payload,
    )
