import json
import uuid
from datetime import datetime, timezone

from memory.db import execute_sql, initialize_memory_db, query_all, query_one


SUPPORTED_MEMORY_TYPES = {
    "known_normal_payment",
    "known_supplier",
    "cash_balance",
    "expected_receivable",
    "recurring_expense",
    "business_rule",
    "user_preference",
    "known_risk",
}

DEFAULT_MEMORY_CONFIDENCE = "confirmed"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def generate_memory_id() -> str:
    return f"mem_{uuid.uuid4().hex}"


def validate_memory_type(memory_type: str) -> str:
    if memory_type not in SUPPORTED_MEMORY_TYPES:
        raise ValueError(f"Unsupported memory_type: {memory_type}")
    return memory_type


def normalize_structured_value(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip() or None
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def parse_structured_value(value: str | None):
    if value is None:
        return None
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _normalize_tags(retrieval_tags) -> str | None:
    if retrieval_tags is None:
        return None
    if isinstance(retrieval_tags, str):
        return retrieval_tags.strip() or None
    return ", ".join(str(tag).strip() for tag in retrieval_tags if str(tag).strip()) or None


def _hydrate_memory(row: dict | None) -> dict | None:
    if not row:
        return None
    memory = dict(row)
    memory["structured_value"] = parse_structured_value(memory.get("structured_value_json"))
    memory["is_active"] = bool(memory.get("is_active"))
    return memory


def add_business_memory(
    user_id: str,
    workspace_id: str,
    memory_type: str,
    fact_text: str,
    entity_name: str | None = None,
    structured_value=None,
    source: str = "manual_input",
    confidence: str = DEFAULT_MEMORY_CONFIDENCE,
    retrieval_tags=None,
    embedding_text: str | None = None,
    db_path: str | None = None,
) -> dict:
    user_id = (user_id or "").strip()
    workspace_id = (workspace_id or "").strip()
    fact_text = (fact_text or "").strip()
    if not user_id:
        raise ValueError("user_id is required")
    if not workspace_id:
        raise ValueError("workspace_id is required")
    if not fact_text:
        raise ValueError("fact_text is required")
    validate_memory_type(memory_type)
    initialize_memory_db(db_path=db_path)

    memory_id = generate_memory_id()
    timestamp = now_iso()
    execute_sql(
        """
        INSERT INTO business_memory (
            memory_id, user_id, workspace_id, memory_type, entity_name, fact_text,
            structured_value_json, source, confidence, created_at, updated_at,
            last_used_at, is_active, embedding_text, retrieval_tags
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, 1, ?, ?)
        """,
        (
            memory_id,
            user_id,
            workspace_id,
            memory_type,
            (entity_name or "").strip() or None,
            fact_text,
            normalize_structured_value(structured_value),
            source,
            confidence,
            timestamp,
            timestamp,
            embedding_text or fact_text,
            _normalize_tags(retrieval_tags),
        ),
        db_path=db_path,
    )
    return get_business_memory(user_id, workspace_id, memory_id, db_path=db_path) or {}


def get_business_memory(
    user_id: str,
    workspace_id: str,
    memory_id: str,
    db_path: str | None = None,
) -> dict | None:
    row = query_one(
        """
        SELECT *
        FROM business_memory
        WHERE user_id = ? AND workspace_id = ? AND memory_id = ?
        """,
        (user_id, workspace_id, memory_id),
        db_path=db_path,
    )
    return _hydrate_memory(row)


def list_business_memory(
    user_id: str,
    workspace_id: str,
    memory_type: str | None = None,
    active_only: bool = True,
    limit: int = 100,
    db_path: str | None = None,
) -> list[dict]:
    initialize_memory_db(db_path=db_path)
    params: list = [user_id, workspace_id]
    clauses = ["user_id = ?", "workspace_id = ?"]
    if memory_type:
        validate_memory_type(memory_type)
        clauses.append("memory_type = ?")
        params.append(memory_type)
    if active_only:
        clauses.append("is_active = 1")
    params.append(max(1, int(limit)))
    rows = query_all(
        f"""
        SELECT *
        FROM business_memory
        WHERE {" AND ".join(clauses)}
        ORDER BY created_at DESC
        LIMIT ?
        """,
        tuple(params),
        db_path=db_path,
    )
    return [memory for memory in (_hydrate_memory(row) for row in rows) if memory]


def count_business_memory(
    user_id: str,
    workspace_id: str,
    active_only: bool = True,
    db_path: str | None = None,
) -> int:
    initialize_memory_db(db_path=db_path)
    clauses = ["user_id = ?", "workspace_id = ?"]
    if active_only:
        clauses.append("is_active = 1")
    row = query_one(
        f"""
        SELECT COUNT(*) AS memory_count
        FROM business_memory
        WHERE {" AND ".join(clauses)}
        """,
        (user_id, workspace_id),
        db_path=db_path,
    )
    return int(row.get("memory_count", 0)) if row else 0


def deactivate_business_memory(
    user_id: str,
    workspace_id: str,
    memory_id: str,
    db_path: str | None = None,
) -> bool:
    cursor = execute_sql(
        """
        UPDATE business_memory
        SET is_active = 0, updated_at = ?
        WHERE user_id = ? AND workspace_id = ? AND memory_id = ?
        """,
        (now_iso(), user_id, workspace_id, memory_id),
        db_path=db_path,
    )
    return cursor.rowcount > 0


def update_memory_last_used(
    user_id: str,
    workspace_id: str,
    memory_ids: list[str],
    db_path: str | None = None,
) -> int:
    timestamp = now_iso()
    updated = 0
    for memory_id in memory_ids:
        cursor = execute_sql(
            """
            UPDATE business_memory
            SET last_used_at = ?
            WHERE user_id = ? AND workspace_id = ? AND memory_id = ? AND is_active = 1
            """,
            (timestamp, user_id, workspace_id, memory_id),
            db_path=db_path,
        )
        updated += max(0, cursor.rowcount)
    return updated
