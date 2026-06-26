import hashlib
import json
from datetime import datetime, timezone

from memory.db import execute_sql, initialize_memory_db, query_all, query_one


PENDING_STATUS = "pending"
HANDLED_ACTION_STATUSES = {
    "done",
    "ignored",
    "rejected",
    "needs_follow_up",
    "feedback_recorded",
}
ACTION_FEEDBACK_TO_STATUS = {
    "complete_action": "done",
    "ignore_action": "ignored",
    "reject_suggestion": "rejected",
    "needs_follow_up": "needs_follow_up",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_json_dumps(value) -> str:
    return json.dumps(value or {}, ensure_ascii=False, sort_keys=True)


def _safe_json_loads(value: str | None):
    if not value:
        return {}
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return {}


def _stable_action_id(action_item: dict, fallback_index: int | None = None) -> str:
    basis = "|".join(
        str(action_item.get(key, ""))
        for key in ["title", "description", "source", "priority"]
    )
    if fallback_index is not None:
        basis = f"{basis}|{fallback_index}"
    digest = hashlib.sha1(basis.encode("utf-8")).hexdigest()[:12]
    return f"action_{digest}"


def normalize_action_item(action_item: dict, fallback_index: int | None = None) -> dict:
    action_item = action_item or {}
    title = action_item.get("title") or action_item.get("action") or action_item.get("description") or ""
    action_id = action_item.get("action_id") or action_item.get("id") or _stable_action_id(action_item, fallback_index)
    metadata = dict(action_item.get("metadata") or {})
    metadata.setdefault("original_action", dict(action_item))
    return {
        "action_id": str(action_id),
        "title": str(title),
        "description": action_item.get("description") or action_item.get("reason") or "",
        "priority": action_item.get("priority") or "medium",
        "status": action_item.get("status") or PENDING_STATUS,
        "source": action_item.get("source") or "agent_chat",
        "due_date": action_item.get("due_date") or action_item.get("suggested_deadline"),
        "metadata": metadata,
    }


def _hydrate_action(row: dict | None) -> dict | None:
    if not row:
        return None
    item = dict(row)
    item["metadata"] = _safe_json_loads(item.get("metadata_json"))
    return item


def action_exists(user_id: str, workspace_id: str, action_id: str, db_path: str | None = None) -> bool:
    return get_action_item(user_id, workspace_id, action_id, db_path=db_path) is not None


def get_action_item(user_id: str, workspace_id: str, action_id: str, db_path: str | None = None) -> dict | None:
    initialize_memory_db(db_path=db_path)
    row = query_one(
        """
        SELECT *
        FROM action_memory
        WHERE user_id = ? AND workspace_id = ? AND action_id = ?
        """,
        (user_id, workspace_id, action_id),
        db_path=db_path,
    )
    return _hydrate_action(row)


def upsert_action_item(
    user_id: str,
    workspace_id: str,
    action_item: dict,
    related_turn_id: str | None = None,
    db_path: str | None = None,
) -> dict:
    initialize_memory_db(db_path=db_path)
    item = normalize_action_item(action_item)
    existing = get_action_item(user_id, workspace_id, item["action_id"], db_path=db_path)
    timestamp = now_iso()
    if existing and existing.get("status") != PENDING_STATUS:
        return existing
    metadata = item["metadata"]
    if existing:
        existing_metadata = existing.get("metadata") or {}
        existing_metadata.update(metadata)
        metadata = existing_metadata
        execute_sql(
            """
            UPDATE action_memory
            SET title = ?, description = ?, priority = ?, source = ?, related_turn_id = ?,
                updated_at = ?, due_date = ?, metadata_json = ?
            WHERE user_id = ? AND workspace_id = ? AND action_id = ?
            """,
            (
                item["title"],
                item["description"],
                item["priority"],
                item["source"],
                related_turn_id or existing.get("related_turn_id"),
                timestamp,
                item["due_date"],
                _safe_json_dumps(metadata),
                user_id,
                workspace_id,
                item["action_id"],
            ),
            db_path=db_path,
        )
    else:
        execute_sql(
            """
            INSERT INTO action_memory (
                action_id, user_id, workspace_id, title, description, priority, status,
                source, related_turn_id, created_at, updated_at, due_date, metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item["action_id"],
                user_id,
                workspace_id,
                item["title"],
                item["description"],
                item["priority"],
                PENDING_STATUS,
                item["source"],
                related_turn_id,
                timestamp,
                timestamp,
                item["due_date"],
                _safe_json_dumps(metadata),
            ),
            db_path=db_path,
        )
    return get_action_item(user_id, workspace_id, item["action_id"], db_path=db_path) or {}


def persist_action_items(
    user_id: str,
    workspace_id: str,
    action_items: list[dict] | None,
    related_turn_id: str | None = None,
    db_path: str | None = None,
) -> list[dict]:
    return [
        upsert_action_item(user_id, workspace_id, item, related_turn_id=related_turn_id, db_path=db_path)
        for item in (action_items or [])
        if isinstance(item, dict)
    ]


def list_action_items(
    user_id: str,
    workspace_id: str,
    status: str | None = None,
    limit: int = 100,
    db_path: str | None = None,
) -> list[dict]:
    initialize_memory_db(db_path=db_path)
    clauses = ["user_id = ?", "workspace_id = ?"]
    params: list = [user_id, workspace_id]
    if status:
        clauses.append("status = ?")
        params.append(status)
    params.append(max(1, int(limit)))
    rows = query_all(
        f"""
        SELECT *
        FROM action_memory
        WHERE {" AND ".join(clauses)}
        ORDER BY updated_at DESC
        LIMIT ?
        """,
        tuple(params),
        db_path=db_path,
    )
    return [item for item in (_hydrate_action(row) for row in rows) if item]


def list_pending_action_items(user_id: str, workspace_id: str, limit: int = 100, db_path: str | None = None) -> list[dict]:
    return list_action_items(user_id, workspace_id, status=PENDING_STATUS, limit=limit, db_path=db_path)


def list_handled_action_items(user_id: str, workspace_id: str, limit: int = 100, db_path: str | None = None) -> list[dict]:
    items = list_action_items(user_id, workspace_id, limit=limit, db_path=db_path)
    return [item for item in items if item.get("status") in HANDLED_ACTION_STATUSES]


def is_action_feedback_allowed(user_id: str, workspace_id: str, action_id: str, db_path: str | None = None) -> bool:
    action = get_action_item(user_id, workspace_id, action_id, db_path=db_path)
    return bool(action and action.get("status") == PENDING_STATUS)


def mark_action_feedback_recorded(
    user_id: str,
    workspace_id: str,
    action_id: str,
    feedback_type: str,
    feedback_reason: str,
    feedback_id: str | None = None,
    db_path: str | None = None,
) -> dict:
    action = get_action_item(user_id, workspace_id, action_id, db_path=db_path)
    if not action:
        action = upsert_action_item(
            user_id,
            workspace_id,
            {"action_id": action_id, "title": action_id, "source": "feedback"},
            db_path=db_path,
        )
    if action.get("status") != PENDING_STATUS:
        return {
            "updated": False,
            "duplicate_feedback": True,
            "action": action,
            "message": "This action item has already received feedback and was moved into handled action items. Duplicate feedback is not allowed.",
        }

    timestamp = now_iso()
    status = ACTION_FEEDBACK_TO_STATUS.get(feedback_type, "feedback_recorded")
    metadata = action.get("metadata") or {}
    metadata["feedback"] = {
        "feedback_id": feedback_id,
        "feedback_type": feedback_type,
        "feedback_reason": feedback_reason,
        "feedback_at": timestamp,
    }
    execute_sql(
        """
        UPDATE action_memory
        SET status = ?, updated_at = ?, metadata_json = ?
        WHERE user_id = ? AND workspace_id = ? AND action_id = ?
        """,
        (status, timestamp, _safe_json_dumps(metadata), user_id, workspace_id, action_id),
        db_path=db_path,
    )
    return {
        "updated": True,
        "duplicate_feedback": False,
        "action": get_action_item(user_id, workspace_id, action_id, db_path=db_path),
        "message": "Action item feedback has been saved and moved into handled action items.",
    }


def count_pending_actions(user_id: str, workspace_id: str, db_path: str | None = None) -> int:
    return len(list_pending_action_items(user_id, workspace_id, db_path=db_path))


def count_handled_actions(user_id: str, workspace_id: str, db_path: str | None = None) -> int:
    return len(list_handled_action_items(user_id, workspace_id, db_path=db_path))
