import streamlit as st


V22_PAGES = [
    "Copilot Home",
    "Analysis Details",
    "Actions & Reports",
    "Data & Settings",
]
V23_PAGES = V22_PAGES


def render_sidebar_navigation(default_page: str = "Copilot Home") -> str:
    """
    Render V2.3 sidebar navigation and return the selected page.
    """
    default_index = V22_PAGES.index(default_page) if default_page in V22_PAGES else 0
    with st.sidebar:
        st.title("FinCopilot V2.3")
        st.caption("CFO Copilot for small businesses")
        page = st.radio("Navigation", V22_PAGES, index=default_index)
        st.info(
            "Upload data and ask questions on the main screen. FinCopilot will run the multi-agent analysis automatically. "
            "If the live Agent API is unavailable, it will fall back safely."
        )
    return page
