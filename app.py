from pathlib import Path

import pandas as pd
import streamlit as st

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv():
        return False

from agent_api.context_builder import build_agent_context_summary
from agent_api.action_sync import summarize_chat_action_items
from agent_api.session_state import ensure_agent_chat_state, update_chat_action_items
from agent_api.trace_builder import trace_to_markdown
from agent.action_item import action_items_to_markdown
from agent.agent_state import (
    get_business_context,
    get_default_agent_state,
    get_saved_action_note,
    reset_action_progress,
    reset_agent_state,
    update_action_status,
    update_agent_state,
)
from agent.clarification import get_questions_for_task
from agent.priority_ranker import action_items_to_dataframe, filter_action_items
from agent.progress_summary import action_items_to_status_markdown
from agent.progress_tracker import filter_actions_by_status, get_recent_progress_events
from agent.report_exporter import build_report_filename, encode_markdown_for_download
from agent.task_templates import get_task_options_for_ui
from agent.tool_registry import list_available_tools
from agent.workspace_builder import build_agent_workspace
from memory.db import initialize_memory_db
from memory.repository import ensure_default_workspace
from memory.workspace import get_current_identity
from src.anomaly_model import run_lof_detection
from src.anomaly_rules import run_rule_based_anomaly_detection
from src.budget_analyzer import analyze_budget
from src.cashflow_analyzer import analyze_cashflow
from src.categorizer import add_transaction_categories
from src.data_loader import load_goals, load_invoices, load_transactions
from src.goal_analyzer import analyze_goals
from src.invoice_analyzer import analyze_invoices
from src.risk_explainer import explain_transaction_risk
from src.safety import get_disclaimer
from src.summary_generator import generate_planning_summary
from agent_api.config import get_agent_api_status
from ui.assistant_home import render_assistant_home
from ui.chat_page import render_chat_page
from ui.action_report_page import render_action_report_page as render_v23_action_report_page
from ui.analysis_detail_page import render_analysis_detail_page as render_v23_analysis_detail_page
from ui.copilot_main import render_copilot_main
from ui.data_settings_page import render_data_settings_page as render_v23_data_settings_page
from ui.navigation import render_sidebar_navigation


load_dotenv()

DATA_DIR = Path("data")
DEFAULT_TRANSACTIONS_PATH = DATA_DIR / "sample_transactions.csv"
DEFAULT_INVOICES_PATH = DATA_DIR / "sample_invoices.csv"
DEFAULT_GOALS_PATH = DATA_DIR / "sample_goals.csv"

STATUS_OPTIONS = [
    "pending",
    "in_progress",
    "verified_normal",
    "needs_follow_up",
    "done",
    "ignored",
]

CHAT_ACTION_STATUS_OPTIONS = ["pending", "in_progress", "done", "ignored"]


def load_dataset(uploaded_file, default_path, loader):
    source = uploaded_file if uploaded_file is not None else default_path
    return loader(source)


def show_dataframe(title, dataframe):
    st.subheader(title)
    if dataframe is None:
        st.info("暂无可展示数据。")
    else:
        st.dataframe(dataframe, use_container_width=True)


def format_money(value):
    if value is None or pd.isna(value):
        value = 0.0
    return f"${value:,.2f}"


def format_percent(value):
    if value is None or pd.isna(value):
        value = 0.0
    return f"{value:.1%}"


def format_days(value):
    if value == float("inf"):
        return "充足"
    return f"{value:,.1f} 天"


def format_anomaly_option(row):
    return (
        f"{row.get('date', '')} | {row.get('merchant', '')} | "
        f"{row.get('amount', '')} | "
        f"{row.get('anomaly_type', row.get('model_name', ''))} | "
        f"{row.get('risk_level', '')}"
    )


def stringify_cell(value):
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    if isinstance(value, dict):
        return ", ".join(f"{key}: {item}" for key, item in value.items())
    return value


def render_risk_explanation(explanation):
    st.subheader("风险解释")
    st.markdown(f"**风险摘要：** {explanation.get('risk_summary', '')}")
    st.markdown("**可能原因：**")
    for item in explanation.get("possible_reasons", []):
        st.markdown(f"- {item}")
    st.markdown("**建议动作：**")
    for item in explanation.get("recommended_actions", []):
        st.markdown(f"- {item}")
    st.caption(explanation.get("disclaimer", ""))


