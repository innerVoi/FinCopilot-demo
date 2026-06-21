from collections import Counter


VALID_ACTION_STATUSES = [
    "pending",
    "in_progress",
    "verified_normal",
    "needs_follow_up",
    "done",
    "ignored",
]

CLOSED_STATUSES = {"verified_normal", "done", "ignored"}
ACTIVE_STATUSES = {"pending", "in_progress", "needs_follow_up"}
PRIORITY_ORDER = {"high": 3, "medium": 2, "low": 1}


def normalize_status(status: str | None) -> str:
    """
    Normalize an action status.
    """
    value = str(status or "").strip().lower()
    if value in VALID_ACTION_STATUSES:
        return value
    return "pending"


def is_closed_status(status: str | None) -> bool:
    """
    Return True if status is closed.
    """
    return normalize_status(status) in CLOSED_STATUSES


def is_active_status(status: str | None) -> bool:
    """
    Return True if status still needs work.
    """
    return normalize_status(status) in ACTIVE_STATUSES


def summarize_progress(action_items: list[dict]) -> dict:
    """
    Summarize action item progress.
    """
    items = list(action_items or [])
    status_counts = Counter(normalize_status(item.get("status")) for item in items)
    active_items = [item for item in items if is_active_status(item.get("status"))]
    closed_items = [item for item in items if is_closed_status(item.get("status"))]
    high_priority_active_count = sum(
        1 for item in active_items if item.get("priority") == "high"
    )
    by_priority = Counter(item.get("priority", "medium") for item in items)
    by_source = Counter(item.get("source", "summary") for item in items)
    total = len(items)
    return {
        "total": total,
        "pending": status_counts.get("pending", 0),
        "in_progress": status_counts.get("in_progress", 0),
        "verified_normal": status_counts.get("verified_normal", 0),
        "needs_follow_up": status_counts.get("needs_follow_up", 0),
        "done": status_counts.get("done", 0),
        "ignored": status_counts.get("ignored", 0),
        "active_count": len(active_items),
        "closed_count": len(closed_items),
        "completion_rate": len(closed_items) / total if total else 0.0,
        "high_priority_active_count": high_priority_active_count,
        "by_priority": dict(by_priority),
        "by_source": dict(by_source),
    }


def filter_actions_by_status(
    action_items: list[dict],
    status: str | None = None,
) -> list[dict]:
    """
    Filter action items by status.
    """
    if not status:
        return list(action_items or [])
    normalized_status = normalize_status(status)
    return [
        item
        for item in action_items or []
        if normalize_status(item.get("status")) == normalized_status
    ]


def get_top_active_actions(action_items: list[dict], n: int = 3) -> list[dict]:
    """
    Return top active actions sorted by priority and rank score.
    """
    active_items = [
        item for item in action_items or [] if is_active_status(item.get("status"))
    ]
    return sorted(
        active_items,
        key=lambda item: (
            PRIORITY_ORDER.get(item.get("priority"), 2),
            item.get("rank_score", 0),
        ),
        reverse=True,
    )[:n]


def get_recent_progress_events(agent_state: dict | None, limit: int = 10) -> list[dict]:
    """
    Return recent progress events from Agent state.
    """
    history = list((agent_state or {}).get("progress_history", []))
    return list(reversed(history[-limit:]))
