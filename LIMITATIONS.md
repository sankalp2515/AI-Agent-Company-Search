# Known limitations (v2, 16 October 2026)

- Builderr's checked collection is hidden, so recall is measured only against our own runs. On a random 100-company batch, 10 websites were verified; most small Norwegian companies have no discoverable static website.
- Websites are found from the registry, from NAV employer homepages, from the previous run, and from name-derived domains. Sites whose brand differs from the legal name are found only when the registry or NAV declares them. No search API is used in the default command.
- Sites that show no organisation number, phone, address or registered role holder are left `ambiguous` or `not_available` rather than risk a wrong-company match.
- NAV jobs: the employer-name prefilter misses ads posted under a brand name that matches neither the company nor any registered workplace. Ads on finn.no are not in NAV's feed. The feed index covers changes from the last 40 days.
- Static HTML only. JavaScript-rendered content, PDFs and social platform pages are not fetched.
- "Dated activity" includes official registry events (kind `official_registry_event`), kept separate from company-published items. They are never presented as news or sentiment.

# Measured and known limitations

This is a reproducible research submission candidate, not a claim of winning or official qualification. Builderr's hidden checked collection is unavailable locally. There is no honest local number for competition recall without independent labels.

- Registry URLs can be absent, stale, shared, or linked to a property manager. Exact identity gates abstain rather than contaminate a profile. Opt-in Brave discovery is implemented and contract-tested, but not live-verified or enabled; a permitted search-provider key and declared spending cap would unlock its measured coverage evaluation.
- Static HTML only: JavaScript shells, PDFs and restricted sources can remain unavailable. No browser rendering, OCR, PDF accounts-history fallback or independent news/sentiment provider in this version.
- Financial values are parsed only from recognized official account fields; currency, account type and reporting period are preserved. An unexpected response format fails rather than guessing. No financial estimates or missing-to-zero conversion.
- Locations use the first 100 registered subunits. Additional pages are explicitly flagged. Empty endpoint results mean that endpoint returned no records, not that the company has no physical operations.
- Jobs and dated news require structured data on fetched verified company pages. Undated marketing text is not a dated event. Owned-profile links require exact taxID in company JSON-LD and do not claim independently verified social-platform ownership.
- Every phase gives breadth priority. Small request budgets can leave later modules failed/unresearched for large batches. Completion remains explicit but coverage falls. Configurable limits are not evidence that the actual evaluator budget is known.
- Private/reserved destinations and redirect targets are DNS checked. DNS rebinding cannot be fully prevented by this standard-library transport; use an evaluator egress firewall that denies private/reserved destination addresses. This is a documented deployment requirement, not a claim of fully pinned DNS.
- Interrupted runs leave phase checkpoints; there is no checkpoint resume mode yet. A complete run produces terminal envelopes. Snapshots/results are written atomically where practical, but no claim is made that forced process termination can always produce a complete batch.
- Prior evidence is preserved in refresh metadata and its original directory. The viewer shows stale last-known facts separately. Earlier snapshot directories must remain available.
- Company-source terms have not been manually audited for every domain. Do not publicly redistribute raw third-party snapshots before checking rights.
- Team/contact identity, remote repository URL, final commit and exact organizer budget/schema/deadline acknowledgement remain release inputs.
# AI upgrade limitations (5 October 2026)

AI mode is implemented and uses live providers and Tavily. This supersedes earlier statements below that no LLM is used. Model reasoning directs tools but published facts are still restricted to deterministic, evidence-checked extraction. This is not a general-purpose browser, PDF/OCR or unrestricted news crawler. Model summaries select verified claims rather than publishing free-form generated prose.

Model/query caps may stop research before every company gets a completed AI loop. This is disclosed separately from terminal envelope completion. Provider pacing/cooldowns are conservative local controls, not guarantees of token-per-minute compliance; real 429s can still occur. All providers failing preserves baseline output but limits discovery. Free-tier credentials may not transfer to the evaluator, and remaining monthly allowances are not verified automatically. No official score, qualification or JBOX bonus eligibility is claimed.

The local simulator is not the organizer harness: hidden union, exact field weights and human rubrics are unavailable. A reviewed reference must be supplied independently before reporting a score. Tests establish operational behavior, not exhaustive semantic accuracy. The original deterministic release and archived reports remain baseline development evidence, not evidence that the new agent was used in those old runs.
