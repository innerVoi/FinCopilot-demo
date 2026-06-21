import pandas as pd
import streamlit as st

from agent_api.action_sync import summarize_chat_action_items
from agent_api.session_state import ensure_agent_chat_state
from agent_api.trace_builder import trace_to_markdown
from src.safety import get_disclaimer


def _ensure_rows(items):
    rows = []
    for item in items or []:
        if isinstance(item, dict):
            rows.append(item)
    return rows


def _show_table(title: str, rows):
    st.subheader(title)
    rows = _ensure_rows(rows)
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
    else:
        st.info("当前暂无可展示数据。")


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
    all_items = chat_items + workspace_items + suggested_items
    chat_summary = summarize_chat_action_items(chat_items)
    priority_counts = {"high": 0, "medium": 0, "low": 0}
    status_counts = {"pending": 0, "in_progress": 0, "done": 0, "ignored": 0}
    for item in all_items:
        priority = str(item.get("priority", "medium")).lower()
        status = str(item.get("status", "pending")).lower()
        if priority in priority_counts:
            priority_counts[priority] += 1
        if status in status_counts:
            status_counts[status] += 1

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("行动项总数", len(all_items))
    col2.metric("高优先级", priority_counts["high"])
    col3.metric("中优先级", priority_counts["medium"])
    col4.metric("低优先级", priority_counts["low"])
    col5, col6, col7, col8 = st.columns(4)
    col5.metric("pending", status_counts["pending"])
    col6.metric("in_progress", status_counts["in_progress"])
    col7.metric("done", status_counts["done"])
    col8.metric("ignored", status_counts["ignored"])
    st.caption(f"Chat-derived action items：{chat_summary.get('total', 0)}")
    _show_table("行动项表格", all_items)
    high_items = [item for item in all_items if str(item.get("priority", "")).lower() == "high"]
    _show_table("Top 高优先级行动项", high_items[:5])


def render_reports_tab(workspace: dict | None = None, agent_chat_state: dict | None = None):
    """
    Render report previews and downloads.
    """
    workspace = workspace or {}
    agent_chat_state = ensure_agent_chat_state(agent_chat_state or {})
    latest_report = agent_chat_state.get("latest_report_markdown", "")
    workflow_report = workspace.get("workflow_report_markdown", "") or workspace.get("workflow_report", "")

    st.subheader("最近一次 Multi-Agent 对话报告")
    if latest_report:
        with st.expander("报告 Markdown 预览", expanded=True):
            st.markdown(latest_report)
        st.download_button(
            "下载 Multi-Agent 报告",
            data=latest_report.encode("utf-8"),
            file_name="fincopilot_multi_agent_report.md",
            mime="text/markdown",
            key="action_report_multi_agent_report_download",
        )
    else:
        st.info("当前还没有 Multi-Agent 对话报告。请先在 Copilot 主界面提问。")

    st.subheader("最近一次 Agent Workflow Report")
    if workflow_report:
        with st.expander("Workflow Report 预览", expanded=False):
            st.markdown(workflow_report)
        st.download_button(
            "下载 Workflow Report",
            data=str(workflow_report).encode("utf-8"),
            file_name="fincopilot_workflow_report.md",
            mime="text/markdown",
            key="action_report_workflow_report_download",
        )
    else:
        st.info("当前还没有 Agent Workflow Report。")


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
        st.info("当前还没有 Multi-Agent Trace。")

    with st.expander("Trace 技术摘要", expanded=False):
        st.json(
            {
                "trace": latest_trace,
                "tool_trace": latest_turn.get("tool_trace", {}),
                "safety_result": latest_turn.get("safety_result", {}),
            }
        )
    trace_download = latest_trace_markdown or trace_to_markdown(latest_trace or {})
    st.download_button(
        "下载 Trace",
        data=trace_download.encode("utf-8"),
        file_name="fincopilot_multi_agent_trace.md",
        mime="text/markdown",
        key="action_report_trace_download",
    )


def render_action_report_page(workspace: dict | None = None, agent_chat_state: dict | None = None):
    """
    Render the unified action and report page.
    """
    st.header("行动与报告")
    tabs = st.tabs(["行动项", "报告", "Trace"])
    with tabs[0]:
        render_action_items_tab(workspace=workspace, agent_chat_state=agent_chat_state)
    with tabs[1]:
        render_reports_tab(workspace=workspace, agent_chat_state=agent_chat_state)
    with tabs[2]:
        render_trace_tab(agent_chat_state=agent_chat_state)
    st.caption(get_disclaimer())
