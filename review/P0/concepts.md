> STATUS: DRAFT - UNVERIFIED - requires human review at the Phase 0 gate

# Visual concepts: how they were made, and the audit

The three concepts and their six mockups are on the review page `docs/concepts/index.html` (on GitHub Pages at
`/concepts/`). This file records the process the brief asked for and the audit run before calling them done.

## Skills used, and what did not run

| Skill | How it was used | Limits |
|---|---|---|
| **emil-design-eng** (Emil Kowalski) | Animation and interaction rules: a 0.97 scale on press, strong ease-out (`cubic-bezier(0.23, 1, 0.32, 1)`), 140 ms transitions on buttons only, no animation on keyboard-driven actions, `prefers-reduced-motion` removes the movement | Mockups are static screens, so most of its motion guidance applies from Phase 1 |
| **Impeccable** 4.7.0 | Modes (follow-me screen = Operate, website = Persuade), the new-work process (seven candidate worlds from the audience's own culture, then committed directions), the colour-strategy choice, the craft floor and the audit below | Its launcher (`scripts/impeccable`) downloads a binary on first run; it was **not run**, so the dice-roll `concept-seed` step and the automated detector did not happen. Directions were chosen by hand from the seven worlds; the audit was done by hand and by computed contrast ratios |
| **taste-skill** v2 | App-screen rules: colour on data not chrome, KPIs as type not tiles, no eyebrow labels, no index numbers, no gradients in UI, one finding per screen, a signature element per product. `draw.mjs --app` dealt `true-black-flat` and `data-terminal` for a monitoring kind; Monitor takes the first one's move (elevation by lightness, primary by inversion) | `inspect.mjs` (browser inspector) was not run |

## Seven worlds the audience knows by heart

The audience: a vlogger and engineering teacher in San Pedro, on a cliff-top trail, phone in one hand in full sun;
later at a desk, studying a control loop. Candidate worlds, by resonance:

1. **The VFR sectional and the UAS facility map**: the pilot's own legal map; LA is Class B country. Carries limits, distance and heading natively. → **Sectional**
2. **The field monitor on a film set**: frame lines, false colour, tally light, peaking. Carries framing and tracking. → **Monitor**
3. **LA County lifeguard towers and beach flags**: painted numbers, flags as status, read from a distance in sun. → **Tower**
4. NOAA nautical chart of San Pedro Bay: soundings, magenta overprint. Close to 1; folded into Sectional.
5. Container-port stencils and placards (Port of LA): bold, but brand-adjacent and industrial; set aside.
6. The engineering computation pad (green grid paper, hand-drawn Bode plots): fits the Control Lab only, and its grid fights the house rules against hairlines; set aside.
7. Kite and spinnaker ripstop panels: committed colour fields and motion; too decorative for a safety screen; set aside.

The category default (a dark drone-app dashboard with a neon accent and a HUD (heads-up display) font) and its
predictable opposite (a cream editorial page) were kept off the list.

## The three directions in tokens

| | Sectional | Monitor | Tower |
|---|---|---|---|
| Physical scene | Phone in full sun; laptop indoors | Evening edit and indoor lab; outdoor needs a bright variant | Phone in full sun on the beach |
| Light or dark | Light | Dark (true black) | Light |
| Colour strategy | Restrained: tinted neutrals + one accent | Committed dark, colour only on data | Committed: tower blue on 30-50 % of each screen |
| Ground / ink | `#fafbf6` paper, `#eceee2` land / `#16222a` | `#000` / `#f3f3f0` | `#a3d3e8` tower, `#fffdf8` / `#0c2b3b` |
| Wisp's colour (drone and path only) | chart magenta `#9f166c` | peaking yellow `#ffd60a` | rescue orange `#c63a12` |
| Limits, sensors, cautions | airspace blue `#1d5aa3` | false colour `#ff5a4e` / `#ffa31a` / `#3ccf6e`; tally `#ff3b30` = recording only | beach-flag yellow `#ffd23f` |
| Type | Overpass (Highway Gothic lineage) | Saira, Saira Semi Condensed | Barlow, Barlow Condensed |
| Signature element | Facility-map ceilings and a ticked flight path | Obstacle distance on the picture's edges; gain faders | Side-view elevation with dimension lines; painted numerals |

All fonts are self-hosted from `docs/concepts/fonts/` (SIL Open Font License).

## Audit (Impeccable `audit` dimensions, scored 0-4, done by hand)

| # | Dimension | Sectional | Monitor | Tower | Key finding |
|---|---|---:|---:|---:|---|
| 1 | Accessibility | 3 | 3 | 3 | Text contrast passes AA everywhere checked (table below). Buttons are real buttons; mode pickers are radio groups. Map and picture have text alternatives. Not yet tested with a screen reader or keyboard-only. |
| 2 | Performance | 3 | 3 | 3 | Static SVG and HTML, self-hosted fonts (272 KB for all three concepts). No 3D yet: the 60 fps requirement is untested until the Phase 1 3D view. |
| 3 | Theming | 3 | 3 | 3 | Tokens on `:root` per concept; some SVG colours in Tower are literal values. Each mockup is single-theme by design (the concept picks light or dark). |
| 4 | Responsive design | 1 | 1 | 1 | Fixed 390 × 844 and 1440 × 900 artboards. Touch targets ≥ 40 px on the phone screens (steppers 34 px in Sectional: P2). The review page itself reflows to 390 px. |
| 5 | Implementation integrity | 3 | 3 | 3 | All three show the same data from one file (`shared/data.js`, with assertions); Control Labs compute the equation, step response and margins live from one model (`shared/model.js`). |
| | **Total** | **13/20** | **13/20** | **13/20** | Acceptable for concept mockups; responsive builds and a screen-reader pass belong to Phase 1. |

**WCAG (Web Content Accessibility Guidelines) contrast, computed** (AA: 4.5:1 for text, 3:1 for large text and
graphics):

| Pair | Ratio | Pair | Ratio | Pair | Ratio |
|---|---:|---|---:|---|---:|
| Sectional ink on paper | 15.6 | Monitor ink on black | 18.9 | Tower ink on tower blue | 9.2 |
| Sectional muted on land | 6.6 | Monitor muted on card | 7.7 | Tower muted on tower blue | 5.7 |
| Sectional magenta on paper | 7.2 | Monitor yellow on black | 14.9 | Tower orange on paper | 5.1 |
| Sectional airspace blue on water | 5.2 | Monitor amber tag on black | 10.5 | Tower orange on tower blue (graphics only) | 3.3 |

The audit caught one failure, fixed before capture: Tower's first orange (`#e4461a`) measured 2.5:1 on the blue
field. It became `#c63a12`, and text on the blue field uses ink.

**Brief requirements on these screens:** telemetry latency is shown on all three (84 ms on the phone, 3 ms from
SITL in the Control Lab); the stop button is always on screen; safety-critical items (battery, link, distance to
the nearest obstacle, airspace) are visible without scrolling; reduced motion is handled; 60 fps 3D is not yet
testable.

## Recommended actions (Phase 1, after a concept is chosen)

1. **[P1]** Build the chosen follow-me screen responsively (320-430 px phones, landscape) and test it outdoors in sun.
2. **[P1]** Screen-reader and keyboard pass on the live app, not the mockups.
3. **[P2]** Raise the Sectional steppers to 44 px targets.
4. **[P2]** Move Tower's literal SVG colours into tokens.
5. **[P2]** If Monitor is kept for the camera view: design the high-brightness outdoor variant first.
