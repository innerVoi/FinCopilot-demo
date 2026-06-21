import streamlit as st


def _format_value(value, empty="暂无"):
    if value in [None, ""]:
        return empty
    return value


def _format_money(value):
    if value is None:
        return "暂无"
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
            ("交易数", data_overview.get("transaction_count", 0)),
            ("发票数", data_overview.get("invoice_count", 0)),
            ("目标数", data_overview.get("goal_count", 0)),
            ("缺失项", len(data_overview.get("missing_items") or [])),
        ]
    )
    if data_overview.get("date_range"):
        st.caption(f"数据区间：{data_overview.get('date_range')}")
    missing_items = data_overview.get("missing_items") or []
    if missing_items:
        st.info("当前仍缺少：" + "、".join(str(item) for item in missing_items[:8]))
    for note in data_overview.get("data_quality_notes") or []:
        st.caption(str(note))


def render_cashflow_invoice_preview(cashflow_preview: dict | None, invoice_preview: dict | None):
    """
    Render cashflow and invoice preview.
    """
    cashflow_preview = cashflow_preview or {}
    invoice_preview = invoice_preview or {}
    if not cashflow_preview and not invoice_preview:
        st.info("暂无可用现金流摘要。")
        return
    _metric_grid(
        [
            ("现金流风险", cashflow_preview.get("risk_level", "unknown")),
            ("30 天预计余额", _format_money(cashflow_preview.get("projected_balance_30d"))),
            ("现金缓冲天数", _format_value(cashflow_preview.get("cash_buffer_days"))),
            ("未付发票金额", _format_money(invoice_preview.get("unpaid_invoice_amount", 0.0))),
            ("逾期发票金额", _format_money(invoice_preview.get("overdue_invoice_amount", 0.0))),
            ("7 天内到期", _format_money(invoice_preview.get("due_7d_amount", 0.0))),
            ("30 天内到期", _format_money(invoice_preview.get("due_30d_amount", 0.0))),
            ("逾期发票数", invoice_preview.get("overdue_invoice_count", 0)),
        ]
    )
    risk_reasons = cashflow_preview.get("risk_reasons") or []
    if risk_reasons:
        st.markdown("**现金流风险原因**")
        for reason in risk_reasons[:5]:
            st.markdown(f"- {reason}")
    actions = cashflow_preview.get("recommended_actions") or []
    if actions:
        st.markdown("**建议动作**")
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
            ("规则异常数", anomaly_preview.get("rule_anomaly_count", 0)),
            ("模型高风险数", anomaly_preview.get("model_high_risk_count", 0)),
            ("模型中风险数", anomaly_preview.get("model_medium_risk_count", 0)),
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
        st.info("暂无可用异常摘要。")
    st.markdown("**Top 规则异常**")
    _render_table(anomaly_preview.get("top_rule_anomalies"), "暂无规则异常明细。")
    st.markdown("**Top 模型异常**")
    _render_table(anomaly_preview.get("top_model_anomalies"), "暂无模型异常明细。")
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
            ("目标数", goal_preview.get("goal_count", 0)),
            ("高风险目标", goal_preview.get("high_risk_goal_count", 0)),
            ("中风险目标", goal_preview.get("medium_risk_goal_count", 0)),
            ("整体完成率", _format_value(goal_preview.get("overall_progress_percent"))),
        ]
    )
    st.markdown("**Top 风险目标**")
    _render_table(goal_preview.get("top_risk_goals"), "暂无财务目标摘要。")


def render_action_preview(action_preview: dict | None):
    """
    Render action item preview.
    """
    action_preview = action_preview or {}
    _metric_grid(
        [
            ("行动项总数", action_preview.get("total", 0)),
            ("高优先级", action_preview.get("high", 0)),
            ("中优先级", action_preview.get("medium", 0)),
            ("低优先级", action_preview.get("low", 0)),
        ]
    )
    _render_table(action_preview.get("items"), "本轮暂无行动项明细。")


