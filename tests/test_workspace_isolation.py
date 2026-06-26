from memory.action_memory_service import list_action_items, upsert_action_item
from memory.admin_service import clear_current_workspace_all_data
from memory.feedback_service import list_user_feedback, submit_feedback
from memory.memory_service import add_business_memory, list_business_memory
from memory.report_service import list_reports, persist_report
from memory.repository import ensure_workspace, list_workspaces
from memory.retrieval import get_memory_context_for_task
from memory.trace_service import list_agent_traces, persist_agent_trace
from memory.turn_service import list_agent_turns, persist_agent_turn


def test_workspace_and_user_isolation(tmp_path):
    db_path = str(tmp_path / "memory.db")
    ensure_workspace("demo_user", "demo_workspace", db_path=db_path)
    ensure_workspace("demo_user", "coffee_shop", db_path=db_path)
    ensure_workspace("other_user", "demo_workspace", db_path=db_path)
    add_business_memory("demo_user", "demo_workspace", "known_supplier", "供应商 A 是长期合作方。", db_path=db_path)
    add_business_memory("demo_user", "coffee_shop", "known_supplier", "咖啡豆供应商 C 是长期合作方。", db_path=db_path)
    add_business_memory("other_user", "demo_workspace", "known_supplier", "其他用户供应商。", db_path=db_path)
    submit_feedback("demo_user", "demo_workspace", "add_business_context", "Demo 反馈。", create_memory=False, db_path=db_path)
    submit_feedback("demo_user", "coffee_shop", "add_business_context", "Coffee 反馈。", create_memory=False, db_path=db_path)
    upsert_action_item("demo_user", "demo_workspace", {"action_id": "A001", "title": "Demo action"}, db_path=db_path)
    upsert_action_item("demo_user", "coffee_shop", {"action_id": "A001", "title": "Coffee action"}, db_path=db_path)
    persist_agent_turn(
        "demo_user",
        "demo_workspace",
        {"turn_id": "turn_demo", "user_query": "Demo query", "assistant_reply": "Demo reply"},
        db_path=db_path,
    )
    persist_agent_turn(
        "demo_user",
        "coffee_shop",
        {"turn_id": "turn_coffee", "user_query": "Coffee query", "assistant_reply": "Coffee reply"},
        db_path=db_path,
    )
    persist_agent_trace("demo_user", "demo_workspace", "turn_demo", {"trace_id": "trace_demo"}, "# Demo", db_path=db_path)
    persist_agent_trace("demo_user", "coffee_shop", "turn_coffee", {"trace_id": "trace_coffee"}, "# Coffee", db_path=db_path)
    persist_report("demo_user", "demo_workspace", "turn_1", "# Demo Report", db_path=db_path)
    persist_report("demo_user", "coffee_shop", "turn_2", "# Coffee Report", db_path=db_path)

    assert {row["workspace_id"] for row in list_workspaces("demo_user", db_path=db_path)} == {"demo_workspace", "coffee_shop"}
    assert {row["workspace_id"] for row in list_workspaces("other_user", db_path=db_path)} == {"demo_workspace"}
    demo_context = get_memory_context_for_task("demo_user", "demo_workspace", db_path=db_path)
    coffee_context = get_memory_context_for_task("demo_user", "coffee_shop", db_path=db_path)
    assert "供应商 A" in demo_context["known_suppliers"][0]
    assert "咖啡豆" in coffee_context["known_suppliers"][0]
    assert list_action_items("demo_user", "demo_workspace", db_path=db_path)[0]["title"] == "Demo action"
    assert list_action_items("demo_user", "coffee_shop", db_path=db_path)[0]["title"] == "Coffee action"
    assert list_user_feedback("demo_user", "demo_workspace", db_path=db_path)[0]["feedback_text"] == "Demo 反馈。"
    assert list_user_feedback("demo_user", "coffee_shop", db_path=db_path)[0]["feedback_text"] == "Coffee 反馈。"
    assert list_agent_turns("demo_user", "demo_workspace", db_path=db_path)[0]["turn_id"] == "turn_demo"
    assert list_agent_turns("demo_user", "coffee_shop", db_path=db_path)[0]["turn_id"] == "turn_coffee"
    assert list_agent_traces("demo_user", "demo_workspace", db_path=db_path)[0]["trace_id"] == "trace_demo"
    assert list_agent_traces("demo_user", "coffee_shop", db_path=db_path)[0]["trace_id"] == "trace_coffee"
    assert list_reports("demo_user", "demo_workspace", db_path=db_path)[0]["report_title"] == "Demo Report"
    assert list_reports("demo_user", "coffee_shop", db_path=db_path)[0]["report_title"] == "Coffee Report"

    clear_current_workspace_all_data("demo_user", "demo_workspace", db_path=db_path)
    assert list_business_memory("demo_user", "demo_workspace", active_only=False, db_path=db_path) == []
    assert list_business_memory("demo_user", "coffee_shop", active_only=False, db_path=db_path)
    assert list_user_feedback("demo_user", "demo_workspace", db_path=db_path) == []
    assert list_user_feedback("demo_user", "coffee_shop", db_path=db_path)
    assert list_agent_turns("demo_user", "demo_workspace", db_path=db_path) == []
    assert list_agent_turns("demo_user", "coffee_shop", db_path=db_path)
