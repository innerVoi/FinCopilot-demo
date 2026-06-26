RESPONSIBLE_FINANCE_DISCLAIMER = (
    "This analysis is for financial organization, risk reminders, and educational support only. "
    "It is not investment, tax, legal, debt-resolution, or professional financial advice. "
    "Review source documents before important financial decisions and consult qualified professionals when needed."
)

PROHIBITED_ADVICE_TOPICS = [
    "investment advice",
    "tax advice",
    "legal advice",
    "debt-resolution advice",
    "return promises",
    "fraud determinations",
]


def get_disclaimer() -> str:
    """
    Return the standard responsible-finance disclaimer.
    """
    return RESPONSIBLE_FINANCE_DISCLAIMER


def append_disclaimer(text: str) -> str:
    """
    Append the disclaimer if it is not already present.
    """
    text = text or ""
    disclaimer = get_disclaimer()
    if disclaimer in text:
        return text
    if not text.strip():
        return disclaimer
    return f"{text.rstrip()}\n\n{disclaimer}"


def build_finance_safety_instruction() -> str:
    """
    Build a safety instruction string for LLM prompts.
    """
    topics = ", ".join(PROHIBITED_ADVICE_TOPICS)
    return (
        "You are a responsible financial organization and risk-reminder assistant. "
        "Explain only from uploaded data and system analysis results. Do not determine fraud, "
        f"and do not provide investment, tax, legal, debt-resolution advice, or return promises. "
        f"Prohibited topics include: {topics}. For important matters, advise users to review source documents "
        "or consult qualified professionals."
    )


def sanitize_llm_output(text: str) -> str:
    """
    Apply minimal safety post-processing to LLM text output.
    """
    return append_disclaimer(text or "")
