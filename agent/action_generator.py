import pandas as pd

from agent.action_item import generate_action_id, make_action_item, normalize_priority


def _safe_summary(result):
    if isinstance(result, dict):
        return result.get("summary", {})
    return {}


def _is_non_empty_df(value) -> bool:
    return isinstance(value, pd.DataFrame) and not value.empty


def _row_to_record(row) -> dict:
    record = {}
    for key, value in row.to_dict().items():
        if hasattr(value, "isoformat"):
            record[key] = value.isoformat()
        else:
            record[key] = value
    return record


def _deadline_for_priority(priority: str) -> str:
    if priority == "high":
        return "within 3 days"
    if priority == "medium":
        return "within 7 days"
    return "this month"


def _with_sequential_ids(action_items: list[dict]) -> list[dict]:
    updated = []
    for index, item in enumerate(action_items or [], start=1):
        copied = dict(item)
        copied["action_id"] = generate_action_id(index)
        updated.append(copied)
    return updated


def generate_cashflow_actions(cashflow_result=None, enriched_context=None) -> list[dict]:
    """
    Generate action items from cashflow risk.
    """
    cashflow = cashflow_result or {}
    enriched_cashflow = (enriched_context or {}).get("enriched_cashflow_summary", {})
    risk_level = normalize_priority(
        enriched_cashflow.get("adjusted_risk_level") or cashflow.get("risk_level")
    )
    raw_risk = enriched_cashflow.get("adjusted_risk_level") or cashflow.get("risk_level")
    if raw_risk not in {"high", "medium"}:
        return []

    if risk_level == "high":
        return [
            make_action_item(
                action_id=generate_action_id(1),
                title="Prioritize the 30-day cash-flow gap",
                description="The system estimates that the 30-day projected balance may be negative or the cash buffer may be insufficient.",
                source="cashflow",
                priority="high",
                reason="Cash-flow risk is high for the next 30 days. Confirm balances, expected collections, and necessary payments first.",
                suggested_deadline="today",
                recommended_steps=[
                    "Confirm the real available balance in business accounts.",
                    "Confirm customer collections expected in the next 30 days.",
                    "Review large required payments due in the next 30 days.",
                    "Prioritize overdue invoices and fixed expenses.",
                ],
                related_record={
                    "risk_level": raw_risk,
                    "projected_balance_30d": cashflow.get("projected_balance_30d"),
                    "adjusted_projected_balance_30d": enriched_cashflow.get(
                        "adjusted_projected_balance_30d"
                    ),
                },
            )
        ]

    return [
        make_action_item(
            action_id=generate_action_id(1),
            title="Review 30-day cash-flow pressure",
            description="The system identified moderate cash-flow pressure. Review expected collections and payables soon.",
            source="cashflow",
            priority="medium",
            reason="Cash-flow risk is medium. Upcoming invoices and fixed expenses may affect short-term balances.",
            suggested_deadline="within 3 days",
            recommended_steps=[
                "Review whether customer collections in the next 30 days are confirmed.",
                "Confirm invoice amounts due in the next 30 days.",
                "Check whether any fixed expenses were not uploaded.",
                "Prioritize larger cash-flow-related tasks in the action list.",
            ],
            related_record={
                "risk_level": raw_risk,
                "projected_balance_30d": cashflow.get("projected_balance_30d"),
                "adjusted_projected_balance_30d": enriched_cashflow.get(
                    "adjusted_projected_balance_30d"
                ),
            },
        )
    ]


