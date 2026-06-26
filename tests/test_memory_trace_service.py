from memory.trace_service import generate_trace_id, get_agent_trace, list_agent_traces, persist_agent_trace


def test_generate_trace_id_has_prefix():
    assert generate_trace_id().startswith("trace_")


def test_persist_get_and_list_agent_traces_scoped(tmp_path):
    db_path = str(tmp_path / "memory.db")
    trace = persist_agent_trace(
        "user_a",
        "shop_1",
        "turn_1",
        trace={"trace_id": "trace_1", "mode": "fallback"},
        trace_markdown="# Trace",
        db_path=db_path,
    )
    assert trace["trace_id"] == "trace_1"
    assert get_agent_trace("user_a", "shop_1", "trace_1", db_path=db_path)["trace"]["mode"] == "fallback"
    assert get_agent_trace("user_b", "shop_1", "trace_1", db_path=db_path) is None
    assert len(list_agent_traces("user_a", "shop_1", db_path=db_path)) == 1
