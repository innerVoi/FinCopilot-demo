import pandas as pd
import streamlit as st

from agent_api.action_sync import summarize_chat_action_items
from agent_api.session_state import ensure_agent_chat_state
from agent_api.trace_builder import trace_to_markdown
from memory.action_memory_service import list_handled_action_items, list_pending_action_items
from memory.workspace import get_current_identity
from src.safety import get_disclaimer
from ui.action_feedback_panel import render_action_feedback_history, render_action_feedback_list


def _ensure_rows(items):
    rows = []
    for item in items or []:
        if isinstance(item, dict):
            rows.append(item)
    return rows


def _contains_han(value) -> bool:
    return any("\u4e00" <= character <= "\u9fff" for character in str(value or ""))


def _filter_english_demo_rows(rows):
    filtered = []
    for row in _ensure_rows(rows):
        visible_values = [
            row.get("title", ""),
            row.get("description", ""),
            row.get("due_date", ""),
            row.get("suggested_deadline", ""),
            row.get("reason", ""),
        ]
        if not any(_contains_han(value) for value in visible_values):
            filtered.append(row)
    return filtered


def _show_table(title: str, rows):
    st.subheader(title)
    rows = _ensure_rows(rows)
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
    else:
        st.info("No data to display yet.")


def _action_display_rows(rows):
    display_columns = [
        "action_id",
        "title",
        "description",
        "priority",
        "status",
        "source",
        "due_date",
        "updated_at",
    ]
    display_rows = []
    for row in _ensure_rows(rows):
        display_rows.append({column: row.get(column, "") for column in display_columns})
    return display_rows


def _clip_text(text: str, max_length: int = 900) -> str:
    value = str(text or "").strip()
    if len(value) <= max_length:
        return value
    return value[: max_length - 1].rstrip() + "..."


