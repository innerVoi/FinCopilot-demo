from agent.progress_tracker import (
    filter_actions_by_status,
    get_recent_progress_events,
    get_top_active_actions,
    is_active_status,
    is_closed_status,
    normalize_status,
    summarize_progress,
)


def make_actions():
    return [
        {"action_id": "A001", "priority": "high", "source": "cashflow", "status": "pending", "rank_score": 42},
        {"action_id": "A002", "priority": "medium", "source": "invoice", "status": "done", "rank_score": 30},
        {"action_id": "A003", "priority": "high", "source": "model_anomaly", "status": "needs_follow_up", "rank_score": 35},
        {"action_id": "A004", "priority": "low", "source": "clarification", "status": "ignored", "rank_score": 10},
    ]


def test_normalize_status_handles_valid_and_invalid_values():
    assert normalize_status("done") == "done"
    assert normalize_status("bad") == "pending"
    assert normalize_status(None) == "pending"


def test_closed_and_active_status_detection():
    assert is_closed_status("done")
    assert is_closed_status("ignored")
    assert is_closed_status("verified_normal")
    assert is_active_status("pending")
    assert is_active_status("in_progress")
    assert is_active_status("needs_follow_up")


def test_summarize_progress_counts_statuses():
    summary = summarize_progress(make_actions())

    assert summary["total"] == 4
    assert summary["active_count"] == 2
    assert summary["closed_count"] == 2
    assert summary["completion_rate"] == 0.5
    assert summary["high_priority_active_count"] == 2


def test_filter_actions_by_status_filters_items():
    result = filter_actions_by_status(make_actions(), status="done")

    assert len(result) == 1
    assert result[0]["action_id"] == "A002"


def test_get_top_active_actions_returns_open_items():
    result = get_top_active_actions(make_actions(), n=2)

    assert len(result) == 2
    assert all(item["status"] in {"pending", "needs_follow_up"} for item in result)
    assert result[0]["priority"] == "high"


def test_get_recent_progress_events_reads_history():
    state = {
        "progress_history": [
            {"action_id": "A001", "new_status": "done"},
            {"action_id": "A002", "new_status": "ignored"},
        ]
    }

    events = get_recent_progress_events(state, limit=1)

    assert events == [{"action_id": "A002", "new_status": "ignored"}]
