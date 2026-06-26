import streamlit as st

from memory.action_memory_service import list_handled_action_items, list_pending_action_items
from memory.admin_service import (
    clear_current_workspace_all_data,
    clear_workspace_actions,
    clear_workspace_business_memory,
    clear_workspace_feedback,
    clear_workspace_turns_traces_reports,
    get_workspace_memory_stats,
)
from memory.feedback_service import list_user_feedback
from memory.memory_service import deactivate_business_memory, list_business_memory
from memory.report_service import list_reports
from memory.repository import create_workspace, get_workspace, list_workspaces
from memory.trace_service import list_agent_traces
from memory.turn_service import list_agent_turns
from memory.workspace import set_current_workspace_id


def _get_db_path() -> str | None:
    session_state = getattr(st, "session_state", None)
    if hasattr(session_state, "get"):
        return session_state.get("memory_db_path")
    return None


def _safe_dataframe(rows, empty_message: str) -> None:
    rows = list(rows or [])
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info(empty_message)


def _feedback_reason(action: dict) -> str:
    return ((action.get("metadata") or {}).get("feedback") or {}).get("feedback_reason", "")


def render_current_identity_card(user_id: str, workspace_id: str) -> None:
    st.subheader("Current Identity & Workspace")
    col1, col2 = st.columns(2)
    col1.metric("user_id", user_id)
    col2.metric("workspace_id", workspace_id)
    try:
        workspace = get_workspace(user_id, workspace_id, db_path=_get_db_path())
    except Exception as exc:
        st.warning(f"Workspace information is unavailable: {exc}")
        return
    if workspace:
        st.caption(f"Workspace name: {workspace.get('workspace_name', '')} | Business type: {workspace.get('business_type', '')}")
    else:
        st.info("The current workspace has not been written to the database yet.")


def render_workspace_switcher(user_id: str) -> None:
    st.subheader("Demo Workspace Switcher")
    db_path = _get_db_path()
    try:
        workspaces = list_workspaces(user_id, db_path=db_path)
    except Exception as exc:
        st.warning(f"Workspace list is unavailable: {exc}")
        workspaces = []
    options = [item["workspace_id"] for item in workspaces]
    if options:
        selected = st.selectbox("Select a workspace for the current user", options, key="memory_workspace_switcher")
        if selected and st.button("Switch Workspace", key="switch_memory_workspace"):
            set_current_workspace_id(st.session_state, selected)
            st.success(f"Switched to workspace: {selected}")
            st.rerun()
    else:
        st.info("No switchable workspace is available for the current user.")

    with st.expander("Create Demo Workspace", expanded=False):
        new_workspace_id = st.text_input("workspace_id", key="new_demo_workspace_id")
        workspace_name = st.text_input("workspace_name", key="new_demo_workspace_name")
        business_type = st.text_input("business_type", key="new_demo_workspace_business_type")
        if st.button("Create Workspace", key="create_demo_workspace"):
            try:
                workspace = create_workspace(
                    user_id=user_id,
                    workspace_id=new_workspace_id,
                    workspace_name=workspace_name or new_workspace_id,
                    business_type=business_type or "Demo business",
                    db_path=db_path,
                )
                set_current_workspace_id(st.session_state, workspace["workspace_id"])
                st.success(f"Created and switched to workspace: {workspace['workspace_id']}")
                st.rerun()
            except Exception as exc:
                st.error(f"Failed to create workspace: {exc}")


def render_workspace_stats(user_id: str, workspace_id: str) -> None:
    st.subheader("Workspace Data Stats")
    try:
        stats = get_workspace_memory_stats(user_id, workspace_id, db_path=_get_db_path())
    except Exception as exc:
        st.warning(f"Workspace stats are unavailable: {exc}")
        return
    labels = [
        ("Business Memory", "business_memory_count"),
        ("Active Memory", "active_business_memory_count"),
        ("Feedback", "user_feedback_count"),
        ("Action", "action_count"),
        ("Pending Action", "pending_action_count"),
        ("Handled Action", "handled_action_count"),
        ("Agent Turns", "agent_turn_count"),
        ("Reports", "report_count"),
        ("Traces", "trace_count"),
    ]
    columns = st.columns(3)
    for index, (label, key) in enumerate(labels):
        columns[index % 3].metric(label, stats.get(key, 0))


def render_business_memory_section(user_id: str, workspace_id: str) -> None:
    st.subheader("Business Memory")
    try:
        memories = list_business_memory(user_id, workspace_id, active_only=False, limit=200, db_path=_get_db_path())
    except Exception as exc:
        st.warning(f"Business Memory is unavailable: {exc}")
        return
    rows = [
        {
            "memory_id": item.get("memory_id"),
            "memory_type": item.get("memory_type"),
            "entity_name": item.get("entity_name") or "",
            "fact_text": item.get("fact_text") or "",
            "is_active": item.get("is_active"),
            "last_used_at": item.get("last_used_at") or "",
        }
        for item in memories
    ]
    _safe_dataframe(rows, "No Business Memory in the current workspace yet.")
    active_ids = [item["memory_id"] for item in memories if item.get("is_active")]
    if active_ids:
        selected = st.selectbox("Select memory to deactivate", active_ids, key="management_deactivate_memory")
        if selected and st.button("Deactivate selected Business Memory", key="management_deactivate_memory_button"):
            deactivate_business_memory(user_id, workspace_id, selected, db_path=_get_db_path())
            st.success("Business Memory has been deactivated.")
            st.rerun()


