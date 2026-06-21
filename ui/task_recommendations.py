import pandas as pd
import streamlit as st


DATASET_LABELS = {
    "transactions": "交易流水",
    "invoices": "发票数据",
    "goals": "财务目标",
}

PRIORITY_ORDER = {
    "high": 0,
    "medium": 1,
    "low": 2,
}

DEFAULT_RECOMMENDED_TASKS = [
    {
        "task_id": "cashflow_check",
        "title": "检查未来 30 天现金流",
        "description": "判断近期资金是否安全，识别发票和支出压力。",
        "query": "未来 30 天现金流安全吗？",
        "category": "cashflow",
        "priority": "high",
        "requires": ["transactions", "invoices"],
        "button_label": "检查现金流",
    },
    {
        "task_id": "anomaly_review",
        "title": "找出最可疑支出",
        "description": "结合规则和模型识别需要核查的交易。",
        "query": "这个月哪些支出最可疑？",
        "category": "anomaly",
        "priority": "high",
        "requires": ["transactions"],
        "button_label": "核查支出",
    },
    {
        "task_id": "invoice_priority",
        "title": "查看发票和付款优先级",
        "description": "识别近期到期、逾期和可能造成现金流压力的发票。",
        "query": "有哪些发票或付款要优先处理？",
        "category": "invoice",
        "priority": "medium",
        "requires": ["invoices"],
        "button_label": "查看发票",
    },
    {
        "task_id": "weekly_action_plan",
        "title": "生成本周财务行动清单",
        "description": "根据现金流、异常支出和目标生成本周优先事项。",
        "query": "帮我生成本周财务行动清单。",
        "category": "action",
        "priority": "medium",
        "requires": ["transactions"],
        "button_label": "生成清单",
    },
    {
        "task_id": "goal_plan",
        "title": "检查财务目标进度",
        "description": "判断目标是否按计划推进，并给出行动建议。",
        "query": "我的财务目标进度怎么样？下一步该怎么做？",
        "category": "goal",
        "priority": "medium",
        "requires": ["goals", "transactions"],
        "button_label": "检查目标",
    },
]


def _has_rows(dataframe) -> bool:
    return isinstance(dataframe, pd.DataFrame) and not dataframe.empty


def get_dataset_flags(transactions_df=None, invoices_df=None, goals_df=None) -> dict:
    """
    Return dataset availability flags.
    """
    return {
        "has_transactions": _has_rows(transactions_df),
        "has_invoices": _has_rows(invoices_df),
        "has_goals": _has_rows(goals_df),
    }


def get_missing_requirements(task: dict, dataset_flags: dict) -> list[str]:
    """
    Return missing dataset requirements for a task.
    """
    dataset_flags = dataset_flags or {}
    missing = []
    for requirement in task.get("requires", []) or []:
        if not dataset_flags.get(f"has_{requirement}", False):
            missing.append(requirement)
    return missing


def _disabled_reason(missing_requirements: list[str]) -> str:
    if not missing_requirements:
        return ""
    labels = [DATASET_LABELS.get(item, item) for item in missing_requirements]
    return "需要先上传" + "和".join(labels) + "。"


def _infer_intent(latest_agent_turn: dict | None) -> str:
    latest_agent_turn = latest_agent_turn or {}
    manager_plan = latest_agent_turn.get("manager_plan", {})
    if not manager_plan:
        manager_plan = latest_agent_turn.get("manager_result", {}).get("manager_plan", {})
    return manager_plan.get("intent", "unknown")


def _build_followup_questions(latest_agent_turn: dict | None) -> list[str]:
    intent = _infer_intent(latest_agent_turn)
    mapping = {
        "cashflow_check": [
            "哪些发票最影响现金流？",
            "我该优先处理哪些支出？",
            "帮我生成本周财务行动清单。",
        ],
        "expense_anomaly_review": [
            "哪些可疑支出需要今天核查？",
            "请解释第一笔可疑支出的原因。",
            "帮我生成异常支出核查清单。",
        ],
        "invoice_or_payment_review": [
            "哪些发票最紧急？",
            "如果暂缓付款有什么风险？",
            "帮我生成付款优先级行动清单。",
        ],
        "goal_or_budget_planning": [
            "哪个财务目标风险最高？",
            "如何调整预算来支持目标？",
            "帮我生成本周目标推进清单。",
        ],
        "general_finance_summary": [
            "帮我生成本周财务行动清单。",
            "哪些风险最优先处理？",
            "我下一步应该先看现金流还是异常支出？",
        ],
    }
    return mapping.get(intent, mapping["general_finance_summary"])


