import pandas as pd

from src.categorizer import add_transaction_categories


FIXED_EXPENSE_CATEGORIES = [
    "rent",
    "subscription",
    "software",
    "utility",
    "insurance",
    "payroll",
]


def _ensure_category(transactions_df):
    if "category" in transactions_df.columns:
        return transactions_df.copy()
    return add_transaction_categories(transactions_df)


def _expense_rows(transactions_df):
    if transactions_df.empty or "amount" not in transactions_df.columns:
        return transactions_df.iloc[0:0].copy()
    return transactions_df[transactions_df["amount"] < 0].copy()


def compute_category_spending(transactions_df):
    """
    Summarize expense amount by category. Expense amounts are positive numbers.
    """
    transactions_df = _ensure_category(transactions_df)
    columns = ["category", "expense_amount", "transaction_count", "expense_share"]
    expenses_df = _expense_rows(transactions_df)
    if expenses_df.empty:
        return pd.DataFrame(columns=columns)

    expenses_df["expense_amount"] = expenses_df["amount"].abs()
    category_df = (
        expenses_df.groupby("category", as_index=False)
        .agg(
            expense_amount=("expense_amount", "sum"),
            transaction_count=("amount", "count"),
        )
        .sort_values("expense_amount", ascending=False)
        .reset_index(drop=True)
    )

    total_expense = category_df["expense_amount"].sum()
    category_df["expense_share"] = (
        category_df["expense_amount"] / total_expense if total_expense else 0
    )
    return category_df[columns]


def compute_monthly_summary(transactions_df):
    """
    Summarize income, expense, and net cashflow by month.
    """
    columns = ["month", "income", "expense", "net_cashflow"]
    if transactions_df.empty or "amount" not in transactions_df.columns:
        return pd.DataFrame(columns=columns)

    monthly_df = transactions_df.copy()
    if "month" not in monthly_df.columns:
        if "date" not in monthly_df.columns:
            return pd.DataFrame(columns=columns)
        monthly_df["date"] = pd.to_datetime(monthly_df["date"])
        monthly_df["month"] = monthly_df["date"].dt.to_period("M").astype(str)

    monthly_df["income"] = monthly_df["amount"].where(monthly_df["amount"] > 0, 0)
    monthly_df["expense"] = monthly_df["amount"].where(monthly_df["amount"] < 0, 0).abs()

    result_df = (
        monthly_df.groupby("month", as_index=False)
        .agg(income=("income", "sum"), expense=("expense", "sum"))
        .sort_values("month")
        .reset_index(drop=True)
    )
    result_df["net_cashflow"] = result_df["income"] - result_df["expense"]
    return result_df[columns]


def compute_budget_summary(transactions_df) -> dict:
    """
    Compute top-level income and expense metrics.
    """
    transactions_df = _ensure_category(transactions_df)
    if transactions_df.empty or "amount" not in transactions_df.columns:
        return {
            "total_income": 0.0,
            "total_expense": 0.0,
            "net_cashflow": 0.0,
            "expense_income_ratio": 0.0,
            "transaction_count": 0,
            "income_transaction_count": 0,
            "expense_transaction_count": 0,
            "largest_expense": 0.0,
            "top_expense_category": "none",
            "fixed_expense_ratio": 0.0,
        }

    income_df = transactions_df[transactions_df["amount"] > 0]
    expense_df = _expense_rows(transactions_df)
    total_income = float(income_df["amount"].sum())
    total_expense = float(expense_df["amount"].abs().sum())
    net_cashflow = total_income - total_expense
    expense_income_ratio = total_expense / total_income if total_income else 0.0
    largest_expense = float(expense_df["amount"].abs().max()) if not expense_df.empty else 0.0

    category_spending_df = compute_category_spending(transactions_df)
    top_expense_category = (
        str(category_spending_df.iloc[0]["category"])
        if not category_spending_df.empty
        else "none"
    )

    fixed_expense_amount = 0.0
    if not expense_df.empty:
        fixed_expense_amount = float(
            expense_df[expense_df["category"].isin(FIXED_EXPENSE_CATEGORIES)][
                "amount"
            ]
            .abs()
            .sum()
        )
    fixed_expense_ratio = fixed_expense_amount / total_expense if total_expense else 0.0

    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "net_cashflow": net_cashflow,
        "expense_income_ratio": expense_income_ratio,
        "transaction_count": int(len(transactions_df)),
        "income_transaction_count": int(len(income_df)),
        "expense_transaction_count": int(len(expense_df)),
        "largest_expense": largest_expense,
        "top_expense_category": top_expense_category,
        "fixed_expense_ratio": fixed_expense_ratio,
    }


def analyze_budget(transactions_df) -> dict:
    """
    Run all budget analysis functions and return one result object.
    """
    transactions_df = _ensure_category(transactions_df)
    return {
        "summary": compute_budget_summary(transactions_df),
        "category_spending": compute_category_spending(transactions_df),
        "monthly_summary": compute_monthly_summary(transactions_df),
    }
