"""
Step 2: flatten data/raw_pull.json into one row per day.

Run:
    python src/clean.py

Joins cycle + recovery + sleep on cycle_id (one physiological day each),
and folds workouts in as same-day aggregates (total workout strain,
calories, minutes in each heart-rate zone, sports done that day).

Output: data/daily.csv - one row per day, ready for correlation/lag analysis.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_PATH = PROJECT_ROOT / "data" / "raw_pull.json"
OUT_PATH = PROJECT_ROOT / "data" / "daily.csv"

MILLI_PER_HOUR = 3_600_000
KJ_PER_KCAL = 4.184
EVENING_HOUR_CUTOFF = 18  # 6pm local time


def local_datetime(iso_ts: str, tz_offset: str) -> datetime:
    """Convert a UTC ISO timestamp + WHOOP's '+/-HH:MM' (or 'Z') offset to a local datetime."""
    dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    if tz_offset == "Z" or not tz_offset:
        return dt
    sign = 1 if tz_offset[0] == "+" else -1
    hours, minutes = (int(x) for x in tz_offset[1:].split(":"))
    return dt + sign * timedelta(hours=hours, minutes=minutes)


def local_date(iso_ts: str, tz_offset: str) -> str:
    return local_datetime(iso_ts, tz_offset).date().isoformat()


def build_cycle_table(cycles: list) -> pd.DataFrame:
    rows = []
    for c in cycles:
        score = c.get("score") or {}
        rows.append(
            {
                "cycle_id": c["id"],
                "date": local_date(c["start"], c["timezone_offset"]),
                "day_strain": score.get("strain"),
                "day_kilojoule": score.get("kilojoule"),
                "day_avg_hr": score.get("average_heart_rate"),
                "day_max_hr": score.get("max_heart_rate"),
            }
        )
    return pd.DataFrame(rows)


def build_recovery_table(recoveries: list) -> pd.DataFrame:
    rows = []
    for r in recoveries:
        score = r.get("score") or {}
        rows.append(
            {
                "cycle_id": r["cycle_id"],
                "recovery_score": score.get("recovery_score"),
                "resting_heart_rate": score.get("resting_heart_rate"),
                "hrv_rmssd_milli": score.get("hrv_rmssd_milli"),
                "spo2_percentage": score.get("spo2_percentage"),
                "skin_temp_celsius": score.get("skin_temp_celsius"),
            }
        )
    return pd.DataFrame(rows)


def build_sleep_table(sleeps: list) -> pd.DataFrame:
    rows = []
    for s in sleeps:
        score = s.get("score") or {}
        stages = score.get("stage_summary") or {}
        needed = score.get("sleep_needed") or {}
        rows.append(
            {
                "cycle_id": s.get("cycle_id"),
                "is_nap": s.get("nap"),
                "sleep_performance_pct": score.get("sleep_performance_percentage"),
                "sleep_consistency_pct": score.get("sleep_consistency_percentage"),
                "sleep_efficiency_pct": score.get("sleep_efficiency_percentage"),
                "respiratory_rate": score.get("respiratory_rate"),
                "hours_in_bed": (stages.get("total_in_bed_time_milli") or 0) / MILLI_PER_HOUR,
                "hours_awake": (stages.get("total_awake_time_milli") or 0) / MILLI_PER_HOUR,
                "hours_light_sleep": (stages.get("total_light_sleep_time_milli") or 0) / MILLI_PER_HOUR,
                "hours_deep_sleep": (stages.get("total_slow_wave_sleep_time_milli") or 0) / MILLI_PER_HOUR,
                "hours_rem_sleep": (stages.get("total_rem_sleep_time_milli") or 0) / MILLI_PER_HOUR,
                "disturbance_count": stages.get("disturbance_count"),
                "hours_sleep_debt": (needed.get("need_from_sleep_debt_milli") or 0) / MILLI_PER_HOUR,
                "hours_needed_baseline": (needed.get("baseline_milli") or 0) / MILLI_PER_HOUR,
            }
        )
    df = pd.DataFrame(rows)
    # drop naps, keep only the main overnight sleep per cycle
    return df[df["is_nap"] == False].drop(columns=["is_nap"])  # noqa: E712


