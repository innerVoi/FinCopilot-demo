import pandas as pd
import streamlit as st


DATASET_LABELS = {
    "transactions": "Transactions",
    "invoices": "Invoices",
    "goals": "Goals",
}

PRIORITY_ORDER = {
    "high": 0,
    "medium": 1,
    "low": 2,
}

DEFAULT_RECOMMENDED_TASKS = [
    {
        "task_id": "cashflow_check",
        "title": "Check 30-Day Cash Flow",
        "description": "Assess near-term cash safety and identify invoice or expense pressure.",
        "query": "Is cash flow safe for the next 30 days?",
        "category": "cashflow",
        "priority": "high",
        "requires": ["transactions", "invoices"],
        "button_label": "Check cash flow",
    },
    {
        "task_id": "anomaly_review",
        "title": "Find Suspicious Expenses",
        "description": "Use rules and models to identify transactions that need review.",
        "query": "Which expenses look most suspicious this month?",
        "category": "anomaly",
        "priority": "high",
        "requires": ["transactions"],
        "button_label": "Review expenses",
    },
    {
        "task_id": "invoice_priority",
        "title": "Review Invoice and Payment Priorities",
        "description": "Identify upcoming, overdue, and cash-flow-sensitive invoices.",
        "query": "Which invoices or payments should be prioritized?",
        "category": "invoice",
        "priority": "medium",
        "requires": ["invoices"],
        "button_label": "Review invoices",
    },
    {
        "task_id": "weekly_action_plan",
        "title": "Generate This Week's Finance Action Plan",
        "description": "Generate weekly priorities from cash flow, anomalies, and goals.",
        "query": "Generate my finance action plan for this week.",
        "category": "action",
        "priority": "medium",
        "requires": ["transactions"],
        "button_label": "Generate plan",
    },
    {
        "task_id": "goal_plan",
        "title": "Check Goal Progress",
        "description": "Check whether goals are on track and suggest next actions.",
        "query": "How are my financial goals progressing, and what should I do next?",
        "category": "goal",
        "priority": "medium",
        "requires": ["goals", "transactions"],
        "button_label": "Check goals",
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
    return "Please upload " + " and ".join(labels) + "。"


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
            "Which invoices affect cash flow the most?",
            "Which expenses should I handle first?",
            "Generate my finance action plan for this week.",
        ],
        "expense_anomaly_review": [
            "Which suspicious expenses should be reviewed today?",
            "Explain why the first suspicious expense was flagged.",
            "Generate an expense anomaly review checklist.",
        ],
        "invoice_or_payment_review": [
            "Which invoices are most urgent?",
            "What are the risks if I delay payment?",
            "Generate a payment-priority action list.",
        ],
        "goal_or_budget_planning": [
            "Which financial goal has the highest risk?",
            "How should I adjust the budget to support the goal?",
            "Generate this week's goal action list.",
        ],
        "general_finance_summary": [
            "Generate my finance action plan for this week.",
            "Which risks should be handled first?",
            "Should I look at cash flow or suspicious expenses first?",
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
                    "description": "Continue from the latest analysis.",
                    "query": question,
                    "category": "followup",
                    "priority": "high" if index == 1 else "medium",
                    "requires": [],
                    "available": True,
                    "missing_requirements": [],
                    "disabled_reason": "",
                    "button_label": "Follow up",
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
            "Analysis is complete. You can review action items, expand the detailed preview, or ask a more specific follow-up.",
            "This report has been synced to Actions & Reports for archiving and download.",
        ]
    if not any(flags.values()):
        return [
            "Upload transactions, invoices, and goals, or use sample data for the full demo flow.",
            "Once data is ready, start by checking cash flow or reviewing suspicious expenses.",
        ]
    hints = []
    if flags["has_transactions"]:
        hints.append("Transactions are available, so FinCopilot can find suspicious expenses or generate this week's action plan.")
    else:
        hints.append("No transactions are available yet, so cash flow, anomaly review, and action planning will be limited.")
    if flags["has_invoices"]:
        hints.append("Invoices are available, so you can check 30-day cash flow and payment priorities.")
    else:
        hints.append("No invoices are available yet, so cash-flow and payment-priority analysis may be incomplete.")
    if flags["has_goals"]:
        hints.append("Goals are available, so you can check goal progress and budget impact.")
    else:
        hints.append("No goals are available yet, so goal-progress analysis is unavailable.")
    return hints


def render_recommended_task_cards(tasks: list[dict]) -> str | None:
    """
    Render recommended task cards and return the selected query.
    """
    tasks = tasks or []
    has_followup = any(task.get("category") == "followup" for task in tasks)
    st.subheader("Suggested Follow-ups" if has_followup else "Recommended Starting Points")
    if not tasks:
        st.info("No recommended tasks yet.")
        return None

    selected_query = None
    columns = st.columns(2)
    for index, task in enumerate(tasks):
        column = columns[index % 2]
        with column.container(border=True):
            st.markdown(f"**{task.get('title', '')}**")
            st.caption(task.get("description", ""))
            required = [DATASET_LABELS.get(item, item) for item in task.get("requires", [])]
            st.caption("Requires: " + (" + ".join(required) if required else "latest analysis result"))
            if task.get("available"):
                st.success("Status: available")
            else:
                st.warning(f"Status: {task.get('disabled_reason', 'missing required data')}")
            if st.button(
                task.get("button_label", "Start"),
                key=f"recommended_task_{task.get('task_id', index)}",
                disabled=not task.get("available", False),
            ):
                selected_query = task.get("query")
                st.session_state["v22_pending_query"] = selected_query
    return selected_query