def prepare_analysis(transactions_file, invoices_file, goals_file):
    result = {
        "transactions_df": None,
        "raw_transactions_df": None,
        "invoices_df": None,
        "goals_df": None,
        "budget_result": None,
        "invoice_result": None,
        "cashflow_result": None,
        "goal_result": None,
        "rule_anomalies_df": None,
        "lof_result_df": None,
        "lof_error": None,
        "load_error": None,
        "reference_date": None,
    }
    try:
        transactions_df = load_dataset(
            transactions_file,
            DEFAULT_TRANSACTIONS_PATH,
            load_transactions,
        )
        raw_transactions_df = transactions_df.copy()
        invoices_df = load_dataset(invoices_file, DEFAULT_INVOICES_PATH, load_invoices)
        goals_df = load_dataset(goals_file, DEFAULT_GOALS_PATH, load_goals)
        transactions_df = add_transaction_categories(transactions_df)
        budget_result = analyze_budget(transactions_df)
        reference_date = (
            transactions_df["date"].max() if "date" in transactions_df.columns else None
        )
        invoice_result = analyze_invoices(invoices_df, reference_date=reference_date)
        cashflow_result = analyze_cashflow(
            transactions_df=transactions_df,
            invoice_result=invoice_result,
            horizon_days=30,
        )
        goal_result = analyze_goals(
            goals_df=goals_df,
            budget_result=budget_result,
            cashflow_result=cashflow_result,
            reference_date=reference_date,
        )
        rule_anomalies_df = run_rule_based_anomaly_detection(
            transactions_df=transactions_df,
            invoice_result=invoice_result,
            reference_date=reference_date,
        )
        try:
            lof_result_df = run_lof_detection(transactions_df)
        except ValueError as error:
            result["lof_error"] = str(error)
        result.update(
            {
                "transactions_df": transactions_df,
                "raw_transactions_df": raw_transactions_df,
                "invoices_df": invoices_df,
                "goals_df": goals_df,
                "budget_result": budget_result,
                "invoice_result": invoice_result,
                "cashflow_result": cashflow_result,
                "goal_result": goal_result,
                "rule_anomalies_df": rule_anomalies_df,
                "lof_result_df": lof_result_df,
                "reference_date": reference_date,
            }
        )
    except (FileNotFoundError, ValueError) as error:
        result["load_error"] = str(error)
    return result


def build_workspace(selected_task_id, analysis):
    agent_context = {
        "transactions_df": analysis["transactions_df"],
        "invoices_df": analysis["invoices_df"],
        "goals_df": analysis["goals_df"],
        "budget_result": analysis["budget_result"],
        "invoice_result": analysis["invoice_result"],
        "cashflow_result": analysis["cashflow_result"],
        "goal_result": analysis["goal_result"],
        "rule_anomalies_df": analysis["rule_anomalies_df"],
        "lof_result_df": analysis["lof_result_df"],
    }
    return build_agent_workspace(
        task_id=selected_task_id,
        context=agent_context,
        user_inputs=get_business_context(st.session_state["agent_state"]),
        agent_state=st.session_state["agent_state"],
    )


def render_data_management(analysis, transactions_file, invoices_file, goals_file):
    st.header("数据管理")
    st.info("上传控件位于左侧 sidebar；Not uploaded时系统使用 data/ 目录下的默认样例数据。")
    if analysis["load_error"]:
        st.error(analysis["load_error"])
        return

    st.success("数据读取成功。")
    st.markdown(
        f"""
        **当前数据来源**
        - Transactions：{"用户上传" if transactions_file else "默认样例"}
        - Invoices：{"用户上传" if invoices_file else "默认样例"}
        - Goals：{"用户上传" if goals_file else "默认样例"}
        """
    )
    show_dataframe("Transactions预览", analysis["raw_transactions_df"])
    show_dataframe("分类后Transactions预览", analysis["transactions_df"])
    show_dataframe("Invoices预览", analysis["invoices_df"])
    show_dataframe("Goals预览", analysis["goals_df"])

    with st.expander("Field Guide与数据质量提示"):
        st.markdown(
            """
            - Transactions需要包含日期、金额、类型、商户或描述等字段。
            - Invoices需要包含金额、到期日 and 支付Status。
            - Goals需要包含目标金额、当前金额、截止日期 and 优先级。
            - 当前 Demo 仅做整理 and Risk Alert，不连接真实银行账户或发票系统。
            """
        )


def render_budget_page(analysis):
    st.header("预算与分类")
    st.info("展示交易分类结果、预算统计、类别支出结构 and 月度收支情况。")
    budget_result = analysis["budget_result"]
    transactions_df = analysis["transactions_df"]
    if budget_result is None or transactions_df is None:
        st.warning("请先在“Data & Settings”页确认数据读取成功。")
        return
    summary = budget_result["summary"]

    col1, col2, col3 = st.columns(3)
    col1.metric("总收入", format_money(summary["total_income"]))
    col2.metric("总支出", format_money(summary["total_expense"]))
    col3.metric("净现金流", format_money(summary["net_cashflow"]))

    col4, col5, col6, col7 = st.columns(4)
    col4.metric("支出收入比", format_percent(summary["expense_income_ratio"]))
    col5.metric("固定支出占比", format_percent(summary["fixed_expense_ratio"]))
    col6.metric("最大单笔支出", format_money(summary["largest_expense"]))
    col7.metric("支出最多的类别", summary["top_expense_category"])

    show_dataframe("类别支出统计", budget_result["category_spending"])
    show_dataframe("月度收支统计", budget_result["monthly_summary"])
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
    transaction_columns = [
        column for column in transaction_columns if column in transactions_df.columns
    ]
    show_dataframe("分类后的交易明细", transactions_df[transaction_columns])


