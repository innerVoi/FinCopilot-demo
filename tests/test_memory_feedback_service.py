import pytest

from memory.feedback_service import (
    add_user_feedback,
    build_memory_fact_from_feedback,
    count_user_feedback,
    list_action_item_feedback,
    list_user_feedback,
    submit_feedback,
    validate_feedback_type,
)
from memory.memory_service import list_business_memory


def test_validate_feedback_type_accepts_supported_type():
    assert validate_feedback_type("confirm_normal_payment") == "confirm_normal_payment"
    assert validate_feedback_type("needs_follow_up") == "needs_follow_up"


def test_validate_feedback_type_rejects_unknown_type():
    with pytest.raises(ValueError):
        validate_feedback_type("unknown")


def test_add_and_list_user_feedback_scoped_by_user_workspace(tmp_path):
    db_path = str(tmp_path / "memory.db")
    add_user_feedback(
        "user_a",
        "shop_1",
        "confirm_supplier",
        "A 是长期供应商。",
        db_path=db_path,
    )
    add_user_feedback(
        "user_b",
        "shop_1",
        "confirm_supplier",
        "B 是长期供应商。",
        db_path=db_path,
    )

    rows = list_user_feedback("user_a", "shop_1", db_path=db_path)
    assert len(rows) == 1
    assert rows[0]["user_id"] == "user_a"
    assert rows[0]["workspace_id"] == "shop_1"
    assert count_user_feedback("user_a", "shop_1", db_path=db_path) == 1


def test_build_memory_fact_from_feedback_converts_supported_types():
    normal_payment = build_memory_fact_from_feedback(
        "confirm_normal_payment",
        "这笔采购款正常。",
        {"merchant": "Acme", "amount": 800},
    )
    supplier = build_memory_fact_from_feedback(
        "confirm_supplier",
        "长期合作。",
        {"merchant": "Acme"},
    )
    cash = build_memory_fact_from_feedback(
        "update_cash_balance",
        "今天账户可用余额。",
        {"amount": 12000, "currency": "CNY"},
    )
    assert normal_payment["memory_type"] == "known_normal_payment"
    assert supplier["memory_type"] == "known_supplier"
    assert cash["memory_type"] == "cash_balance"


def test_build_memory_fact_from_feedback_returns_none_for_action_feedback():
    assert build_memory_fact_from_feedback("complete_action", "已完成。") is None


def test_submit_feedback_creates_business_memory_for_high_value_feedback(tmp_path):
    db_path = str(tmp_path / "memory.db")
    result = submit_feedback(
        "user_a",
        "shop_1",
        "confirm_normal_payment",
        "这是正常采购。",
        target_type="transaction",
        target_metadata={"merchant": "Acme", "amount": 800},
        db_path=db_path,
    )
    assert result["memory_created"] is True
    memories = list_business_memory("user_a", "shop_1", db_path=db_path)
    assert len(memories) == 1
    assert memories[0]["memory_type"] == "known_normal_payment"


def test_submit_feedback_action_feedback_only_writes_feedback(tmp_path):
    db_path = str(tmp_path / "memory.db")
    result = submit_feedback(
        "user_a",
        "shop_1",
        "complete_action",
        "行动项已完成。",
        target_type="action_item",
        db_path=db_path,
    )
    assert result["memory_created"] is False
    assert count_user_feedback("user_a", "shop_1", db_path=db_path) == 1
    assert list_business_memory("user_a", "shop_1", db_path=db_path) == []


def test_list_action_item_feedback_filters_target_type_and_action_id(tmp_path):
    db_path = str(tmp_path / "memory.db")
    submit_feedback(
        "user_a",
        "shop_1",
        "needs_follow_up",
        "还需要继续联系客户。",
        target_type="action_item",
        target_id="A001",
        create_memory=False,
        db_path=db_path,
    )
    submit_feedback(
        "user_a",
        "shop_1",
        "add_business_context",
        "门店周末客流更高。",
        target_type="general_feedback",
        create_memory=False,
        db_path=db_path,
    )
    rows = list_action_item_feedback("user_a", "shop_1", action_id="A001", db_path=db_path)
    assert len(rows) == 1
    assert rows[0]["target_id"] == "A001"
