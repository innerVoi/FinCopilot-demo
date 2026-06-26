from datetime import datetime, timezone

from memory.db import query_all, query_one, execute_sql, initialize_memory_db
from memory.workspace import get_default_user_id, get_default_workspace_id


DEFAULT_WORKSPACE_NAME = "Demo Small Business"
DEFAULT_BUSINESS_TYPE = "Small Retail / Food Service"


def now_iso() -> str:
    """
    Return current UTC ISO timestamp.
    """
    return datetime.now(timezone.utc).isoformat()


def ensure_user(user_id: str, user_name: str | None = None, db_path: str | None = None) -> dict:
    """
    Create a user if missing and return it.
    """
    initialize_memory_db(db_path=db_path)
    existing = get_user(user_id, db_path=db_path)
    if existing:
        return existing
    execute_sql(
        """
        INSERT INTO users (user_id, user_name, created_at)
        VALUES (?, ?, ?)
        """,
        (user_id, user_name or user_id, now_iso()),
        db_path=db_path,
    )
    return get_user(user_id, db_path=db_path) or {}


def get_user(user_id: str, db_path: str | None = None) -> dict | None:
    """
    Get a user by user_id.
    """
    return query_one(
        "SELECT user_id, user_name, created_at FROM users WHERE user_id = ?",
        (user_id,),
        db_path=db_path,
    )


def ensure_workspace(
    user_id: str,
    workspace_id: str,
    workspace_name: str | None = None,
    business_type: str | None = None,
    db_path: str | None = None,
) -> dict:
    """
    Create a workspace scoped to user_id if missing and return it.
    """
    initialize_memory_db(db_path=db_path)
    ensure_user(user_id, db_path=db_path)
    existing = get_workspace(user_id, workspace_id, db_path=db_path)
    if existing:
        return existing
    execute_sql(
        """
        INSERT INTO workspaces (workspace_id, user_id, workspace_name, business_type, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            workspace_id,
            user_id,
            workspace_name or DEFAULT_WORKSPACE_NAME,
            business_type or DEFAULT_BUSINESS_TYPE,
            now_iso(),
        ),
        db_path=db_path,
    )
    return get_workspace(user_id, workspace_id, db_path=db_path) or {}


def create_workspace(
    user_id: str,
    workspace_id: str,
    workspace_name: str | None = None,
    business_type: str | None = None,
    db_path: str | None = None,
) -> dict:
    """
    Create a workspace for one user, returning the existing row if present.
    """
    return ensure_workspace(
        user_id=user_id,
        workspace_id=workspace_id,
        workspace_name=workspace_name,
        business_type=business_type,
        db_path=db_path,
    )


def get_workspace(user_id: str, workspace_id: str, db_path: str | None = None) -> dict | None:
    """
    Get a workspace only within a user scope.
    """
    return query_one(
        """
        SELECT workspace_id, user_id, workspace_name, business_type, created_at
        FROM workspaces
        WHERE user_id = ? AND workspace_id = ?
        """,
        (user_id, workspace_id),
        db_path=db_path,
    )


def list_workspaces(user_id: str, db_path: str | None = None) -> list[dict]:
    """
    List only workspaces for one user_id.
    """
    return query_all(
        """
        SELECT workspace_id, user_id, workspace_name, business_type, created_at
        FROM workspaces
        WHERE user_id = ?
        ORDER BY created_at ASC
        """,
        (user_id,),
        db_path=db_path,
    )


def ensure_default_workspace(db_path: str | None = None) -> dict:
    """
    Ensure demo_user and demo_workspace exist.
    """
    user_id = get_default_user_id()
    workspace_id = get_default_workspace_id()
    user = ensure_user(user_id, user_name="Demo User", db_path=db_path)
    workspace = ensure_workspace(
        user_id=user_id,
        workspace_id=workspace_id,
        workspace_name=DEFAULT_WORKSPACE_NAME,
        business_type=DEFAULT_BUSINESS_TYPE,
        db_path=db_path,
    )
    return {"user": user, "workspace": workspace}
