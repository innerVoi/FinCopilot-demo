import json

import pandas as pd

from src.safety import get_disclaimer
from src.summary_generator import (
    build_summary_context,
    generate_planning_summary,
    safe_top_records,
    template_generate_planning_summary,
)


def make_budget_result():
    return {
        "summary": {
            "total_income": 1000.0,
            "total_expense": 600.0,
            "net_cashflow": 400.0,
            "top_expense_category": "software",
            "fixed_expense_ratio": 0.25,
        },
        "category_spending": pd.DataFrame(
            [
                {
                    "category": "software",
                    "expense_amount": 300.0,
                    "transaction_count": 2,
                    "expense_share": 0.5,
                }
            ]
        ),
    }


def make_invoice_result():
    return {
        "summary": {
            "due_30d_amount": 1200.0,
            "overdue_invoice_amount": 100.0,
        }
    }


def test_safe_top_records_handles_empty_dataframe():
    assert safe_top_records(pd.DataFrame()) == []


def test_safe_top_records_returns_list_of_dicts():
    df = pd.DataFrame(
        [{"date": pd.Timestamp("2026-06-01"), "merchant": "AWS", "amount": -220.0}]
    )

    records = safe_top_records(df)

    assert isinstance(records, list)
    assert records[0]["date"] == "2026-06-01T00:00:00"


def test_build_summary_context_is_json_serializable():
    context = build_summary_context(
        budget_result=make_budget_result(),
        invoice_result=make_invoice_result(),
        rule_anomalies_df=pd.DataFrame(
            [{"merchant": "AWS", "amount": -620.0, "risk_level": "medium"}]
        ),
        lof_result_df=pd.DataFrame(
            [{"merchant": "Vendor X", "amount": -2100.0, "risk_level": "high"}]
        ),
        goals_df=pd.DataFrame(
            [
                {
                    "goal_id": "G001",
                    "goal_name": "Emergency fund",
                    "target_amount": 5000.0,
                    "current_amount": 1800.0,
                    "due_date": pd.Timestamp("2026-12-31"),
                    "priority": "high",
                }
            ]
        ),
    )

    assert isinstance(context, dict)
    json.dumps(context, ensure_ascii=False)


def test_template_generate_planning_summary_contains_required_sections():
    context = build_summary_context(
        budget_result=make_budget_result(),
        invoice_result=make_invoice_result(),
    )

    summary = template_generate_planning_summary(context)

    for heading in [
        "## 本期财务概况",
        "## 预算与支出观察",
        "## 发票与现金流提醒",
        "## 异常支出提醒",
        "## 财务目标观察",
        "## 建议行动",
        "## 假设与限制",
        "## 免责声明",
    ]:
        assert heading in summary
    assert get_disclaimer() in summary


def test_generate_planning_summary_with_use_llm_false_uses_template(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-that-should-not-be-used")

    summary = generate_planning_summary(
        budget_result=make_budget_result(),
        invoice_result=make_invoice_result(),
        use_llm=False,
    )

    assert "## 本期财务概况" in summary
    assert get_disclaimer() in summary
