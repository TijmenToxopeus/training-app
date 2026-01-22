from enum import Enum


class Sport(str, Enum):
    RUN = "run"


class WorkoutType(str, Enum):
    EASY = "easy"
    LONG = "long"
    TEMPO = "tempo"
    INTERVALS = "intervals"
    RECOVERY = "recovery"
    REST = "rest"
    RACE = "race"