def render_invoice_page(analysis):
    st.header("发票与现金流")
    st.info("现金流分析基于上传数据估算，不代表真实账户余额或专业财务预测。")
    invoice_result = analysis["invoice_result"]
    cashflow_result = analysis["cashflow_result"]
    if invoice_result is None:
        st.warning("请先在“Data & Settings”页确认数据读取成功。")
        return

    summary = invoice_result["summary"]
    col1, col2, col3 = st.columns(3)
    col1.metric("发票总额", format_money(summary["total_invoice_amount"]))
    col2.metric("已支付金额", format_money(summary["paid_invoice_amount"]))
    col3.metric("未支付金额", format_money(summary["unpaid_invoice_amount"]))

    col4, col5, col6 = st.columns(3)
    col4.metric("逾期金额", format_money(summary["overdue_invoice_amount"]))
    col5.metric("未来 7 天到期金额", format_money(summary["due_7d_amount"]))
    col6.metric("未来 30 天到期金额", format_money(summary["due_30d_amount"]))

    show_dataframe("未来 7 天到期发票", invoice_result["upcoming_7d"])
    show_dataframe("未来 30 天到期发票", invoice_result["upcoming_30d"])
    show_dataframe("逾期发票", invoice_result["overdue"])

    if cashflow_result is None:
        return
    st.subheader("现金流风险分析")
    col1, col2, col3 = st.columns(3)
    col1.metric("当前余额估算", format_money(cashflow_result["current_balance_estimate"]))
    col2.metric("未来 30 天预计余额", format_money(cashflow_result["projected_balance_30d"]))
    col3.metric("现金流风险等级", cashflow_result["risk_level"])

    col4, col5, col6 = st.columns(3)
    col4.metric("未来 30 天待付发票", format_money(cashflow_result["upcoming_invoice_outflow_30d"]))
    col5.metric("未来 30 天预计运营现金流", format_money(cashflow_result["projected_operating_cashflow_30d"]))
    col6.metric("现金缓冲天数", format_days(cashflow_result["cash_buffer_days"]))

    st.markdown("**风险原因：**")
    for reason in cashflow_result.get("risk_reasons", []):
        st.markdown(f"- {reason}")
    st.markdown("**建议动作：**")
    for action in cashflow_result.get("recommended_actions", []):
        st.markdown(f"- {action}")


def render_anomaly_page(analysis, use_llm):
    st.header("异常支出识别")
    st.info("规则/统计识别适合明确异常；LOF Model适合发现偏离局部交易模式的潜在异常。")
    detection_method = st.radio(
        "选择异常检测方式",
        ["规则/统计识别", "LOF Model识别"],
        key="financial_analysis_detection_method",
    )

    if detection_method == "规则/统计识别":
        rule_anomalies_df = analysis["rule_anomalies_df"]
        if rule_anomalies_df is None:
            st.warning("请先在“Data & Settings”页确认数据读取成功。")
        elif rule_anomalies_df.empty:
            st.success("当前未发现明显异常支出。")
        else:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("异常总数", len(rule_anomalies_df))
            col2.metric("高风险异常数", int((rule_anomalies_df["risk_level"] == "high").sum()))
            col3.metric("中风险异常数", int((rule_anomalies_df["risk_level"] == "medium").sum()))
            col4.metric("低风险异常数", int((rule_anomalies_df["risk_level"] == "low").sum()))
            rule_columns = [
                "date",
                "merchant",
                "description",
                "amount",
                "category",
                "anomaly_type",
                "risk_level",
                "reason",
                "recommended_action",
            ]
            rule_columns = [column for column in rule_columns if column in rule_anomalies_df.columns]
            show_dataframe("异常支出列表", rule_anomalies_df[rule_columns])
            option_rows = rule_anomalies_df.reset_index(drop=True)
            selected_index = st.selectbox(
                "选择一条规则异常生成解释",
                option_rows.index,
                format_func=lambda index: format_anomaly_option(option_rows.loc[index]),
            )
            if st.button("生成该异常的风险解释", key="rule_explanation_button"):
                render_risk_explanation(
                    explain_transaction_risk(option_rows.loc[selected_index], use_llm=use_llm)
                )
    else:
        lof_result_df = analysis["lof_result_df"]
        if analysis["lof_error"]:
            st.error(f"LOF Model检测失败：{analysis['lof_error']}")
        elif lof_result_df is None:
            st.warning("请先在“Data & Settings”页确认数据读取成功。")
        elif lof_result_df.empty:
            st.warning("当前没有可用于 LOF 检测的交易数据。")
        else:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("交易总数", len(lof_result_df))
            col2.metric("高风险交易数", int((lof_result_df["risk_level"] == "high").sum()))
            col3.metric("中风险交易数", int((lof_result_df["risk_level"] == "medium").sum()))
            col4.metric("低风险交易数", int((lof_result_df["risk_level"] == "low").sum()))
            show_only_risky = st.checkbox("仅展示中高风险交易", value=True)
            display_df = lof_result_df.copy()
            if show_only_risky:
                display_df = display_df[display_df["risk_level"].isin(["high", "medium"])]
            display_columns = [
                "date",
                "merchant",
                "description",
                "amount",
                "category",
                "account",
                "anomaly_score",
                "risk_level",
                "model_evidence",
            ]
            display_columns = [column for column in display_columns if column in display_df.columns]
            show_dataframe("LOF 检测结果表", display_df[display_columns])
            explanation_candidates = lof_result_df[lof_result_df["risk_level"].isin(["high", "medium"])]
            if explanation_candidates.empty:
                explanation_candidates = lof_result_df
            option_rows = explanation_candidates.reset_index(drop=True)
            selected_index = st.selectbox(
                "选择一条 LOF 交易生成解释",
                option_rows.index,
                format_func=lambda index: format_anomaly_option(option_rows.loc[index]),
            )
            if st.button("生成该交易的风险解释", key="lof_explanation_button"):
                render_risk_explanation(
                    explain_transaction_risk(option_rows.loc[selected_index], use_llm=use_llm)
                )


