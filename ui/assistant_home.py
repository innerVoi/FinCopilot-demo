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

    st.title("FinCopilot: Finance Action Assistant for Small Businesses")
    st.caption("Current version: FinCopilot V2.3 Memory-Augmented Agentic CFO Copilot")
    st.caption(
        "Connect transactions, invoices, cash flow, suspicious expenses, and goals to understand whether cash is safe, where risk sits, and what to do next."
    )

    entry_col1, entry_col2, entry_col3 = st.columns(3)
    entry_col1.info("Ask directly: open FinCopilot Chat")
    entry_col2.info("Review task flow: open Agent Workspace")
    entry_col3.info("Track action items: open Action Center")

    st.subheader("Three Questions FinCopilot Prioritizes")
    col1, col2, col3 = st.columns(3)
    col1.info("Do I have enough cash right now?")
    col2.warning("Which expenses need review?")
    col3.success("What should I collect, pay, or control next?")

    st.subheader("Current Business Status")
    progress_summary = workspace.get("progress_summary", {})
    action_summary = workspace.get("action_summary", {})
    invoice_summary = invoice_result.get("summary", {})
    goal_summary = goal_result.get("summary", {})

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Cash-Flow Risk", cashflow_result.get("risk_level", "unknown"))
    col2.metric(
        "Projected 30-Day Balance",
        _format_money(cashflow_result.get("projected_balance_30d", 0)),
    )
    col3.metric("High-Priority Action Items", action_summary.get("high", 0))
    col4.metric("Pending Action Items", progress_summary.get("active_count", 0))

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Anomaly Action Items", action_summary.get("by_source", {}).get("rule_anomaly", 0))
    col6.metric(
        "Overdue Invoice Amount",
        _format_money(invoice_summary.get("overdue_invoice_amount", 0)),
    )
    col7.metric(
        "Goal Progress",
        _format_percent(goal_summary.get("overall_progress_percent", 0)),
    )
    col8.metric("Completion Rate", f"{progress_summary.get('completion_rate', 0.0) * 100:.0f}%")

    st.subheader("Questions to Try")
    example_questions = [
        "Is cash flow safe for the next 30 days?",
        "Which expenses look most suspicious this month?",
        "Which invoices or payments should be prioritized?",
        "Can I spend 5,000 on a promotion?",
        "Should I collect cash, pay invoices, or cut costs first?",
        "Generate this week's finance action plan.",
    ]
    for question in example_questions:
        if st.button(question, key=f"example_{question}"):
            st.session_state["pending_chat_query"] = question
            st.info("Question saved. Open FinCopilot Chat to continue.")

    st.subheader("Latest Agent Conversation")
    if latest_agent_turn:
        col1, col2, col3, col4 = st.columns(4)
        manager_plan = latest_agent_turn.get("manager_plan", {})
        col1.metric("Task Type", manager_plan.get("intent", "unknown"))
        col2.metric("Agent Mode", latest_agent_turn.get("mode", "fallback"))
        col3.metric("Suggested Actions", len(latest_agent_turn.get("suggested_actions", [])))
        col4.metric("Information Needed", len(latest_agent_turn.get("clarifying_questions", [])))
    else:
        st.info("No Agent conversation yet.")

    st.subheader("Agent Chat Action Sync")
    chat_summary = summarize_chat_action_items(chat_action_items or [])
    col1, col2, col3 = st.columns(3)
    col1.metric("Chat Action Items", chat_summary.get("total", 0))
    col2.metric("High-Priority Chat Action Items", chat_summary.get("high", 0))
    col3.metric(
        "Latest Agent Mode",
        (latest_agent_turn or {}).get("mode", "None"),
    )

    st.subheader("Top Reminder This Week")
    high_active = progress_summary.get("high_priority_active_count", 0)
    active_count = progress_summary.get("active_count", 0)
    if active_count:
        st.warning(
            f"There are still {active_count} open action items, including {high_active} high-priority items. Prioritize cash flow, overdue invoices, and high-risk suspicious-expense tasks."
        )
    else:
        st.info("No action items have been generated yet. Choose a task in Agent Workspace or ask a finance question in Chat.")

    if use_llm:
        st.caption("LLM explanation is enabled. Agent Chat API calls are still controlled by ENABLE_AGENT_API and OPENAI_API_KEY.")
    st.caption(f"Safety Boundaries: {get_disclaimer()}")
