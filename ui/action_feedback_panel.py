import hashlib

import streamlit as st

from memory.action_memory_service import get_action_item
from memory.feedback_service import list_action_item_feedback, submit_feedback


ACTION_FEEDBACK_OPTIONS = {
    "complete_action": "Completed",
    "ignore_action": "Ignore for now",
    "reject_suggestion": "Not suitable",
    "needs_follow_up": "Needs follow-up",
}


def _get_db_path() -> str | None:
    session_state = getattr(st, "session_state", None)
    if hasattr(session_state, "get"):
        return session_state.get("memory_db_path")
    return None


def extract_action_id(action_item: dict, fallback_index: int | None = None) -> str:
    action_item = action_item or {}
    for key in ["action_id", "id", "target_id"]:
        value = action_item.get(key)
        if value not in [None, ""]:
            return str(value)
    basis = "|".join(
        str(action_item.get(key, ""))
        for key in ["title", "description", "priority", "source"]
    )
    if fallback_index is not None:
        basis = f"{basis}|{fallback_index}"
    digest = hashlib.sha1(basis.encode("utf-8")).hexdigest()[:12]
    return f"action_{digest}"


def build_action_target_metadata(action_item: dict) -> dict:
    action_item = action_item or {}
    return {
        "action_id": extract_action_id(action_item),
        "title": action_item.get("title") or action_item.get("description") or "",
        "description": action_item.get("description") or "",
        "priority": action_item.get("priority") or "medium",
        "status": action_item.get("status") or "pending",
        "source": action_item.get("source") or "",
    }


def render_action_feedback_form(
    user_id: str,
    workspace_id: str,
    action_item: dict,
    turn_id: str | None = None,
    key_prefix: str = "action_feedback",
) -> None:
    action_item = action_item or {}
    action_id = extract_action_id(action_item)
    try:
        persisted_action = get_action_item(user_id, workspace_id, action_id, db_path=_get_db_path())
    except Exception:
        persisted_action = None
    if persisted_action and persisted_action.get("status") != "pending":
        metadata = persisted_action.get("metadata") or {}
        feedback = metadata.get("feedback") or {}
        st.info(f"This action item has already been handled: {persisted_action.get('status')}. Duplicate feedback is not allowed.")
        if feedback.get("feedback_reason"):
            st.caption(f"Handling reason: {feedback.get('feedback_reason')}")
        return
    title = action_item.get("title") or action_item.get("description") or action_id
    st.markdown(f"**{title}**")
    feedback_type = st.selectbox(
        "Feedback Type",
        list(ACTION_FEEDBACK_OPTIONS.keys()),
        format_func=lambda value: ACTION_FEEDBACK_OPTIONS.get(value, value),
        key=f"{key_prefix}_{action_id}_type",
    )
    reason_text = st.text_area(
        "Feedback Reason",
        key=f"{key_prefix}_{action_id}_reason",
        placeholder="Add a reason so FinCopilot can remember the handling context.",
    )
    if st.button("Submit Action Item Feedback", key=f"{key_prefix}_{action_id}_submit"):
        if not str(reason_text or "").strip():
            st.warning("Please add a feedback reason so FinCopilot can remember the handling context.")
            return
        try:
            submit_feedback(
                user_id=user_id,
                workspace_id=workspace_id,
                feedback_type=feedback_type,
                feedback_text=reason_text,
                turn_id=turn_id,
                target_type="action_item",
                target_id=action_id,
                target_metadata=build_action_target_metadata(action_item),
                create_memory=False,
                db_path=_get_db_path(),
            )
            st.success("Action item feedback has been saved and moved into handled action items.")
            st.rerun()
        except Exception as exc:
            st.error(f"Failed to save action item feedback: {exc}")


def render_action_feedback_list(
    user_id: str,
    workspace_id: str,
    action_items: list[dict] | None,
    turn_id: str | None = None,
) -> None:
    items = [item for item in (action_items or []) if isinstance(item, dict)]
    st.subheader("Action Item Feedback")
    if not items:
        st.info("No action items are available for feedback yet.")
        return
    for index, item in enumerate(items[:10]):
        action_id = extract_action_id(item, fallback_index=index)
        with st.expander(f"{index + 1}. {item.get('title') or item.get('description') or action_id}", expanded=False):
            item = {**item, "action_id": action_id}
            render_action_feedback_form(
                user_id=user_id,
                workspace_id=workspace_id,
                action_item=item,
                turn_id=turn_id,
                key_prefix=f"action_feedback_{index}",
            )


def render_action_feedback_history(user_id: str, workspace_id: str) -> None:
    st.subheader("Action Item Feedback History")
    try:
        rows = list_action_item_feedback(
            user_id=user_id,
            workspace_id=workspace_id,
            limit=100,
            db_path=_get_db_path(),
        )
    except Exception as exc:
        st.warning(f"Action item feedback history is temporarily unavailable: {exc}")
        return
    if not rows:
        st.info("No action item feedback exists in the current workspace yet.")
        return
    st.dataframe(
        [
            {
                "created_at": row.get("created_at"),
                "action_id": row.get("target_id"),
                "feedback_type": row.get("feedback_type"),
                "reason": row.get("feedback_text"),
            }
            for row in rows
        ],
        use_container_width=True,
        hide_index=True,
    )
