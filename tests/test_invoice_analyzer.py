import pandas as pd

from src.invoice_analyzer import (
    analyze_invoices,
    compute_invoice_summary,
    get_overdue_invoices,
    get_upcoming_invoices,
)


def make_invoices_df():
    return pd.DataFrame(
        [
            {
                "invoice_id": "INV-001",
                "vendor": "Vendor A",
                "due_date": "2026-06-20",
                "amount": 100,
                "status": "paid",
                "category": "supplier",
            },
            {
                "invoice_id": "INV-002",
                "vendor": "Vendor B",
                "due_date": "2026-06-22",
                "amount": 200,
                "status": "unpaid",
                "category": "supplier",
            },
            {
                "invoice_id": "INV-003",
                "vendor": "Consultant",
                "due_date": "2026-06-10",
                "amount": 300,
                "status": "overdue",
                "category": "service",
            },
            {
                "invoice_id": "INV-004",
                "vendor": "Insurance",
                "due_date": "2026-07-10",
                "amount": 400,
                "status": "unpaid",
                "category": "insurance",
            },
        ]
    )


def test_invoice_summary_amounts_and_counts():
    summary = compute_invoice_summary(make_invoices_df(), reference_date="2026-06-20")

    assert summary["total_invoice_amount"] == 1000
    assert summary["paid_invoice_amount"] == 100
    assert summary["unpaid_invoice_amount"] == 600
    assert summary["overdue_invoice_amount"] == 300


def test_upcoming_and_overdue_invoices():
    invoices_df = make_invoices_df()

    upcoming_7d = get_upcoming_invoices(invoices_df, days=7, reference_date="2026-06-20")
    upcoming_30d = get_upcoming_invoices(invoices_df, days=30, reference_date="2026-06-20")
    overdue = get_overdue_invoices(invoices_df, reference_date="2026-06-20")

    assert len(upcoming_7d) == 1
    assert len(upcoming_30d) == 2
    assert len(overdue) == 1


def test_analyze_invoices_returns_expected_sections():
    result = analyze_invoices(make_invoices_df(), reference_date="2026-06-20")

    assert {"summary", "upcoming_7d", "upcoming_30d", "overdue"}.issubset(result.keys())
