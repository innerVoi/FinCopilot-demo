"""
Validate OPENAI_API_KEY for FinCopilot.

Usage:
    python api_valid.py
    python api_valid.py --model gpt-5.4-mini
    python api_valid.py --base-url https://api.zzz-api.top
    python api_valid.py --prompt "请用一句话说明你是谁"
    python api_valid.py --skip-chat-test
    python api_valid.py --test-responses-api
    python api_valid.py --conda-env fincopilot

The script never prints the full API key.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess


PLACEHOLDER_VALUES = {
    "your_api_key_here",
    "your_openai_api_key",
    "sk-your-api-key",
    "sk-your_api_key_here",
    "test-key",
}

DEFAULT_COMPATIBLE_BASE_URL = "https://api.zzz-api.top"
# DEFAULT_COMPATIBLE_BASE_URL = "https://api.zhizengzeng.com/v1"


def mask_api_key(api_key: str | None) -> str:
    """Return a safe masked API key preview."""
    value = (api_key or "").strip()
    if not value:
        return ""
    if len(value) <= 10:
        return f"{value[:3]}..."
    return f"{value[:7]}...{value[-4:]}"


def is_placeholder_key(api_key: str | None) -> bool:
    value = (api_key or "").strip().lower()
    return value in PLACEHOLDER_VALUES or "your_api_key" in value


def is_locally_plausible_key(api_key: str | None) -> bool:
    """Run a local sanity check before making any network request."""
    value = (api_key or "").strip()
    if not value or is_placeholder_key(value):
        return False
    return value.startswith(("sk-", "sk-proj-")) and len(value) >= 20


def sanitize_openai_error(error: Exception) -> str:
    """Convert common OpenAI errors into safe, actionable messages."""
    text = str(error)
    lower = text.lower()
    if "incorrect api key provided" in lower or "401" in text:
        return "Invalid or rejected API key for this base_url. Check OPENAI_API_KEY and OPENAI_BASE_URL."
    if "model" in lower and ("not found" in lower or "does not exist" in lower or "404" in text):
        return "Configured model is not available to this account. Try another OPENAI_AGENT_MODEL."
    if "permission" in lower or "access" in lower or "403" in text:
        return "The API key does not have permission for the selected model."
    if "rate limit" in lower or "429" in text:
        return "OpenAI API rate limit or quota issue. Check billing/quota or retry later."
    return text


def _parse_conda_env_vars_text(output: str) -> dict[str, str]:
    env_vars = {}
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        separator = "=" if "=" in line else ":" if ":" in line else None
        if not separator:
            continue
        key, value = line.split(separator, 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if key:
            env_vars[key] = value
    return env_vars


def read_conda_env_config_vars(conda_env: str = "fincopilot") -> tuple[dict[str, str], str | None]:
    """
    Read variables configured with:
        conda env config vars set OPENAI_API_KEY=... -n fincopilot
    """
    base_cmd = ["conda", "env", "config", "vars", "list", "-n", conda_env]
    try:
        completed = subprocess.run(
            [*base_cmd, "--json"],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
        payload = json.loads(completed.stdout or "{}")
        env_vars = payload.get("env_vars") or payload.get("vars") or {}
        return {str(key): str(value) for key, value in env_vars.items()}, None
    except Exception:
        pass

    try:
        completed = subprocess.run(
            base_cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
        return _parse_conda_env_vars_text(completed.stdout), None
    except Exception as error:
        return {}, str(error)


def get_env_value(name: str, conda_env_vars: dict[str, str]) -> tuple[str, str]:
    current_value = (os.getenv(name) or "").strip()
    if current_value:
        return current_value, "current_process_env"
    conda_value = (conda_env_vars.get(name) or "").strip()
    if conda_value:
        return conda_value, "conda_env_config_vars"
    return "", "missing"


def get_configured_model(
    cli_model: str | None = None,
    conda_env_vars: dict[str, str] | None = None,
) -> tuple[str, str]:
    conda_env_vars = conda_env_vars or {}
    if cli_model:
        return cli_model.strip(), "cli_arg"
    agent_model, agent_source = get_env_value("OPENAI_AGENT_MODEL", conda_env_vars)
    if agent_model:
        return agent_model, agent_source
    model, model_source = get_env_value("OPENAI_MODEL", conda_env_vars)
    if model:
        return model, model_source
    return (
        "gpt-5.4-mini",
        "default",
    )


def get_configured_base_url(
    cli_base_url: str | None = None,
    conda_env_vars: dict[str, str] | None = None,
) -> tuple[str, str]:
    conda_env_vars = conda_env_vars or {}
    if cli_base_url:
        return cli_base_url.strip().rstrip("/"), "cli_arg"
    for name in ["OPENAI_BASE_URL", "OPENAI_API_BASE", "OPENAI_API_URL"]:
        value, source = get_env_value(name, conda_env_vars)
        if value:
            return value.rstrip("/"), source
    return DEFAULT_COMPATIBLE_BASE_URL, "default_zzz_api"


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


def extract_chat_content(response) -> str:
    candidates = [
        ["choices", 0, "message", "content"],
        ["choices", 0, "text"],
        ["output_text"],
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


def extract_finish_reason(response) -> str:
    finish_reason = _get_nested_value(response, ["choices", 0, "finish_reason"])
    if finish_reason:
        return str(finish_reason)
    if hasattr(response, "model_dump"):
        finish_reason = _get_nested_value(response.model_dump(), ["choices", 0, "finish_reason"])
        if finish_reason:
            return str(finish_reason)
    return ""


def describe_response_shape(response) -> str:
    try:
        data = response.model_dump() if hasattr(response, "model_dump") else response
        if isinstance(data, dict):
            top_keys = list(data.keys())[:8]
            choice_keys = []
            choices = data.get("choices")
            if isinstance(choices, list) and choices and isinstance(choices[0], dict):
                choice_keys = list(choices[0].keys())[:8]
            return f"top_keys={top_keys}, first_choice_keys={choice_keys}"
    except Exception:
        pass
    return f"type={type(response).__name__}"


def validate_api_key(
    model: str,
    base_url: str,
    model_source: str = "unknown",
    base_url_source: str = "unknown",
    conda_env: str = "fincopilot",
    conda_env_vars: dict[str, str] | None = None,
    conda_error: str | None = None,
    prompt: str = "请用一句话说明你是谁。",
    skip_chat_test: bool = False,
    test_models_list: bool = False,
    test_responses_api: bool = False,
    allow_empty_output: bool = False,
) -> int:
    print("FinCopilot OpenAI-compatible API validation")
    print("--------------------------------------------")
    print(".env_loaded=False")
    print(f"conda_env={conda_env}")

    if conda_env_vars is None:
        conda_env_vars, conda_error = read_conda_env_config_vars(conda_env)
    if conda_error:
        print(f"conda_env_config_vars_read=FAILED: {conda_error}")
    else:
        print("conda_env_config_vars_read=PASSED")

    api_key, api_key_source = get_env_value("OPENAI_API_KEY", conda_env_vars)
    print(f"OPENAI_API_KEY_present={bool(api_key)}")
    print(f"OPENAI_API_KEY_source={api_key_source}")
    print(f"OPENAI_API_KEY_len={len(api_key)}")
    print(f"OPENAI_API_KEY_masked={mask_api_key(api_key)}")
    print(f"local_format_valid={is_locally_plausible_key(api_key)}")
    print(f"base_url={base_url}")
    print(f"base_url_source={base_url_source}")
    print(f"configured_model={model}")
    print(f"configured_model_source={model_source}")

    if not api_key:
        print("RESULT=FAILED")
        print(f"reason=OPENAI_API_KEY is missing from current environment and conda env config vars for {conda_env}")
        return 2

    if not is_locally_plausible_key(api_key):
        print("RESULT=FAILED")
        print("reason=OPENAI_API_KEY is empty, placeholder, malformed, or too short")
        return 2

    try:
        from openai import OpenAI
    except ImportError as error:
        print("RESULT=FAILED")
        print(f"reason=OpenAI SDK import failed: {error}")
        return 2

    client = OpenAI(api_key=api_key, base_url=base_url)

    if test_models_list:
        try:
            models = client.models.list()
            first_model = next(iter(models.data), None)
            print("models_list_test=PASSED")
            print(f"first_model_seen={getattr(first_model, 'id', '') if first_model else ''}")
        except Exception as error:
            print("models_list_test=FAILED")
            print(f"models_list_reason={sanitize_openai_error(error)}")

    if skip_chat_test:
        print("chat_test=SKIPPED")
        print("RESULT=PASSED")
        return 0

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是一个简洁、准确的助手。"},
                {"role": "user", "content": prompt},
            ],
            # max_tokens=256,
        )
        print(response)
        output_text = extract_chat_content(response)
        finish_reason = extract_finish_reason(response)
        print("chat_test=PASSED")
        print(f"finish_reason={finish_reason}")
        print("model_output_begin")
        print(output_text)
        print("model_output_end")
        if not output_text:
            print("RESULT=FAILED")
            print(f"reason=chat response content is empty; {describe_response_shape(response)}")
            if not allow_empty_output:
                return 1
            print("warning=empty output allowed by --allow-empty-output")
    except Exception as error:
        print("RESULT=FAILED")
        print("chat_test=FAILED")
        print(f"reason={sanitize_openai_error(error)}")
        return 1

    if test_responses_api:
        try:
            response = client.responses.create(
                model=model,
                input="Reply with OK only.",
                max_output_tokens=16,
            )
            output_text = getattr(response, "output_text", "") or ""
            print("responses_api_test=PASSED")
            print(f"responses_api_preview={output_text[:80]}")
        except Exception as error:
            print("responses_api_test=FAILED")
            print(f"responses_api_reason={sanitize_openai_error(error)}")

    print("RESULT=PASSED")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate FinCopilot OpenAI-compatible API settings.")
    parser.add_argument(
        "--conda-env",
        default="fincopilot",
        help="Conda environment name to read with `conda env config vars list -n`. Defaults to fincopilot.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model used for the chat test. Defaults to OPENAI_AGENT_MODEL, OPENAI_MODEL, then gpt-5.4-mini.",
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="OpenAI-compatible API base URL. Defaults to OPENAI_BASE_URL / OPENAI_API_BASE, then https://api.zzz-api.top.",
    )
    parser.add_argument(
        "--prompt",
        default="请用一句话说明你是谁。",
        help="User prompt sent to chat.completions.create(). The model output is printed between model_output_begin/end.",
    )
    parser.add_argument(
        "--skip-chat-test",
        action="store_true",
        help="Only validate local configuration; do not call chat.completions.create().",
    )
    parser.add_argument(
        "--allow-empty-output",
        action="store_true",
        help="Treat empty model output as a warning instead of failure.",
    )
    parser.add_argument(
        "--test-models-list",
        action="store_true",
        help="Also try models.list(). Some compatible providers do not support it.",
    )
    parser.add_argument(
        "--test-responses-api",
        action="store_true",
        help="Also try responses.create(). Some compatible providers do not support it.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    conda_env_vars, conda_error = read_conda_env_config_vars(args.conda_env)
    model, model_source = get_configured_model(args.model, conda_env_vars=conda_env_vars)
    base_url, base_url_source = get_configured_base_url(args.base_url, conda_env_vars=conda_env_vars)
    return validate_api_key(
        model=model,
        base_url=base_url,
        model_source=model_source,
        base_url_source=base_url_source,
        conda_env=args.conda_env,
        conda_env_vars=conda_env_vars,
        conda_error=conda_error,
        prompt=args.prompt,
        skip_chat_test=args.skip_chat_test,
        test_models_list=args.test_models_list,
        test_responses_api=args.test_responses_api,
        allow_empty_output=args.allow_empty_output,
    )


if __name__ == "__main__":
    raise SystemExit(main())
