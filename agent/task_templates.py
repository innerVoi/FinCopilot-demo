AGENT_TASKS = [
    {
        "task_id": "cashflow_safety_check",
        "task_name": "Check whether cash flow is safe for the next 30 days",
        "task_goal": "Determine whether cash-flow pressure exists over the next 30 days and identify the main risk drivers.",
        "workflow_steps": [
            "Check whether transaction, invoice, and goal data are available.",
            "Check whether actual account balance, future customer collections, or unuploaded invoices are missing.",
            "Call the budget summary tool to understand recent income, expenses, and net cash flow.",
            "Call the invoice tool to identify overdue and upcoming invoices.",
            "Call the cash-flow risk tool to estimate 30-day balance and risk level.",
            "Call anomaly detection tools to identify large unusual expenses that may affect cash flow.",
            "Summarize cash-flow risk drivers.",
            "Output an initial conclusion and indicate that action items should be generated next.",
        ],
        "required_tools": [
            "analyze_budget",
            "analyze_invoices",
            "analyze_cashflow",
            "run_rule_based_anomaly_detection",
            "run_lof_detection",
        ],
        "missing_info_fields": [
            "current_cash_balance",
            "expected_receivables_30d",
            "unuploaded_invoices_estimate",
            "large_upcoming_payments",
        ],
    },
    {
        "task_id": "suspicious_expense_review",
        "task_name": "Review this month's most suspicious expenses",
        "task_goal": "Identify the expenses most worth reviewing and prepare for a follow-up review checklist.",
        "workflow_steps": [
            "Call the rule/statistical anomaly detection tool.",
            "Call the LOF model anomaly detection tool.",
            "Merge both anomaly result sets.",
            "Sort by risk level, anomaly score, and amount impact.",
            "Identify top suspicious transactions.",
            "Check whether the user needs to add transaction context.",
            "Summarize the evidence for each anomaly.",
            "Indicate that action items and handling status can be generated next.",
        ],
        "required_tools": [
            "run_rule_based_anomaly_detection",
            "run_lof_detection",
            "explain_transaction_risk",
        ],
        "missing_info_fields": [
            "known_authorized_large_payments",
            "business_context_for_top_anomalies",
            "recurring_vendor_list",
        ],
    },
    {
        "task_id": "goal_action_plan",
        "task_name": "Create a financial goal action plan",
        "task_goal": "Analyze whether goals such as cash buffer, tax reserve, and operating reserve are reachable, then prepare for follow-up action planning.",
        "workflow_steps": [
            "Check whether financial goal data exists.",
            "Call the budget summary tool to understand current net cash flow.",
            "Call the cash-flow risk tool to evaluate whether future cash flow supports the goals.",
            "Call the goal analysis tool to calculate progress, remaining gap, and required monthly savings.",
            "Identify high-risk goals.",
            "Check whether actual balance or goal priority is missing.",
            "Summarize goal risks.",
            "Indicate that a concrete action plan can be generated next.",
        ],
        "required_tools": [
            "analyze_budget",
            "analyze_cashflow",
            "analyze_goals",
        ],
        "missing_info_fields": [
            "goal_priority_confirmation",
            "current_cash_balance",
            "expected_monthly_savings_capacity",
        ],
    },
]


def get_supported_agent_tasks() -> list[dict]:
    """
    Return all supported fixed Agent tasks.
    """
    return [task.copy() for task in AGENT_TASKS]


def get_task_template(task_id: str) -> dict:
    """
    Return a task template by task_id.
    """
    for task in AGENT_TASKS:
        if task["task_id"] == task_id:
            return task.copy()
    raise ValueError(f"Unsupported agent task_id: {task_id}")


def get_task_options_for_ui() -> dict:
    """
    Return task display name to task_id mapping for Streamlit selectbox.
    """
    return {task["task_name"]: task["task_id"] for task in AGENT_TASKS}
