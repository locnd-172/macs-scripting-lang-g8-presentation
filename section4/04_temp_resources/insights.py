"""Fake LLM analysis and a fake database. Neither of them needs any files."""

from media_tools import ToolError

saved = {}  # post id -> insights


def analyze(post_id, transcript):
    if post_id == "llm-timeout":
        raise ToolError("LLM request timed out")
    return {"sentiment": "positive", "topics": ["product launch"]}


def save_insights(post_id, insights):
    if post_id == "db-down":
        raise ToolError("database unavailable")
    saved[post_id] = insights
