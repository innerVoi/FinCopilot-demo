import pandas as pd

from agent.action_generator import (
    generate_action_items,
    generate_cashflow_actions,
    generate_clarification_actions,
    generate_goal_actions,
    generate_invoice_actions,
    generate_model_anomaly_actions,
    generate_rule_anomaly_actions,
)


def test_generate_cashflow_actions_from_high_risk():
    actions = generate_cashflow_actions({"risk_level": "high", "projected_balance_30d": -100})

    assert actions
    assert actions[0]["source"] == "cashflow"
    assert actions[0]["priority"] == "high"


def test_generate_invoice_actions_from_overdue_amount():
    actions = generate_invoice_actions({"summary": {"overdue_invoice_amount": 300}})

    assert actions
    assert actions[0]["source"] == "invoice"
    assert actions[0]["priority"] == "high"


def test_generate_rule_anomaly_actions_handles_empty_dataframe():
    assert generate_rule_anomaly_actions(pd.DataFrame()) == []


def test_generate_rule_anomaly_actions_from_high_risk_row():
    df = pd.DataFrame(
        [
            {
                "merchant": "Vendor X",
                "amount": -2600,
                "risk_level": "high",
                "anomaly_type": "large_amount",
                "reason": "金额较高。",
            }
        ]
    )

    actions = generate_rule_anomaly_actions(df)

    assert actions
    assert actions[0]["source"] == "rule_anomaly"
    assert actions[0]["priority"] == "high"


def test_generate_model_anomaly_actions_from_high_risk_row():
    df = pd.DataFrame(
        [
            {
                "merchant": "Unknown Store",
                "amount": -980,
                "risk_level": "high",
                "anomaly_score": 0.95,
                "model_evidence": "模型分数较高。",
            }
        ]
    )

    actions = generate_model_anomaly_actions(df)

    assert actions
    assert actions[0]["source"] == "model_anomaly"
    assert actions[0]["priority"] == "high"


def test_generate_goal_actions_from_high_risk_goal():
    goal_result = {
        "goals": pd.DataFrame(
            [
                {
                    "goal_name": "30 天现金缓冲",
                    "goal_risk_level": "high",
                    "remaining_amount": 3000,
                    "goal_recommendation": "目标存在达成风险。",
                }
            ]
        )
    }

    actions = generate_goal_actions(goal_result)

    assert actions
    assert actions[0]["source"] == "goal"
    assert actions[0]["priority"] == "high"


def test_generate_clarification_actions_from_missing_fields():
    actions = generate_clarification_actions(
        {
            "missing_fields": ["current_cash_balance"],
            "unanswered_questions": [
                {"question": "当前企业账户真实可用余额是多少？"}
            ],
        }
    )

    assert actions
    assert actions[0]["source"] == "clarification"


def test_generate_action_items_returns_list():
    context = {
        "cashflow_result": {"risk_level": "high"},
        "invoice_result": {"summary": {"overdue_invoice_amount": 200}},
        "rule_anomalies_df": pd.DataFrame(),
        "lof_result_df": pd.DataFrame(),
    }
    workspace = {
        "clarification_status": {"missing_fields": [], "unanswered_questions": []},
        "enriched_context": {},
    }

    actions = generate_action_items("cashflow_safety_check", context, workspace=workspace)

    assert isinstance(actions, list)
    assert actions
