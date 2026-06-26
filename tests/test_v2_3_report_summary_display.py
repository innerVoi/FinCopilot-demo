from agent_api.answer_presenter import build_report_card
from agent_api.detail_preview_builder import build_report_preview
import ui.inline_detail_preview as inline_detail_preview
import ui.result_cards as result_cards


LONG_SUMMARY = "这是一段很长的报告摘要。" * 80
REPORT = f"# FinCopilot Report\n\n{LONG_SUMMARY}\n\n## 详情\n\n完整报告正文。"


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

    def expander(self, *args, **kwargs):
        return DummyContext()


def test_build_report_card_separates_title_and_summary():
    card = build_report_card({"report_markdown": REPORT})
    assert card["available"] is True
    assert card["title"] == "Multi-Agent 对话报告"
    assert "报告摘要" not in card["title"]
    assert LONG_SUMMARY[:20] in card["summary"]
    assert len(card["title"]) < 40


def test_build_report_preview_separates_title_and_summary():
    preview = build_report_preview({"report_markdown": REPORT})
    assert preview["has_report"] is True
    assert preview["report_title"] == "FinCopilot Multi-Agent 对话报告"
    assert LONG_SUMMARY[:20] in preview["report_summary"]
    assert len(preview["report_title"]) < 60


def test_render_report_card_supports_long_summary(monkeypatch):
    monkeypatch.setattr(result_cards, "st", DummyStreamlit())
    result_cards.render_report_card(build_report_card({"report_markdown": REPORT}), report_markdown=REPORT)


def test_render_report_preview_supports_long_summary(monkeypatch):
    monkeypatch.setattr(inline_detail_preview, "st", DummyStreamlit())
    inline_detail_preview.render_report_preview(build_report_preview({"report_markdown": REPORT}), {"report_markdown": REPORT})
