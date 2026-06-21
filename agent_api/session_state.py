from copy import deepcopy


def get_default_agent_chat_state() -> dict:
    """
    Return the default Agent Chat state.
    """
    return {
        "messages": [],
        "turns": [],
        "latest_turn_result": None,
        "latest_trace": None,
        "latest_suggested_actions": [],
        "latest_clarifying_questions": [],
        "chat_action_items": [],
        "latest_report_markdown": "",
        "latest_trace_markdown": "",
    }


def ensure_agent_chat_state(state: dict | None) -> dict:
    """
    Complete missing chat state fields.
    """
    default_state = get_default_agent_chat_state()
    if not isinstance(state, dict):
        return default_state
    normalized = deepcopy(default_state)
    normalized.update(state)
    for key in [
        "messages",
        "turns",
        "latest_suggested_actions",
        "latest_clarifying_questions",
        "chat_action_items",
    ]:
        if not isinstance(normalized.get(key), list):
            normalized[key] = []
    for key in ["latest_report_markdown", "latest_trace_markdown"]:
        if not isinstance(normalized.get(key), str):
            normalized[key] = ""
    return normalized


def append_user_message(state: dict | None, content: str) -> dict:
    """
    Append a user message.
    """
    state = ensure_agent_chat_state(state)
    state["messages"].append({"role": "user", "content": content or ""})
    return state


def append_assistant_message(state: dict | None, content: str, metadata: dict | None = None) -> dict:
    """
    Append an assistant message.
    """
    state = ensure_agent_chat_state(state)
    message = {"role": "assistant", "content": content or ""}
    if metadata is not None:
        message["metadata"] = metadata
    state["messages"].append(message)
    return state


def add_turn_result(state: dict | None, turn_result: dict, trace: dict | None = None) -> dict:
    """
    Record one complete multi-agent turn.
    """
    state = ensure_agent_chat_state(state)
    turn_result = turn_result or {}
    trace = trace or turn_result.get("trace")
    state["latest_turn_result"] = turn_result
    state["latest_trace"] = trace
    state["latest_suggested_actions"] = list(turn_result.get("suggested_actions", []))
    state["latest_clarifying_questions"] = list(turn_result.get("clarifying_questions", []))
    state["latest_report_markdown"] = turn_result.get("report_markdown", "")
    state["latest_trace_markdown"] = turn_result.get("trace_markdown", "")
    state["turns"].append(
        {
            "user_query": turn_result.get("user_query", ""),
            "assistant_reply": turn_result.get("assistant_reply", ""),
            "turn_result": turn_result,
            "trace": trace,
        }
    )
    return state


def reset_agent_chat_state() -> dict:
    """
    Reset Agent Chat state.
    """
    return get_default_agent_chat_state()


def get_latest_turn_result(state: dict | None) -> dict | None:
    """
    Return the latest turn result.
    """
    return ensure_agent_chat_state(state).get("latest_turn_result")


def update_chat_action_items(state: dict | None, action_items: list[dict]) -> dict:
    """
    Update chat-derived action items.
    """
    state = ensure_agent_chat_state(state)
    state["chat_action_items"] = list(action_items or [])
    return state


def get_chat_action_items(state: dict | None) -> list[dict]:
    """
    Return chat-derived action items.
    """
    return list(ensure_agent_chat_state(state).get("chat_action_items", []))


def update_latest_reports(
    state: dict | None,
    report_markdown: str | None = None,
    trace_markdown: str | None = None,
) -> dict:
    """
    Update latest Multi-Agent report and trace Markdown.
    """
    state = ensure_agent_chat_state(state)
    if report_markdown is not None:
        state["latest_report_markdown"] = str(report_markdown or "")
    if trace_markdown is not None:
        state["latest_trace_markdown"] = str(trace_markdown or "")
    return state
