"""Seeded 20% spot-check sample of experiments (plan §8.1 step 6). Drawn once, never redrawn.
CLI: python -m rq1_map.spotcheck
"""
import math
from pathlib import Path

import pandas as pd

from tools.common import load_config

SAMPLE = Path(__file__).resolve().parent / "spotcheck_sample.csv"


def make_sample(experiments, seed, frac, path=SAMPLE):
    path = Path(path)
    if path.exists():
        raise SystemExit(f"{path} exists; the spot-check sample is fixed once drawn")
    ids = list(experiments.exp_id.sample(n=math.ceil(len(experiments) * frac), random_state=seed))
    pd.DataFrame({"exp_id": ids}).to_csv(path, index=False)
    return ids


if __name__ == "__main__":
    cfg = load_config("rq1")
    exps = pd.read_csv(Path(__file__).resolve().parent / "experiments.csv", dtype=str)
    print(make_sample(exps, cfg["seed"], cfg["spotcheck_frac"]))
