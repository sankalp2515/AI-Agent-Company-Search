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

Implemented default order: Groq, NVIDIA, Cloudflare, Cohere; Mistral disabled until available. `orglens run --ai` uses this real fallback chain and bounded parallel research across independent companies, not speculative five-way duplication. Authentication failures disable a provider; transient errors enter independent cooldowns. Rate limits remain account-specific. Current official Cohere documentation still documents R7B; live calls succeeded, but trial/evaluator terms must be confirmed.

Zero authorized paid spend. Default per-run application caps are 100 model attempts and 25 basic queries; explicitly launched tests use the caps recorded in their reports. These are workload caps, not provider billing guarantees. Confirm free account settings and disable paid overage. Do not claim official evaluation will be free: evaluator keys, remaining quotas and unit prices still need organizer confirmation.

Tavily is configured, integrated and live-tested: 1,000 free monthly credits; basic search uses one credit, advanced uses two. SerpAPI currently advertises 250 free monthly searches and 50/hour throughput; it is not integrated. Search results are candidates only, never publication evidence. Fetch the permitted underlying source and apply exact-entity checks. Free accounts are not sufficient for unlimited daily 1,000+ company evaluation.

Cloudflare Chat Completions base URL:
https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/v1
The user sample's https://cloudflare.com base URL is incorrect. Direct Workers AI is distinct from an AI Gateway routing URL.

Run diagnostic: uv run --frozen python scripts/verify_providers.py
Last sanitized report: out/provider-verification.json (ignored).
The CLI now loads local .env safely and enables real AI research with --ai. JSON output was verified with actual research-state payloads for Groq, Cloudflare and Cohere. Groq built-in tool calls are disabled: this program, not the model host, executes bounded actions. Model-generated facts and unsupported summary fields are rejected.

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
