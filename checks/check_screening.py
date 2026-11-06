"""Screening check (plan §8.1 step 4): the author decided every record routed to her, any second rater
did their sample, and PRISMA reconciles. Kappa is reported by tools.kappa, not enforced (CHANGELOG 2026-10-27)."""
import argparse
import sys

import pandas as pd

from tools.common import ROOT
from tools.kappa import human
from tools.prisma import counts, reconcile


def check(base):
    errors = []
    merged = pd.read_csv(base / "screening" / "merged.csv", dtype=str)
    author = human(base, "author")
    need = set(merged.loc[merged.needs_human.str.lower() == "true", "record_id"])
    second_look = base / "screening" / "ai_suggestions_unseen.csv"
    if second_look.exists():
        s = pd.read_csv(second_look, dtype=str)
        need |= set(s.record_id[s.ai_suggestion == "include"])
    missing = sorted(need - set(author.index))
    if missing:
        errors.append(f"{len(missing)} records need an author decision: {missing[:10]}")
    sample_path = base / "screening" / "second_rater_sample.csv"
    if sample_path.exists():  # RQ1 has no second rater (CHANGELOG 2026-11-07)
        miss2 = sorted(set(pd.read_csv(sample_path, dtype=str).record_id) - set(human(base, "second").index))
        if miss2:
            errors.append(f"{len(miss2)} records in the sample lack a second rater decision: {miss2[:10]}")
    errors += reconcile(counts(base))
    return errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rq", choices=["rq1", "rq3"])
    base = ROOT / {"rq1": "rq1_map", "rq3": "rq3_stimulation"}[ap.parse_args().rq]
    errors = check(base)
    for e in errors:
        print("FAIL:", e)
    if errors:
        sys.exit(1)
    print("screening check OK")


if __name__ == "__main__":
    main()
