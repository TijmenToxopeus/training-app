from pathlib import Path

from training_app.adapters.storage.profile_store import load_profile, save_profile


def test_profile_store_roundtrip(tmp_path: Path):
    p = tmp_path / "profile.json"
    data = {
        "baseline_distance_km": 5.0,
        "baseline_time_sec": 1200,
        "weekly_km": 35.0,
        "long_run_km": 14.0,
        "race_date": "2026-03-15",
        "export_dir": "exports",
    }
    save_profile(data, p)

    loaded = load_profile(p)
    assert loaded["baseline_distance_km"] == 5.0
    assert loaded["baseline_time_sec"] == 1200
    assert loaded["weekly_km"] == 35.0
    assert loaded["long_run_km"] == 14.0
    assert loaded["race_date"] == "2026-03-15"
