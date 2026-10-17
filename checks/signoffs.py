"""Human sign-offs: one row per checked item in checks/human_signoffs.csv."""
from pathlib import Path

import pandas as pd

SIGNOFFS = Path(__file__).resolve().parent / "human_signoffs.csv"


def _passed(step, path):
    df = pd.read_csv(path, dtype=str).fillna("")
    return set(df.loc[(df.step == step) & (df.result == "pass"), "item"])


def has_signoff(step, item, path=SIGNOFFS):
    return item in _passed(step, path)


def missing(step, items, path=SIGNOFFS):
    done = _passed(step, path)
    return [i for i in items if i not in done]
