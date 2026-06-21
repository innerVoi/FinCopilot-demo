SAFETY_NOTE = "本预览仅用于财务整理、风险提醒和教育性支持，不构成投资、税务、法律、债务处置或专业财务建议；系统不会认定欺诈，也不会执行付款或转账。"


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


def _as_dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _clip_text(value, max_length: int = 1000) -> str:
    text = str(value or "").strip()
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip() + "..."


def _merge_dicts(*items: dict | None) -> dict:
    merged = {}
    for item in items:
        if isinstance(item, dict):
            merged.update({key: value for key, value in item.items() if value not in [None, ""]})
    return merged


def find_tool_result(tool_results: list[dict] | None, tool_name: str) -> dict | None:
    """
    Find a named tool result from tool_results.
    """
    for result in ensure_list(tool_results):
        if isinstance(result, dict) and result.get("tool_name") == tool_name:
            return result
    return None


def get_specialist_result(specialist_outputs: dict | None, agent_name: str) -> dict:
    """
    Return one specialist result, accepting wrapped and direct payloads.
    """
    payload = safe_get(specialist_outputs, agent_name, {})
    if not isinstance(payload, dict):
        return {}
    result = payload.get("result")
    if isinstance(result, dict):
        return result
    return payload


def _get_manager_plan(turn_result: dict | None) -> dict:
    turn_result = _as_dict(turn_result)
    manager_plan = _as_dict(turn_result.get("manager_plan"))
    if manager_plan:
        return manager_plan
    return _as_dict(_as_dict(turn_result.get("manager_result")).get("manager_plan"))


def _tool_payload(turn_result: dict | None, tool_name: str) -> dict:
    tool_result = find_tool_result(safe_get(turn_result, "tool_results", []), tool_name)
    return _as_dict(safe_get(tool_result, "result", {}))


def build_data_overview(agent_context_summary: dict | None) -> dict:
    """
    Build a compact data overview preview.
    """
    snapshot = _as_dict(safe_get(agent_context_summary, "business_snapshot", {}))
    availability = _as_dict(safe_get(agent_context_summary, "data_availability", {}))
    date_min = snapshot.get("date_min") or ""
    date_max = snapshot.get("date_max") or ""
    date_range = f"{date_min} 至 {date_max}" if date_min or date_max else ""
    missing_items = ensure_list(availability.get("missing_items"))
    notes = []
    if missing_items:
        notes.append("部分数据未上传或不可用，预览仅基于当前可用摘要。")
    return {
        "transaction_count": snapshot.get("transaction_count", 0),
        "invoice_count": snapshot.get("invoice_count", 0),
        "goal_count": snapshot.get("goal_count", 0),
        "date_range": date_range,
        "missing_items": missing_items,
        "data_quality_notes": notes,
    }


def build_cashflow_preview(turn_result: dict | None, agent_context_summary: dict | None = None) -> dict:
    """
    Build cashflow preview from context, tool results and specialist output.
    """
    context_summary = _as_dict(safe_get(agent_context_summary, "cashflow_summary", {}))
    tool_summary = _tool_payload(turn_result, "get_cashflow_summary")
    agent_summary = get_specialist_result(safe_get(turn_result, "specialist_outputs", {}), "cashflow_agent")
    merged = _merge_dicts(context_summary, tool_summary)
    return {
        "risk_level": merged.get("adjusted_risk_level") or merged.get("risk_level", "unknown"),
        "projected_balance_30d": merged.get("adjusted_projected_balance_30d", merged.get("projected_balance_30d")),
        "cash_buffer_days": merged.get("cash_buffer_days"),
        "risk_reasons": ensure_list(merged.get("adjustment_reasons")) or ensure_list(merged.get("risk_reasons")),
        "recommended_actions": ensure_list(merged.get("recommended_actions")) or ensure_list(agent_summary.get("recommended_actions")),
        "agent_summary": _clip_text(agent_summary.get("summary", ""), 500),
    }


def build_invoice_preview(turn_result: dict | None, agent_context_summary: dict | None = None) -> dict:
    """
    Build invoice preview from context and tool results.
    """
    context_summary = _as_dict(safe_get(agent_context_summary, "invoice_summary", {}))
    tool_summary = _tool_payload(turn_result, "get_invoice_summary")
    merged = _merge_dicts(context_summary, tool_summary)
    overdue_count = merged.get("overdue_invoice_count", 0)
    notes = []
    if overdue_count:
        notes.append("存在逾期发票，请结合原始发票和合同核查。")
    return {
        "total_invoice_amount": merged.get("total_invoice_amount", 0.0),
        "unpaid_invoice_amount": merged.get("unpaid_invoice_amount", 0.0),
        "overdue_invoice_amount": merged.get("overdue_invoice_amount", 0.0),
        "due_7d_amount": merged.get("due_7d_amount", 0.0),
        "due_30d_amount": merged.get("due_30d_amount", 0.0),
        "overdue_invoice_count": overdue_count,
        "notes": notes,
    }


