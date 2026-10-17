# OrgLens readiness verdict — 17 October 2026 (v3 code)

**Verdict: GO for submitting version 1 now.** Use revisions 2–5, which close 18 October, to iterate on coverage. No official score or qualification is claimed. Builderr's checked collection is hidden.

## What changed since the FIX BEFORE SUBMISSION audit

**Identity defects fixed, each with a regression test (`tests/test_integrity_fixes.py`):**

- JSON-LD identifiers must be exact 9-digit organisation numbers; LEI/DUNS values and suffixes no longer match.
- A conflicting organisation number in text, footer or JSON-LD vetoes publication.
- Phone matches are bounded tokens.
- A partial-name domain plus a shared board member is no longer proof.

**Proof paths kept, in stricter form:**

- **Registered operating head:** a domain that spells the complete legal name, on which the registered daglig leder or owner is named alongside the company name. Ordinary board members do not count.
- **Registry declaration:** the domain must carry the company name, and the page must show the full core name.

**Parent-site case found and fixed during this session's audit:** a parent/group site declared in the registry (MYLIFE DIABETES CARE AS → ypsomed.com) was rejected. The company is now matched to its own brand page, which shows its exact legal name and registered address.

**Refresh** is now source-aware:

- Stale facts survive repeated failed refreshes, with previous evidence and snapshots carried forward.
- A successful registry response no longer masks a failed company-site source.
- A genuinely observed removal is still reported as a change.

**NAV jobs:**

- Brand, locality and compact-spelling candidates are discovered (for example "Uplink" for UP LINK AS).
- A truncated or failed feed, or a failed detail fetch, is reported as `failed`, never as `not_available` or `ambiguous`.
- Publication still requires the ad's employer organisation number to equal the company or one of its registered subunits.

**Reliability:**

- Each HTTP response body has a 25-second wall-clock cap. A trickling server previously hung a 1,100-company run.
- The HTTP deadline reserves time for writing envelopes, validation and the viewer, so runs finish inside `--max-seconds`.
- Official endpoints get bounded retries plus a second-chance pass after transient 5xx bursts.

**Activity:** `Article` schema on About, Privacy and Contact pages is no longer counted as dated news.

**Viewer:**

- No truncation at 500 companies.
- Search and filters keep the profile in sync, with an explicit empty state.
- Stale facts are labelled "Not re-verified" and cite their previous sources.

## Verification (all on the final code, run sequentially)

| Check | Result |
|---|---|
| Test suite | 80 passed; clean install from the lockfile |
| Secret guard (`scripts/check_secrets.py`) | 0 findings on all publishable files; raw snapshots stay git-ignored |
| 100-company smoke, 2,000 requests / 2,700 s caps | 100/100 valid; 1,510 requests; 253 s; $0 |
| Live refresh of the same 100 | 100/100 valid; **0 changes, 0 false stale facts** |
| 1,100-company scale, 20,000 / 5,400 s caps | 1,100/1,100 valid; 15,451 requests; 1,976 s |
| 1,100-company stress, 2,000 / 2,700 s caps | 1,100/1,100 valid; exactly 2,000 requests; 238 s; unqueried families reported as `failed` |

**Smoke coverage (100 companies):**

| Family | Companies |
|---|---|
| Identity, accounts, roles, workplaces | 100 each |
| Websites | 8 |
| Descriptions | 7 |
| Social profiles | 3 |
| Contact | 39 |
| Registry/company activity | 100 |
| Jobs | 0 |

**Scale coverage (1,100 companies):**

| Family | Companies |
|---|---|
| Identity / accounts / roles / workplaces | 1,100 / 1,097 / 1,097 / 1,100 |
| Websites | 115 |
| Descriptions | 67 |
| Social profiles | 70 |
| Contact | 425 |
| Jobs | 5 |

**Website methods at scale (115 total):**

| Method | Websites |
|---|---|
| Labelled organisation number | 45 |
| Full-name domain plus registered operating head | 33 |
| Legal name plus registered address | 14 |
| Registry declaration | 13 |
| Legal name plus registered phone | 10 |

The registry-declared and operating-head websites from the scale run were reviewed by hand; the one parent-site case was fixed (see above). The other website methods (organisation number, legal name plus address or phone) were not reviewed by hand in this session.

**Desktop and mobile UI, verified in a real browser:**

- Search, filter, empty state and two-company comparison work.
- There is no horizontal overflow at 375, 490 or 1,280 px.
- Every phone control is at least 44.8 px tall.

## Why GO, and the risks that remain

On the 17 October public board (300-company set), most entries score UX 0/8 and synthesis 0–7.2/12. OrgLens produces a verified cited narrative in every envelope and a responsive viewer in every run. Precision has been prioritised over recall.

Remaining risks:

1. **The official resource budget is not stated.** At 2,000 requests for 1,100 companies, identity and accounts use the whole budget, and external coverage falls to zero. The run still completes with honest states. Ask Builderr for the budget, and pass `--registry` when a frozen snapshot is supplied (it saves one request per company).
2. **External recall is modest:** websites are verified for about 10% of random companies. Most of this universe is small holding and property companies with no findable site. The leading entry's recall (35.8/50) suggests that richer discovery, possibly a search API with organizer-supplied keys, is the main lever for revisions.
3. **The jobs prefilter still misses brand names** that match neither the legal name nor any workplace name.
4. **Fields such as reviews, ratings and sentiment are not collected.** The board currently excludes them.
