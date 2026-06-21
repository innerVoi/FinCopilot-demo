import pandas as pd

from agent.clarification import assess_clarification_status


BASE_ITEMS = {
    "transactions_df": "交易流水数据",
    "invoices_df": "发票数据",
    "goals_df": "财务目标数据",
    "budget_result": "预算统计结果",
    "invoice_result": "发票整理结果",
    "cashflow_result": "现金流风险结果",
    "goal_result": "财务目标分析结果",
    "rule_anomalies_df": "规则/统计异常结果",
    "lof_result_df": "LOF 模型异常结果",
}

TASK_CLARIFYING_QUESTIONS = {
    "cashflow_safety_check": {
        "current_cash_balance": "当前企业账户的真实可用余额是多少？",
        "expected_receivables_30d": "未来 30 天是否有确定的客户回款？金额大约是多少？",
        "unuploaded_invoices_estimate": "是否还有未上传的发票或固定支出？",
        "large_upcoming_payments": "是否存在未来 30 天必须支付的大额款项？",
    },
    "suspicious_expense_review": {
        "known_authorized_large_payments": "是否有已知的正常大额付款，例如房租、供应商合同款或税费？",
        "recurring_vendor_list": "是否有固定供应商名单？",
        "business_context_for_top_anomalies": "对 Top 高风险交易，是否有业务背景说明？",
    },
    "goal_action_plan": {
        "goal_priority_confirmation": "哪个财务目标是当前最高优先级？",
        "current_cash_balance": "当前真实可用于目标储备的现金是多少？",
        "expected_monthly_savings_capacity": "未来每月预计可用于储蓄或储备的金额是多少？",
    },
}


def is_non_empty_dataframe(obj) -> bool:
    """
    Return True if obj is a non-empty pandas DataFrame.
    """
    return isinstance(obj, pd.DataFrame) and not obj.empty


def _has_result(obj) -> bool:
    if obj is None:
        return False
    if isinstance(obj, dict):
        return bool(obj)
    return is_non_empty_dataframe(obj)


def check_base_data_availability(context: dict) -> dict:
    """
    Check whether core data and analysis results are available.
    """
    context = context or {}
    available_items = []
    missing_items = []

    for key, label in BASE_ITEMS.items():
        value = context.get(key)
        if key.endswith("_df"):
            is_available = is_non_empty_dataframe(value)
        else:
            is_available = _has_result(value)

        if is_available:
            available_items.append(label)
        else:
            missing_items.append(label)

    return {
        "available_items": available_items,
        "missing_items": missing_items,
    }


def _has_user_input(user_inputs, field):
    value = (user_inputs or {}).get(field)
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (int, float)):
        return value != 0
    return bool(value)


def check_task_completeness(task_id: str, context: dict, user_inputs: dict | None = None) -> dict:
    """
    Check data completeness for a selected Agent task.
    """
    base_check = check_base_data_availability(context or {})
    available_items = list(base_check["available_items"])
    missing_items = list(base_check["missing_items"])
    clarifying_questions = []
    notes = []
    clarification_status = assess_clarification_status(task_id, user_inputs or {})
    provided_business_context = clarification_status["provided_fields"]

    task_questions = TASK_CLARIFYING_QUESTIONS.get(task_id, {})
    for field, question in task_questions.items():
        if _has_user_input(user_inputs, field):
            available_items.append(f"用户补充：{field}")
        else:
            missing_items.append(f"待补充：{field}")
            clarifying_questions.append(question)

    if task_id == "goal_action_plan" and "财务目标数据" in missing_items:
        notes.append("财务目标行动计划需要至少一条目标数据。")
    if task_id == "cashflow_safety_check":
        notes.append("现金流安全检查可先基于上传数据估算，但真实余额和未来回款会影响准确性。")
    if task_id == "suspicious_expense_review":
        notes.append("异常支出处理需要结合业务背景确认，系统不会认定交易为欺诈。")

    has_transactions = "交易流水数据" in available_items
    if not has_transactions:
        status = "missing"
    elif clarifying_questions:
        status = "partial"
    else:
        status = "complete"

    return {
        "status": status,
        "available_items": available_items,
        "missing_items": missing_items,
        "provided_business_context": provided_business_context,
        "clarifying_questions": clarifying_questions,
        "clarification_completion_ratio": clarification_status["completion_ratio"],
        "notes": notes,
    }
