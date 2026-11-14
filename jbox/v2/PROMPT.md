# JBOX build prompt, version 2

For the new account with 50 credits. Hosting uses about 1 credit a day, so 13 days to 23 November needs about 13. That leaves about 37 for building.

**Data:** 1,000 companies (700 random, 298 employers of 20 or more, plus Melbye and Equinor), 41,302 sourced facts, 221 verified websites, researched 13 November 2026 by commit `b3c53bf`.

**Before pasting:** the data in `jbox/site-data-v2/` must be pushed to `main` on GitHub, because JBOX reads it from there. Attach the four screenshots in `jbox/v2/screenshots/` (home by day, home by night, company with source panel, compare). Review JBOX's screen and flow map against the checklist at the end before it starts building.

---

## Prompt 1: the build

Build **Signalpost**, a public website for researching Norwegian companies. A visitor can find a company, compare two, and check where any fact came from, on laptop and phone. The attached screenshots show the exact look. Match them.

No login, accounts, roles, payments, admin or editing. Read-only and public. Never invent company data, placeholder companies, testimonials or statistics.

### Data

No database. All data is public static JSON. Fetch it on the server and cache it for a day. Do not copy it into the code.

- All companies: `https://raw.githubusercontent.com/sankalp2515/AI-Agent-Company-Search/main/jbox/site-data-v2/index.json`
- One company: `https://raw.githubusercontent.com/sankalp2515/AI-Agent-Company-Search/main/jbox/site-data-v2/company/[org_number].json`

List item fields: org_number, name, legal_form, industry_code, industry, municipality, address, founded_on, employees, latest_period_end, revenue, operating_result, net_result, assets, equity, website, description, profile_count, news_count, job_count, fact_count, last_checked, state_official_website, state_owned_profiles, state_activity, state_description, state_jobs, state_financials, state_leadership, state_locations, state_contact.

A company file has `company` (same fields plus `summary`), `facts` and `statements`.

Fact fields: id, section, label, value_text, value_number, unit, period, link_url, source_url, source_name, source_class, retrieved_at, where_in_source, identity_check, content_sha256. `section` is one of identity, financials, people, workplaces, web, news, inspections, hiring, registry_events. Financial facts repeat per year: `period` is "YYYY-MM-DD to YYYY-MM-DD".

Statement fields: position, kind, text, fact_ids (ids separated by `|`).

**Empty means unknown. Never show an empty number as 0.** Show company names in title case ("Melbye AS", keeping AS, ASA, SA, ANS, DA in capitals). Show municipalities in title case.

State values and the words to show:

- `available`: show the data
- `not_available`: "We looked and found nothing."
- `blocked`: "The source refused the request."
- `ambiguous`: "Not sure it is the right company, so nothing is published."
- `failed`: "The check failed on this run."
- `not_applicable`: "Does not apply to this company."

### Pages

**Home (`/`)**

1. Sticky header: logo (the fix mark with four ticks, then "Signalpost"), links Find, Compare, How it works, and a theme button that reads "NIGHT CHART" or "DAY CHART". On phones keep all three links visible as a second compact row under the logo; never hide them.
2. Hero, two columns on laptops. Left: small label "NORWEGIAN COMPANIES · CHARTED FROM PUBLIC SOURCES" and the headline "Every fact has a *way back.*" with "way back." in magenta italic Newsreader. Right: the sentence "Find a Norwegian company, compare two, and tap any figure to see exactly where it came from. What nobody could confirm stays marked as unsurveyed." and a large search field (60px high, 1.5px ink border, placeholder "Company name, number, town or industry", a `/` key hint, and pressing `/` focuses it). Under it: "Try Melbye · 941 009 697 · Lillestrøm" as links.
3. **The soundings chart**, full width, about 560px high on laptops and 420px on phones, pale blue with a double ink frame. Draw it in SVG:
   - One mark per company. Place them biggest employer first. A company shows its employee count in 11px Plex Mono only if that label would not overlap one already placed (check with a 6px grid). Otherwise, or if employees is empty, it shows a small ring "∘" at 55% opacity. This thinning is how real charts keep soundings readable.
   - Across: founding year from 1970 to this year. Anything older sits in a narrow strip at the left edge. Leave 70px on the left for the revenue labels. Tick labels "≤1970, 1980, 1990, 2000, 2010, 2020" and "FOUNDED →".
   - Up: latest revenue on a log scale from 10 thousand to 20 billion NOK, with labels 100 K, 1 M, 10 M, 100 M, 1 BN.
   - A hatched band 64px high along the bottom, labelled "UNSURVEYED · NO REVENUE FILED". Companies with empty revenue go there, never at zero.
   - Seven faint wavy contour lines behind the marks, a small magenta compass rose bottom right, and a boxed legend: "HOW TO READ THIS CHART. Each number is one company: its employee count, placed by founding year and revenue. Tap one to open it."
   - Hover or keyboard focus on a mark turns it magenta and larger, and shows a card: name, municipality, founding year, revenue or "No revenue filed", employees, and "[fact_count] facts, each with a source". Click opens the company page.
   - Typing in the search or picking a filter dims every mark that doesn't match to 15% opacity.
   - On phones draw every third company. Marks fade in over 600ms on first load, oldest first.
