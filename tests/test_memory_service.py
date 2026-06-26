import pytest

from memory.memory_service import (
    add_business_memory,
    count_business_memory,
    deactivate_business_memory,
    get_business_memory,
    list_business_memory,
    normalize_structured_value,
    parse_structured_value,
    update_memory_last_used,
    validate_memory_type,
)


def test_validate_memory_type_rejects_unknown_type():
    with pytest.raises(ValueError):
        validate_memory_type("unknown")


def test_structured_value_round_trip():
    value = {"amount": 1200, "currency": "CNY"}
    encoded = normalize_structured_value(value)
    assert parse_structured_value(encoded) == value


def test_add_get_and_list_business_memory_scoped_by_user_and_workspace(tmp_path):
    db_path = str(tmp_path / "memory.db")
    memory = add_business_memory(
        user_id="user_a",
        workspace_id="shop_1",
        memory_type="known_supplier",
        entity_name="Acme",
        fact_text="Acme 是常用供应商。",
        retrieval_tags=["supplier", "acme"],
        db_path=db_path,
    )
    add_business_memory(
        user_id="user_b",
        workspace_id="shop_1",
        memory_type="known_supplier",
        fact_text="另一个用户的供应商。",
        db_path=db_path,
    )

    fetched = get_business_memory("user_a", "shop_1", memory["memory_id"], db_path=db_path)
    assert fetched["fact_text"] == "Acme 是常用供应商。"
    assert get_business_memory("user_b", "shop_1", memory["memory_id"], db_path=db_path) is None

    rows = list_business_memory("user_a", "shop_1", db_path=db_path)
    assert len(rows) == 1
    assert rows[0]["user_id"] == "user_a"
    assert rows[0]["workspace_id"] == "shop_1"
    assert count_business_memory("user_a", "shop_1", db_path=db_path) == 1


def test_deactivate_business_memory_hides_from_active_list(tmp_path):
    db_path = str(tmp_path / "memory.db")
    memory = add_business_memory(
        "user_a",
        "shop_1",
        "known_risk",
        "某供应商付款存在争议。",
        db_path=db_path,
    )
    assert deactivate_business_memory("user_a", "shop_1", memory["memory_id"], db_path=db_path)
    assert list_business_memory("user_a", "shop_1", active_only=True, db_path=db_path) == []
    assert len(list_business_memory("user_a", "shop_1", active_only=False, db_path=db_path)) == 1


def test_update_memory_last_used_is_scoped(tmp_path):
    db_path = str(tmp_path / "memory.db")
    memory = add_business_memory(
        "user_a",
        "shop_1",
        "business_rule",
        "优先保障工资和房租。",
        db_path=db_path,
    )
    assert update_memory_last_used("user_b", "shop_1", [memory["memory_id"]], db_path=db_path) == 0
    assert update_memory_last_used("user_a", "shop_1", [memory["memory_id"]], db_path=db_path) == 1
    fetched = get_business_memory("user_a", "shop_1", memory["memory_id"], db_path=db_path)
    assert fetched["last_used_at"]
