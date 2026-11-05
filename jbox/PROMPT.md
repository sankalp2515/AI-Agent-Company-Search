# JBOX build prompts

Deadline: send the live link by **7 November 2026, 23:59 IST**.

Paste Prompt 1 into JBOX. JBOX's prompt box accepts images only, so the data is served as public JSON from this repository's `jbox/site-data/` folder, which must be pushed first. When JBOX shows its screen and flow map, review it against the checklist at the end before starting the build. The account has 20 credits.

---

## Prompt 1: full brief

Build **Signalpost**, a public website for researching Norwegian companies. Visitors can find a company, compare two, and check where any fact came from, on laptop and phone.

No login, accounts, roles, payments, admin area or editing. The site is read-only and public. Do not invent any company data, and do not add placeholder companies, testimonials or statistics.

### Data

No database is needed. All data is public static JSON, fetched in the browser or at request time. Do not copy it into the code, and do not create any tables.

- List of all 400 companies: `https://raw.githubusercontent.com/sankalp2515/AI-Agent-Company-Search/main/jbox/site-data/index.json`
- One company: `https://raw.githubusercontent.com/sankalp2515/AI-Agent-Company-Search/main/jbox/site-data/company/[org_number].json`

Each item in the list has: org_number, name, legal_form, industry_code, industry, municipality, address, founded_on, employees, latest_period_end, revenue, operating_result, net_result, assets, equity, website, profile_count, news_count, fact_count, last_checked, rechecked, material_changes, sample, news_state, state_official_website, state_owned_profiles, state_activity, state_description, state_jobs, state_financials, state_leadership, state_locations, state_contact.

A company file has `company` (the same fields plus summary), `facts` and `statements`.

Each fact has: id, org_number, section, label, value_text, value_number, unit, period, link_url, source_url, source_name, source_class, retrieved_at, where_in_source, identity_check, content_sha256. `section` is one of: identity, financials, people, workplaces, web, news, hiring, registry_events.

Each statement has: org_number, position, kind, text, fact_ids (fact ids separated by `|`).

Empty means unknown. Never show an empty number as 0.

The state columns hold one of these, and must be shown in these words:

- `available`: show the data
- `not_available`: "We looked and found nothing."
- `blocked`: "The source refused the request."
- `ambiguous`: "Not sure it is the right company, so nothing is published."
- `failed`: "The check failed on this run."
- `not_applicable`: "Does not apply to this company."

### Pages

**Home (`/`)**
- Headline: "Every fact has a way back." Subhead: "Look up a Norwegian company, compare two, and check where any fact came from. Where nobody could confirm something, we say so."
- Below that, a live example: a card showing Melbye AS's latest revenue from the data with its fix mark, a dashed magenta line drawing to a second card naming its source and retrieval date. Tapping the mark opens the real source panel.
- A large search field labelled "Find a company", on the first screen, filtering as you type on name, organisation number, municipality and industry. Default list order: companies with a website first, then by fact_count.
- Each result shows name, organisation number, municipality and industry, plus a "Compare" toggle. Picking companies fills a bar fixed to the bottom of the screen, and at two it offers "Compare these two".
- No match: "No match. This site covers 400 researched Norwegian companies, not all of Norway."

**Company (`/company/[org_number]`)**
- Heading: name, then organisation number, legal form, municipality and industry. A "Compare with another" button.
- "In brief": the company's statements as separate short paragraphs, each with a fix mark for its first fact.
- "Filed accounts": table with years as columns, newest first. Rows: Revenue, Operating result, Net result, Total assets, Equity. Every figure has a fix mark. Show "Not filed" for a missing year. Losses use a minus sign and the bad colour. The table scrolls inside its own box on phones.
- Then: "On the web" (section web), "News from the company" (section news), "Hiring" (section hiring, or the state_jobs words), "People" (section people), "Registered workplaces" (section workplaces, first 6 with a show-more), "Recent register events" (section registry_events, newest 5). A section with no data shows the unsurveyed block with the reason.
- A "What we checked" rail: website, profiles, job ads, accounts, leadership, workplaces and contact, each with its state. Sticky on the right from 900px, below the content on phones. End with "Last checked [date]".

**Compare (`/compare?a=[org]&b=[org]`)**
- Default pair: Melbye AS (941009697) and Empress Norge AS (915313760). Shareable URL.
- Two labelled company pickers that stay stuck to the top while scrolling.
- One row per item, label on its own line, then two equal columns, **even on a phone**. There is no sideways scrolling.
- Rows: Revenue, Operating result, Net result, Total assets, Equity (figure, fix mark and a bar, both bars on one scale per row, loss bars hatched), Employees, Accounts year, Founded, Website, Linked profiles, News, Job ads.
- Note: "Bars share one scale per row. Figures come from each company's latest filed accounts."

