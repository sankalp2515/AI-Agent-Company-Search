# Signalpost design system

For the JBOX bonus site. A working visual reference built from real data is in `reference/index.html`. That page is a guide for JBOX only. The site we submit must be built in JBOX.

## Who it is for and what they must do

Someone about to apply to, sell to, partner with or invest in a Norwegian company. Builderr's three required tasks, on laptop and phone:

1. Find a company.
2. Compare two.
3. Check where a fact came from.

Builderr scores the site on UX and runs a popular vote. So the site has two jobs: make the three tasks effortless for a judge, and show a voter something memorable within ten seconds.

## The idea: a nautical chart of a company

A signal post tells you where you are and how far to trust it. The site borrows from the Norwegian nautical chart, a document built on the same discipline as this agent: every mark was surveyed, and anything that wasn't is labelled as such.

| Chart idea | In the site | Why it helps |
|---|---|---|
| Position fix (circle with a dot) | The **fix mark** beside every fact | One recognisable way to check any fact |
| Bearing line | Dashed magenta line from a fact to its source | Shows the idea on the first screen, without words |
| Unsurveyed water (hatched) | The **unsurveyed** pattern for anything unknown | Absence can never be misread as zero, which the challenge explicitly forbids |
| Magenta notes | Magenta is used only for tracing sources | The colour itself comes to mean "you can check this" |
| Italic for water, upright for land | Facts stand upright, notes about them lean | Separates what is known from commentary |

**The one thing to remember it by:** tap any number and it shows you where it came from.

## Colour

Every text pair below measures at least 4.5:1 on all three backgrounds, in both themes.

| Token | Light | Dark | Use and reason |
|---|---|---|---|
| `water` | `#F3F8F9` | `#0B1A22` | Page. A pale chart blue that avoids the warm cream most editorial sites use. |
| `shoal` | `#DDECF1` | `#12303C` | Bar tracks and quiet fills. |
| `land` | `#F2E8CC` | `#2B2A1E` | Rare accent surface, for chart character. |
| `paper` | `#FFFFFF` | `#0F232D` | Cards and the source panel, so they lift off the water. |
| `ink` | `#10303C` | `#E4EEF1` | Text and primary shapes. 13:1 on water in light mode. |
| `muted` | `#49646E` | `#9DB6BF` | Labels. 5.9:1 on water in light mode. |
| `line` | `#B9CFD6` | `#2B4C59` | Dividers. |
| `mark` | `#A3115C` | `#F27AB3` | Source tracing only. Never decoration. 7:1 on water in light mode. |
| `good` | `#0C6B58` | `#5FD0B5` | Checked and found. |
| `warn` | `#8A5A00` | `#E6B85C` | Blocked, ambiguous or failed. |
| `bad` | `#B3261E` | `#F2938B` | Losses. Always paired with a minus sign and a hatched bar, so colour is never the only signal. |
| `hatch` | `#9DB9C2` | `#3C6070` | Unsurveyed pattern. |

Dark mode follows a ship's night chart, which exists to protect the eyes on a dark bridge.

## Type

| Face | Role | Reason |
|---|---|---|
| Schibsted Grotesk 400 to 800 | Headings and interface | Drawn for Schibsted, the Norwegian media group, so æ, ø and å look native. |
| IBM Plex Mono 400, 500 | Every figure and organisation number | Tabular digits line up in columns. A figure reads as a measurement. |
| Newsreader Italic 400 | Annotations only | The chart's italic convention. Never for facts. |

Scale in px: 13, 15, 16 (body), 17, 22, 28, 36, 44, 56, 76. Headings use tight tracking (-0.03em) and bold weight. Body stays near 65 characters wide at line height 1.5. All three fonts are on Google Fonts.

## Spacing and grid

- **Spacing:** 4, 8, 12, 16, 24, 32, 48, 72. Small steps bind a fact to its label, and large steps separate sections, so few boxes are needed.
- **Grid:** 4 columns on phones, 12 from 760px, 1160px maximum, 16px minimum gutter.
- **Profile layout:** reading column plus a 280px sticky rail from 900px. On phones the rail moves below the content.
- **Corners:** 3px. Charts are drawn with straight edges, and big radii would make it feel like a generic app.
- **Shadows:** none. Lines and paper against water do the work.

## Components

| Component | Behaviour |
|---|---|
| **Fix mark** | 16px visual inside a 44px tap target. Scales up and fills on hover. Label: "Check the source of [fact]". |
| **Source panel** | Side panel on laptops, bottom sheet on phones, so the fact stays visible. Shows answer, source name, retrieval date, reporting period, exact place in the source, why it is the right company, source fingerprint, and a link to the original. Escape closes it and focus returns to the mark. |
| **Unsurveyed block** | Hatched, dashed border, with the reason in words: looked and found nothing, source refused, unsure of the company, or check failed. |
| **Search** | Large field with a visible label. Filters as you type on name, number, town and industry. A no-match state states the sample size. |
| **Result row** | Name, number, town and industry, with a Compare toggle. |
| **Compare tray** | Fixed at the bottom. Shows picks and a "Compare these two" button at two. |
| **Compare row** | Always two columns, even on phones, with the label on its own line above. Each bar row shares one scale. A loss bar is hatched. |
| **Accounts table** | Years as columns, newest first. Scrolls inside its own box on phones, never the page. |
| **What we checked rail** | Every information type with its state, in shape as well as colour: solid dot, hatched dot or diamond. |

## Icons and illustration

Lucide outline icons at 1.5px, always with a text label. No emoji, stock photos or AI art. The only illustration is depth contours drawn by code on the home page, so the data stays the picture.

## Motion

- **Signature:** the bearing line draws from fact to source in 520ms. It appears once, on the first screen.
- **Feedback:** 160ms on hover and press. The source panel takes 220ms.
- **Bars:** grow to value over 520ms when companies change.
- **Rules:** nothing waits for scrolling, and everything is complete at rest. Reduced-motion settings turn it all off.

## Story flow

1. **Promise:** "Every fact has a way back." A real figure and its real source prove it at once.
2. **Find:** search is on the first screen. There is no marketing page in front of it.
3. **Read:** a short brief, then accounts, web, news, hiring and people.
4. **Trace:** any mark opens source, date, exact place and why it is the right company.
5. **Compare:** two companies side by side.
6. **Trust:** unknowns stay visible, each with a reason.

## Major decisions

| Decision | Rejected | Why |
|---|---|---|
| Product as the hero | Marketing landing page | Judges score ease of use, and voters should touch the product at once. |
| A mark on every fact | A "Sources" tab or footnotes | Checking is the core task, so it takes one tap from the fact. |
| Two columns on phones | Sideways scrolling or stacked cards | Comparing means seeing both at once. |
| Hatching for unknowns | Dashes or "N/A" | A dash looks like a blank or a zero. Texture can't be misread. |
| Chart magenta and pale blue | The design database's navy and amber | Navy says "bank template". Magenta is unusual, and it comes from the subject. |
| Schibsted, Plex and Newsreader | The database's Exo and Roboto Mono | Exo reads as science fiction, and monospace body text tires readers. I kept the database's contrast, density and accessibility rules. |
| "400 researched companies" stated openly | Implying all of Norway | The whole project's advantage is honesty, and overclaiming would undercut it. |