def build_anomaly_preview(turn_result: dict | None, agent_context_summary: dict | None = None) -> dict:
    """
    Build anomaly preview from context, tool results and specialist output.
    """
    context_summary = _as_dict(safe_get(agent_context_summary, "anomaly_summary", {}))
    tool_summary = _tool_payload(turn_result, "get_anomaly_summary")
    agent_summary = get_specialist_result(safe_get(turn_result, "specialist_outputs", {}), "anomaly_agent")
    merged = _merge_dicts(context_summary, tool_summary)
    return {
        "rule_anomaly_count": merged.get("rule_anomaly_count", 0),
        "model_high_risk_count": merged.get("model_high_risk_count", 0),
        "model_medium_risk_count": merged.get("model_medium_risk_count", 0),
        "top_rule_anomalies": ensure_list(merged.get("top_rule_anomalies"))[:5],
        "top_model_anomalies": ensure_list(merged.get("top_model_anomalies"))[:5],
        "agent_summary": _clip_text(agent_summary.get("summary", ""), 500),
        "risk_notes": ensure_list(agent_summary.get("risks")),
    }


def build_goal_preview(turn_result: dict | None, agent_context_summary: dict | None = None) -> dict:
    """
    Build financial goal preview.
    """
    context_summary = _as_dict(safe_get(agent_context_summary, "goal_summary", {}))
    tool_summary = _tool_payload(turn_result, "get_goal_summary")
    merged = _merge_dicts(context_summary, tool_summary)
    return {
        "goal_count": merged.get("goal_count", 0),
        "high_risk_goal_count": merged.get("high_risk_goal_count", 0),
        "medium_risk_goal_count": merged.get("medium_risk_goal_count", 0),
        "overall_progress_percent": merged.get("overall_progress_percent"),
        "top_risk_goals": ensure_list(merged.get("top_risk_goals"))[:5],
    }


def _normalize_action_item(item, source: str = "agent_chat") -> dict | None:
    if isinstance(item, dict):
        title = item.get("title") or item.get("action") or item.get("description") or ""
        if not title:
            return None
        return {
            "action_id": item.get("action_id") or item.get("id") or "",
            "title": title,
            "priority": item.get("priority", "medium"),
            "status": item.get("status", "pending"),
            "suggested_deadline": item.get("suggested_deadline", "3 天内"),
            "source": item.get("source", source),
        }
    title = str(item or "").strip()
    if not title:
        return None
    return {
        "action_id": "",
        "title": title,
        "priority": "medium",
        "status": "pending",
        "suggested_deadline": "3 天内",
        "source": source,
    }


def build_action_preview(turn_result: dict | None, agent_context_summary: dict | None = None) -> dict:
    """
    Build action item preview.
    """
    turn_result = _as_dict(turn_result)
    raw_items = ensure_list(turn_result.get("chat_action_items"))
    source = "agent_chat"
    if not raw_items:
        raw_items = ensure_list(turn_result.get("suggested_actions"))
        source = "suggested_actions"
    if not raw_items:
        raw_items = ensure_list(_as_dict(safe_get(agent_context_summary, "action_summary", {})).get("top_actions"))
        source = "action_center"

    items = [item for item in (_normalize_action_item(raw_item, source=source) for raw_item in raw_items) if item]
    priority_counts = {"high": 0, "medium": 0, "low": 0}
    for item in items:
        priority = str(item.get("priority", "medium")).lower()
        if priority in priority_counts:
            priority_counts[priority] += 1
    return {
        "total": len(items),
        "high": priority_counts["high"],
        "medium": priority_counts["medium"],
        "low": priority_counts["low"],
        "items": items[:5],
    }


def build_report_preview(turn_result: dict | None) -> dict:
    """
    Build report preview and metadata.
    """
    report = str(safe_get(turn_result, "report_markdown", "") or "")
    trace_markdown = str(safe_get(turn_result, "trace_markdown", "") or "")
    return {
        "has_report": bool(report.strip()),
        "report_title": "FinCopilot Multi-Agent 对话报告",
        "report_preview": _clip_text(report, 1000),
        "report_length": len(report),
        "has_trace_markdown": bool(trace_markdown.strip()),
    }


