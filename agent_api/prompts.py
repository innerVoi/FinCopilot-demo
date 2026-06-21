from agent_api.schemas import (
    ANOMALY_AGENT,
    CASHFLOW_AGENT,
    MANAGER_AGENT,
    PLANNING_AGENT,
    REPORT_AGENT,
    SAFETY_AGENT,
    SUPPORTED_INTENTS,
    SUPPORTED_SPECIALIST_AGENTS,
)
from agent_api.tool_schemas import build_tool_descriptions_text, get_agent_tool_names


COMMON_SAFETY_INSTRUCTIONS = """
你是 FinCopilot 中的小微企业财务行动助手的一部分。
你只能基于用户上传数据、工具结果和用户补充信息进行分析。
你不能编造财务数字。
你不能认定任何交易为欺诈，只能提示“可能存在风险，建议核查”。
你不能提供投资、税务、法律、债务处置或专业财务建议。
你不能承诺任何财务结果。
你不能建议用户自动付款、转账或执行不可逆财务操作。
如信息不足，必须明确说明不确定性，并提出需要补充的信息。
"""

MANAGER_AGENT_PROMPT = """
你是 FinCopilot 的 Manager Agent，负责理解小微企业主的财务问题，并决定应该调用哪些专业 Agent 和工具。

你的任务：
1. 理解用户的真实目标；
2. 判断 intent；
3. 判断需要哪些 Specialist Agent；
4. 判断是否需要追问；
5. 规划需要使用哪些工具摘要；
6. 不直接计算财务指标；
7. 不编造财务结果；
8. 输出结构化 Manager Plan。

输出要求：
1. 只输出 JSON；
2. 不输出 Markdown；
3. 不要解释 JSON；
4. intent 只能从允许的 intents 中选择；
5. selected_agents 只能从允许的 specialist agents 中选择；
6. tool_plan 只能从可用工具列表中选择；
7. 不编造财务数字；
8. 不直接计算指标；
9. 不直接判断异常；
10. 不认定欺诈；
11. 不提供投资、税务、法律或债务处置建议。

你需要优先帮助用户回答三个问题：
1. 我现在的钱够不够？
2. 哪些支出有问题？
3. 接下来该怎么收钱、付款和控制风险？
"""

CASHFLOW_AGENT_PROMPT = """
你是 FinCopilot 的 Cashflow Agent，负责解释小微企业现金流风险。

你只能基于工具返回的现金流摘要、发票摘要、行动项摘要和用户补充业务信息进行判断。

你需要回答：
1. 当前现金流风险等级是什么；
2. 主要风险来源是什么；
3. 还缺少哪些关键信息；
4. 用户下一步应优先核查什么。

你不能提供融资、投资、税务、法律或债务处置建议。

输出要求：只输出 JSON，不输出 Markdown，不解释 JSON 之外的内容；不要编造数字；所有数字必须来自上下文摘要；如果上下文中没有数据，应说明信息不足。
"""

ANOMALY_AGENT_PROMPT = """
你是 FinCopilot 的 Anomaly Agent，负责解释异常支出和可疑交易。

你只能基于规则异常、模型异常和工具结果进行解释。
你不能认定欺诈。
你只能说“可能存在风险”“建议核查”“需要确认业务背景”。

你需要输出：
1. 最值得核查的支出；
2. 异常原因；
3. 核查建议；
4. 需要用户补充的业务背景。

输出要求：只输出 JSON，不输出 Markdown，不解释 JSON 之外的内容；不要编造数字；所有数字必须来自上下文摘要；不能认定欺诈，只能提示可能存在风险并建议核查。
"""

PLANNING_AGENT_PROMPT = """
你是 FinCopilot 的 Planning Agent，负责将小微企业的经营目标转化为谨慎的行动建议。

你可以帮助用户分析：
1. 是否适合增加促销预算；
2. 是否适合增加采购或进货；
3. 当前目标是否现实；
4. 哪些行动应优先执行。

你不能承诺收入增长。
你不能提供投资、税务、法律或债务处置建议。
你必须说明建议基于当前上传数据和用户补充信息，可能不完整。

输出要求：只输出 JSON，不输出 Markdown，不解释 JSON 之外的内容；不要编造数字；所有数字必须来自上下文摘要；不能承诺结果。
"""

REPORT_AGENT_PROMPT = """
你是 FinCopilot 的 Report Agent，负责把 Agent 工作流结果整理成清晰、负责任、可执行的报告。

报告应包含：
1. 当前状态；
2. 主要发现；
3. 主要风险；
4. 建议行动；
5. 未确定信息；
6. 安全边界。

你不能编造数据。
你必须保留免责声明。

输出要求：只输出 JSON，不输出 Markdown，不解释 JSON 之外的内容；不要编造数字；所有数字必须来自上下文摘要。
"""

SAFETY_AGENT_PROMPT = """
你是 FinCopilot 的 Safety Agent，负责检查输出是否符合财务安全边界。

你需要阻止：
1. 投资建议；
2. 税务建议；
3. 法律建议；
4. 债务处置建议；
5. 欺诈认定；
6. 收益承诺；
7. 自动付款或转账建议；
8. 过度确定的财务判断。

如果输出存在风险，应改写为风险提醒、核查建议和不确定性说明。
"""

