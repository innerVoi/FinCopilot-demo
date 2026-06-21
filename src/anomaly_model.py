import numpy as np
import pandas as pd
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler


FEATURE_COLUMNS = [
    "abs_amount",
    "log_abs_amount",
    "day_of_week",
    "day_of_month",
    "is_weekend",
    "merchant_frequency",
    "category_frequency",
    "account_frequency",
    "amount_category_zscore",
    "is_expense",
    "is_income",
]


def build_model_features(transactions_df):
    """
    Build numeric features for LOF and return feature_df plus enriched_df.
    """
    df = transactions_df.copy()
    if df.empty:
        return pd.DataFrame(columns=FEATURE_COLUMNS), df

    if "date" not in df.columns:
        df["date"] = pd.Timestamp.today().normalize()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["date"] = df["date"].fillna(pd.Timestamp.today().normalize())

    if "amount" not in df.columns:
        df["amount"] = 0.0
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)

    if "merchant" not in df.columns:
        df["merchant"] = "unknown"
    df["merchant"] = df["merchant"].fillna("unknown").astype(str)

    if "category" not in df.columns:
        df["category"] = "other"
    df["category"] = df["category"].fillna("other").astype(str)

    if "account" not in df.columns:
        df["account"] = "unknown"
    df["account"] = df["account"].fillna("unknown").astype(str)

    if "abs_amount" not in df.columns:
        df["abs_amount"] = df["amount"].abs()
    df["abs_amount"] = pd.to_numeric(df["abs_amount"], errors="coerce").fillna(0.0)

    if "is_expense" not in df.columns:
        df["is_expense"] = df["amount"] < 0
    if "is_income" not in df.columns:
        df["is_income"] = df["amount"] > 0
    df["is_expense"] = df["is_expense"].astype(int)
    df["is_income"] = df["is_income"].astype(int)

    df["log_abs_amount"] = np.log1p(df["abs_amount"])
    df["day_of_week"] = df["date"].dt.dayofweek
    df["day_of_month"] = df["date"].dt.day
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)

    n_transactions = len(df)
    df["merchant_frequency"] = df["merchant"].map(df["merchant"].value_counts()) / n_transactions
    df["category_frequency"] = df["category"].map(df["category"].value_counts()) / n_transactions
    df["account_frequency"] = df["account"].map(df["account"].value_counts()) / n_transactions

    category_mean = df.groupby("category")["abs_amount"].transform("mean")
    category_std = df.groupby("category")["abs_amount"].transform("std")
    category_std = category_std.replace(0, np.nan)
    zscore = ((df["abs_amount"] - category_mean) / category_std).abs()
    df["amount_category_zscore"] = zscore.replace([np.inf, -np.inf], np.nan).fillna(0.0)

    feature_df = df[FEATURE_COLUMNS].copy()
    feature_df = feature_df.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    feature_df = feature_df.astype(float)
    return feature_df, df


def normalize_scores(raw_scores):
    """
    Normalize raw anomaly scores to [0, 1] with min-max scaling.
    """
    scores = np.asarray(raw_scores, dtype=float)
    if scores.size == 0:
        return np.array([])

    min_score = np.nanmin(scores)
    max_score = np.nanmax(scores)
    if max_score == min_score:
        return np.zeros_like(scores, dtype=float)
    return (scores - min_score) / (max_score - min_score)


def assign_risk_levels(scores, high_quantile=0.95, medium_quantile=0.80):
    """
    Assign high / medium / low based on normalized anomaly scores.
    """
    scores = np.asarray(scores, dtype=float)
    if scores.size == 0:
        return []

    if len(scores) < 5:
        high_threshold = 0.80
        medium_threshold = 0.50
    else:
        high_threshold = np.quantile(scores, high_quantile, method="higher")
        medium_threshold = np.quantile(scores, medium_quantile, method="lower")

    risk_levels = []
    for score in scores:
        if score >= high_threshold:
            risk_levels.append("high")
        elif score >= medium_threshold:
            risk_levels.append("medium")
        else:
            risk_levels.append("low")
    return risk_levels


def build_model_evidence(row):
    """
    Build a short evidence string for one model-scored transaction.
    """
    evidence_parts = [
        f"金额为 {row.get('abs_amount', 0.0):.2f}",
        f"类别为 {row.get('category', 'other')}",
    ]

    if row.get("amount_category_zscore", 0.0) >= 1.5:
        evidence_parts.append("金额相对同类别偏离程度较高")
    if row.get("merchant_frequency", 1.0) <= 0.08:
        evidence_parts.append("商户出现频率较低")
    if row.get("category_frequency", 1.0) <= 0.08:
        evidence_parts.append("类别出现频率较低")
    if row.get("is_weekend", 0) == 1:
        evidence_parts.append("该交易发生在周末")
    if row.get("is_income", 0) == 1:
        evidence_parts.append("收入和支出都参与了局部交易模式计算")

    return "；".join(evidence_parts) + "。"


def _low_risk_result(enriched_df, evidence):
    result_df = enriched_df.copy()
    result_df["anomaly_branch"] = "model"
    result_df["model_name"] = "LOF"
    result_df["anomaly_score"] = 0.0
    result_df["risk_level"] = "low"
    result_df["model_evidence"] = evidence
    return result_df


def run_lof_detection(
    transactions_df,
    n_neighbors=10,
    contamination="auto",
    high_quantile=0.95,
    medium_quantile=0.80,
):
    """
    Run Local Outlier Factor model detection and return scored transactions.
    """
    feature_df, enriched_df = build_model_features(transactions_df)
    if enriched_df.empty:
        result_df = enriched_df.copy()
        result_df["anomaly_branch"] = []
        result_df["model_name"] = []
        result_df["anomaly_score"] = []
        result_df["risk_level"] = []
        result_df["model_evidence"] = []
        return result_df

    if len(feature_df) < 3:
        return _low_risk_result(
            enriched_df,
            "样本数量过少，LOF 模型无法可靠评估异常程度。",
        )

    n_samples = len(feature_df)
    effective_neighbors = min(n_neighbors, max(2, n_samples - 1))
    scaled_features = StandardScaler().fit_transform(feature_df)

    lof = LocalOutlierFactor(
        n_neighbors=effective_neighbors,
        contamination=contamination,
    )
    lof.fit_predict(scaled_features)
    raw_scores = -lof.negative_outlier_factor_
    anomaly_scores = normalize_scores(raw_scores)

    result_df = enriched_df.copy()
    result_df["anomaly_branch"] = "model"
    result_df["model_name"] = "LOF"
    result_df["anomaly_score"] = anomaly_scores
    result_df["risk_level"] = assign_risk_levels(
        anomaly_scores,
        high_quantile=high_quantile,
        medium_quantile=medium_quantile,
    )
    result_df["model_evidence"] = result_df.apply(build_model_evidence, axis=1)
    return result_df.sort_values("anomaly_score", ascending=False).reset_index(drop=True)
