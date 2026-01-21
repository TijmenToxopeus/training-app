from datetime import date
from pydantic import BaseModel
from training_app.domain.enums import WorkoutType, Sport


class WorkoutTemplate(BaseModel):
    sport: Sport
    type: WorkoutType
    description: str


class ScheduledWorkout(BaseModel):
    date: date
    template: WorkoutTemplate
    target_distance_km: float | None = None
    target_duration_min: float | None = None
