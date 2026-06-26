import streamlit as st


def _format_value(value, empty="Not available"):
    if value in [None, ""]:
        return empty
    return value


def _format_money(value):
    if value is None:
        return "Not available"
    try:
        return f"{float(value):,.2f}"
    except (TypeError, ValueError):
        return str(value)


def _metric_grid(items: list[tuple[str, object]], max_columns: int = 4):
    if not items:
        return
    columns = st.columns(min(len(items), max_columns))
    for index, (label, value) in enumerate(items):
        columns[index % len(columns)].metric(label=label, value=_format_value(value))


def _render_table(items: list[dict] | None, empty_message: str):
    rows = [item for item in (items or []) if isinstance(item, dict)]
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info(empty_message)


def render_data_overview_preview(data_overview: dict | None):
    """
    Render data overview preview.
    """
    data_overview = data_overview or {}
    _metric_grid(
        [
            ("Transactions", data_overview.get("transaction_count", 0)),
            ("Invoices", data_overview.get("invoice_count", 0)),
            ("Goals", data_overview.get("goal_count", 0)),
            ("Missing Items", len(data_overview.get("missing_items") or [])),
        ]
    )
    if data_overview.get("date_range"):
        st.caption(f"Data range: {data_overview.get('date_range')}")
    missing_items = data_overview.get("missing_items") or []
    if missing_items:
        st.info("Still missing: " + ", ".join(str(item) for item in missing_items[:8]))
    for note in data_overview.get("data_quality_notes") or []:
        st.caption(str(note))


def render_cashflow_invoice_preview(cashflow_preview: dict | None, invoice_preview: dict | None):
    """
    Render cashflow and invoice preview.
    """
    cashflow_preview = cashflow_preview or {}
    invoice_preview = invoice_preview or {}
    if not cashflow_preview and not invoice_preview:
        st.info("No cash-flow summary is available yet.")
        return
    _metric_grid(
        [
            ("Cash-Flow Risk", cashflow_preview.get("risk_level", "unknown")),
            ("30-Day Projected Balance", _format_money(cashflow_preview.get("projected_balance_30d"))),
            ("Cash Buffer Days", _format_value(cashflow_preview.get("cash_buffer_days"))),
            ("Unpaid Invoice Amount", _format_money(invoice_preview.get("unpaid_invoice_amount", 0.0))),
            ("Overdue Invoice Amount", _format_money(invoice_preview.get("overdue_invoice_amount", 0.0))),
            ("Due in 7 Days", _format_money(invoice_preview.get("due_7d_amount", 0.0))),
            ("Due in 30 Days", _format_money(invoice_preview.get("due_30d_amount", 0.0))),
            ("Overdue Invoice Count", invoice_preview.get("overdue_invoice_count", 0)),
        ]
    )
    risk_reasons = cashflow_preview.get("risk_reasons") or []
    if risk_reasons:
        st.markdown("**Cash-Flow Risk Reasons**")
        for reason in risk_reasons[:5]:
            st.markdown(f"- {reason}")
    actions = cashflow_preview.get("recommended_actions") or []
    if actions:
        st.markdown("**Recommended Actions**")
        for action in actions[:5]:
            st.markdown(f"- {action}")
    if cashflow_preview.get("agent_summary"):
        st.caption(cashflow_preview.get("agent_summary"))


def render_anomaly_preview(anomaly_preview: dict | None):
    """
    Render anomaly preview.
    """
    anomaly_preview = anomaly_preview or {}
    _metric_grid(
        [
            ("Rule Anomalies", anomaly_preview.get("rule_anomaly_count", 0)),
            ("Model High Risk", anomaly_preview.get("model_high_risk_count", 0)),
            ("Model Medium Risk", anomaly_preview.get("model_medium_risk_count", 0)),
        ],
        max_columns=3,
    )
    if not any(
        [
            anomaly_preview.get("rule_anomaly_count"),
            anomaly_preview.get("model_high_risk_count"),
            anomaly_preview.get("model_medium_risk_count"),
            anomaly_preview.get("top_rule_anomalies"),
            anomaly_preview.get("top_model_anomalies"),
        ]
    ):
        st.info("No anomaly summary is available yet.")
    st.markdown("**Top Rule Anomalies**")
    _render_table(anomaly_preview.get("top_rule_anomalies"), "No rule anomaly details yet.")
    st.markdown("**Top Model Anomalies**")
    _render_table(anomaly_preview.get("top_model_anomalies"), "No model anomaly details yet.")
    st.caption("If an anomaly is actually normal business spending, tell FinCopilot in the feedback area so it can be stored as business memory.")
    if anomaly_preview.get("agent_summary"):
        st.caption(anomaly_preview.get("agent_summary"))
    for note in anomaly_preview.get("risk_notes") or []:
        st.warning(str(note))


