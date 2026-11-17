"""Forecast GTA VI's launch-day Twitch viewers, hour by hour (make.fun
gta6-twitch-ccu-forecast-01).

Method
------
The only hard fact at forecast time is hour 1's viewer count p1. Everything
else comes from the case's own `comparables`: past big launches whose hourly
Twitch curves (SullyGnome averages) ship inside every case file. For each
comparable we form the release-day curve normalised by its own hour-1 count,
    r_h = viewers(hour h) / viewers(hour 1),        h = 2..24,
and take the distribution of ln r_h across comparable launches as the prior
for the target's hour h. The forecast is p1 times the prior's quantiles.

Two guards keep the prior honest:

* Launches that were not yet live at 00:00 UTC on their release day (a single
  global unlock later in the day: their hour-1 count is a sliver of their day
  peak and their normalised curve explodes mid-day) do not resemble a rolling
  midnight-local console launch, so a comparable only enters the prior when
  its hour-1 count is at least LIVE_FRAC of its own release-day peak. If too
  few launches pass, the bar is lowered until enough do.
* The comparable that is the target category's own pre-release history is
  marked "Not a launch" in its unlock note and is always left out.

The per-hour log-quantile curves are lightly smoothed across neighbouring
hours (empirical quantiles from ~40 launches are noisy), and the spread
around the median is scaled by WIDTH_SCALE. Both constants, and LIVE_FRAC,
were calibrated on the four practice cases and by leave-one-out over the
comparables themselves; see DEVLOG.md.

The program is deterministic, standard library only, and reads every
*.in file in $MAKEFUN_INPUT_DIR (else /input), writing <id>.out to
$MAKEFUN_OUTPUT_DIR (else /output).
"""

import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]

# --- calibrated constants (see DEVLOG.md) ---
LIVE_FRAC = 0.05      # hour-1 >= this share of the day peak: "already live"
MIN_COMPS = 6         # relax LIVE_FRAC until at least this many launches pass
MIN_DAY_HOURS = 18    # a comparable needs this many of its 24 release-day hours
WIDTH_SCALE = 1.0     # multiplies the log-spread around the median
SMOOTH_PASSES = 1     # [1,2,1]/4 smoothing passes over the log-quantile curves


def parse_ts(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def hour_key(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def release_day_curve(comp):
    """The comparable's 24 release-day hourly viewer counts (None if absent)."""
    by_hour = {}
    for point in comp.get("hourly") or []:
        value = point.get("viewers")
        if value is not None:
            by_hour[point["from"]] = float(value)
    start = parse_ts(comp["day_start"])
    return [by_hour.get(hour_key(start + timedelta(hours=k))) for k in range(24)]


def is_launch(comp):
    return "not a launch" not in (comp.get("unlock") or "").lower()


def select_curves(comparables):
    """Normalised release-day curves of the launches that were live at hour 1."""
    pool = []
    for comp in comparables:
        if not is_launch(comp):
            continue
        day = release_day_curve(comp)
        present = [v for v in day if v is not None]
        if day[0] is None or day[0] <= 0 or len(present) < MIN_DAY_HOURS:
            continue
        pool.append((day[0] / max(present), [None if v is None else v / day[0] for v in day]))
    frac = LIVE_FRAC
    while True:
        chosen = [curve for share, curve in pool if share >= frac]
        if len(chosen) >= MIN_COMPS or frac <= 0.01:
            return chosen
        frac *= 0.5


def empirical_quantile(sorted_values, level):
    """The level-quantile of a sorted sample, linear interpolation (type 7)."""
    n = len(sorted_values)
    if n == 1:
        return sorted_values[0]
    pos = level * (n - 1)
    low = int(math.floor(pos))
    high = min(low + 1, n - 1)
    return sorted_values[low] + (sorted_values[high] - sorted_values[low]) * (pos - low)


def smooth(curve):
    """One [1,2,1]/4 pass over a per-hour sequence, edges shrunk to fit."""
    out = []
    for i, value in enumerate(curve):
        total, weight = 2.0 * value, 2.0
        if i > 0:
            total += curve[i - 1]
            weight += 1.0
        if i < len(curve) - 1:
            total += curve[i + 1]
            weight += 1.0
        out.append(total / weight)
    return out


def prior_log_quantiles(comparables):
    """For hours 2..24, the five log-ratio quantiles across comparable launches."""
    curves = select_curves(comparables)
    per_level = [[] for _ in LEVELS]  # per_level[j][k] = log quantile, hour k+2
    for k in range(1, 24):
        samples = sorted(math.log(curve[k]) for curve in curves if curve[k])
        if not samples:
            samples = [0.0]
        for j, level in enumerate(LEVELS):
            per_level[j].append(empirical_quantile(samples, level))
    for _ in range(SMOOTH_PASSES):
        per_level = [smooth(curve) for curve in per_level]
    rows = []
    for i in range(23):
        logs = [per_level[j][i] for j in range(len(LEVELS))]
        median = logs[2]
        rows.append([median + (value - median) * WIDTH_SCALE for value in logs])
    return rows


def round2(x):
    """Round half up to 2 decimals; whole numbers come back as ints."""
    value = math.floor(x * 100 + 0.5) / 100
    return int(value) if float(value).is_integer() else value


def forecast_case(case, name):
    if case["levels"] != LEVELS:
        raise ValueError(f"{name} asks for levels {case['levels']}, not {LEVELS}")
    first = next((row for row in case["known"] if row["hour"] == 1), None)
    if first is None:
        raise ValueError(f"{name} has no hour-1 print")
    p1 = max(1.0, float(first["viewers"]))
    log_rows = prior_log_quantiles(case.get("comparables") or [])
    hours = []
    for row in case["forecast"]:
        logs = log_rows[row["hour"] - 2]
        quantiles = []
        for value in logs:
            q = p1 * math.exp(value)
            q = min(max(q, 0.5), 1_000_000_000.0)
            if quantiles and q < quantiles[-1]:
                q = quantiles[-1]
            quantiles.append(round2(q))
        hours.append({"hour": row["hour"], "q": quantiles})
    return {"hours": hours}


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        forecast = forecast_case(case, path.name)
        text = json.dumps(forecast, separators=(",", ":")) + "\n"
        (OUTPUT_DIR / f"{path.stem}.out").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
