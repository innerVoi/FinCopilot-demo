import streamlit as st


def render_status_badge(status_badge: dict | None):
    """
    Render a status badge.
    """
    status_badge = status_badge or {}
    label = status_badge.get("label", "状态")
    value = status_badge.get("value", "unknown")
    status_type = status_badge.get("type", "info")
    message = f"{label}: {value}"
    if status_type == "danger":
        st.error(message)
    elif status_type == "warning":
        st.warning(message)
    elif status_type == "success":
        st.success(message)
    else:
        st.info(message)


def render_metric_cards(metric_cards: list[dict] | None):
    """
    Render key metric cards.
    """
    cards = list(metric_cards or [])
    if not cards:
        st.info("暂无关键指标。")
        return
    columns = st.columns(min(len(cards), 4))
    for index, card in enumerate(cards):
        column = columns[index % len(columns)]
        column.metric(
            label=str(card.get("label", "")),
            value=card.get("value", ""),
            help=card.get("help"),
        )


def _render_message_by_type(message_type: str, text: str):
    if message_type == "danger":
        st.error(text)
    elif message_type == "warning":
        st.warning(text)
    else:
        st.info(text)


def render_risk_cards(risk_cards: list[dict] | None):
    """
    Render risk cards.
    """
    cards = list(risk_cards or [])
    st.subheader("主要风险")
    if not cards:
        st.info("本轮没有生成明确风险提醒。")
        return
    for card in cards:
        title = card.get("title", "风险提醒")
        description = card.get("description", "")
        source = card.get("source", "")
        _render_message_by_type(card.get("type", "info"), f"**{title}**\n\n{description}\n\n来源：{source}")


def render_action_cards(action_cards: list[dict] | None):
    """
    Render suggested action cards.
    """
    cards = list(action_cards or [])
    st.subheader("建议行动")
    if not cards:
        st.info("本轮没有生成新的建议行动。")
        return
    for card in cards:
        with st.container(border=True):
            st.markdown(f"**{card.get('title', '')}**")
            st.caption(
                f"优先级：{card.get('priority', 'medium')} | "
                f"建议截止：{card.get('deadline', '')} | "
                f"状态：{card.get('status', 'pending')}"
            )
            description = card.get("description", "")
            if description:
                st.markdown(description)


def render_clarification_cards(clarification_cards: list[dict] | None):
    """
    Render clarification cards.
    """
    cards = list(clarification_cards or [])
    st.subheader("仍需补充的信息")
    if not cards:
        st.info("本轮没有必须补充的信息。")
        return
    for card in cards:
        st.warning(f"**{card.get('question', '')}**\n\n{card.get('why_needed', '')}")


def render_detail_sections(detail_sections: list[dict] | None):
    """
    Render detail-entry cards.
    """
    sections = list(detail_sections or [])
    st.subheader("查看详情")
    if not sections:
        st.info("暂无详情入口。")
        return
    for section in sections:
        st.markdown(
            f"- **{section.get('label', '')}**："
            f"{section.get('target_page', '')} / {section.get('section', '')}。"
            f"{section.get('description', '')}"
        )


def render_report_card(report: dict | None, report_markdown: str | None = None):
    """
    Render report entry and download button.
    """
    report = report or {}
    st.subheader("报告")
    if not report.get("available"):
        st.info("本轮暂未生成可下载报告。")
        return
    st.success(report.get("title", "Multi-Agent 对话报告"))
    st.download_button(
        label=report.get("download_label", "下载本轮报告"),
        data=(report_markdown or "").encode("utf-8"),
        file_name="fincopilot_multi_agent_report.md",
        mime="text/markdown",
        key="result_cards_report_download",
    )


def render_answer_presentation(presentation: dict | None, turn_result: dict | None = None):
    """
    Render the complete answer presentation.
    """
    presentation = presentation or {}
    turn_result = turn_result or {}

    st.subheader(presentation.get("headline", "FinCopilot 已完成本轮分析"))
    summary = presentation.get("summary", "")
    if summary:
        st.markdown(summary)

    render_status_badge(presentation.get("status_badge", {}))
    render_metric_cards(presentation.get("metric_cards", []))
    render_risk_cards(presentation.get("risk_cards", []))
    render_action_cards(presentation.get("action_cards", []))
    render_clarification_cards(presentation.get("clarification_cards", []))
    render_detail_sections(presentation.get("detail_sections", []))
    st.caption("你可以继续在下方展开“详细结果预览”，也可以进入详情页查看完整表格、历史记录和下载归档。")
    render_report_card(presentation.get("report", {}), report_markdown=turn_result.get("report_markdown", ""))

    with st.expander("查看完整文字回复"):
        st.markdown(turn_result.get("assistant_reply", "") or "暂无完整文字回复。")

    errors = turn_result.get("errors", [])
    if errors:
        with st.expander("查看本轮 Agent 诊断信息"):
            for error in errors:
                st.markdown(f"- {error}")
            st.caption(
                "api_status 只代表本地配置允许尝试真实 Agent；如果真实请求失败、模型不可用或输出无法解析，系统会自动 fallback。"
            )

    with st.expander("高级详情"):
        tab_manager, tab_tools, tab_specialists, tab_trace, tab_safety = st.tabs(
            ["Manager Plan", "Tool Results", "Specialist Outputs", "Trace", "Safety"]
        )
        with tab_manager:
            st.json(turn_result.get("manager_plan", {}))
        with tab_tools:
            st.json(turn_result.get("tool_results", []))
        with tab_specialists:
            st.json(turn_result.get("specialist_outputs", {}))
        with tab_trace:
            st.json(turn_result.get("trace", {}))
        with tab_safety:
            st.json(turn_result.get("safety_result", {}))

    st.caption(presentation.get("safety_note", ""))
