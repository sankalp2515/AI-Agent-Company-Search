# Signalpost design system, version 2

10 November 2026, updated 13 November. For the rebuild on the new JBOX account. A working reference built from our real data is in `reference/index.html` (run the `jbox-reference` preview and open `/v2/reference/index.html`). The agent's own viewer now uses this design too, because the evaluator scores UX and synthesis on it. Market research and a scored comparison with all 13 voting sites and the incumbents are in [MARKET-AND-SCORECARD.md](MARKET-AND-SCORECARD.md).

## What the 13 voting sites do

I opened all 13 on 7 November. Three (Avidha, Raveena, Afra) were stuck on "Preparing preview" because they link to an unpublished preview. The other ten:

| Site | What it does well | Weakness |
|---|---|---|
| Arnav | Map of Norway with a revenue dot per company, a radial "every dot connects a fact to its source" diagram, serif display type | 100 companies. The map is decoration once you start searching |
| Hardik | Rotating 3D terrain illustration in the hero | Labelled "conceptual illustration". It shows no data |
| Rohith | Filter chips, compare up to 3, a stat grid at the top of each profile, "What changed" | Raw URLs in the summary text, Norwegian field names |
| Kildespor | Dense directory with coverage dots, brand taglines, `/` shortcut, theme switch | Looks like an admin table |
| Alex (SQOPA) | 1,000 companies, three-pane layout, "Not found is information, too" | Busy first screen |
| Sarthak | Calm serif, 1,000 companies, 46,791 facts stated up front | Little to remember |
| Ritambra | Live fact card with a source extract in the hero | Same idea as our first build |
| Dhruv, Karan, Hridya | Working directories with filters | Generic |

Two patterns matter:

- **Eight of the ten are dark green or cream with a serif headline that says "Find a company. Follow the source."** A voter who opens five of them will not remember which was which.
- **The two most memorable (Arnav, Hardik) won attention with one big hero visual.** Neither visual helps you do the three tasks.

Our first build had the strongest tracing idea (a mark on every figure) but a plain hero, no filters, no theme switch and 400 companies. It was also dark, so it blended in.

## The idea: the chart of Norwegian business

Version 1 borrowed three symbols from the Norwegian nautical chart. Version 2 makes the whole site a chart, in daylight.

On a sea chart the water is covered in small numbers. Each one is a depth that somebody measured. On our first screen, **each number is a company**: its employee count, placed by the year it was founded (across) and its revenue (up). Companies with no filed revenue sit in a hatched band labelled "unsurveyed". Tap a number and you are on that company.

| Decision | Reason |
|---|---|
| The hero is a real chart of every company in the data | The two sites voters will remember have a hero visual. Ours is the only one where the visual is the data and the navigation. It also shows honestly how much we know: the hatched band is visible at a glance |
| Day chart by default, night chart as a switch | Seven of ten rivals are dark. A pale blue chart with black ink and magenta marks is recognisable in a thumbnail on the voting page, which is where the vote starts |
| One accent, magenta, used only for "you can check this" | Real charts print notes and bearings in magenta. Scarcity teaches the colour's meaning within one screen |
| Keep the fix mark on every figure | It is our best idea and nobody else has it. Rivals use numbered footnotes, which need reading. A mark needs one tap |
| Hatching for everything unknown | The challenge forbids showing a missing value as zero. Texture can't be misread as a number |

**The one thing to remember it by:** a chart where every number is a company, and every figure shows its way back.

## Colour

All text pairs measure at least 4.5:1 in both themes.

| Token | Day chart | Night chart | Use and reason |
|---|---|---|---|
| `paper` | `#FBFCFA` | `#071821` | Page. Deep water on a chart is left white |
| `water` | `#DCECF1` | `#0C2632` | The chart panel and quiet fills. Shallow-water blue |
| `shoal` | `#C3DFE8` | `#123746` | Contour lines and bar tracks |
| `land` | `#F4E8C3` | `#2B2918` | Rare highlight surface, the buff of charted land. Used for the selected row and the compare tray only |
| `card` | `#FFFFFF` | `#0B202A` | Panels that lift off the page |
| `ink` | `#0E2A36` | `#E6F0F2` | Text, frames, bars. 14:1 on paper |
| `muted` | `#48626D` | `#9CB6BF` | Labels. 6:1 on paper |
| `line` | `#B4CAD2` | `#25495A` | Hairlines |
| `mark` | `#B0146A` | `#FF86BE` | Source tracing only. 6.9:1 on paper |
| `good` | `#0B6B57` | `#5FD0B5` | Growth, found |
| `warn` | `#8A5A00` | `#E6B85C` | Blocked, unsure, failed |
| `bad` | `#B3261E` | `#F2938B` | Losses, always with a minus sign and a hatched bar |
| `hatch` | `#9DB9C2` | `#3C6070` | The unsurveyed pattern |

The night chart follows a ship's night chart, which is dimmed to protect eyes on a dark bridge. It is a second theme, not the brand.

## Typography

| Face | Role | Reason |
|---|---|---|
| **Schibsted Grotesk** 400, 500, 700, 800 | Headings and interface | Drawn for Schibsted, the Norwegian media group. Æ, Ø and Å are native, and a Norwegian reader has seen it in the news all their life |
| **IBM Plex Mono** 400, 500 | Every figure, organisation number, date and label | Tabular digits line up. A figure in mono reads as a measurement, which is what a sounding is |
| **Newsreader Italic** 400 | Short annotations and the accent phrase in the headline | Charts set water names and notes in italic. Facts stand upright, and commentary leans |

