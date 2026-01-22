import json
from pathlib import Path

from training_app.domain.plan import TrainingPlan


def export_plan_to_json(plan: TrainingPlan, path: str | Path, indent: int = 2) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Pydantic v2: model_dump() gives plain Python types (dates become date objects)
    # json.dump can't serialize date, so we use model_dump(mode="json")
    data = plan.model_dump(mode="json")

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent)