def render_goals_page(analysis):
    st.header("Goals")
    goal_result = analysis["goal_result"]
    if goal_result is None:
        st.warning("请先在“Data & Settings”页确认数据读取成功。")
        return
    goal_summary = goal_result["summary"]
    goals_analysis_df = goal_result["goals"]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("目标总数", goal_summary["goal_count"])
    col2.metric("已完成目标", goal_summary["completed_goal_count"])
    col3.metric("高风险目标", goal_summary["high_risk_goal_count"])
    col4.metric("中风险目标", goal_summary["medium_risk_goal_count"])

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("总目标金额", format_money(goal_summary["total_target_amount"]))
    col6.metric("当前已完成金额", format_money(goal_summary["total_current_amount"]))
    col7.metric("剩余缺口", format_money(goal_summary["total_remaining_amount"]))
    col8.metric("整体完成率", f"{goal_summary['overall_progress_percent']:.1f}%")

    display_columns = [
        "goal_id",
        "goal_name",
        "priority",
        "target_amount",
        "current_amount",
        "remaining_amount",
        "progress_percent",
        "due_date",
        "days_remaining",
        "required_monthly_saving",
        "goal_risk_level",
        "goal_status",
        "goal_recommendation",
    ]
    display_columns = [column for column in display_columns if column in goals_analysis_df.columns]
    show_dataframe("目标进度分析", goals_analysis_df[display_columns])
    st.caption(get_disclaimer())


def render_financial_analysis(analysis, use_llm):
    st.header("财务分析")
    tab_budget, tab_invoice, tab_anomaly, tab_goals = st.tabs(
        ["预算与分类", "发票与现金流", "异常支出识别", "Goals"]
    )
    with tab_budget:
        render_budget_page(analysis)
    with tab_invoice:
        render_invoice_page(analysis)
    with tab_anomaly:
        render_anomaly_page(analysis, use_llm)
    with tab_goals:
        render_goals_page(analysis)


def render_action_list(workspace, selected_task_id, editable=True, key_prefix=""):
    ranked_actions = workspace.get("ranked_action_items", [])
    if not ranked_actions:
        st.info("当前还没有Action Items。请先在“Copilot Home”提问，或在“Analysis Details”中查看 Agent 执行轨迹。")
        return

    progress_summary = workspace.get("progress_summary", {})
    action_summary = workspace.get("action_summary", {})
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Action Items总数", action_summary.get("total", 0))
    col2.metric("高优先级", action_summary.get("high", 0))
    col3.metric("仍需处理", progress_summary.get("active_count", 0))
    col4.metric("完成率", f"{progress_summary.get('completion_rate', 0.0) * 100:.0f}%")

    status_filter = st.selectbox(
        "按Status筛选",
        ["全部"] + STATUS_OPTIONS,
        key=f"{key_prefix}action_status_filter",
    )
    filtered_actions = ranked_actions
    if status_filter != "全部":
        filtered_actions = filter_actions_by_status(filtered_actions, status=status_filter)

    actions_df = action_items_to_dataframe(filtered_actions)
    if actions_df.empty:
        st.info("当前筛选条件下没有Action Items。")
    else:
        st.dataframe(actions_df, use_container_width=True)

    st.markdown("**Top Action Items详情：**")
    for item in filtered_actions[:3]:
        with st.expander(f"{item.get('priority', '')} | {item.get('status', '')} | {item.get('title', '')}"):
            st.markdown(f"**Source: ** {item.get('source', '')}")
            st.markdown(f"**原因：** {item.get('reason', '')}")
            st.markdown(f"**建议截止时间：** {item.get('suggested_deadline', '')}")
            st.markdown("**建议步骤：**")
            for step in item.get("recommended_steps", []):
                st.markdown(f"- {step}")
            st.caption(item.get("safety_note", ""))

    if editable:
        st.markdown("**更新Action ItemsStatus: **")
        for item in filtered_actions[:5]:
            action_id = item.get("action_id", "")
            current_status = item.get("status", "pending")
            if current_status not in STATUS_OPTIONS:
                current_status = "pending"
            with st.expander(f"{current_status} | {item.get('title', '')}"):
                new_status = st.selectbox(
                    "更新Status",
                    STATUS_OPTIONS,
                    index=STATUS_OPTIONS.index(current_status),
                    key=f"{key_prefix}status_{selected_task_id}_{action_id}",
                )
                note = st.text_area(
                    "处理备注，可选",
                    value=get_saved_action_note(
                        st.session_state["agent_state"],
                        selected_task_id,
                        action_id,
                    ),
                    key=f"{key_prefix}note_{selected_task_id}_{action_id}",
                )
                if st.button("保存Status", key=f"{key_prefix}save_status_{selected_task_id}_{action_id}"):
                    st.session_state["agent_state"] = update_action_status(
                        st.session_state["agent_state"],
                        task_id=selected_task_id,
                        action_id=action_id,
                        new_status=new_status,
                        note=note,
                    )
                    st.success("Action ItemsStatus已保存。")
                    st.rerun()

    with st.expander("最近Status更新记录"):
        recent_events = get_recent_progress_events(st.session_state["agent_state"], limit=10)
        if recent_events:
            st.dataframe(pd.DataFrame(recent_events), use_container_width=True)
        else:
            st.info("当前还没有Action ItemsStatus更新记录。")


