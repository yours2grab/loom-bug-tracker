"""
loom_transcript.py — Pull transcript from any public Loom share URL.

No API key needed. Works for any video (including beta testers' own accounts).

Strategy:
1. Fetch the Loom share page
2. Parse window.__APOLLO_STATE__ (embedded JSON)
3. Find VideoTranscriptDetails → source_url (signed CDN link)
4. Fetch the transcript JSON and join phrases[].value
"""
import re
import json
import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
}


def extract_video_id(loom_url):
    match = re.search(r"loom\.com/share/([a-f0-9]+)", loom_url)
    if not match:
        raise ValueError(f"Could not extract Loom video ID from: {loom_url}")
    return match.group(1)


def get_transcript(loom_url, api_key=None):
    """
    Fetch the full transcript for any public Loom share URL.
    Returns plain text string, or None if transcript is unavailable.
    api_key is unused — kept for interface compatibility.
    """
    video_id = extract_video_id(loom_url)

    # Step 1: Fetch the share page
    resp = requests.get(
        f"https://www.loom.com/share/{video_id}",
        headers=HEADERS,
        timeout=15,
    )
    if resp.status_code != 200:
        print(f"  Loom share page returned {resp.status_code}")
        return None

    # Step 2: Extract window.__APOLLO_STATE__
    match = re.search(
        r"window\.__APOLLO_STATE__\s*=\s*(\{.*)",
        resp.text,
        re.DOTALL,
    )
    if not match:
        print("  Could not find __APOLLO_STATE__ in Loom page.")
        return None

    try:
        apollo, _ = json.JSONDecoder().raw_decode(match.group(1))
    except json.JSONDecodeError as e:
        print(f"  Failed to parse Apollo state: {e}")
        return None

    # Step 3: Find VideoTranscriptDetails key and get source_url
    source_url = None
    for key, val in apollo.items():
        if key.startswith("VideoTranscriptDetails:") and isinstance(val, dict):
            source_url = val.get("source_url")
            if source_url:
                break

    if not source_url:
        print("  No transcript source_url found (video may not have captions).")
        return None

    # Step 4: Fetch the transcript JSON from CDN
    tr_resp = requests.get(source_url, timeout=15)
    if tr_resp.status_code != 200:
        print(f"  Transcript CDN returned {tr_resp.status_code}")
        return None

    tr_data = tr_resp.json()
    phrases = tr_data.get("phrases", [])
    if not phrases:
        print("  Transcript JSON has no phrases.")
        return None

    return " ".join(p["value"] for p in phrases if p.get("value"))
