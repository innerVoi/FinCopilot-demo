from agent_api.response_composer import compose_agent_trace_summary, compose_final_answer


def test_compose_final_answer_contains_required_sections():
    answer = compose_final_answer(
        "未来 30 天现金流安全吗？",
        manager_plan={"intent": "cashflow_check", "user_goal": "检查现金流"},
        specialist_outputs={
            "cashflow_agent": {
                "result": {
                    "agent_name": "cashflow_agent",
                    "summary": "现金流存在压力。",
                    "findings": ["未来 30 天有付款压力。"],
                    "risks": ["回款延迟会影响余额。"],
                    "recommended_actions": ["确认真实余额。"],
                    "questions": ["未来 30 天是否有回款？"],
                    "needs_user_input": True,
                    "confidence": "medium",
                    "safety_note": "safe",
                }
            }
        },
    )
    assert "任务理解" in answer
    assert "专业 Agent 发现" in answer
    assert "建议行动" in answer
    assert "安全边界" in answer


def test_compose_agent_trace_summary_returns_dict():
    trace = compose_agent_trace_summary(
        manager_result={"mode": "fallback", "manager_plan": {"intent": "cashflow_check"}},
        specialist_outputs={"cashflow_agent": {"mode": "fallback"}},
        tool_results=[{"tool_name": "get_cashflow_summary", "status": "success"}],
    )
    assert trace["manager_mode"] == "fallback"
    assert trace["tool_success_count"] == 1
    assert trace["specialist_agents"] == ["cashflow_agent"]


def test_empty_specialist_outputs_does_not_crash():
    answer = compose_final_answer("hello")
    assert isinstance(answer, str)
    assert "任务理解" in answer
