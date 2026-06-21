import pandas as pd

from src.goal_analyzer import analyze_goals, analyze_single_goal


def test_analyze_single_goal_progress():
    goal = {
        "goal_id": "G001",
        "goal_name": "Emergency fund",
        "target_amount": 1000,
        "current_amount": 400,
        "due_date": "2026-12-31",
        "priority": "high",
    }

    result = analyze_single_goal(goal, net_cashflow=1000, reference_date="2026-06-30")

    assert result["progress_ratio"] == 0.4
    assert result["progress_percent"] == 40
    assert result["remaining_amount"] == 600


def test_analyze_single_goal_completed():
    goal = {
        "target_amount": 1000,
        "current_amount": 1000,
        "due_date": "2026-12-31",
        "priority": "medium",
    }

    result = analyze_single_goal(goal, net_cashflow=100, reference_date="2026-06-30")

    assert result["goal_status"] == "已完成"
    assert result["goal_risk_level"] == "low"
    assert result["remaining_amount"] == 0


def test_analyze_single_goal_overdue():
    goal = {
        "target_amount": 1000,
        "current_amount": 400,
        "due_date": "2026-01-01",
        "priority": "high",
    }

    result = analyze_single_goal(goal, net_cashflow=1000, reference_date="2026-06-30")

    assert result["goal_status"] == "已逾期"
    assert result["goal_risk_level"] == "high"


def test_analyze_single_goal_high_risk_required_saving():
    goal = {
        "target_amount": 12000,
        "current_amount": 0,
        "due_date": "2026-12-31",
        "priority": "high",
    }

    result = analyze_single_goal(goal, net_cashflow=100, reference_date="2026-06-30")

    assert result["goal_risk_level"] == "high"


def test_analyze_goals_output_fields():
    goals_df = pd.DataFrame(
        [
            {
                "goal_id": "G001",
                "goal_name": "Emergency fund",
                "target_amount": 1000,
                "current_amount": 400,
                "due_date": "2026-12-31",
                "priority": "high",
            }
        ]
    )
    budget_result = {"summary": {"net_cashflow": 500}}
    cashflow_result = {"risk_level": "low"}

    result = analyze_goals(
        goals_df,
        budget_result=budget_result,
        cashflow_result=cashflow_result,
        reference_date="2026-06-30",
    )

    assert {"summary", "goals"}.issubset(result.keys())
    summary_keys = {
        "goal_count",
        "completed_goal_count",
        "high_risk_goal_count",
        "medium_risk_goal_count",
        "total_target_amount",
        "total_current_amount",
        "total_remaining_amount",
        "overall_progress_percent",
    }
    assert summary_keys.issubset(result["summary"].keys())
