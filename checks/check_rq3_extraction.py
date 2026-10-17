"""RQ3 extraction check (plan §8.3 steps 5-6, §12): schema and enums, usable statistics per effect,
montages known, complete RoB 2 per study, second-rater checks on at least 20% of rows.
CLI: python -m checks.check_rq3_extraction
"""
import math
import sys
from pathlib import Path

import pandas as pd

SHEETS = Path(__file__).resolve().parent.parent / "rq3_stimulation"
ENUMS = {"population": {"healthy", "MCI", "AD"}, "design": {"parallel", "crossover"}, "stim": {"tDCS", "tACS"},
         "timing": {"encoding", "retrieval", "offline"}, "test_type": {"recall", "recognition", "source"},
         "higher_is_better": {"1", "0"}}
ROB_DOMAINS = ["d1_randomisation", "d2_deviations", "d3_missing", "d4_measurement", "d5_selection", "overall"]
ROB_VALUES = {"low", "some", "high"}


def _blank(s):
    return s.isna() | (s.astype(str).str.strip() == "")


def validate(effects, montages, rob2):
    errors, warnings = [], []
    e = effects.copy()
    for col, allowed in ENUMS.items():
        vals = e[col].astype(str).str.replace(r"\.0$", "", regex=True)
        bad = ~vals.isin(allowed)
        if bad.any():
            errors.append(f"{col} must be one of {sorted(allowed)}: {sorted(e.es_id[bad])}")
    stats = ["m_active", "sd_active", "m_sham", "sd_sham"]
    has_means = ~e[stats].apply(_blank).any(axis=1)
    has_t = ~_blank(e.t_value)
    no_data = ~has_means & ~(has_t & (e.design == "parallel"))
    if no_data.any():
        errors.append(f"need means and SDs (or t for parallel designs): {sorted(e.es_id[no_data])}")
    sd = e[["sd_active", "sd_sham"]].apply(pd.to_numeric, errors="coerce")
    bad_sd = has_means & (sd <= 0).any(axis=1)
    if bad_sd.any():
        errors.append(f"SD must be > 0: {sorted(e.es_id[bad_sd])}")
    n = e[["n_active", "n_sham"]].apply(pd.to_numeric, errors="coerce")
    if (n.isna() | (n < 2)).any(axis=1).any():
        errors.append(f"n_active/n_sham must be numbers >= 2: {sorted(e.es_id[(n.isna() | (n < 2)).any(axis=1)])}")
    cross_n = (e.design == "crossover") & (n.n_active != n.n_sham)
    if cross_n.any():
        errors.append(f"crossover rows need n_active == n_sham: {sorted(e.es_id[cross_n])}")
    unknown = sorted(set(e.montage_id) - set(montages.montage_id))
    if unknown:
        errors.append(f"montage_id not in montages.csv: {unknown}")

    rob = rob2.set_index("study_id")
    missing = sorted(set(e.study_id) - set(rob.index))
    if missing:
        errors.append(f"studies without a RoB 2 row: {missing}")
    for sid in sorted(set(e.study_id) & set(rob.index)):
        r = rob.loc[sid]
        bad = [d for d in ROB_DOMAINS if str(r[d]) not in ROB_VALUES]
        if bad:
            errors.append(f"{sid}: RoB 2 domains not rated low/some/high: {bad}")
        if (e.loc[e.study_id == sid, "design"] == "crossover").any() and str(r["d1b_carryover"]) not in ROB_VALUES:
            errors.append(f"{sid}: crossover study needs d1b_carryover rated")

    if len(e) and (~_blank(e.checked_by)).sum() < math.ceil(0.2 * len(e)):
        errors.append(f"checked_by filled on {(~_blank(e.checked_by)).sum()} of {len(e)} rows; the second rater "
                      f"must check at least {math.ceil(0.2 * len(e))}")
    return errors, warnings


def main():
    read = lambda f: pd.read_csv(SHEETS / f, dtype=str, keep_default_na=False).replace("", None)
    errors, warnings = validate(read("effects.csv"), read("montages.csv"), read("rob2.csv"))
    for w in warnings:
        print("WARNING:", w)
    for e in errors:
        print("FAIL:", e)
    if errors:
        sys.exit(1)
    print("RQ3 extraction check OK")


if __name__ == "__main__":
    main()
