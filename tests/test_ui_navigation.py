from ui.navigation import V22_PAGES


def test_v22_pages_contains_new_main_entries():
    assert "Copilot Home" in V22_PAGES
    assert "Analysis Details" in V22_PAGES
    assert "Actions & Reports" in V22_PAGES
    assert "Data & Settings" in V22_PAGES


def test_v22_pages_hides_v21_top_level_entries():
    assert "助理首页" not in V22_PAGES
    assert "和 FinCopilot 对话" not in V22_PAGES
    assert "Agent 工作台" not in V22_PAGES
    assert "财务分析" not in V22_PAGES
    assert "行动中心" not in V22_PAGES
    assert "报告中心" not in V22_PAGES
    assert "数据管理" not in V22_PAGES


def test_v22_pages_has_four_entries():
    assert len(V22_PAGES) == 4


def test_v22_default_page_is_copilot_main():
    assert V22_PAGES[0] == "Copilot Home"
