import pandas as pd

from agent.clarification import assess_clarification_status


BASE_ITEMS = {
    "transactions_df": "Transaction data",
    "invoices_df": "Invoice data",
    "goals_df": "Financial goal data",
    "budget_result": "Budget summary result",
    "invoice_result": "Invoice review result",
    "cashflow_result": "Cash-flow risk result",
    "goal_result": "Financial goal analysis result",
    "rule_anomalies_df": "Rule/statistical anomaly result",
    "lof_result_df": "LOF model anomaly result",
}

TASK_CLARIFYING_QUESTIONS = {
    "cashflow_safety_check": {
        "current_cash_balance": "What is the real available balance in the current business account?",
        "expected_receivables_30d": "Are there confirmed customer collections in the next 30 days? What is the approximate amount?",
        "unuploaded_invoices_estimate": "Are there any unuploaded invoices or fixed expenses?",
        "large_upcoming_payments": "Are there required large payments in the next 30 days?",
    },
    "suspicious_expense_review": {
        "known_authorized_large_payments": "Are there known normal large payments, such as rent, supplier contracts, or taxes?",
        "recurring_vendor_list": "Do you have a list of regular suppliers?",
        "business_context_for_top_anomalies": "Do you have business context for the top high-risk transactions?",
    },
    "goal_action_plan": {
        "goal_priority_confirmation": "Which financial goal is the highest priority right now?",
        "current_cash_balance": "What cash is currently available for goal reserves?",
        "expected_monthly_savings_capacity": "How much can be saved or reserved each month going forward?",
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
            available_items.append(f"User provided: {field}")
        else:
            missing_items.append(f"Needs input: {field}")
            clarifying_questions.append(question)

    if task_id == "goal_action_plan" and "Financial goal data" in missing_items:
        notes.append("A goal action plan needs at least one financial goal record.")
    if task_id == "cashflow_safety_check":
        notes.append("Cash-flow safety can be estimated from uploaded data first, but actual balance and future collections affect accuracy.")
    if task_id == "suspicious_expense_review":
        notes.append("Suspicious expense handling needs business context; the system does not determine fraud.")

    has_transactions = "Transaction data" in available_items
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
