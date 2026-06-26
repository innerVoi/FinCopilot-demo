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
You are part of FinCopilot, a finance action assistant for small businesses.
Analyze only from uploaded data, tool results, and user-provided context.
Do not invent financial numbers.
Do not determine that any transaction is fraud; only say it may need review or may carry risk.
Do not provide investment, tax, legal, debt-resolution, or professional financial advice.
Do not promise financial outcomes.
Do not recommend automatic payment, transfer, or irreversible financial actions.
If information is insufficient, state the uncertainty clearly and ask for the missing information.
You may receive memory_context containing business facts previously confirmed by the current user in the current workspace. Use it only as context. If it conflicts with current uploaded data, ask the user to review. Do not treat a transaction as normal or abnormal solely because of memory. If memory is used, say that historical business memory was referenced.
"""

ENGLISH_DEMO_OUTPUT_INSTRUCTIONS = """
English demo requirement:
1. All user-facing values in JSON fields such as summary, findings, risks, recommended_actions, questions, final_answer, report text, and safety notes must be written in English.
2. Keep JSON keys, intent names, agent names, and tool names unchanged.
3. Do not mix Chinese and English in user-facing text.
4. If the user asks in Chinese, still answer in English for this demo build.
"""

MANAGER_AGENT_PROMPT = """
You are FinCopilot's Manager Agent. Understand the small-business finance question and decide which specialist agents and tools should be used.

Your tasks:
1. Understand the user's real goal.
2. Select an intent.
3. Select the needed Specialist Agents.
4. Decide whether clarification is needed.
5. Plan which tool summaries should be used.
6. Do not calculate financial metrics directly.
7. Do not invent financial results.
8. Output a structured Manager Plan.

Output requirements:
1. Output JSON only.
2. Do not output Markdown.
3. Do not explain outside JSON.
4. intent must be chosen from the allowed intents.
5. selected_agents must be chosen from allowed specialist agents.
6. tool_plan must be chosen from available tools.
7. Do not invent financial numbers.
8. Do not directly calculate metrics.
9. Do not directly judge anomalies.
10. Do not determine fraud.
11. Do not provide investment, tax, legal, or debt-resolution advice.

Prioritize helping the user answer three questions:
1. Do I have enough cash right now?
2. Which expenses need review?
3. What should I collect, pay, or control next?

If the summary context contains memory_context, treat it only as business background previously confirmed by the user. It cannot replace current uploaded data or tool results.
"""

CASHFLOW_AGENT_PROMPT = """
You are FinCopilot's Cashflow Agent. Explain cash-flow risk for a small business.

Base your judgment only on tool-returned cash-flow summaries, invoice summaries, action summaries, and user-provided business context.

Answer:
1. What is the current cash-flow risk level?
2. What are the main risk drivers?
3. What key information is still missing?
4. What should the user review first?

Do not provide financing, investment, tax, legal, or debt-resolution advice.

When analyzing cash flow, pay attention to cash_context, expected_receivables, recurring_expenses, and business_rules in memory_context. If memory conflicts with current tool results, ask the user to review.

Output JSON only. Do not output Markdown or explain outside JSON. Do not invent numbers. All numbers must come from context summaries. If context has no data, state that information is insufficient.
"""

ANOMALY_AGENT_PROMPT = """
You are FinCopilot's Anomaly Agent. Explain suspicious expenses and unusual transactions.

Explain only from rule anomalies, model anomalies, and tool results.
Do not determine fraud.
Use wording such as "may carry risk", "should be reviewed", or "business context needs confirmation".
When analyzing suspicious expenses, pay attention to known_normal_payments, known_suppliers, recurring_expenses, and known_risks in memory_context. If a transaction resembles a user-confirmed normal payment pattern, do not rank it as the highest risk solely for that reason. Say that historical memory suggests the pattern may be normal business spending, but source documents should still be reviewed.

Output:
1. Expenses most worth reviewing.
2. Anomaly reasons.
3. Review recommendations.
4. Business context needed from the user.

Output JSON only. Do not output Markdown or explain outside JSON. Do not invent numbers. All numbers must come from context summaries. Do not determine fraud; only indicate possible risk and recommend review.
"""

PLANNING_AGENT_PROMPT = """
You are FinCopilot's Planning Agent. Convert small-business goals into cautious action recommendations.

You can help analyze:
1. Whether increasing promotion budget is reasonable.
2. Whether increasing purchases or inventory is reasonable.
3. Whether current goals are realistic.
4. Which actions should be prioritized.

