from datetime import datetime, timezone


BUSINESS_CONTEXT_DEFAULTS = {
    "current_cash_balance": None,
    "expected_receivables_30d": None,
    "unuploaded_invoices_estimate": None,
    "large_upcoming_payments": None,
    "known_authorized_large_payments": "",
    "recurring_vendor_list": "",
    "business_context_for_top_anomalies": "",
    "goal_priority_confirmation": "",
    "expected_monthly_savings_capacity": None,
    "business_notes": "",
}


def get_default_agent_state() -> dict:
    """
    Return the default Agent Workspace state.
    """
    return {
        "business_context": BUSINESS_CONTEXT_DEFAULTS.copy(),
        "task_context": {
            "selected_task_id": None,
            "last_completed_task_id": None,
            "last_workspace_status": None,
        },
        "clarification_history": [],
        "action_status": {},
        "action_notes": {},
        "progress_history": [],
    }


def _normalize_state(agent_state: dict | None) -> dict:
    state = get_default_agent_state()
    if not agent_state:
        return state
    state["business_context"] = merge_business_context(
        agent_state.get("business_context"),
        None,
    )
    state["task_context"].update(agent_state.get("task_context", {}))
    state["clarification_history"] = list(
        agent_state.get("clarification_history", [])
    )
    state["action_status"] = dict(agent_state.get("action_status", {}))
    state["action_notes"] = dict(agent_state.get("action_notes", {}))
    state["progress_history"] = list(agent_state.get("progress_history", []))
    return state


def _is_valid_update_value(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (int, float)):
        return value != 0
    return bool(value)


def merge_business_context(
    existing_context: dict | None,
    new_values: dict | None,
) -> dict:
    """
    Merge user-provided business context while keeping all known fields.
    """
    merged = BUSINESS_CONTEXT_DEFAULTS.copy()
    for key, value in (existing_context or {}).items():
        if key in merged and _is_valid_update_value(value):
            merged[key] = value

    for key, value in (new_values or {}).items():
        if key in merged and _is_valid_update_value(value):
            merged[key] = value

    return merged


def update_agent_state(
    agent_state: dict | None,
    task_id: str | None = None,
    business_context_updates: dict | None = None,
) -> dict:
    """
    Update Agent state with task selection and business context changes.
    """
    current_state = _normalize_state(agent_state)
    updated_state = _normalize_state(current_state)
    updated_state["business_context"] = merge_business_context(
        current_state.get("business_context"),
        business_context_updates,
    )
    updated_state["task_context"].update(current_state.get("task_context", {}))
    updated_state["clarification_history"] = list(
        current_state.get("clarification_history", [])
    )

    if task_id is not None:
        updated_state["task_context"]["selected_task_id"] = task_id

    if business_context_updates:
        updated_state["clarification_history"].append(
            {
                "task_id": task_id,
                "provided_fields": [
                    key
                    for key, value in business_context_updates.items()
                    if key in BUSINESS_CONTEXT_DEFAULTS and _is_valid_update_value(value)
                ],
            }
        )

    return updated_state


def reset_agent_state() -> dict:
    """
    Return a reset Agent state.
    """
    return get_default_agent_state()


def get_business_context(agent_state: dict | None) -> dict:
    """
    Safely get business context from Agent state.
    """
    if not agent_state:
        return BUSINESS_CONTEXT_DEFAULTS.copy()
    return merge_business_context(agent_state.get("business_context"), None)


def get_action_key(task_id: str, action_id: str) -> str:
    """
    Build a persisted action state key.
    """
    return f"{task_id}:{action_id}"


def _normalize_status(status: str | None) -> str:
    valid_statuses = {
        "pending",
        "in_progress",
        "verified_normal",
        "needs_follow_up",
        "done",
        "ignored",
    }
    value = str(status or "").strip().lower()
    if value in valid_statuses:
        return value
    return "pending"


def update_action_status(
    agent_state: dict | None,
    task_id: str,
    action_id: str,
    new_status: str,
    note: str | None = None,
) -> dict:
    """
    Update one action status and append a progress history event.
    """
    state = _normalize_state(agent_state)
    action_key = get_action_key(task_id, action_id)
    old_status = state["action_status"].get(action_key, "pending")
    normalized_status = _normalize_status(new_status)
    state["action_status"][action_key] = normalized_status
    if note is not None:
        state["action_notes"][action_key] = str(note)
    state["progress_history"].append(
        {
            "task_id": task_id,
            "action_id": action_id,
            "old_status": old_status,
            "new_status": normalized_status,
            "note": "" if note is None else str(note),
            "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
    )
    return state


def get_saved_action_status(
    agent_state: dict | None,
    task_id: str,
    action_id: str,
    default: str = "pending",
) -> str:
    """
    Return a saved action status.
    """
    state = _normalize_state(agent_state)
    return _normalize_status(
        state["action_status"].get(get_action_key(task_id, action_id), default)
    )


def get_saved_action_note(agent_state: dict | None, task_id: str, action_id: str) -> str:
    """
    Return a saved action note.
    """
    state = _normalize_state(agent_state)
    return state["action_notes"].get(get_action_key(task_id, action_id), "")


def reset_action_progress(agent_state: dict | None, task_id: str | None = None) -> dict:
    """
    Reset action progress for one task or all tasks.
    """
    state = _normalize_state(agent_state)
    if task_id is None:
        state["action_status"] = {}
        state["action_notes"] = {}
        state["progress_history"] = []
        return state

    prefix = f"{task_id}:"
    state["action_status"] = {
        key: value
        for key, value in state["action_status"].items()
        if not key.startswith(prefix)
    }
    state["action_notes"] = {
        key: value
        for key, value in state["action_notes"].items()
        if not key.startswith(prefix)
    }
    state["progress_history"] = [
        event
        for event in state["progress_history"]
        if event.get("task_id") != task_id
    ]
    return state


def apply_saved_status_to_actions(
    action_items: list[dict],
    agent_state: dict | None,
    task_id: str,
) -> list[dict]:
    """
    Apply saved session state status and notes to action items.
    """
    updated_items = []
    for item in action_items or []:
        copied = dict(item)
        action_id = copied.get("action_id", "")
        copied["status"] = get_saved_action_status(
            agent_state,
            task_id,
            action_id,
            default=copied.get("status", "pending"),
        )
        copied["note"] = get_saved_action_note(agent_state, task_id, action_id)
        updated_items.append(copied)
    return updated_items
