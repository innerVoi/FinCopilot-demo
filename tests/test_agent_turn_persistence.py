from agent_api.orchestrator import run_multi_agent_turn
from memory.action_memory_service import list_pending_action_items
from memory.report_service import list_reports
from memory.trace_service import list_agent_traces
from memory.turn_service import list_agent_turns


def test_run_multi_agent_turn_persists_turn_trace_report_and_actions(tmp_path, monkeypatch):
    monkeypatch.setenv("ENABLE_AGENT_API", "false")
    db_path = str(tmp_path / "memory.db")
    result = run_multi_agent_turn(
        "未来 30 天现金流安全吗？",
        user_id="user_a",
        workspace_id="shop_1",
        memory_db_path=db_path,
    )
    assert result["persisted"] is True
    assert result["turn_id"]
    assert len(list_agent_turns("user_a", "shop_1", db_path=db_path)) == 1
    assert len(list_agent_traces("user_a", "shop_1", db_path=db_path)) == 1
    assert len(list_reports("user_a", "shop_1", db_path=db_path)) == 1
    assert len(list_pending_action_items("user_a", "shop_1", db_path=db_path)) == len(result["chat_action_items"])
