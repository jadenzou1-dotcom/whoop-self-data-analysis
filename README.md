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

- [ ] Check WHOOP developer platform API access requirements
- [ ] OAuth setup + data pull
- [ ] Cleaning + feature engineering
- [ ] Lag correlation / regression analysis
- [ ] Plots
- [ ] Findings write-up

## Findings

_(TBD)_
