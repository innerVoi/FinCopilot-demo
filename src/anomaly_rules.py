import pandas as pd


ANOMALY_COLUMNS = [
    "date",
    "description",
    "merchant",
    "amount",
    "abs_amount",
    "type",
    "account",
    "category",
    "anomaly_branch",
    "anomaly_type",
    "risk_level",
    "reason",
    "recommended_action",
    "anomaly_key",
]


def _empty_anomalies():
    return pd.DataFrame(columns=ANOMALY_COLUMNS)


def _prepare_transactions(transactions_df):
    transactions_df = transactions_df.copy()
    if transactions_df.empty:
        return transactions_df

    if "amount" in transactions_df.columns:
        transactions_df["amount"] = pd.to_numeric(transactions_df["amount"])
    if "abs_amount" not in transactions_df.columns and "amount" in transactions_df.columns:
        transactions_df["abs_amount"] = transactions_df["amount"].abs()
    if "date" in transactions_df.columns:
        transactions_df["date"] = pd.to_datetime(transactions_df["date"])
    if "category" not in transactions_df.columns:
        transactions_df["category"] = "other"
    if "type" not in transactions_df.columns:
        transactions_df["type"] = transactions_df["amount"].apply(
            lambda amount: "expense" if amount < 0 else "income"
        )
    if "account" not in transactions_df.columns:
        transactions_df["account"] = "unknown"

    return transactions_df


def _expense_rows(transactions_df):
    transactions_df = _prepare_transactions(transactions_df)
    if transactions_df.empty or "amount" not in transactions_df.columns:
        return transactions_df.iloc[0:0].copy()
    return transactions_df[transactions_df["amount"] < 0].copy()


def _build_anomaly_row(row, anomaly_type, risk_level, reason, recommended_action):
    anomaly_row = {
        "date": row.get("date"),
        "description": row.get("description", ""),
        "merchant": row.get("merchant", ""),
        "amount": row.get("amount", 0.0),
        "abs_amount": row.get("abs_amount", abs(row.get("amount", 0.0))),
        "type": row.get("type", "expense"),
        "account": row.get("account", "unknown"),
        "category": row.get("category", "other"),
        "anomaly_branch": "rule",
        "anomaly_type": anomaly_type,
        "risk_level": risk_level,
        "reason": reason,
        "recommended_action": recommended_action,
    }
    anomaly_row["anomaly_key"] = (
        f"{anomaly_row['date']}|{anomaly_row['merchant']}|"
        f"{anomaly_row['amount']}|{anomaly_type}"
    )
    return anomaly_row


def _rows_to_df(rows):
    if not rows:
        return _empty_anomalies()
    return pd.DataFrame(rows).reindex(columns=ANOMALY_COLUMNS)


def detect_large_amount_anomalies(
    transactions_df,
    min_amount=300.0,
    std_multiplier=2.0,
):
    """
    Detect expenses that are unusually large compared with their category.
    """
    expenses_df = _expense_rows(transactions_df)
    if expenses_df.empty:
        return _empty_anomalies()

    anomaly_rows = []
    for category, category_df in expenses_df.groupby("category"):
        if len(category_df) < 3:
            continue

        mean_amount = category_df["abs_amount"].mean()
        std_amount = category_df["abs_amount"].std(ddof=0)
        if pd.isna(std_amount) or std_amount == 0:
            continue

        threshold = mean_amount + std_multiplier * std_amount
        severe_threshold = mean_amount + 3 * std_amount
        ratio_threshold = mean_amount * 2.5

        for _, row in category_df.iterrows():
            abs_amount = row["abs_amount"]
            is_statistical_outlier = abs_amount > threshold
            is_large_relative_to_average = abs_amount >= ratio_threshold
            if abs_amount < min_amount or not (
                is_statistical_outlier or is_large_relative_to_average
            ):
                continue

            risk_level = "high" if abs_amount >= severe_threshold else "medium"
            reason = (
                f"This expense amount is {abs_amount:.2f}, higher than the usual level "
                f"for category {category}. Review whether it is a one-off large purchase, "
                "miscategorized item, or unusual charge."
            )
            recommended_action = (
                "Review the source transaction record and confirm whether this expense is valid, "
                "should be recategorized, or is a one-off large expense."
            )
            anomaly_rows.append(
                _build_anomaly_row(
                    row,
                    "large_amount_anomaly",
                    risk_level,
                    reason,
                    recommended_action,
                )
            )

    return _rows_to_df(anomaly_rows)


