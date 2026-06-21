import pandas as pd
import streamlit as st

from agent_api.config import get_agent_api_status
from src.safety import get_disclaimer
from ui.upload_panel import render_data_status_card, render_quick_upload_panel, render_upload_help


def _is_non_empty_df(value) -> bool:
    return isinstance(value, pd.DataFrame) and not value.empty


def _preview_dataset(title: str, dataframe):
    st.subheader(title)
    if _is_non_empty_df(dataframe):
        st.caption(f"行数：{len(dataframe)}")
        if "date" in dataframe.columns:
            st.caption(f"日期范围：{dataframe['date'].min()} 至 {dataframe['date'].max()}")
        st.dataframe(dataframe.head(200), use_container_width=True)
    else:
        st.info("暂无数据。请先在 Copilot 主界面上传数据，或使用默认样例数据。")


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
    _preview_dataset("transactions.csv 预览", transactions_df)
    _preview_dataset("invoices.csv 预览", invoices_df)
    _preview_dataset("goals.csv 预览", goals_df)


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
    st.caption("字段名可以根据当前项目实际 CSV 模板调整。")


def render_agent_model_tab():
    """
    Render read-only Agent and model status.
    """
    status = get_agent_api_status()
    if status.get("mode") == "api_agent":
        st.success(status.get("user_message", "当前使用真实 Agent 分析。"))
    else:
        st.info(status.get("user_message", "当前真实 Agent 暂不可用，系统将自动 fallback。"))
    st.markdown(f"**当前 Agent 模式：** {status.get('mode', 'fallback')}")
    st.markdown(f"**当前模型：** {status.get('model', 'gpt-5.4-mini')}")
    st.markdown(f"**API Key 是否存在：** {'是' if status.get('has_api_key') else '否'}")
    st.markdown(f"**API Base URL：** {status.get('base_url', '')}")
    st.markdown("Agent API 默认在存在可用密钥时尝试启用；请求失败、模型不可用或输出无法解析时会自动 fallback。")
    st.markdown("模型可通过环境变量 `OPENAI_AGENT_MODEL` 或 `OPENAI_MODEL` 指定。")


def render_safety_boundary_tab():
    """
    Render safety boundary.
    """
    st.markdown("FinCopilot 仅用于财务整理、风险提醒和教育性支持。")
    for item in [
        "不提供投资建议",
        "不提供税务建议",
        "不提供法律建议",
        "不提供债务处置建议",
        "不认定任何交易为欺诈",
        "不执行真实付款",
        "不执行真实转账",
        "不承诺收益或财务结果",
    ]:
        st.markdown(f"- {item}")
    st.caption(get_disclaimer())


def render_data_settings_page(transactions_df=None, invoices_df=None, goals_df=None):
    """
    Render the unified data and settings page.
    """
    st.header("数据与设置")
    tabs = st.tabs(["数据上传", "数据预览", "字段说明", "Agent 与模型", "安全边界"])
    with tabs[0]:
        render_data_upload_tab(transactions_df=transactions_df, invoices_df=invoices_df, goals_df=goals_df)
    with tabs[1]:
        render_data_preview_tab(transactions_df=transactions_df, invoices_df=invoices_df, goals_df=goals_df)
    with tabs[2]:
        render_field_guide_tab()
    with tabs[3]:
        render_agent_model_tab()
    with tabs[4]:
        render_safety_boundary_tab()
