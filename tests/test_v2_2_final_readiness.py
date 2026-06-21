from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_final_docs_exist():
    assert (ROOT / "README.md").exists()
    assert (ROOT / "demo_script.md").exists()
    assert (ROOT / "v2_2_checklist.md").exists()
    assert (ROOT / "docs/v2_2_product_layout_plan.md").exists()
    assert (ROOT / "docs/v2_2_final_demo_plan.md").exists()


def test_readme_contains_v22_final_contract():
    readme = read_text("README.md")
    assert "FinCopilot V2.2" in readme
    assert "Copilot 主界面" in readme
    assert "默认尝试" in readme and "Agent API" in readme
    assert "fallback" in readme
    assert "gpt-5.4-mini" in readme


def test_demo_script_contains_v22_demo():
    demo_script = read_text("demo_script.md")
    assert "FinCopilot V2.2 Demo 演示脚本" in demo_script
    assert "V2.2 Demo" in demo_script


def test_checklist_contains_key_sections():
    checklist = read_text("v2_2_checklist.md")
    assert "Sidebar 导航" in checklist
    assert "Agent API 策略" in checklist
    assert "安全边界" in checklist


def test_env_example_contains_required_v22_defaults():
    env_example = read_text(".env.example")
    assert "OPENAI_AGENT_MODEL=gpt-5.4-mini" in env_example
    assert "OPENAI_MODEL=gpt-5.4-mini" in env_example
    assert "ENABLE_AGENT_API=true" in env_example