def render_chat_action_items_section():
    st.subheader("来自 Agent Chat 的Action Items")
    st.session_state["agent_chat_state"] = ensure_agent_chat_state(
        st.session_state.get("agent_chat_state", {})
    )
    chat_action_items = st.session_state["agent_chat_state"].get("chat_action_items", [])
    if not chat_action_items:
        st.info("当前还没有来自 Agent Chat 的Action Items。请先在“Copilot Home”提出一个问题。")
        return

    summary = summarize_chat_action_items(chat_action_items)
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Chat Action Items总数", summary.get("total", 0))
    col2.metric("高优先级", summary.get("high", 0))
    col3.metric("中优先级", summary.get("medium", 0))
    col4.metric("低优先级", summary.get("low", 0))
    col5.metric("已完成", summary.get("done", 0))

    display_rows = [
        {
            "action_id": item.get("action_id", ""),
            "title": item.get("title", ""),
            "priority": item.get("priority", ""),
            "source": item.get("source", ""),
            "status": item.get("status", "pending"),
            "suggested_deadline": item.get("suggested_deadline", ""),
            "reason": item.get("reason", ""),
        }
        for item in chat_action_items
    ]
    st.dataframe(pd.DataFrame(display_rows), use_container_width=True)

    st.markdown("**更新 Chat Action ItemsStatus: **")
    updated_items = [dict(item) for item in chat_action_items]
    for index, item in enumerate(updated_items):
        action_id = item.get("action_id", f"C{index + 1:03d}")
        current_status = item.get("status", "pending")
        if current_status not in CHAT_ACTION_STATUS_OPTIONS:
            current_status = "pending"
        with st.expander(f"{current_status} | {item.get('title', '')}"):
            new_status = st.selectbox(
                "更新Status",
                CHAT_ACTION_STATUS_OPTIONS,
                index=CHAT_ACTION_STATUS_OPTIONS.index(current_status),
                key=f"chat_action_status_{action_id}",
            )
            updated_items[index]["status"] = new_status
            st.markdown(f"**Priority: ** {item.get('priority', '')}")
            st.markdown(f"**建议截止时间：** {item.get('suggested_deadline', '')}")
            st.markdown(f"**原因：** {item.get('reason', '')}")
            st.markdown("**建议步骤：**")
            for step in item.get("recommended_steps", []):
                st.markdown(f"- {step}")
            st.caption(item.get("safety_note", ""))

    if st.button("保存 Chat Action ItemsStatus", key="save_chat_action_statuses"):
        st.session_state["agent_chat_state"] = update_chat_action_items(
            st.session_state["agent_chat_state"],
            updated_items,
        )
        st.success("Chat Action ItemsStatus已保存。")
        st.rerun()


