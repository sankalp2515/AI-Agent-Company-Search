# Sources, models, APIs and licensing

Implementation: original OrgLens code, MIT. The downloaded Builderr reference archive was inspected for requirements and replayed during preparation; it is not redistributed in the implementation package. No starter source files are imported by OrgLens.

Dependencies: Beautiful Soup (MIT), soupsieve (MIT), typing-extensions (PSF). The uv lockfile pins transitive dependencies. Test tooling is pytest (MIT) and its locked dependencies. Build tooling is hatchling (MIT). Review licence metadata at release using the installed distributions.

Official APIs: Brønnøysundregistrene Enhetsregisteret identity, roles and subunits; Regnskapsregisteret annual accounts. Public official-data source terms apply, including attribution and NLOD where offered. Evidence records preserve each original endpoint. No key is required by the used public endpoints.

Company-owned sources: public static home, contact/about, careers/news pages and embedded JSON-LD reached from a registry-listed website. The system checks robots for the user agent, limits each company crawl, preserves source provenance and rejects restricted/nonpublic destinations. Robots is an access signal, not a copyright licence. Public availability does not automatically grant redistribution rights; the evaluator package is a source-evidence research artifact and a domain-level terms review remains required before public hosting of retained page bytes. No platform APIs, unofficial platform connectors, social scraping or licensed news feeds are enabled.

External costs: $0 in declared model/search/platform API costs for the default configuration. Network/storage/compute are separate. Optional Brave Web Search discovery requires explicit CLI activation, `BRAVE_API_KEY`, a declared per-request rate and a positive spending cap. Expected optional search charge is bounded by `min(query_count × declared_rate, approved_cap)`; attempted queries are conservatively charged even if the provider errors. No paid connector runs silently. Never put credentials in the repository, command arguments or result artifacts.

Brave documentation and terms reviewed on 5 October 2026: https://api-dashboard.search.brave.com/app/documentation/web-search/get-started and https://api-dashboard.search.brave.com/terms-of-service. Live access and plan-specific rights are unverified until a key/plan is provided. Results/snippets are transient and not claim evidence. No third-party snippet corpus is created. The default submission does not require this service or use its unverified outputs.

Caches: official snapshots supplied by the evaluator are explicitly declared by path, hash and actual retrieval timestamp in the run report. Live responses are stored only as evidence, not reused to pretend a fresh retrieval occurred. Previous results are used only for diffs and clearly marked last-known values after unsuccessful refreshes.

Models: no LLM or learned model in the default submitted version. Synthesis is generated from accepted claims using fixed templates with evidence references. An LLM key is not a blocker to running the agent.
