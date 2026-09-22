# Design package: AI Climate Prediction (Tier 1, trimmed)

Deploy folder: `climate-site/` (index.html + assets/). Review files live here, outside it.
Hero footage: the Higgsfield video is not generated yet (connector waiting on sign-in). The hero ships as a
procedural "isobar field" drawn on a canvas and driven by scroll, using the same band, gate, and lerp
engineering the video hero uses. When the video is approved it replaces the canvas; nothing else changes.

## 1. Brand premise
**The reading.** A forecast is only as good as the reading it starts from. Indian weather apps fail on the
street level because they start from a 12 km grid box, not a reading. This site teaches and sells one idea:
read the live sky first, then predict, then show the reading so anyone can check it.

## 2. Palette (sampled from the monsoon-night-to-radar world of the hero)
```css
:root{
  --canvas:#0b161d;        /* deep monsoon night, blue-green tint */
  --panel:#12232c;
  --panel-2:#172e39;
  --accent:#67e8c5;        /* radar mint: CTA, focus, rare emphasis */
  --accent-hover:#8ff2d6;
  --accent-muted:rgba(103,232,197,.18);
  --text-secondary:#a9bcc0;
  --text-primary:#eaf3f1;
  --rain:#6fb4ff;          /* data colors only, never decoration */
  --heat:#ffb35c;
}
```

## 3. Type trio
Display: Unbounded 500 / 700. Body: Manrope 400 / 600. Labels: IBM Plex Mono 400.

## 4. Band map (hero 400vh, scroll range 300vh; ranges are starting points)
| Band | Range | Footage moment | Copy (verbatim) | Entrance |
|---|---|---|---|---|
| 1 | 0.00 to 0.20 | dense dark contours, night, cell faint at left | "The sky already told you." | blur-to-sharp, with load ramp |
| 2 | 0.24 to 0.46 | lines ripple, a blue rain cell blooms at right | "Clear skies, said the app." / "Then the street flooded." | drift-down |
| 3 | 0.50 to 0.72 | contours tighten into ordered bands | "Any Indian city. Every 15 minutes." / "History back to 1940." | grid snap-align |
| 4 | 0.78 to 1.00 | contours settle around one calm cell at left; right lane clear | h1 "Tomorrow, read today." sub "AI Climate Prediction turns live readings into next-day forecasts you can check against the sky." CTA "See live readings" / "How it works" | word rise into staged settle |

Action lane: left third (the cell). Text lane: right 55 percent. Lines calm down toward the right edge.

## 5. Static-hero copy block (phones, reduced motion)
"Tomorrow, read today." / "AI Climate Prediction turns live readings into next-day forecasts you can check against the sky." / "See live readings" / "How it works"

## 6. Below-fold outline (single CTA anchor: #early)
- **Live readings (#live)**, horizontal card strip. Kicker "LIVE NOW". H2 "Six cities, read this minute." Lede "Straight from the feed our model learns from. Refreshed every 15 minutes. No key, no login." Cards: city, temperature, humidity, rain, wind, condition. Living element: pulsing live dot. Data: Open-Meteo, fetched in the browser.
- **How it works (#how)**, vertical timeline with a self-drawing spine. Kicker "THE METHOD". H2 "Read. Learn. Forecast."
  1. "Read." "Live conditions and forty years of daily history for the exact point you care about. Not a 12 km grid box."
  2. "Learn." "A model trained on what actually happened the next day, at that point, in that season."
  3. "Forecast." "Tomorrow's temperature, shown with the reading it came from, so you can check it against the sky."
- **The interactive moment (#run)**, centered stage. Kicker "TRY IT". H2 "Hold to pull tomorrow." Lede "Pick a city. Press and hold. Seven days arrive from the live feed our model trains on." Button label "Hold". Under the cards: "Live forecast feed from Open-Meteo. The project's own next-day estimate plugs in here." Releasing early eases back. Completion lights the seven cards in sequence. Reduced motion: one click completes it.
- **Straight answers (#faq)**, two-column list. Kicker "STRAIGHT ANSWERS". H2 "What people ask first."
  - "Is this real data?" "Yes. Every number on this page comes from Open-Meteo's public feed, which needs no key and refreshes every 15 minutes. India's official station network, 1,729 IMD stations, is the next source once access is granted."
  - "How accurate is it?" "We publish the average error on the last 365 days the model never saw, right under the forecast, next to the plain carry-today-forward baseline. A number you cannot check is not a forecast."
  - "Does it work for my town?" "Any point in India with a latitude and longitude. No grid box, no nearest big city."
  - "Can I use it in my own app?" "Yes. The code is open source under the MIT license. Run it, fork it, ship it."
- **CTA (#early)**, split panel. Kicker "EARLY ACCESS". H2 "Get the first forecasts." Lede "Leave your city and email. When next-day forecasts open for your area, you hear first." Form labels: "Your name", "Email", "City". Button: "Send me the first forecast". Microcopy: "Demo form. Nothing is sent yet." Success: "Noted. {City} is on the list. Check the sky tomorrow, then check us." Handling: JS-only success state (disclosed).
- **Footer**: "AI Climate Prediction. Open source under the MIT license." "Weather data: Open-Meteo." "The hero is drawn live on your screen. No photos or stock footage were used." Links: GitHub, Data source, Back to top.

## 7. Vector layer plan
- Signature: the isobar field. Canvas contours in the hero; hand-drawn SVG contour dividers between sections that draw themselves on entry; a vertical spine in the timeline.
- One fixed environment layer: two soft radial glows drifting on a 90 s cycle plus faint grain.
- Whisper elements: live dot pulse (live), spine glow (how), ring breath (run), accent hairline shimmer (faq), none on the form.
- Reduced motion: everything at final state, drives stopped, canvas drawn once at rest.

## 8. Engineering list
dt-normalized lerp loop that rests off-screen; delta-gated DOM writes (opacity 0.01, --k 0.008); smoothstep band edges with first band no ease-in and last band no ease-out; four-layer legibility (base scrim, per-band scrim on the text column, text-shadow token, chip scrim); five static-hero gates identical in CSS and JS with live change listeners; complete without any media; overflow-x clip; entrances via IntersectionObserver with retired stagger delays; body.paused on hidden tabs; skip link, landmarks, focus-visible, 44 px targets under coarse pointer; og tags left for the deploy step.

## 9. Copy gate
Every viewer-facing line above ships verbatim. Before anyone sees the page: zero em dashes, zero of the stock words (leverage, seamless, empower, unlock, robust, actionable, data-driven, solutions), and the body-copy sweep for AI tells. "Read. Learn. Forecast." is a designed triplet and stays.
