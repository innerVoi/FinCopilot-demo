import pandas as pd

from src.categorizer import add_transaction_categories, classify_transaction


def test_common_merchants_are_classified():
    rows = [
        ({"description": "Coffee", "merchant": "Starbucks"}, "food"),
        ({"description": "Cloud subscription", "merchant": "AWS"}, "software"),
        ({"description": "Netflix subscription", "merchant": "Netflix"}, "subscription"),
        ({"description": "Vendor invoice payment", "merchant": "Vendor B"}, "supplier"),
        ({"description": "Mystery item", "merchant": "Unknown Shop"}, "other"),
    ]

    for row, expected_category in rows:
        result = classify_transaction(row)
        assert result["category"] == expected_category


def test_add_transaction_categories_adds_expected_columns():
    df = pd.DataFrame(
        [
            {"description": "Coffee", "merchant": "Starbucks", "amount": -6.5},
            {"description": "Tax payment", "merchant": "IRS", "amount": -700},
        ]
    )

    result = add_transaction_categories(df)

    assert {"category", "category_confidence", "category_reason"}.issubset(result.columns)
    assert result.loc[0, "category"] == "food"
    assert result.loc[1, "category"] == "tax"
