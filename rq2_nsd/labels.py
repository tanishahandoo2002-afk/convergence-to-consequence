"""Trial labels from NSD's responses.tsv (plan §8.2 step 5).

First viewings are "new", later viewings "old"; outcome from old/new status and accuracy; viewing number
and delay since the last viewing are computed over the participant's whole history, across sessions.
"""
import numpy as np
import pandas as pd

OUTCOMES = {(1, 1): "hit", (1, 0): "miss", (0, 0): "fa", (0, 1): "cr"}


def label_trials(behav, cols):
    df = behav.rename(columns={v: k for k, v in cols.items()})[list(cols)].copy()
    df = df.sort_values(["session", "run", "trial"], kind="stable").reset_index(drop=True)
    df["viewing"] = df.groupby("image").cumcount() + 1
    prev = df.groupby("image")["time"].shift()
    df["log_delay_s"] = np.log10((df.time - prev) * 86400)  # NaN on first viewing
    missing = (df["missing"] == 1) | df.rt.isna()
    # missing responses may carry NaN accuracy; they are masked below, so fill before casting
    old, correct = df.is_old.fillna(0).astype(int), df.is_correct.fillna(0).astype(int)
    df["response_old"] = (old == correct).astype("Int64").mask(missing)
    df["outcome"] = pd.Series([OUTCOMES[(o, c)] for o, c in zip(old, correct)], dtype="object").mask(missing)
    return df[["session", "run", "trial", "image", "viewing", "is_old", "response_old", "outcome", "rt",
               "log_delay_s", "memory_recent"]]
