import pandas as pd


CATEGORY_RULES = {
    "salary": ["salary", "payroll income", "monthly salary"],
    "client_payment": ["client payment", "invoice paid", "client"],
    "rent": ["rent", "apartment", "office rent", "lease"],
    "food": [
        "coffee",
        "restaurant",
        "lunch",
        "dinner",
        "chipotle",
        "starbucks",
        "grocery",
    ],
    "transport": ["uber", "lyft", "metro", "gas", "shell", "ride sharing"],
    "software": ["aws", "openai", "adobe", "cloud", "software", "api"],
    "subscription": ["netflix", "spotify", "subscription"],
    "supplier": ["vendor", "supplier"],
    "utility": ["electricity", "utility", "internet", "phone"],
    "tax": ["tax", "irs"],
    "insurance": ["insurance"],
    "office": ["office supplies", "office depot", "book purchase"],
    "payroll": ["gusto", "payroll service"],
}


def classify_transaction(row) -> dict:
    """
    Classify one transaction using simple keyword rules.

    Returns a dict with category, category_confidence, and category_reason.
    """
    description = str(row.get("description", "")).lower()
    merchant = str(row.get("merchant", "")).lower()
    searchable_text = f"{description} {merchant}"

    for category, keywords in CATEGORY_RULES.items():
        for keyword in keywords:
            if keyword in searchable_text:
                return {
                    "category": category,
                    "category_confidence": 0.9,
                    "category_reason": (
                        f"Matched keyword '{keyword}' in merchant/description."
                    ),
                }

    return {
        "category": "other",
        "category_confidence": 0.3,
        "category_reason": "No keyword rule matched.",
    }


def add_transaction_categories(transactions_df):
    """
    Add category, category_confidence, and category_reason columns.
    """
    transactions_df = transactions_df.copy()
    if transactions_df.empty:
        transactions_df["category"] = []
        transactions_df["category_confidence"] = []
        transactions_df["category_reason"] = []
        return transactions_df

    classified_rows = transactions_df.apply(classify_transaction, axis=1)
    classified_df = pd.DataFrame(classified_rows.tolist(), index=transactions_df.index)
    transactions_df[["category", "category_confidence", "category_reason"]] = classified_df[
        ["category", "category_confidence", "category_reason"]
    ]
    return transactions_df
