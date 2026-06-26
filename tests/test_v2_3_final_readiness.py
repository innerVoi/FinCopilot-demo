from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_v2_3_final_docs_exist():
    assert (ROOT / "README.md").exists()
    assert (ROOT / "demo_script.md").exists()
    assert (ROOT / "v2_3_checklist.md").exists()
    assert (ROOT / "docs/v2_3_memory_design.md").exists()
    assert (ROOT / "docs/v2_3_rag_future_plan.md").exists()


def test_readme_contains_v2_3_final_contract():
    readme = read_text("README.md")
    assert "FinCopilot V2.3" in readme
    assert "Memory-Augmented Agentic CFO Copilot" in readme
    assert "user_id" in readme
    assert "workspace_id" in readme
    assert "Action Lifecycle" in readme
    assert "RAG" in readme


def test_demo_script_contains_v2_3_demo_path():
    demo_script = read_text("demo_script.md")
    assert "V2.3 Demo" in demo_script
    assert "Workspace Isolation" in demo_script
    assert "Action Lifecycle" in demo_script


def test_v2_3_checklist_contains_key_sections():
    checklist = read_text("v2_3_checklist.md")
    assert "Memory-Augmented Agent" in checklist
    assert "Action Lifecycle" in checklist
    assert "RAG 铺垫" in checklist


def test_env_example_contains_v2_3_memory_defaults():
    env_example = read_text(".env.example")
    assert "FINCOPILOT_MEMORY_DB_PATH" in env_example
    assert "FINCOPILOT_DEFAULT_USER_ID" in env_example
    assert "FINCOPILOT_DEFAULT_WORKSPACE_ID" in env_example
