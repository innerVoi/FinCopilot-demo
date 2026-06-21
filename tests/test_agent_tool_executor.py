from agent.task_planner import build_tool_step, create_task_plan
from agent.tool_executor import (
    execute_tool_plan,
    execute_tool_step,
    has_context_output,
    summarize_tool_output,
)


def test_has_context_output_detects_existing_dict_output():
    assert has_context_output({"budget_result": {"summary": {}}}, "budget_result")
    assert not has_context_output({"budget_result": {}}, "budget_result")


def test_summarize_budget_output_contains_net_cashflow():
    summary = summarize_tool_output(
        "analyze_budget",
        {"summary": {"net_cashflow": 250.0, "top_expense_category": "Software"}},
    )

    assert summary["net_cashflow"] == 250.0
    assert summary["top_expense_category"] == "Software"


def test_summarize_cashflow_output_contains_risk_fields():
    summary = summarize_tool_output(
        "analyze_cashflow",
        {"risk_level": "medium", "projected_balance_30d": 1200.0},
    )

    assert summary["risk_level"] == "medium"
    assert summary["projected_balance_30d"] == 1200.0


def test_execute_tool_step_reuses_existing_output():
    step = build_tool_step("analyze_budget", 1)
    context = {"budget_result": {"summary": {"net_cashflow": 100.0}}}

    record = execute_tool_step(step, context)

    assert record["status"] == "reused"
    assert record["summary"]["net_cashflow"] == 100.0


def test_execute_tool_step_skips_when_inputs_are_missing():
    step = build_tool_step("analyze_budget", 1)

    record = execute_tool_step(step, {})

    assert record["status"] == "skipped"
    assert "transactions_df" in record["error"]


def test_execute_tool_step_skips_llm_tool():
    step = build_tool_step("explain_transaction_risk", 1)

    record = execute_tool_step(step, {"selected_anomaly_row": {"amount": -100}})

    assert record["status"] == "skipped"
    assert "不会自动批量调用大模型" in record["error"]


def test_execute_tool_plan_returns_records_and_summary():
    data_check = {"status": "ready", "clarifying_questions": []}
    plan = create_task_plan("suspicious_expense_review", data_check=data_check)

    result = execute_tool_plan(plan, {})

    assert result["execution_records"]
    assert result["execution_summary"]["skipped"] >= 1
