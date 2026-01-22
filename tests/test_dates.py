from datetime import date

from training_app.services.planning.utils import align_to_next_monday


def test_align_to_next_monday():
    # Wednesday -> next Monday
    d = date(2026, 1, 7)
    monday = align_to_next_monday(d)

    assert monday.weekday() == 0
    assert monday >= d
