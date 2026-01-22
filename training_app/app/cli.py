from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from training_app.services.calibration.running import calibrate_from_race
from training_app.services.planning.running_plan_generator import generate_half_marathon_plan_7w_3d
from training_app.services.planning.utils import align_to_next_monday
from training_app.adapters.export.json_export import export_plan_to_json
from training_app.adapters.export.ics_export import export_plan_to_ics
from training_app.services.rendering.workout_renderer import render_workout
from training_app.adapters.storage.profile_store import load_profile, save_profile


PROFILE_PATH_DEFAULT = Path("profiles/default.json")


# -----------------------------
# Parsing helpers
# -----------------------------
def _parse_date(s: str) -> date:
    return date.fromisoformat(s)


def _parse_time_to_seconds(s: str) -> int:
    parts = s.strip().split(":")
    if len(parts) == 2:
        mm, ss = parts
        hh = "0"
    elif len(parts) == 3:
        hh, mm, ss = parts
    else:
        raise argparse.ArgumentTypeError("Time must be MM:SS or HH:MM:SS")

    try:
        h = int(hh)
        m = int(mm)
        sec = int(ss)
    except ValueError as e:
        raise argparse.ArgumentTypeError("Time must contain only integers") from e

    if h < 0 or m < 0 or sec < 0 or sec >= 60:
        raise argparse.ArgumentTypeError("Invalid time format/range")

    if len(parts) == 3 and m >= 60:
        raise argparse.ArgumentTypeError("For HH:MM:SS, MM must be < 60")

    return h * 3600 + m * 60 + sec


def _format_seconds_hms(total_seconds: int) -> str:
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _monday_of_week(d: date) -> date:
    return d - timedelta(days=d.weekday())


# -----------------------------
# Interactive prompt helpers
# -----------------------------
def _prompt_str(prompt: str, default: Optional[str] = None) -> str:
    if default is not None and default != "":
        s = input(f"{prompt} [{default}]: ").strip()
        return s if s else default
    s = input(f"{prompt}: ").strip()
    return s


def _prompt_float(prompt: str, default: Optional[float] = None, min_value: float | None = None) -> float:
    while True:
        raw = _prompt_str(prompt, str(default) if default is not None else None)
        try:
            val = float(raw)
        except ValueError:
            print("Please enter a number.")
            continue
        if min_value is not None and val < min_value:
            print(f"Value must be >= {min_value}.")
            continue
        return val


def _prompt_time_seconds(prompt: str, default_seconds: Optional[int] = None) -> int:
    default_str = _format_seconds_hms(default_seconds) if default_seconds is not None else None
    while True:
        raw = _prompt_str(prompt, default_str)
        try:
            return _parse_time_to_seconds(raw)
        except Exception:
            print('Enter time as "MM:SS" or "HH:MM:SS", e.g. 20:00 or 1:25:30.')


def _prompt_date(prompt: str, default: Optional[date] = None) -> date:
    default_str = default.isoformat() if default is not None else None
    while True:
        raw = _prompt_str(prompt, default_str)
        try:
            return _parse_date(raw)
        except Exception:
            print('Enter date as "YYYY-MM-DD", e.g. 2026-03-15.')


def _prompt_yes_no(prompt: str, default_yes: bool = True) -> bool:
    default = "y" if default_yes else "n"
    while True:
        raw = _prompt_str(prompt + " (y/n)", default).lower()
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print("Please enter y or n.")


# -----------------------------
# Argparse
# -----------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="training-app",
        description="Generate a 7-week half marathon plan (3 days/week) with JSON/ICS export.",
    )

    p.add_argument("--interactive", action="store_true", help="Run an interactive setup wizard.")

    # Baseline
    p.add_argument("--baseline-distance", type=float, default=None, help="Baseline distance (km).")
    p.add_argument("--baseline-time", type=_parse_time_to_seconds, default=None, help='Baseline time "MM:SS" or "HH:MM:SS".')

    # Personalization
    p.add_argument("--weekly-km", type=float, default=None, help="Your current average weekly km (recommended).")
    p.add_argument("--long-run-km", type=float, default=None, help="Your current longest run km (recommended).")

    # Plan dates
    p.add_argument("--race-date", type=_parse_date, default=None, help="Race date YYYY-MM-DD.")
    p.add_argument("--start-date", type=_parse_date, default=None, help="Plan start date YYYY-MM-DD.")

    # Export
    p.add_argument("--export-dir", type=str, default=None, help="Directory to write exports.")
    p.add_argument("--no-export", action="store_true", help="Do not write JSON/ICS export files.")

    # Profile path (advanced)
    p.add_argument("--profile", type=str, default=str(PROFILE_PATH_DEFAULT), help="Path to profile JSON.")
    return p