def generate_invoice_actions(invoice_result=None) -> list[dict]:
    """
    Generate action items from invoice pressure.
    """
    summary = _safe_summary(invoice_result)
    actions = []
    overdue_amount = float(summary.get("overdue_invoice_amount", 0.0) or 0.0)
    due_7d_amount = float(summary.get("due_7d_amount", 0.0) or 0.0)
    due_30d_amount = float(summary.get("due_30d_amount", 0.0) or 0.0)

    if overdue_amount > 0:
        actions.append(
            make_action_item(
                action_id=generate_action_id(len(actions) + 1),
                title="Handle overdue invoices",
                description="Overdue invoices exist. Confirm payment status and next handling steps.",
                source="invoice",
                priority="high",
                reason=f"Overdue invoice amount is {overdue_amount:.2f}.",
                suggested_deadline="today",
                recommended_steps=[
                    "Review the overdue invoice list.",
                    "Confirm whether payment has already been made but the status was not updated.",
                    "If unpaid, arrange a payment plan or record the required follow-up.",
                    "Update invoice status.",
                ],
                related_record={"overdue_invoice_amount": overdue_amount},
            )
        )

    if due_7d_amount > 0:
        actions.append(
            make_action_item(
                action_id=generate_action_id(len(actions) + 1),
                title="Confirm invoices due in the next 7 days",
                description="Invoices are due within the next 7 days. Confirm payment arrangements in advance.",
                source="invoice",
                priority="medium",
                reason=f"Invoice amount due in the next 7 days is {due_7d_amount:.2f}.",
                suggested_deadline="within 3 days",
                recommended_steps=[
                    "Review invoices due in the next 7 days.",
                    "Confirm whether the invoices are accurate and still payable.",
                    "Include required payments in the short-term cash-flow plan.",
                ],
                related_record={"due_7d_amount": due_7d_amount},
            )
        )

    if due_30d_amount >= 2000:
        actions.append(
            make_action_item(
                action_id=generate_action_id(len(actions) + 1),
                title="Plan invoice payments for the next 30 days",
                description="Invoice payments due in the next 30 days are high. Plan the payment cadence in advance.",
                source="invoice",
                priority="medium",
                reason=f"Invoice amount due in the next 30 days is {due_30d_amount:.2f}.",
                suggested_deadline="within 7 days",
                recommended_steps=[
                    "Review the list of invoices due in the next 30 days.",
                    "Sort by due date and amount.",
                    "Confirm payment priority alongside the cash-flow view.",
                ],
                related_record={"due_30d_amount": due_30d_amount},
            )
        )

    return actions


def generate_rule_anomaly_actions(rule_anomalies_df=None, max_items=5) -> list[dict]:
    """
    Generate action items from rule/statistical anomalies.
    """
    if not _is_non_empty_df(rule_anomalies_df) or "risk_level" not in rule_anomalies_df.columns:
        return []

    risky_df = rule_anomalies_df[
        rule_anomalies_df["risk_level"].isin(["high", "medium"])
    ].copy()
    if "amount" in risky_df.columns:
        risky_df["abs_amount"] = pd.to_numeric(risky_df["amount"], errors="coerce").abs()
        risky_df = risky_df.sort_values(
            by=["risk_level", "abs_amount"],
            ascending=[True, False],
        )

    actions = []
    for _, row in risky_df.head(max_items).iterrows():
        priority = normalize_priority(row.get("risk_level"))
        merchant = row.get("merchant", "Unknown merchant")
        anomaly_type = row.get("anomaly_type", "rule")
        actions.append(
            make_action_item(
                action_id=generate_action_id(len(actions) + 1),
                title=f"Review {anomaly_type} anomaly for {merchant}",
                description="This transaction was flagged by the rule/statistical branch as a record that needs review.",
                source="rule_anomaly",
                priority=priority,
                reason=str(row.get("reason", "This transaction matched rule/statistical anomaly conditions.")),
                suggested_deadline=_deadline_for_priority(priority),
                recommended_steps=[
                    "Review the original transaction evidence.",
                    "Confirm whether the transaction was authorized.",
                    "Decide whether it needs to be reclassified.",
                    "If it cannot be explained, mark it for follow-up.",
                ],
                related_record=_row_to_record(row),
            )
        )
    return actions


def generate_model_anomaly_actions(lof_result_df=None, max_items=5) -> list[dict]:
    """
    Generate action items from LOF model anomalies.
    """
    if not _is_non_empty_df(lof_result_df) or "risk_level" not in lof_result_df.columns:
        return []

    risky_df = lof_result_df[lof_result_df["risk_level"].isin(["high", "medium"])].copy()
    if risky_df.empty:
        return []
    if "abs_amount" not in risky_df.columns and "amount" in risky_df.columns:
        risky_df["abs_amount"] = pd.to_numeric(risky_df["amount"], errors="coerce").abs()
    sort_columns = [
        column
        for column in ["risk_level", "anomaly_score", "abs_amount"]
        if column in risky_df.columns
    ]
    if sort_columns:
        ascending = [True if column == "risk_level" else False for column in sort_columns]
        risky_df = risky_df.sort_values(by=sort_columns, ascending=ascending)

    actions = []
    for _, row in risky_df.head(max_items).iterrows():
        priority = normalize_priority(row.get("risk_level"))
        merchant = row.get("merchant", "Unknown merchant")
        actions.append(
            make_action_item(
                action_id=generate_action_id(len(actions) + 1),
                title=f"Review high-risk model transaction: {merchant}",
                description="This transaction was identified by the LOF model as deviating from local transaction patterns.",
                source="model_anomaly",
                priority=priority,
                reason=str(row.get("model_evidence", "The model score indicates this transaction deviates from common patterns.")),
                suggested_deadline=_deadline_for_priority(priority),
                recommended_steps=[
                    "Review the model evidence.",
                    "Check whether the merchant and amount fit the business context.",
                    "Decide whether it is normal business spending, a one-off expense, or an anomaly needing follow-up.",
                    "Update handling status in the follow-up tracker.",
                ],
                related_record=_row_to_record(row),
            )
        )
    return actions


