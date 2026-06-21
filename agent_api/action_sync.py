SAFETY_NOTE = "本行动项仅用于财务整理和风险提醒，不构成专业财务建议。"

HIGH_KEYWORDS = ["现金流缺口", "逾期", "断流", "高风险", "必须", "优先", "今天"]
MEDIUM_KEYWORDS = ["确认", "补充", "核查", "回款", "余额", "发票"]
LOW_KEYWORDS = ["复盘", "记录", "整理", "报告"]
VALID_PRIORITIES = {"high", "medium", "low"}
CHAT_ACTION_STATUSES = {"pending", "in_progress", "done", "ignored"}


def normalize_chat_action_text(action) -> str:
    """
    Convert a suggested action into display text.
    Supports plain strings and dictionaries from Agent outputs.
    """
    if isinstance(action, str):
        return action.strip()
    if isinstance(action, dict):
        for key in ["title", "action", "text", "description", "recommendation"]:
            value = action.get(key)
            if value:
                return str(value).strip()
    if action is None:
        return ""
    return str(action).strip()


def infer_action_priority(action_text: str, manager_plan: dict | None = None) -> str:
    """
    Infer high / medium / low from action text and Manager intent.
    """
    text = str(action_text or "")
    if any(keyword in text for keyword in HIGH_KEYWORDS):
        return "high"
    if any(keyword in text for keyword in MEDIUM_KEYWORDS):
        return "medium"
    if any(keyword in text for keyword in LOW_KEYWORDS):
        return "low"

    intent = str((manager_plan or {}).get("intent", ""))
    if intent in {"cashflow_check", "expense_anomaly_review"}:
        return "medium"
    if intent in {"report_generation", "financial_summary"}:
        return "low"
    return "medium"


def infer_action_deadline(priority: str) -> str:
    """
    Infer suggested deadline from priority.
    """
    normalized_priority = str(priority or "").strip().lower()
    if normalized_priority == "high":
        return "今天"
    if normalized_priority == "low":
        return "本周内"
    return "3 天内"


def _normalize_action_status(status: str | None) -> str:
    value = str(status or "").strip().lower()
    if value in CHAT_ACTION_STATUSES:
        return value
    return "pending"


def build_chat_action_item(
    action_text: str,
    index: int,
    turn_result: dict | None = None,
) -> dict:
    """
    Convert one suggested action into a formal chat-derived action item.
    """
    turn_result = turn_result or {}
    manager_plan = turn_result.get("manager_plan", {}) or {}
    title = normalize_chat_action_text(action_text)
    priority = infer_action_priority(title, manager_plan=manager_plan)
    return {
        "action_id": f"C{max(int(index), 1):03d}",
        "title": title,
        "description": "该行动项来自 FinCopilot 多 Agent 对话。",
        "source": "agent_chat",
        "priority": priority,
        "reason": "Multi-Agent 对话建议将该事项纳入行动中心跟踪。",
        "suggested_deadline": infer_action_deadline(priority),
        "recommended_steps": [
            "核查相关原始凭证和业务事实。",
            "在行动中心更新处理状态。",
            "必要时回到 Agent Chat 补充信息并重新分析。",
        ],
        "related_record": {
            "user_query": turn_result.get("user_query", ""),
            "intent": manager_plan.get("intent", "unknown"),
        },
        "status": "pending",
        "safety_note": SAFETY_NOTE,
    }


def sync_turn_result_to_action_items(turn_result: dict | None) -> list[dict]:
    """
    Convert run_multi_agent_turn suggested_actions into formal action items.
    """
    turn_result = turn_result or {}
    action_items = []
    for action in turn_result.get("suggested_actions", []) or []:
        action_text = normalize_chat_action_text(action)
        if not action_text:
            continue
        action_items.append(
            build_chat_action_item(
                action_text,
                len(action_items) + 1,
                turn_result=turn_result,
            )
        )
    return action_items


def merge_chat_action_items(existing_items: list[dict] | None, new_items: list[dict] | None) -> list[dict]:
    """
    Merge chat-derived action items by title and preserve existing status.
    """
    merged = []
    title_to_index = {}
    for item in existing_items or []:
        normalized_item = dict(item or {})
        normalized_item["status"] = _normalize_action_status(normalized_item.get("status"))
        title = normalize_chat_action_text(normalized_item.get("title"))
        if not title or title in title_to_index:
            continue
        normalized_item["title"] = title
        title_to_index[title] = len(merged)
        merged.append(normalized_item)

    for item in new_items or []:
        normalized_item = dict(item or {})
        title = normalize_chat_action_text(normalized_item.get("title"))
        if not title:
            continue
        if title in title_to_index:
            existing = merged[title_to_index[title]]
            preserved_status = _normalize_action_status(existing.get("status"))
            existing.update(normalized_item)
            existing["status"] = preserved_status
            continue
        normalized_item["title"] = title
        normalized_item["status"] = _normalize_action_status(normalized_item.get("status"))
        title_to_index[title] = len(merged)
        merged.append(normalized_item)

    for index, item in enumerate(merged, start=1):
        item["action_id"] = f"C{index:03d}"
        item.setdefault("source", "agent_chat")
        item.setdefault("safety_note", SAFETY_NOTE)
    return merged


def summarize_chat_action_items(action_items: list[dict] | None) -> dict:
    """
    Summarize chat-derived action items.
    """
    items = list(action_items or [])
    summary = {
        "total": len(items),
        "high": 0,
        "medium": 0,
        "low": 0,
        "pending": 0,
        "done": 0,
    }
    for item in items:
        priority = str((item or {}).get("priority", "medium")).strip().lower()
        if priority not in VALID_PRIORITIES:
            priority = "medium"
        status = _normalize_action_status((item or {}).get("status"))
        summary[priority] += 1
        if status == "done":
            summary["done"] += 1
        elif status == "pending":
            summary["pending"] += 1
    return summary
