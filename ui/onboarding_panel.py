import pandas as pd
import streamlit as st


def _has_rows(dataframe) -> bool:
    return isinstance(dataframe, pd.DataFrame) and not dataframe.empty


def _missing_data_labels(transactions_df=None, invoices_df=None, goals_df=None) -> list[str]:
    missing = []
    if not _has_rows(transactions_df):
        missing.append("Transactions")
    if not _has_rows(invoices_df):
        missing.append("Invoices")
    if not _has_rows(goals_df):
        missing.append("Goals")
    return missing


def infer_onboarding_state(
    transactions_df=None,
    invoices_df=None,
    goals_df=None,
    agent_api_status: dict | None = None,
    latest_agent_turn: dict | None = None,
) -> str:
    """
    Infer onboarding state for the Copilot main page.
    """
    if latest_agent_turn:
        return "after_first_turn"

    has_transactions = _has_rows(transactions_df)
    has_invoices = _has_rows(invoices_df)
    has_goals = _has_rows(goals_df)
    has_any_data = has_transactions or has_invoices or has_goals

    if not has_any_data:
        return "no_data"
    if agent_api_status and agent_api_status.get("mode") == "fallback":
        return "fallback_mode"
    if has_transactions and has_invoices:
        return "ready"
    return "partial_data"


def build_onboarding_messages(
    onboarding_state: str,
    transactions_df=None,
    invoices_df=None,
    goals_df=None,
    agent_api_status: dict | None = None,
) -> dict:
    """
    Build onboarding copy from state.
    """
    missing = _missing_data_labels(transactions_df, invoices_df, goals_df)
    messages = {
        "no_data": {
            "title": "Upload data, or start with sample data",
            "description": "FinCopilot can analyze cash flow, suspicious expenses, and weekly action items from transactions, invoices, and goals.",
            "primary_cta": "Use sample data",
            "secondary_cta": "View field guide",
            "tips": [
                "You can upload transactions.csv, invoices.csv, and goals.csv.",
                "If no files are uploaded, the built-in sample data lets you try the full flow quickly.",
                "Once data is ready, ask: Is cash flow safe for the next 30 days?",
            ],
        },
        "partial_data": {
            "title": "Some data is ready",
            "description": "Some tasks are available, while missing data may reduce analysis quality.",
            "primary_cta": "Run available tasks",
            "secondary_cta": "Add missing data",
            "tips": [f"Currently missing: {', '.join(missing)}."] if missing else [],
        },
        "ready": {
            "title": "Data is ready. You can start asking questions.",
            "description": "You can check future cash flow, suspicious expenses, invoice pressure, or generate this week's action plan.",
            "primary_cta": "Choose a recommended task",
            "secondary_cta": "Ask a question directly",
            "tips": ["Start with cash flow, then review suspicious expenses and this week's action items."],
        },
        "after_first_turn": {
            "title": "Analysis Complete",
            "description": "You can review action items, add missing information, or ask a more specific follow-up question.",
            "primary_cta": "Follow up",
            "secondary_cta": "Open Actions & Reports",
            "tips": ["Follow-up questions are based on the latest analysis."],
        },
        "fallback_mode": {
            "title": "Fallback Analysis Is Active",
            "description": "The live Agent API is unavailable, but local fallback rules and tools can still generate a useful analysis. You can continue uploading data and asking questions.",
            "primary_cta": "Continue with fallback",
            "secondary_cta": "View model status",
            "tips": [agent_api_status.get("user_message", "")] if agent_api_status else [],
        },
    }
    return messages.get(onboarding_state, messages["no_data"])


def render_onboarding_panel(
    transactions_df=None,
    invoices_df=None,
    goals_df=None,
    agent_api_status: dict | None = None,
    latest_agent_turn: dict | None = None,
):
    """
    Render onboarding guidance for the main page.
    """
    state = infer_onboarding_state(
        transactions_df=transactions_df,
        invoices_df=invoices_df,
        goals_df=goals_df,
        agent_api_status=agent_api_status,
        latest_agent_turn=latest_agent_turn,
    )
    message = build_onboarding_messages(
        state,
        transactions_df=transactions_df,
        invoices_df=invoices_df,
        goals_df=goals_df,
        agent_api_status=agent_api_status,
    )
    with st.container(border=True):
        st.markdown(f"**{message.get('title', '')}**")
        st.markdown(message.get("description", ""))
        tips = message.get("tips", [])
        if tips:
            for tip in tips:
                if tip:
                    st.caption(tip)
        col1, col2 = st.columns(2)
        col1.info(message.get("primary_cta", "Start"))
        col2.info(message.get("secondary_cta", "Details"))
