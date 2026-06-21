import streamlit as st


def _has_rows(dataframe) -> bool:
    return dataframe is not None and not getattr(dataframe, "empty", True)


def _row_count(dataframe) -> int:
    if dataframe is None:
        return 0
    try:
        return int(len(dataframe))
    except TypeError:
        return 0


def get_data_status_summary(transactions_df=None, invoices_df=None, goals_df=None) -> dict:
    """
    Return data availability and row counts for the main Copilot UI.
    """
    has_transactions = _has_rows(transactions_df)
    has_invoices = _has_rows(invoices_df)
    has_goals = _has_rows(goals_df)
    ready_tasks = []
    if has_transactions:
        ready_tasks.extend(["anomaly_review", "weekly_action_plan"])
    if has_transactions and has_invoices:
        ready_tasks.append("cashflow_check")
    if has_invoices:
        ready_tasks.append("invoice_priority")
    if has_transactions and has_goals:
        ready_tasks.append("goal_plan")
    return {
        "has_transactions": has_transactions,
        "has_invoices": has_invoices,
        "has_goals": has_goals,
        "transactions_count": _row_count(transactions_df),
        "invoices_count": _row_count(invoices_df),
        "goals_count": _row_count(goals_df),
        "transaction_count": _row_count(transactions_df),
        "invoice_count": _row_count(invoices_df),
        "goal_count": _row_count(goals_df),
        "ready_tasks": ready_tasks,
        "missing_for_cashflow": [] if has_transactions and has_invoices else [
            item for item, available in [("transactions", has_transactions), ("invoices", has_invoices)] if not available
        ],
        "missing_for_goal": [] if has_transactions and has_goals else [
            item for item, available in [("transactions", has_transactions), ("goals", has_goals)] if not available
        ],
    }


def render_data_status_card(
    transactions_df=None,
    invoices_df=None,
    goals_df=None,
    agent_api_status: dict | None = None,
):
    """
    Display current data and Agent status.
    """
    summary = get_data_status_summary(transactions_df, invoices_df, goals_df)
    agent_api_status = agent_api_status or {}
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        "交易流水",
        "已加载" if summary["has_transactions"] else "未上传",
        f"{summary['transactions_count']} 条",
    )
    col2.metric(
        "发票数据",
        "已加载" if summary["has_invoices"] else "未上传",
        f"{summary['invoices_count']} 条",
    )
    col3.metric(
        "财务目标",
        "已加载" if summary["has_goals"] else "未上传",
        f"{summary['goals_count']} 条",
    )
    col4.metric(
        "Agent 状态",
        "真实 Agent" if agent_api_status.get("mode") == "api_agent" else "fallback",
        agent_api_status.get("model", ""),
    )
    return summary


def render_quick_upload_panel():
    """
    Render quick upload controls for the Copilot main page.
    """
    with st.expander("先给 FinCopilot 一些数据", expanded=False):
        st.caption("你可以上传交易流水、发票和财务目标；也可以直接使用默认样例数据体验完整流程。")
        use_sample_data = st.checkbox(
            "未上传时使用默认样例数据",
            value=True,
            key="v22_use_sample_data",
        )
        transactions_file = st.file_uploader(
            "上传交易流水 CSV",
            type=["csv"],
            key="v22_transactions_file",
        )
        invoices_file = st.file_uploader(
            "上传发票 CSV",
            type=["csv"],
            key="v22_invoices_file",
        )
        goals_file = st.file_uploader(
            "上传财务目标 CSV",
            type=["csv"],
            key="v22_goals_file",
        )
        st.caption("未上传时会使用内置 sample data，方便快速演示。")
    return {
        "transactions_file": transactions_file,
        "invoices_file": invoices_file,
        "goals_file": goals_file,
        "use_sample_data": use_sample_data,
    }


def render_upload_help():
    """
    Render brief upload guidance.
    """
    st.caption(
        "上传交易、发票和目标 CSV 后，你可以直接问：未来 30 天现金流安全吗？"
        "哪些支出最可疑？我该优先处理哪些发票或行动项？"
    )