def detect_duplicate_charges(
    transactions_df,
    days_window=7,
    amount_tolerance=2.0,
    min_amount=5.0,
):
    """
    Detect possible duplicate charges from the same merchant.
    """
    expenses_df = _expense_rows(transactions_df)
    if expenses_df.empty or "merchant" not in expenses_df.columns:
        return _empty_anomalies()

    anomaly_rows = []
    expenses_df = expenses_df.sort_values(["merchant", "date", "abs_amount"])
    for merchant, merchant_df in expenses_df.groupby("merchant"):
        merchant_df = merchant_df.reset_index(drop=True)
        for current_index in range(1, len(merchant_df)):
            current_row = merchant_df.iloc[current_index]
            if current_row["abs_amount"] <= min_amount:
                continue

            previous_rows = merchant_df.iloc[:current_index]
            nearby_rows = previous_rows[
                (current_row["date"] - previous_rows["date"]).dt.days.between(
                    0,
                    days_window,
                )
                & (
                    (current_row["abs_amount"] - previous_rows["abs_amount"]).abs()
                    <= amount_tolerance
                )
            ]
            if nearby_rows.empty:
                continue

            reason = (
                f"{merchant} has multiple charges with similar amounts within {days_window} days. "
                "This may be a normal subscription renewal or a duplicate charge."
            )
            recommended_action = "Check this merchant's invoice or subscription record to confirm whether duplicate billing occurred."
            anomaly_rows.append(
                _build_anomaly_row(
                    current_row,
                    "duplicate_charge",
                    "medium",
                    reason,
                    recommended_action,
                )
            )

    return _rows_to_df(anomaly_rows)


def detect_rare_merchant_anomalies(transactions_df, min_amount=300.0, max_count=1):
    """
    Detect large expenses from merchants that appear rarely in the dataset.
    """
    expenses_df = _expense_rows(transactions_df)
    if expenses_df.empty or "merchant" not in expenses_df.columns:
        return _empty_anomalies()

    merchant_counts = expenses_df["merchant"].value_counts()
    anomaly_rows = []
    for _, row in expenses_df.iterrows():
        merchant = row.get("merchant", "")
        abs_amount = row["abs_amount"]
        if merchant_counts.get(merchant, 0) > max_count or abs_amount < min_amount:
            continue

        risk_level = "high" if abs_amount >= 1000 else "medium"
        reason = (
            "This merchant appears rarely in the current data and the transaction amount is relatively high, "
            "so it is flagged as a rare-merchant expense."
        )
        recommended_action = "Confirm whether this is a known merchant and whether the transaction was authorized."
        anomaly_rows.append(
            _build_anomaly_row(
                row,
                "rare_merchant",
                risk_level,
                reason,
                recommended_action,
            )
        )

    return _rows_to_df(anomaly_rows)


def detect_category_spikes(
    transactions_df,
    share_threshold=0.35,
    top_k_per_category=3,
):
    """
    Detect categories that take an unusually large share of total expenses.
    """
    expenses_df = _expense_rows(transactions_df)
    if expenses_df.empty:
        return _empty_anomalies()

    total_expense = expenses_df["abs_amount"].sum()
    if total_expense == 0:
        return _empty_anomalies()

    anomaly_rows = []
    category_amounts = expenses_df.groupby("category")["abs_amount"].sum()
    for category, category_amount in category_amounts.items():
        expense_share = category_amount / total_expense
        if expense_share < share_threshold:
            continue

        risk_level = "high" if expense_share >= 0.50 else "medium"
        category_rows = expenses_df[expenses_df["category"] == category].nlargest(
            top_k_per_category,
            "abs_amount",
        )
        for _, row in category_rows.iterrows():
            reason = (
                f"Category {category} accounts for {expense_share:.1%} of total expenses in this period, "
                "which may pressure budget or cash flow."
            )
            recommended_action = (
                "Review whether large expenses in this category are necessary and whether budget allocation should be adjusted."
            )
            anomaly_rows.append(
                _build_anomaly_row(
                    row,
                    "category_spike",
                    risk_level,
                    reason,
                    recommended_action,
                )
            )

    return _rows_to_df(anomaly_rows)


