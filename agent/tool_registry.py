TOOL_REGISTRY = {
    "categorize_transactions": {
        "tool_name": "categorize_transactions",
        "display_name": "交易分类工具",
        "description": "基于关键词规则为交易流水添加类别和分类原因。",
        "input_keys": ["transactions_df"],
        "output_key": "transactions_df",
        "category": "data_processing",
        "is_deterministic": True,
        "requires_llm": False,
        "safety_note": "仅做规则分类，不构成会计或审计结论。",
    },
    "analyze_budget": {
        "tool_name": "analyze_budget",
        "display_name": "预算统计工具",
        "description": "统计收入、支出、净现金流、类别支出和月度收支。",
        "input_keys": ["transactions_df"],
        "output_key": "budget_result",
        "category": "budget",
        "is_deterministic": True,
        "requires_llm": False,
        "safety_note": "仅基于上传交易数据统计，不代表完整财务报表。",
    },
    "analyze_invoices": {
        "tool_name": "analyze_invoices",
        "display_name": "发票整理工具",
        "description": "整理已支付、未支付、逾期和未来到期发票。",
        "input_keys": ["invoices_df"],
        "output_key": "invoice_result",
        "category": "invoice",
        "is_deterministic": True,
        "requires_llm": False,
        "safety_note": "仅基于上传发票数据整理，不代表法律或税务判断。",
    },
    "analyze_cashflow": {
        "tool_name": "analyze_cashflow",
        "display_name": "现金流风险分析工具",
        "description": "基于交易流水和发票结果估算未来 30 天现金流风险。",
        "input_keys": ["transactions_df", "invoice_result"],
        "output_key": "cashflow_result",
        "category": "cashflow",
        "is_deterministic": True,
        "requires_llm": False,
        "safety_note": "仅基于上传数据进行现金流估算，不代表真实账户余额或专业财务预测。",
    },
    "analyze_goals": {
        "tool_name": "analyze_goals",
        "display_name": "财务目标分析工具",
        "description": "分析财务目标完成率、缺口、风险等级和建议动作。",
        "input_keys": ["goals_df", "budget_result", "cashflow_result"],
        "output_key": "goal_result",
        "category": "goal",
        "is_deterministic": True,
        "requires_llm": False,
        "safety_note": "仅用于目标进度整理和提醒，不构成投资或专业理财建议。",
    },
    "detect_rule_anomalies": {
        "tool_name": "detect_rule_anomalies",
        "display_name": "规则/统计异常识别工具",
        "description": "识别大额支出、重复扣费、罕见商户和发票压力等规则异常。",
        "input_keys": ["transactions_df", "invoice_result"],
        "output_key": "rule_anomalies_df",
        "category": "anomaly",
        "is_deterministic": True,
        "requires_llm": False,
        "safety_note": "只提示可能需要核查的记录，不认定欺诈。",
    },
    "detect_lof_anomalies": {
        "tool_name": "detect_lof_anomalies",
        "display_name": "LOF 模型异常检测工具",
        "description": "使用 Local Outlier Factor 为交易计算异常分数和风险等级。",
        "input_keys": ["transactions_df"],
        "output_key": "lof_result_df",
        "category": "anomaly",
        "is_deterministic": True,
        "requires_llm": False,
        "safety_note": "模型分数用于风险提醒，不代表事实认定。",
    },
    "explain_transaction_risk": {
        "tool_name": "explain_transaction_risk",
        "display_name": "单条异常解释工具",
        "description": "对单条异常记录生成自然语言风险解释。",
        "input_keys": ["selected_anomaly_row"],
        "output_key": "risk_explanation",
        "category": "explanation",
        "is_deterministic": False,
        "requires_llm": True,
        "safety_note": "不会自动批量调用；无 API Key 时使用模板 fallback。",
    },
    "generate_planning_summary": {
        "tool_name": "generate_planning_summary",
        "display_name": "Copilot 摘要工具",
        "description": "基于已有分析结果生成负责任的经营财务摘要。",
        "input_keys": [
            "budget_result",
            "invoice_result",
            "cashflow_result",
            "goal_result",
            "rule_anomalies_df",
            "lof_result_df",
        ],
        "output_key": "planning_summary",
        "category": "summary",
        "is_deterministic": False,
        "requires_llm": True,
        "safety_note": "不会自动执行；摘要必须包含负责任财务免责声明。",
    },
}


def get_tool_registry() -> dict:
    """
    Return all registered Agent tools.
    """
    return {name: spec.copy() for name, spec in TOOL_REGISTRY.items()}


def list_available_tools() -> list[dict]:
    """
    Return all tool specs as a list for UI display.
    """
    return list(get_tool_registry().values())


def get_tool_spec(tool_name: str) -> dict:
    """
    Return a registered tool spec by name.
    """
    registry = get_tool_registry()
    if tool_name not in registry:
        raise ValueError(f"Unsupported tool_name: {tool_name}")
    return registry[tool_name]


def get_tools_by_category(category: str) -> list[dict]:
    """
    Return tools matching a category.
    """
    return [
        tool
        for tool in list_available_tools()
        if tool.get("category") == category
    ]


def validate_tool_plan(tool_names: list[str]) -> dict:
    """
    Validate that all planned tools are registered.
    """
    registry = get_tool_registry()
    available_tools = [tool_name for tool_name in tool_names if tool_name in registry]
    missing_tools = [tool_name for tool_name in tool_names if tool_name not in registry]
    return {
        "valid": not missing_tools,
        "available_tools": available_tools,
        "missing_tools": missing_tools,
    }
