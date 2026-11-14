# Market research and scorecard

13 November 2026. How company-research products are built and launched, and how our site compares with the 13 Signalpost voting sites and the two incumbents.

## How these products are built and launched

| Product | How it is built | How it reaches users | What we take from it |
|---|---|---|---|
| **Proff** (Norway's incumbent, part of Enento) | Register and accounts data on one page per company: key figures, roles, shareholders, addresses | Free browsing found through search, then Proff Pluss at NOK 99 a month and Forvalt subscriptions from NOK 12,490 a year for ratings, ownership, segmentation and APIs | One page per company that search engines can find. People pay for decisions (ratings, lists), not for raw facts |
| **OpenCorporates** | Open register data from many countries, with the source of each field | Free pages, paid API and bulk data | Provenance on every field builds trust, and open data is a feature rather than a weakness |
| **Clay with Claygent** | An agent that visits websites and summarises them, over a "waterfall" of 130+ data providers | Free trial, then sold on coverage ("80%+ enrichment coverage"), with workflows and CRM sync | Lead with coverage and with what a team can do next: export a list and act on it |
| **Exa Websets** | A web-research agent that builds lists of companies matching criteria, each with citations | Developer API plus a simple interface, and partnerships with data providers | Every answer cites a source. Building lists is the job people pay for |

Three patterns repeat across all of them:

1. **Every company has its own page** that search engines index. This is how people discover these products.
2. **Evidence sells trust.** OpenCorporates and the AI agents all show where a fact came from. Proff does not show sources per figure, and this is our clearest advantage over the incumbent.
3. **Lists and change alerts bring people back.** Prospecting lists, export, and "tell me when this company changes" are what people pay for.

## Scorecard

Scored 0 to 5 by me on 7 November (rivals) and 13 November (ours). Rival mobile layouts were not tested, so that column is marked as not checked. "Ours" is the rebuilt agent viewer (`out/site1000/run/index.html`) with the version 2 design. The JBOX build follows the same design but does not exist yet.

| Site | Companies | Find | Compare | Check a source | Unknowns shown honestly | Memorable at first sight | Extras | Total of 30 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **Ours, version 2** | 1,000 | 4 | 5 | 5 | 5 | 4 | 4 | **27** |
| Rohith | 150 | 4 | 4 | 4 | 4 | 3 | 4 | 23 |
| Arnav | 100 | 3 | 3 | 4 | 3 | 5 | 3 | 21 |
| Kildespor | 100 | 4 | 4 | 4 | 3 | 3 | 3 | 21 |
| Alex (SQOPA) | 1,000 | 4 | 3 | 4 | 4 | 3 | 3 | 21 |
| Sarthak | 1,000 | 4 | 3 | 4 | 3 | 3 | 2 | 19 |
| Karan | 1,034 | 4 | 3 | 3 | 3 | 2 | 3 | 18 |
| Hardik | 100 | 3 | 3 | 3 | 3 | 4 | 2 | 18 |
| Ritambra | not stated | 3 | 3 | 4 | 3 | 3 | 2 | 18 |
| Dhruv | 100 | 4 | 3 | 3 | 3 | 2 | 3 | 18 |
| Hridya | 120 | 3 | 3 | 3 | 3 | 3 | 2 | 17 |
| Avidha, Raveena, Afra | n/a | 0 | 0 | 0 | 0 | 0 | 0 | 0: voters saw "Preparing preview" |
| Proff (incumbent) | all | 5 | 3 | 1 | 2 | 2 | 5 | 18 |
| OpenCorporates | all | 5 | 1 | 3 | 2 | 1 | 4 | 16 |

Why ours scores where it does:

- **Compare 5:** both companies sit on one centre line, with bars sharing a scale only when they share a currency (Equinor reports in USD and Melbye in NOK). No other site checks this.
- **Check a source 5:** every figure has a mark that opens the source with retrieval time, period, exact place, identity proof and fingerprint. Rohith and Kildespor use numbered footnotes, which take reading. Arnav's panel shows raw `organisasjonsnummer=` text.
- **Unknowns 5:** one hatched "Unsurveyed" block with the reason for each gap, and the summary lists what is still unknown.
- **Memorable 4, not 5:** Arnav's map is more striking at first sight. Our chart, where every number is a company, is the only hero visual that is also the data and a way in.
- **Find 4, not 5:** Proff searches all of Norway. Ours searches the researched set only. The JBOX build adds a live register lookup for any organisation number.
- **Extras 4:** night theme, CSV export of the filtered list, shareable links for a company or a pair, and a new financial-position sentence (operating margin and equity ratio from the filed figures). It has no change alerts, which need accounts and a server.

**Verdict:** on this scorecard ours leads the voting sites by 4 points and the incumbents on everything except search reach. That is my judgement, not a vote. Voters may still prefer Arnav's map at first glance, which is why the chart has to be on the first screen at full width.

## Improvements made because of this research

| From | Change | Status |
|---|---|---|
| Proff, Clay | Export the filtered company list as CSV | Done in the agent viewer |
| Investors and buyers | A sourced sentence on operating margin and equity ratio, flagging when liabilities exceed assets | Done in the agent's summaries: 987 of 1,000 companies |
| OpenCorporates, Exa | Source on every figure, including summary sentences | Done |
| Proff | Search any organisation number live in the official register | In the JBOX prompt |
| Rivals' preview links | Publish to a permanent `sites.jboxai.com` address before sending the link | In the JBOX checklist |
| Proff, Clay | Change alerts | Not done: a static site has no accounts or server |
