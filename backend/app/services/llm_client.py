import os

from app.config import settings


def is_llm_available() -> bool:
    api_key = settings.anthropic_api_key or os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
    return bool(api_key)


def call_llm(prompt: str, max_tokens: int = 1500) -> str:
    api_key = settings.anthropic_api_key or os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
    base_url = os.environ.get("ANTHROPIC_BASE_URL")

    if not api_key:
        return ""

    try:
        import anthropic
        kwargs: dict = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        try:
            import httpx2
            kwargs["http_client"] = httpx2.Client(verify=False)
        except ImportError:
            pass

        model = os.environ.get("ANTHROPIC_DEFAULT_SONNET_MODEL", "claude-sonnet-4-20250514")
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
