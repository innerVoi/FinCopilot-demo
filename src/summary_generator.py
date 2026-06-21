import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from src.risk_explainer import has_openai_api_key
from src.safety import get_disclaimer, sanitize_llm_output


PROMPT_PATH = Path("prompts/financial_summary_prompt.txt")
DEFAULT_MODEL = "gpt-5.4-mini"
DEFAULT_RECORD_COLUMNS = [
    "date",
    "merchant",
    "description",
    "amount",
    "category",
    "account",
    "anomaly_type",
    "risk_level",
    "anomaly_score",
    "model_evidence",
    "reason",
    "goal_status",
    "goal_risk_level",
    "goal_recommendation",
]


def _to_json_safe_value(value):
    if isinstance(value, dict):
        return _json_safe_dict(value)
    if isinstance(value, list):
        return [_to_json_safe_value(item) for item in value]
    if pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def _json_safe_dict(data):
    return {key: _to_json_safe_value(value) for key, value in data.items()}


def safe_top_records(df, n=5, columns=None) -> list:
    """
    Safely extract top records from a DataFrame as JSON-safe dicts.
    """
    if df is None or df.empty:
        return []

    columns = columns or DEFAULT_RECORD_COLUMNS
    selected_columns = [column for column in columns if column in df.columns]
    if not selected_columns:
        return []

    records = []
    for record in df.head(n)[selected_columns].to_dict(orient="records"):
        records.append(_json_safe_dict(record))
    return records


def build_summary_context(
    budget_result=None,
    invoice_result=None,
    cashflow_result=None,
    goal_result=None,
    rule_anomalies_df=None,
    lof_result_df=None,
    goals_df=None,
) -> dict:
    """
    Build a compact JSON-serializable context for summary generation.
    """
    budget_result = budget_result or {}
    invoice_result = invoice_result or {}
    cashflow_result = cashflow_result or {}
    goal_result = goal_result or {}
    budget_summary = budget_result.get("summary", {})
    category_spending = safe_top_records(
        budget_result.get("category_spending"),
        n=5,
        columns=["category", "expense_amount", "transaction_count", "expense_share"],
    )
    invoice_summary = invoice_result.get("summary", {})

    top_model_df = lof_result_df
    if top_model_df is not None and not top_model_df.empty and "risk_level" in top_model_df:
        risky_df = top_model_df[top_model_df["risk_level"].isin(["high", "medium"])]
        top_model_df = risky_df if not risky_df.empty else top_model_df

    goal_records = []
    goal_summary = goal_result.get("summary", {})
    if goal_result.get("goals") is not None:
        goal_records = safe_top_records(
            goal_result.get("goals"),
            n=5,
            columns=[
                "goal_id",
                "goal_name",
                "target_amount",
                "current_amount",
                "remaining_amount",
                "progress_percent",
                "days_remaining",
                "required_monthly_saving",
                "goal_risk_level",
                "goal_status",
                "goal_recommendation",
            ],
        )
    elif goals_df is not None:
        goal_records = safe_top_records(
            goals_df,
            n=5,
            columns=[
                "goal_id",
                "goal_name",
                "target_amount",
                "current_amount",
                "due_date",
                "priority",
            ],
        )

    context = {
        "budget_summary": _json_safe_dict(budget_summary),
        "category_spending": category_spending,
        "invoice_summary": _json_safe_dict(invoice_summary),
        "cashflow": _json_safe_dict(cashflow_result),
        "goal_summary": _json_safe_dict(goal_summary),
        "top_rule_anomalies": safe_top_records(rule_anomalies_df, n=5),
        "top_model_anomalies": safe_top_records(top_model_df, n=5),
        "goals": goal_records,
    }
    json.dumps(context, ensure_ascii=False)
    return context


