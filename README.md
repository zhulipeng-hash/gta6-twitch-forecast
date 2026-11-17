# GTA VI launch-day Twitch viewers forecast

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/zhulipeng-hash/gta6-twitch-forecast/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/zhulipeng-hash/gta6-twitch-forecast/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

Entry for make.fun's **gta6-twitch-ccu-forecast-01** ("Forecast GTA VI's
launch-day Twitch viewers hour by hour"). Repository: <https://github.com/zhulipeng-hash/gta6-twitch-forecast>.

`main.py` (Python 3, standard library only) reads every `*.in` case file in
`$MAKEFUN_INPUT_DIR` (else `/input`) and writes `<id>.out` to
`$MAKEFUN_OUTPUT_DIR` (else `/output`): for each of hours 2–24 of the release
day, five quantiles (5/25/50/75/95%) of the Twitch category's viewer count.

## Method in one paragraph

Everything is anchored on hour 1's printed count `p1`. The case file itself
carries ~40 past big launches' hourly curves; the program normalises each by
its own hour-1 count, keeps the launches that were already live at 00:00 UTC
(hour 1 at least 5% of their day peak — the rolling midnight-local console
launches, GTA VI's own pattern), and takes the per-hour distribution of the
log ratio `ln(viewers_h / viewers_1)` across them as the prior. The forecast
is `p1` times the prior's empirical quantiles, lightly smoothed across
neighbouring hours. No network, no model calls, deterministic. See
`DEVLOG.md` for calibration and local scores, and the docstring in
`main.py`.

## Run it

```sh
mkdir -p out
MAKEFUN_INPUT_DIR=<dir with .in files> MAKEFUN_OUTPUT_DIR=out python3 main.py
```

## Local evaluation

`dev/evaluate.py` replicates the official log-scale pinball loss and scores
the entry on the four practice cases (answers in `dev/data/`, from the same
SullyGnome series the cases were built from) and by leave-one-out over the
comparables:

```sh
python3 dev/evaluate.py practice   # entry 0.284 vs house baseline 0.387
python3 dev/evaluate.py loo
```

MIT licensed (LICENSE).