def render_agent_workspace(analysis, selected_task_id):
    st.header("Agent 工作台")
    st.markdown("这里展示 FinCopilot 的任务规划、工具调用、追问补全、行动清单、进展跟踪 and 工作流Reports。")
    task_options = get_task_options_for_ui()
    selected_task_name = st.selectbox(
        "请选择 Copilot 要完成的任务",
        list(task_options.keys()),
        index=list(task_options.values()).index(selected_task_id),
        key="workspace_task_selector",
    )
    selected_task_id = task_options[selected_task_name]
    st.session_state["selected_task_id"] = selected_task_id

    questions = get_questions_for_task(selected_task_id)
    saved_business_context = get_business_context(st.session_state["agent_state"])
    pending_user_inputs = {}
    with st.expander("补充业务信息，用于提高 Agent 分析准确性", expanded=True):
        st.caption("数值为 0 时默认视为暂未填写；点击保存后才会更新 Agent 上下文。")
        for question in questions:
            field = question["field"]
            existing_value = saved_business_context.get(field)
            if question.get("input_type") == "number":
                pending_user_inputs[field] = st.number_input(
                    question["question"],
                    value=float(existing_value or 0.0),
                    key=f"clarify_{selected_task_id}_{field}",
                )
            else:
                pending_user_inputs[field] = st.text_area(
                    question["question"],
                    value=str(existing_value or ""),
                    key=f"clarify_{selected_task_id}_{field}",
                )
            st.caption(question.get("reason", ""))
        col_save, col_reset = st.columns(2)
        if col_save.button("保存补充信息并重新分析"):
            st.session_state["agent_state"] = update_agent_state(
                st.session_state["agent_state"],
                task_id=selected_task_id,
                business_context_updates=pending_user_inputs,
            )
            st.success("补充信息已保存，Agent 工作台已更新。")
            st.rerun()
        if col_reset.button("重置 Agent 补充信息"):
            st.session_state["agent_state"] = reset_agent_state()
            st.warning("Agent 补充信息已重置。")
            st.rerun()

    workspace = build_workspace(selected_task_id, analysis)
    task = workspace["task"]
    task_plan = workspace["task_plan"]
    tool_execution = workspace["tool_execution"]

    st.subheader("1. Agent 理解的任务目标")
    st.markdown(f"**任务：** {task.get('task_name', '')}")
    st.markdown(f"**目标：** {task.get('task_goal', '')}")

    st.subheader("2. Agent 执行计划")
    for index, step in enumerate(task.get("workflow_steps", []), start=1):
        st.markdown(f"{index}. {step}")
    plan_status = task_plan.get("plan_status", "unknown")
    if plan_status == "ready":
        st.success("ready：关键数据 and 工具已具备，可以执行当前任务计划。")
    elif plan_status == "needs_clarification":
        st.warning("needs_clarification：可以先做初步分析，但生成行动计划前建议补充信息。")
    else:
        st.error(f"{plan_status}：当前缺少关键数据或工具，无法可靠执行完整任务。")

    data_check = workspace["data_check"]
    clarification_status = workspace.get("clarification_status", {})
    st.subheader("3. 数据完整性检查")
    st.markdown(f"**检查Status: ** {data_check.get('status', 'unknown')}")
    for title, key in [
        ("已具备的信息", "available_items"),
        ("缺失或不确定的信息", "missing_items"),
        ("建议追问", "clarifying_questions"),
    ]:
        st.markdown(f"**{title}：**")
        items = data_check.get(key, [])
        if items:
            for item in items:
                st.markdown(f"- {item}")
        else:
            st.markdown("- 暂无")

    st.subheader("4. 澄清信息完成度")
    st.metric("澄清信息完成度", f"{clarification_status.get('completion_ratio', 0.0) * 100:.0f}%")
    st.subheader("5. 已补充的业务上下文")
    provided_items = {
        key: value
        for key, value in workspace.get("business_context", {}).items()
        if value not in [None, "", 0, 0.0]
    }
    if provided_items:
        st.json(provided_items)
    else:
        st.info("当前尚未保存业务补充信息。")

    st.subheader("6. 结构化工具调用计划")
    tool_steps_df = pd.DataFrame(task_plan.get("tool_steps", []))
    if tool_steps_df.empty:
        st.warning("当前任务没有可执行工具步骤。")
    else:
        if "input_keys" in tool_steps_df.columns:
            tool_steps_df["input_keys"] = tool_steps_df["input_keys"].apply(stringify_cell)
        st.dataframe(tool_steps_df, use_container_width=True)

    st.subheader("7. 工具执行轨迹")
    execution_records_df = pd.DataFrame(tool_execution.get("execution_records", []))
    if execution_records_df.empty:
        st.warning("当前没有工具执行记录。")
    else:
        for column in ["input_keys", "summary"]:
            if column in execution_records_df.columns:
                execution_records_df[column] = execution_records_df[column].apply(stringify_cell)
        st.dataframe(execution_records_df, use_container_width=True)

    st.subheader("8. 已有工具结果摘要")
    st.json(workspace.get("tool_result_summary", {}))
    st.subheader("9. 补充信息对分析的影响")
    st.info(workspace.get("context_impact_summary", "当前尚未形成补充信息影响说明。"))

    st.subheader("10. 行动清单与进展跟踪")
    render_action_list(workspace, selected_task_id, editable=True, key_prefix="workspace_")
    if st.button("重置当前任务Action ItemsStatus"):
        st.session_state["agent_state"] = reset_action_progress(
            st.session_state["agent_state"],
            task_id=selected_task_id,
        )
        st.warning("当前任务的Action ItemsStatus已重置。")
        st.rerun()

    st.subheader("11. Agent 进展结论")
    st.info(workspace.get("agent_progress_conclusion", "当前暂无进展结论。"))
    st.subheader("12. Agent 初步结论")
    st.info(workspace.get("initial_conclusion", ""))

    st.subheader("13. Agent 工作流Reports")
    render_workflow_report(workspace, selected_task_id)

    st.subheader("14. 下一步")
    st.warning(workspace.get("next_step_hint", ""))

    with st.expander("查看 Agent 可用工具"):
        tools_df = pd.DataFrame(list_available_tools())
        if "input_keys" in tools_df.columns:
            tools_df["input_keys"] = tools_df["input_keys"].apply(stringify_cell)
        st.dataframe(tools_df, use_container_width=True)


def render_action_center(workspace, selected_task_id):
    st.header("行动中心")
    st.caption("集中展示当前任务生成的Action Items、处理Status and 最近进展。")
    render_chat_action_items_section()
    st.subheader("来自 Agent 工作台的Action Items")
    render_action_list(workspace, selected_task_id, editable=True, key_prefix="center_")
    with st.expander("复制带Status的行动清单 Markdown"):
        st.text_area(
            "带Status的行动清单",
            action_items_to_status_markdown(workspace.get("ranked_action_items", [])),
            height=350,
        )


