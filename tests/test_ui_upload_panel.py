import pandas as pd

from ui.upload_panel import get_data_status_summary


def test_get_data_status_summary_handles_empty_inputs():
    summary = get_data_status_summary()
    assert summary["has_transactions"] is False
    assert summary["has_invoices"] is False
    assert summary["has_goals"] is False
    assert summary["transactions_count"] == 0


def test_get_data_status_summary_handles_non_empty_dataframes():
    summary = get_data_status_summary(
        transactions_df=pd.DataFrame([{"amount": 1}]),
        invoices_df=pd.DataFrame([{"amount": 2}, {"amount": 3}]),
        goals_df=pd.DataFrame([{"goal": "cash"}]),
    )
    assert summary["has_transactions"] is True
    assert summary["has_invoices"] is True
    assert summary["has_goals"] is True
    assert summary["transactions_count"] == 1
    assert summary["invoices_count"] == 2
    assert summary["goals_count"] == 1
