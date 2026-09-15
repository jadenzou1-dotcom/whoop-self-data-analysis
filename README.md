# WHOOP Self-Data Analysis

Personal-data project analyzing my own WHOOP data — sleep, HRV, recovery, and
later strain/activity — to find real trends, not just charts. Actual
lag-correlation / regression analysis, not eyeballing two lines on a graph.

## Goal

Look for trends in my own data: what actions I take actually move which body
metrics, and by how much. Examples of the kind of claim this should be able
to test: "sleep debt this week → lower HRV next week," or "evening activity →
higher resting heart rate that same night." A credible null result ("no
meaningful lag effect, but strong same-day correlation") is a fine outcome
too.

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

### Notebooks

- **`01_sleep_vs_hrv_rhr.ipynb`** — initial exploratory pass: basic sleep
  variables (total sleep hours, sleep consistency, sleep efficiency, deep
  sleep hours) plus 1-5 day trailing sleep averages, each checked against
  HRV and resting heart rate as outputs.
- **`02_sleep_vs_hrv_rhr_full_pairwise.ipynb`** — more granular follow-up:
  isolated single nights (not averaged with anything) and skip-day pairwise
  combinations (e.g. the average of night 2 + night 4, skipping night 3),
  extended to a 7-day lookback, for both total sleep and deep sleep
  specifically. These are much more unique/specific inputs, so a real
  correlation is less likely — but worth checking anyway, since it'd be an
  interesting result if one turned up. Partly inspired by marathon-runner
  folklore that the night *before* a race matters less than the night before
  that one — if some particular combination of nights matters more than a
  simple cumulative average, this is where it would show up.
- **Notebook 3 onward (future)** — bring in strain, activity/workout data,
  and other WHOOP metrics beyond sleep.

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
