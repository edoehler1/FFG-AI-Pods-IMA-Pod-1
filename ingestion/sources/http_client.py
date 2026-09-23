import httpx

# Corporate networks often use HTTPS-intercepting proxies with custom CA certs.
# Try verified first, fall back to unverified if SSL fails.
_ssl_verify = True


def get(url: str, **kwargs) -> httpx.Response:
    global _ssl_verify
    kwargs.setdefault("timeout", 30)

    if _ssl_verify:
        try:
            return httpx.get(url, verify=True, **kwargs)
        except httpx.ConnectError:
            print("  SSL verification failed — falling back to unverified (corporate proxy detected)")
            _ssl_verify = False

    return httpx.get(url, verify=False, **kwargs)
