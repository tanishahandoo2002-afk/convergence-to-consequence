import math

import numpy as np
import pandas as pd

from rq2_nsd.labels import label_trials
from tools.common import load_config

COLS = load_config("rq2")["behav_columns"]


def behav(rows):
    """rows: (session, run, trial, image, time, is_old, is_correct, rt, missing, memory_recent)"""
    names = ["session", "run", "trial", "image", "time", "is_old", "is_correct", "rt", "missing", "memory_recent"]
    return pd.DataFrame(rows, columns=[COLS[n] for n in names])


def test_outcomes():
    out = label_trials(behav([(1, 1, i + 1, 10 + i, 100 + i / 86400, o, c, 800, 0, 0)
                              for i, (o, c) in enumerate([(1, 1), (1, 0), (0, 0), (0, 1)])]), COLS)
    assert list(out.outcome) == ["hit", "miss", "fa", "cr"]
    assert list(out.response_old) == [1, 0, 1, 0]


def test_viewing_and_delay_across_sessions():
    out = label_trials(behav([(1, 1, 1, 5, 100.0, 0, 1, 800, 0, 0), (1, 1, 2, 5, 100.0 + 60 / 86400, 1, 1, 800, 0, 1),
                              (3, 1, 1, 5, 110.0, 1, 1, 800, 0, 0)]), COLS)
    assert list(out.viewing) == [1, 2, 3]
    assert math.isnan(out.log_delay_s[0])
    assert abs(out.log_delay_s[1] - math.log10(60)) < 1e-6
    assert abs(out.log_delay_s[2] - math.log10(10 * 86400 - 60)) < 1e-6


def test_missing_response():
    out = label_trials(behav([(1, 1, 1, 5, 100.0, 0, 1, 800, 0, 0), (1, 1, 2, 5, 100.1, 1, 0, np.nan, 1, 1)]), COLS)
    assert pd.isna(out.outcome[1]) and pd.isna(out.response_old[1])
    assert out.viewing[1] == 2


def test_chronological_order():
    rows = [(2, 1, 1, 7, 105.0, 0, 1, 800, 0, 0), (1, 2, 1, 6, 100.5, 0, 1, 800, 0, 0), (1, 1, 2, 5, 100.1, 0, 1, 800, 0, 0)]
    out = label_trials(behav(rows), COLS)
    assert list(zip(out.session, out.run, out.trial)) == [(1, 1, 2), (1, 2, 1), (2, 1, 1)]