def template_generate_planning_summary(context: dict) -> str:
    """
    Generate a deterministic Markdown planning summary.
    """
    budget = context.get("budget_summary", {})
    invoices = context.get("invoice_summary", {})
    cashflow = context.get("cashflow", {})
    goal_summary = context.get("goal_summary", {})
    category_spending = context.get("category_spending", [])
    rule_anomalies = context.get("top_rule_anomalies", [])
    model_anomalies = context.get("top_model_anomalies", [])
    goals = context.get("goals", [])

    total_income = budget.get("total_income", 0.0)
    total_expense = budget.get("total_expense", 0.0)
    net_cashflow = budget.get("net_cashflow", 0.0)
    top_category = budget.get("top_expense_category", "none")
    fixed_ratio = budget.get("fixed_expense_ratio", 0.0)
    overdue_amount = invoices.get("overdue_invoice_amount", 0.0)
    due_30d_amount = invoices.get("due_30d_amount", 0.0)
    cashflow_risk = cashflow.get("risk_level", "unknown")
    projected_balance = cashflow.get("projected_balance_30d", 0.0)
    cash_buffer_days = cashflow.get("cash_buffer_days", 0.0)
    cashflow_reasons = cashflow.get("risk_reasons", [])
    upcoming_invoice_outflow = cashflow.get("upcoming_invoice_outflow_30d", due_30d_amount)

    category_text = "暂无类别支出数据。"
    if category_spending:
        category_text = "；".join(
            f"{item.get('category')} 支出 {item.get('expense_amount', 0):.2f}"
            for item in category_spending[:3]
        )

    anomaly_count = len(rule_anomalies) + len(model_anomalies)
    goal_text = "暂无财务目标数据。"
    if goal_summary:
        goal_text = (
            f"当前共有 {goal_summary.get('goal_count', 0)} 个财务目标，"
            f"已完成 {goal_summary.get('completed_goal_count', 0)} 个，"
            f"高风险目标 {goal_summary.get('high_risk_goal_count', 0)} 个，"
            f"整体完成率约为 {goal_summary.get('overall_progress_percent', 0.0):.1f}%。"
        )
        if goals:
            focus_goals = [
                f"{goal.get('goal_name')}（{goal.get('goal_status')}）"
                for goal in goals[:3]
            ]
            goal_text += " 建议优先关注：" + "；".join(focus_goals) + "。"
    elif goals:
        goal_items = []
        for goal in goals:
            target = goal.get("target_amount") or 0
            current = goal.get("current_amount") or 0
            progress = current / target if target else 0
            goal_items.append(
                f"{goal.get('goal_name')} 当前完成约 {progress:.1%}"
            )
        goal_text = "；".join(goal_items)

    return (
        "## 本期财务概况\n"
        f"本期总收入为 {total_income:.2f}，总支出为 {total_expense:.2f}，"
        f"净现金流为 {net_cashflow:.2f}。\n\n"
        "## 预算与支出观察\n"
        f"支出最多的类别为 {top_category}，固定支出占比约为 {fixed_ratio:.1%}。"
        f"{category_text}\n\n"
        "## 发票与现金流提醒\n"
        f"未来 30 天待付发票金额为 {upcoming_invoice_outflow:.2f}，"
        f"逾期发票金额为 {overdue_amount:.2f}。根据当前上传数据估算，"
        f"未来 30 天预计余额为 {projected_balance:.2f}，现金流风险等级为 {cashflow_risk}，"
        f"现金缓冲天数约为 {cash_buffer_days:.1f} 天。"
        f"主要原因包括：{'；'.join(cashflow_reasons) if cashflow_reasons else '暂无明显风险原因。'}\n\n"
        "## 异常支出提醒\n"
        f"当前摘要上下文中包含 {anomaly_count} 条重点异常或模型高分记录。"
        "这些记录不代表已确认问题，只表示可能需要核查。\n\n"
        "## 财务目标观察\n"
        f"{goal_text}\n\n"
        "## 建议行动\n"
        "1. 优先核查高风险异常交易的原始凭证和账单。\n"
        "2. 复查未来 30 天到期和逾期发票，安排付款计划。\n"
        "3. 对支出占比较高的类别设置预算提醒或复盘机制。\n\n"
        "## 假设与限制\n"
        "本摘要仅基于当前上传的交易流水、发票和财务目标数据生成，"
        "未包含未上传的现金交易、贷款、税务细节或外部账户信息。\n\n"
        "## 免责声明\n"
        f"{get_disclaimer()}"
    )


def _load_prompt(path):
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def llm_generate_planning_summary(context: dict, model=None) -> str:
    """
    Try to call the OpenAI API, falling back to the deterministic template.
    """
    if not has_openai_api_key():
        return template_generate_planning_summary(context)

    try:
        from openai import OpenAI

        client = OpenAI()
        model = model or os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
        system_prompt = _load_prompt(PROMPT_PATH)
        response = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(context, ensure_ascii=False),
                },
            ],
        )
        return sanitize_llm_output(response.output_text)
    except Exception:
        return template_generate_planning_summary(context)


def generate_planning_summary(
    budget_result=None,
    invoice_result=None,
    cashflow_result=None,
    goal_result=None,
    rule_anomalies_df=None,
    lof_result_df=None,
    goals_df=None,
    use_llm=True,
) -> str:
    """
    Public entry point for planning summary generation.
    """
    context = build_summary_context(
        budget_result=budget_result,
        invoice_result=invoice_result,
        cashflow_result=cashflow_result,
        goal_result=goal_result,
        rule_anomalies_df=rule_anomalies_df,
        lof_result_df=lof_result_df,
        goals_df=goals_df,
    )
    if use_llm and has_openai_api_key():
        return llm_generate_planning_summary(context)
    return template_generate_planning_summary(context)
