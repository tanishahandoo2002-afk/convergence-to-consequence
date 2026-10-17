"""Cohen's kappa between raters (plan §8.1 step 4): Gemini–Qwen, each AI–author, author–second rater.

CLI:
  python -m tools.kappa rq1 --make-second-rater-sample   # seeded 20% of records, never overwritten
  python -m tools.kappa rq1                               # writes screening/kappa.csv
"""
import argparse
import math

import pandas as pd
from sklearn.metrics import cohen_kappa_score

from tools.common import ROOT, load_config


def kappa(a, b):
    """Kappa on the records both raters decided ('unsure' is its own category). Returns (kappa, n)."""
    idx = a.index.intersection(b.index)
    return float(cohen_kappa_score(a.loc[idx].astype(str), b.loc[idx].astype(str))), len(idx)


def human(base, rater, stage="title_abstract"):
    p = base / "screening" / "human_decisions.csv"
    if not p.exists():
        return pd.Series(dtype=str)
    h = pd.read_csv(p, dtype=str)
    h = h[(h.rater == rater) & (h.stage == stage)]
    return h.drop_duplicates("record_id", keep="last").set_index("record_id").decision


def report(base):
    merged = pd.read_csv(base / "screening" / "merged.csv", dtype=str).set_index("record_id")
    author, second = human(base, "author"), human(base, "second")
    pairs = {"gemini-qwen": (merged.gemini, merged.qwen), "gemini-author": (merged.gemini, author),
             "qwen-author": (merged.qwen, author), "author-second": (author, second)}
    rows = []
    for name, (a, b) in pairs.items():
        k, n = kappa(a, b) if len(a.index.intersection(b.index)) else (math.nan, 0)
        rows.append({"pair": name, "kappa": round(k, 3), "n": n})
    out = pd.DataFrame(rows)
    out.to_csv(base / "screening" / "kappa.csv", index=False)
    return out


def make_second_rater_sample(base, seed, frac):
    path = base / "screening" / "second_rater_sample.csv"
    if path.exists():
        raise SystemExit(f"{path} exists; the sample is fixed once drawn")
    rec = pd.read_csv(base / "search" / "records.csv", dtype=str)
    rec.sample(n=math.ceil(len(rec) * frac), random_state=seed)[["record_id"]].to_csv(path, index=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rq", choices=["rq1", "rq3"])
    ap.add_argument("--make-second-rater-sample", action="store_true")
    a = ap.parse_args()
    base = ROOT / {"rq1": "rq1_map", "rq3": "rq3_stimulation"}[a.rq]
    cfg = load_config("screening")
    if a.make_second_rater_sample:
        make_second_rater_sample(base, cfg["seed"], cfg["second_rater_sample"])
    else:
        print(report(base).to_string(index=False))


if __name__ == "__main__":
    main()
