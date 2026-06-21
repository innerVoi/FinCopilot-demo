import pandas as pd

from src.anomaly_rules import (
    detect_category_spikes,
    detect_duplicate_charges,
    detect_invoice_pressure,
    detect_large_amount_anomalies,
    detect_rare_merchant_anomalies,
    detect_unusual_time_anomalies,
    run_rule_based_anomaly_detection,
)


def test_detect_large_amount_anomalies():
    transactions_df = pd.DataFrame(
        [
            {"date": "2026-06-01", "merchant": "Cafe A", "amount": -20, "category": "food"},
            {"date": "2026-06-02", "merchant": "Cafe B", "amount": -25, "category": "food"},
            {"date": "2026-06-03", "merchant": "Cafe C", "amount": -30, "category": "food"},
            {"date": "2026-06-04", "merchant": "Cafe D", "amount": -600, "category": "food"},
        ]
    )

    result = detect_large_amount_anomalies(transactions_df)

    assert "large_amount_anomaly" in result["anomaly_type"].values
    assert result.iloc[0]["abs_amount"] == 600


def test_detect_duplicate_charges():
    transactions_df = pd.DataFrame(
        [
            {
                "date": "2026-06-08",
                "merchant": "Netflix",
                "amount": -19.99,
                "category": "subscription",
            },
            {
                "date": "2026-06-10",
                "merchant": "Netflix",
                "amount": -19.99,
                "category": "subscription",
            },
        ]
    )

    result = detect_duplicate_charges(transactions_df)

    assert len(result) == 1
    assert result.iloc[0]["anomaly_type"] == "duplicate_charge"


def test_detect_rare_merchant_anomalies():
    transactions_df = pd.DataFrame(
        [
            {
                "date": "2026-06-07",
                "merchant": "Unknown Store",
                "amount": -980,
                "category": "other",
            },
            {"date": "2026-06-08", "merchant": "Cafe", "amount": -20, "category": "food"},
        ]
    )

    result = detect_rare_merchant_anomalies(transactions_df)

    assert "rare_merchant" in result["anomaly_type"].values
    assert result.iloc[0]["merchant"] == "Unknown Store"


def test_detect_category_spikes():
    transactions_df = pd.DataFrame(
        [
            {
                "date": "2026-06-01",
                "merchant": "Vendor A",
                "amount": -1000,
                "category": "supplier",
            },
            {
                "date": "2026-06-02",
                "merchant": "Vendor B",
                "amount": -800,
                "category": "supplier",
            },
            {"date": "2026-06-03", "merchant": "Cafe", "amount": -100, "category": "food"},
            {
                "date": "2026-06-04",
                "merchant": "Metro",
                "amount": -100,
                "category": "transport",
            },
        ]
    )

    result = detect_category_spikes(transactions_df)

    assert "category_spike" in result["anomaly_type"].values
    assert set(result["category"]) == {"supplier"}


def test_detect_unusual_time_anomalies():
    transactions_df = pd.DataFrame(
        [
            {
                "date": "2026-06-07",
                "merchant": "Unknown Store",
                "amount": -300,
                "category": "other",
            }
        ]
    )

    result = detect_unusual_time_anomalies(transactions_df)

    assert len(result) == 1
    assert result.iloc[0]["anomaly_type"] == "unusual_time"


def test_detect_invoice_pressure():
    invoice_result = {
        "summary": {
            "due_30d_amount": 2500.0,
            "overdue_invoice_amount": 0.0,
        }
    }

    result = detect_invoice_pressure(invoice_result, reference_date="2026-06-20")

    assert len(result) == 1
    assert result.iloc[0]["anomaly_type"] == "invoice_pressure"


def test_run_rule_based_anomaly_detection_returns_required_columns():
    transactions_df = pd.DataFrame(
        [
            {
                "date": "2026-06-07",
                "description": "Unknown online purchase",
                "merchant": "Unknown Store",
                "amount": -980,
                "category": "other",
                "account": "credit_card",
            }
        ]
    )
    invoice_result = {
        "summary": {
            "due_30d_amount": 2500.0,
            "overdue_invoice_amount": 500.0,
        }
    }

    result = run_rule_based_anomaly_detection(
        transactions_df,
        invoice_result=invoice_result,
        reference_date="2026-06-20",
    )

    required_columns = {
        "date",
        "description",
        "merchant",
        "amount",
        "abs_amount",
        "category",
        "anomaly_branch",
        "anomaly_type",
        "risk_level",
        "reason",
        "recommended_action",
    }
    assert required_columns.issubset(result.columns)
    assert set(result["anomaly_branch"]) == {"rule"}