def build_recommended_tasks(
    transactions_df=None,
    invoices_df=None,
    goals_df=None,
    latest_agent_turn: dict | None = None,
) -> list[dict]:
    """
    Build task cards from dataset availability and latest turn result.
    """
    dataset_flags = get_dataset_flags(transactions_df, invoices_df, goals_df)
    tasks = []
    for task in DEFAULT_RECOMMENDED_TASKS:
        item = dict(task)
        missing = get_missing_requirements(item, dataset_flags)
        item["available"] = not missing
        item["missing_requirements"] = missing
        item["disabled_reason"] = _disabled_reason(missing)
        tasks.append(item)

    if latest_agent_turn:
        for index, question in enumerate(_build_followup_questions(latest_agent_turn), start=1):
            tasks.append(
                {
                    "task_id": f"followup_{index}",
                    "title": question,
                    "description": "基于最近一次分析结果继续追问。",
                    "query": question,
                    "category": "followup",
                    "priority": "high" if index == 1 else "medium",
                    "requires": [],
                    "available": True,
                    "missing_requirements": [],
                    "disabled_reason": "",
                    "button_label": "继续追问",
                }
            )
    return sort_recommended_tasks(tasks)


def sort_recommended_tasks(tasks: list[dict]) -> list[dict]:
    """
    Sort available and high-priority tasks first.
    """
    return sorted(
        tasks or [],
        key=lambda task: (
            0 if task.get("available") else 1,
            PRIORITY_ORDER.get(task.get("priority", "medium"), 1),
            str(task.get("task_id", "")),
        ),
    )


def get_next_step_hints(
    transactions_df=None,
    invoices_df=None,
    goals_df=None,
    latest_agent_turn: dict | None = None,
) -> list[str]:
    """
    Build friendly next-step hints from dataset and latest turn state.
    """
    flags = get_dataset_flags(transactions_df, invoices_df, goals_df)
    if latest_agent_turn:
        return [
            "分析已完成。你可以查看行动项、展开详细预览，或继续追问更具体的问题。",
            "本轮报告已同步到“行动与报告”页面，适合后续归档和下载。",
        ]
    if not any(flags.values()):
        return [
            "你可以先上传交易流水、发票和财务目标，也可以直接使用默认样例数据体验完整流程。",
            "准备好数据后，建议先检查现金流或核查可疑支出。",
        ]
    hints = []
    if flags["has_transactions"]:
        hints.append("你已经有交易流水，可以先让 FinCopilot 找出最可疑支出或生成本周行动清单。")
    else:
        hints.append("还没有交易流水，现金流、异常支出和行动清单会受到限制。")
    if flags["has_invoices"]:
        hints.append("你已经有发票数据，可以检查未来 30 天现金流和付款优先级。")
    else:
        hints.append("还没有发票数据，现金流和付款优先级判断可能不完整。")
    if flags["has_goals"]:
        hints.append("你已经有财务目标，可以检查目标进度和预算影响。")
    else:
        hints.append("还没有财务目标，因此目标进度分析暂不可用。")
    return hints


def render_recommended_task_cards(tasks: list[dict]) -> str | None:
    """
    Render recommended task cards and return the selected query.
    """
    tasks = tasks or []
    has_followup = any(task.get("category") == "followup" for task in tasks)
    st.subheader("你还可以继续问" if has_followup else "推荐你先试试")
    if not tasks:
        st.info("暂无推荐任务。")
        return None

    selected_query = None
    columns = st.columns(2)
    for index, task in enumerate(tasks):
        column = columns[index % 2]
        with column.container(border=True):
            st.markdown(f"**{task.get('title', '')}**")
            st.caption(task.get("description", ""))
            required = [DATASET_LABELS.get(item, item) for item in task.get("requires", [])]
            st.caption("需要：" + (" + ".join(required) if required else "最近一次分析结果"))
            if task.get("available"):
                st.success("状态：可用")
            else:
                st.warning(f"状态：{task.get('disabled_reason', '缺少必要数据')}")
            if st.button(
                task.get("button_label", "开始"),
                key=f"recommended_task_{task.get('task_id', index)}",
                disabled=not task.get("available", False),
            ):
                selected_query = task.get("query")
                st.session_state["v22_pending_query"] = selected_query
    return selected_query
