import streamlit as st

from agent_api.action_sync import merge_chat_action_items, summarize_chat_action_items
from agent_api.config import get_agent_api_status
from agent_api.orchestrator import run_multi_agent_turn
from agent_api.session_state import (
    add_turn_result,
    append_assistant_message,
    append_user_message,
    ensure_agent_chat_state,
    get_chat_action_items,
    get_default_agent_chat_state,
    reset_agent_chat_state,
    update_chat_action_items,
    update_latest_reports,
)
from agent_api.trace_builder import trace_to_markdown
from memory.workspace import get_current_identity


DISCLAIMER = (
    "This response is for financial organization, risk reminders, and educational support only. "
    "It is not investment, tax, legal, debt-resolution, or professional financial advice."
)


def build_placeholder_assistant_reply(user_query: str) -> str:
    """Build a rule-based placeholder reply before real Agent API integration."""
    query = (user_query or "").strip().lower()
    if any(keyword in query for keyword in ["cash flow", "cashflow", "balance", "cash", "runway"]):
        reply = (
            "I will first review budget, invoices, cash flow, and suspicious expenses. "
            "Use the Copilot Home workflow to run the full 30-day cash-flow check."
        )
    elif any(keyword in query for keyword in ["suspicious", "expense", "anomaly", "duplicate", "unusual"]):
        reply = (
            "I will combine rule-based anomalies and LOF model signals to identify expenses that deserve review."
        )
    elif any(keyword in query for keyword in ["goal", "promotion", "purchase", "budget", "plan"]):
        reply = (
            "I will review cash flow, goal progress, and action items to help evaluate whether the plan is safe."
        )
    else:
        reply = (
            "I can help review cash flow, suspicious expenses, invoice pressure, and goals, then turn recommendations into action items and reports."
        )
    return f"{reply}\n\n{DISCLAIMER}"


def initialize_chat_state():
    """Initialize chat messages."""
    if "agent_chat_state" not in st.session_state:
        st.session_state["agent_chat_state"] = get_default_agent_chat_state()
    st.session_state["agent_chat_state"] = ensure_agent_chat_state(
        st.session_state["agent_chat_state"]
    )


def sync_turn_outputs_to_chat_state(turn_result: dict) -> None:
    """Persist action items and Markdown reports from one Agent Chat turn."""
    new_chat_actions = turn_result.get("chat_action_items", [])
    existing_chat_actions = get_chat_action_items(st.session_state["agent_chat_state"])
    merged_chat_actions = merge_chat_action_items(existing_chat_actions, new_chat_actions)
    st.session_state["agent_chat_state"] = update_chat_action_items(
        st.session_state["agent_chat_state"],
        merged_chat_actions,
    )
    st.session_state["agent_chat_state"] = update_latest_reports(
        st.session_state["agent_chat_state"],
        report_markdown=turn_result.get("report_markdown", ""),
        trace_markdown=turn_result.get("trace_markdown", ""),
    )


def run_and_record_chat_turn(
    user_query: str,
    agent_context_summary: dict | None = None,
    user_id: str | None = None,
    workspace_id: str | None = None,
) -> dict:
    """Run one chat turn and persist all UI-facing outputs."""
    st.session_state["agent_chat_state"] = append_user_message(
        st.session_state["agent_chat_state"],
        user_query,
    )
    turn_result = run_multi_agent_turn(
        user_query,
        agent_context_summary=agent_context_summary,
        chat_state=st.session_state["agent_chat_state"],
        user_id=user_id,
        workspace_id=workspace_id,
        memory_db_path=st.session_state.get("memory_db_path"),
    )
    sync_turn_outputs_to_chat_state(turn_result)
    st.session_state["agent_chat_state"] = append_assistant_message(
        st.session_state["agent_chat_state"],
        turn_result.get("assistant_reply", ""),
        metadata=turn_result,
    )
    st.session_state["agent_chat_state"] = add_turn_result(
        st.session_state["agent_chat_state"],
        turn_result=turn_result,
        trace=turn_result.get("trace"),
    )
    return turn_result