**How it works (`/method`)**
Short page. Facts come from Brønnøysundregistrene, Regnskapsregisteret, NAV's job feed and verified company websites. A website is published only after exact identity proof. It is better to miss something than to publish it under the wrong company. The site covers 400 Norwegian companies researched by the OrgLens agent on 3 and 4 November 2026.

**Footer on every page:** "Research by OrgLens. Contains data under the Norwegian Licence for Open Government Data (NLOD) made available by Brønnøysundregistrene." plus links to the method page and https://github.com/sankalp2515/AI-Agent-Company-Search.

### The two signature components

**Fix mark.** Beside every fact: a 16px magenta ring with a centre dot, inside a 44px tap target, with the label "Check the source of [fact label]". It opens the source panel.

**Source panel.** A side panel 440px wide on laptops, a bottom sheet on phones, with a 3px magenta edge. Shows the fact label, the value large (full number such as "NOK 353,709,793") and then, labelled: "Where it came from" (source_name), "Retrieved" (date from retrieved_at), "Reporting period" (period, if any), "Exact place in the source" (where_in_source), "Why this is the right company" (identity_check), "Fingerprint of the saved source" (first 16 characters of content_sha256), and a button "Open the original source" linking to source_url in a new tab. Escape and Close dismiss it, and focus returns to the mark.

**Unsurveyed block.** Any unknown value: diagonal hatching at 135 degrees with a dashed border, and the reason in words on a solid background. Never a dash, "N/A" or 0.

### Design

The concept is a nautical chart. Every fact is a confirmed position, and what nobody confirmed is unsurveyed water. Follow this exactly. Do not use gradients, shadows, emoji, stock images, large rounded corners, generic card grids or a default component-library look.

Fonts (Google Fonts): **Schibsted Grotesk** for headings and interface, with headings at weight 800 and -0.03em tracking. **IBM Plex Mono** for every figure and organisation number. **Newsreader Italic** only for short annotations.

Colours as CSS variables, following the device's light or dark setting:

| Token | Light | Dark |
|---|---|---|
| water (page) | #F3F8F9 | #0B1A22 |
| shoal | #DDECF1 | #12303C |
| paper (cards, panel) | #FFFFFF | #0F232D |
| ink (text) | #10303C | #E4EEF1 |
| muted | #49646E | #9DB6BF |
| line | #B9CFD6 | #2B4C59 |
| mark (magenta, source tracing only) | #A3115C | #F27AB3 |
| good | #0C6B58 | #5FD0B5 |
| warn | #8A5A00 | #E6B85C |
| bad | #B3261E | #F2938B |
| hatch | #9DB9C2 | #3C6070 |

Spacing scale 4, 8, 12, 16, 24, 32, 48, 72. Corners 3px. Maximum width 1160px, minimum gutter 16px. Sections are separated by lines and space, not boxes. Home background: faint depth contour lines in the line colour, behind the hero only, drawn with canvas or inline SVG.

Motion: the dashed line draws once in 520ms on the home page. Other feedback 160ms. Panel 220ms. Respect prefers-reduced-motion.

### Quality bar

- Every tap target at least 44px. Visible keyboard focus everywhere.
- No horizontal page scrolling at 360px, 390px, 768px or 1440px.
- Pages load fast: fetch one company file at a time, and load the list only once.
- Show a short loading state and a clear error state with a retry.
- The back button and shared links work on every page.
- Norwegian letters æ, ø and å display and search correctly.

---

## Prompt 2: optional, only if credits remain

> When someone types a 9-digit organisation number that is not in our data, fetch https://data.brreg.no/enhetsregisteret/api/enheter/[number] from the browser and show a basic page with that company's name, legal form, address and industry, with a source link, labelled "Live from the official register. Not researched by OrgLens." Handle a 404 with a clear message.

The register's API allows browser requests (checked on 5 November 2026).

---

## Review checklist before you send the link

Test on a laptop and on a real phone:

- [ ] Search "melbye" and open it.
- [ ] Tap a revenue figure's mark. The panel shows NOK 353,709,793, period 2025, and the original source opens.
- [ ] On the Empress Norge AS page, the operating result is negative, not 0.
- [ ] A company with no website shows the hatched block with a reason.
- [ ] Compare Melbye and Empress: two columns on the phone, no sideways scrolling.
- [ ] A shared compare link opens the same pair.
- [ ] Search "Lillestrøm" with the ø.
- [ ] Open it in a private window, without being logged in to JBOX.