4. Four counts in Plex Mono under the chart, computed from the data: companies charted, facts each with a source (sum of fact_count), verified websites (count with a website), and "0 guesses published".
5. Section "01 · FIND", heading "Find a company". Filter chips: All, Verified website, Hiring now (job_count > 0), Has news (news_count > 0), a Municipality select and an Industry select. Sort select: Depth of research (website first, then fact_count), Revenue, Name, Founded. Show 12 rows, then "Show more".
6. Each row: the **survey ring**, the name (link) with organisation number and municipality in mono beneath, the description or industry, revenue as "NOK 353.7 m" with "[n] facts" beneath (or italic "not filed"), and a "+ Compare" button. Picking a company fills a tray fixed to the bottom on the buff colour. At two it offers "Compare these two".
7. No match: "No match in the [count] researched companies." If the query is a 9-digit number, offer "Look it up live in the official register" (see Live lookup).

**Company (`/company/[org_number]`)**, server-rendered, with its own title and description.

1. "← Find a company", label "COMPANY RESEARCH · LAST CHECKED [date]", the name very large, then organisation number, legal form, municipality and founding year in mono. Buttons "Compare with another" and "Official register ↗".
2. **At a glance**: Revenue, Net result, Employees, Website, Job ads, each with a fix mark. Under Revenue and Net result show the change on the previous year from the financial facts, as "+3.1% on 2024" in green or "−0.1% on 2024" in red. Short figures here ("353.7 m"). The full number is in the table and the source panel.
3. "In brief": the first two statements, each with a fix mark for its first fact, then "Read the full summary".
4. "Filed accounts": years as columns, newest first. Rows Revenue, Operating result, Net result, Total assets, Equity. Each row has a small trend line (SVG, 74 by 22, magenta dot on the newest year). Every figure has a fix mark. "Not filed" for a missing year. Losses use a minus sign and the bad colour. The table scrolls inside its own box on phones. On phones hide the trend column so the newest year's figure always shows in full, never cut off mid-number.
5. "On the web" (web), "News from the company" (news, newest first), "Official inspections" (inspections), "Hiring" (hiring), "People" (people), "Registered workplaces" (first 6, then show more), "Recent register events" (newest 5).
6. All empty sections are gathered into **one** unsurveyed block near the end, listing each with its reason. Never repeat an empty block per section.
7. "What we checked" rail, sticky on the right from 900px and below the content on phones: Website, Profiles, News, Job ads, Accounts, Leadership, Workplaces, Contact, each with its state as a filled dot, hatched dot or diamond plus the word.

**Compare (`/compare?a=[org]&b=[org]`)**. Default pair 941009697 and the company with the next highest fact_count. Shareable URL.

1. Two company pickers in a header that sticks under the site header. Company A's name is right-aligned and B's left-aligned, meeting at a centre line.
2. One row per item: the label centred in small mono capitals, then a butterfly. A's figure and bar grow **left** from a 1px centre line, and B's grow **right**. Both bars use one scale per row. A loss bar is hatched in the bad colour. Every figure has a fix mark. **Two columns even on a 360px phone. No sideways scrolling.**
3. Rows: Revenue, Operating result, Net result, Total assets, Equity, Employees, Founded, Website, Linked profiles, News, Job ads. Unknown values show a small hatched box with "unsurveyed".
4. Note: "Both bars in a row share one scale. Figures come from each company's latest filed accounts."

**How it works (`/method`)**. Short. Facts come from Brønnøysundregistrene, Regnskapsregisteret, NAV's job feed, Mattilsynet's inspection results and each company's own verified website. A website is published only after proof that it belongs to that exact organisation number. It is better to miss something than to publish it under the wrong company. State the number of companies and the research date from the data.

**Live lookup.** For a 9-digit number not in the data, a server route fetches `https://data.brreg.no/enhetsregisteret/api/enheter/[number]` and shows name, legal form, address and industry with a source link, labelled "Live from the official register. Not researched by Signalpost." A 404 shows a clear message.

**Footer:** "Research by OrgLens. Contains data under the Norwegian Licence for Open Government Data (NLOD) made available by Brønnøysundregistrene. Contains data from Mattilsynet." plus links to the method page and https://github.com/sankalp2515/AI-Agent-Company-Search.

### Signature components

**Fix mark.** After every figure: a 13px magenta ring (1.6px stroke) with a 3.5px centre dot, inside a 44px tap target. `aria-label="Check the source of [label]"`. On hover the ring grows 35% and tints. It opens the source panel.

