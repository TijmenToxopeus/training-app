from datetime import date
from pydantic import BaseModel
from typing import List
from training_app.domain.workout import ScheduledWorkout


class TrainingPlan(BaseModel):
    start_date: date
    end_date: date
    goal_race_date: date
    workouts: List[ScheduledWorkout]
