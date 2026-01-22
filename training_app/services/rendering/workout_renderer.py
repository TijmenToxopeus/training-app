from __future__ import annotations

from typing import Tuple

from training_app.domain.workout import ScheduledWorkout


def render_workout(workout: ScheduledWorkout) -> Tuple[str, str]:
    """
    Returns (summary, description) for a scheduled workout.

    - summary: short one-liner (for calendar titles / CLI overview)
    - description: longer details (for calendar description / CLI detail)

    Uses:
    - workout.template.type
    - workout.target_distance_km / target_duration_min
    - workout.template.structure (if present)
    - falls back to workout.template.description
    """
    wtype = workout.template.type.value
    km = workout.target_distance_km
    mins = workout.target_duration_min
    struct = workout.template.structure or {}

    # ---- Summary ----
    parts = [f"Run: {wtype}"]
    if km is not None:
        parts.append(f"{km:.1f} km")
    elif mins is not None:
        parts.append(f"{mins:.0f} min")
    summary = " (" + ", ".join(parts[1:]) + ")" if len(parts) > 1 else ""
    summary = parts[0] + summary

    # ---- Description ----
    # If we have structured data, try to build a nice description.
    # Otherwise fall back to the template.description.
    description = workout.template.description.strip()

    # Build a compact "Structure:" line when relevant (helps in calendars)
    structure_bits = []

    # Common keys for interval sessions
    if "reps" in struct and "work_min" in struct:
        reps = struct.get("reps")
        work_min = struct.get("work_min")
        rest_min = struct.get("rest_min")
        target_pace = struct.get("target_pace")
        bit = f"{reps}×{work_min}min"
        if rest_min is not None:
            bit += f" (rest {rest_min}min)"
        if target_pace:
            bit += f" @ {target_pace}"
        structure_bits.append(bit)

    # Tempo sessions
    if "tempo_min" in struct:
        tempo_min = struct.get("tempo_min")
        target_pace = struct.get("target_pace")
        bit = f"tempo {tempo_min}min"
        if target_pace:
            bit += f" @ {target_pace}"
        structure_bits.append(bit)

    # Warmup/cooldown (applies to many sessions)
    wu = struct.get("warmup_min")
    cd = struct.get("cooldown_min")
    if wu is not None or cd is not None:
        wu_s = f"WU {wu}min" if wu is not None else None
        cd_s = f"CD {cd}min" if cd is not None else None
        structure_bits.append(", ".join([x for x in [wu_s, cd_s] if x]))

    # Easy pace range hint
    easy_range = struct.get("easy_pace_range")
    if easy_range:
        structure_bits.append(f"easy pace {easy_range}")

    # Strides
    if "strides" in struct and isinstance(struct["strides"], dict):
        s = struct["strides"]
        cnt = s.get("count")
        dur = s.get("duration_sec")
        rec = s.get("recovery_sec")
        if cnt and dur:
            bit = f"strides {cnt}×{dur}s"
            if rec:
                bit += f" (rec {rec}s)"
            structure_bits.append(bit)

    notes = struct.get("notes")
    if notes:
        structure_bits.append(f"notes: {notes}")

    if structure_bits:
        description = (description + "\n\n" if description else "") + "Structure: " + " | ".join(structure_bits)

    return summary, description
