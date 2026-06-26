from memory.repository import (
    ensure_default_workspace,
    ensure_user,
    ensure_workspace,
    get_user,
    get_workspace,
    list_workspaces,
    now_iso,
)


def test_now_iso_returns_string():
    assert "T" in now_iso()


def test_ensure_user_and_get_user(tmp_path):
    db_path = str(tmp_path / "memory.db")
    user = ensure_user("user_a", user_name="User A", db_path=db_path)
    assert user["user_id"] == "user_a"
    assert get_user("user_a", db_path=db_path)["user_name"] == "User A"


def test_ensure_workspace_and_get_workspace(tmp_path):
    db_path = str(tmp_path / "memory.db")
    workspace = ensure_workspace("user_a", "shop_1", workspace_name="Shop 1", db_path=db_path)
    assert workspace["workspace_id"] == "shop_1"
    assert get_workspace("user_a", "shop_1", db_path=db_path)["workspace_name"] == "Shop 1"
    assert get_workspace("user_b", "shop_1", db_path=db_path) is None


def test_list_workspaces_only_returns_user_scope(tmp_path):
    db_path = str(tmp_path / "memory.db")
    ensure_workspace("user_a", "shop_1", db_path=db_path)
    ensure_workspace("user_b", "shop_1", db_path=db_path)
    rows = list_workspaces("user_a", db_path=db_path)
    assert len(rows) == 1
    assert rows[0]["user_id"] == "user_a"


def test_ensure_default_workspace(tmp_path, monkeypatch):
    db_path = str(tmp_path / "memory.db")
    monkeypatch.delenv("FINCOPILOT_DEFAULT_USER_ID", raising=False)
    monkeypatch.delenv("FINCOPILOT_DEFAULT_WORKSPACE_ID", raising=False)
    payload = ensure_default_workspace(db_path=db_path)
    assert payload["user"]["user_id"] == "demo_user"
    assert payload["workspace"]["workspace_id"] == "demo_workspace"
    assert payload["workspace"]["workspace_name"] == "Demo 小微商家"


def test_same_workspace_id_different_users_do_not_conflict(tmp_path):
    db_path = str(tmp_path / "memory.db")
    ensure_workspace("user_a", "shop_1", workspace_name="A Shop", db_path=db_path)
    ensure_workspace("user_b", "shop_1", workspace_name="B Shop", db_path=db_path)
    assert get_workspace("user_a", "shop_1", db_path=db_path)["workspace_name"] == "A Shop"
    assert get_workspace("user_b", "shop_1", db_path=db_path)["workspace_name"] == "B Shop"
