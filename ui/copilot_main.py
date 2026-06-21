import streamlit as st

from agent_api.answer_presenter import build_answer_presentation
from agent_api.config import get_agent_api_status
from agent_api.detail_preview_builder import build_detail_preview
from agent_api.session_state import ensure_agent_chat_state, get_default_agent_chat_state
from ui.chat_page import run_and_record_chat_turn
from ui.inline_detail_preview import render_inline_detail_preview
from ui.onboarding_panel import render_onboarding_panel
from ui.result_cards import render_answer_presentation
from ui.task_recommendations import (
    build_recommended_tasks,
    get_next_step_hints,
    render_recommended_task_cards,
)
from ui.upload_panel import render_data_status_card, render_quick_upload_panel, render_upload_help


RECOMMENDED_QUESTIONS = [
    "未来 30 天现金流安全吗？",
    "这个月哪些支出最可疑？",
    "有哪些发票或付款要优先处理？",
    "我应该先收钱、付款还是控费？",
    "帮我生成本周财务行动清单。",
]


def _initialize_chat_state():
    if "agent_chat_state" not in st.session_state:
        st.session_state["agent_chat_state"] = get_default_agent_chat_state()
    st.session_state["agent_chat_state"] = ensure_agent_chat_state(
        st.session_state["agent_chat_state"]
    )


def _display_agent_status(status: dict):
    if status.get("mode") == "api_agent":
        st.success(status.get("user_message", "当前使用真实 Agent 分析。"))
    else:
        st.info(status.get("user_message", "当前真实 Agent 暂不可用，系统将自动使用 fallback 分析。"))


def _display_turn_result(turn_result: dict | None, agent_context_summary: dict | None = None):
    if not turn_result:
        st.info("还没有分析结果。你可以选择一个推荐问题，或直接输入一个财务问题。")
        return

    presentation = build_answer_presentation(turn_result)
    render_answer_presentation(presentation, turn_result=turn_result)
    detail_preview = build_detail_preview(turn_result, agent_context_summary=agent_context_summary)
    render_inline_detail_preview(detail_preview, turn_result=turn_result)
    st.caption("完整行动项和报告已同步到“行动与报告”页面。")


def render_copilot_main(
    agent_context_summary: dict | None = None,
    transactions_df=None,
    invoices_df=None,
    goals_df=None,
    latest_agent_turn: dict | None = None,
):
    """
    Render the V2.2 Copilot main interface.
    """
    _initialize_chat_state()
    latest_turn = latest_agent_turn or st.session_state["agent_chat_state"].get("latest_turn_result")
    st.title("💸 FinCopilot V2.2")
    st.caption("在一个主界面上传数据、提出问题，并获得多 Agent 财务分析结果。")

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

    manual_query = st.chat_input("直接问我一个财务问题，例如：未来 30 天现金流安全吗？")
    pending_query = st.session_state.pop("v22_pending_query", None)
    user_query = manual_query or task_query or pending_query
    if user_query:
        run_and_record_chat_turn(user_query, agent_context_summary=agent_context_summary)
        st.rerun()

    _display_turn_result(latest_turn, agent_context_summary=agent_context_summary)
