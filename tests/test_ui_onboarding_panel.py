import pandas as pd

import ui.onboarding_panel as onboarding_panel


class DummyContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def __getattr__(self, _name):
        return lambda *args, **kwargs: None


class DummyStreamlit:
    def __getattr__(self, _name):
        return lambda *args, **kwargs: None

    def columns(self, count):
        return [DummyContext() for _ in range(count)]

    def container(self, *args, **kwargs):
        return DummyContext()


def patch_streamlit(monkeypatch):
    monkeypatch.setattr(onboarding_panel, "st", DummyStreamlit())


def test_infer_onboarding_state_no_data():
    assert onboarding_panel.infer_onboarding_state() == "no_data"


def test_infer_onboarding_state_partial_data():
    state = onboarding_panel.infer_onboarding_state(
        transactions_df=pd.DataFrame([{"amount": 1}])
    )
    assert state == "partial_data"


def test_infer_onboarding_state_after_first_turn():
    assert onboarding_panel.infer_onboarding_state(latest_agent_turn={"mode": "fallback"}) == "after_first_turn"


def test_fallback_mode_has_friendly_message():
    state = onboarding_panel.infer_onboarding_state(
        transactions_df=pd.DataFrame([{"amount": 1}]),
        invoices_df=pd.DataFrame([{"amount": 2}]),
        agent_api_status={"mode": "fallback", "user_message": "当前真实 Agent 暂不可用，系统将自动使用 fallback 分析。"},
    )
    message = onboarding_panel.build_onboarding_messages(
        state,
        agent_api_status={"mode": "fallback", "user_message": "当前真实 Agent 暂不可用，系统将自动使用 fallback 分析。"},
    )
    assert state == "fallback_mode"
    assert "fallback" in message["description"]


def test_build_onboarding_messages_returns_required_fields():
    message = onboarding_panel.build_onboarding_messages("no_data")
    assert {"title", "description", "tips"}.issubset(message)


def test_render_onboarding_panel_supports_none(monkeypatch):
    patch_streamlit(monkeypatch)
    onboarding_panel.render_onboarding_panel()
