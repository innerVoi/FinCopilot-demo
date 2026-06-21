import json

import numpy as np
import pandas as pd

from src.risk_explainer import (
    explain_transaction_risk,
    row_to_safe_dict,
    template_explain_transaction_risk,
)
from src.safety import get_disclaimer


def make_row():
    return pd.Series(
        {
            "date": pd.Timestamp("2026-06-07"),
            "description": "Unknown online purchase",
            "merchant": "Unknown Store",
            "amount": np.float64(-980.0),
            "abs_amount": np.float64(980.0),
            "category": "other",
            "account": "credit_card",
            "anomaly_branch": "rule",
            "anomaly_type": "rare_merchant",
            "risk_level": "medium",
            "reason": "商户出现频率较低且金额较高。",
            "recommended_action": "请核查原始交易凭证。",
        }
    )


def test_row_to_safe_dict_handles_pandas_series_and_json_serializes():
    safe_row = row_to_safe_dict(make_row())

    assert safe_row["date"] == "2026-06-07T00:00:00"
    assert isinstance(safe_row["amount"], float)
    json.dumps(safe_row, ensure_ascii=False)


def test_template_explain_transaction_risk_returns_required_schema():
    result = template_explain_transaction_risk(make_row())

    assert isinstance(result, dict)
    assert result["risk_summary"]
    assert isinstance(result["possible_reasons"], list)
    assert isinstance(result["recommended_actions"], list)
    assert result["disclaimer"] == get_disclaimer()


def test_explain_transaction_risk_with_use_llm_false_uses_template(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-that-should-not-be-used")

    result = explain_transaction_risk(make_row(), use_llm=False)

    assert result["disclaimer"] == get_disclaimer()
    assert result["risk_summary"]
