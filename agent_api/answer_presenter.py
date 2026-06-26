SAFETY_NOTE = (
    "This result is for financial organization, risk reminders, and educational support only. "
    "It is not investment, tax, legal, debt-resolution, or professional financial advice."
)

HEADLINE_BY_INTENT = {
    "cashflow_check": "Cash-flow safety analysis is complete",
    "expense_anomaly_review": "Suspicious-expense review is complete",
    "goal_or_budget_planning": "Budget and goal action plan is ready",
    "promotion_or_purchase_planning": "Business planning risk analysis is complete",
    "invoice_or_payment_review": "Invoice and payment priority review is complete",
    "general_finance_summary": "Financial overview is ready",
    "unknown": "FinCopilot has completed this analysis",
}

INTENT_TO_DETAIL_SECTIONS = {
    "cashflow_check": [
        {"label": "Cash-flow Details", "target_page": "Analysis Details", "section": "Invoices & Cash Flow", "description": "View cash-flow metrics, invoice pressure, and tool summaries."},
        {"label": "Action Items", "target_page": "Actions & Reports", "section": "Action Items", "description": "Review suggested actions and handling status."},
    ],
    "expense_anomaly_review": [
        {"label": "Suspicious Expense Details", "target_page": "Analysis Details", "section": "Suspicious Expenses", "description": "View rule-based and model-based anomaly results."},
        {"label": "Action Items", "target_page": "Actions & Reports", "section": "Action Items", "description": "Review anomaly-check action items."},
    ],
    "goal_or_budget_planning": [
        {"label": "Goal Details", "target_page": "Analysis Details", "section": "Goals", "description": "View goal progress and budget impact."},
        {"label": "Reports", "target_page": "Actions & Reports", "section": "Reports", "description": "View this Multi-Agent report."},
    ],
    "promotion_or_purchase_planning": [
        {"label": "Business Planning Details", "target_page": "Analysis Details", "section": "Goals", "description": "View cash-flow, budget, and goal impact."},
        {"label": "Reports", "target_page": "Actions & Reports", "section": "Reports", "description": "View this Multi-Agent report."},
    ],
    "invoice_or_payment_review": [
        {"label": "Invoice and Payment Details", "target_page": "Analysis Details", "section": "Invoices & Cash Flow", "description": "Review invoice status and payment pressure."},
        {"label": "Action Items", "target_page": "Actions & Reports", "section": "Action Items", "description": "Review payment-priority action items."},
    ],
    "general_finance_summary": [
        {"label": "Full Analysis Details", "target_page": "Analysis Details", "section": "Budget & Categories", "description": "View budget, cash-flow, anomaly, and goal details."},
        {"label": "Full Report", "target_page": "Actions & Reports", "section": "Reports", "description": "View this Multi-Agent report."},
    ],
}


def safe_get(data: dict | None, key: str, default=None):
    """
    Safely read a dictionary key.
    """
    if not isinstance(data, dict):
        return default
    return data.get(key, default)


def ensure_list(value) -> list:
    """
    Convert common values into a list.
    """
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple) or isinstance(value, set):
        return list(value)
    if isinstance(value, str):
        return [value] if value else []
    return [value]


def infer_status_type(value: str | None) -> str:
    """
    Map risk / confidence / mode values into UI status types.
    """
    normalized = str(value or "").strip().lower()
    if normalized in {"high", "danger", "error", "fallback"}:
        return "danger"
    if normalized in {"medium", "warning", "mixed"}:
        return "warning"
    if normalized in {"low", "success", "safe", "api_agent"}:
        return "success"
    return "info"


def _get_manager_plan(turn_result: dict | None) -> dict:
    turn_result = turn_result or {}
    manager_plan = safe_get(turn_result, "manager_plan", {})
    if manager_plan:
        return manager_plan
    manager_result = safe_get(turn_result, "manager_result", {})
    return safe_get(manager_result, "manager_plan", {}) or {}


def _iter_specialist_results(turn_result: dict | None):
    specialist_outputs = safe_get(turn_result, "specialist_outputs", {}) or {}
    for agent_name, payload in specialist_outputs.items():
        if not isinstance(payload, dict):
            continue
        yield agent_name, safe_get(payload, "result", {}) or {}


