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
        return "3 天内"
    if priority == "medium":
        return "7 天内"
    return "本月内"


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
                title="优先核查未来 30 天现金流缺口",
                description="系统估算未来 30 天预计余额可能为负或现金缓冲不足。",
                source="cashflow",
                priority="high",
                reason="未来 30 天现金流风险较高，需要优先确认余额、回款和必要支出。",
                suggested_deadline="今天",
                recommended_steps=[
                    "确认当前企业账户真实可用余额。",
                    "确认未来 30 天确定客户回款。",
                    "核查未来 30 天必须支付的大额款项。",
                    "优先处理逾期发票和固定支出。",
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
            title="复查未来 30 天现金流压力",
            description="系统识别到中等现金流压力，建议尽快复查未来回款和待付款。",
            source="cashflow",
            priority="medium",
            reason="现金流风险为 medium，未来发票和固定支出可能影响短期余额。",
            suggested_deadline="3 天内",
            recommended_steps=[
                "复核未来 30 天客户回款是否确定。",
                "确认未来 30 天待付发票金额。",
                "检查是否有未上传固定支出。",
                "在行动清单中优先处理金额较大的现金流相关任务。",
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
                title="处理逾期发票",
                description="当前存在逾期发票，需要确认付款状态和后续处理安排。",
                source="invoice",
                priority="high",
                reason=f"逾期发票金额为 {overdue_amount:.2f}。",
                suggested_deadline="今天",
                recommended_steps=[
                    "查看逾期发票列表。",
                    "确认是否已经支付但未更新状态。",
                    "如果尚未支付，安排付款计划或记录需要跟进。",
                    "更新发票状态。",
                ],
                related_record={"overdue_invoice_amount": overdue_amount},
            )
        )

    if due_7d_amount > 0:
        actions.append(
            make_action_item(
                action_id=generate_action_id(len(actions) + 1),
                title="确认未来 7 天到期发票",
                description="未来 7 天存在即将到期发票，需要提前确认付款安排。",
                source="invoice",
                priority="medium",
                reason=f"未来 7 天到期发票金额为 {due_7d_amount:.2f}。",
                suggested_deadline="3 天内",
                recommended_steps=[
                    "查看未来 7 天到期发票。",
                    "确认发票是否准确且仍需支付。",
                    "将必要付款纳入短期现金流安排。",
                ],
                related_record={"due_7d_amount": due_7d_amount},
            )
        )

    if due_30d_amount >= 2000:
        actions.append(
            make_action_item(
                action_id=generate_action_id(len(actions) + 1),
                title="规划未来 30 天发票付款安排",
                description="未来 30 天待付发票金额较高，需要提前组织付款节奏。",
                source="invoice",
                priority="medium",
                reason=f"未来 30 天到期发票金额为 {due_30d_amount:.2f}。",
                suggested_deadline="7 天内",
                recommended_steps=[
                    "查看未来 30 天到期发票清单。",
                    "按到期日和金额排序。",
                    "与现金流视图一起确认付款优先级。",
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
        merchant = row.get("merchant", "未知商户")
        anomaly_type = row.get("anomaly_type", "规则")
        actions.append(
            make_action_item(
                action_id=generate_action_id(len(actions) + 1),
                title=f"核查 {merchant} 的 {anomaly_type} 异常",
                description="该交易被规则/统计分支识别为需要核查的异常记录。",
                source="rule_anomaly",
                priority=priority,
                reason=str(row.get("reason", "该交易命中了规则/统计异常条件。")),
                suggested_deadline=_deadline_for_priority(priority),
                recommended_steps=[
                    "核查原始交易凭证。",
                    "确认该交易是否为授权支出。",
                    "判断是否需要重新分类。",
                    "如无法解释，标记为需要跟进。",
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
        merchant = row.get("merchant", "未知商户")
        actions.append(
            make_action_item(
                action_id=generate_action_id(len(actions) + 1),
                title=f"核查模型高风险交易：{merchant}",
                description="该交易被 LOF 模型识别为偏离局部交易模式的记录。",
                source="model_anomaly",
                priority=priority,
                reason=str(row.get("model_evidence", "模型分数显示该交易偏离常见模式。")),
                suggested_deadline=_deadline_for_priority(priority),
                recommended_steps=[
                    "查看模型证据。",
                    "核查商户和金额是否符合业务背景。",
                    "判断是否为正常业务支出、一次性支出或需要跟进的异常。",
                    "在后续进展跟踪中更新处理状态。",
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
        goal_name = row.get("goal_name", "未命名目标")
        actions.append(
            make_action_item(
                action_id=generate_action_id(len(actions) + 1),
                title=f"复查财务目标：{goal_name}",
                description="该财务目标存在进度或现金流压力，需要确认优先级和可执行路径。",
                source="goal",
                priority=priority,
                reason=str(row.get("goal_recommendation", "该目标存在达成风险。")),
                suggested_deadline=_deadline_for_priority(priority),
                recommended_steps=[
                    "查看目标剩余缺口。",
                    "确认目标优先级。",
                    "评估当前净现金流是否支持目标。",
                    "必要时调整目标期限或每月储备节奏。",
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
    steps.append("保存补充信息并重新运行 Agent Workspace。")
    return [
        make_action_item(
            action_id=generate_action_id(1),
            title="补充关键业务信息",
            description="当前任务仍有未回答的澄清问题，补充后可提高分析和行动清单质量。",
            source="clarification",
            priority="medium",
            reason="部分业务上下文尚未填写，当前结论仍可能依赖上传数据估算。",
            suggested_deadline="下次复查前",
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
