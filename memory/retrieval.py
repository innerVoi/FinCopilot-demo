from memory.memory_service import (
    list_business_memory,
    update_memory_last_used,
    validate_memory_type,
)


TASK_MEMORY_TYPE_MAP = {
    "cashflow_forecast": ["cash_balance", "expected_receivable", "recurring_expense", "business_rule"],
    "cashflow_check": ["cash_balance", "expected_receivable", "recurring_expense", "business_rule"],
    "expense_anomaly": ["known_normal_payment", "known_supplier", "recurring_expense", "known_risk"],
    "expense_anomaly_review": ["known_normal_payment", "known_supplier", "recurring_expense", "known_risk"],
    "priority_payment": ["known_supplier", "business_rule", "cash_balance", "user_preference"],
    "invoice_or_payment_review": ["known_supplier", "business_rule", "cash_balance", "expected_receivable"],
    "action_list": ["business_rule", "user_preference", "known_risk", "expected_receivable"],
    "goal_or_budget_planning": ["business_rule", "user_preference", "recurring_expense", "known_risk"],
    "general_finance_summary": [
        "known_normal_payment",
        "known_supplier",
        "cash_balance",
        "expected_receivable",
        "recurring_expense",
        "business_rule",
        "user_preference",
        "known_risk",
    ],
}

SUMMARY_KEY_BY_MEMORY_TYPE = {
    "known_normal_payment": "known_normal_payments",
    "known_supplier": "known_suppliers",
    "cash_balance": "cash_context",
    "expected_receivable": "expected_receivables",
    "recurring_expense": "recurring_expenses",
    "business_rule": "business_rules",
    "user_preference": "user_preferences",
    "known_risk": "known_risks",
}


def normalize_query_text(query: str | None) -> str:
    return " ".join(str(query or "").lower().split())


def infer_memory_types_for_task(task_type: str | None) -> list[str]:
    return TASK_MEMORY_TYPE_MAP.get(task_type or "", TASK_MEMORY_TYPE_MAP["general_finance_summary"])


def _matches_query(memory: dict, normalized_query: str) -> bool:
    if not normalized_query:
        return True
    haystack = " ".join(
        str(memory.get(field) or "")
        for field in ["fact_text", "entity_name", "retrieval_tags", "embedding_text"]
    ).lower()
    return all(token in haystack for token in normalized_query.split())


def search_business_memory(
    user_id: str,
    workspace_id: str,
    query: str | None = None,
    memory_types: list[str] | None = None,
    active_only: bool = True,
    limit: int = 20,
    db_path: str | None = None,
) -> list[dict]:
    types = memory_types or [None]
    normalized_query = normalize_query_text(query)
    results = []
    seen = set()
    for memory_type in types:
        if memory_type:
            validate_memory_type(memory_type)
        candidates = list_business_memory(
            user_id=user_id,
            workspace_id=workspace_id,
            memory_type=memory_type,
            active_only=active_only,
            limit=max(limit, 50),
            db_path=db_path,
        )
        for memory in candidates:
            memory_id = memory.get("memory_id")
            if memory_id in seen or not _matches_query(memory, normalized_query):
                continue
            seen.add(memory_id)
            results.append(memory)
            if len(results) >= limit:
                return results
    return results


def retrieve_memory_for_task(
    user_id: str,
    workspace_id: str,
    task_type: str | None = None,
    user_query: str | None = None,
    limit: int = 20,
    db_path: str | None = None,
) -> list[dict]:
    memory_types = infer_memory_types_for_task(task_type)
    memories = search_business_memory(
        user_id=user_id,
        workspace_id=workspace_id,
        query=user_query,
        memory_types=memory_types,
        limit=limit,
        db_path=db_path,
    )
    if not memories and user_query:
        memories = search_business_memory(
            user_id=user_id,
            workspace_id=workspace_id,
            memory_types=memory_types,
            limit=limit,
            db_path=db_path,
        )
    update_memory_last_used(
        user_id=user_id,
        workspace_id=workspace_id,
        memory_ids=[memory["memory_id"] for memory in memories],
        db_path=db_path,
    )
    return memories


def group_memories_by_type(memories: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for memory in memories:
        grouped.setdefault(memory.get("memory_type", "unknown"), []).append(memory)
    return grouped


def build_memory_context_summary(memories: list[dict], max_items_per_type: int = 5) -> dict:
    summary = {
        "memory_count": len(memories),
        "used_memory_ids": [memory.get("memory_id") for memory in memories if memory.get("memory_id")],
        "known_normal_payments": [],
        "known_suppliers": [],
        "cash_context": [],
        "expected_receivables": [],
        "recurring_expenses": [],
        "business_rules": [],
        "user_preferences": [],
        "known_risks": [],
        "memory_notes": "",
    }
    grouped = group_memories_by_type(memories)
    for memory_type, key in SUMMARY_KEY_BY_MEMORY_TYPE.items():
        summary[key] = [
            memory.get("fact_text", "")
            for memory in grouped.get(memory_type, [])[:max_items_per_type]
            if memory.get("fact_text")
        ]
    if memories:
        summary["memory_notes"] = f"This analysis can reference {len(memories)} historical business memory records."
    else:
        summary["memory_notes"] = "No historical business memory is available yet. This analysis mainly uses the current uploaded data."
    return summary


def get_memory_context_for_task(
    user_id: str,
    workspace_id: str,
    task_type: str | None = None,
    user_query: str | None = None,
    limit: int = 20,
    db_path: str | None = None,
) -> dict:
    memories = retrieve_memory_for_task(
        user_id=user_id,
        workspace_id=workspace_id,
        task_type=task_type,
        user_query=user_query,
        limit=limit,
        db_path=db_path,
    )
    return build_memory_context_summary(memories)
