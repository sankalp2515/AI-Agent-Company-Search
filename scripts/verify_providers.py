"""Bounded provider checks; never print credentials, response bodies or request URLs."""
import concurrent.futures
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path


def load_env(path=".env"):
    for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        match = re.match(r"\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)", line)
        if match:
            value = match[2].strip()
            if value[:1] in {"'", '"'} and value[-1:] == value[:1]:
                value = value[1:-1]
            else:
                value = value.split(" #", 1)[0].strip()
            os.environ.setdefault(match[1], value)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def request(url, key, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None,
                                 headers={"Authorization": "Bearer " + key, "Content-Type": "application/json", "User-Agent": "OrgLens/0.1 provider-check", "Accept": "application/json"})
    with urllib.request.build_opener(NoRedirect()).open(req, timeout=25) as response:
        data = response.read(2_000_001)
        if len(data) > 2_000_000:
            raise ValueError("response_size")
        return json.loads(data)


def check(provider, base, key, preferred, cohere=False, catalog=True):
    result = {"provider": provider, "configured": bool(key), "model": preferred,
              "status": "not_configured", "generation_requests": 0}
    if not key:
        return result
    started = time.monotonic()
    try:
        if catalog:
            payload = request(base + "/models", key)
            ids = [m.get("id", m.get("name", "")) for m in payload.get("data", payload.get("models", []))]
            result["catalog_count"] = len(ids)
            result["candidate_models"] = [m for m in ids if any(x in m.lower() for x in ("small", "gpt-oss", "llama-3.1-8b", "command-a"))][:30]
            if preferred not in ids:
                result["status"] = "requested_model_not_in_catalog"
                return result
        body = {"model": preferred, "messages": [{"role": "user", "content": 'Reply with exactly {"ok":true} and no other text.'}],
                "max_tokens": 128, "temperature": 0}
        result["generation_requests"] = 1
        payload = request(base + ("/chat" if cohere else "/chat/completions"), key, body)
        content = "".join(x.get("text", "") for x in payload.get("message", {}).get("content", [])) if cohere else payload["choices"][0]["message"].get("content", "")
        result["status"] = "generation_ok" if content else "empty_content"
        result["json_contract_ok"] = content.strip() == '{"ok":true}'
        result["usage"] = payload.get("usage", {})
    except urllib.error.HTTPError as exc:
        result["status"] = "http_error"
        result["http_status"] = exc.code
    except Exception as exc:
        result["status"] = "transport_or_schema_error"
        result["error_type"] = type(exc).__name__
    finally:
        result["elapsed_seconds"] = round(time.monotonic() - started, 3)
    return result


if __name__ == "__main__":
    load_env()
    account = os.getenv("CLOUDFLARE_ACCOUNT_ID") or os.getenv("AccountID", "")
    specs = [
        ("groq", "https://api.groq.com/openai/v1", os.getenv("GROQ_API_KEY"), "openai/gpt-oss-20b", False, True),
        ("mistral", "https://api.mistral.ai/v1", os.getenv("MISTRAL_API_KEY"), "mistral-small-latest", False, True),
        ("nvidia", "https://integrate.api.nvidia.com/v1", os.getenv("NVIDIA_API_KEY") or os.getenv("NVDIA_API_KEY"), "openai/gpt-oss-20b", False, True),
        ("cohere", "https://api.cohere.com/v2", os.getenv("COHERE_API_KEY"), "command-r7b-12-2024", True, False),
        ("cloudflare", "https://api.cloudflare.com/client/v4/accounts/" + account + "/ai/v1", os.getenv("CLOUDFLARE_API_KEY") or os.getenv("Cloudflare_API_KEY"), "@cf/meta/llama-3.1-8b-instruct-fp8-fast", False, False),
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(lambda args: check(*args), specs))
    report = {"results": results, "scope": "Connectivity only; no company research or account billing verification", "paid_upgrades_enabled": False}
    Path("out").mkdir(exist_ok=True)
    Path("out/provider-verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
