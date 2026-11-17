# DEVLOG — gta6-twitch-ccu-forecast-01 entry

## What the program does

`main.py` (repo root, Python stdlib only, deterministic, ~0.08 s per case):

1. Anchors on the case's hour-1 print `p1`.
2. Builds the prior **at run time from the case's own `comparables`** (the
   ~40 past launches shipped inside every case file): each comparable's
   release-day curve is normalised by its own hour-1 count, giving log
   ratios `ln(viewers_h / viewers_1)` for h = 2..24.
3. Filter: a comparable enters the prior only if it was already live at
   00:00 UTC — hour-1 count ≥ 5% of its own release-day peak
   (`LIVE_FRAC = 0.05`; relaxed ×0.5 steps if fewer than 6 launches pass).
   This keeps rolling midnight-local console launches (GTA VI's pattern,
   and all four practice launches) and drops single-global-unlock launches
   whose hour 1 is near zero and whose normalised curves explode mid-day
   (Silksong, Battlefield 6, Baldur's Gate 3, …). The comparable that is
   GTA VI's own pre-release category history is marked "Not a launch" in
   its unlock note and is always excluded.
4. Per hour, the forecast's five quantiles are the empirical quantiles
   (type-7 interpolation) of that hour's log-ratio sample, smoothed with
   one [1,2,1]/4 pass across neighbouring hours, exponentiated × p1,
   forced non-decreasing, clamped to (0, 1e9], rounded half-up to 2 dp.

No network, no model calls, no baked-in data: the prior adapts to whatever
comparables the final case (h00, 42 launches incl. the four practice
games) carries.

## Data sources (development only — the entry itself is self-contained)

- Practice answers: the kit's case files hold no answers, so the four
  practice launches' release-day hours were fetched from SullyGnome with
  the exact API the kit's `input/NOTICE.txt` documents (one GameViewers
  request per launch, "Average viewers" dataset; 4 requests total, no
  bulk download). Cross-check: each fetched series' hour-1 value equals
  the case's `known` print exactly (23,357 / 116,550 / 269,517 /
  119,087), confirming the same source and alignment the house used.
  Stored in `dev/data/practice_answers.json`; the raw monthly responses
  are kept locally under `dev/data/` but git-ignored.
- Everything else comes from the kit itself (case files, starter, rules).

## Local scores (official loss replicated exactly)

Scorer validation: the house baseline, run through `dev/evaluate.py`,
scores **0.387097** on the practice — the house reports ~0.387.

Final configuration (LIVE_FRAC 0.05, symmetric width 1.0, 1 smoothing pass):

| case | this entry | house baseline |
|---|---|---|
| p00 Marvel's Wolverine | 0.5477 | 0.7437 |
| p01 Red Dead Redemption 2 | 0.2259 | 0.2868 |
| p02 God of War Ragnarök | 0.1505 | 0.2146 |
| p03 Marvel's Spider-Man 2 | 0.2136 | 0.3033 |
| **mean** | **0.2844** | **0.3871** |

26.5% below the baseline on the practice mean, and below it on every case.
Leave-one-out over the 37 usable comparables: 0.826 vs baseline 0.930
overall; restricted to the 26 "live at hour 1" launches (the target's own
class): **0.245 vs baseline 0.284** on the same subset.

Grader-style checks: each practice case run alone in a fresh input dir,
twice — outputs byte-identical, 23 rows, quantiles non-decreasing and in
range, ≤ 65,536 bytes, ~0.08 s per run (limit 8 s).

## Calibration: what was tried and rejected (on evidence, not taste)

- **LIVE_FRAC 0.15–0.30** (stricter "live" filter): practice worsened to
  0.31–0.37 — Wolverine (hour-1 share 0.11) is exactly the kind of launch
  the loose filter keeps in the prior's support.
- **Asymmetric upper-tail widening** (spread ×1.2–1.6 above the median):
  helped LOO over *all* launches (driven by the explosive global-unlock
  targets) but **hurt** the live-class LOO subset monotonically
  (0.245 → 0.269) and was a wash on the practice. Rejected.
- **Shifting the centre** to the 0.55–0.65 empirical quantile: practice
  improved to 0.271 but the 26-case live LOO worsened monotonically
  (0.245 → 0.253). The four practice curves happened to run hot; the
  larger sample says the true median is the right centre. Rejected.
- **Conditioning on pre-release heat** (max viewers in the 24 h before
  day start ÷ p1): correlation with the day's peak ratio across
  comparables is weak (r ≈ 0.27) and driven by outliers. Rejected.
- Smoothing 0 vs 1 vs 2 passes: within ±0.001 everywhere; kept 1.

## Remaining risks

- **The bar is not just the baseline.** A prize needs a final loss below
  the *better* of the house baseline and the house's one-shot AI model
  forecast (superbot, made 2026-11-18T23:00Z). The model forecast's loss
  is unknowable in advance; the margin under the baseline (26% on
  practice) is the cushion.
- **One-case final.** The final is a single day of a single game; a
  Wolverine-like outcome (hour 1 a lull, day peak 9× hour 1) would score
  ~0.5 for this method no matter the calibration — the prior's 95%
  quantile covers part of that tail, by design, at a small cost on
  ordinary days.
- **Measure difference.** Practice prints are SullyGnome hourly averages;
  final prints are means of 60 minute reads. Same quantity in spirit,
  slightly different noise; nothing in the method depends on the
  difference.
- Practice is four cases; the constants chosen are the ones both the
  practice and the 26-case live-class LOO agree on, deliberately not the
  practice-only optimum.
