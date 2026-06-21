import numpy as np
import pandas as pd

from src.anomaly_model import (
    FEATURE_COLUMNS,
    assign_risk_levels,
    build_model_features,
    normalize_scores,
    run_lof_detection,
)


def make_transactions_df():
    return pd.DataFrame(
        [
            {
                "date": "2026-06-01",
                "description": "Coffee",
                "merchant": "Cafe A",
                "amount": -5.0,
                "category": "food",
                "account": "credit_card",
            },
            {
                "date": "2026-06-02",
                "description": "Lunch",
                "merchant": "Cafe B",
                "amount": -12.0,
                "category": "food",
                "account": "credit_card",
            },
            {
                "date": "2026-06-03",
                "description": "Dinner",
                "merchant": "Cafe C",
                "amount": -18.0,
                "category": "food",
                "account": "credit_card",
            },
            {
                "date": "2026-06-04",
                "description": "Cloud",
                "merchant": "AWS",
                "amount": -220.0,
                "category": "software",
                "account": "business",
            },
            {
                "date": "2026-06-05",
                "description": "Salary",
                "merchant": "Company Inc",
                "amount": 4800.0,
                "category": "salary",
                "account": "checking",
            },
            {
                "date": "2026-06-06",
                "description": "Unknown purchase",
                "merchant": "Unknown Store",
                "amount": -980.0,
                "category": "other",
                "account": "credit_card",
            },
        ]
    )


def test_build_model_features_returns_numeric_complete_features():
    feature_df, enriched_df = build_model_features(make_transactions_df())

    assert set(FEATURE_COLUMNS).issubset(feature_df.columns)
    assert len(feature_df) == len(enriched_df)
    assert feature_df.isna().sum().sum() == 0
    assert all(np.issubdtype(dtype, np.number) for dtype in feature_df.dtypes)


def test_normalize_scores_min_max_and_constant_values():
    assert np.allclose(normalize_scores([2, 4, 6]), [0.0, 0.5, 1.0])
    assert np.allclose(normalize_scores([3, 3, 3]), [0.0, 0.0, 0.0])


def test_assign_risk_levels_is_stable():
    risk_levels = assign_risk_levels([0.1, 0.2, 0.3, 0.8, 0.95])

    assert risk_levels[-1] == "high"
    assert risk_levels[-2] in {"medium", "high"}
    assert risk_levels[0] == "low"


def test_run_lof_detection_returns_model_columns_and_sorted_scores():
    result = run_lof_detection(make_transactions_df(), n_neighbors=3)

    required_columns = {
        "anomaly_branch",
        "model_name",
        "anomaly_score",
        "risk_level",
        "model_evidence",
    }
    assert required_columns.issubset(result.columns)
    assert set(result["anomaly_branch"]) == {"model"}
    assert set(result["model_name"]) == {"LOF"}
    assert result["anomaly_score"].between(0, 1).all()
    assert set(result["risk_level"]).issubset({"low", "medium", "high"})
    assert result["anomaly_score"].is_monotonic_decreasing


def test_run_lof_detection_handles_small_samples():
    small_df = make_transactions_df().head(2)

    result = run_lof_detection(small_df)

    assert len(result) == len(small_df)
    assert (result["anomaly_score"] == 0).all()
    assert set(result["risk_level"]) == {"low"}
    assert result["model_evidence"].str.contains("样本数量过少").all()