def _extract_report_summary(report_markdown: str) -> str:
    lines = [
        line.strip()
        for line in str(report_markdown or "").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    return _clip_text("\n\n".join(lines[:4])) if lines else "This report has been generated. Expand it to view the full content."


def _get_streamlit_session_state() -> dict:
    session_state = getattr(st, "session_state", None)
    return session_state if hasattr(session_state, "get") else {}


def render_action_items_tab(workspace: dict | None = None, agent_chat_state: dict | None = None):
    """
    Render action item management.
    """
    workspace = workspace or {}
    agent_chat_state = ensure_agent_chat_state(agent_chat_state or {})
    workspace_items = _ensure_rows(workspace.get("ranked_action_items", []))
    chat_items = _ensure_rows(agent_chat_state.get("chat_action_items", []))
    latest_turn = agent_chat_state.get("latest_turn_result") or {}
    suggested_items = [
        {"title": item, "priority": "medium", "status": "pending", "source": "suggested_actions"}
        for item in latest_turn.get("suggested_actions", []) or []
        if item
    ]
    all_items = _filter_english_demo_rows(chat_items + workspace_items + suggested_items)
    identity = get_current_identity(_get_streamlit_session_state())
    db_path = _get_streamlit_session_state().get("memory_db_path")
    try:
        pending_items = _filter_english_demo_rows(
            list_pending_action_items(identity["user_id"], identity["workspace_id"], db_path=db_path)
        )
        handled_items = _filter_english_demo_rows(
            list_handled_action_items(identity["user_id"], identity["workspace_id"], db_path=db_path)
        )
    except Exception:
        pending_items = []
        handled_items = []
    chat_summary = summarize_chat_action_items(chat_items)
    priority_counts = {"high": 0, "medium": 0, "low": 0}
    status_counts = {"pending": 0, "in_progress": 0, "done": 0, "ignored": 0}
    display_items = pending_items + handled_items if (pending_items or handled_items) else all_items
    for item in display_items:
        priority = str(item.get("priority", "medium")).lower()
        status = str(item.get("status", "pending")).lower()
        if priority in priority_counts:
            priority_counts[priority] += 1
        if status in status_counts:
            status_counts[status] += 1

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Action Items", len(display_items))
    col2.metric("High Priority", priority_counts["high"])
    col3.metric("Medium Priority", priority_counts["medium"])
    col4.metric("Low Priority", priority_counts["low"])
    col5, col6, col7, col8 = st.columns(4)
    col5.metric("pending", status_counts["pending"])
    col6.metric("in_progress", status_counts["in_progress"])
    col7.metric("done", status_counts["done"])
    col8.metric("ignored", status_counts["ignored"])
    st.caption(f"Chat-derived action items: {chat_summary.get('total', 0)}")
    if not pending_items and not handled_items and all_items:
        st.info("Action items have not been persisted yet. Complete an analysis on Copilot Home first.")
    _show_table("Pending Action Items", _action_display_rows(pending_items))
    if pending_items:
        render_action_feedback_list(
            user_id=identity["user_id"],
            workspace_id=identity["workspace_id"],
            action_items=pending_items,
            turn_id=latest_turn.get("turn_id"),
        )
    _show_table("Handled Action Items", _action_display_rows(handled_items))
    high_items = [item for item in display_items if str(item.get("priority", "")).lower() == "high"]
    _show_table("Top High-Priority Action Items", _action_display_rows(high_items[:5]))
    render_action_feedback_history(
        user_id=identity["user_id"],
        workspace_id=identity["workspace_id"],
    )


def render_reports_tab(workspace: dict | None = None, agent_chat_state: dict | None = None):
    """
    Render report previews and downloads.
    """
    workspace = workspace or {}
    agent_chat_state = ensure_agent_chat_state(agent_chat_state or {})
    latest_report = agent_chat_state.get("latest_report_markdown", "")
    workflow_report = workspace.get("workflow_report_markdown", "") or workspace.get("workflow_report", "")

    st.subheader("Latest Multi-Agent Conversation Report")
    if latest_report:
        st.markdown("**Report Title**")
        st.write("FinCopilot Multi-Agent Conversation Report")
        st.markdown("**Report Summary**")
        st.markdown(_extract_report_summary(latest_report))
        with st.expander("View Full Report Markdown", expanded=False):
            st.markdown(latest_report)
        st.download_button(
            "Download Multi-Agent Report",
            data=latest_report.encode("utf-8"),
            file_name="fincopilot_multi_agent_report.md",
            mime="text/markdown",
            key="action_report_multi_agent_report_download",
        )
    else:
        st.info("No Multi-Agent conversation report yet. Ask a question on Copilot Home first.")

    st.subheader("Latest Agent Workflow Report")
    if workflow_report:
        st.markdown("**Report Title**")
        st.write("Agent Workflow Report")
        st.markdown("**Report Summary**")
        st.markdown(_extract_report_summary(str(workflow_report)))
        with st.expander("View Full Workflow Report", expanded=False):
            st.markdown(workflow_report)
        st.download_button(
            "Download Workflow Report",
            data=str(workflow_report).encode("utf-8"),
            file_name="fincopilot_workflow_report.md",
            mime="text/markdown",
            key="action_report_workflow_report_download",
        )
    else:
        st.info("No Agent Workflow Report yet.")


def render_trace_tab(agent_chat_state: dict | None = None):
    """
    Render recent Multi-Agent Trace.
    """
    agent_chat_state = ensure_agent_chat_state(agent_chat_state or {})
    latest_trace = agent_chat_state.get("latest_trace", {})
    latest_trace_markdown = agent_chat_state.get("latest_trace_markdown", "")
    latest_turn = agent_chat_state.get("latest_turn_result") or {}
    if latest_trace_markdown:
        st.markdown(latest_trace_markdown)
    elif latest_trace:
        st.markdown(trace_to_markdown(latest_trace))
    else:
        st.info("No Multi-Agent trace is available yet.")

    with st.expander("Trace Technical Summary", expanded=False):
        st.json(
            {
                "trace": latest_trace,
                "tool_trace": latest_turn.get("tool_trace", {}),
                "safety_result": latest_turn.get("safety_result", {}),
            }
        )
    trace_download = latest_trace_markdown or trace_to_markdown(latest_trace or {})
    st.download_button(
        "Download Trace",
        data=trace_download.encode("utf-8"),
        file_name="fincopilot_multi_agent_trace.md",
        mime="text/markdown",
        key="action_report_trace_download",
    )


def render_action_report_page(workspace: dict | None = None, agent_chat_state: dict | None = None):
    """
    Render the unified action and report page.
    """
    st.header("Actions & Reports")
    tabs = st.tabs(["Action Items", "Reports", "Trace"])
    with tabs[0]:
        render_action_items_tab(workspace=workspace, agent_chat_state=agent_chat_state)
    with tabs[1]:
        render_reports_tab(workspace=workspace, agent_chat_state=agent_chat_state)
    with tabs[2]:
        render_trace_tab(agent_chat_state=agent_chat_state)
    st.caption(get_disclaimer())
