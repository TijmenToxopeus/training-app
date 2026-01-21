from pydantic import BaseModel
from training_app.domain.enums import Sport


class RunningPaces(BaseModel):
    easy_min: float  # sec/km
    easy_max: float
    threshold: float
    interval: float


class RunningProfile(BaseModel):
    sport: Sport = Sport.RUN
    baseline_race_distance_km: float
    baseline_race_time_sec: float
    paces: RunningPaces
