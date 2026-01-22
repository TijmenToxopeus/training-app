from datetime import date, timedelta


def align_to_next_monday(d: date) -> date:
    """Return the next Monday on/after the given date."""
    # Monday == 0 ... Sunday == 6
    days_ahead = (7 - d.weekday()) % 7
    return d + timedelta(days=days_ahead)