def build_trace_preview(turn_result: dict | None) -> dict:
    """
    Build compact trace preview.
    """
    turn_result = _as_dict(turn_result)
    trace = _as_dict(turn_result.get("trace"))
    tool_trace = _as_dict(turn_result.get("tool_trace"))
    manager_plan = _get_manager_plan(turn_result)
    safety_result = _as_dict(turn_result.get("safety_result"))
    specialist_outputs = _as_dict(turn_result.get("specialist_outputs"))
    return {
        "mode": trace.get("mode") or turn_result.get("mode", "fallback"),
        "intent": manager_plan.get("intent", "unknown"),
        "tools_called": ensure_list(tool_trace.get("tools_called")) or [
            item.get("tool_name") for item in ensure_list(turn_result.get("tool_results")) if isinstance(item, dict)
        ],
        "agents_called": list(specialist_outputs.keys()),
        "tool_success": tool_trace.get("success", 0),
        "tool_failed": tool_trace.get("failed", 0),
        "safety_safe": safety_result.get("safe", safety_result.get("is_safe", True)),
        "risks": ensure_list(safety_result.get("risks")),
    }


def build_tool_preview(turn_result: dict | None) -> dict:
    """
    Build tool result preview.
    """
    items = []
    success = 0
    failed = 0
    for result in ensure_list(safe_get(turn_result, "tool_results", [])):
        if not isinstance(result, dict):
            continue
        status = result.get("status", "unknown")
        if status == "success":
            success += 1
        elif status == "failed":
            failed += 1
        summary = "返回可用摘要" if status == "success" else result.get("error", "工具未返回可用摘要")
        items.append(
            {
                "tool_name": result.get("tool_name", ""),
                "status": status,
                "summary": summary,
            }
        )
    return {
        "total": len(items),
        "success": success,
        "failed": failed,
        "items": items,
    }


def build_agent_preview(turn_result: dict | None) -> dict:
    """
    Build Manager and Specialist execution preview.
    """
    manager_plan = _get_manager_plan(turn_result)
    specialist_outputs = _as_dict(safe_get(turn_result, "specialist_outputs", {}))
    specialist_summaries = []
    for agent_name, payload in specialist_outputs.items():
        if not isinstance(payload, dict):
            continue
        result = get_specialist_result(specialist_outputs, agent_name)
        specialist_summaries.append(
            {
                "agent_name": agent_name,
                "mode": payload.get("mode", safe_get(turn_result, "mode", "fallback")),
                "summary": _clip_text(result.get("summary", ""), 300),
            }
        )
    return {
        "manager_intent": manager_plan.get("intent", "unknown"),
        "selected_agents": ensure_list(manager_plan.get("selected_agents")),
        "specialist_summaries": specialist_summaries,
    }


def build_detail_navigation(turn_result: dict | None) -> list[dict]:
    """
    Build entry hints for full detail pages.
    """
    intent = _get_manager_plan(turn_result).get("intent", "unknown")
    entries = [
        {
            "label": "在当前页面展开详细预览",
            "page": "Copilot 主界面",
            "section": "详细结果预览",
            "reason": "无需离开当前页面，可查看现金流、异常、行动项和报告预览。",
        }
    ]
    if intent in {"cashflow_check", "invoice_or_payment_review"}:
        entries.append(
            {
                "label": "查看完整现金流分析",
                "page": "分析详情",
                "section": "发票与现金流",
                "reason": "查看完整现金流指标、发票压力和明细表。",
            }
        )
    elif intent == "expense_anomaly_review":
        entries.append(
            {
                "label": "查看完整异常支出分析",
                "page": "分析详情",
                "section": "异常支出",
                "reason": "查看规则异常、模型异常和明细证据。",
            }
        )
    elif intent in {"goal_or_budget_planning", "promotion_or_purchase_planning"}:
        entries.append(
            {
                "label": "查看完整目标分析",
                "page": "分析详情",
                "section": "财务目标",
                "reason": "查看目标进度、风险目标和预算影响。",
            }
        )
    else:
        entries.append(
            {
                "label": "查看完整分析详情",
                "page": "分析详情",
                "section": "综合分析",
                "reason": "查看预算、现金流、异常和目标的完整结果。",
            }
        )
    entries.append(
        {
            "label": "查看行动与报告",
            "page": "行动与报告",
            "section": "行动项 / 报告",
            "reason": "跟踪行动项状态并下载归档报告。",
        }
    )
    return entries


def build_detail_preview(turn_result: dict | None, agent_context_summary: dict | None = None) -> dict:
    """
    Build the full inline detail preview payload.
    """
    return {
        "data_overview": build_data_overview(agent_context_summary),
        "cashflow_preview": build_cashflow_preview(turn_result, agent_context_summary),
        "invoice_preview": build_invoice_preview(turn_result, agent_context_summary),
        "anomaly_preview": build_anomaly_preview(turn_result, agent_context_summary),
        "goal_preview": build_goal_preview(turn_result, agent_context_summary),
        "action_preview": build_action_preview(turn_result, agent_context_summary),
        "report_preview": build_report_preview(turn_result),
        "trace_preview": build_trace_preview(turn_result),
        "tool_preview": build_tool_preview(turn_result),
        "agent_preview": build_agent_preview(turn_result),
        "detail_navigation": build_detail_navigation(turn_result),
        "safety_note": SAFETY_NOTE,
    }
