from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from training_app.domain.enums import Sport, WorkoutType
from training_app.domain.plan import TrainingPlan
from training_app.domain.profile import RunningProfile
from training_app.domain.workout import WorkoutTemplate, ScheduledWorkout


def _sec_to_pace_str(sec_per_km: float) -> str:
    m = int(sec_per_km // 60)
    s = int(round(sec_per_km % 60))
    return f"{m}:{s:02d}/km"


def _easy_range_str(profile: RunningProfile) -> str:
    p = profile.paces
    return f"{_sec_to_pace_str(p.easy_min)}–{_sec_to_pace_str(p.easy_max)}"


def _round_km(x: float) -> float:
    return round(x * 2) / 2.0  # nearest 0.5 km


@dataclass(frozen=True)
class PlanParams:
    weeks: int = 7
    days_per_week: int = 3

    weekly_growth: float = 0.08
    down_week_index: int = 3           # week 4
    down_week_factor: float = 0.80     # -20%

    # Normal (non-race-week) volume split
    frac_intervals: float = 0.25
    frac_tempo: float = 0.25
    frac_long: float = 0.50

    long_cap_km: float = 20.0

    # Race week session sizes (km)
    race_week_easy_km: float = 5.0
    race_week_tempo_km: float = 6.0
    hm_distance_km: float = 21.1


def _interval_structure_for_week(week_idx: int, profile: RunningProfile) -> dict:
    """
    Progressive interval sessions across build weeks 0..5.
    Very simple and adjustable.
    """
    p = profile.paces

    # (reps, work_min, rest_min)
    # Build a bit, keep week 4 (idx 3) easier by design in weekly volume already.
    table = {
        0: (5, 2, 2),
        1: (6, 2, 2),
        2: (6, 2, 2),
        3: (5, 2, 2),  # down-ish feel
        4: (5, 3, 2),
        5: (6, 3, 2),
    }
    reps, work_min, rest_min = table.get(week_idx, (6, 2, 2))

    return {
        "warmup_min": 12,
        "reps": reps,
        "work_min": work_min,
        "rest_min": rest_min,
        "cooldown_min": 10,
        "target": "interval_pace",
        "target_pace": _sec_to_pace_str(p.interval),
        "easy_pace_range": _easy_range_str(profile),
    }


def _tempo_structure_for_week(week_idx: int, profile: RunningProfile) -> dict:
    """
    Progressive tempo sessions across build weeks 0..5.
    """
    p = profile.paces

    tempo_minutes = {
        0: 15,
        1: 18,
        2: 20,
        3: 15,  # down-ish
        4: 22,
        5: 25,
    }.get(week_idx, 20)

    return {
        "warmup_min": 10,
        "tempo_min": tempo_minutes,
        "cooldown_min": 10,
        "target": "threshold_pace",
        "target_pace": _sec_to_pace_str(p.threshold),
        "easy_pace_range": _easy_range_str(profile),
    }


def generate_half_marathon_plan_7w_3d(
    profile: RunningProfile,
    start_date: date,
    goal_race_date: date,
    params: PlanParams | None = None,
) -> TrainingPlan:
    """
    7-week Half Marathon plan, 3 days/week:
      Tue: intervals
      Thu: tempo
      Sun: long

    Final week is a race week:
      race_date-5: easy + strides
      race_date-3: short tempo
      race_date: HM race
    """

    if params is None:
        params = PlanParams()

    if params.days_per_week != 3:
        raise ValueError("This generator is fixed to 3 days/week.")
    if params.weeks != 7:
        raise ValueError("This v0 generator expects 7 weeks.")
    if goal_race_date < start_date:
        raise ValueError("goal_race_date must be on/after start_date.")

    p = profile.paces

    # --- Estimate a conservative starting weekly volume (km) ---
    base = profile.baseline_race_distance_km
    start_weekly_km = max(22.0, min(34.0, base * 4.5))  # 5k -> 22.5 km/wk

    # Build weekly volumes for weeks 0..5 (6 build weeks). Week 6 is race week.
    weekly_km: list[float] = []
    current = start_weekly_km
    for w in range(params.weeks):
        if w == params.weeks - 1:
            weekly_km.append(current)
            continue

        if w == params.down_week_index:
            current = current * params.down_week_factor
        elif w > 0:
            current = current * (1.0 + params.weekly_growth)

        weekly_km.append(current)

    workouts: list[ScheduledWorkout] = []

    def add_workout(d: date, wtype: WorkoutType, km: float | None, desc: str, structure: dict):
        tmpl = WorkoutTemplate(
            sport=Sport.RUN,
            type=wtype,
            description=desc,
            structure=structure,
        )
        workouts.append(
            ScheduledWorkout(
                date=d,
                template=tmpl,
                target_distance_km=_round_km(km) if km is not None else None,
            )
        )

    # -----------------------------
    # Build weeks (0..5)
    # -----------------------------
    for w in range(params.weeks - 1):
        week_start = start_date + timedelta(days=7 * w)
        d_intervals = week_start + timedelta(days=1)  # Tue
        d_tempo = week_start + timedelta(days=3)      # Thu
        d_long = week_start + timedelta(days=6)       # Sun

        wk_total = weekly_km[w]

        km_intervals = wk_total * params.frac_intervals
        km_tempo = wk_total * params.frac_tempo
        km_long = wk_total * params.frac_long

        # Cap long run and redistribute overflow to tempo
        km_long_capped = min(km_long, params.long_cap_km)
        overflow = km_long - km_long_capped
        km_long = km_long_capped
        if overflow > 0:
            km_tempo += overflow

        interval_struct = _interval_structure_for_week(w, profile)
        tempo_struct = _tempo_structure_for_week(w, profile)

        intervals_desc = (
            f"Intervals: {interval_struct['warmup_min']} min easy, "
            f"{interval_struct['reps']}×{interval_struct['work_min']} min @ {interval_struct['target_pace']}, "
            f"{interval_struct['rest_min']} min jog, cooldown {interval_struct['cooldown_min']} min. "
            f"Easy pace: {interval_struct['easy_pace_range']}."
        )
        tempo_desc = (
            f"Tempo: {tempo_struct['warmup_min']} min easy, "
            f"{tempo_struct['tempo_min']} min @ {tempo_struct['target_pace']}, "
            f"cooldown {tempo_struct['cooldown_min']} min. "
            f"Easy pace: {tempo_struct['easy_pace_range']}."
        )
        long_desc = (
            f"Long run easy. Pace: {_easy_range_str(profile)}. "
            f"Optional: last 10–15 min slightly faster if you feel great."
        )
        long_struct = {
            "mode": "easy",
            "target": "easy_pace_range",
            "easy_pace_range": _easy_range_str(profile),
            "notes": "Keep it easy; optional gentle pickup at the end.",
        }

        add_workout(d_intervals, WorkoutType.INTERVALS, km_intervals, intervals_desc, interval_struct)
        add_workout(d_tempo, WorkoutType.TEMPO, km_tempo, tempo_desc, tempo_struct)
        add_workout(d_long, WorkoutType.LONG, km_long, long_desc, long_struct)

    # -----------------------------
    # Race week (final week)
    # -----------------------------
    race_week_start = start_date + timedelta(days=7 * (params.weeks - 1))
    race_week_end = race_week_start + timedelta(days=6)

    if not (race_week_start <= goal_race_date <= race_week_end):
        raise ValueError(
            f"goal_race_date ({goal_race_date}) must fall in the final week "
            f"({race_week_start}..{race_week_end}) for this v0 generator."
        )

    d_easy = goal_race_date - timedelta(days=5)
    d_sharp = goal_race_date - timedelta(days=3)

    easy_struct = {
        "warmup_min": 0,
        "strides": {"count": 6, "duration_sec": 20, "recovery_sec": 90},
        "target": "easy_pace_range",
        "easy_pace_range": _easy_range_str(profile),
        "notes": "Relaxed run + strides with full recovery.",
    }
    easy_desc = (
        f"Easy + strides: easy pace {_easy_range_str(profile)}. "
        f"Add {easy_struct['strides']['count']}×{easy_struct['strides']['duration_sec']}s strides "
        f"with ~{easy_struct['strides']['recovery_sec']}s easy between."
    )

    sharp_struct = {
        "warmup_min": 10,
        "tempo_min": 12,
        "cooldown_min": 10,
        "target": "threshold_pace",
        "target_pace": _sec_to_pace_str(p.threshold),
        "notes": "Short, snappy; do not turn into a hard workout.",
    }
    sharp_desc = (
        f"Short tempo: {sharp_struct['warmup_min']} min easy + "
        f"{sharp_struct['tempo_min']} min @ {_sec_to_pace_str(p.threshold)} + "
        f"{sharp_struct['cooldown_min']} min cooldown."
    )

    race_struct = {
        "distance_km": params.hm_distance_km,
        "target": "race",
        "notes": "Start controlled; fuel/hydrate appropriately; try to negative split if feeling good.",
    }
    race_desc = "Half Marathon RACE (21.1 km). Start controlled; aim to negative split if feeling good."

    add_workout(d_easy, WorkoutType.EASY, params.race_week_easy_km, easy_desc, easy_struct)
    add_workout(d_sharp, WorkoutType.TEMPO, params.race_week_tempo_km, sharp_desc, sharp_struct)
    add_workout(goal_race_date, WorkoutType.RACE, params.hm_distance_km, race_desc, race_struct)

    workouts.sort(key=lambda w: w.date)

    return TrainingPlan(
        start_date=start_date,
        end_date=race_week_end,
        goal_race_date=goal_race_date,
        workouts=workouts,
    )