def render_feedback_section(user_id: str, workspace_id: str) -> None:
    st.subheader("User Feedback")
    try:
        rows = list_user_feedback(user_id, workspace_id, limit=200, db_path=_get_db_path())
    except Exception as exc:
        st.warning(f"User Feedback is unavailable: {exc}")
        return
    _safe_dataframe(
        [
            {
                "created_at": item.get("created_at"),
                "feedback_type": item.get("feedback_type"),
                "target_type": item.get("target_type") or "",
                "target_id": item.get("target_id") or "",
                "feedback_text": item.get("feedback_text") or "",
            }
            for item in rows
        ],
        "No User Feedback in the current workspace yet.",
    )


def render_action_memory_section(user_id: str, workspace_id: str) -> None:
    st.subheader("Action Memory")
    try:
        pending = list_pending_action_items(user_id, workspace_id, db_path=_get_db_path())
        handled = list_handled_action_items(user_id, workspace_id, db_path=_get_db_path())
    except Exception as exc:
        st.warning(f"Action Memory is unavailable: {exc}")
        return
    st.markdown("**Pending Action Items**")
    _safe_dataframe(pending, "No pending action items in the current workspace.")
    st.markdown("**Handled Action Items**")
    _safe_dataframe(
        [
            {
                "action_id": item.get("action_id"),
                "title": item.get("title"),
                "status": item.get("status"),
                "feedback_reason": _feedback_reason(item),
                "updated_at": item.get("updated_at"),
            }
            for item in handled
        ],
        "No handled action items in the current workspace.",
    )


def render_turns_section(user_id: str, workspace_id: str) -> None:
    st.subheader("Agent Turns")
    try:
        turns = list_agent_turns(user_id, workspace_id, limit=50, db_path=_get_db_path())
        traces = list_agent_traces(user_id, workspace_id, limit=5, db_path=_get_db_path())
    except Exception as exc:
        st.warning(f"Agent Turns are unavailable: {exc}")
        return
    _safe_dataframe(
        [
            {
                "created_at": item.get("created_at"),
                "turn_id": item.get("turn_id"),
                "mode": item.get("mode"),
                "user_query": item.get("user_query"),
                "final_answer": str(item.get("final_answer") or "")[:240],
            }
            for item in turns
        ],
        "No Agent Turns in the current workspace yet.",
    )
    st.caption(f"Recent trace count: {len(traces)}")


def render_reports_section(user_id: str, workspace_id: str) -> None:
    st.subheader("Reports")
    try:
        reports = list_reports(user_id, workspace_id, limit=50, db_path=_get_db_path())
    except Exception as exc:
        st.warning(f"Reports are unavailable: {exc}")
        return
    if not reports:
        st.info("No Reports in the current workspace yet.")
        return
    for report in reports:
        with st.expander(report.get("report_title") or "FinCopilot Multi-Agent Finance Report", expanded=False):
            st.caption(report.get("created_at") or "")
            st.markdown(report.get("report_summary") or "No report summary yet.")
            with st.expander("View Full Report Markdown", expanded=False):
                st.markdown(report.get("report_markdown") or "No full report body yet.")


def render_isolation_notice() -> None:
    st.subheader("Isolation Check")
    st.info(
        "This page only shows data for the current user_id and workspace_id. "
        "FinCopilot does not read memory across users or workspaces. "
        "Future RAG retrieval must filter by user_id and workspace_id first."
    )


def render_workspace_clear_panel(user_id: str, workspace_id: str) -> None:
    st.subheader("Current Workspace Cleanup")
    st.warning("Cleanup only affects the current user_id / workspace_id and does not delete users or workspaces.")
    confirm_text = st.text_input("Type CLEAR to confirm cleanup", key="workspace_clear_confirm_text")
    cleanup_options = {
        "Clear Business Memory only": clear_workspace_business_memory,
        "Clear User Feedback only": clear_workspace_feedback,
        "Clear Action Memory only": clear_workspace_actions,
        "Clear Turns / Traces / Reports only": clear_workspace_turns_traces_reports,
        "Clear all Memory data in the current Workspace": clear_current_workspace_all_data,
    }
    selected = st.selectbox("Cleanup scope", list(cleanup_options.keys()), key="workspace_clear_scope")
    if st.button("Run cleanup", key="workspace_clear_execute"):
        if confirm_text != "CLEAR":
            st.error("Type CLEAR to confirm cleanup for the current workspace.")
            return
        try:
            result = cleanup_options[selected](user_id, workspace_id, db_path=_get_db_path())
            st.success(f"Cleanup completed: {result}")
            st.rerun()
        except Exception as exc:
            st.error(f"Cleanup failed: {exc}")


def render_rag_future_note() -> None:
    st.subheader("RAG Future Note")
    st.caption(
        "V2.3 currently uses structured memory retrieval, not vector retrieval. "
        "business_memory reserves embedding_text and retrieval_tags for future workspace-scoped RAG."
    )


def render_memory_management_page(user_id: str, workspace_id: str) -> None:
    render_current_identity_card(user_id, workspace_id)
    render_workspace_switcher(user_id)
    render_workspace_stats(user_id, workspace_id)
    render_business_memory_section(user_id, workspace_id)
    render_feedback_section(user_id, workspace_id)
    render_action_memory_section(user_id, workspace_id)
    render_turns_section(user_id, workspace_id)
    render_reports_section(user_id, workspace_id)
    render_isolation_notice()
    render_workspace_clear_panel(user_id, workspace_id)
    render_rag_future_note()