def detect_unusual_time_anomalies(transactions_df, min_amount=200.0):
    """
    Detect large weekend expenses.
    """
    expenses_df = _expense_rows(transactions_df)
    if expenses_df.empty or "date" not in expenses_df.columns:
        return _empty_anomalies()

    weekend_df = expenses_df[
        (expenses_df["date"].dt.weekday >= 5) & (expenses_df["abs_amount"] >= min_amount)
    ]
    anomaly_rows = []
    for _, row in weekend_df.iterrows():
        risk_level = "high" if row["abs_amount"] >= 500 else "medium"
        reason = "This transaction occurred on a weekend and has a relatively high amount, so it may need review."
        recommended_action = "Confirm whether this large weekend expense was authorized and planned."
        anomaly_rows.append(
            _build_anomaly_row(
                row,
                "unusual_time",
                risk_level,
                reason,
                recommended_action,
            )
        )

    return _rows_to_df(anomaly_rows)


def detect_invoice_pressure(
    invoice_result,
    reference_date=None,
    due_30d_threshold=2000.0,
):
    """
    Detect invoice pressure from upcoming or overdue invoices.
    """
    if not invoice_result:
        return _empty_anomalies()

    summary = invoice_result.get("summary", {})
    due_30d_amount = float(summary.get("due_30d_amount", 0.0))
    overdue_invoice_amount = float(summary.get("overdue_invoice_amount", 0.0))
    if due_30d_amount < due_30d_threshold and overdue_invoice_amount <= 0:
        return _empty_anomalies()

    if reference_date is None:
        reference_date = pd.Timestamp.today().normalize()
    reference_date = pd.to_datetime(reference_date)

    amount = overdue_invoice_amount if overdue_invoice_amount > 0 else due_30d_amount
    risk_level = (
        "high"
        if overdue_invoice_amount > 0 and due_30d_amount >= due_30d_threshold
        else "medium"
    )
    if overdue_invoice_amount > 0 and due_30d_amount >= due_30d_threshold:
        reason = "Invoices due in the next 30 days are high and overdue invoices exist, which may pressure cash flow."
    elif due_30d_amount >= due_30d_threshold:
        reason = "Invoices due in the next 30 days are high and may pressure cash flow."
    else:
        reason = "There are overdue invoices, which may affect payment planning and cash-flow stability."

    row = {
        "date": reference_date,
        "description": "Invoice pressure detected",
        "merchant": "Invoice Summary",
        "amount": -amount,
        "abs_amount": amount,
        "type": "expense",
        "account": "business",
        "category": "invoice",
    }
    recommended_action = "Prioritize overdue invoice review and plan payments for the next 30 days."
    return _rows_to_df(
        [
            _build_anomaly_row(
                row,
                "invoice_pressure",
                risk_level,
                reason,
                recommended_action,
            )
        ]
    )


def run_rule_based_anomaly_detection(
    transactions_df,
    invoice_result=None,
    reference_date=None,
):
    """
    Run all rule/statistical anomaly checks and return one DataFrame.
    """
    detection_results = [
        detect_large_amount_anomalies(transactions_df),
        detect_duplicate_charges(transactions_df),
        detect_rare_merchant_anomalies(transactions_df),
        detect_category_spikes(transactions_df),
        detect_unusual_time_anomalies(transactions_df),
        detect_invoice_pressure(invoice_result, reference_date=reference_date),
    ]
    non_empty_results = [df for df in detection_results if not df.empty]
    if not non_empty_results:
        return _empty_anomalies()

    anomalies_df = pd.concat(non_empty_results, ignore_index=True)
    anomalies_df = anomalies_df.drop_duplicates(subset=["anomaly_key"])
    risk_order = {"high": 0, "medium": 1, "low": 2}
    anomalies_df["risk_sort"] = anomalies_df["risk_level"].map(risk_order).fillna(99)
    anomalies_df = anomalies_df.sort_values(
        ["risk_sort", "date", "merchant", "anomaly_type"],
        ascending=[True, True, True, True],
    )
    return anomalies_df.drop(columns=["risk_sort"]).reset_index(drop=True)
