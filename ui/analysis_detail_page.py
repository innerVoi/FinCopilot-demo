import pandas as pd
import streamlit as st

from src.safety import get_disclaimer


EMPTY_STATE = "暂无数据。请先在 Copilot 主界面上传数据，或使用默认样例数据。"


def _is_non_empty_df(value) -> bool:
    return isinstance(value, pd.DataFrame) and not value.empty


def _format_money(value):
    try:
        if value is None or pd.isna(value):
            value = 0.0
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return "$0.00"


def _format_percent(value):
    try:
        if value is None or pd.isna(value):
            value = 0.0
        value = float(value)
        if value <= 1:
            value *= 100
        return f"{value:.1f}%"
    except (TypeError, ValueError):
        return "0.0%"


def _format_days(value):
    if value == float("inf"):
        return "充足"
    try:
        return f"{float(value):,.1f} 天"
    except (TypeError, ValueError):
        return "暂无"


def _show_dataframe(title: str, dataframe):
    st.subheader(title)
    if _is_non_empty_df(dataframe):
        st.dataframe(dataframe, use_container_width=True)
    else:
        st.info(EMPTY_STATE)


def _safe_columns(dataframe, columns):
    if not isinstance(dataframe, pd.DataFrame):
        return dataframe
    selected = [column for column in columns if column in dataframe.columns]
    return dataframe[selected] if selected else dataframe


def render_budget_detail_tab(transactions_df=None, budget_result=None):
    """
    Render budget and categorization details.
    """
    budget_result = budget_result or {}
    summary = budget_result.get("summary", {}) if isinstance(budget_result, dict) else {}
    if not summary and not _is_non_empty_df(transactions_df):
        st.info(EMPTY_STATE)
        return

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("总收入", _format_money(summary.get("total_income")))
    col2.metric("总支出", _format_money(summary.get("total_expense")))
    col3.metric("净现金流", _format_money(summary.get("net_cashflow")))
    col4.metric("支出收入比", _format_percent(summary.get("expense_income_ratio")))

    col5, col6 = st.columns(2)
    col5.metric("Top 支出类别", summary.get("top_expense_category") or "暂无")
    col6.metric("最大单笔支出", _format_money(summary.get("largest_expense")))

    _show_dataframe("类别支出表", budget_result.get("category_spending"))
    _show_dataframe("月度摘要", budget_result.get("monthly_summary"))
    transaction_columns = [
        "date",
        "description",
        "merchant",
        "amount",
        "type",
        "account",
        "category",
        "category_confidence",
        "category_reason",
    ]
    _show_dataframe("已分类交易表", _safe_columns(transactions_df, transaction_columns))


def render_invoice_cashflow_detail_tab(invoices_df=None, invoice_result=None, cashflow_result=None):
    """
    Render invoice and cashflow details.
    """
    invoice_result = invoice_result or {}
    summary = invoice_result.get("summary", {}) if isinstance(invoice_result, dict) else {}
    cashflow_result = cashflow_result or {}
    if not summary and not cashflow_result and not _is_non_empty_df(invoices_df):
        st.info(EMPTY_STATE)
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("发票总额", _format_money(summary.get("total_invoice_amount")))
    col2.metric("已付金额", _format_money(summary.get("paid_invoice_amount")))
    col3.metric("未付金额", _format_money(summary.get("unpaid_invoice_amount")))

    col4, col5, col6 = st.columns(3)
    col4.metric("逾期金额", _format_money(summary.get("overdue_invoice_amount")))
    col5.metric("7 天内到期", _format_money(summary.get("due_7d_amount")))
    col6.metric("30 天内到期", _format_money(summary.get("due_30d_amount")))

    st.subheader("现金流摘要")
    col7, col8, col9 = st.columns(3)
    col7.metric("风险等级", cashflow_result.get("risk_level", "unknown"))
    col8.metric("30 天预计余额", _format_money(cashflow_result.get("projected_balance_30d")))
    col9.metric("现金缓冲天数", _format_days(cashflow_result.get("cash_buffer_days")))
    for reason in cashflow_result.get("risk_reasons", []) or []:
        st.markdown(f"- {reason}")
    _show_dataframe("发票明细表", invoices_df)
    _show_dataframe("未来 7 天到期发票", invoice_result.get("upcoming_7d"))
    _show_dataframe("逾期发票", invoice_result.get("overdue"))