def render_goal_preview(goal_preview: dict | None):
    """
    Render financial goal preview.
    """
    goal_preview = goal_preview or {}
    _metric_grid(
        [
            ("Goals", goal_preview.get("goal_count", 0)),
            ("High-Risk Goals", goal_preview.get("high_risk_goal_count", 0)),
            ("Medium-Risk Goals", goal_preview.get("medium_risk_goal_count", 0)),
            ("Overall Progress", _format_value(goal_preview.get("overall_progress_percent"))),
        ]
    )
    st.markdown("**Top Risk Goals**")
    _render_table(goal_preview.get("top_risk_goals"), "No goals summary yet.")


def render_action_preview(action_preview: dict | None):
    """
    Render action item preview.
    """
    action_preview = action_preview or {}
    _metric_grid(
        [
            ("Total Action Items", action_preview.get("total", 0)),
            ("High Priority", action_preview.get("high", 0)),
            ("Medium Priority", action_preview.get("medium", 0)),
            ("Low Priority", action_preview.get("low", 0)),
            ("Pending", action_preview.get("pending", 0)),
            ("Handled", action_preview.get("handled", 0)),
        ]
    )
    _render_table(action_preview.get("items"), "No action item details for this turn yet.")


def render_memory_preview(memory_preview: dict | None):
    """
    Render memory usage preview.
    """
    memory_preview = memory_preview or {}
    memory_count = int(memory_preview.get("memory_count") or 0)
    if not memory_count:
        st.info("This analysis mainly uses the currently uploaded data. No historical business memory is available yet.")
        return
    st.success(f"This analysis referenced {memory_count} historical business memory records.")
    for key, label in [
        ("known_normal_payments", "Known Normal Payments"),
        ("known_suppliers", "Long-Term Suppliers"),
        ("cash_context", "Cash Context"),
        ("expected_receivables", "Expected Receivables"),
        ("recurring_expenses", "Recurring Expenses"),
        ("business_rules", "Business Rules"),
        ("user_preferences", "User Preferences"),
        ("known_risks", "Known Risks"),
    ]:
        items = list(memory_preview.get(key) or [])
        if not items:
            continue
        st.markdown(f"**{label}**")
        for item in items[:5]:
            st.markdown(f"- {item}")


def render_report_preview(report_preview: dict | None, turn_result: dict | None = None):
    """
    Render report preview and download entry.
    """
    report_preview = report_preview or {}
    turn_result = turn_result or {}
    if not report_preview.get("has_report"):
        st.info("No report preview was generated for this turn yet.")
        return
    st.success("Report generated")
    st.markdown("**Report Title**")
    st.write(report_preview.get("report_title", "FinCopilot Multi-Agent Conversation Report"))
    st.markdown("**Report Summary**")
    st.markdown(report_preview.get("report_summary") or "No summary yet.")
    st.metric("Report Length", report_preview.get("report_length", 0))
    with st.expander("View Report Preview", expanded=False):
        st.markdown(report_preview.get("report_preview") or "No report preview yet.")
    st.download_button(
        label="Download This Report",
        data=(turn_result.get("report_markdown", "") or "").encode("utf-8"),
        file_name="fincopilot_multi_agent_report.md",
        mime="text/markdown",
        key="inline_detail_report_download",
    )
    if report_preview.get("has_trace_markdown"):
        st.caption("A Multi-Agent Trace was also generated for this turn and can be viewed in Advanced Details.")


