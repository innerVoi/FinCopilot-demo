from pathlib import Path

import pandas as pd


TRANSACTION_COLUMNS = ["date", "description", "merchant", "amount", "type", "account"]
INVOICE_COLUMNS = ["invoice_id", "vendor", "due_date", "amount", "status", "category"]
GOAL_COLUMNS = [
    "goal_id",
    "goal_name",
    "target_amount",
    "current_amount",
    "due_date",
    "priority",
]


def _read_csv(file_or_path):
    """Read a CSV from either an uploaded file object or a local path."""
    if isinstance(file_or_path, (str, Path)) and not Path(file_or_path).exists():
        raise FileNotFoundError("Default sample data was not found. Check the data/ directory.")
    return pd.read_csv(file_or_path)


def _check_required_columns(df, required_columns, dataset_name):
    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        raise ValueError(f"{dataset_name} is missing required columns: {', '.join(missing_columns)}")


def _convert_date_column(df, column_name):
    try:
        df[column_name] = pd.to_datetime(df[column_name], format="%Y-%m-%d")
    except (TypeError, ValueError):
        raise ValueError("Date field format is invalid. Use YYYY-MM-DD format.") from None


def _convert_amount_column(df, column_name):
    try:
        df[column_name] = pd.to_numeric(df[column_name])
    except (TypeError, ValueError):
        raise ValueError("Amount field format is invalid. Make sure the amount field is numeric.") from None


def load_transactions(file_or_path):
    """Load and lightly standardize transaction CSV data."""
    transactions_df = _read_csv(file_or_path)
    _check_required_columns(transactions_df, TRANSACTION_COLUMNS, "Transactions")
    _convert_date_column(transactions_df, "date")
    _convert_amount_column(transactions_df, "amount")

    transactions_df["month"] = transactions_df["date"].dt.to_period("M").astype(str)
    transactions_df["abs_amount"] = transactions_df["amount"].abs()
    transactions_df["is_expense"] = transactions_df["amount"] < 0
    transactions_df["is_income"] = transactions_df["amount"] > 0

    return transactions_df


def load_invoices(file_or_path):
    """Load and lightly standardize invoice CSV data."""
    invoices_df = _read_csv(file_or_path)
    _check_required_columns(invoices_df, INVOICE_COLUMNS, "Invoices")
    _convert_date_column(invoices_df, "due_date")
    _convert_amount_column(invoices_df, "amount")

    return invoices_df


def load_goals(file_or_path):
    """Load and lightly standardize financial goal CSV data."""
    goals_df = _read_csv(file_or_path)
    _check_required_columns(goals_df, GOAL_COLUMNS, "Goals")
    _convert_amount_column(goals_df, "target_amount")
    _convert_amount_column(goals_df, "current_amount")
    _convert_date_column(goals_df, "due_date")

    return goals_df