PROMPT_MAP = {
    MANAGER_AGENT: MANAGER_AGENT_PROMPT,
    CASHFLOW_AGENT: CASHFLOW_AGENT_PROMPT,
    ANOMALY_AGENT: ANOMALY_AGENT_PROMPT,
    PLANNING_AGENT: PLANNING_AGENT_PROMPT,
    REPORT_AGENT: REPORT_AGENT_PROMPT,
    SAFETY_AGENT: SAFETY_AGENT_PROMPT,
}


def get_agent_prompt(agent_name: str) -> str:
    """
    Return the system prompt for an agent.
    """
    agent_prompt = PROMPT_MAP.get(agent_name, MANAGER_AGENT_PROMPT)
    return f"{COMMON_SAFETY_INSTRUCTIONS.strip()}\n\n{agent_prompt.strip()}"


def get_all_agent_prompts() -> dict:
    """
    Return all agent prompts.
    """
    return {agent_name: get_agent_prompt(agent_name) for agent_name in PROMPT_MAP}


def build_manager_prompt_with_context(user_query: str, context_summary: dict | None = None) -> str:
    """
    Build a Manager Agent prompt with compact context only.
    """
    context_summary = context_summary or {}
    manager_context = {
        "business_snapshot": context_summary.get("business_snapshot", {}),
        "data_availability": context_summary.get("data_availability", {}),
        "business_context": context_summary.get("business_context", {}),
        "available_tool_names": get_agent_tool_names(),
    }
    output_schema = {
        "intent": "cashflow_check",
        "user_goal": "判断未来 30 天现金流是否安全",
        "selected_agents": ["cashflow_agent"],
        "tool_plan": ["get_cashflow_summary"],
        "need_clarification": True,
        "clarifying_questions": ["当前企业账户真实可用余额是多少？"],
        "response_strategy": "answer_with_cashflow_risk_and_action_plan",
        "safety_notes": ["只做财务整理和风险提醒，不提供投资、税务、法律或债务处置建议。"],
    }
    return (
        f"{get_agent_prompt(MANAGER_AGENT)}\n\n"
        "请基于以下用户问题、摘要上下文中的高层摘要和可用工具说明生成 Manager Plan。不要使用或要求完整 DataFrame。\n\n"
        f"用户问题：{user_query or ''}\n"
        f"高层摘要：{manager_context}\n\n"
        f"允许的 intents：{SUPPORTED_INTENTS}\n"
        f"允许的 specialist agents：{SUPPORTED_SPECIALIST_AGENTS}\n"
        f"{build_tool_descriptions_text()}\n"
        f"输出 JSON schema 示例：{output_schema}\n"
        "必须只输出 JSON，不要输出 Markdown，不要输出额外解释。\n"
    )


def build_specialist_prompt_with_context(
    agent_name: str,
    user_query: str,
    manager_plan: dict | None = None,
    context_summary: dict | None = None,
) -> str:
    """
    Build a Specialist Agent prompt with compact context only.
    """
    manager_plan = manager_plan or {}
    context_summary = context_summary or {}
    if agent_name == CASHFLOW_AGENT:
        relevant_context = {
            "cashflow_summary": context_summary.get("cashflow_summary", {}),
            "invoice_summary": context_summary.get("invoice_summary", {}),
            "action_summary": context_summary.get("action_summary", {}),
        }
    elif agent_name == ANOMALY_AGENT:
        relevant_context = {
            "anomaly_summary": context_summary.get("anomaly_summary", {}),
            "business_context": context_summary.get("business_context", {}),
        }
    elif agent_name == PLANNING_AGENT:
        relevant_context = {
            "goal_summary": context_summary.get("goal_summary", {}),
            "cashflow_summary": context_summary.get("cashflow_summary", {}),
            "action_summary": context_summary.get("action_summary", {}),
        }
    elif agent_name == REPORT_AGENT:
        relevant_context = {
            "business_snapshot": context_summary.get("business_snapshot", {}),
            "report_summary": context_summary.get("report_summary", {}),
            "progress_summary": context_summary.get("progress_summary", {}),
        }
    else:
        relevant_context = {
            "business_snapshot": context_summary.get("business_snapshot", {}),
            "data_availability": context_summary.get("data_availability", {}),
        }
    output_schema = {
        "agent_name": agent_name,
        "summary": "...",
        "findings": [],
        "risks": [],
        "recommended_actions": [],
        "needs_user_input": False,
        "questions": [],
        "confidence": "medium",
        "safety_note": "...",
    }
    return (
        f"{get_agent_prompt(agent_name)}\n\n"
        "请基于 Manager Plan 和工具摘要进行说明。不要编造财务数字，不要读取完整 DataFrame。\n"
        "必须只输出 JSON，不要输出 Markdown，不要输出额外解释。\n\n"
        f"用户问题：{user_query or ''}\n"
        f"Manager Plan：{manager_plan}\n"
        f"相关摘要上下文：{relevant_context}\n"
        f"输出 JSON schema 示例：{output_schema}\n"
    )
