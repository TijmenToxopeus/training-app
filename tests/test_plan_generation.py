from datetime import date, timedelta

from training_app.services.calibration.running import calibrate_from_race
from training_app.services.planning.running_plan_generator import (
    generate_half_marathon_plan_7w_3d,
)


def test_plan_has_7_weeks_and_race():
    profile = calibrate_from_race(5.0, 20 * 60)
    start = date(2026, 1, 5)  # Monday
    race = start + timedelta(weeks=7, days=-1)

    plan = generate_half_marathon_plan_7w_3d(profile, start, race)

    assert plan.goal_race_date == race
    assert (plan.end_date - plan.start_date).days == 7 * 7 - 1

    race_days = [w for w in plan.workouts if w.template.type.value == "race"]
    assert len(race_days) == 1
    assert race_days[0].date == race


def test_plan_accepts_personalized_weekly_km():
    profile = calibrate_from_race(5.0, 20 * 60)
    start = date(2026, 1, 5)  # Monday
    race = start + timedelta(weeks=7, days=-1)

    plan = generate_half_marathon_plan_7w_3d(
        profile=profile,
        start_date=start,
        goal_race_date=race,
        start_weekly_km=40.0,
        current_long_run_km=12.0,
    )

    assert len(plan.workouts) > 0