CLARIFICATION_SCHEMA = [
    {
        "field": "current_cash_balance",
        "question": "What is the real available balance in the current business account?",
        "reason": "Cash-flow risk needs the real balance; otherwise it can only be estimated from uploaded transactions.",
        "input_type": "number",
        "required": False,
        "task_ids": ["cashflow_safety_check", "goal_action_plan"],
    },
    {
        "field": "expected_receivables_30d",
        "question": "Are there confirmed customer collections in the next 30 days? What is the approximate amount?",
        "reason": "Future collections directly affect 30-day cash-flow safety.",
        "input_type": "number",
        "required": False,
        "task_ids": ["cashflow_safety_check"],
    },
    {
        "field": "unuploaded_invoices_estimate",
        "question": "Are there any unuploaded invoices or fixed expenses? What is the estimated amount?",
        "reason": "Unuploaded expenses can cause cash-flow risk to be underestimated.",
        "input_type": "number",
        "required": False,
        "task_ids": ["cashflow_safety_check"],
    },
    {
        "field": "large_upcoming_payments",
        "question": "Are there required large payments in the next 30 days? What is the estimated amount?",
        "reason": "Large required payments can change short-term cash-flow pressure.",
        "input_type": "number",
        "required": False,
        "task_ids": ["cashflow_safety_check"],
    },
    {
        "field": "known_authorized_large_payments",
        "question": "Are there known normal large payments, such as rent, taxes, or contract payments?",
        "reason": "Known normal payments help distinguish reasonable business expenses from items that need review.",
        "input_type": "text",
        "required": False,
        "task_ids": ["suspicious_expense_review"],
    },
    {
        "field": "recurring_vendor_list",
        "question": "Do you have a list of regular suppliers or common merchants?",
        "reason": "Regular supplier context helps prioritize unfamiliar merchants for review.",
        "input_type": "text",
        "required": False,
        "task_ids": ["suspicious_expense_review"],
    },
    {
        "field": "business_context_for_top_anomalies",
        "question": "Do you have business context for the current top high-risk transactions?",
        "reason": "Business context helps the Agent generate more practical review recommendations.",
        "input_type": "text",
        "required": False,
        "task_ids": ["suspicious_expense_review"],
    },
    {
        "field": "goal_priority_confirmation",
        "question": "Which financial goal is the highest priority right now?",
        "reason": "Goal priority affects how follow-up action plans are ordered.",
        "input_type": "text",
        "required": False,
        "task_ids": ["goal_action_plan"],
    },
    {
        "field": "expected_monthly_savings_capacity",
        "question": "How much can be reserved or invested toward goals each month going forward?",
        "reason": "Monthly reserve capacity affects goal timelines and achievability.",
        "input_type": "number",
        "required": False,
        "task_ids": ["goal_action_plan"],
    },
]


def get_clarification_schema() -> list[dict]:
    """
    Return all clarification question definitions.
    """
    return [question.copy() for question in CLARIFICATION_SCHEMA]


def get_questions_for_task(task_id: str) -> list[dict]:
    """
    Return clarification questions for a task.
    """
    return [
        question.copy()
        for question in CLARIFICATION_SCHEMA
        if task_id in question.get("task_ids", [])
    ]


def is_value_provided(value) -> bool:
    """
    Return True if a user value should count as provided.
    """
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (int, float)):
        return value != 0
    return bool(value)


def assess_clarification_status(
    task_id: str,
    business_context: dict | None,
) -> dict:
    """
    Assess which clarification questions are answered for a task.
    """
    questions = get_questions_for_task(task_id)
    context = business_context or {}
    provided_fields = []
    missing_fields = []
    answered_questions = []
    unanswered_questions = []

    for question in questions:
        field = question["field"]
        if is_value_provided(context.get(field)):
            provided_fields.append(field)
            answered_questions.append(question)
        else:
            missing_fields.append(field)
            unanswered_questions.append(question)

    completion_ratio = len(provided_fields) / len(questions) if questions else 1.0
    return {
        "provided_fields": provided_fields,
        "missing_fields": missing_fields,
        "answered_questions": answered_questions,
        "unanswered_questions": unanswered_questions,
        "completion_ratio": completion_ratio,
    }


def build_clarification_panel_data(
    task_id: str,
    business_context: dict | None,
) -> dict:
    """
    Build Streamlit-friendly clarification panel data.
    """
    return {
        "task_id": task_id,
        "questions": get_questions_for_task(task_id),
        "status": assess_clarification_status(task_id, business_context),
    }
