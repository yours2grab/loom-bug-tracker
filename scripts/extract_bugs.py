"""
extract_bugs.py — Use Claude to extract structured bugs from content
"""
import json
import anthropic

SEVERITY_RULES = """
- Critical: App is unusable, blocks all users
- High: App crashes or data is wrong
- Medium: Feature is broken but app still works
- Low: UI issue, visual glitch, or typo
"""

EXTRACTION_PROMPT = """You are a bug extraction assistant for Sucana, a B2B SaaS analytics platform.

Extract all distinct bugs from the following content. Return a JSON array of bug objects.

Severity rules:
{severity_rules}

Rules:
- One object per distinct bug. If the content describes 3 bugs, return 3 objects.
- Title: concise, under 10 words, describes the specific problem.
- Description: 2-4 sentences. What happened, what was expected, any visible impact.
- If no clear bug is described, return an empty array [].

Return ONLY valid JSON — no markdown, no explanation. Format:
[
  {{
    "title": "...",
    "description": "...",
    "severity": "Critical|High|Medium|Low"
  }}
]

Content to analyze:
---
{content}
---

Reporter: {reporter}
"""


def extract_bugs(content, reporter, source_url, loom_url=None, api_key=None):
    """
    Extract structured bugs from transcript or plain text.
    Returns list of bug dicts with: title, description, reporter, severity, source_url
    """
    client = anthropic.Anthropic(api_key=api_key)

    prompt = EXTRACTION_PROMPT.format(
        severity_rules=SEVERITY_RULES,
        content=content,
        reporter=reporter,
    )

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()

    try:
        bugs = json.loads(raw)
    except json.JSONDecodeError:
        # Try to salvage if Claude added markdown fences
        import re
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if match:
            bugs = json.loads(match.group(0))
        else:
            bugs = []

    # Attach metadata
    for bug in bugs:
        bug["reporter"] = reporter
        bug["source_url"] = loom_url or source_url

    return bugs
