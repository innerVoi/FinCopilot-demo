from agent.agent_state import (
    apply_saved_status_to_actions,
    get_action_key,
    get_business_context,
    get_default_agent_state,
    get_saved_action_note,
    get_saved_action_status,
    merge_business_context,
    reset_action_progress,
    reset_agent_state,
    update_action_status,
    update_agent_state,
)


def test_get_default_agent_state_returns_required_sections():
    state = get_default_agent_state()

    assert isinstance(state, dict)
    assert "business_context" in state
    assert "task_context" in state
    assert "clarification_history" in state
    assert "action_status" in state
    assert "action_notes" in state
    assert "progress_history" in state


def test_merge_business_context_keeps_existing_when_new_value_empty():
    merged = merge_business_context(
        {"current_cash_balance": 5000, "business_notes": "keep"},
        {"current_cash_balance": 0, "business_notes": ""},
    )

    assert merged["current_cash_balance"] == 5000
    assert merged["business_notes"] == "keep"


def test_merge_business_context_applies_valid_new_values():
    merged = merge_business_context(
        {"current_cash_balance": 5000},
        {"current_cash_balance": 8000, "recurring_vendor_list": "AWS, Stripe"},
    )

    assert merged["current_cash_balance"] == 8000
    assert merged["recurring_vendor_list"] == "AWS, Stripe"


def test_update_agent_state_updates_task_id_and_context():
    state = update_agent_state(
        None,
        task_id="cashflow_safety_check",
        business_context_updates={"expected_receivables_30d": 1200},
    )

    assert state["task_context"]["selected_task_id"] == "cashflow_safety_check"
    assert state["business_context"]["expected_receivables_30d"] == 1200
    assert state["clarification_history"]


def test_get_business_context_is_safe_for_none():
    context = get_business_context(None)

    assert "current_cash_balance" in context


def test_reset_agent_state_returns_default_state():
    state = reset_agent_state()

    assert state == get_default_agent_state()


def test_get_action_key_returns_task_and_action_id():
    assert get_action_key("cashflow_safety_check", "A001") == "cashflow_safety_check:A001"


def test_update_action_status_saves_status_note_and_history():
    state = update_action_status(
        None,
        "cashflow_safety_check",
        "A001",
        "done",
        note="已核查。",
    )

    assert get_saved_action_status(state, "cashflow_safety_check", "A001") == "done"
    assert get_saved_action_note(state, "cashflow_safety_check", "A001") == "已核查。"
    assert state["progress_history"]


def test_reset_action_progress_resets_one_task():
    state = update_action_status(None, "cashflow_safety_check", "A001", "done")
    state = update_action_status(state, "goal_action_plan", "A001", "in_progress")

    reset_state = reset_action_progress(state, task_id="cashflow_safety_check")

    assert get_saved_action_status(reset_state, "cashflow_safety_check", "A001") == "pending"
    assert get_saved_action_status(reset_state, "goal_action_plan", "A001") == "in_progress"


def test_apply_saved_status_to_actions_applies_status_and_note():
    state = update_action_status(
        None,
        "cashflow_safety_check",
        "A001",
        "needs_follow_up",
        note="等待供应商确认。",
    )
    actions = [{"action_id": "A001", "status": "pending"}]

    result = apply_saved_status_to_actions(actions, state, "cashflow_safety_check")

    assert result[0]["status"] == "needs_follow_up"
    assert result[0]["note"] == "等待供应商确认。"