def render_chat_page(agent_context_summary: dict | None = None):
    """Render the FinCopilot chat placeholder page."""
    initialize_chat_state()
    st.header("FinCopilot Chat")
    status = get_agent_api_status()
    if status["enabled"]:
        st.success(f"Agent API is enabled. Model: {status['model']}.")
    else:
        st.info(f"Currently using fallback mode: {status['reason']}")
    st.caption("The Manager Agent understands the task and plans which specialist agents to call. It does not perform financial calculations directly; key numbers still come from local Python tools.")

    col_clear, col_mode = st.columns([1, 3])
    if col_clear.button("Clear Chat"):
        st.session_state["agent_chat_state"] = reset_agent_chat_state()
        st.success("Chat cleared.")
        st.rerun()
    latest_turn = st.session_state["agent_chat_state"].get("latest_turn_result")
    if latest_turn:
        col_mode.caption(f"Latest conversation mode: {latest_turn.get('mode', 'fallback')}")

    with st.expander("View Current Agent Context Summary"):
        if agent_context_summary:
            st.json(agent_context_summary)
        else:
            st.info("No Agent context summary is available yet.")

    pending_query = st.session_state.pop("pending_chat_query", None)
    if pending_query:
        identity = get_current_identity(st.session_state)
        run_and_record_chat_turn(
            pending_query,
            agent_context_summary=agent_context_summary,
            user_id=identity["user_id"],
            workspace_id=identity["workspace_id"],
        )

    for message_index, message in enumerate(st.session_state["agent_chat_state"]["messages"]):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            metadata = message.get("metadata") or {}
            if message["role"] == "assistant" and metadata:
                st.caption(f"Multi-Agent mode: {metadata.get('mode', 'fallback')}")
                with st.expander("View Multi-Agent Trace"):
                    st.json(metadata.get("trace", {}))
                with st.expander("View Manager Agent Plan"):
                    st.json(metadata.get("manager_plan", {}))
                with st.expander("View Manager-Selected Tool Summary"):
                    st.json(metadata.get("tool_results", []))
                with st.expander("View Tool Call Trace"):
                    st.json(metadata.get("tool_trace", {}))
                with st.expander("View Specialist Agent Outputs"):
                    st.json(metadata.get("specialist_outputs", {}))
                with st.expander("View Safety Result"):
                    st.json(metadata.get("safety_result", {}))
                with st.expander("View Multi-Agent Trace Markdown"):
                    st.markdown(trace_to_markdown(metadata.get("trace", {})))
                with st.expander("View Multi-Agent Trace Summary"):
                    st.json(metadata.get("agent_trace_summary", {}))
                with st.expander("View Action Items Generated This Turn"):
                    chat_action_items = metadata.get("chat_action_items", [])
                    if chat_action_items:
                        st.dataframe(chat_action_items, use_container_width=True)
                    else:
                        st.info("No new action items were generated this turn.")
                with st.expander("View This Turn's Multi-Agent Report"):
                    report_markdown = metadata.get("report_markdown", "")
                    if report_markdown:
                        st.markdown(report_markdown)
                        st.text_area(
                            "Copy This Turn's Multi-Agent Report",
                            report_markdown,
                            height=320,
                            key=f"copy_report_{message_index}",
                        )
                    else:
                        st.info("No Multi-Agent Report was generated for this turn.")

    latest_turn = st.session_state["agent_chat_state"].get("latest_turn_result")
    if latest_turn:
        st.subheader("Latest Suggested Actions")
        for action in latest_turn.get("suggested_actions", []):
            st.markdown(f"- {action}")
        st.subheader("Information Still Needed")
        for question in latest_turn.get("clarifying_questions", []):
            st.markdown(f"- {question}")
        st.subheader("Official Action Items from Agent Chat")
        chat_action_items = latest_turn.get("chat_action_items", [])
        if chat_action_items:
            summary = summarize_chat_action_items(
                st.session_state["agent_chat_state"].get("chat_action_items", [])
            )
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Chat Action Items", summary.get("total", 0))
            col2.metric("High Priority", summary.get("high", 0))
            col3.metric("Pending", summary.get("pending", 0))
            col4.metric("Done", summary.get("done", 0))
            st.dataframe(chat_action_items, use_container_width=True)
        else:
            st.info("The latest turn did not generate official action items.")

    user_query = st.chat_input("Ask a small-business finance question, for example: Is cash flow safe for the next 30 days?")
    if user_query:
        identity = get_current_identity(st.session_state)
        run_and_record_chat_turn(
            user_query,
            agent_context_summary=agent_context_summary,
            user_id=identity["user_id"],
            workspace_id=identity["workspace_id"],
        )
        st.rerun()

    st.caption("Tip: for full task planning, open Agent Workspace and select a finance task.")
