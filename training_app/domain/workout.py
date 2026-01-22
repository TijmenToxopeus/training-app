from __future__ import annotations

from datetime import date
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field
from training_app.domain.enums import Sport, WorkoutType


class WorkoutTemplate(BaseModel):
    """
    A reusable description of a workout.
    `structure` holds machine-readable info (reps, durations, targets, etc.)
    so we can later export nicely (ICS, Strava workout builder, etc.).
    """
    sport: Sport
    type: WorkoutType
    description: str

    # JSON-like structure, e.g. {"warmup_min": 12, "reps": 6, "work_min": 2, ...}
    structure: Dict[str, Any] = Field(default_factory=dict)


class ScheduledWorkout(BaseModel):
    """
    A workout placed on a calendar date.
    """
    date: date
    template: WorkoutTemplate

    # v0: distance-based targets. Later you can add duration / TSS / etc.
    target_distance_km: Optional[float] = None
    target_duration_min: Optional[float] = None
