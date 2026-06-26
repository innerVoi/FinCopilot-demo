from agent_api.config import get_agent_api_status, get_openai_api_key, get_openai_base_url


def sanitize_openai_error(error: Exception) -> str:
    """
    Convert OpenAI SDK errors into safe, actionable UI messages.
    """
    text = str(error)
    if "Incorrect API key provided" in text or "401" in text:
        return "The OpenAI API key is invalid or rejected. Check OPENAI_API_KEY, confirm it has not expired, and restart Streamlit after changes."
    if "model" in text.lower() and ("not found" in text.lower() or "does not exist" in text.lower() or "404" in text):
        return "The configured OpenAI model is unavailable. Check whether OPENAI_AGENT_MODEL / OPENAI_MODEL is available to this account, then restart Streamlit."
    if "permission" in text.lower() or "access" in text.lower() or "403" in text:
        return "The current API key does not have access to the selected model. Use an available model or check account permissions."
    if "rate limit" in text.lower() or "429" in text:
        return "The OpenAI API is currently rate-limited. Try again later or check account quota."
    return text


def get_openai_client():
    """
    Create an OpenAI client when an API key is configured.
    This function does not send any API request.
    """
    api_key = get_openai_api_key()
    if not api_key:
        return None
    try:
        from openai import OpenAI
    except ImportError:
        return None
    return OpenAI(api_key=api_key, base_url=get_openai_base_url())


def _get_nested_value(data, path: list):
    current = data
    for key in path:
        if isinstance(key, int):
            if not isinstance(current, list) or len(current) <= key:
                return None
            current = current[key]
        elif isinstance(current, dict):
            current = current.get(key)
        else:
            current = getattr(current, key, None)
        if current is None:
            return None
    return current


def _normalize_text_content(content) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks = []
        for item in content:
            if isinstance(item, str):
                chunks.append(item)
            elif isinstance(item, dict):
                chunks.append(str(item.get("text") or item.get("content") or ""))
            else:
                chunks.append(str(getattr(item, "text", "") or getattr(item, "content", "")))
        return "".join(chunks)
    return str(content)


def extract_chat_completion_text(response) -> str:
    """
    Extract text from common OpenAI-compatible response shapes.
    """
    candidates = [
        ["output_text"],
        ["choices", 0, "message", "content"],
        ["choices", 0, "text"],
        ["output", 0, "content", 0, "text"],
    ]
    for path in candidates:
        text = _normalize_text_content(_get_nested_value(response, path)).strip()
        if text:
            return text

    if hasattr(response, "model_dump"):
        dumped = response.model_dump()
        for path in candidates:
            text = _normalize_text_content(_get_nested_value(dumped, path)).strip()
            if text:
                return text

    return ""


def describe_response_shape(response) -> str:
    """
    Return a compact response-shape description for diagnostics.
    """
    try:
        if hasattr(response, "model_dump"):
            data = response.model_dump()
        elif isinstance(response, dict):
            data = response
        else:
            data = {}
        if isinstance(data, dict):
            top_keys = list(data.keys())[:8]
            choice_keys = []
            choices = data.get("choices")
            if isinstance(choices, list) and choices:
                first_choice = choices[0]
                if isinstance(first_choice, dict):
                    choice_keys = list(first_choice.keys())[:8]
            return f"top_keys={top_keys}, first_choice_keys={choice_keys}"
    except Exception:
        pass
    return f"type={type(response).__name__}"


def create_chat_completion_text(client, model: str, messages: list[dict]) -> str:
    """
    Call an OpenAI-compatible Chat Completions endpoint and return text content.
    """
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0,
    )
    text = extract_chat_completion_text(response)
    if not text:
        raise ValueError(f"Chat completion returned empty content. {describe_response_shape(response)}")
    return text


def check_client_available() -> dict:
    """
    Check whether a client can be constructed without sending API requests.
    """
    status = get_agent_api_status()
    if not status["has_api_key"]:
        return {
            "available": False,
            "reason": "OPENAI_API_KEY was not detected.",
        }
    try:
        client = get_openai_client()
    except Exception as error:
        return {
            "available": False,
            "reason": f"Failed to construct OpenAI client: {sanitize_openai_error(error)}",
        }
    if client is None:
        return {
            "available": False,
            "reason": "OpenAI SDK is unavailable or the API key is missing.",
        }
    return {
        "available": True,
        "reason": f"OpenAI client can be constructed; base_url={get_openai_base_url()}; no real API request was sent.",
    }
