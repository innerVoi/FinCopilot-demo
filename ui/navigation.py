import streamlit as st


V22_PAGES = [
    "Copilot 主界面",
    "分析详情",
    "行动与报告",
    "数据与设置",
]


def render_sidebar_navigation(default_page: str = "Copilot 主界面") -> str:
    """
    Render V2.2 sidebar navigation and return the selected page.
    """
    default_index = V22_PAGES.index(default_page) if default_page in V22_PAGES else 0
    with st.sidebar:
        st.title("FinCopilot V2.2")
        st.caption("小微企业财务 Copilot")
        page = st.radio("导航", V22_PAGES, index=default_index)
        st.info(
            "在主界面上传数据并提问，FinCopilot 会自动调用多 Agent 分析；"
            "如果真实 Agent 不可用，会自动 fallback。"
        )
    return page
