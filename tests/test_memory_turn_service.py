from memory.turn_service import (
    generate_turn_id,
    get_agent_turn,
    list_agent_turns,
    persist_agent_turn,
    safe_json_dumps,
    safe_json_loads,
)


def test_safe_json_roundtrip():
    payload = {"a": 1}
    assert safe_json_loads(safe_json_dumps(payload)) == payload


def test_generate_turn_id_has_prefix():
    assert generate_turn_id().startswith("turn_")


def test_persist_get_and_list_agent_turns_scoped(tmp_path):
    db_path = str(tmp_path / "memory.db")
    turn = persist_agent_turn(
        "user_a",
        "shop_1",
        {
            "user_query": "现金流安全吗？",
            "manager_plan": {"intent": "cashflow_check"},
            "tool_results": [{"tool_name": "get_cashflow_summary"}],
            "specialist_outputs": {"cashflow_agent": {}},
            "assistant_reply": "回复",
            "mode": "fallback",
        },
        db_path=db_path,
    )
    assert get_agent_turn("user_a", "shop_1", turn["turn_id"], db_path=db_path)["manager_plan"]["intent"] == "cashflow_check"
    assert get_agent_turn("user_b", "shop_1", turn["turn_id"], db_path=db_path) is None
    assert len(list_agent_turns("user_a", "shop_1", db_path=db_path)) == 1