def render_report_preview(report_preview: dict | None, turn_result: dict | None = None):
    """
    Render report preview and download entry.
    """
    report_preview = report_preview or {}
    turn_result = turn_result or {}
    if not report_preview.get("has_report"):
        st.info("本轮暂未生成可预览报告。")
        return
    st.success(report_preview.get("report_title", "FinCopilot Multi-Agent 对话报告"))
    st.metric("报告长度", report_preview.get("report_length", 0))
    with st.expander("查看报告前 1000 字", expanded=False):
        st.markdown(report_preview.get("report_preview") or "暂无报告预览。")
    st.download_button(
        label="下载本轮报告",
        data=(turn_result.get("report_markdown", "") or "").encode("utf-8"),
        file_name="fincopilot_multi_agent_report.md",
        mime="text/markdown",
        key="inline_detail_report_download",
    )
    if report_preview.get("has_trace_markdown"):
        st.caption("本轮同时生成了 Multi-Agent Trace，可在高级详情中查看。")


def render_agent_execution_preview(trace_preview: dict | None, tool_preview: dict | None, agent_preview: dict | None):
    """
    Render Agent execution preview.
    """
    trace_preview = trace_preview or {}
    tool_preview = tool_preview or {}
    agent_preview = agent_preview or {}
    _metric_grid(
        [
            ("模式", trace_preview.get("mode", "fallback")),
            ("意图", trace_preview.get("intent", "unknown")),
            ("工具成功", trace_preview.get("tool_success", tool_preview.get("success", 0))),
            ("工具失败", trace_preview.get("tool_failed", tool_preview.get("failed", 0))),
        ]
    )
    tools_called = trace_preview.get("tools_called") or []
    agents_called = trace_preview.get("agents_called") or agent_preview.get("selected_agents") or []
    st.markdown("**调用工具**")
    st.markdown("、".join(str(item) for item in tools_called) if tools_called else "暂无工具调用。")
    st.markdown("**Specialist Agents**")
    st.markdown("、".join(str(item) for item in agents_called) if agents_called else "暂无 Specialist Agent 调用。")
    safety_text = "通过" if trace_preview.get("safety_safe", True) else "需要复核"
    st.caption(f"安全检查：{safety_text}")
    for summary in agent_preview.get("specialist_summaries") or []:
        with st.container(border=True):
            st.markdown(f"**{summary.get('agent_name', '')}**")
            st.caption(f"模式：{summary.get('mode', 'fallback')}")
            if summary.get("summary"):
                st.markdown(summary.get("summary"))
    with st.expander("高级技术详情", expanded=False):
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
        st.info("暂无详情页入口说明。")
        return
    for entry in entries:
        st.markdown(
            f"- **{entry.get('label', '')}**："
            f"{entry.get('page', '')} / {entry.get('section', '')}。"
            f"{entry.get('reason', '')}"
        )


def render_inline_detail_preview(detail_preview: dict | None, turn_result: dict | None = None):
    """
    Render the full inline detail preview on the Copilot main page.
    """
    detail_preview = detail_preview or {}
    st.subheader("详细结果预览")
    st.caption("以下内容来自本轮已有分析结果和数据摘要，默认折叠展示。")
    with st.expander("数据概览", expanded=False):
        render_data_overview_preview(detail_preview.get("data_overview", {}))
    with st.expander("现金流与发票", expanded=False):
        render_cashflow_invoice_preview(
            detail_preview.get("cashflow_preview", {}),
            detail_preview.get("invoice_preview", {}),
        )
    with st.expander("异常支出", expanded=False):
        render_anomaly_preview(detail_preview.get("anomaly_preview", {}))
    with st.expander("财务目标", expanded=False):
        render_goal_preview(detail_preview.get("goal_preview", {}))
    with st.expander("行动项", expanded=False):
        render_action_preview(detail_preview.get("action_preview", {}))
    with st.expander("报告预览", expanded=False):
        render_report_preview(detail_preview.get("report_preview", {}), turn_result=turn_result)
    with st.expander("Agent 执行摘要", expanded=False):
        render_agent_execution_preview(
            detail_preview.get("trace_preview", {}),
            detail_preview.get("tool_preview", {}),
            detail_preview.get("agent_preview", {}),
        )
    with st.expander("详情页入口", expanded=False):
        render_detail_navigation(detail_preview.get("detail_navigation", []))
    st.caption(detail_preview.get("safety_note", ""))
