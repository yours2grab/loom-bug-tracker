"""
scan_slack.py — Fetch unprocessed messages from #bugs-and-feedback
"""
import requests
import os
import time

PROCESSED_LOG = os.path.join(os.path.dirname(__file__), "../data/processed_messages.txt")

KNOWN_USERS = {
    "U0AC6GNQAS3": "Virgil",
    "U0ACKV7RVFY": "Vinod",
    "U0ACJJ8BR1B": "Victor",
    "U0AJTM6RL00": "Carlos",
}


def load_processed_timestamps():
    if not os.path.exists(PROCESSED_LOG):
        return set()
    with open(PROCESSED_LOG, "r") as f:
        return set(line.strip() for line in f if line.strip())


def resolve_username(user_id, token):
    known = KNOWN_USERS.get(user_id)
    if known:
        return known
    resp = requests.get(
        "https://slack.com/api/users.info",
        headers={"Authorization": f"Bearer {token}"},
        params={"user": user_id},
    )
    data = resp.json()
    if data.get("ok"):
        return data["user"]["profile"].get("display_name") or data["user"]["name"]
    return user_id


def get_unprocessed_messages(token, channel_id, lookback_hours=3.5):
    processed = load_processed_timestamps()
    oldest = str(time.time() - lookback_hours * 3600)
    messages = []
    cursor = None

    while True:
        params = {"channel": channel_id, "limit": 200, "oldest": oldest}
        if cursor:
            params["cursor"] = cursor

        resp = requests.get(
            "https://slack.com/api/conversations.history",
            headers={"Authorization": f"Bearer {token}"},
            params=params,
        )
        data = resp.json()

        if not data.get("ok"):
            raise RuntimeError(f"Slack API error: {data.get('error')}")

        for msg in data.get("messages", []):
            ts = msg.get("ts", "")
            if ts in processed:
                continue
            if msg.get("subtype"):
                continue  # skip bot messages, joins, etc.

            user_id = msg.get("user", "")
            text = msg.get("text", "")

            # Extract Loom URLs
            loom_urls = [
                word for word in text.split()
                if "loom.com/share/" in word
            ]

            messages.append({
                "ts": ts,
                "user_id": user_id,
                "reporter": resolve_username(user_id, token),
                "text": text,
                "loom_urls": loom_urls,
                "permalink": None,  # fetched later if needed
            })

        if data.get("response_metadata", {}).get("next_cursor"):
            cursor = data["response_metadata"]["next_cursor"]
        else:
            break

    return messages


def get_message_permalink(token, channel_id, ts):
    resp = requests.get(
        "https://slack.com/api/chat.getPermalink",
        headers={"Authorization": f"Bearer {token}"},
        params={"channel": channel_id, "message_ts": ts},
    )
    data = resp.json()
    return data.get("permalink", "")