def render_workflow_report(workspace, selected_task_id):
    report_md = workspace.get("workflow_report_markdown", "")
    if not report_md:
        st.info("当前暂无可生成的 Agent 工作流Reports。")
        return
    st.markdown("以下Reports汇总了当前任务的 Agent 执行过程、工具结果、行动清单 and 进展Status。")
    with st.expander("预览 Agent 工作流Reports", expanded=False):
        st.markdown(report_md)
    st.text_area(
        "复制 Markdown Reports",
        report_md,
        height=400,
        key=f"workflow_report_{selected_task_id}",
    )
    st.download_button(
        label="下载 Markdown Reports",
        data=encode_markdown_for_download(report_md),
        file_name=build_report_filename(selected_task_id),
        mime="text/markdown",
    )
    st.caption(get_disclaimer())


def render_report_center(analysis, workspace, selected_task_id, use_llm):
    st.header("Reports中心")
    st.info("集中展示 Copilot 摘要、Agent 工作流Reports、Multi-Agent 对话Reports and 带Status行动清单。")
    chat_state = ensure_agent_chat_state(st.session_state.get("agent_chat_state", {}))
    latest_report_markdown = chat_state.get("latest_report_markdown", "")
    latest_trace_markdown = chat_state.get("latest_trace_markdown", "")

    st.subheader("最近一次 Multi-Agent 对话Reports")
    if latest_report_markdown:
        with st.expander("预览最近一次 Multi-Agent Reports", expanded=True):
            st.markdown(latest_report_markdown)
        st.text_area(
            "复制最近一次 Multi-Agent Reports",
            latest_report_markdown,
            height=320,
            key="latest_multi_agent_report_copy",
        )
        st.download_button(
            label="下载最近一次 Multi-Agent Reports",
            data=latest_report_markdown.encode("utf-8"),
            file_name="fincopilot_multi_agent_report.md",
            mime="text/markdown",
        )
    else:
        st.info("当前还没有 Multi-Agent 对话Reports。请先在“Copilot Home”提出一个问题。")

    st.subheader("最近一次 Multi-Agent Trace")
    if latest_trace_markdown:
        with st.expander("预览最近一次 Multi-Agent Trace", expanded=False):
            st.markdown(latest_trace_markdown)
        st.text_area(
            "复制最近一次 Multi-Agent Trace",
            latest_trace_markdown,
            height=260,
            key="latest_multi_agent_trace_copy",
        )
        st.download_button(
            label="下载最近一次 Multi-Agent Trace",
            data=latest_trace_markdown.encode("utf-8"),
            file_name="fincopilot_multi_agent_trace.md",
            mime="text/markdown",
        )
    else:
        latest_trace = chat_state.get("latest_trace")
        if latest_trace:
            st.markdown(trace_to_markdown(latest_trace))
        else:
            st.info("No Multi-Agent trace is available yet.")

    if "planning_summary" not in st.session_state:
        st.session_state["planning_summary"] = None

    if analysis["budget_result"] is None or analysis["invoice_result"] is None or analysis["goals_df"] is None:
        st.warning("请先在“Data & Settings”页确认数据读取成功。")
    else:
        button_label = "重新生成本期财务规划摘要" if st.session_state["planning_summary"] else "生成本期财务规划摘要"
        if st.button(button_label):
            st.session_state["planning_summary"] = generate_planning_summary(
                budget_result=analysis["budget_result"],
                invoice_result=analysis["invoice_result"],
                cashflow_result=analysis["cashflow_result"],
                goal_result=analysis["goal_result"],
                rule_anomalies_df=analysis["rule_anomalies_df"],
                lof_result_df=analysis["lof_result_df"],
                goals_df=analysis["goals_df"],
                use_llm=use_llm,
            )
        if st.session_state["planning_summary"]:
            st.subheader("Copilot 财务规划摘要")
            st.markdown(st.session_state["planning_summary"])

    st.subheader("Agent 工作流Reports")
    render_workflow_report(workspace, selected_task_id)
    st.subheader("带Status行动清单 Markdown")
    st.text_area(
        "复制带Status的行动清单",
        action_items_to_status_markdown(workspace.get("ranked_action_items", [])),
        height=300,
    )
    with st.expander("复制基础行动清单 Markdown"):
        st.text_area(
            "行动清单",
            action_items_to_markdown(workspace.get("ranked_action_items", [])),
            height=300,
        )
    st.caption(get_disclaimer())


def render_analysis_detail_page(analysis, selected_task_id, use_llm):
    st.header("Analysis Details")
    tab_financial, tab_workspace = st.tabs(["财务分析", "Agent 执行轨迹"])
    with tab_financial:
        render_financial_analysis(analysis, use_llm)
    with tab_workspace:
        render_agent_workspace(analysis, selected_task_id)


def render_action_report_page(analysis, workspace, selected_task_id, use_llm):
    st.header("Actions & Reports")
    tab_actions, tab_report, tab_trace = st.tabs(["Action Items", "Reports", "Trace"])
    with tab_actions:
        render_action_center(workspace, selected_task_id)
    with tab_report:
        render_report_center(analysis, workspace, selected_task_id, use_llm)
    with tab_trace:
        chat_state = ensure_agent_chat_state(st.session_state.get("agent_chat_state", {}))
        trace_markdown = chat_state.get("latest_trace_markdown", "")
        if trace_markdown:
            st.markdown(trace_markdown)
        elif chat_state.get("latest_trace"):
            st.markdown(trace_to_markdown(chat_state.get("latest_trace")))
        else:
            st.info("No Multi-Agent trace is available yet.")


