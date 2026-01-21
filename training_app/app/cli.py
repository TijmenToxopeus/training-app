from training_app.services.calibration.running import calibrate_from_race


def format_pace(sec_per_km: float) -> str:
    minutes = int(sec_per_km // 60)
    seconds = int(sec_per_km % 60)
    return f"{minutes}:{seconds:02d} / km"


def main():
    # --- Test baseline ---
    race_distance_km = 5.0
    race_time_sec = 20 * 60  # 20:00

    profile = calibrate_from_race(
        race_distance_km=race_distance_km,
        race_time_sec=race_time_sec,
    )

    p = profile.paces

    print("Running calibration result")
    print("--------------------------")
    print(f"Baseline: {race_distance_km} km in 20:00")
    print()
    print(f"Easy pace:      {format_pace(p.easy_min)} – {format_pace(p.easy_max)}")
    print(f"Threshold pace: {format_pace(p.threshold)}")
    print(f"Interval pace:  {format_pace(p.interval)}")


if __name__ == "__main__":
    main()
