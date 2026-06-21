import pandas as pd

import ui.task_recommendations as task_recommendations


class DummyContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def __getattr__(self, _name):
        return lambda *args, **kwargs: None


class DummyStreamlit:
    session_state = {}

    def __getattr__(self, _name):
        return lambda *args, **kwargs: None

    def columns(self, count):
        return [DummyContext() for _ in range(count)]


def patch_streamlit(monkeypatch):
    monkeypatch.setattr(task_recommendations, "st", DummyStreamlit())


def test_get_dataset_flags_none_returns_false():
    flags = task_recommendations.get_dataset_flags()
    assert flags == {
        "has_transactions": False,
        "has_invoices": False,
        "has_goals": False,
    }


def test_get_dataset_flags_non_empty_dataframe_returns_true():
    flags = task_recommendations.get_dataset_flags(
        transactions_df=pd.DataFrame([{"amount": 1}]),
        invoices_df=pd.DataFrame([{"amount": 2}]),
        goals_df=pd.DataFrame([{"goal": "cash"}]),
    )
    assert flags["has_transactions"] is True
    assert flags["has_invoices"] is True
    assert flags["has_goals"] is True


def test_get_missing_requirements_detects_missing_data():
    task = {"requires": ["transactions", "invoices"]}
    missing = task_recommendations.get_missing_requirements(
        task,
        {"has_transactions": True, "has_invoices": False},
    )
    assert missing == ["invoices"]


def test_build_recommended_tasks_returns_list():
    tasks = task_recommendations.build_recommended_tasks()
    assert tasks


def test_cashflow_check_missing_invoices_is_unavailable():
    tasks = task_recommendations.build_recommended_tasks(
        transactions_df=pd.DataFrame([{"amount": 1}])
    )
    cashflow = next(task for task in tasks if task["task_id"] == "cashflow_check")
    assert cashflow["available"] is False
    assert "发票" in cashflow["disabled_reason"]


def test_anomaly_review_with_transactions_is_available():
    tasks = task_recommendations.build_recommended_tasks(
        transactions_df=pd.DataFrame([{"amount": 1}])
    )
    anomaly = next(task for task in tasks if task["task_id"] == "anomaly_review")
    assert anomaly["available"] is True


def test_goal_plan_missing_goals_is_unavailable():
    tasks = task_recommendations.build_recommended_tasks(
        transactions_df=pd.DataFrame([{"amount": 1}])
    )
    goal = next(task for task in tasks if task["task_id"] == "goal_plan")
    assert goal["available"] is False
    assert "财务目标" in goal["disabled_reason"]


def test_sort_recommended_tasks_puts_available_first():
    tasks = task_recommendations.sort_recommended_tasks(
        [
            {"task_id": "b", "available": False, "priority": "high"},
            {"task_id": "a", "available": True, "priority": "medium"},
        ]
    )
    assert tasks[0]["task_id"] == "a"


def test_get_next_step_hints_no_data_mentions_sample_data():
    hints = task_recommendations.get_next_step_hints()
    assert any("样例数据" in hint for hint in hints)


def test_get_next_step_hints_transactions_mentions_anomaly():
    hints = task_recommendations.get_next_step_hints(
        transactions_df=pd.DataFrame([{"amount": 1}])
    )
    assert any("可疑支出" in hint for hint in hints)


def test_render_recommended_task_cards_supports_empty(monkeypatch):
    patch_streamlit(monkeypatch)
    assert task_recommendations.render_recommended_task_cards([]) is None
