import streamlit as st

from memory.feedback_service import list_user_feedback, submit_feedback
from ui.action_feedback_panel import render_action_feedback_list


GENERAL_FEEDBACK_OPTIONS = {
    "add_business_context": "Add business context",
    "update_cash_balance": "Update current cash balance",
    "add_expected_receivable": "Add expected receivable",
    "confirm_known_risk": "Confirm known risk",
}

FEEDBACK_TYPE_LABELS = {
    "confirm_normal_payment": "Normal payment",
    "confirm_supplier": "Long-term supplier",
    "confirm_recurring_expense": "Recurring expense",
    "update_cash_balance": "Cash balance",
    "add_expected_receivable": "Expected receivable",
    "confirm_known_risk": "Known risk",
    "complete_action": "Completed action item",
    "ignore_action": "Ignored action item",
    "reject_suggestion": "Suggestion not suitable",
    "add_business_context": "Business context",
}


def _get_db_path() -> str | None:
    session_state = getattr(st, "session_state", None)
    if hasattr(session_state, "get"):
        return session_state.get("memory_db_path")
    return None


def _safe_rerun() -> None:
    rerun = getattr(st, "rerun", None)
    if callable(rerun):
        rerun()


def _submit_and_report(**kwargs) -> None:
    try:
        result = submit_feedback(db_path=_get_db_path(), **kwargs)
        st.success(result.get("message", "Feedback has been saved."))
        _safe_rerun()
    except Exception as exc:
        st.error(f"Failed to save feedback: {exc}")


def render_general_feedback_form(
    user_id: str,
    workspace_id: str,
    turn_id: str | None = None,
) -> None:
    with st.expander("Add Feedback for FinCopilot Memory", expanded=False):
        feedback_type = st.selectbox(
            "Feedback Type",
            list(GENERAL_FEEDBACK_OPTIONS.keys()),
            format_func=lambda value: GENERAL_FEEDBACK_OPTIONS.get(value, value),
            key="general_memory_feedback_type",
        )
        entity_name = st.text_input("Related Entity", key="general_memory_feedback_entity")
        amount = st.text_input("Amount or Balance", key="general_memory_feedback_amount")
        feedback_text = st.text_area("Feedback Notes", key="general_memory_feedback_text")
        if st.button("Save Feedback", key="submit_general_memory_feedback"):
            metadata = {
                "entity_name": entity_name,
                "amount": amount,
            }
            _submit_and_report(
                user_id=user_id,
                workspace_id=workspace_id,
                feedback_type=feedback_type,
                feedback_text=feedback_text,
                turn_id=turn_id,
                target_type="general_feedback",
                target_metadata=metadata,
            )


def _transaction_metadata(transaction: dict | None) -> dict:
    transaction = transaction or {}
    return {
        "merchant": transaction.get("merchant") or transaction.get("vendor") or transaction.get("description"),
        "amount": transaction.get("amount"),
        "date": transaction.get("date"),
        "category": transaction.get("category"),
        "description": transaction.get("description"),
    }


def render_transaction_feedback_buttons(
    user_id: str,
    workspace_id: str,
    transaction: dict,
    turn_id: str | None = None,
) -> None:
    transaction = transaction or {}
    target_id = str(transaction.get("transaction_id") or transaction.get("id") or transaction.get("description") or "")
    metadata = _transaction_metadata(transaction)
    merchant = metadata.get("merchant") or "this transaction"
    button_specs = [
        ("Normal Payment", "confirm_normal_payment", f"{merchant} is normal business spending."),
        ("Long-Term Supplier", "confirm_supplier", f"{merchant} is a long-term supplier."),
        ("Recurring Expense", "confirm_recurring_expense", f"{merchant} is a recurring expense."),
        ("Needs Review", "confirm_known_risk", f"{merchant} needs continued review."),
    ]
    columns = st.columns(len(button_specs))
    for index, (label, feedback_type, feedback_text) in enumerate(button_specs):
        if columns[index].button(label, key=f"tx_feedback_{feedback_type}_{target_id}_{index}"):
            _submit_and_report(
                user_id=user_id,
                workspace_id=workspace_id,
                feedback_type=feedback_type,
                feedback_text=feedback_text,
                turn_id=turn_id,
                target_type="transaction",
                target_id=target_id,
                target_metadata=metadata,
            )


def render_action_feedback_buttons(
    user_id: str,
    workspace_id: str,
    action_item: dict,
    turn_id: str | None = None,
) -> None:
    action_item = action_item or {}
    title = action_item.get("title") or action_item.get("description") or "Action Items"
    target_id = str(action_item.get("action_id") or action_item.get("id") or title)
    button_specs = [
        ("Completed", "complete_action", f"Action item completed: {title}"),
        ("Ignore for Now", "ignore_action", f"Action item ignored for now: {title}"),
        ("Not Suitable", "reject_suggestion", f"This suggestion does not fit the current business context: {title}"),
    ]
    columns = st.columns(len(button_specs))
    for index, (label, feedback_type, feedback_text) in enumerate(button_specs):
        if columns[index].button(label, key=f"action_feedback_{feedback_type}_{target_id}_{index}"):
            _submit_and_report(
                user_id=user_id,
                workspace_id=workspace_id,
                feedback_type=feedback_type,
                feedback_text=feedback_text,
                turn_id=turn_id,
                target_type="action_item",
                target_id=target_id,
                target_metadata=action_item,
            )


def render_feedback_history(user_id: str, workspace_id: str) -> None:
    st.subheader("User Feedback History")
    try:
        feedback_rows = list_user_feedback(
            user_id=user_id,
            workspace_id=workspace_id,
            limit=100,
            db_path=_get_db_path(),
        )
    except Exception as exc:
        st.warning(f"User feedback history is temporarily unavailable: {exc}")
        return

    if not feedback_rows:
        st.info("No user feedback exists in the current workspace yet.")
        return
    rows = [
        {
            "created_at": row.get("created_at"),
            "feedback_type": FEEDBACK_TYPE_LABELS.get(row.get("feedback_type"), row.get("feedback_type")),
            "target_type": row.get("target_type") or "",
            "feedback_text": row.get("feedback_text") or "",
        }
        for row in feedback_rows
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)


def render_feedback_panel(
    user_id: str,
    workspace_id: str,
    latest_turn_result: dict | None = None,
) -> None:
    latest_turn_result = latest_turn_result or {}
    turn_id = latest_turn_result.get("turn_id")
    st.subheader("Feedback & Memory")
    st.caption("Confirmed business facts are first saved as user feedback. Items suitable for reuse are converted into Business Memory.")
    render_general_feedback_form(user_id=user_id, workspace_id=workspace_id, turn_id=turn_id)

    suggested_actions = latest_turn_result.get("suggested_actions") or []
    if suggested_actions:
        with st.expander("Give Feedback on This Turn's Suggested Actions", expanded=False):
            render_action_feedback_list(
                user_id=user_id,
                workspace_id=workspace_id,
                action_items=[
                    {"title": str(action), "action_id": f"suggested_{index}", "source": "suggested_actions"}
                    for index, action in enumerate(suggested_actions[:5])
                ],
                turn_id=turn_id,
            )
