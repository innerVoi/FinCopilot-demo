TOOL_REGISTRY = {
    "categorize_transactions": {
        "tool_name": "categorize_transactions",
        "display_name": "Transaction Categorization Tool",
        "description": "Adds categories and categorization reasons to transactions using keyword rules.",
        "input_keys": ["transactions_df"],
        "output_key": "transactions_df",
        "category": "data_processing",
        "is_deterministic": True,
        "requires_llm": False,
        "safety_note": "Rule-based categorization only; not an accounting or audit conclusion.",
    },
    "analyze_budget": {
        "tool_name": "analyze_budget",
        "display_name": "Budget Summary Tool",
        "description": "Summarizes income, expenses, net cash flow, category spending, and monthly cash movement.",
        "input_keys": ["transactions_df"],
        "output_key": "budget_result",
        "category": "budget",
        "is_deterministic": True,
        "requires_llm": False,
        "safety_note": "Based only on uploaded transaction data; not a complete financial statement.",
    },
    "analyze_invoices": {
        "tool_name": "analyze_invoices",
        "display_name": "Invoice Review Tool",
        "description": "Organizes paid, unpaid, overdue, and upcoming invoices.",
        "input_keys": ["invoices_df"],
        "output_key": "invoice_result",
        "category": "invoice",
        "is_deterministic": True,
        "requires_llm": False,
        "safety_note": "Based only on uploaded invoice data; not legal or tax judgment.",
    },
    "analyze_cashflow": {
        "tool_name": "analyze_cashflow",
        "display_name": "Cash-Flow Risk Analysis Tool",
        "description": "Estimates 30-day cash-flow risk from transactions and invoice results.",
        "input_keys": ["transactions_df", "invoice_result"],
        "output_key": "cashflow_result",
        "category": "cashflow",
        "is_deterministic": True,
        "requires_llm": False,
        "safety_note": "Cash-flow estimate based only on uploaded data; not actual account balance or professional forecasting.",
    },
    "analyze_goals": {
        "tool_name": "analyze_goals",
        "display_name": "Financial Goal Analysis Tool",
        "description": "Analyzes financial goal progress, gaps, risk levels, and suggested actions.",
        "input_keys": ["goals_df", "budget_result", "cashflow_result"],
        "output_key": "goal_result",
        "category": "goal",
        "is_deterministic": True,
        "requires_llm": False,
        "safety_note": "For goal tracking and reminders only; not investment or professional financial advice.",
    },
    "detect_rule_anomalies": {
        "tool_name": "detect_rule_anomalies",
        "display_name": "Rule and Statistical Anomaly Tool",
        "description": "Detects rule anomalies such as large expenses, duplicate charges, rare merchants, and invoice pressure.",
        "input_keys": ["transactions_df", "invoice_result"],
        "output_key": "rule_anomalies_df",
        "category": "anomaly",
        "is_deterministic": True,
        "requires_llm": False,
        "safety_note": "Only flags records that may need review; does not determine fraud.",
    },
    "detect_lof_anomalies": {
        "tool_name": "detect_lof_anomalies",
        "display_name": "LOF Model Anomaly Tool",
        "description": "Uses Local Outlier Factor to score transaction anomaly risk.",
        "input_keys": ["transactions_df"],
        "output_key": "lof_result_df",
        "category": "anomaly",
        "is_deterministic": True,
        "requires_llm": False,
        "safety_note": "Model scores are risk reminders, not factual determinations.",
    },
    "explain_transaction_risk": {
        "tool_name": "explain_transaction_risk",
        "display_name": "Single-Anomaly Explanation Tool",
        "description": "Generates a natural-language risk explanation for one anomaly record.",
        "input_keys": ["selected_anomaly_row"],
        "output_key": "risk_explanation",
        "category": "explanation",
        "is_deterministic": False,
        "requires_llm": True,
        "safety_note": "Not called automatically in batch; uses a template fallback when no API key is available.",
    },
    "generate_planning_summary": {
        "tool_name": "generate_planning_summary",
        "display_name": "Copilot Summary Tool",
        "description": "Generates a responsible business finance summary from existing analysis results.",
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
        "safety_note": "Not executed automatically; summaries must include the responsible-finance disclaimer.",
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
