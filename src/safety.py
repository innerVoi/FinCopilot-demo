RESPONSIBLE_FINANCE_DISCLAIMER = (
    "本分析仅用于财务整理、风险提醒和教育性支持，"
    "不构成投资、税务、法律、债务处置或专业财务建议。"
    "重要交易和财务决策请核查原始凭证，并在必要时咨询合格专业人士。"
)

PROHIBITED_ADVICE_TOPICS = [
    "投资建议",
    "税务建议",
    "法律建议",
    "债务处置建议",
    "收益承诺",
    "欺诈认定",
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
    topics = "、".join(PROHIBITED_ADVICE_TOPICS)
    return (
        "你是一个负责任的财务整理与风险提醒助手。只能基于用户上传数据和"
        "系统分析结果进行解释；不得认定欺诈；不得提供投资、税务、法律、"
        f"债务处置建议或收益承诺。禁止主题包括：{topics}。"
        "重要事项应建议用户核查原始凭证或咨询合格专业人士。"
    )


def sanitize_llm_output(text: str) -> str:
    """
    Apply minimal safety post-processing to LLM text output.
    """
    return append_disclaimer(text or "")
