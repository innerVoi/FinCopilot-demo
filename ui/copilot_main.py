import streamlit as st

from agent_api.answer_presenter import build_answer_presentation
from agent_api.config import get_agent_api_status
from agent_api.detail_preview_builder import build_detail_preview
from agent_api.session_state import ensure_agent_chat_state, get_default_agent_chat_state
from memory.retrieval import get_memory_context_for_task
from memory.workspace import get_current_identity
from ui.chat_page import run_and_record_chat_turn
from ui.inline_detail_preview import render_inline_detail_preview
from ui.memory_feedback_panel import render_feedback_panel
from ui.memory_panel import render_memory_context_summary
from ui.onboarding_panel import render_onboarding_panel
from ui.result_cards import render_answer_presentation
from ui.task_recommendations import (
    build_recommended_tasks,
    get_next_step_hints,
    render_recommended_task_cards,
)
from ui.upload_panel import render_data_status_card, render_quick_upload_panel, render_upload_help


RECOMMENDED_QUESTIONS = [
    "Is cash flow safe for the next 30 days?",
    "Which expenses look most suspicious this month?",
    "Which invoices or payments should be prioritized?",
    "Should I collect cash, pay bills, or control expenses first?",
    "Generate my finance action plan for this week.",
]


def _initialize_chat_state():
    if "agent_chat_state" not in st.session_state:
        st.session_state["agent_chat_state"] = get_default_agent_chat_state()
    st.session_state["agent_chat_state"] = ensure_agent_chat_state(
        st.session_state["agent_chat_state"]
    )


def _display_agent_status(status: dict):
    if status.get("mode") == "api_agent":
        st.success(status.get("user_message", "Live Agent analysis is active."))
    else:
        st.info(status.get("user_message", "The live Agent API is unavailable. FinCopilot will automatically use fallback analysis."))


def _display_turn_result(turn_result: dict | None, agent_context_summary: dict | None = None):
    if not turn_result:
        st.info("No analysis yet. Choose a recommended question or type a finance question directly.")
        return

    presentation = build_answer_presentation(turn_result)
    render_answer_presentation(presentation, turn_result=turn_result)
    if turn_result.get("persisted"):
        st.success("This analysis has been saved.")
    elif turn_result.get("persistence_errors"):
        st.warning("Analysis completed, but saving the history failed: " + "；".join(turn_result.get("persistence_errors", [])))
    detail_preview = build_detail_preview(turn_result, agent_context_summary=agent_context_summary)
    render_inline_detail_preview(detail_preview, turn_result=turn_result)
    st.caption("Full action items and reports have been synced to the Actions & Reports page.")
    identity = get_current_identity(st.session_state)
    render_feedback_panel(
        user_id=identity["user_id"],
        workspace_id=identity["workspace_id"],
        latest_turn_result=turn_result,
    )


def render_copilot_main(
    agent_context_summary: dict | None = None,
    transactions_df=None,
    invoices_df=None,
    goals_df=None,
    latest_agent_turn: dict | None = None,
):
    """
    Render the V2.3 Copilot main interface.
    """
    _initialize_chat_state()
    latest_turn = latest_agent_turn or st.session_state["agent_chat_state"].get("latest_turn_result")
    st.title("💸 FinCopilot V2.3")
    st.caption("An AI finance copilot for small businesses. Upload data, ask questions, and get multi-agent financial analysis in one place.")

    status = get_agent_api_status()
    render_data_status_card(
        transactions_df=transactions_df,
        invoices_df=invoices_df,
        goals_df=goals_df,
        agent_api_status=status,
    )
    _display_agent_status(status)
    render_onboarding_panel(
        transactions_df=transactions_df,
        invoices_df=invoices_df,
        goals_df=goals_df,
        agent_api_status=status,
        latest_agent_turn=latest_turn,
    )

    render_quick_upload_panel()
    render_upload_help()
    for hint in get_next_step_hints(
        transactions_df=transactions_df,
        invoices_df=invoices_df,
        goals_df=goals_df,
        latest_agent_turn=latest_turn,
    ):
        st.info(hint)

    tasks = build_recommended_tasks(
        transactions_df=transactions_df,
        invoices_df=invoices_df,
        goals_df=goals_df,
        latest_agent_turn=latest_turn,
    )
    task_query = render_recommended_task_cards(tasks)
    try:
        identity = get_current_identity(st.session_state)
        memory_context = get_memory_context_for_task(
            user_id=identity["user_id"],
            workspace_id=identity["workspace_id"],
            task_type="general_finance_summary",
            user_query=task_query,
            limit=8,
            db_path=st.session_state.get("memory_db_path"),
        )
        render_memory_context_summary(memory_context)
    except Exception as exc:
        st.info(f"Business Memory is temporarily unavailable. This analysis is mainly based on uploaded data. {exc}")

    manual_query = st.chat_input("Ask a finance question, for example: Is cash flow safe for the next 30 days?")
    pending_query = st.session_state.pop("v22_pending_query", None)
    user_query = manual_query or task_query or pending_query
    if user_query:
        identity = get_current_identity(st.session_state)
        run_and_record_chat_turn(
            user_query,
            agent_context_summary=agent_context_summary,
            user_id=identity["user_id"],
            workspace_id=identity["workspace_id"],
        )
        st.rerun()

    _display_turn_result(latest_turn, agent_context_summary=agent_context_summary)