def build_workout_daily_table(workouts: list) -> pd.DataFrame:
    rows = []
    for w in workouts:
        score = w.get("score") or {}
        zones = score.get("zone_durations") or {}
        start_local = local_datetime(w["start"], w["timezone_offset"])
        zone4_5 = ((zones.get("zone_four_milli") or 0) + (zones.get("zone_five_milli") or 0)) / 60000
        is_evening = start_local.hour >= EVENING_HOUR_CUTOFF
        rows.append(
            {
                "date": start_local.date().isoformat(),
                "sport_name": w.get("sport_name"),
                "distance_meter": score.get("distance_meter") or 0,
                "zone1_3_minutes": (
                    (zones.get("zone_one_milli") or 0)
                    + (zones.get("zone_two_milli") or 0)
                    + (zones.get("zone_three_milli") or 0)
                )
                / 60000,
                "zone4_5_minutes": zone4_5,
                "evening_zone4_5_minutes": zone4_5 if is_evening else 0.0,
                "had_evening_hard_workout": is_evening and zone4_5 > 0,
            }
        )
    if not rows:
        return pd.DataFrame(
            columns=[
                "date", "num_workouts", "sports", "distance_meter_total",
                "zone1_3_minutes", "zone4_5_minutes",
                "evening_zone4_5_minutes", "had_evening_hard_workout",
            ]
        )
    df = pd.DataFrame(rows)
    agg = df.groupby("date").agg(
        num_workouts=("sport_name", "count"),
        sports=("sport_name", lambda s: ",".join(sorted(set(s)))),
        distance_meter_total=("distance_meter", "sum"),
        zone1_3_minutes=("zone1_3_minutes", "sum"),
        zone4_5_minutes=("zone4_5_minutes", "sum"),
        evening_zone4_5_minutes=("evening_zone4_5_minutes", "sum"),
        had_evening_hard_workout=("had_evening_hard_workout", "any"),
    )
    return agg.reset_index()


def main():
    raw = json.loads(RAW_PATH.read_text())

    cycles = build_cycle_table(raw["cycles"]["records"])
    recovery = build_recovery_table(raw["recovery"]["records"])
    sleep = build_sleep_table(raw["sleep"]["records"])
    workouts_daily = build_workout_daily_table(raw["workouts"]["records"])

    daily = cycles.merge(recovery, on="cycle_id", how="left")
    daily = daily.merge(sleep, on="cycle_id", how="left")
    daily = daily.merge(workouts_daily, on="date", how="left")

    daily["total_kcal_burned"] = daily["day_kilojoule"] / KJ_PER_KCAL
    daily = daily.drop(columns=["day_kilojoule"])

    daily["num_workouts"] = daily["num_workouts"].fillna(0).astype(int)
    for col in ["distance_meter_total", "zone1_3_minutes", "zone4_5_minutes", "evening_zone4_5_minutes"]:
        daily[col] = daily[col].fillna(0.0)
    daily["had_evening_hard_workout"] = daily["had_evening_hard_workout"].fillna(False)

    # Drop days with no recovery/sleep at all - either a boundary artifact from the
    # pull's start-date cutoff, or a night WHOOP wasn't worn. Not usable either way.
    before = len(daily)
    daily = daily.dropna(subset=["recovery_score", "sleep_performance_pct"], how="all")
    dropped = before - len(daily)
    if dropped:
        print(f"Dropped {dropped} day(s) with no recovery/sleep data (boundary or unworn nights).")

    daily = daily.sort_values("date").reset_index(drop=True)

    OUT_PATH.parent.mkdir(exist_ok=True)
    daily.to_csv(OUT_PATH, index=False)

    print(f"{len(daily)} days written to {OUT_PATH}")
    print(daily.head())


if __name__ == "__main__":
    main()