def main():
    args = build_parser().parse_args()

    profile_path = Path(args.profile)
    stored: Dict[str, Any] = load_profile(profile_path)

    # ---------
    # Defaults from stored profile (if present)
    # ---------
    default_baseline_distance = stored.get("baseline_distance_km", 5.0)
    default_baseline_time = stored.get("baseline_time_sec", _parse_time_to_seconds("20:00"))
    default_weekly_km = stored.get("weekly_km", None)
    default_long_run_km = stored.get("long_run_km", None)
    default_race_date = date.fromisoformat(stored["race_date"]) if "race_date" in stored else None
    default_export_dir = stored.get("export_dir", "exports")

    # ---------
    # Interactive wizard (optional)
    # ---------
    if args.interactive:
        print("\n=== Training App Setup (Interactive) ===\n")
        baseline_distance = _prompt_float("Baseline distance (km)", default_baseline_distance, min_value=0.1)
        baseline_time = _prompt_time_seconds("Baseline time (MM:SS or HH:MM:SS)", int(default_baseline_time))

        weekly_km = _prompt_float("Current average weekly km", default_weekly_km, min_value=0.0)
        long_run_km = _prompt_float("Current longest run km", default_long_run_km, min_value=0.0)

        race_date = _prompt_date("Race date (YYYY-MM-DD)", default_race_date)
        export_dir = _prompt_str("Export directory", default_export_dir)
        do_export = _prompt_yes_no("Write JSON/ICS exports?", default_yes=not args.no_export)
        no_export = not do_export

        # start-date: we derive from race date to ensure race date is in final week
        race_week_monday = _monday_of_week(race_date)
        start_date = race_week_monday - timedelta(weeks=6)
        start_date = align_to_next_monday(start_date)

    else:
        # Non-interactive: merge CLI args over stored defaults over hard defaults
        baseline_distance = args.baseline_distance if args.baseline_distance is not None else default_baseline_distance
        baseline_time = args.baseline_time if args.baseline_time is not None else default_baseline_time

        weekly_km = args.weekly_km if args.weekly_km is not None else default_weekly_km
        long_run_km = args.long_run_km if args.long_run_km is not None else default_long_run_km

        export_dir = args.export_dir if args.export_dir is not None else default_export_dir
        no_export = args.no_export

        # Dates logic:
        if args.race_date is None and args.start_date is None:
            # If stored race_date exists, use it; else default to next Monday + 7-week Sunday race
            if default_race_date is not None:
                race_date = default_race_date
                race_week_monday = _monday_of_week(race_date)
                start_date = race_week_monday - timedelta(weeks=6)
                start_date = align_to_next_monday(start_date)
            else:
                start_date = align_to_next_monday(date.today())
                race_date = start_date + timedelta(weeks=7, days=-1)
        elif args.race_date is not None and args.start_date is None:
            race_date = args.race_date
            race_week_monday = _monday_of_week(race_date)
            start_date = race_week_monday - timedelta(weeks=6)
            start_date = align_to_next_monday(start_date)
        elif args.race_date is None and args.start_date is not None:
            start_date = align_to_next_monday(args.start_date)
            race_date = start_date + timedelta(weeks=7, days=-1)
        else:
            start_date = align_to_next_monday(args.start_date)
            race_date = args.race_date

    # Basic sanity checks
    if baseline_distance <= 0:
        raise SystemExit("baseline-distance must be > 0")
    if baseline_time <= 0:
        raise SystemExit("baseline-time must be > 0 seconds")

    if weekly_km is not None and weekly_km < 0:
        raise SystemExit("weekly-km must be >= 0")
    if long_run_km is not None and long_run_km < 0:
        raise SystemExit("long-run-km must be >= 0")

    # ---------
    # Calibration
    # ---------
    user_running_profile = calibrate_from_race(
        race_distance_km=float(baseline_distance),
        race_time_sec=float(baseline_time),
    )

    # ---------
    # Plan generation (personalized)
    # ---------
    plan = generate_half_marathon_plan_7w_3d(
        profile=user_running_profile,
        start_date=start_date,
        goal_race_date=race_date,
        start_weekly_km=weekly_km if weekly_km and weekly_km > 0 else None,
        current_long_run_km=long_run_km if long_run_km and long_run_km > 0 else None,
    )

    # ---------
    # Print output
    # ---------
    print("\n7-week Half Marathon plan (3 days/week: intervals + tempo + long + race week)")
    print("--------------------------------------------------------------------------")
    print(f"Baseline: {baseline_distance:g} km in {_format_seconds_hms(int(baseline_time))}")
    if weekly_km is not None:
        print(f"Weekly km: {weekly_km:g}")
    if long_run_km is not None:
        print(f"Longest run: {long_run_km:g} km")
    print(f"Plan:     {plan.start_date} to {plan.end_date}")
    print(f"Race:     {plan.goal_race_date}\n")

    # Group by week (nice readability)
    week0 = plan.start_date
    for i in range(7):
        ws = week0 + timedelta(days=7 * i)
        we = ws + timedelta(days=6)
        print(f"Week {i+1}: {ws} → {we}")
        for w in [x for x in plan.workouts if ws <= x.date <= we]:
            summary, desc = render_workout(w)
            print(f"  {w.date} | {summary}")
            print(f"    {desc.replace(chr(10), chr(10) + '    ')}")
        print()

    # ---------
    # Export
    # ---------
    if not no_export:
        export_dir_path = Path(export_dir)
        export_plan_to_json(plan, export_dir_path / "plan.json")
        export_plan_to_ics(plan, export_dir_path / "plan.ics")
        print("Exported:")
        print(f" - {export_dir_path / 'plan.json'}")
        print(f" - {export_dir_path / 'plan.ics'}\n")

    # ---------
    # Persist merged defaults for next time
    # ---------
    new_profile: Dict[str, Any] = {
        "baseline_distance_km": float(baseline_distance),
        "baseline_time_sec": int(baseline_time),
        "weekly_km": float(weekly_km) if weekly_km is not None else None,
        "long_run_km": float(long_run_km) if long_run_km is not None else None,
        "race_date": race_date.isoformat(),
        "export_dir": str(export_dir),
    }
    save_profile(new_profile, profile_path)


if __name__ == "__main__":
    main()
