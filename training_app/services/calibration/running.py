from training_app.domain.profile import RunningProfile, RunningPaces


def calibrate_from_race(
    race_distance_km: float,
    race_time_sec: float,
) -> RunningProfile:
    """
    Calibrate running paces from a recent race result.

    Assumptions (v0):
    - Threshold pace is slightly slower than race pace
    - Easy pace is significantly slower than threshold
    - Interval pace is faster than threshold
    """

    race_pace_sec_per_km = race_time_sec / race_distance_km

    # --- Simple heuristic offsets (seconds per km) ---
    threshold_pace = race_pace_sec_per_km + 8
    easy_min = threshold_pace + 40
    easy_max = threshold_pace + 80
    interval_pace = threshold_pace - 15

    paces = RunningPaces(
        easy_min=easy_min,
        easy_max=easy_max,
        threshold=threshold_pace,
        interval=interval_pace,
    )

    return RunningProfile(
        baseline_race_distance_km=race_distance_km,
        baseline_race_time_sec=race_time_sec,
        paces=paces,
    )
