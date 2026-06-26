from agent_api.orchestrator import run_multi_agent_turn
from memory.memory_service import add_business_memory, get_business_memory


def test_run_multi_agent_turn_contains_memory_context_and_trace(tmp_path, monkeypatch):
    db_path = str(tmp_path / "memory.db")
    monkeypatch.setenv("ENABLE_AGENT_API", "false")
    memory = add_business_memory(
        "user_a",
        "shop_1",
        "cash_balance",
        "当前现金余额为 12000 元。",
        db_path=db_path,
    )
    result = run_multi_agent_turn(
        "未来 30 天现金流安全吗？",
        agent_context_summary={"cashflow_summary": {"risk_level": "medium"}},
        user_id="user_a",
        workspace_id="shop_1",
        memory_db_path=db_path,
    )
    assert result["memory_context"]["memory_count"] == 1
    assert result["memory_trace"]["retrieval_scope"] == "current_user_current_workspace_only"
    assert result["memory_augmented"] is True
    assert memory["memory_id"] in result["used_memory_ids"]
    assert get_business_memory("user_a", "shop_1", memory["memory_id"], db_path=db_path)["last_used_at"]
    assert "历史业务记忆" in result["assistant_reply"]


def test_run_multi_agent_turn_fallback_without_memory_still_has_memory_fields(tmp_path, monkeypatch):
    monkeypatch.setenv("ENABLE_AGENT_API", "false")
    result = run_multi_agent_turn(
        "总结一下财务情况",
        user_id="user_a",
        workspace_id="shop_1",
        memory_db_path=str(tmp_path / "memory.db"),
    )
    assert result["memory_context"]["memory_count"] == 0
    assert result["memory_augmented"] is False
    assert result["used_memory_ids"] == []
    assert "memory" in result["trace"]