def render_anomaly_detail_tab(rule_anomalies_df=None, lof_result_df=None, risk_explanation=None):
    """
    Render anomaly detail tables and method notes.
    """
    rule_count = len(rule_anomalies_df) if isinstance(rule_anomalies_df, pd.DataFrame) else 0
    high_count = 0
    medium_count = 0
    if _is_non_empty_df(lof_result_df) and "risk_level" in lof_result_df.columns:
        high_count = int((lof_result_df["risk_level"] == "high").sum())
        medium_count = int((lof_result_df["risk_level"] == "medium").sum())
    col1, col2, col3 = st.columns(3)
    col1.metric("规则异常数量", rule_count)
    col2.metric("LOF 高风险数量", high_count)
    col3.metric("LOF 中风险数量", medium_count)

    _show_dataframe("规则异常表", rule_anomalies_df)
    _show_dataframe("模型异常表", lof_result_df)
    if risk_explanation:
        st.subheader("单条异常解释结果")
        st.json(risk_explanation)
    with st.expander("异常检测方法说明", expanded=False):
        st.markdown(
            "规则异常用于识别明确的金额、重复、逾期等模式；LOF 模型用于提示偏离历史局部模式的交易。"
            "这些结果仅用于核查提醒，不代表欺诈认定。"
        )


def render_goal_detail_tab(goals_df=None, goal_result=None):
    """
    Render financial goal details.
    """
    goal_result = goal_result or {}
    summary = goal_result.get("summary", {}) if isinstance(goal_result, dict) else {}
    goals_analysis_df = goal_result.get("goals") if isinstance(goal_result, dict) else None
    if not summary and not _is_non_empty_df(goals_df):
        st.info(EMPTY_STATE)
        return

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("目标数量", summary.get("goal_count", 0))
    col2.metric("总目标金额", _format_money(summary.get("total_target_amount")))
    col3.metric("已完成金额", _format_money(summary.get("total_current_amount")))
    col4.metric("剩余金额", _format_money(summary.get("total_remaining_amount")))

    col5, col6, col7 = st.columns(3)
    col5.metric("目标完成率", _format_percent(summary.get("overall_progress_percent")))
    col6.metric("高风险目标", summary.get("high_risk_goal_count", 0))
    col7.metric("中风险目标", summary.get("medium_risk_goal_count", 0))
    _show_dataframe("目标明细表", goals_analysis_df if goals_analysis_df is not None else goals_df)


def render_agent_trace_detail_tab(agent_chat_state: dict | None = None, workspace: dict | None = None):
    """
    Render Manager, Tool, Specialist, Trace and workspace details.
    """
    agent_chat_state = agent_chat_state or {}
    workspace = workspace or {}
    latest_turn = agent_chat_state.get("latest_turn_result") or {}
    if not latest_turn and not workspace:
        st.info("当前还没有 Agent 执行记录。请先在 Copilot 主界面提问。")
        return
    st.subheader("最近一次 Manager Plan")
    st.json(latest_turn.get("manager_plan", {}))
    st.subheader("Tool Results")
    st.json(latest_turn.get("tool_results", []))
    st.subheader("Specialist Outputs")
    st.json(latest_turn.get("specialist_outputs", {}))
    st.subheader("Multi-Agent Trace")
    st.json(latest_turn.get("trace", agent_chat_state.get("latest_trace", {})))
    st.subheader("Safety Result")
    st.json(latest_turn.get("safety_result", {}))
    with st.expander("原 v2 Agent Workspace", expanded=False):
        st.json(workspace)
    workflow_report = workspace.get("workflow_report_markdown", "")
    if workflow_report:
        with st.expander("Workflow Report", expanded=False):
            st.markdown(workflow_report)


def render_analysis_detail_page(
    transactions_df=None,
    invoices_df=None,
    goals_df=None,
    budget_result=None,
    invoice_result=None,
    cashflow_result=None,
    goal_result=None,
    rule_anomalies_df=None,
    lof_result_df=None,
    risk_explanation=None,
    workspace=None,
    agent_chat_state=None,
):
    """
    Render the unified analysis detail page.
    """
    st.header("分析详情")
    tabs = st.tabs(["预算与分类", "发票与现金流", "异常支出", "财务目标", "Agent 执行轨迹"])
    with tabs[0]:
        render_budget_detail_tab(transactions_df=transactions_df, budget_result=budget_result)
    with tabs[1]:
        render_invoice_cashflow_detail_tab(
            invoices_df=invoices_df,
            invoice_result=invoice_result,
            cashflow_result=cashflow_result,
        )
    with tabs[2]:
        render_anomaly_detail_tab(
            rule_anomalies_df=rule_anomalies_df,
            lof_result_df=lof_result_df,
            risk_explanation=risk_explanation,
        )
    with tabs[3]:
        render_goal_detail_tab(goals_df=goals_df, goal_result=goal_result)
    with tabs[4]:
        render_agent_trace_detail_tab(agent_chat_state=agent_chat_state, workspace=workspace)
    st.caption(get_disclaimer())
