import ui.memory_panel as memory_panel


class DummyContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def __getattr__(self, _name):
        return lambda *args, **kwargs: None


class DummyStreamlit:
    def __init__(self):
        self.messages = []

    def __getattr__(self, name):
        def recorder(*args, **kwargs):
            self.messages.append((name, args, kwargs))
            return None

        return recorder

    def expander(self, *args, **kwargs):
        return DummyContext()

    def button(self, *args, **kwargs):
        return False

    def selectbox(self, label, options, **kwargs):
        return options[0] if options else None


def test_render_memory_context_summary_empty(monkeypatch):
    dummy = DummyStreamlit()
    monkeypatch.setattr(memory_panel, "st", dummy)
    memory_panel.render_memory_context_summary({"memory_count": 0})
    assert any(call[0] == "info" for call in dummy.messages)


def test_render_memory_context_summary_with_items(monkeypatch):
    dummy = DummyStreamlit()
    monkeypatch.setattr(memory_panel, "st", dummy)
    memory_panel.render_memory_context_summary(
        {
            "memory_count": 1,
            "memory_notes": "本次分析可参考 1 条历史业务记忆。",
            "known_suppliers": ["A 是固定供应商。"],
        }
    )
    assert any(call[0] == "subheader" for call in dummy.messages)
    assert any(call[0] == "markdown" for call in dummy.messages)


def test_render_memory_management_panel_callable(monkeypatch):
    dummy = DummyStreamlit()
    monkeypatch.setattr(memory_panel, "st", dummy)
    monkeypatch.setattr(memory_panel, "count_business_memory", lambda *args, **kwargs: 1)
    monkeypatch.setattr(
        memory_panel,
        "list_business_memory",
        lambda *args, **kwargs: [
            {
                "memory_id": "m1",
                "memory_type": "known_supplier",
                "fact_text": "A 是固定供应商。",
                "is_active": True,
            }
        ],
    )
    memory_panel.render_memory_management_panel("user_a", "shop_1", db_path="/tmp/test.db")
    assert any(call[0] == "metric" for call in dummy.messages)