def _first_specialist_summary(turn_result: dict | None) -> str:
    for _agent_name, result in _iter_specialist_results(turn_result):
        summary = str(safe_get(result, "summary", "") or "").strip()
        if summary:
            return summary
    return ""


def _clip_text(text: str, max_length: int = 220) -> str:
    value = " ".join(str(text or "").split())
    if len(value) <= max_length:
        return value
    return value[: max_length - 1].rstrip() + "..."


def _extract_report_summary(report_markdown: str, max_length: int = 900) -> str:
    """
    Extract a readable report summary without using it as a title.
    """
    lines = [
        line.strip()
        for line in str(report_markdown or "").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    summary = "\n\n".join(lines[:4])
    return _clip_text(summary, max_length=max_length) if summary else "This report has been generated. Expand it to view the full content."


def build_headline(turn_result: dict | None) -> str:
    """
    Build a short headline from intent and specialist summaries.
    """
    manager_plan = _get_manager_plan(turn_result)
    intent = safe_get(manager_plan, "intent", "unknown")
    summary = _first_specialist_summary(turn_result)
    if summary:
        return _clip_text(summary, max_length=42)
    return HEADLINE_BY_INTENT.get(intent, HEADLINE_BY_INTENT["unknown"])


def build_summary(turn_result: dict | None) -> str:
    """
    Build a compact summary for the main UI.
    """
    turn_result = turn_result or {}
    assistant_reply = str(safe_get(turn_result, "assistant_reply", "") or "").strip()
    if assistant_reply:
        parts = [part.strip() for part in assistant_reply.replace("\n", " ").split("。") if part.strip()]
        return _clip_text("。".join(parts[:2]) + ("。" if parts else ""), max_length=260)
    specialist_summary = _first_specialist_summary(turn_result)
    if specialist_summary:
        return _clip_text(specialist_summary, max_length=260)
    return "FinCopilot has completed this analysis. Review the metrics, risks, action items, and follow-up questions below."


def build_status_badge(turn_result: dict | None) -> dict:
    """
    Build the main status badge.
    """
    turn_result = turn_result or {}
    value = safe_get(turn_result, "mode", "fallback")
    return {
        "label": "Agent Mode",
        "value": value,
        "type": infer_status_type(value),
    }


def build_metric_cards(turn_result: dict | None) -> list[dict]:
    """
    Build key metric cards.
    """
    turn_result = turn_result or {}
    manager_plan = _get_manager_plan(turn_result)
    tool_results = ensure_list(safe_get(turn_result, "tool_results", []))
    specialist_outputs = safe_get(turn_result, "specialist_outputs", {}) or {}
    return [
        {"label": "Task Type", "value": safe_get(manager_plan, "intent", "unknown"), "help": "Task type identified by the Manager Agent."},
        {"label": "Agent Mode", "value": safe_get(turn_result, "mode", "fallback"), "help": "Whether this turn used live Agent, fallback, or mixed mode."},
        {"label": "Tools Used", "value": len(tool_results), "help": "Number of tool summaries triggered by the Manager Plan."},
        {"label": "Specialists", "value": len(specialist_outputs), "help": "Number of Specialist Agents involved in this turn."},
        {"label": "Suggested Actions", "value": len(ensure_list(safe_get(turn_result, "suggested_actions", []))), "help": "Number of suggested actions generated this turn."},
        {"label": "Info Needed", "value": len(ensure_list(safe_get(turn_result, "clarifying_questions", []))), "help": "Additional information that would improve analysis quality."},
    ]


def _infer_risk_severity(text: str) -> str:
    value = str(text or "").lower()
    if any(keyword in value for keyword in ["high risk", "gap", "overdue", "insufficient", "anomaly"]):
        return "high"
    if any(keyword in value for keyword in ["may", "needs confirmation", "incomplete"]):
        return "medium"
    return "low"


def build_risk_cards(turn_result: dict | None) -> list[dict]:
    """
    Extract risks from Specialist outputs.
    """
    cards = []
    for agent_name, result in _iter_specialist_results(turn_result):
        for risk in ensure_list(safe_get(result, "risks", [])):
            description = str(risk or "").strip()
            if not description:
                continue
            severity = _infer_risk_severity(description)
            cards.append(
                {
                    "title": "Risk Alert",
                    "description": description,
                    "severity": severity,
                    "type": infer_status_type(severity),
                    "source": agent_name,
                }
            )
    return cards


def build_action_cards(turn_result: dict | None) -> list[dict]:
    """
    Build action cards from chat_action_items or suggested_actions.
    """
    turn_result = turn_result or {}
    action_items = ensure_list(safe_get(turn_result, "chat_action_items", []))
    if action_items:
        cards = []
        for item in action_items:
            if not isinstance(item, dict):
                continue
            cards.append(
                {
                    "title": safe_get(item, "title", ""),
                    "priority": safe_get(item, "priority", "medium"),
                    "description": safe_get(item, "description", safe_get(item, "reason", "")),
                    "deadline": safe_get(item, "suggested_deadline", "within 3 days"),
                    "status": safe_get(item, "status", "pending"),
                }
            )
        return [card for card in cards if card["title"]]

    cards = []
    for action in ensure_list(safe_get(turn_result, "suggested_actions", [])):
        title = str(action or "").strip()
        if title:
            cards.append(
                {
                    "title": title,
                    "priority": "medium",
                    "description": "This action comes from the current Multi-Agent analysis.",
                    "deadline": "within 3 days",
                    "status": "pending",
                }
            )
    return cards


def build_clarification_cards(turn_result: dict | None) -> list[dict]:
    """
    Build clarification cards from clarifying questions.
    """
    return [
        {
            "question": str(question or ""),
            "why_needed": "Providing this information will make follow-up analysis more accurate.",
        }
        for question in ensure_list(safe_get(turn_result or {}, "clarifying_questions", []))
        if str(question or "").strip()
    ]


def build_detail_sections(turn_result: dict | None) -> list[dict]:
    """
    Build detail-entry cards by intent.
    """
    intent = safe_get(_get_manager_plan(turn_result), "intent", "unknown")
    inline_section = {
        "label": "Expand the detailed preview on this page",
        "target_page": "Copilot Home",
        "section": "Detailed Result Preview",
        "description": "View cash flow, anomalies, action items, and report previews without leaving this page.",
    }
    return [inline_section] + list(
        INTENT_TO_DETAIL_SECTIONS.get(intent, INTENT_TO_DETAIL_SECTIONS["general_finance_summary"])
    )


def build_report_card(turn_result: dict | None) -> dict:
    """
    Build report availability card.
    """
    report_markdown = str(safe_get(turn_result or {}, "report_markdown", "") or "")
    return {
        "available": bool(report_markdown.strip()),
        "title": "Multi-Agent Conversation Report",
        "summary": _extract_report_summary(report_markdown) if report_markdown.strip() else "",
        "download_label": "Download this report",
    }


def build_memory_cards(turn_result: dict | None) -> list[dict]:
    """
    Build memory cards from turn_result["memory_context"].
    """
    memory_context = safe_get(turn_result or {}, "memory_context", {}) or {}
    memory_count = int(safe_get(memory_context, "memory_count", 0) or 0)
    if not memory_count:
        return [
            {
                "title": "No Business Memory Yet",
                "description": "This analysis is mainly based on the currently uploaded data.",
                "items": [],
            }
        ]
    items = []
    for key in [
        "known_normal_payments",
        "known_suppliers",
        "cash_context",
        "expected_receivables",
        "recurring_expenses",
        "business_rules",
        "user_preferences",
        "known_risks",
    ]:
        items.extend(str(item) for item in ensure_list(memory_context.get(key)) if str(item).strip())
    return [
        {
            "title": "Business Memory Used",
            "description": f"This analysis used {memory_count} user-confirmed business facts.",
            "items": items[:6],
        }
    ]


def build_answer_presentation(turn_result: dict | None) -> dict:
    """
    Convert a turn_result into a UI-friendly presentation dictionary.
    """
    return {
        "headline": build_headline(turn_result),
        "summary": build_summary(turn_result),
        "status_badge": build_status_badge(turn_result),
        "metric_cards": build_metric_cards(turn_result),
        "memory_cards": build_memory_cards(turn_result),
        "risk_cards": build_risk_cards(turn_result),
        "action_cards": build_action_cards(turn_result),
        "clarification_cards": build_clarification_cards(turn_result),
        "detail_sections": build_detail_sections(turn_result),
        "report": build_report_card(turn_result),
        "debug_available": bool(turn_result),
        "safety_note": SAFETY_NOTE,
    }
