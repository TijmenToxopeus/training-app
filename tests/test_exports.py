from pathlib import Path
from datetime import date, timedelta

from training_app.services.calibration.running import calibrate_from_race
from training_app.services.planning.running_plan_generator import generate_half_marathon_plan_7w_3d
from training_app.adapters.export.json_export import export_plan_to_json
from training_app.adapters.export.ics_export import export_plan_to_ics


def test_exports(tmp_path: Path):
    profile = calibrate_from_race(5.0, 20 * 60)
    start = date(2026, 1, 5)
    race = start + timedelta(weeks=7, days=-1)

    plan = generate_half_marathon_plan_7w_3d(profile, start, race)

    json_path = tmp_path / "plan.json"
    ics_path = tmp_path / "plan.ics"

    export_plan_to_json(plan, json_path)
    export_plan_to_ics(plan, ics_path)

    assert json_path.exists()
    assert ics_path.exists()
