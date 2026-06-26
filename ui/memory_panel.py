import streamlit as st

from memory.memory_service import (
    SUPPORTED_MEMORY_TYPES,
    add_business_memory,
    count_business_memory,
    deactivate_business_memory,
    list_business_memory,
)


MEMORY_TYPE_LABELS = {
    "known_normal_payments": "Known Normal Payments",
    "known_suppliers": "Known Suppliers",
    "cash_context": "Cash Context",
    "expected_receivables": "Expected Receivables",
    "recurring_expenses": "Recurring Expenses",
    "business_rules": "Business Rules",
    "user_preferences": "User Preferences",
    "known_risks": "Known Risks",
}

MEMORY_TYPE_OPTIONS = {
    "known_normal_payment": "Known Normal Payment",
    "known_supplier": "Known Supplier",
    "cash_balance": "Cash Balance / Cash Context",
    "expected_receivable": "Expected Receivable",
    "recurring_expense": "Recurring Expense",
    "business_rule": "Business Rule",
    "user_preference": "User Preference",
    "known_risk": "Known Risk",
}


def render_memory_context_summary(memory_context: dict | None) -> None:
    if not memory_context or not memory_context.get("memory_count"):
        st.info("No historical business memory yet. This analysis is mainly based on the currently uploaded data.")
        return

    st.subheader("Business Memory Context")
    st.caption(memory_context.get("memory_notes", ""))
    for key, label in MEMORY_TYPE_LABELS.items():
        items = memory_context.get(key) or []
        if not items:
            continue
        st.markdown(f"**{label}**")
        for item in items:
            st.markdown(f"- {item}")


def render_business_memory_table(memories: list[dict]) -> None:
    if not memories:
        st.info("No business memory in the current workspace yet.")
        return
    rows = [
        {
            "memory_id": memory.get("memory_id"),
            "type": MEMORY_TYPE_OPTIONS.get(memory.get("memory_type"), memory.get("memory_type")),
            "entity": memory.get("entity_name") or "",
            "fact": memory.get("fact_text") or "",
            "confidence": memory.get("confidence") or "",
            "source": memory.get("source") or "",
            "active": "yes" if memory.get("is_active") else "no",
            "updated_at": memory.get("updated_at") or "",
        }
        for memory in memories
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)


def render_add_memory_form(user_id: str, workspace_id: str, db_path: str | None = None) -> None:
    with st.expander("Add Business Memory", expanded=False):
        type_options = sorted(SUPPORTED_MEMORY_TYPES)
        memory_type = st.selectbox(
            "Memory type",
            type_options,
            format_func=lambda value: MEMORY_TYPE_OPTIONS.get(value, value),
            key="business_memory_type",
        )
        entity_name = st.text_input("Related entity", key="business_memory_entity")
        fact_text = st.text_area("Business fact", key="business_memory_fact")
        retrieval_tags = st.text_input("Retrieval tags", key="business_memory_tags")
        if st.button("Save Business Memory", key="save_business_memory"):
            try:
                add_business_memory(
                    user_id=user_id,
                    workspace_id=workspace_id,
                    memory_type=memory_type,
                    entity_name=entity_name,
                    fact_text=fact_text,
                    retrieval_tags=retrieval_tags,
                    db_path=db_path,
                )
                st.success("Business Memory has been saved.")
                st.rerun()
            except Exception as exc:
                st.error(f"Failed to save Business Memory: {exc}")


def render_memory_management_panel(user_id: str, workspace_id: str, db_path: str | None = None) -> None:
    st.subheader("Business Memory Management")
    st.caption("Use feedback in Copilot Home to turn confirmed business facts into reusable memory.")
    try:
        active_count = count_business_memory(user_id, workspace_id, active_only=True, db_path=db_path)
        memories = list_business_memory(
            user_id=user_id,
            workspace_id=workspace_id,
            active_only=False,
            limit=200,
            db_path=db_path,
        )
    except Exception as exc:
        st.warning(f"Business Memory is unavailable: {exc}")
        return

    st.metric("Active Memory", active_count)
    render_business_memory_table(memories)
    render_add_memory_form(user_id, workspace_id, db_path=db_path)

    active_memories = [memory for memory in memories if memory.get("is_active")]
    if not active_memories:
        return
    with st.expander("Deactivate Business Memory", expanded=False):
        selected_memory_id = st.selectbox(
            "Select memory to deactivate",
            [memory["memory_id"] for memory in active_memories],
            key="deactivate_business_memory_id",
        )
        if st.button("Deactivate selected memory", key="deactivate_business_memory"):
            try:
                deactivate_business_memory(
                    user_id=user_id,
                    workspace_id=workspace_id,
                    memory_id=selected_memory_id,
                    db_path=db_path,
                )
                st.success("Business Memory has been deactivated.")
                st.rerun()
            except Exception as exc:
                st.error(f"Failed to deactivate Business Memory: {exc}")
