from memory.memory_service import update_memory_last_used
from memory.retrieval import get_memory_context_for_task
from memory.workspace import get_default_user_id, get_default_workspace_id


def infer_task_type_from_manager_plan(manager_plan: dict | None) -> str:
    manager_plan = manager_plan or {}
    return str(manager_plan.get("intent") or manager_plan.get("task_type") or "general_finance_summary")


def infer_initial_task_type(user_query: str | None) -> str:
    query = str(user_query or "").lower()
    if any(keyword in query for keyword in ["cash flow", "cashflow", "balance", "receivable", "collection"]):
        return "cashflow_check"
    if any(keyword in query for keyword in ["anomaly", "suspicious", "expense", "review"]):
        return "expense_anomaly_review"
    if any(keyword in query for keyword in ["invoice", "payment", "due", "overdue"]):
        return "invoice_or_payment_review"
    if any(keyword in query for keyword in ["goal", "budget", "plan"]):
        return "goal_or_budget_planning"
    return "general_finance_summary"


def build_memory_augmented_context(
    user_id: str,
    workspace_id: str,
    user_query: str | None,
    agent_context_summary: dict | None = None,
    task_type: str | None = None,
    db_path: str | None = None,
) -> dict:
    context_summary = dict(agent_context_summary or {})
    resolved_task_type = task_type or infer_initial_task_type(user_query)
    memory_context = get_memory_context_for_task(
        user_id=user_id,
        workspace_id=workspace_id,
        task_type=resolved_task_type,
        user_query=user_query,
        limit=12,
        db_path=db_path,
    )
    context_summary["memory_context"] = memory_context
    return context_summary


def build_memory_trace(
    user_id: str,
    workspace_id: str,
    task_type: str,
    memory_context: dict | None,
) -> dict:
    memory_context = memory_context or {}
    memory_count = int(memory_context.get("memory_count") or 0)
    return {
        "user_id": user_id,
        "workspace_id": workspace_id,
        "task_type": task_type or "general_finance_summary",
        "memory_count": memory_count,
        "used_memory_ids": list(memory_context.get("used_memory_ids") or []),
        "memory_augmented": memory_count > 0,
        "retrieval_scope": "current_user_current_workspace_only",
        "notes": [
            "Memory retrieval was restricted to the current user_id and workspace_id.",
        ],
    }


def mark_used_memories(
    user_id: str,
    workspace_id: str,
    memory_context: dict | None,
    db_path: str | None = None,
) -> int:
    used_memory_ids = list((memory_context or {}).get("used_memory_ids") or [])
    if not used_memory_ids:
        return 0
    return update_memory_last_used(
        user_id=user_id,
        workspace_id=workspace_id,
        memory_ids=used_memory_ids,
        db_path=db_path,
    )


def prepare_memory_for_agent_turn(
    user_id: str | None,
    workspace_id: str | None,
    user_query: str | None,
    agent_context_summary: dict | None = None,
    task_type: str | None = None,
    db_path: str | None = None,
) -> dict:
    resolved_user_id = user_id or get_default_user_id()
    resolved_workspace_id = workspace_id or get_default_workspace_id()
    resolved_task_type = task_type or infer_initial_task_type(user_query)
    augmented_context = build_memory_augmented_context(
        user_id=resolved_user_id,
        workspace_id=resolved_workspace_id,
        user_query=user_query,
        agent_context_summary=agent_context_summary,
        task_type=resolved_task_type,
        db_path=db_path,
    )
    memory_context = augmented_context.get("memory_context", {})
    mark_used_memories(
        user_id=resolved_user_id,
        workspace_id=resolved_workspace_id,
        memory_context=memory_context,
        db_path=db_path,
    )
    return {
        "agent_context_summary": augmented_context,
        "memory_context": memory_context,
        "memory_trace": build_memory_trace(
            user_id=resolved_user_id,
            workspace_id=resolved_workspace_id,
            task_type=resolved_task_type,
            memory_context=memory_context,
        ),
        "task_type": resolved_task_type,
    }