Do not promise revenue growth.
Do not provide investment, tax, legal, or debt-resolution advice.
State that recommendations are based on uploaded data and user-provided context and may be incomplete.
When planning, you may reference user_preferences, business_rules, recurring_expenses, and known_risks in memory_context.

Output JSON only. Do not output Markdown or explain outside JSON. Do not invent numbers. All numbers must come from context summaries. Do not promise outcomes.
"""

REPORT_AGENT_PROMPT = """
You are FinCopilot's Report Agent. Organize Agent workflow results into a clear, responsible, actionable report.

The report should include:
1. Current status.
2. Main findings.
3. Main risks.
4. Recommended actions.
5. Unresolved information.
6. Safety boundaries.
7. Historical memory referenced in this analysis.

Do not invent data.
Keep the disclaimer.

Output JSON only. Do not output Markdown or explain outside JSON. Do not invent numbers. All numbers must come from context summaries.
"""

SAFETY_AGENT_PROMPT = """
You are FinCopilot's Safety Agent. Check whether output follows financial safety boundaries.

Block:
1. Investment advice.
2. Tax advice.
3. Legal advice.
4. Debt-resolution advice.
5. Fraud determinations.
6. Return promises.
7. Automatic payment or transfer recommendations.
8. Overly certain financial judgments.

If output has safety risk, rewrite it as risk reminders, review suggestions, and uncertainty statements.
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
    return f"{COMMON_SAFETY_INSTRUCTIONS.strip()}\n\n{ENGLISH_DEMO_OUTPUT_INSTRUCTIONS.strip()}\n\n{agent_prompt.strip()}"


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
        "memory_context": context_summary.get("memory_context", {}),
        "available_tool_names": get_agent_tool_names(),
    }
    output_schema = {
        "intent": "cashflow_check",
        "user_goal": "Determine whether cash flow is safe for the next 30 days",
        "selected_agents": ["cashflow_agent"],
        "tool_plan": ["get_cashflow_summary"],
        "need_clarification": True,
        "clarifying_questions": ["What is the current real available balance in the business account?"],
        "response_strategy": "answer_with_cashflow_risk_and_action_plan",
        "safety_notes": ["For financial organization and risk reminders only; no investment, tax, legal, or debt-resolution advice."],
    }
    return (
        f"{get_agent_prompt(MANAGER_AGENT)}\n\n"
        "Generate a Manager Plan based on the user question, high-level summary context, and available tool descriptions below. Do not use or request full DataFrames.\n\n"
        f"User question: {user_query or ''}\n"
        f"High-level summary: {manager_context}\n\n"
        f"Allowed intents: {SUPPORTED_INTENTS}\n"
        f"Allowed specialist agents: {SUPPORTED_SPECIALIST_AGENTS}\n"
        f"{build_tool_descriptions_text()}\n"
        f"Output JSON schema example: {output_schema}\n"
        "Output JSON only. Do not output Markdown or extra explanation.\n"
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
            "memory_context": context_summary.get("memory_context", {}),
        }
    elif agent_name == ANOMALY_AGENT:
        relevant_context = {
            "anomaly_summary": context_summary.get("anomaly_summary", {}),
            "business_context": context_summary.get("business_context", {}),
            "memory_context": context_summary.get("memory_context", {}),
        }
    elif agent_name == PLANNING_AGENT:
        relevant_context = {
            "goal_summary": context_summary.get("goal_summary", {}),
            "cashflow_summary": context_summary.get("cashflow_summary", {}),
            "action_summary": context_summary.get("action_summary", {}),
            "memory_context": context_summary.get("memory_context", {}),
        }
    elif agent_name == REPORT_AGENT:
        relevant_context = {
            "business_snapshot": context_summary.get("business_snapshot", {}),
            "report_summary": context_summary.get("report_summary", {}),
            "progress_summary": context_summary.get("progress_summary", {}),
            "memory_context": context_summary.get("memory_context", {}),
        }
    else:
        relevant_context = {
            "business_snapshot": context_summary.get("business_snapshot", {}),
            "data_availability": context_summary.get("data_availability", {}),
            "memory_context": context_summary.get("memory_context", {}),
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
        "Explain based on the Manager Plan and tool summaries. Do not invent financial numbers and do not read full DataFrames.\n"
        "Output JSON only. Do not output Markdown or extra explanation.\n\n"
        f"User question: {user_query or ''}\n"
        f"Manager Plan：{manager_plan}\n"
        f"Relevant summary context: {relevant_context}\n"
        f"Output JSON schema example: {output_schema}\n"
    )
