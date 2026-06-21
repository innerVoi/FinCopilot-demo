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


DISCLAIMER = "本回复仅用于财务整理和风险提醒，不构成投资、税务、法律、债务处置或专业财务建议。"


def build_placeholder_assistant_reply(user_query: str) -> str:
    """Build a rule-based placeholder reply before real Agent API integration."""
    query = (user_query or "").strip()
    if any(keyword in query for keyword in ["现金流", "钱够", "余额", "够不够"]):
        reply = (
            "我会优先检查预算、发票、现金流和异常支出。当前版本可以在 Agent 工作台中选择"
            "“检查未来 30 天现金流是否安全”来查看完整流程。"
        )
    elif any(keyword in query for keyword in ["异常", "可疑", "支出", "重复"]):
        reply = (
            "我会结合规则异常和 LOF 模型结果，找出最值得核查的支出。当前版本可以在 Agent 工作台中选择"
            "“处理本月最可疑的异常支出”。"
        )
    elif any(keyword in query for keyword in ["目标", "促销", "进货", "预算", "计划"]):
        reply = (
            "我会检查现金流、目标进度和行动项，帮助你评估当前计划是否稳妥，并把建议同步到行动中心。"
        )
    else:
        reply = (
            "我可以帮助你检查现金流、异常支出、发票压力和财务目标，并把多 Agent 建议沉淀为行动项和报告。"
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


def run_and_record_chat_turn(user_query: str, agent_context_summary: dict | None = None) -> dict:
    """Run one chat turn and persist all UI-facing outputs."""
    st.session_state["agent_chat_state"] = append_user_message(
        st.session_state["agent_chat_state"],
        user_query,
    )
    turn_result = run_multi_agent_turn(
        user_query,
        agent_context_summary=agent_context_summary,
        chat_state=st.session_state["agent_chat_state"],
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
    st.header("和 FinCopilot 对话")
    status = get_agent_api_status()
    if status["enabled"]:
        st.success(f"Agent API 已启用，模型：{status['model']}。")
    else:
        st.info(f"当前使用 fallback 模式：{status['reason']}")
    st.caption("Manager Agent 只负责理解任务和规划调用哪些专业 Agent，不直接做财务计算。所有关键数值仍来自本地 Python 工具。")

    col_clear, col_mode = st.columns([1, 3])
    if col_clear.button("清空对话"):
        st.session_state["agent_chat_state"] = reset_agent_chat_state()
        st.success("对话已清空。")
        st.rerun()
    latest_turn = st.session_state["agent_chat_state"].get("latest_turn_result")
    if latest_turn:
        col_mode.caption(f"最近一次对话模式：{latest_turn.get('mode', 'fallback')}")

    with st.expander("查看当前 Agent 可用上下文摘要"):
        if agent_context_summary:
            st.json(agent_context_summary)
        else:
            st.info("当前还没有可用的 Agent 上下文摘要。")

    pending_query = st.session_state.pop("pending_chat_query", None)
    if pending_query:
        run_and_record_chat_turn(pending_query, agent_context_summary=agent_context_summary)

    for message_index, message in enumerate(st.session_state["agent_chat_state"]["messages"]):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            metadata = message.get("metadata") or {}
            if message["role"] == "assistant" and metadata:
                st.caption(f"Multi-Agent mode: {metadata.get('mode', 'fallback')}")
                with st.expander("查看 Multi-Agent Trace"):
                    st.json(metadata.get("trace", {}))
                with st.expander("查看 Manager Agent Plan"):
                    st.json(metadata.get("manager_plan", {}))
                with st.expander("查看 Manager 选择的工具摘要"):
                    st.json(metadata.get("tool_results", []))
                with st.expander("查看工具调用轨迹"):
                    st.json(metadata.get("tool_trace", {}))
                with st.expander("查看 Specialist Agents 输出"):
                    st.json(metadata.get("specialist_outputs", {}))
                with st.expander("查看 Safety Result"):
                    st.json(metadata.get("safety_result", {}))
                with st.expander("查看 Multi-Agent Trace Markdown"):
                    st.markdown(trace_to_markdown(metadata.get("trace", {})))
                with st.expander("查看 Multi-Agent Trace Summary"):
                    st.json(metadata.get("agent_trace_summary", {}))
                with st.expander("查看本轮生成的行动项"):
                    chat_action_items = metadata.get("chat_action_items", [])
                    if chat_action_items:
                        st.dataframe(chat_action_items, use_container_width=True)
                    else:
                        st.info("本轮没有生成新的行动项。")
                with st.expander("查看本轮 Multi-Agent 报告"):
                    report_markdown = metadata.get("report_markdown", "")
                    if report_markdown:
                        st.markdown(report_markdown)
                        st.text_area(
                            "复制本轮 Multi-Agent 报告",
                            report_markdown,
                            height=320,
                            key=f"copy_report_{message_index}",
                        )
                    else:
                        st.info("本轮暂无 Multi-Agent 报告。")

    latest_turn = st.session_state["agent_chat_state"].get("latest_turn_result")
    if latest_turn:
        st.subheader("最新建议行动")
        for action in latest_turn.get("suggested_actions", []):
            st.markdown(f"- {action}")
        st.subheader("仍需补充的信息")
        for question in latest_turn.get("clarifying_questions", []):
            st.markdown(f"- {question}")
        st.subheader("来自 Agent Chat 的正式行动项")
        chat_action_items = latest_turn.get("chat_action_items", [])
        if chat_action_items:
            summary = summarize_chat_action_items(
                st.session_state["agent_chat_state"].get("chat_action_items", [])
            )
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Chat 行动项", summary.get("total", 0))
            col2.metric("高优先级", summary.get("high", 0))
            col3.metric("待处理", summary.get("pending", 0))
            col4.metric("已完成", summary.get("done", 0))
            st.dataframe(chat_action_items, use_container_width=True)
        else:
            st.info("最近一轮没有生成正式行动项。")

    user_query = st.chat_input("问我一个小微企业财务问题，例如：未来 30 天现金流安全吗？")
    if user_query:
        run_and_record_chat_turn(user_query, agent_context_summary=agent_context_summary)
        st.rerun()

    st.caption("建议：需要完整任务规划时，可进入“Agent 工作台”选择一个财务任务。")
