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


def session_behav(seed=0, n=750):
    """One synthetic session: images drawn from a pool so some repeat within the session."""
    rng = np.random.default_rng(seed)
    images = rng.integers(0, 300, n)
    last, gaps, old = {}, [], []
    for i, im in enumerate(images):
        gaps.append(i - last[im] if im in last else 0)
        old.append(int(im in last))
        last[im] = i
    return behav([(1, 1 + i // 63, i % 63 + 1, int(images[i]), 100 + i * 4 / 86400, old[i], 1, 800, 0, gaps[i])
                  for i in range(n)])


def test_missing_column_lists_real_columns():
    from checks.check_rq2 import check_behaviour
    b = session_behav().drop(columns=[COLS["time"]])
    errors = check_behaviour(b, COLS)
    assert len(errors) == 1 and COLS["time"] in errors[0] and COLS["session"] in errors[0]


def test_image_order_mismatch_reported():
    from checks.check_rq2 import check_behaviour
    b = session_behav()
    labelled = label_trials(b, COLS)
    expected = labelled.image.copy()
    assert check_behaviour(b, COLS, expected_images=expected) == []
    expected.iloc[[10, 11]] = expected.iloc[[11, 10]].to_numpy()
    errors = check_behaviour(b, COLS, expected_images=expected)
    assert any("trial" in e and "session 1" in e and "image order" in e for e in errors)


def test_delay_agrees_with_memory_recent():
    from checks.check_rq2 import check_behaviour
    b = session_behav()
    assert check_behaviour(b, COLS) == []
    b[COLS["memory_recent"]] = -b[COLS["memory_recent"]]
    assert any("memory_recent" in e for e in check_behaviour(b, COLS))


def test_is_old_must_match_viewing():
    from checks.check_rq2 import check_behaviour
    b = session_behav()
    b.loc[0, COLS["is_old"]] = 1
    assert any("is_old" in e for e in check_behaviour(b, COLS))


def test_short_session_reported():
    from checks.check_rq2 import check_behaviour
    assert any("session 1" in e and "749" in e for e in check_behaviour(session_behav().iloc[:749], COLS))


def test_missing_response_with_nan_correct_does_not_crash():
    out = label_trials(behav([(1, 1, 1, 5, 100.0, 0, 1, 800, 0, 0),
                              (1, 1, 2, 6, 100.1, 0, np.nan, np.nan, 1, 0)]), COLS)
    assert pd.isna(out.outcome[1]) and out.outcome[0] == "cr"