def generate_goal_actions(goal_result=None, max_items=5) -> list[dict]:
    """
    Generate action items from financial goal risk.
    """
    goals_df = goal_result.get("goals") if isinstance(goal_result, dict) else None
    if not _is_non_empty_df(goals_df) or "goal_risk_level" not in goals_df.columns:
        return []

    risky_df = goals_df[goals_df["goal_risk_level"].isin(["high", "medium"])].copy()
    if risky_df.empty:
        return []
    if "remaining_amount" in risky_df.columns:
        risky_df = risky_df.sort_values(
            by=["goal_risk_level", "remaining_amount"],
            ascending=[True, False],
        )

    actions = []
    for _, row in risky_df.head(max_items).iterrows():
        priority = normalize_priority(row.get("goal_risk_level"))
        goal_name = row.get("goal_name", "Unnamed goal")
        actions.append(
            make_action_item(
                action_id=generate_action_id(len(actions) + 1),
                title=f"Review financial goal: {goal_name}",
                description="This financial goal has progress or cash-flow pressure. Confirm priority and an executable path.",
                source="goal",
                priority=priority,
                reason=str(row.get("goal_recommendation", "This goal has completion risk.")),
                suggested_deadline=_deadline_for_priority(priority),
                recommended_steps=[
                    "Review the remaining gap for the goal.",
                    "Confirm goal priority.",
                    "Assess whether current net cash flow can support the goal.",
                    "Adjust the target date or monthly reserve pace if needed.",
                ],
                related_record=_row_to_record(row),
            )
        )
    return actions


def generate_clarification_actions(clarification_status=None) -> list[dict]:
    """
    Generate action items for unanswered clarification questions.
    """
    status = clarification_status or {}
    unanswered_questions = status.get("unanswered_questions", [])
    if not unanswered_questions:
        return []

    steps = [
        question.get("question", "")
        for question in unanswered_questions
        if question.get("question")
    ]
    steps.append("Save the additional information and rerun Agent Workspace.")
    return [
        make_action_item(
            action_id=generate_action_id(1),
            title="Add key business information",
            description="This task still has unanswered clarification questions. Adding the information can improve the analysis and action list.",
            source="clarification",
            priority="medium",
            reason="Some business context is still missing, so current conclusions may rely on estimates from the uploaded data.",
            suggested_deadline="before the next review",
            recommended_steps=steps,
            related_record={"missing_fields": status.get("missing_fields", [])},
        )
    ]


def generate_action_items(
    task_id: str,
    context: dict,
    workspace: dict | None = None,
    max_items_per_source=5,
) -> list[dict]:
    """
    Generate action items for a selected Agent task.
    """
    context = context or {}
    workspace = workspace or {}
    enriched_context = workspace.get("enriched_context", {})
    clarification_status = workspace.get("clarification_status", {})

    if task_id == "cashflow_safety_check":
        actions = (
            generate_cashflow_actions(context.get("cashflow_result"), enriched_context)
            + generate_invoice_actions(context.get("invoice_result"))
            + generate_rule_anomaly_actions(
                context.get("rule_anomalies_df"),
                max_items=max_items_per_source,
            )
            + generate_model_anomaly_actions(
                context.get("lof_result_df"),
                max_items=max_items_per_source,
            )
            + generate_clarification_actions(clarification_status)
        )
        return _with_sequential_ids(actions)

    if task_id == "suspicious_expense_review":
        actions = (
            generate_rule_anomaly_actions(
                context.get("rule_anomalies_df"),
                max_items=max_items_per_source,
            )
            + generate_model_anomaly_actions(
                context.get("lof_result_df"),
                max_items=max_items_per_source,
            )
            + generate_clarification_actions(clarification_status)
        )
        return _with_sequential_ids(actions)

    if task_id == "goal_action_plan":
        actions = (
            generate_goal_actions(
                context.get("goal_result"),
                max_items=max_items_per_source,
            )
            + generate_cashflow_actions(context.get("cashflow_result"), enriched_context)
            + generate_clarification_actions(clarification_status)
        )
        return _with_sequential_ids(actions)

    return _with_sequential_ids(generate_clarification_actions(clarification_status))
