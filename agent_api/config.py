import os


DEFAULT_OPENAI_BASE_URL = "https://api.zzz-api.top/v1"

PLACEHOLDER_API_KEYS = {
    "your_api_key_here",
    "your_openai_api_key",
    "sk-your-api-key",
    "sk-your_api_key_here",
    "test-key",
}


def get_raw_openai_api_key() -> str | None:
    """
    Return the raw OPENAI_API_KEY value after trimming whitespace.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key and api_key.strip():
        return api_key.strip()
    return None


def is_placeholder_api_key(api_key: str | None) -> bool:
    """
    Detect common placeholder values that should never trigger real API calls.
    """
    value = (api_key or "").strip().lower()
    return value in PLACEHOLDER_API_KEYS or "your_api_key" in value


def is_potentially_valid_openai_api_key(api_key: str | None) -> bool:
    """
    Perform a local sanity check before attempting OpenAI API calls.
    """
    value = (api_key or "").strip()
    if not value or is_placeholder_api_key(value):
        return False
    return value.startswith(("sk-", "sk-proj-")) and len(value) >= 20


def get_openai_api_key() -> str | None:
    """
    Get a locally plausible OPENAI_API_KEY.
    """
    api_key = get_raw_openai_api_key()
    if is_potentially_valid_openai_api_key(api_key):
        return api_key
    return None


def get_agent_model(default: str = "gpt-5.4-mini") -> str:
    """
    Get the model used by the Agent API.
    """
    return (
        os.getenv("OPENAI_AGENT_MODEL")
        or os.getenv("OPENAI_MODEL")
        or default
    ).strip()


def get_openai_base_url(default: str = DEFAULT_OPENAI_BASE_URL) -> str:
    """
    Get the OpenAI-compatible API base URL.
    """
    return (
        os.getenv("OPENAI_BASE_URL")
        or os.getenv("OPENAI_API_BASE")
        or os.getenv("OPENAI_API_URL")
        or default
    ).strip().rstrip("/")


def _env_flag_is_true(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _env_flag_is_false(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"0", "false", "no", "off"}


def is_agent_api_enabled() -> bool:
    """
    V2.3 defaults to trying the real Agent API when a valid API key exists.
    ENABLE_AGENT_API=false is kept only as a developer override.
    """
    if _env_flag_is_false(os.getenv("ENABLE_AGENT_API")):
        return False
    return bool(get_openai_api_key())


def get_agent_api_status() -> dict:
    """
    Return a safe Agent API status payload for UI display.
    """
    raw_api_key = get_raw_openai_api_key()
    has_api_key = bool(get_openai_api_key())
    has_invalid_api_key = bool(raw_api_key) and not has_api_key
    disabled_by_env = _env_flag_is_false(os.getenv("ENABLE_AGENT_API"))
    enabled = (not disabled_by_env) and has_api_key

    if enabled:
        mode = "api_agent"
        reason = "Agent API is available."
        user_message = "Live Agent analysis is active."
    elif has_invalid_api_key:
        mode = "fallback"
        reason = "OPENAI_API_KEY is present but invalid."
        user_message = "The live Agent API is unavailable. FinCopilot will use local fallback analysis."
    elif disabled_by_env:
        mode = "fallback"
        reason = "Agent API is disabled by environment variable."
        user_message = "Development fallback mode is active."
    else:
        mode = "fallback"
        reason = "OPENAI_API_KEY is missing."
        user_message = "The live Agent API is unavailable. FinCopilot will use local fallback analysis."

    return {
        "enabled": enabled,
        "has_api_key": has_api_key,
        "has_invalid_api_key": has_invalid_api_key,
        "model": get_agent_model(),
        "base_url": get_openai_base_url(),
        "mode": mode,
        "reason": reason,
        "user_message": user_message,
    }


def should_use_fallback() -> bool:
    """
    Return True when the app should stay on deterministic fallback behavior.
    """
    return not is_agent_api_enabled()
