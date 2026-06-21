import pandas as pd


def _normalize_invoices(invoices_df):
    invoices_df = invoices_df.copy()
    if invoices_df.empty:
        return invoices_df

    if "status" in invoices_df.columns:
        invoices_df["status"] = invoices_df["status"].astype(str).str.lower()
    if "due_date" in invoices_df.columns:
        invoices_df["due_date"] = pd.to_datetime(invoices_df["due_date"])
    if "amount" in invoices_df.columns:
        invoices_df["amount"] = pd.to_numeric(invoices_df["amount"])

    return invoices_df


def _get_reference_date(reference_date=None):
    if reference_date is None:
        return pd.Timestamp.today().normalize()
    return pd.to_datetime(reference_date).normalize()


def get_overdue_invoices(invoices_df, reference_date=None):
    """
    Return invoices that are explicitly overdue or past due and not paid.
    """
    invoices_df = _normalize_invoices(invoices_df)
    if invoices_df.empty:
        return invoices_df

    reference_date = _get_reference_date(reference_date)
    status = invoices_df["status"] if "status" in invoices_df.columns else ""
    due_date = invoices_df["due_date"] if "due_date" in invoices_df.columns else reference_date

    overdue_mask = (status == "overdue") | ((due_date < reference_date) & (status != "paid"))
    return invoices_df[overdue_mask].sort_values("due_date").reset_index(drop=True)


def get_upcoming_invoices(invoices_df, days=7, reference_date=None):
    """
    Return unpaid invoices due from reference_date through reference_date + days.
    """
    invoices_df = _normalize_invoices(invoices_df)
    if invoices_df.empty:
        return invoices_df

    reference_date = _get_reference_date(reference_date)
    end_date = reference_date + pd.Timedelta(days=days)
    status = invoices_df["status"] if "status" in invoices_df.columns else ""
    due_date = invoices_df["due_date"] if "due_date" in invoices_df.columns else reference_date

    upcoming_mask = (
        (status != "paid") & (due_date >= reference_date) & (due_date <= end_date)
    )
    return invoices_df[upcoming_mask].sort_values("due_date").reset_index(drop=True)


def compute_invoice_summary(invoices_df, reference_date=None) -> dict:
    """
    Compute invoice amount and count metrics.
    """
    invoices_df = _normalize_invoices(invoices_df)
    if invoices_df.empty or "amount" not in invoices_df.columns:
        return {
            "total_invoice_amount": 0.0,
            "paid_invoice_amount": 0.0,
            "unpaid_invoice_amount": 0.0,
            "overdue_invoice_amount": 0.0,
            "invoice_count": 0,
            "paid_invoice_count": 0,
            "unpaid_invoice_count": 0,
            "overdue_invoice_count": 0,
            "due_7d_amount": 0.0,
            "due_30d_amount": 0.0,
        }

    paid_df = invoices_df[invoices_df["status"] == "paid"]
    unpaid_df = invoices_df[invoices_df["status"] == "unpaid"]
    overdue_df = get_overdue_invoices(invoices_df, reference_date=reference_date)
    upcoming_7d_df = get_upcoming_invoices(invoices_df, days=7, reference_date=reference_date)
    upcoming_30d_df = get_upcoming_invoices(invoices_df, days=30, reference_date=reference_date)

    return {
        "total_invoice_amount": float(invoices_df["amount"].sum()),
        "paid_invoice_amount": float(paid_df["amount"].sum()),
        "unpaid_invoice_amount": float(unpaid_df["amount"].sum()),
        "overdue_invoice_amount": float(overdue_df["amount"].sum()),
        "invoice_count": int(len(invoices_df)),
        "paid_invoice_count": int(len(paid_df)),
        "unpaid_invoice_count": int(len(unpaid_df)),
        "overdue_invoice_count": int(len(overdue_df)),
        "due_7d_amount": float(upcoming_7d_df["amount"].sum()),
        "due_30d_amount": float(upcoming_30d_df["amount"].sum()),
    }


def analyze_invoices(invoices_df, reference_date=None) -> dict:
    """
    Run all invoice analysis functions and return one result object.
    """
    invoices_df = _normalize_invoices(invoices_df)
    return {
        "summary": compute_invoice_summary(invoices_df, reference_date=reference_date),
        "upcoming_7d": get_upcoming_invoices(
            invoices_df,
            days=7,
            reference_date=reference_date,
        ),
        "upcoming_30d": get_upcoming_invoices(
            invoices_df,
            days=30,
            reference_date=reference_date,
        ),
        "overdue": get_overdue_invoices(invoices_df, reference_date=reference_date),
    }
