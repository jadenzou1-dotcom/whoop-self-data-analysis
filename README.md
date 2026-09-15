# WHOOP Sleep/HRV/Recovery Analysis

Personal-data project analyzing whether sleep patterns predict next-day/next-week
recovery metrics (HRV, recovery score) using real WHOOP data — not just charts,
but actual lag-correlation / regression analysis.

## Goal

Test claims like "sleep debt this week → lower HRV next week" statistically,
rather than eyeballing two lines on a graph. A credible null result ("no
meaningful lag effect, but strong same-day correlation") is a fine outcome.

## Plan

1. **Data pull** — WHOOP API (OAuth) → sleep, HRV, recovery, strain history →
   local CSV/SQLite (`src/pull_data.py` → `data/`).
2. **Cleaning** — handle missing nights, align to daily/weekly buckets
   (`src/clean.py`).
3. **Feature engineering** — weekly aggregates (avg sleep hours, sleep debt,
   avg HRV, avg strain) + lagged versions (this week's sleep vs next week's
   HRV) (`src/features.py`).
4. **Analysis** — correlation matrix, lag correlation, simple linear
   regression (sleep_hours_t → HRV_t+1) with significance checks
   (`notebooks/analysis.ipynb` or `src/analysis.py`).
5. **Visualization** — a handful of clear plots: scatter of lagged sleep vs
   HRV, rolling trend lines (`output/`).
6. **Write-up** — this README gets a "Findings" section with the actual
   result, stated honestly.

## Structure

```
proj/
  data/        raw + cleaned datasets (gitignored)
  notebooks/   exploratory analysis
  src/         data pull, cleaning, feature engineering, analysis scripts
  output/      generated plots, figures
```

## Status

- [x] Check WHOOP developer platform API access requirements
- [x] OAuth setup + data pull (`src/whoop_client.py`, `src/pull_data.py` — 9 months, auto-paginated)
- [x] Cleaning + feature engineering (`src/clean.py` → `data/daily.csv`, one row/day)
- [ ] Lag correlation / regression analysis
- [ ] Plots
- [ ] Findings write-up

## Future analysis idea: does evening-hard-exercise timing raise resting HR, controlling for daytime load?

Don't just regress `sleep_proximity_zone45_load` (evening zone4/5 minutes weighted by
closeness to that night's sleep onset — see `src/clean.py`) against
`resting_heart_rate` directly. Evening hard-effort days are probably correlated
with generally hard-effort days (more zone1-3 earlier too), so a naive fit
would partly just be re-detecting "high-strain days raise RHR," not "timing
specifically matters."

Fix: hold total daytime load roughly constant before comparing evening timing.
Two ways to do this when the time comes:

1. **Matching** — bucket days by daytime load (`zone1_3_minutes` and/or
   `day_strain` minus the evening portion), then only compare evening-heavy
   vs evening-light days *within* the same daytime-load bucket.
2. **Multiple regression with daytime load as a covariate** — regress
   `resting_heart_rate ~ sleep_proximity_zone45_load + daytime_zone1_3_minutes + day_strain`
   (or similar) so the model estimates the marginal effect of evening timing
   *after* accounting for how hard the day already was. This is the more
   standard approach and scales better as more control variables come up
   (alcohol, illness, stress are unmeasured but at least daytime load isn't).

Worth revisiting once there's a notebook and enough evening-hard-workout days
accumulated (~23 out of 270 days as of 2026-09-15) to have any power for this.
