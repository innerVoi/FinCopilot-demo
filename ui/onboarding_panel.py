import pandas as pd
import streamlit as st


def _has_rows(dataframe) -> bool:
    return isinstance(dataframe, pd.DataFrame) and not dataframe.empty


def _missing_data_labels(transactions_df=None, invoices_df=None, goals_df=None) -> list[str]:
    missing = []
    if not _has_rows(transactions_df):
        missing.append("交易流水")
    if not _has_rows(invoices_df):
        missing.append("发票数据")
    if not _has_rows(goals_df):
        missing.append("财务目标")
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
            "title": "先上传数据，或直接使用样例数据开始",
            "description": "FinCopilot 可以基于交易流水、发票和财务目标，帮你分析现金流、异常支出和本周行动项。",
            "primary_cta": "使用默认样例数据",
            "secondary_cta": "查看字段说明",
            "tips": [
                "可以先上传 transactions.csv、invoices.csv 和 goals.csv。",
                "未上传时系统会使用内置样例数据，方便你快速体验完整流程。",
                "准备好数据后，可以直接问：未来 30 天现金流安全吗？",
            ],
        },
        "partial_data": {
            "title": "已有部分数据，可以先开始分析",
            "description": "某些任务已经可用，缺失的数据会影响部分分析准确性。",
            "primary_cta": "先做可用任务",
            "secondary_cta": "补充缺失数据",
            "tips": [f"当前还缺少：{'、'.join(missing)}。"] if missing else [],
        },
        "ready": {
            "title": "数据已准备好，可以开始提问",
            "description": "你可以检查未来现金流、可疑支出、发票压力或生成本周行动清单。",
            "primary_cta": "选择推荐任务",
            "secondary_cta": "直接输入问题",
            "tips": ["建议先检查现金流，再核查异常支出和本周行动项。"],
        },
        "after_first_turn": {
            "title": "分析已完成，建议继续处理下一步",
            "description": "你可以查看行动项、补充缺失信息，或继续追问更具体的问题。",
            "primary_cta": "继续追问",
            "secondary_cta": "查看行动与报告",
            "tips": ["下方会根据最近一次分析推荐后续问题。"],
        },
        "fallback_mode": {
            "title": "当前使用 fallback 分析",
            "description": "真实 Agent 暂不可用，但 fallback 本地规则和工具仍可生成基础分析结果。你可以继续上传数据和提问。",
            "primary_cta": "继续使用 fallback",
            "secondary_cta": "查看模型状态",
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
        col1.info(message.get("primary_cta", "开始"))
        col2.info(message.get("secondary_cta", "查看详情"))
