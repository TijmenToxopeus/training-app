from datetime import date, timedelta

from training_app.services.calibration.running import calibrate_from_race
from training_app.services.planning.running_plan_generator import generate_half_marathon_plan_7w_3d
from training_app.services.rendering.workout_renderer import render_workout


def test_renderer_produces_summary_and_description():
    profile = calibrate_from_race(5.0, 20 * 60)
    start = date(2026, 1, 5)  # Monday
    race = start + timedelta(weeks=7, days=-1)

    plan = generate_half_marathon_plan_7w_3d(profile, start, race)

    w = plan.workouts[0]
    summary, desc = render_workout(w)

    assert isinstance(summary, str) and len(summary) > 0
    assert isinstance(desc, str) and len(desc) > 0
