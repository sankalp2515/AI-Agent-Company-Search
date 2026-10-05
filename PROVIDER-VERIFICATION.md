# Provider verification — 5 October 2026

Credential values were not displayed or saved in reports. User-provided aliases are supported by the diagnostic script; the secret .env was not edited. Nine small generation attempts across two checks; no company data sent, no paid upgrade enabled. Actual account billing tiers cannot be established by a successful completion.

| Provider | Tested model | Final result |
| --- | --- | --- |
| Groq | openai/gpt-oss-20b | Generated exact requested JSON |
| NVIDIA | openai/gpt-oss-20b | Listed in authenticated catalog; generated exact JSON |
| Cohere | command-r7b-12-2024 | Generated exact JSON |
| Cloudflare | @cf/meta/llama-3.1-8b-instruct-fp8-fast | Generated exact JSON |
| Mistral | mistral-small-latest | Catalog succeeded; two generation attempts returned HTTP 429 |

Initial NVIDIA llama-3.1-8b candidate was absent from the current account catalog. Cloudflare's original @cf/meta/llama-3.1-8b-instruct returned HTTP 410. Cohere command-a-plus-05-2026 consumed its 128-token cap on reasoning without final text; it is not suitable for that tiny output budget. Initial Groq catalog HTTP 403 disappeared after supplying a normal application User-Agent; root cause is not proven.

Proposed order: Groq, NVIDIA, Cloudflare, Cohere; Mistral disabled until available. This is an integration plan, NOT an implemented runtime fallback chain. Cohere R7B lifecycle must be checked before the final frozen release. Use bounded concurrency across independent companies rather than duplicating each task across all five providers. Provider limits and cooldowns must remain independent. Auth failures must disable the provider, not loop retries.

Provisional development allowance: zero authorized paid spend, 100 additional model attempts and 25 basic search queries per explicitly launched test run. These are proposed application limits, not provider billing guarantees; confirm free account settings and disable paid overage. Do not claim official evaluation will be free: evaluator model keys, quotas and unit prices still need organizer confirmation.

Tavily is preferred for free local discovery: 1,000 monthly credits; basic search uses one credit, advanced uses two. SerpAPI currently advertises 250 free monthly searches and 50/hour throughput. Neither is configured yet. Search results are candidates only, never publication evidence. Fetch the permitted underlying source and apply exact-entity checks. Free accounts are not sufficient for unlimited daily 1,000+ company evaluation.

Cloudflare Chat Completions base URL:
https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/v1
The user sample's https://cloudflare.com base URL is incorrect. Direct Workers AI is distinct from an AI Gateway routing URL.

Run diagnostic: uv run --frozen python scripts/verify_providers.py
Last sanitized report: out/provider-verification.json (ignored).
Current OrgLens runtime is still deterministic; this diagnostic does not enable AI research or .env loading in the CLI.

## Official sources consulted

- https://console.groq.com/docs/models
- https://console.groq.com/docs/rate-limits
- https://docs.mistral.ai/api/endpoint/models
- https://docs.mistral.ai/api/endpoint/chat
- https://docs.api.nvidia.com/nim/reference/openai-gpt-oss-20b-infer
- https://docs.cohere.com/v2/reference/chat
- https://docs.cohere.com/docs/command-r7b
- https://docs.cohere.com/v2/docs/rate-limits
- https://developers.cloudflare.com/workers-ai/configuration/open-ai-compatibility/
- https://developers.cloudflare.com/workers-ai/platform/pricing/
- https://docs.tavily.com/documentation/api-credits
- https://docs.tavily.com/documentation/api-reference/endpoint/search
- https://serpapi.com/pricing
