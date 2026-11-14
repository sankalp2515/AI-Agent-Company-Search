# Signalpost launch review

5 November 2026. Reviewed from three seats: UX, frontend architecture and CEO.

## CEO verdict

| Question | Verdict |
|---|---|
| Submit the first build to the JBOX bonus? | No. It worked, but most company pages repeated "We looked and found nothing" many times and gave no quick summary. |
| Submit after the current fixes pass? | Yes, if the retest passes. |
| Launch it as a business? | No. It's a strong demo of the product, not yet a business. |

What blocks a business launch:

- **Coverage:** 41 of 400 companies have a verified website. The other 359 rely on register data, which anyone can look up for free. Paying customers need more.
- **Customer:** we have no evidence that anyone would pay, and we don't know whether job seekers, sales teams or investors are the first buyer. Talking to 10 Norwegian sales teams would teach more than another redesign.
- **Freshness:** the data is a snapshot from 3 and 4 November. The product promises to stay current, so it needs a scheduled refresh.
- **Language:** the audience is Norwegian, and the site is in English with Norwegian industry names. Launching in Norway needs a Norwegian version. This is where Håvard's experience would matter.
- **Legal:** company websites and personal data need a rights review before public hosting at scale. `SOURCE-RIGHTS.md` already flags this for retained page bytes, which the site doesn't host.

## UX audit of the first build

| Finding | Severity | Fix |
|---|---|---|
| Thin companies repeat the same empty block in sections and rail | High: most pages | One block listing everything not found |
| No quick summary at the top of a company page | High | "At a glance" strip |
| Searching outside the 400 is a dead end | High | Live lookup in the official register |
| 400 results render at once | Medium | First 12, then "Show more" |
| Same title on every page, no share image, sitemap or structured data | Medium | Per-page metadata |
| Content is rendered in the browser only | Medium | Server rendering |
| Fix marks on legal form and town add noise | Medium | Removed from that line |
| `/design-system` is public | Medium | Removed |
| "In brief" repeats the sections below | Medium | Two statements, then a toggle |
| Every compare row is a heading, and there's no skip link | Medium | Correct semantics |
| Dates repeat in register events | Low | One date per row |
| Norwegian roles and form names; `['BDO AS']`, `30000.0 NOK`, "Uoppgitt" | Medium | Fixed in the data at no credit cost |

## Retest of the improved build

All passed in the JBOX preview at 1280px and 375px wide, with 11 credits left:

- **Search:** finds by name, number and "lillestrøm". "equinor" shows live register results, labelled as not researched.
- **Thin company page:** one "not found" block, and no repeated empty sections.
- **Source panel:** Melbye's 2025 revenue shows NOK 353,709,793 and the period.
- **Compare:** two columns on a phone, with a compact sticky header.
- **Bad organisation number:** returns a 404 page.
- **Data match:** net result on 5 sampled company pages matches the data file.
- **Technical:** per-page titles, sitemap with 403 URLs, robots.txt, structured data on company pages, no sideways scrolling on the pages tested.

Not yet checked:

- A real phone, and real users.
- A Lighthouse or automated WCAG audit.
- The published site. Canonical URLs carried preview parameters in the preview, so check them after publishing.

Known limits:

- Industry names stay in Norwegian, and company names stay in register capitals.
- `/design-system` still exists because JBOX requires it. It's unlisted and blocked in robots.txt.
- The tall phone page for large companies, about 6,500px.

## Frontend architecture

JBOX fixes the base stack: Next.js and JBOX hosting. Within it:

| Area | Decision | Why |
|---|---|---|
| Rendering | Server-render company pages, revalidate daily | Fast first view, works for search engines |
| Data | Static JSON per company, one index file | No database to secure or pay for, and easy to audit |
| Live lookup | Server routes to the official register | The accounts API doesn't allow browser calls |
| Components | Small set: FixMark, SourcePanel, Unsurveyed, AtAGlance, CompareRow | The product's identity lives in a few parts |
| Layout | Mobile-first CSS grid, tokens as CSS variables | Light and dark from one set of values |
| Animation | CSS only | One signature line doesn't justify GSAP or Framer Motion |
| Accessibility | WCAG 2.2 AA: 44px targets, focus return, skip link, shape as well as colour | Also the UX score |
| SEO | Per-page metadata, Organization JSON-LD from published facts, sitemap | Each company page can rank for its own name |
| Performance | `next/font`, no client-side list on company pages, list paginated | The list is 358 KB |
| Images | No photos; inline SVG and canvas contours | Nothing to optimise is the best optimisation |
| Deployment | JBOX hosting. Data served from this repo's `main` | Data updates need no credits |

**Risk:** the site reads from GitHub's raw file service, which is not a production CDN. Server caching reduces the exposure. A real launch should move the files to the site's own storage.

## Landing page strategy

| Section | Job in the decision |
|---|---|
| Hero with a real figure tracing to its source | Proves the promise in seconds |
| Search | Lets people act at once, which is what judges score |
| Use cases: apply, sell, partner, invest | "Is this for me?" |
| How it works | Lowers effort: three steps |
| What we refuse to do | Our real differentiator, with a real company as the example |
| What's in the research | Honest scale, so nobody is misled later |
| FAQ | Answers objections: coverage, freshness, advice |
| Closing call to action | One next step |

**Left out on purpose:** testimonials, customer logos, pricing tables and case studies. We have no customers or prices, and inventing them would be fabrication on a product whose whole claim is evidence. A real company walkthrough and a real refusal do that job honestly. "Free, no account" is the true pricing statement.