**Source panel.** 400px side panel on laptops with a 3px magenta left edge. Bottom sheet on phones with a 3px magenta top edge. On laptops, draw a 1.5px dashed magenta line from the tapped mark to the panel in 520ms. Content: "⊙ POSITION CONFIRMED", the fact label and company, the value large and in full ("NOK 353,709,793"), then labelled rows: "Where it came from" (source_name), "Retrieved" (retrieved_at as date and time), "Reporting period" (period), "Exact place in the source" (where_in_source, allowed to wrap), "Why this is the right company" (identity_check), "Fingerprint of the saved source" (first 16 characters of content_sha256). Button "Open the original source ↗" (source_url, new tab). Escape and Close dismiss it and focus returns to the mark.

**Survey ring.** 36px SVG ring of 8 arcs with small gaps, clockwise from the top: website, profiles, news, description, jobs, accounts, leadership, workplaces. An arc is the line colour when not found, magenta when found for the first five, and ink when found for the last three. `aria-label="[n] of 8 areas found"`.

**Unsurveyed block.** Diagonal hatching at 135 degrees, dashed border, the word UNSURVEYED in mono capitals and the reason on a solid background. Never a dash, "N/A" or 0.

### Design

The concept is a Norwegian nautical chart in daylight. Every fact is a confirmed position, and what nobody confirmed is unsurveyed water. **Do not use** gradients, shadows, emoji, stock images, illustrations, rounded cards, a green palette, a serif headline or a default component-library look.

Fonts from Google Fonts: **Schibsted Grotesk** (400, 500, 700, 800) for headings and interface. Headlines are weight 800, tracking -0.045em, line height 0.95, up to 92px on laptops. **IBM Plex Mono** (400, 500) for every figure, organisation number, date and small capital label (11 to 12px, tracking 0.1em). **Newsreader Italic** only for short notes and the two magenta words in the headline.

CSS variables. Default is the day chart. The theme button switches to the night chart and remembers the choice.

| Token | Day | Night |
|---|---|---|
| paper (page) | #FBFCFA | #071821 |
| water (chart panel) | #DCECF1 | #0C2632 |
| shoal (contours, bar tracks) | #C3DFE8 | #123746 |
| land (compare tray, selected row) | #F4E8C3 | #2B2918 |
| card | #FFFFFF | #0B202A |
| ink | #0E2A36 | #E6F0F2 |
| muted | #48626D | #9CB6BF |
| line | #B4CAD2 | #25495A |
| mark (magenta, source tracing only) | #B0146A | #FF86BE |
| good | #0B6B57 | #5FD0B5 |
| warn | #8A5A00 | #E6B85C |
| bad | #B3261E | #F2938B |
| hatch | #9DB9C2 | #3C6070 |

Spacing 4, 8, 12, 16, 24, 32, 48, 72, 96. Corners 3px on controls and 0 on panels. Maximum width 1200px, gutters 24px (16px on phones). Panels have a 1px ink frame. Each section opens with a 1px ink rule carrying a numbered mono label on the left ("01 · FIND") and an italic note on the right.

Motion: bearing line 520ms, panel 220ms, compare bars 520ms, hover 160ms. Respect prefers-reduced-motion.

### Quality bar

- Tap targets at least 44px. Visible keyboard focus in magenta everywhere. A skip link.
- No horizontal page scrolling at 360, 390, 768 or 1440px.
- The list loads once. Company pages fetch one file.
- Loading and error states with a retry. Back button and shared links work everywhere.
- Per-page titles, a sitemap, and Organization structured data on company pages built only from published facts.
- Æ, Ø and Å display and search correctly ("lillestrom" also finds Lillestrøm).

---

## Prompt 2: only if at least 20 credits remain after fixes

> Add a language button "NO / EN" in the header. It switches interface labels only, never company data, and remembers the choice. Use exactly these Norwegian labels: Find a company = Finn et selskap. Compare = Sammenlign. How it works = Slik virker det. Revenue = Omsetning. Operating result = Driftsresultat. Net result = Årsresultat. Total assets = Sum eiendeler. Equity = Egenkapital. Employees = Ansatte. Founded = Stiftet. Website = Nettsted. Filed accounts = Innsendte regnskap. Unsurveyed = Ikke kartlagt. Check the source = Sjekk kilden. Open the original source = Åpne originalkilden. Every fact has a way back. = Hvert faktum har en vei tilbake.

---

## Review checklist

On a laptop and a real phone, in a private window:

- [ ] The chart shows on the first screen. Tapping a number opens that company.
- [ ] Search "melbye", open it, tap the revenue mark: the panel shows NOK 353,709,793, period 2025, and the original opens.
- [ ] A company with a loss shows a minus sign, not 0. A company with no revenue sits in the hatched band.
- [ ] A company with no website shows one unsurveyed block with reasons.
- [ ] Compare two companies on the phone: two columns, bars meet at the centre, no sideways scrolling.
- [ ] A shared compare link opens the same pair.
- [ ] Search "Lillestrøm" and "lillestrom".
- [ ] Night chart switch works and is remembered.
- [ ] Publish to a `sites.jboxai.com` address. Three rival entries link to an unpublished preview and show "Preparing preview" to voters.
