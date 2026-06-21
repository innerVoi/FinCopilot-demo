TOOL_NAMES = [
    "get_business_snapshot",
    "get_budget_summary",
    "get_invoice_summary",
    "get_cashflow_summary",
    "get_anomaly_summary",
    "get_goal_summary",
    "get_action_summary",
    "get_progress_summary",
    "get_workflow_report_summary",
    "get_full_context_summary",
]


def _tool_schema(name: str, subject: str) -> dict:
    return {
        "name": name,
        "description": (
            f"Return a compact {subject} summary, not raw data. "
            "Use only for financial organization and risk reminders. "
            "This tool does not execute real financial operations."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "returns": "dict",
    }


AGENT_TOOL_SCHEMAS = [
    _tool_schema("get_business_snapshot", "business snapshot"),
    _tool_schema("get_budget_summary", "budget and category spending"),
    _tool_schema("get_invoice_summary", "invoice and payment pressure"),
    _tool_schema("get_cashflow_summary", "cashflow risk"),
    _tool_schema("get_anomaly_summary", "expense anomaly"),
    _tool_schema("get_goal_summary", "financial goal"),
    _tool_schema("get_action_summary", "action item"),
    _tool_schema("get_progress_summary", "action progress"),
    _tool_schema("get_workflow_report_summary", "workflow report"),
    _tool_schema("get_full_context_summary", "full context summary; do not call by default unless necessary"),
]


def get_agent_tool_schemas() -> list[dict]:
    """
    Return all Agent tool schemas.
    """
    return [schema.copy() for schema in AGENT_TOOL_SCHEMAS]


def get_agent_tool_names() -> list[str]:
    """
    Return all Agent tool names.
    """
    return [schema["name"] for schema in AGENT_TOOL_SCHEMAS]


def get_tool_schema(tool_name: str) -> dict | None:
    """
    Return one tool schema by name.
    """
    for schema in AGENT_TOOL_SCHEMAS:
        if schema["name"] == tool_name:
            return schema.copy()
    return None


def validate_tool_name(tool_name: str) -> bool:
    """
    Check whether a tool name is supported.
    """
    return tool_name in get_agent_tool_names()


def build_tool_descriptions_text() -> str:
    """
    Build a compact tool description text for Manager Agent prompts.
    """
    lines = [
        "可用工具列表（均返回摘要，不返回原始数据，不执行真实财务操作）："
    ]
    for schema in AGENT_TOOL_SCHEMAS:
        lines.append(f"- {schema['name']}: {schema['description']}")
    lines.append("不要默认调用 get_full_context_summary，除非确实需要整体摘要。")
    return "\n".join(lines)
