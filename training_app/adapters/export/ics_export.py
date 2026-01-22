from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import uuid

from training_app.domain.plan import TrainingPlan
from training_app.services.rendering.workout_renderer import render_workout



def _ics_escape(s: str) -> str:
    return (
        s.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def export_plan_to_ics(plan: TrainingPlan, path: str | Path) -> None:
    """
    Export the plan to an iCalendar (.ics) file with all-day events.

    Notes:
    - DTSTART;VALUE=DATE means an all-day event.
    - Many calendars treat all-day events as spanning midnight-to-midnight.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    now_utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    lines: list[str] = []
    lines.append("BEGIN:VCALENDAR")
    lines.append("VERSION:2.0")
    lines.append("PRODID:-//training-app//EN")
    lines.append("CALSCALE:GREGORIAN")

    for w in plan.workouts:
        uid = str(uuid.uuid4())
        dtstart = w.date.strftime("%Y%m%d")

        summary, description = render_workout(w)

        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{uid}")
        lines.append(f"DTSTAMP:{now_utc}")
        lines.append(f"DTSTART;VALUE=DATE:{dtstart}")
        lines.append(f"SUMMARY:{_ics_escape(summary)}")
        lines.append(f"DESCRIPTION:{_ics_escape(description)}")
        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")

    content = "\r\n".join(lines) + "\r\n"
    path.write_text(content, encoding="utf-8")
