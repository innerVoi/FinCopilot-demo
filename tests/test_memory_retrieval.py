from memory.memory_service import add_business_memory
from memory.feedback_service import submit_feedback
from memory.retrieval import (
    build_memory_context_summary,
    get_memory_context_for_task,
    infer_memory_types_for_task,
    retrieve_memory_for_task,
    search_business_memory,
)


def test_infer_memory_types_for_task_uses_known_mapping():
    assert "cash_balance" in infer_memory_types_for_task("cashflow_forecast")
    assert "known_supplier" in infer_memory_types_for_task("expense_anomaly")
    assert infer_memory_types_for_task("unknown")


def test_search_business_memory_filters_by_query_and_scope(tmp_path):
    db_path = str(tmp_path / "memory.db")
    add_business_memory(
        "user_a",
        "shop_1",
        "known_supplier",
        "Acme 是咖啡豆常用供应商。",
        entity_name="Acme",
        retrieval_tags=["咖啡豆", "供应商"],
        db_path=db_path,
    )
    add_business_memory(
        "user_a",
        "shop_2",
        "known_supplier",
        "Acme 在另一个工作区。",
        entity_name="Acme",
        db_path=db_path,
    )

    rows = search_business_memory(
        "user_a",
        "shop_1",
        query="咖啡豆",
        memory_types=["known_supplier"],
        db_path=db_path,
    )
    assert len(rows) == 1
    assert rows[0]["workspace_id"] == "shop_1"


def test_retrieve_memory_for_task_falls_back_to_type_when_query_misses(tmp_path):
    db_path = str(tmp_path / "memory.db")
    memory = add_business_memory(
        "user_a",
        "shop_1",
        "cash_balance",
        "当前最低安全现金余额为 30000 元。",
        db_path=db_path,
    )
    rows = retrieve_memory_for_task(
        "user_a",
        "shop_1",
        task_type="cashflow_forecast",
        user_query="完全不匹配",
        db_path=db_path,
    )
    assert [row["memory_id"] for row in rows] == [memory["memory_id"]]


def test_build_memory_context_summary_groups_supported_types():
    summary = build_memory_context_summary(
        [
            {"memory_id": "m1", "memory_type": "known_supplier", "fact_text": "A 是固定供应商。"},
            {"memory_id": "m2", "memory_type": "business_rule", "fact_text": "先付工资。"},
        ]
    )
    assert summary["memory_count"] == 2
    assert summary["known_suppliers"] == ["A 是固定供应商。"]
    assert summary["business_rules"] == ["先付工资。"]
    assert "2 条" in summary["memory_notes"]


def test_get_memory_context_for_task_returns_summary(tmp_path):
    db_path = str(tmp_path / "memory.db")
    add_business_memory(
        "user_a",
        "shop_1",
        "known_risk",
        "上月广告费异常上涨。",
        db_path=db_path,
    )
    summary = get_memory_context_for_task(
        "user_a",
        "shop_1",
        task_type="expense_anomaly",
        db_path=db_path,
    )
    assert summary["memory_count"] == 1
    assert summary["known_risks"] == ["上月广告费异常上涨。"]


def test_submit_feedback_created_memory_can_be_retrieved_for_task(tmp_path):
    db_path = str(tmp_path / "memory.db")
    submit_feedback(
        "user_a",
        "shop_1",
        "update_cash_balance",
        "这是今天账户可用余额。",
        target_metadata={"amount": 12000, "currency": "CNY"},
        db_path=db_path,
    )
    summary = get_memory_context_for_task(
        "user_a",
        "shop_1",
        task_type="cashflow_forecast",
        db_path=db_path,
    )
    assert summary["memory_count"] == 1
    assert "12000" in summary["cash_context"][0]
