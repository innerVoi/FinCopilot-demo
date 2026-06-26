from memory.workspace import (
    build_workspace_display_name,
    get_current_identity,
    get_current_user_id,
    get_current_workspace_id,
    get_default_user_id,
    get_default_workspace_id,
    set_current_identity,
)


def test_default_identity(monkeypatch):
    monkeypatch.delenv("FINCOPILOT_DEFAULT_USER_ID", raising=False)
    monkeypatch.delenv("FINCOPILOT_DEFAULT_WORKSPACE_ID", raising=False)
    assert get_default_user_id() == "demo_user"
    assert get_default_workspace_id() == "demo_workspace"


def test_default_identity_env_override(monkeypatch):
    monkeypatch.setenv("FINCOPILOT_DEFAULT_USER_ID", "user_x")
    monkeypatch.setenv("FINCOPILOT_DEFAULT_WORKSPACE_ID", "shop_x")
    assert get_default_user_id() == "user_x"
    assert get_default_workspace_id() == "shop_x"


def test_current_identity_handles_none():
    identity = get_current_identity(None)
    assert identity == {"user_id": "demo_user", "workspace_id": "demo_workspace"}
    assert get_current_user_id(None) == "demo_user"
    assert get_current_workspace_id(None) == "demo_workspace"


def test_set_current_identity_writes_dict():
    session_state = {}
    identity = set_current_identity(session_state, user_id="user_a", workspace_id="shop_1")
    assert identity == {"user_id": "user_a", "workspace_id": "shop_1"}
    assert session_state["current_user_id"] == "user_a"
    assert session_state["current_workspace_id"] == "shop_1"


def test_build_workspace_display_name_returns_string():
    assert build_workspace_display_name("user_a", "shop_1") == "user_a / shop_1"