def render_data_settings_page(analysis, transactions_file, invoices_file, goals_file):
    st.header("Data & Settings")
    tab_data, tab_api, tab_safety = st.tabs(["Data Upload & Preview", "API & Model", "Safety Boundaries"])
    with tab_data:
        render_data_management(analysis, transactions_file, invoices_file, goals_file)
    with tab_api:
        status = get_agent_api_status()
        if status.get("mode") == "api_agent":
            st.success(status.get("user_message", "Live Agent analysis is active."))
        else:
            st.info(status.get("user_message", "The live Agent API is unavailable. FinCopilot will automatically fall back."))
        st.markdown(f"**Model:** {status.get('model', 'gpt-5.4-mini')}")
        st.markdown(f"**API Base URL:** {status.get('base_url', '')}")
        st.markdown(
            "**Model configuration:** override with `OPENAI_AGENT_MODEL` or `OPENAI_MODEL`; "
            "override the OpenAI-compatible endpoint with `OPENAI_BASE_URL`."
        )
        st.markdown("**Developer override:** Set `ENABLE_AGENT_API=false` to force fallback mode.")
    with tab_safety:
        st.markdown("FinCopilot is for financial organization, risk reminders, and educational support only.")
        st.markdown("- Does not provide investment advice")
        st.markdown("- Does not provide tax advice")
        st.markdown("- Does not provide legal advice")
        st.markdown("- Does not provide debt-resolution advice")
        st.markdown("- Does not determine that any transaction is fraud")
        st.markdown("- Does not execute real payments or transfers")
        st.caption(get_disclaimer())


st.set_page_config(
    page_title="FinCopilot V2.3",
    page_icon="💸",
    layout="wide",
)

if "agent_state" not in st.session_state:
    st.session_state["agent_state"] = get_default_agent_state()

task_options_for_state = get_task_options_for_ui()
default_task_id = next(iter(task_options_for_state.values()))
if "selected_task_id" not in st.session_state:
    st.session_state["selected_task_id"] = default_task_id

try:
    memory_db_path = initialize_memory_db()
    ensure_default_workspace(db_path=memory_db_path)
    st.session_state["memory_db_path"] = memory_db_path
    st.session_state.pop("memory_init_error", None)
except Exception as exc:
    st.session_state["memory_init_error"] = str(exc)

current_identity = get_current_identity(st.session_state)

page = render_sidebar_navigation()
use_llm = False

transactions_file = st.session_state.get("v22_transactions_file")
invoices_file = st.session_state.get("v22_invoices_file")
goals_file = st.session_state.get("v22_goals_file")

analysis = prepare_analysis(transactions_file, invoices_file, goals_file)
if analysis["load_error"]:
    st.error(analysis["load_error"])

workspace_for_pages = {}
if not analysis["load_error"]:
    workspace_for_pages = build_workspace(st.session_state["selected_task_id"], analysis)

agent_context_summary = build_agent_context_summary(
    {
        "transactions_df": analysis["transactions_df"],
        "invoices_df": analysis["invoices_df"],
        "goals_df": analysis["goals_df"],
        "budget_result": analysis["budget_result"],
        "invoice_result": analysis["invoice_result"],
        "cashflow_result": analysis["cashflow_result"],
        "goal_result": analysis["goal_result"],
        "rule_anomalies_df": analysis["rule_anomalies_df"],
        "lof_result_df": analysis["lof_result_df"],
        "workspace": workspace_for_pages,
        "agent_state": st.session_state.get("agent_state"),
    }
)

if page == "Copilot Home":
    render_copilot_main(
        agent_context_summary=agent_context_summary,
        transactions_df=analysis["transactions_df"],
        invoices_df=analysis["invoices_df"],
        goals_df=analysis["goals_df"],
        latest_agent_turn=st.session_state.get("agent_chat_state", {}).get("latest_turn_result"),
    )
elif page == "Analysis Details":
    render_v23_analysis_detail_page(
        transactions_df=analysis["transactions_df"],
        invoices_df=analysis["invoices_df"],
        goals_df=analysis["goals_df"],
        budget_result=analysis["budget_result"],
        invoice_result=analysis["invoice_result"],
        cashflow_result=analysis["cashflow_result"],
        goal_result=analysis["goal_result"],
        rule_anomalies_df=analysis["rule_anomalies_df"],
        lof_result_df=analysis["lof_result_df"],
        workspace=workspace_for_pages,
        agent_chat_state=st.session_state.get("agent_chat_state", {}),
    )
elif page == "Actions & Reports":
    render_v23_action_report_page(
        workspace=workspace_for_pages,
        agent_chat_state=st.session_state.get("agent_chat_state", {}),
    )
elif page == "Data & Settings":
    render_v23_data_settings_page(
        transactions_df=analysis["transactions_df"],
        invoices_df=analysis["invoices_df"],
        goals_df=analysis["goals_df"],
    )
