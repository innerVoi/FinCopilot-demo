from agent_api.memory_orchestrator import (
    build_memory_augmented_context,
    build_memory_trace,
    infer_initial_task_type,
    infer_task_type_from_manager_plan,
    mark_used_memories,
    prepare_memory_for_agent_turn,
)
from memory.memory_service import add_business_memory, get_business_memory


def test_infer_initial_task_type_by_keywords():
    assert infer_initial_task_type("未来现金流够不够？") == "cashflow_check"
    assert infer_initial_task_type("这个月哪些支出可疑？") == "expense_anomaly_review"
    assert infer_initial_task_type("有哪些发票到期？") == "invoice_or_payment_review"
    assert infer_initial_task_type("预算目标怎么计划？") == "goal_or_budget_planning"
    assert infer_initial_task_type("总结一下") == "general_finance_summary"


def test_infer_task_type_from_manager_plan():
    assert infer_task_type_from_manager_plan({"intent": "cashflow_check"}) == "cashflow_check"
    assert infer_task_type_from_manager_plan(None) == "general_finance_summary"


def test_build_memory_augmented_context_injects_memory_context(tmp_path):
    db_path = str(tmp_path / "memory.db")
    add_business_memory(
        "user_a",
        "shop_1",
        "cash_balance",
        "当前现金余额为 12000 元。",
        db_path=db_path,
    )
    context = build_memory_augmented_context(
        "user_a",
        "shop_1",
        "现金流安全吗？",
        {"cashflow_summary": {"risk_level": "medium"}},
        db_path=db_path,
    )
    assert context["cashflow_summary"]["risk_level"] == "medium"
    assert context["memory_context"]["memory_count"] == 1
    assert context["memory_context"]["cash_context"] == ["当前现金余额为 12000 元。"]


def test_build_memory_trace_contains_scope():
    trace = build_memory_trace(
        "user_a",
        "shop_1",
        "cashflow_check",
        {"memory_count": 1, "used_memory_ids": ["mem_1"]},
    )
    assert trace["retrieval_scope"] == "current_user_current_workspace_only"
    assert trace["memory_augmented"] is True


def test_mark_used_memories_updates_last_used(tmp_path):
    db_path = str(tmp_path / "memory.db")
    memory = add_business_memory(
        "user_a",
        "shop_1",
        "known_supplier",
        "A 是长期供应商。",
        db_path=db_path,
    )
    count = mark_used_memories(
        "user_a",
        "shop_1",
        {"used_memory_ids": [memory["memory_id"]]},
        db_path=db_path,
    )
    assert count == 1
    assert get_business_memory("user_a", "shop_1", memory["memory_id"], db_path=db_path)["last_used_at"]


def test_prepare_memory_for_agent_turn_returns_all_parts(tmp_path):
    db_path = str(tmp_path / "memory.db")
    add_business_memory(
        "user_a",
        "shop_1",
        "known_risk",
        "广告费近期需要持续核查。",
        db_path=db_path,
    )
    payload = prepare_memory_for_agent_turn(
        "user_a",
        "shop_1",
        "哪些支出可疑？",
        db_path=db_path,
    )
    assert payload["agent_context_summary"]["memory_context"]["memory_count"] == 1
    assert payload["memory_trace"]["memory_augmented"] is True
    assert payload["task_type"] == "expense_anomaly_review"
