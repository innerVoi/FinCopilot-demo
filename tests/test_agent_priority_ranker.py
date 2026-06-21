from agent.action_item import make_action_item
from agent.priority_ranker import (
    action_items_to_dataframe,
    compute_action_rank_score,
    filter_action_items,
    rank_action_items,
    summarize_action_items,
)


def make_item(action_id, priority, source):
    return make_action_item(
        action_id=action_id,
        title=f"{priority} {source}",
        description="说明",
        source=source,
        priority=priority,
        reason="原因",
        suggested_deadline="今天" if priority == "high" else "7 天内",
        recommended_steps=["步骤"],
    )


def test_compute_action_rank_score_returns_int():
    score = compute_action_rank_score(make_item("A001", "high", "cashflow"))

    assert isinstance(score, int)


def test_high_priority_scores_above_medium():
    high_score = compute_action_rank_score(make_item("A001", "high", "cashflow"))
    medium_score = compute_action_rank_score(make_item("A002", "medium", "cashflow"))

    assert high_score > medium_score


def test_rank_action_items_orders_by_score():
    items = [
        make_item("A001", "low", "clarification"),
        make_item("A002", "high", "cashflow"),
    ]

    ranked = rank_action_items(items)

    assert ranked[0]["priority"] == "high"
    assert "rank_score" in ranked[0]


def test_filter_action_items_by_priority_and_source():
    items = [
        make_item("A001", "high", "cashflow"),
        make_item("A002", "medium", "invoice"),
    ]

    assert len(filter_action_items(items, priority="high")) == 1
    assert len(filter_action_items(items, source="invoice")) == 1


def test_summarize_action_items_counts_items():
    items = [
        make_item("A001", "high", "cashflow"),
        make_item("A002", "medium", "invoice"),
    ]

    summary = summarize_action_items(items)

    assert summary["total"] == 2
    assert summary["high"] == 1
    assert summary["medium"] == 1
    assert summary["by_source"]["cashflow"] == 1


def test_action_items_to_dataframe_returns_dataframe():
    df = action_items_to_dataframe([make_item("A001", "high", "cashflow")])

    assert not df.empty
    assert "action_id" in df.columns