def render_agent_execution_preview(trace_preview: dict | None, tool_preview: dict | None, agent_preview: dict | None):
    """
    Render Agent execution preview.
    """
    trace_preview = trace_preview or {}
    tool_preview = tool_preview or {}
    agent_preview = agent_preview or {}
    _metric_grid(
        [
            ("Mode", trace_preview.get("mode", "fallback")),
            ("Intent", trace_preview.get("intent", "unknown")),
            ("Tools Succeeded", trace_preview.get("tool_success", tool_preview.get("success", 0))),
            ("Tools Failed", trace_preview.get("tool_failed", tool_preview.get("failed", 0))),
        ]
    )
    tools_called = trace_preview.get("tools_called") or []
    agents_called = trace_preview.get("agents_called") or agent_preview.get("selected_agents") or []
    st.markdown("**Tools Called**")
    st.markdown(", ".join(str(item) for item in tools_called) if tools_called else "No tool calls yet.")
    st.markdown("**Specialist Agents**")
    st.markdown(", ".join(str(item) for item in agents_called) if agents_called else "No Specialist Agent calls yet.")
    safety_text = "Passed" if trace_preview.get("safety_safe", True) else "Needs review"
    st.caption(f"Safety check: {safety_text}")
    for summary in agent_preview.get("specialist_summaries") or []:
        with st.container(border=True):
            st.markdown(f"**{summary.get('agent_name', '')}**")
            st.caption(f"Mode: {summary.get('mode', 'fallback')}")
            if summary.get("summary"):
                st.markdown(summary.get("summary"))
    with st.expander("Advanced Technical Details", expanded=False):
        st.json(
            {
                "trace_preview": trace_preview,
                "tool_preview": tool_preview,
                "agent_preview": agent_preview,
            }
        )


def render_detail_navigation(detail_navigation: list[dict] | None):
    """
    Render detail navigation hints.
    """
    entries = [entry for entry in (detail_navigation or []) if isinstance(entry, dict)]
    if not entries:
        st.info("No detail-page navigation hints yet.")
        return
    for entry in entries:
        st.markdown(
            f"- **{entry.get('label', '')}**: "
            f"{entry.get('page', '')} / {entry.get('section', '')}. "
            f"{entry.get('reason', '')}"
        )


def render_inline_detail_preview(detail_preview: dict | None, turn_result: dict | None = None):
    """
    Render the full inline detail preview on the Copilot main page.
    """
    detail_preview = detail_preview or {}
    st.subheader("Detailed Result Preview")
    st.caption("These sections come from the current turn's analysis results and data summary. They are collapsed by default.")
    with st.expander("Data Overview", expanded=False):
        render_data_overview_preview(detail_preview.get("data_overview", {}))
    with st.expander("Cash Flow & Invoices", expanded=False):
        render_cashflow_invoice_preview(
            detail_preview.get("cashflow_preview", {}),
            detail_preview.get("invoice_preview", {}),
        )
    with st.expander("Suspicious Expenses", expanded=False):
        render_anomaly_preview(detail_preview.get("anomaly_preview", {}))
    with st.expander("Goals", expanded=False):
        render_goal_preview(detail_preview.get("goal_preview", {}))
    with st.expander("Action Items", expanded=False):
        render_action_preview(detail_preview.get("action_preview", {}))
    with st.expander("Business Memory Used This Turn", expanded=False):
        render_memory_preview(detail_preview.get("memory_preview", {}))
    with st.expander("Report Preview", expanded=False):
        render_report_preview(detail_preview.get("report_preview", {}), turn_result=turn_result)
    with st.expander("Agent Execution Summary", expanded=False):
        render_agent_execution_preview(
            detail_preview.get("trace_preview", {}),
            detail_preview.get("tool_preview", {}),
            detail_preview.get("agent_preview", {}),
        )
    with st.expander("Detail Page Shortcuts", expanded=False):
        render_detail_navigation(detail_preview.get("detail_navigation", []))
    st.caption(detail_preview.get("safety_note", ""))
