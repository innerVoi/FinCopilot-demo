import streamlit as st

from agent_api.action_sync import summarize_chat_action_items
from src.safety import get_disclaimer


def safe_get_nested(data, keys, default=None):
    """Safely read nested dictionaries."""
    current = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def _format_money(value):
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return "$0.00"


def _format_percent(value):
    try:
        return f"{float(value):.1f}%"
    except (TypeError, ValueError):
        return "0.0%"


def render_assistant_home(
    cashflow_result=None,
    invoice_result=None,
    goal_result=None,
    workspace=None,
    use_llm=False,
    latest_agent_turn=None,
    chat_action_items=None,
):
    """Render the Assistant-first home page."""
    cashflow_result = cashflow_result or {}
    invoice_result = invoice_result or {}
    goal_result = goal_result or {}
    workspace = workspace or {}

    st.title("FinCopilot：小微企业财务行动助手")
    st.caption("当前版本：FinCopilot V2.1 完整 Demo")
    st.caption(
        "把交易、发票、现金流、异常支出和财务目标串起来，帮你判断钱是否安全、风险在哪里、下一步该做什么。"
    )

    entry_col1, entry_col2, entry_col3 = st.columns(3)
    entry_col1.info("直接提问：进入“和 FinCopilot 对话”")
    entry_col2.info("查看任务过程：进入“Agent 工作台”")
    entry_col3.info("跟进行动项：进入“行动中心”")

    st.subheader("我优先帮你回答三件事")
    col1, col2, col3 = st.columns(3)
    col1.info("我现在的钱够不够？")
    col2.warning("哪些支出有问题？")
    col3.success("接下来该怎么收钱、花钱和控制风险？")

    st.subheader("当前经营状态概览")
    progress_summary = workspace.get("progress_summary", {})
    action_summary = workspace.get("action_summary", {})
    invoice_summary = invoice_result.get("summary", {})
    goal_summary = goal_result.get("summary", {})

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("现金流风险", cashflow_result.get("risk_level", "unknown"))
    col2.metric(
        "未来 30 天预计余额",
        _format_money(cashflow_result.get("projected_balance_30d", 0)),
    )
    col3.metric("高优先级行动项", action_summary.get("high", 0))
    col4.metric("待处理行动项", progress_summary.get("active_count", 0))

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("异常行动项", action_summary.get("by_source", {}).get("rule_anomaly", 0))
    col6.metric(
        "逾期发票金额",
        _format_money(invoice_summary.get("overdue_invoice_amount", 0)),
    )
    col7.metric(
        "目标完成率",
        _format_percent(goal_summary.get("overall_progress_percent", 0)),
    )
    col8.metric("完成率", f"{progress_summary.get('completion_rate', 0.0) * 100:.0f}%")

    st.subheader("你可以这样问我")
    example_questions = [
        "未来 30 天现金流安全吗？",
        "这个月哪些支出最可疑？",
        "有哪些发票或付款要优先处理？",
        "我能不能花 5000 做促销？",
        "我应该先收钱、付款还是控费？",
        "帮我生成本周财务行动清单。",
    ]
    for question in example_questions:
        if st.button(question, key=f"example_{question}"):
            st.session_state["pending_chat_query"] = question
            st.info("问题已记录，可进入“和 FinCopilot 对话”页面继续。")

    st.subheader("最近一次 Agent 对话")
    if latest_agent_turn:
        col1, col2, col3, col4 = st.columns(4)
        manager_plan = latest_agent_turn.get("manager_plan", {})
        col1.metric("任务类型", manager_plan.get("intent", "unknown"))
        col2.metric("Agent 模式", latest_agent_turn.get("mode", "fallback"))
        col3.metric("建议行动", len(latest_agent_turn.get("suggested_actions", [])))
        col4.metric("需补充信息", len(latest_agent_turn.get("clarifying_questions", [])))
    else:
        st.info("还没有进行 Agent 对话。")

    st.subheader("Agent Chat 行动同步")
    chat_summary = summarize_chat_action_items(chat_action_items or [])
    col1, col2, col3 = st.columns(3)
    col1.metric("Chat 行动项", chat_summary.get("total", 0))
    col2.metric("高优先级 Chat 行动项", chat_summary.get("high", 0))
    col3.metric(
        "最近一次 Agent 模式",
        (latest_agent_turn or {}).get("mode", "暂无"),
    )

    st.subheader("本周最重要提醒")
    high_active = progress_summary.get("high_priority_active_count", 0)
    active_count = progress_summary.get("active_count", 0)
    if active_count:
        st.warning(
            f"当前仍有 {active_count} 个行动项未关闭，其中 {high_active} 个为高优先级。建议优先处理现金流、逾期发票和高风险异常支出相关任务。"
        )
    else:
        st.info("当前还没有生成行动项。请先进入 Agent 工作台选择任务，或在对话页提出一个财务问题。")

    if use_llm:
        st.caption("已启用大模型解释选项；Agent Chat API 调用仍由 ENABLE_AGENT_API 和 OPENAI_API_KEY 控制。")
    st.caption(f"安全边界：{get_disclaimer()}")
