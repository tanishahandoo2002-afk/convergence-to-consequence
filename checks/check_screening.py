"""Screening check (plan §8.1 step 4, §12): human decisions complete, kappa rule, PRISMA reconciles."""
import argparse
import sys

import pandas as pd

from tools.common import ROOT, load_config
from tools.kappa import human, kappa
from tools.prisma import counts, reconcile


def check(base, kappa_min):
    errors = []
    merged = pd.read_csv(base / "screening" / "merged.csv", dtype=str)
    author = human(base, "author")
    need = merged.loc[merged.needs_human.str.lower() == "true", "record_id"]
    missing = sorted(set(need) - set(author.index))
    if missing:
        errors.append(f"{len(missing)} records need an author decision: {missing[:10]}")
    sample_path = base / "screening" / "second_rater_sample.csv"
    if not sample_path.exists():
        errors.append("second_rater_sample.csv missing: python -m tools.kappa <rq> --make-second-rater-sample")
    else:
        miss2 = sorted(set(pd.read_csv(sample_path, dtype=str).record_id) - set(human(base, "second").index))
        if miss2:
            errors.append(f"{len(miss2)} records in the sample lack a second rater decision: {miss2[:10]}")
    m = merged.set_index("record_id")
    for ai in ("gemini", "qwen"):
        if len(m.index.intersection(author.index)) >= 2:
            k, n = kappa(m[ai], author)
            if k < kappa_min:
                rest = sorted(set(m.index) - set(author.index))
                if rest:
                    errors.append(f"{ai}-author kappa {k:.2f} < {kappa_min} (n={n}): plan §12 requires the author "
                                  f"to screen every record; {len(rest)} remain")
    errors += reconcile(counts(base))
    return errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rq", choices=["rq1", "rq3"])
    base = ROOT / {"rq1": "rq1_map", "rq3": "rq3_stimulation"}[ap.parse_args().rq]
    errors = check(base, load_config("screening")["kappa_min"])
    for e in errors:
        print("FAIL:", e)
    if errors:
        sys.exit(1)
    print("screening check OK")


if __name__ == "__main__":
    main()