- **Scale (px):** 12, 13, 15, 16 body, 19 lede, 26, 40, 60, 92.
- **Headlines:** weight 800, tracking -0.045em, line height 0.95. The size does the work that colour does on other sites.
- **Labels:** Plex Mono 500, 11 to 12px, uppercase, tracking 0.1em.
- **Company names:** shown in title case ("Melbye AS"), not register capitals, because a wall of capitals is hard to scan.
- **Body:** line height 1.5, at most 62 characters wide.

## Spacing and grid

- **Spacing:** 4, 8, 12, 16, 24, 32, 48, 72, 96. Small steps bind a figure to its label. Large steps separate sections, so few boxes are needed.
- **Grid:** 12 columns, 1200px maximum, 24px gutters. 4 columns and 16px gutters below 860px.
- **Frames:** 1px ink. The chart has a double frame, like a chart's border. Sections open with a 1px ink rule carrying a numbered label on the left and an italic note on the right.
- **Corners:** 3px on controls, 0 on panels. Charts are drawn with straight edges.
- **Shadows and gradients:** none.

## Components

| Component | Behaviour | Why |
|---|---|---|
| **Soundings chart** | Every company is a number (employees) or a small ring (unknown). Across: founding year, 1970 and earlier at the left edge. Up: latest revenue on a log scale. Bottom band: hatched, for companies with no filed revenue. Hover or focus shows a card. Tap opens the company. Filters and search dim the numbers that don't match. On phones it shows every third company and stays tappable | It is the brand image, the overview and a way in, all at once |
| **Fix mark** | 13px magenta ring with a centre dot inside a 44px target, after every figure. Label: "Check the source of [fact]" | Checking a fact is a core task, so it takes one tap from the fact |
| **Source panel** | Side panel on laptops with a dashed magenta bearing line drawn from the figure to the panel in 520ms. Bottom sheet on phones. Shows the value in full, source, retrieval time, reporting period, exact place, why it is the right company, fingerprint and a link to the original | The line makes the idea visible without words |
| **Survey ring** | A ring of 8 arcs beside each company in a list: website, profiles, news, description, jobs, accounts, leadership, workplaces. A found arc is filled, and web arcs are magenta | Shows how much is known before you click. Rings also sort well by eye |
| **At a glance** | Four to six figures under the company name, each with a mark and the change on the previous year | The first build's review found no quick summary |
| **Accounts table** | Years as columns, newest first, with a small trend line per row. Scrolls inside its own box on phones | Three years in one look |
| **Unsurveyed block** | Hatched, dashed border, the word UNSURVEYED and the reason in plain words | Absence can't be mistaken for zero |
| **Compare** | Butterfly layout. Company A's bars grow left from a centre line and company B's grow right, on one scale per row. Two columns even on phones. A loss bar is hatched red | The centre line makes the comparison a single glance. No rival does this |
| **Filter chips** | All, verified website, hiring now, has news, municipality, industry. Sort by depth of research, revenue, name, founded | Matches the best directories among the rivals |
| **Compare tray** | Fixed at the bottom on `land` buff once one company is picked | The only place the buff appears, so it is noticed |

## Iconography and illustration

- **Logo:** the fix mark with four ticks, like a chart's position symbol. It is the same shape as the control people tap, so the brand and the main action are one thing.
- **Icons:** Lucide outline at 1.75px, always with a text label. Arrows are typed characters (↗ ←).
- **Illustration:** depth contours and a compass rose, both drawn in code. No photos, stock art, AI images, emoji or 3D.

The rule is that every picture on the site is either data or a chart convention.

## Motion

| Moment | Motion | Reason |
|---|---|---|
| First load | Soundings fade in over 600ms, oldest companies first | Reads as a chart being surveyed |
| Opening a source | Bearing line draws in 520ms, panel slides in 220ms | The signature |
| Compare bars | Grow from the centre line in 520ms | Shows the scale |
| Hover and press | 160ms | Feedback only |

Nothing waits for scrolling, everything is complete at rest, and reduced-motion settings turn all of it off.

## Story flow

1. **Promise:** "Every fact has a way back."
2. **Proof:** the chart. A thousand numbers, each one a company.
3. **Find:** search is on the first screen, and `/` focuses it.
4. **Read:** at a glance, a short brief, then accounts, web, news, hiring, people.
5. **Trace:** any mark draws its line to the source.
6. **Compare:** two companies on one centre line.
7. **Trust:** unknowns stay visible, each with a reason.

## Decisions I rejected

| Rejected | Why |
|---|---|
| A map of Norway | Arnav has it, and a second map would look like a copy. We also have no coordinates in the data |
| A 3D or WebGL hero | High build risk in one shot, slow on phones, and it would show no data |
| Dark by default | It would put us in the same thumbnail as seven rivals |
| A serif headline | Eight rivals use one |
| Marketing sections, testimonials, pricing | We have no customers. Inventing them would undercut a product about evidence |
| A Norwegian language switch in the first build | Worth doing for Håvard, but it adds risk to the one build. It is the second prompt if credits allow |
