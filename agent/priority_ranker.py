from collections import Counter

import pandas as pd

from agent.action_item import action_item_to_display_dict


PRIORITY_SCORE = {
    "high": 3,
    "medium": 2,
    "low": 1,
}

SOURCE_SCORE = {
    "cashflow": 3,
    "invoice": 3,
    "model_anomaly": 2,
    "rule_anomaly": 2,
    "goal": 2,
    "clarification": 1,
    "summary": 1,
}

DEADLINE_SCORE = {
    "today": 3,
    "within 3 days": 2,
    "within 7 days": 1,
    "this month": 1,
    "this week": 1,
    "before the next review": 1,
}


def compute_action_rank_score(action_item: dict) -> int:
    """
    Compute a stable rank score for an action item.
    """
    item = action_item or {}
    priority_score = PRIORITY_SCORE.get(item.get("priority"), 2)
    source_score = SOURCE_SCORE.get(item.get("source"), 1)
    deadline_score = DEADLINE_SCORE.get(item.get("suggested_deadline"), 0)
    return priority_score * 10 + source_score * 3 + deadline_score


def rank_action_items(action_items: list[dict]) -> list[dict]:
    """
    Rank action items by priority, source and deadline.
    """
    ranked_items = []
    for item in action_items or []:
        copied = dict(item)
        copied["rank_score"] = compute_action_rank_score(copied)
        ranked_items.append(copied)
    return sorted(
        ranked_items,
        key=lambda item: (
            PRIORITY_SCORE.get(item.get("priority"), 2),
            item.get("rank_score", 0),
            item.get("action_id", ""),
        ),
        reverse=True,
    )


def filter_action_items(
    action_items: list[dict],
    priority=None,
    source=None,
    status=None,
) -> list[dict]:
    """
    Filter action items by priority, source and status.
    """
    filtered = list(action_items or [])
    if priority:
        filtered = [item for item in filtered if item.get("priority") == priority]
    if source:
        filtered = [item for item in filtered if item.get("source") == source]
    if status:
        filtered = [item for item in filtered if item.get("status") == status]
    return filtered


def summarize_action_items(action_items: list[dict]) -> dict:
    """
    Summarize action item counts.
    """
    items = list(action_items or [])
    priority_counts = Counter(item.get("priority", "medium") for item in items)
    source_counts = Counter(item.get("source", "summary") for item in items)
    return {
        "total": len(items),
        "high": priority_counts.get("high", 0),
        "medium": priority_counts.get("medium", 0),
        "low": priority_counts.get("low", 0),
        "by_source": dict(source_counts),
    }


def action_items_to_dataframe(action_items: list[dict]):
    """
    Convert action items to a pandas DataFrame for Streamlit display.
    """
    return pd.DataFrame(
        [action_item_to_display_dict(item) for item in action_items or []]
    )
