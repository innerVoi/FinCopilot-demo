VALID_PRIORITIES = {"high", "medium", "low"}
VALID_SOURCES = {
    "cashflow",
    "invoice",
    "rule_anomaly",
    "model_anomaly",
    "goal",
    "clarification",
    "summary",
}

DEFAULT_SAFETY_NOTE = "本行动项仅用于财务整理和风险提醒，不构成专业财务建议。"


def normalize_priority(priority: str | None) -> str:
    """
    Normalize priority to high / medium / low.
    """
    value = str(priority or "").strip().lower()
    if value in VALID_PRIORITIES:
        return value
    return "medium"


def normalize_source(source: str | None) -> str:
    """
    Normalize source to a known action source.
    """
    value = str(source or "").strip().lower()
    if value in VALID_SOURCES:
        return value
    return "summary"


def generate_action_id(index: int) -> str:
    """
    Generate a stable action id, for example A001.
    """
    return f"A{max(int(index), 1):03d}"


def make_action_item(
    action_id: str,
    title: str,
    description: str,
    source: str,
    priority: str,
    reason: str,
    suggested_deadline: str,
    recommended_steps: list[str] | None = None,
    related_record: dict | None = None,
    status: str = "pending",
    safety_note: str | None = None,
) -> dict:
    """
    Create a standard Agent action item.
    """
    return {
        "action_id": action_id,
        "title": str(title or ""),
        "description": str(description or ""),
        "source": normalize_source(source),
        "priority": normalize_priority(priority),
        "reason": str(reason or ""),
        "suggested_deadline": str(suggested_deadline or "下次复查前"),
        "recommended_steps": list(recommended_steps or []),
        "related_record": dict(related_record or {}),
        "status": status or "pending",
        "safety_note": safety_note or DEFAULT_SAFETY_NOTE,
    }


def action_item_to_display_dict(action_item: dict) -> dict:
    """
    Flatten an action item for Streamlit table display.
    """
    item = action_item or {}
    return {
        "action_id": item.get("action_id", ""),
        "priority": item.get("priority", ""),
        "source": item.get("source", ""),
        "title": item.get("title", ""),
        "reason": item.get("reason", ""),
        "suggested_deadline": item.get("suggested_deadline", ""),
        "status": item.get("status", ""),
        "rank_score": item.get("rank_score", 0),
    }


def action_items_to_markdown(action_items: list[dict]) -> str:
    """
    Convert action items to copyable Markdown.
    """
    lines = ["# FinCopilot 行动清单"]
    for item in action_items or []:
        lines.append(f"## [{item.get('priority', '')}] {item.get('title', '')}")
        lines.append(f"- 来源：{item.get('source', '')}")
        lines.append(f"- 原因：{item.get('reason', '')}")
        lines.append(f"- 建议截止时间：{item.get('suggested_deadline', '')}")
        lines.append("- 建议步骤：")
        for step in item.get("recommended_steps", []):
            lines.append(f"  - {step}")
        lines.append("")
    return "\n".join(lines)
