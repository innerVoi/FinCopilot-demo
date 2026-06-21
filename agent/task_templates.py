AGENT_TASKS = [
    {
        "task_id": "cashflow_safety_check",
        "task_name": "检查未来 30 天现金流是否安全",
        "task_goal": "判断未来 30 天是否存在现金流压力，并识别主要风险来源。",
        "workflow_steps": [
            "检查交易流水、发票和财务目标数据是否存在。",
            "检查是否缺少真实账户余额、未来客户回款和未上传发票。",
            "调用预算统计工具，了解近期收入、支出和净现金流。",
            "调用发票整理工具，识别逾期和即将到期发票。",
            "调用现金流风险工具，估算未来 30 天余额和风险等级。",
            "调用异常检测工具，识别可能影响现金流的大额异常支出。",
            "汇总现金流风险来源。",
            "输出初步结论，并提示后续需要生成行动清单。",
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
        "task_name": "处理本月最可疑的异常支出",
        "task_goal": "识别最值得核查的异常支出，并为后续生成核查清单做准备。",
        "workflow_steps": [
            "调用规则/统计异常识别工具。",
            "调用 LOF 模型异常检测工具。",
            "合并两类异常结果。",
            "按风险等级、异常分数和金额影响排序。",
            "识别 Top 可疑交易。",
            "检查是否需要用户补充交易背景。",
            "汇总每条异常的检测依据。",
            "提示后续可生成行动清单和处理状态。",
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
        "task_name": "制定财务目标行动计划",
        "task_goal": "分析现金缓冲、税费准备金和运营储备等目标是否可达，并为后续行动计划做准备。",
        "workflow_steps": [
            "检查财务目标数据是否存在。",
            "调用预算统计工具，了解当前净现金流。",
            "调用现金流风险工具，判断未来现金流是否支持目标。",
            "调用目标分析工具，计算完成率、剩余缺口和所需月均储蓄。",
            "找出高风险目标。",
            "检查是否缺少真实余额或目标优先级。",
            "汇总目标风险。",
            "提示后续可生成具体行动计划。",
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
