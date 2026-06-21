SAFETY_NOTE = "本结果仅用于财务整理、风险提醒和教育性支持，不构成投资、税务、法律、债务处置或专业财务建议。"

HEADLINE_BY_INTENT = {
    "cashflow_check": "现金流安全性分析已完成",
    "expense_anomaly_review": "异常支出核查建议已生成",
    "goal_or_budget_planning": "预算与目标行动建议已生成",
    "promotion_or_purchase_planning": "经营计划风险分析已完成",
    "invoice_or_payment_review": "发票与付款优先级分析已完成",
    "general_finance_summary": "财务概览总结已生成",
    "unknown": "FinCopilot 已完成本轮分析",
}

INTENT_TO_DETAIL_SECTIONS = {
    "cashflow_check": [
        {"label": "现金流详情", "target_page": "分析详情", "section": "发票与现金流", "description": "查看现金流指标、发票压力和工具摘要。"},
        {"label": "行动项", "target_page": "行动与报告", "section": "行动项", "description": "查看本轮建议行动和处理状态。"},
    ],
    "expense_anomaly_review": [
        {"label": "异常支出详情", "target_page": "分析详情", "section": "异常支出", "description": "查看规则异常和模型异常结果。"},
        {"label": "行动项", "target_page": "行动与报告", "section": "行动项", "description": "查看异常核查行动项。"},
    ],
    "goal_or_budget_planning": [
        {"label": "财务目标详情", "target_page": "分析详情", "section": "财务目标", "description": "查看目标进度和预算影响。"},
        {"label": "报告", "target_page": "行动与报告", "section": "报告", "description": "查看本轮 Multi-Agent 报告。"},
    ],
    "promotion_or_purchase_planning": [
        {"label": "经营计划详情", "target_page": "分析详情", "section": "财务目标", "description": "查看现金流、预算和目标影响。"},
        {"label": "报告", "target_page": "行动与报告", "section": "报告", "description": "查看本轮 Multi-Agent 报告。"},
    ],
    "invoice_or_payment_review": [
        {"label": "发票与付款详情", "target_page": "分析详情", "section": "发票与现金流", "description": "查看发票状态和付款压力。"},
        {"label": "行动项", "target_page": "行动与报告", "section": "行动项", "description": "查看付款优先级行动项。"},
    ],
    "general_finance_summary": [
        {"label": "完整分析详情", "target_page": "分析详情", "section": "预算与分类", "description": "查看预算、现金流、异常和目标详情。"},
        {"label": "完整报告", "target_page": "行动与报告", "section": "报告", "description": "查看本轮 Multi-Agent 报告。"},
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
    return "FinCopilot 已完成本轮分析。你可以查看下方指标、风险、行动项和补充问题。"


def build_status_badge(turn_result: dict | None) -> dict:
    """
    Build the main status badge.
    """
    turn_result = turn_result or {}
    value = safe_get(turn_result, "mode", "fallback")
    return {
        "label": "Agent 模式",
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
        {"label": "任务类型", "value": safe_get(manager_plan, "intent", "unknown"), "help": "Manager Agent 识别出的任务类型。"},
        {"label": "Agent 模式", "value": safe_get(turn_result, "mode", "fallback"), "help": "本轮是真实 Agent、fallback 或 mixed。"},
        {"label": "调用工具数", "value": len(tool_results), "help": "Manager Plan 触发的工具摘要数量。"},
        {"label": "专业 Agent 数", "value": len(specialist_outputs), "help": "本轮参与分析的 Specialist Agents 数量。"},
        {"label": "建议行动", "value": len(ensure_list(safe_get(turn_result, "suggested_actions", []))), "help": "本轮生成的建议行动数量。"},
        {"label": "需补充信息", "value": len(ensure_list(safe_get(turn_result, "clarifying_questions", []))), "help": "为了提高判断准确性建议补充的信息数量。"},
    ]


def _infer_risk_severity(text: str) -> str:
    value = str(text or "")
    if any(keyword in value for keyword in ["高风险", "缺口", "逾期", "不足", "异常"]):
        return "high"
    if any(keyword in value for keyword in ["可能", "需要确认", "不完整"]):
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
                    "title": "风险提醒",
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
                    "deadline": safe_get(item, "suggested_deadline", "3 天内"),
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
                    "description": "该行动来自本轮 Multi-Agent 分析建议。",
                    "deadline": "3 天内",
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
            "why_needed": "补充该信息可以让后续分析更准确。",
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
        "label": "在当前页面展开详细预览",
        "target_page": "Copilot 主界面",
        "section": "详细结果预览",
        "description": "无需离开当前页面，可查看现金流、异常、行动项和报告预览。",
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
        "title": "Multi-Agent 对话报告",
        "download_label": "下载本轮报告",
    }


def build_answer_presentation(turn_result: dict | None) -> dict:
    """
    Convert a turn_result into a UI-friendly presentation dictionary.
    """
    return {
        "headline": build_headline(turn_result),
        "summary": build_summary(turn_result),
        "status_badge": build_status_badge(turn_result),
        "metric_cards": build_metric_cards(turn_result),
        "risk_cards": build_risk_cards(turn_result),
        "action_cards": build_action_cards(turn_result),
        "clarification_cards": build_clarification_cards(turn_result),
        "detail_sections": build_detail_sections(turn_result),
        "report": build_report_card(turn_result),
        "debug_available": bool(turn_result),
        "safety_note": SAFETY_NOTE,
    }
