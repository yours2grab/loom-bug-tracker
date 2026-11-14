"""
basecamp_todos.py — Create Basecamp to-dos and send Slack notifications
"""
import random
import requests

REPLY_MESSAGES = [
    "We've got you {reporter}. Thank you for sharing. As we speak the dev team is firing up their computers. House tunes in the background. And we're on it. Keep an eye on your Slack inbox. 🐛",
    "Heard you loud and clear {reporter}. The team just dropped everything. Coffee poured, terminals open. We're hunting this one down. 🎯",
    "On it {reporter}. Bug logged, team notified, and someone already said 'I think I know what this is.' Stay tuned. 🔧",
    "Thanks for flagging this {reporter}. The dev team is already in the zone. Lo-fi beats playing, code editors glowing. We'll get back to you. 🎵",
    "Appreciate you {reporter}. This just hit the top of the queue. Three engineers, one bug. It doesn't stand a chance. 💪",
    "Got it {reporter}. The team is locking in right now. Headphones on, distractions off. We're coming for this bug. 🎧",
    "You're the best {reporter}. Bug captured, team updated, and we're already talking fixes. Hang tight. ⚡",
    "Noted {reporter}. We just put this bug on the wall of shame. It won't be there long because we're about to squash it. 🪲",
    "Thank you {reporter}. The dev cave just lit up. Monitors on, snacks out, and we're diving in. You'll hear from us soon. 🖥️",
    "Loud and clear {reporter}. This bug just made the hit list. The team is suiting up. Consider it handled. 🎯",
    "Big thanks {reporter}. We've logged it and the team is already on the case. Think detectives but with better keyboards. 🕵️",
    "We see you {reporter}. Bug is in the system, team is in motion. Someone just cracked their knuckles. This is happening. 👊",
    "Captured {reporter}. The team just went into fix mode. Music up, code flying. We'll circle back when it's done. 🚀",
    "You're a legend {reporter}. Bug logged and the whole crew is on it. We don't let these things slide. Watch this space. 🔥",
    "Thanks for the heads up {reporter}. Dev team is assembling as we speak. This bug picked the wrong day to show up. ⚔️",
    "Received {reporter}. Three devs just opened the same file at the same time. That's how you know we're serious. Consider it priority one. 🏆",
    "Appreciate the report {reporter}. The team just went quiet, which means they're focused. That's a good sign for us, bad sign for this bug. 🤫",
    "On the radar {reporter}. The dev team just switched from building features to hunting bugs. Yours is first in line. 🎪",
    "Thank you {reporter}. Someone on the team just said 'leave it to me' with way too much confidence. We love that energy. We're on it. 😤",
    "Locked in {reporter}. Bug is logged, team is briefed, and the fix is already being discussed. You'll be the first to know. 📬",
    "We hear you {reporter}. The team just entered what we call 'bug mode.' It involves a lot of squinting at screens and mumbling. Progress is being made. 🧐",
    "Solid catch {reporter}. This one is now front and center. The team is treating it like a puzzle and they love puzzles. 🧩",
    "Thanks {reporter}. The dev team just collectively sighed and then immediately got to work. That's our process. We're fixing it. 😅",
    "Right on {reporter}. Bug documented, team mobilized, and there's a whiteboard with your bug's name on it. Literally. 📝",
    "Copy that {reporter}. The team is in the lab right now. Whiteboards full, energy high. This bug's days are numbered. 🧪",
]


# Basecamp

def create_todo(bug, config):
    """Create one Basecamp to-do for a single bug object."""
    account_id = config["basecamp_account_id"]
    project_id = config["basecamp_project_id"]
    todolist_id = config["basecamp_todolist_id"]
    token = config["basecamp_oauth_token"]
    vinod_id = config["basecamp_vinod_id"]
    virgil_id = config["basecamp_virgil_id"]
    victor_id = config["basecamp_victor_id"]

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
            "User-Agent": "LoomBugTracker (virgil@virgilbrewster.com)",
        },
        json={
            "content": title,
            "description": description,
            "assignee_ids": [int(vinod_id), int(virgil_id), int(victor_id)],
        },
    )
    resp.raise_for_status()
    return resp.json().get("url", "")


# Slack

def post_reporter_reply(config, channel_id, thread_ts, reporter):
    """Reply to the reporter's original Slack message."""
    msg = random.choice(REPLY_MESSAGES).format(reporter=reporter)
    _slack_post(config["slack_token"], {
        "channel": channel_id,
        "thread_ts": thread_ts,
        "text": msg,
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


def forward_message(config, reporter, text, permalink):
    """Forward any non-bug message to the team so nothing gets missed."""
    preview = text[:200] + ("..." if len(text) > 200 else "")
    msg = f"💬 New message in #bugs-and-feedback from {reporter}:\n\n>{preview}\n\nNo bug extracted. Review it here: {permalink}"

    for uid in [config["slack_virgil_id"], config["slack_vinod_id"], config["slack_victor_id"]]:
        send_dm(config, uid, msg)


def _slack_post(token, payload):
    requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=payload,
    )
