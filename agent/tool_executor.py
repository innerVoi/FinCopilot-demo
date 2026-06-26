import pandas as pd

from src.anomaly_model import run_lof_detection
from src.anomaly_rules import run_rule_based_anomaly_detection
from src.budget_analyzer import analyze_budget
from src.cashflow_analyzer import analyze_cashflow
from src.categorizer import add_transaction_categories
from src.goal_analyzer import analyze_goals
from src.invoice_analyzer import analyze_invoices


def has_context_output(context: dict, output_key: str) -> bool:
    """
    Return True if context already contains a meaningful tool output.
    """
    if not context or output_key not in context:
        return False
    value = context.get(output_key)
    if value is None:
        return False
    if isinstance(value, pd.DataFrame):
        return not value.empty
    if isinstance(value, dict):
        return bool(value)
    return bool(value)


def _count_risk(df, level):
    if df is None or getattr(df, "empty", True) or "risk_level" not in df.columns:
        return 0
    return int((df["risk_level"] == level).sum())


def summarize_tool_output(tool_name: str, output) -> dict:
    """
    Build a compact summary for a tool output.
    """
    if output is None:
        return {}

    if tool_name == "analyze_budget":
        summary = output.get("summary", {}) if isinstance(output, dict) else {}
        return {
            "total_income": summary.get("total_income", 0.0),
            "total_expense": summary.get("total_expense", 0.0),
            "net_cashflow": summary.get("net_cashflow", 0.0),
            "top_expense_category": summary.get("top_expense_category", "none"),
        }

    if tool_name == "analyze_invoices":
        summary = output.get("summary", {}) if isinstance(output, dict) else {}
        return {
            "unpaid_invoice_amount": summary.get("unpaid_invoice_amount", 0.0),
            "overdue_invoice_amount": summary.get("overdue_invoice_amount", 0.0),
            "due_30d_amount": summary.get("due_30d_amount", 0.0),
        }

    if tool_name == "analyze_cashflow":
        return {
            "risk_level": output.get("risk_level", "unknown"),
            "projected_balance_30d": output.get("projected_balance_30d", 0.0),
            "cash_buffer_days": output.get("cash_buffer_days", 0.0),
        }

    if tool_name == "analyze_goals":
        summary = output.get("summary", {}) if isinstance(output, dict) else {}
        return {
            "goal_count": summary.get("goal_count", 0),
            "high_risk_goal_count": summary.get("high_risk_goal_count", 0),
            "overall_progress_percent": summary.get("overall_progress_percent", 0.0),
        }

    if tool_name == "detect_rule_anomalies":
        return {
            "rule_anomaly_count": 0 if getattr(output, "empty", True) else int(len(output)),
            "high_risk_count": _count_risk(output, "high"),
            "medium_risk_count": _count_risk(output, "medium"),
        }

    if tool_name == "detect_lof_anomalies":
        return {
            "model_result_count": 0 if getattr(output, "empty", True) else int(len(output)),
            "high_risk_count": _count_risk(output, "high"),
            "medium_risk_count": _count_risk(output, "medium"),
        }

    if isinstance(output, pd.DataFrame):
        return {"row_count": int(len(output))}
    if isinstance(output, dict):
        return {"keys": list(output.keys())}
    return {"value": str(output)}


def _missing_inputs(tool_step, context):
    return [
        key
        for key in tool_step.get("input_keys", [])
        if not has_context_output(context, key)
    ]


def _execute_tool(tool_name, context):
    if tool_name == "categorize_transactions":
        return add_transaction_categories(context["transactions_df"])
    if tool_name == "analyze_budget":
        return analyze_budget(context["transactions_df"])
    if tool_name == "analyze_invoices":
        return analyze_invoices(context["invoices_df"])
    if tool_name == "analyze_cashflow":
        return analyze_cashflow(context["transactions_df"], context.get("invoice_result"))
    if tool_name == "analyze_goals":
        return analyze_goals(
            context["goals_df"],
            budget_result=context.get("budget_result"),
            cashflow_result=context.get("cashflow_result"),
        )
    if tool_name == "detect_rule_anomalies":
        return run_rule_based_anomaly_detection(
            context["transactions_df"],
            invoice_result=context.get("invoice_result"),
        )
    if tool_name == "detect_lof_anomalies":
        return run_lof_detection(context["transactions_df"])
    raise ValueError(f"Tool is not auto-executable in Agent Workspace: {tool_name}")


def execute_tool_step(tool_step: dict, context: dict, reuse_existing: bool = True) -> dict:
    """
    Execute one planned tool step or reuse existing output.
    """
    context = context or {}
    tool_name = tool_step["tool_name"]
    output_key = tool_step["output_key"]
    record = {
        "tool_name": tool_name,
        "display_name": tool_step.get("display_name", tool_name),
        "status": "skipped",
        "input_keys": tool_step.get("input_keys", []),
        "output_key": output_key,
        "summary": {},
        "error": None,
    }

    if tool_name in ["explain_transaction_risk", "generate_planning_summary"]:
        record["status"] = "skipped"
        record["error"] = "This tool requires explicit user action. Agent Workspace does not automatically batch-call LLM tools."
        return record

    if reuse_existing and has_context_output(context, output_key):
        output = context[output_key]
        record["status"] = "reused"
        record["summary"] = summarize_tool_output(tool_name, output)
        return record

    missing_inputs = _missing_inputs(tool_step, context)
    if missing_inputs:
        record["status"] = "skipped"
        record["error"] = f"Missing required inputs: {', '.join(missing_inputs)}"
        return record

    try:
        output = _execute_tool(tool_name, context)
        context[output_key] = output
        record["status"] = "executed"
        record["summary"] = summarize_tool_output(tool_name, output)
        return record
    except Exception as error:
        record["status"] = "failed"
        record["error"] = str(error)
        return record


def execute_tool_plan(tool_plan: dict, context: dict, reuse_existing: bool = True) -> dict:
    """
    Execute all planned tool steps.
    """
    updated_context = dict(context or {})
    records = [
        execute_tool_step(step, updated_context, reuse_existing=reuse_existing)
        for step in tool_plan.get("tool_steps", [])
    ]
    execution_summary = {
        "reused": sum(1 for record in records if record["status"] == "reused"),
        "executed": sum(1 for record in records if record["status"] == "executed"),
        "skipped": sum(1 for record in records if record["status"] == "skipped"),
        "failed": sum(1 for record in records if record["status"] == "failed"),
    }
    return {
        "plan_status": tool_plan.get("plan_status", "unknown"),
        "execution_records": records,
        "updated_context": updated_context,
        "execution_summary": execution_summary,
    }
