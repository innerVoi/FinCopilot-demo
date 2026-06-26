import uuid
from datetime import datetime, timezone

from memory.db import execute_sql, initialize_memory_db, query_all, query_one
from memory.memory_service import add_business_memory
from memory.action_memory_service import (
    ACTION_FEEDBACK_TO_STATUS,
    get_action_item,
    is_action_feedback_allowed,
    mark_action_feedback_recorded,
)


SUPPORTED_FEEDBACK_TYPES = {
    "confirm_normal_payment",
    "confirm_supplier",
    "confirm_recurring_expense",
    "update_cash_balance",
    "add_expected_receivable",
    "confirm_known_risk",
    "complete_action",
    "ignore_action",
    "reject_suggestion",
    "needs_follow_up",
    "add_business_context",
}

FEEDBACK_TO_MEMORY_TYPE = {
    "confirm_normal_payment": "known_normal_payment",
    "confirm_supplier": "known_supplier",
    "confirm_recurring_expense": "recurring_expense",
    "update_cash_balance": "cash_balance",
    "add_expected_receivable": "expected_receivable",
    "confirm_known_risk": "known_risk",
    "add_business_context": "business_rule",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def generate_feedback_id() -> str:
    return f"fb_{uuid.uuid4().hex}"


def validate_feedback_type(feedback_type: str) -> str:
    if feedback_type not in SUPPORTED_FEEDBACK_TYPES:
        raise ValueError(f"Unsupported feedback_type: {feedback_type}")
    return feedback_type


def add_user_feedback(
    user_id: str,
    workspace_id: str,
    feedback_type: str,
    feedback_text: str,
    turn_id: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    db_path: str | None = None,
) -> dict:
    user_id = (user_id or "").strip()
    workspace_id = (workspace_id or "").strip()
    feedback_text = (feedback_text or "").strip()
    if not user_id:
        raise ValueError("user_id is required")
    if not workspace_id:
        raise ValueError("workspace_id is required")
    if not feedback_text:
        raise ValueError("feedback_text is required")
    validate_feedback_type(feedback_type)
    initialize_memory_db(db_path=db_path)

    feedback_id = generate_feedback_id()
    execute_sql(
        """
        INSERT INTO user_feedback (
            feedback_id, user_id, workspace_id, turn_id, target_type, target_id,
            feedback_type, feedback_text, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            feedback_id,
            user_id,
            workspace_id,
            turn_id,
            target_type,
            target_id,
            feedback_type,
            feedback_text,
            now_iso(),
        ),
        db_path=db_path,
    )
    return query_one(
        """
        SELECT *
        FROM user_feedback
        WHERE user_id = ? AND workspace_id = ? AND feedback_id = ?
        """,
        (user_id, workspace_id, feedback_id),
        db_path=db_path,
    ) or {}


def list_user_feedback(
    user_id: str,
    workspace_id: str,
    feedback_type: str | None = None,
    limit: int = 100,
    db_path: str | None = None,
) -> list[dict]:
    initialize_memory_db(db_path=db_path)
    clauses = ["user_id = ?", "workspace_id = ?"]
    params: list = [user_id, workspace_id]
    if feedback_type:
        validate_feedback_type(feedback_type)
        clauses.append("feedback_type = ?")
        params.append(feedback_type)
    params.append(max(1, int(limit)))
    return query_all(
        f"""
        SELECT *
        FROM user_feedback
        WHERE {" AND ".join(clauses)}
        ORDER BY created_at DESC
        LIMIT ?
        """,
        tuple(params),
        db_path=db_path,
    )


def list_action_item_feedback(
    user_id: str,
    workspace_id: str,
    action_id: str | None = None,
    limit: int = 100,
    db_path: str | None = None,
) -> list[dict]:
    initialize_memory_db(db_path=db_path)
    clauses = ["user_id = ?", "workspace_id = ?", "target_type = ?"]
    params: list = [user_id, workspace_id, "action_item"]
    if action_id:
        clauses.append("target_id = ?")
        params.append(action_id)
    params.append(max(1, int(limit)))
    return query_all(
        f"""
        SELECT *
        FROM user_feedback
        WHERE {" AND ".join(clauses)}
        ORDER BY created_at DESC
        LIMIT ?
        """,
        tuple(params),
        db_path=db_path,
    )


def _first_present(metadata: dict, *keys):
    for key in keys:
        value = metadata.get(key)
        if value not in [None, ""]:
            return value
    return None


def build_memory_fact_from_feedback(
    feedback_type: str,
    feedback_text: str,
    target_metadata: dict | None = None,
) -> dict | None:
    validate_feedback_type(feedback_type)
    memory_type = FEEDBACK_TO_MEMORY_TYPE.get(feedback_type)
    if not memory_type:
        return None

    metadata = target_metadata or {}
    entity_name = _first_present(metadata, "merchant", "vendor", "supplier", "customer", "entity_name")
    amount = _first_present(metadata, "amount", "balance")
    date_value = _first_present(metadata, "date", "as_of_date", "due_date", "expected_date")
    currency = _first_present(metadata, "currency") or "CNY"

    if feedback_type == "confirm_normal_payment":
        fact_text = f"{entity_name or 'this expense'} was confirmed by the user as normal business spending. {feedback_text}"
    elif feedback_type == "confirm_supplier":
        fact_text = f"{entity_name or 'this supplier'} was confirmed by the user as a long-term partner. {feedback_text}"
    elif feedback_type == "confirm_recurring_expense":
        fact_text = f"{entity_name or 'this expense'} was confirmed by the user as a recurring expense. {feedback_text}"
    elif feedback_type == "update_cash_balance":
        if amount is not None:
            fact_text = f"Current cash balance is {amount} {currency}. {feedback_text}"
        else:
            fact_text = f"The user updated the current cash balance: {feedback_text}"
    elif feedback_type == "add_expected_receivable":
        if amount is not None:
            fact_text = f"{entity_name or 'Customer'} is expected to pay {amount} {currency}. {feedback_text}"
        else:
            fact_text = f"The user added expected future receivables: {feedback_text}"
    elif feedback_type == "confirm_known_risk":
        fact_text = f"The user confirmed a business risk that needs continued attention: {feedback_text}"
    else:
        fact_text = feedback_text

    if date_value:
        fact_text = f"{fact_text} Related date: {date_value}."

    return {
        "memory_type": memory_type,
        "fact_text": " ".join(str(fact_text).split()),
        "entity_name": str(entity_name).strip() if entity_name is not None else None,
        "structured_value": metadata or None,
        "retrieval_tags": [
            feedback_type,
            memory_type,
            str(entity_name) if entity_name else "",
        ],
    }


def submit_feedback(
    user_id: str,
    workspace_id: str,
    feedback_type: str,
    feedback_text: str,
    turn_id: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    target_metadata: dict | None = None,
    create_memory: bool = True,
    db_path: str | None = None,
) -> dict:
    if target_type == "action_item" and target_id:
        action = get_action_item(user_id, workspace_id, target_id, db_path=db_path)
        if action and not is_action_feedback_allowed(user_id, workspace_id, target_id, db_path=db_path):
            return {
                "feedback": None,
                "memory_created": False,
                "memory": None,
                "action_updated": False,
                "action_status": action.get("status"),
                "duplicate_feedback": True,
                "message": "This action item has already received feedback and was moved into handled action items. Duplicate feedback is not allowed.",
            }

    feedback = add_user_feedback(
        user_id=user_id,
        workspace_id=workspace_id,
        feedback_type=feedback_type,
        feedback_text=feedback_text,
        turn_id=turn_id,
        target_type=target_type,
        target_id=target_id,
        db_path=db_path,
    )

    memory = None
    action_update_result = None
    if target_type == "action_item" and target_id:
        action_update_result = mark_action_feedback_recorded(
            user_id=user_id,
            workspace_id=workspace_id,
            action_id=target_id,
            feedback_type=feedback_type,
            feedback_reason=feedback_text,
            feedback_id=feedback.get("feedback_id"),
            db_path=db_path,
        )
        create_memory = False
    if create_memory:
        payload = build_memory_fact_from_feedback(
            feedback_type=feedback_type,
            feedback_text=feedback_text,
            target_metadata=target_metadata,
        )
        if payload:
            memory = add_business_memory(
                user_id=user_id,
                workspace_id=workspace_id,
                memory_type=payload["memory_type"],
                fact_text=payload["fact_text"],
                entity_name=payload.get("entity_name"),
                structured_value=payload.get("structured_value"),
                source="user_feedback",
                confidence="user_confirmed",
                retrieval_tags=payload.get("retrieval_tags"),
                db_path=db_path,
            )

    action_status = (action_update_result or {}).get("action", {}).get("status")
    return {
        "feedback": feedback,
        "memory_created": bool(memory),
        "memory": memory,
        "action_updated": bool((action_update_result or {}).get("updated")),
        "action_status": action_status,
        "duplicate_feedback": bool((action_update_result or {}).get("duplicate_feedback")),
        "message": (
            "Action item feedback has been saved and moved into handled action items."
            if action_update_result and action_update_result.get("updated")
            else ("Feedback has been saved and converted into business memory." if memory else "Feedback has been saved.")
        ),
    }


def count_user_feedback(user_id: str, workspace_id: str, db_path: str | None = None) -> int:
    initialize_memory_db(db_path=db_path)
    row = query_one(
        """
        SELECT COUNT(*) AS feedback_count
        FROM user_feedback
        WHERE user_id = ? AND workspace_id = ?
        """,
        (user_id, workspace_id),
        db_path=db_path,
    )
    return int(row.get("feedback_count", 0)) if row else 0
