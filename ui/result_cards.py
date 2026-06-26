import streamlit as st


def render_status_badge(status_badge: dict | None):
    """
    Render a status badge.
    """
    status_badge = status_badge or {}
    label = status_badge.get("label", "Status")
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
        st.info("No key metrics yet.")
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
    st.subheader("Key Risks")
    if not cards:
        st.info("No explicit risk alerts were generated this turn.")
        return
    for card in cards:
        title = card.get("title", "Risk Alert")
        description = card.get("description", "")
        source = card.get("source", "")
        _render_message_by_type(card.get("type", "info"), f"**{title}**\n\n{description}\n\nSource: {source}")


def render_memory_cards(memory_cards: list[dict] | None):
    """
    Render memory cards used by this turn.
    """
    cards = list(memory_cards or [])
    st.subheader("Business Memory Used This Turn")
    if not cards:
        st.info("This analysis is mainly based on the currently uploaded data.")
        return
    for card in cards:
        with st.container(border=True):
            st.markdown(f"**{card.get('title', '')}**")
            description = card.get("description", "")
            if description:
                st.caption(description)
            items = list(card.get("items") or [])
            if items:
                for item in items[:6]:
                    st.markdown(f"- {item}")


def render_action_cards(action_cards: list[dict] | None):
    """
    Render suggested action cards.
    """
    cards = list(action_cards or [])
    st.subheader("Suggested Actions")
    if not cards:
        st.info("No new suggested actions were generated this turn.")
        return
    for card in cards:
        with st.container(border=True):
            st.markdown(f"**{card.get('title', '')}**")
            st.caption(
                f"Priority: {card.get('priority', 'medium')} | "
                f"Suggested deadline: {card.get('deadline', '')} | "
                f"Status: {card.get('status', 'pending')}"
            )
            description = card.get("description", "")
            if description:
                st.markdown(description)


def render_clarification_cards(clarification_cards: list[dict] | None):
    """
    Render clarification cards.
    """
    cards = list(clarification_cards or [])
    st.subheader("Information Still Needed")
    if not cards:
        st.info("No required follow-up information for this turn.")
        return
    for card in cards:
        st.warning(f"**{card.get('question', '')}**\n\n{card.get('why_needed', '')}")


def render_detail_sections(detail_sections: list[dict] | None):
    """
    Render detail-entry cards.
    """
    sections = list(detail_sections or [])
    st.subheader("Details")
    if not sections:
        st.info("No detail links yet.")
        return
    for section in sections:
        st.markdown(
            f"- **{section.get('label', '')}**: "
            f"{section.get('target_page', '')} / {section.get('section', '')}. "
            f"{section.get('description', '')}"
        )


def render_report_card(report: dict | None, report_markdown: str | None = None):
    """
    Render report entry and download button.
    """
    report = report or {}
    st.subheader("Reports")
    if not report.get("available"):
        st.info("No downloadable report was generated for this turn yet.")
        return
    st.success("Report generated")
    st.markdown("**Report Title**")
    st.write(report.get("title", "Multi-Agent Conversation Report"))
    summary = report.get("summary", "")
    if summary:
        st.markdown("**Report Summary**")
        st.markdown(summary)
    with st.expander("View Full Report", expanded=False):
        st.markdown(report_markdown or "No full report yet.")
    st.download_button(
        label=report.get("download_label", "Download This Report"),
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

    st.subheader(presentation.get("headline", "FinCopilot has completed this analysis"))
    summary = presentation.get("summary", "")
    if summary:
        st.markdown(summary)

    render_status_badge(presentation.get("status_badge", {}))
    render_metric_cards(presentation.get("metric_cards", []))
    render_memory_cards(presentation.get("memory_cards", []))
    render_risk_cards(presentation.get("risk_cards", []))
    render_action_cards(presentation.get("action_cards", []))
    render_clarification_cards(presentation.get("clarification_cards", []))
    render_detail_sections(presentation.get("detail_sections", []))
    st.caption("You can expand Detailed Result Preview below, or open the detail pages to review full tables, history, and downloadable archives.")
    render_report_card(presentation.get("report", {}), report_markdown=turn_result.get("report_markdown", ""))

    with st.expander("View Full Text Response"):
        st.markdown(turn_result.get("assistant_reply", "") or "No full text response yet.")

    errors = turn_result.get("errors", [])
    if errors:
        with st.expander("View Agent Diagnostics"):
            for error in errors:
                st.markdown(f"- {error}")
            st.caption(
                "api_status only means local configuration allows a Live Agent attempt. If the real request fails, the model is unavailable, or output cannot be parsed, the system falls back automatically."
            )

    with st.expander("Advanced Details"):
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
