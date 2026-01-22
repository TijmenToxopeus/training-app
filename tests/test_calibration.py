from training_app.services.calibration.running import calibrate_from_race


def test_calibration_pace_ordering():
    profile = calibrate_from_race(5.0, 20 * 60)
    p = profile.paces

    assert p.interval < p.threshold
    assert p.threshold < p.easy_min
    assert p.easy_min < p.easy_max
