import pandas as pd
import streamlit as st

from agent_api.config import get_agent_api_status
from memory.workspace import get_current_identity
from src.safety import get_disclaimer
from ui.memory_management_page import render_memory_management_page
from ui.upload_panel import render_data_status_card, render_quick_upload_panel, render_upload_help


def _is_non_empty_df(value) -> bool:
    return isinstance(value, pd.DataFrame) and not value.empty


def _preview_dataset(title: str, dataframe):
    st.subheader(title)
    if _is_non_empty_df(dataframe):
        st.caption(f"Rows: {len(dataframe)}")
        if "date" in dataframe.columns:
            st.caption(f"Date range: {dataframe['date'].min()} to {dataframe['date'].max()}")
        st.dataframe(dataframe.head(200), use_container_width=True)
    else:
        st.info("No data yet. Upload data on Copilot Home or use sample data.")


def render_data_upload_tab(transactions_df=None, invoices_df=None, goals_df=None):
    """
    Render data upload controls and current data status.
    """
    render_data_status_card(
        transactions_df=transactions_df,
        invoices_df=invoices_df,
        goals_df=goals_df,
        agent_api_status=get_agent_api_status(),
    )
    render_quick_upload_panel()
    render_upload_help()


def render_data_preview_tab(transactions_df=None, invoices_df=None, goals_df=None):
    """
    Render uploaded data previews.
    """
    _preview_dataset("transactions.csv Preview", transactions_df)
    _preview_dataset("invoices.csv Preview", invoices_df)
    _preview_dataset("goals.csv Preview", goals_df)


def render_field_guide_tab():
    """
    Render CSV field guide.
    """
    st.subheader("transactions.csv")
    st.markdown("- `date`\n- `description`\n- `merchant`\n- `amount`\n- `account`\n- `category`")
    st.subheader("invoices.csv")
    st.markdown("- `invoice_id`\n- `vendor`\n- `due_date`\n- `amount`\n- `status`\n- `category`")
    st.subheader("goals.csv")
    st.markdown("- `goal_name`\n- `target_amount`\n- `current_amount`\n- `deadline`\n- `priority`")
    st.caption("Field names can be adjusted to match the current CSV templates.")


def render_agent_model_tab():
    """
    Render read-only Agent and model status.
    """
    status = get_agent_api_status()
    if status.get("mode") == "api_agent":
        st.success(status.get("user_message", "Live Agent analysis is active."))
    else:
        st.info(status.get("user_message", "The live Agent API is unavailable. FinCopilot will automatically fall back."))
    st.markdown(f"**Current Agent mode: ** {status.get('mode', 'fallback')}")
    st.markdown(f"**Current model:** {status.get('model', 'gpt-5.4-mini')}")
    st.markdown(f"**API key present: ** {'Yes' if status.get('has_api_key') else 'No'}")
    st.markdown(f"**API Base URL:** {status.get('base_url', '')}")
    st.markdown("Agent API is attempted by default when a usable key exists. Requests automatically fall back if the model is unavailable, the call fails, or the output cannot be parsed.")
    st.markdown("The model can be configured with `OPENAI_AGENT_MODEL` or `OPENAI_MODEL`.")


def render_memory_workspace_tab():
    """
    Render current memory database and workspace identity.
    """
    identity = get_current_identity(st.session_state)
    if st.session_state.get("memory_init_error"):
        st.error(f"Memory database initialization failed: {st.session_state.get('memory_init_error')}")
        return
    render_memory_management_page(identity["user_id"], identity["workspace_id"])


def render_safety_boundary_tab():
    """
    Render safety boundary.
    """
    st.markdown("FinCopilot is for financial organization, risk reminders, and educational support only.")
    for item in [
        "Does not provide investment advice",
        "Does not provide tax advice",
        "Does not provide legal advice",
        "Does not provide debt-resolution advice",
        "Does not determine that any transaction is fraud",
        "Does not execute real payments",
        "Does not execute real transfers",
        "Does not promise returns or financial outcomes",
    ]:
        st.markdown(f"- {item}")
    st.caption(get_disclaimer())


def render_data_settings_page(transactions_df=None, invoices_df=None, goals_df=None):
    """
    Render the unified data and settings page.
    """
    st.header("Data & Settings")
    tabs = st.tabs(["Data Upload", "Data Preview", "Field Guide", "Agent & Model", "Memory & Workspace", "Safety Boundaries"])
    with tabs[0]:
        render_data_upload_tab(transactions_df=transactions_df, invoices_df=invoices_df, goals_df=goals_df)
    with tabs[1]:
        render_data_preview_tab(transactions_df=transactions_df, invoices_df=invoices_df, goals_df=goals_df)
    with tabs[2]:
        render_field_guide_tab()
    with tabs[3]:
        render_agent_model_tab()
    with tabs[4]:
        render_memory_workspace_tab()
    with tabs[5]:
        render_safety_boundary_tab()
