import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from src.safety import get_disclaimer


PROMPT_PATH = Path("prompts/risk_explanation_prompt.txt")
DEFAULT_MODEL = "gpt-5.4-mini"
EXPLANATION_FIELDS = [
    "date",
    "description",
    "merchant",
    "amount",
    "abs_amount",
    "category",
    "account",
    "anomaly_branch",
    "anomaly_type",
    "risk_level",
    "reason",
    "recommended_action",
    "model_name",
    "anomaly_score",
    "model_evidence",
]


def has_openai_api_key() -> bool:
    """
    Check whether OPENAI_API_KEY is configured.
    """
    return bool(os.getenv("OPENAI_API_KEY"))


def _to_json_safe_value(value):
    if pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def row_to_safe_dict(row) -> dict:
    """
    Convert a pandas Series or dict into a JSON-safe, limited dict.
    """
    if isinstance(row, pd.Series):
        raw_data = row.to_dict()
    elif isinstance(row, dict):
        raw_data = row
    else:
        raw_data = dict(row)

    safe_data = {}
    for field in EXPLANATION_FIELDS:
        if field in raw_data:
            safe_data[field] = _to_json_safe_value(raw_data[field])
    return safe_data


def template_explain_transaction_risk(row) -> dict:
    """
    Generate a deterministic fallback explanation for one anomaly row.
    """
    safe_row = row_to_safe_dict(row)
    branch = safe_row.get("anomaly_branch") or "unknown"
    risk_level = safe_row.get("risk_level") or "unknown"
    merchant = safe_row.get("merchant") or "this merchant"
    amount = safe_row.get("amount")
    anomaly_type = safe_row.get("anomaly_type") or "model_score"

    risk_summary = (
        f"This record for {merchant} was flagged as {risk_level} risk. "
        "Review its source documents, bills, or categorization."
    )
    if amount is not None:
        risk_summary = (
            f"The {amount} record for {merchant} was flagged as {risk_level} risk. "
            "Review its source documents, bills, or categorization."
        )

    possible_reasons = [
        f"The anomaly branch is {branch}.",
        f"The risk level is {risk_level}.",
    ]
    if safe_row.get("reason"):
        possible_reasons.append(str(safe_row["reason"]))
    elif safe_row.get("model_evidence"):
        possible_reasons.append(f"Model evidence: {safe_row['model_evidence']}")
    else:
        possible_reasons.append(f"The system identified anomaly type {anomaly_type}.")

    recommended_actions = [
        "Review the original transaction evidence.",
        "Confirm whether this transaction was authorized by the owner or business.",
        "Reclassify the transaction if needed, or record it as a one-off expense and update the budget.",
    ]
    if safe_row.get("recommended_action"):
        recommended_actions.insert(0, str(safe_row["recommended_action"]))

    return {
        "risk_summary": risk_summary,
        "possible_reasons": possible_reasons,
        "recommended_actions": recommended_actions,
        "disclaimer": get_disclaimer(),
    }


def _load_prompt(path):
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _ensure_explanation_schema(result, fallback_row):
    if not isinstance(result, dict):
        return template_explain_transaction_risk(fallback_row)

    explanation = template_explain_transaction_risk(fallback_row)
    risk_summary = result.get("risk_summary")
    possible_reasons = result.get("possible_reasons")
    recommended_actions = result.get("recommended_actions")
    disclaimer = result.get("disclaimer") or get_disclaimer()

    if isinstance(risk_summary, str) and risk_summary.strip():
        explanation["risk_summary"] = risk_summary.strip()
    if isinstance(possible_reasons, list):
        explanation["possible_reasons"] = [str(item) for item in possible_reasons]
    if isinstance(recommended_actions, list):
        explanation["recommended_actions"] = [
            str(item) for item in recommended_actions
        ]
    explanation["disclaimer"] = disclaimer
    if get_disclaimer() not in explanation["disclaimer"]:
        explanation["disclaimer"] = get_disclaimer()
    return explanation


def llm_explain_transaction_risk(row, model=None) -> dict:
    """
    Try to call the OpenAI API, falling back to the deterministic template.
    """
    if not has_openai_api_key():
        return template_explain_transaction_risk(row)

    try:
        from openai import OpenAI

        client = OpenAI()
        model = model or os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
        system_prompt = _load_prompt(PROMPT_PATH)
        safe_row = row_to_safe_dict(row)
        response = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(safe_row, ensure_ascii=False),
                },
            ],
        )
        result = json.loads(response.output_text)
        return _ensure_explanation_schema(result, row)
    except Exception:
        return template_explain_transaction_risk(row)


def explain_transaction_risk(row, use_llm=True) -> dict:
    """
    Public entry point for transaction risk explanations.
    """
    if use_llm and has_openai_api_key():
        return llm_explain_transaction_risk(row)
    return template_explain_transaction_risk(row)
