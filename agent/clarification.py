CLARIFICATION_SCHEMA = [
    {
        "field": "current_cash_balance",
        "question": "当前企业账户真实可用余额是多少？",
        "reason": "现金流风险判断需要真实余额，否则只能基于上传流水估算。",
        "input_type": "number",
        "required": False,
        "task_ids": ["cashflow_safety_check", "goal_action_plan"],
    },
    {
        "field": "expected_receivables_30d",
        "question": "未来 30 天是否有确定客户回款？金额大约是多少？",
        "reason": "未来回款会直接影响 30 天现金流安全判断。",
        "input_type": "number",
        "required": False,
        "task_ids": ["cashflow_safety_check"],
    },
    {
        "field": "unuploaded_invoices_estimate",
        "question": "是否还有未上传的发票或固定支出？估计金额是多少？",
        "reason": "未上传支出会让现金流风险被低估。",
        "input_type": "number",
        "required": False,
        "task_ids": ["cashflow_safety_check"],
    },
    {
        "field": "large_upcoming_payments",
        "question": "未来 30 天是否有必须支付的大额款项？估计金额是多少？",
        "reason": "大额必要付款会改变短期现金流压力。",
        "input_type": "number",
        "required": False,
        "task_ids": ["cashflow_safety_check"],
    },
    {
        "field": "known_authorized_large_payments",
        "question": "是否存在已知正常的大额付款，例如房租、税费或合同款？",
        "reason": "已知正常付款可以帮助区分业务合理支出和待核查异常。",
        "input_type": "text",
        "required": False,
        "task_ids": ["suspicious_expense_review"],
    },
    {
        "field": "recurring_vendor_list",
        "question": "是否有固定供应商或常用商户名单？",
        "reason": "常用供应商背景可以帮助后续优先核查陌生商户。",
        "input_type": "text",
        "required": False,
        "task_ids": ["suspicious_expense_review"],
    },
    {
        "field": "business_context_for_top_anomalies",
        "question": "对当前 Top 高风险交易，是否有业务背景说明？",
        "reason": "业务背景可以帮助 Agent 生成更贴近实际的核查建议。",
        "input_type": "text",
        "required": False,
        "task_ids": ["suspicious_expense_review"],
    },
    {
        "field": "goal_priority_confirmation",
        "question": "当前最高优先级的财务目标是哪一个？",
        "reason": "目标优先级会影响后续行动计划排序。",
        "input_type": "text",
        "required": False,
        "task_ids": ["goal_action_plan"],
    },
    {
        "field": "expected_monthly_savings_capacity",
        "question": "未来每月预计可用于储备或目标投入的金额是多少？",
        "reason": "月度储备能力会影响目标期限和可达性判断。",
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
