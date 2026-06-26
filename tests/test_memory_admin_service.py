from memory.action_memory_service import upsert_action_item
from memory.admin_service import (
    clear_current_workspace_all_data,
    clear_workspace_actions,
    clear_workspace_business_memory,
    clear_workspace_feedback,
    clear_workspace_turns_traces_reports,
    get_workspace_memory_stats,
    list_workspace_overview,
)
from memory.feedback_service import submit_feedback
from memory.memory_service import add_business_memory, list_business_memory
from memory.persistence_service import persist_full_agent_turn
from memory.repository import ensure_workspace, get_user, get_workspace
from memory.report_service import list_reports


def seed_workspace(db_path: str, user_id: str, workspace_id: str):
    ensure_workspace(user_id, workspace_id, db_path=db_path)
    add_business_memory(user_id, workspace_id, "known_supplier", "A 是长期供应商。", db_path=db_path)
    submit_feedback(user_id, workspace_id, "add_business_context", "周末客流较高。", create_memory=False, db_path=db_path)
    upsert_action_item(user_id, workspace_id, {"action_id": "A001", "title": "联系客户"}, db_path=db_path)
    persist_full_agent_turn(
        user_id,
        workspace_id,
        {
            "user_query": "现金流安全吗？",
            "assistant_reply": "回复",
            "mode": "fallback",
            "manager_plan": {},
            "tool_results": [],
            "specialist_outputs": {},
            "trace": {"trace_id": f"trace_{workspace_id}"},
            "trace_markdown": "# Trace",
            "report_markdown": "# Report\n\n摘要",
            "chat_action_items": [{"action_id": "A002", "title": "核查发票"}],
        },
        db_path=db_path,
    )


def test_workspace_memory_stats_only_current_workspace(tmp_path):
    db_path = str(tmp_path / "memory.db")
    seed_workspace(db_path, "user_a", "demo_workspace")
    seed_workspace(db_path, "user_a", "coffee_shop")
    stats = get_workspace_memory_stats("user_a", "demo_workspace", db_path=db_path)
    assert stats["business_memory_count"] == 1
    assert stats["user_feedback_count"] == 1
    assert stats["agent_turn_count"] == 1
    assert stats["report_count"] == 1


def test_list_workspace_overview_returns_latest_sections(tmp_path):
    db_path = str(tmp_path / "memory.db")
    seed_workspace(db_path, "user_a", "demo_workspace")
    overview = list_workspace_overview("user_a", "demo_workspace", db_path=db_path)
    assert overview["identity"]["workspace_id"] == "demo_workspace"
    assert overview["latest_business_memory"]
    assert overview["latest_feedback"]
    assert overview["latest_actions"]
    assert overview["latest_turns"]
    assert overview["latest_reports"]


def test_clear_functions_only_clear_current_workspace(tmp_path):
    db_path = str(tmp_path / "memory.db")
    seed_workspace(db_path, "user_a", "demo_workspace")
    seed_workspace(db_path, "user_a", "coffee_shop")
    assert clear_workspace_business_memory("user_a", "demo_workspace", db_path=db_path) == 1
    assert list_business_memory("user_a", "demo_workspace", active_only=False, db_path=db_path) == []
    assert list_business_memory("user_a", "coffee_shop", active_only=False, db_path=db_path)
    assert clear_workspace_feedback("user_a", "demo_workspace", db_path=db_path) == 1
    assert clear_workspace_actions("user_a", "demo_workspace", db_path=db_path) >= 1
    deleted = clear_workspace_turns_traces_reports("user_a", "demo_workspace", db_path=db_path)
    assert deleted["agent_turns_deleted"] == 1
    assert list_reports("user_a", "coffee_shop", db_path=db_path)


def test_clear_current_workspace_all_data_keeps_users_and_workspaces(tmp_path):
    db_path = str(tmp_path / "memory.db")
    seed_workspace(db_path, "user_a", "demo_workspace")
    result = clear_current_workspace_all_data("user_a", "demo_workspace", db_path=db_path)
    assert result["business_memory_deleted"] == 1
    assert get_user("user_a", db_path=db_path)
    assert get_workspace("user_a", "demo_workspace", db_path=db_path)
