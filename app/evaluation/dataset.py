"""Evaluation dataset loader."""

import json
from pathlib import Path
from typing import List, Optional

from app.evaluation.models import EvalSample

DEFAULT_DATASET_PATH = Path("data/golden_dataset.json")


def load_eval_dataset(
    path: Optional[Path] = None,
    limit: Optional[int] = None,
) -> List[EvalSample]:
    """Load benchmark evaluation samples from the golden dataset."""
    target = path or DEFAULT_DATASET_PATH
    if not target.exists():
        raise FileNotFoundError(f"Evaluation dataset not found at {target}")

    with open(target, "r", encoding="utf-8") as f:
        records = json.load(f)

    samples = [EvalSample(**item) for item in records]
    return samples[:limit] if limit else samples
