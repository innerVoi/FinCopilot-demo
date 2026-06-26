import os


DEFAULT_USER_ID = "demo_user"
DEFAULT_WORKSPACE_ID = "demo_workspace"


def get_default_user_id() -> str:
    """
    Return the default demo user id.
    """
    return os.getenv("FINCOPILOT_DEFAULT_USER_ID", DEFAULT_USER_ID).strip() or DEFAULT_USER_ID


def get_default_workspace_id() -> str:
    """
    Return the default demo workspace id.
    """
    return os.getenv("FINCOPILOT_DEFAULT_WORKSPACE_ID", DEFAULT_WORKSPACE_ID).strip() or DEFAULT_WORKSPACE_ID


def get_current_user_id(session_state: dict | None = None) -> str:
    """
    Return current user id from session state, falling back to default.
    """
    session_state = session_state or {}
    return session_state.get("current_user_id") or get_default_user_id()


def get_current_workspace_id(session_state: dict | None = None) -> str:
    """
    Return current workspace id from session state, falling back to default.
    """
    session_state = session_state or {}
    return session_state.get("current_workspace_id") or get_default_workspace_id()


def get_current_identity(session_state: dict | None = None) -> dict:
    """
    Return current user/workspace identity.
    """
    return {
        "user_id": get_current_user_id(session_state),
        "workspace_id": get_current_workspace_id(session_state),
    }


def set_current_identity(
    session_state: dict,
    user_id: str | None = None,
    workspace_id: str | None = None,
) -> dict:
    """
    Set current user/workspace identity in a dict-like session state.
    """
    if session_state is None:
        session_state = {}
    if user_id:
        session_state["current_user_id"] = user_id
    if workspace_id:
        session_state["current_workspace_id"] = workspace_id
    return get_current_identity(session_state)


def set_current_workspace_id(session_state: dict | None, workspace_id: str) -> dict:
    """
    Switch only workspace_id in session state.
    """
    if session_state is None:
        session_state = {}
    if workspace_id:
        session_state["current_workspace_id"] = workspace_id
    return get_current_identity(session_state)


def build_workspace_display_name(user_id: str, workspace_id: str) -> str:
    """
    Build a human-readable workspace display name.
    """
    return f"{user_id} / {workspace_id}"
