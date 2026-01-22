from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

from training_app.services.calibration.running import calibrate_from_race
from training_app.services.planning.running_plan_generator import generate_half_marathon_plan_7w_3d
from training_app.services.planning.utils import align_to_next_monday
from training_app.services.rendering.workout_renderer import render_workout
from training_app.adapters.export.json_export import export_plan_to_json
from training_app.adapters.export.ics_export import export_plan_to_ics


def _parse_date(s: str) -> date:
    # Expect YYYY-MM-DD
    return date.fromisoformat(s)


def _parse_time_to_seconds(s: str) -> int:
    """
    Parse a time string "MM:SS" or "HH:MM:SS" into total seconds.
    Examples:
      "20:00" -> 1200
      "1:25:30" -> 5130
    """
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

    if h < 0 or m < 0 or sec < 0 or sec >= 60 or m >= 60 and len(parts) == 3:
        # For HH:MM:SS we enforce MM < 60. For MM:SS, MM can be any non-negative.
        raise argparse.ArgumentTypeError("Invalid time format/range")

    return h * 3600 + m * 60 + sec


def _format_seconds_hms(total_seconds: int) -> str:
    if total_seconds < 0:
        total_seconds = 0
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _monday_of_week(d: date) -> date:
    # Monday == 0 ... Sunday == 6
    return d - timedelta(days=d.weekday())


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="training-app",
        description="Generate a 7-week half marathon plan (3 days/week) and export JSON/ICS.",
    )

    # --- Baseline (calibration) ---
    p.add_argument(
        "--baseline-distance",
        type=float,
        default=5.0,
        help="Baseline race distance in km (default: 5.0).",
    )
    p.add_argument(
        "--baseline-time",
        type=_parse_time_to_seconds,
        default=_parse_time_to_seconds("20:00"),
        help='Baseline race time as "MM:SS" or "HH:MM:SS" (default: 20:00).',
    )

    # --- Plan dates ---
    p.add_argument(
        "--race-date",
        type=_parse_date,
        default=None,
        help="Race date in YYYY-MM-DD. If omitted, defaults to Sunday of final week starting next Monday.",
    )
    p.add_argument(
        "--start-date",
        type=_parse_date,
        default=None,
        help="Plan start date in YYYY-MM-DD. If omitted, derived from race-date (or next Monday if race-date omitted).",
    )

    # --- Export ---
    p.add_argument(
        "--export-dir",
        type=str,
        default="exports",
        help="Directory to write exports (default: exports).",
    )
    p.add_argument(
        "--no-export",
        action="store_true",
        help="Do not write JSON/ICS export files.",
    )

    return p


def main():
    args = build_parser().parse_args()

    # --- Calibration from baseline ---
    if args.baseline_distance <= 0:
        raise SystemExit("baseline-distance must be > 0")
    if args.baseline_time <= 0:
        raise SystemExit("baseline-time must be > 0 seconds")

    profile = calibrate_from_race(
        race_distance_km=float(args.baseline_distance),
        race_time_sec=float(args.baseline_time),
    )

    # --- Determine start_date and race_date ---
    if args.race_date is None and args.start_date is None:
        start_date = align_to_next_monday(date.today())
        race_date = start_date + timedelta(weeks=7, days=-1)  # Sunday of final week
    elif args.race_date is not None and args.start_date is None:
        race_date = args.race_date
        race_week_monday = _monday_of_week(race_date)
        start_date = race_week_monday - timedelta(weeks=6)
    elif args.race_date is None and args.start_date is not None:
        start_date = align_to_next_monday(args.start_date)
        race_date = start_date + timedelta(weeks=7, days=-1)
    else:
        start_date = align_to_next_monday(args.start_date)
        race_date = args.race_date

    plan = generate_half_marathon_plan_7w_3d(
        profile=profile,
        start_date=start_date,
        goal_race_date=race_date,
    )

    print("7-week Half Marathon plan (3 days/week: intervals + tempo + long + race week)")
    print("--------------------------------------------------------------------------")
    print(f"Baseline: {args.baseline_distance:g} km in {_format_seconds_hms(int(args.baseline_time))}")
    print(f"Plan:     {plan.start_date} to {plan.end_date}")
    print(f"Race:     {plan.goal_race_date}")
    print()

    for w in plan.workouts:
        km = f"{w.target_distance_km:.1f} km" if w.target_distance_km is not None else "-"
        print(f"{w.date} | {w.template.type.value:10s} | {km:8s} | {w.template.description}")

    if not args.no_export:
        export_dir = Path(args.export_dir)
        export_plan_to_json(plan, export_dir / "plan.json")
        export_plan_to_ics(plan, export_dir / "plan.ics")
        print("\nExported:")
        print(f" - {export_dir / 'plan.json'}")
        print(f" - {export_dir / 'plan.ics'}")


if __name__ == "__main__":
    main()
