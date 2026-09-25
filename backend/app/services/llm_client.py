import os

from app.config import settings


def is_llm_available() -> bool:
    api_key = settings.anthropic_api_key or os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
    return bool(api_key)


def call_llm(prompt: str, max_tokens: int = 1500) -> str:
    api_key = settings.anthropic_api_key or os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
    base_url = settings.anthropic_base_url or os.environ.get("ANTHROPIC_BASE_URL", "")

    if not api_key:
        return ""

    model = settings.anthropic_model or os.environ.get("ANTHROPIC_DEFAULT_SONNET_MODEL", "claude-sonnet-4-20250514")

    if base_url:
        if not base_url.rstrip("/").endswith("/v1"):
            base_url = base_url.rstrip("/") + "/v1"
        return _call_openai_compatible(prompt, max_tokens, api_key, base_url, model)

    return _call_anthropic_native(prompt, max_tokens, api_key, model)


def _call_openai_compatible(prompt: str, max_tokens: int, api_key: str, base_url: str, model: str) -> str:
    try:
        import httpx2
        client = httpx2.Client(verify=False, timeout=120)
        resp = client.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"LLM gateway error: {e}")
        return ""


def _call_anthropic_native(prompt: str, max_tokens: int, api_key: str, model: str) -> str:
    try:
        import anthropic
        kwargs: dict = {"api_key": api_key}
        try:
            import httpx2
            kwargs["http_client"] = httpx2.Client(verify=False)
        except ImportError:
            pass

        client = anthropic.Anthropic(**kwargs)
        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
    except Exception as e:
        print(f"Claude API error: {e}")
        return ""
