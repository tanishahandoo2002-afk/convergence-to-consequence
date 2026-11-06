"""Cohen's kappa between raters (plan §8.1 step 4): ASI–Qwen, each AI–author, author–second rater.

CLI:
  python -m tools.kappa rq1 --make-second-rater-sample   # seeded 20% of records, never overwritten
  python -m tools.kappa rq1 --make-second-rater-sheet    # their blind sheet for that sample, never overwritten
  python -m tools.kappa rq1                               # writes screening/kappa.csv
"""
import argparse
import math

import pandas as pd
from sklearn.metrics import cohen_kappa_score

from tools.common import ROOT, load_config

SECOND_LOOK_SHEET = "human_decisions_second_look.csv"
SECOND_RATER_SHEET = "second_rater_decisions.csv"
FULL_TEXT_SHEET = "full_text_check.csv"
SHEETS = ("human_decisions.csv", SECOND_LOOK_SHEET, SECOND_RATER_SHEET, FULL_TEXT_SHEET)


def kappa(a, b):
    """Kappa on the records both raters decided ('unsure' is its own category). Returns (kappa, n)."""
    idx = a.index.intersection(b.index)
    return float(cohen_kappa_score(a.loc[idx].astype(str), b.loc[idx].astype(str))), len(idx)


def human(base, rater, stage="title_abstract", sheets=SHEETS):
    paths = [base / "screening" / s for s in sheets if (base / "screening" / s).exists()]
    if not paths:
        return pd.Series(dtype=str)
    h = pd.concat([pd.read_csv(p, dtype=str) for p in paths], ignore_index=True)
    if "agree" in h:
        # yes keeps the AI suggestion and no reverses it; a typed decision wins, and anything else counts as unanswered
        agree = h.agree.str.strip().str.lower()
        flipped = h.ai_suggestion.map({"include": "exclude", "exclude": "include"})
        h["decision"] = h.decision.fillna(h.ai_suggestion.where(agree == "yes", flipped.where(agree == "no")))
    h = h[(h.rater == rater) & (h.stage == stage) & h.decision.notna()]
    return h.drop_duplicates("record_id", keep="last").set_index("record_id").decision


def report(base):
    merged = pd.read_csv(base / "screening" / "merged.csv", dtype=str).set_index("record_id")
    author, second = human(base, "author"), human(base, "second")
    # second-look records were picked because both AIs excluded them, which would bias AI-author kappa
    routed = human(base, "author", sheets=SHEETS[:1])
    pairs = {"asi-qwen": (merged.asi, merged.qwen), "asi-author": (merged.asi, routed),
             "qwen-author": (merged.qwen, routed), "author-second": (author, second)}
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


def make_second_rater_sheet(base, seed):
    """The second rater's sheet: title and abstract only, blind to every other decision. Never overwritten,
    because it holds their answers. Returns whether it wrote."""
    path = base / "screening" / SECOND_RATER_SHEET
    if path.exists():
        return False
    sample = pd.read_csv(base / "screening" / "second_rater_sample.csv", dtype=str).record_id
    rec = pd.read_csv(base / "search" / "records.csv", dtype=str).fillna("")
    sheet = rec[rec.record_id.isin(sample)].sample(frac=1, random_state=seed)
    sheet = sheet.assign(stage="title_abstract", rater="second", decision="", reason="", date="")
    sheet[["record_id", "stage", "rater", "year", "doi", "title", "abstract", "decision", "reason", "date"]].to_csv(path, index=False)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rq", choices=["rq1", "rq3"])
    ap.add_argument("--make-second-rater-sample", action="store_true")
    ap.add_argument("--make-second-rater-sheet", action="store_true")
    a = ap.parse_args()
    base = ROOT / {"rq1": "rq1_map", "rq3": "rq3_stimulation"}[a.rq]
    cfg = load_config("screening")
    if a.make_second_rater_sample:
        make_second_rater_sample(base, cfg["seed"], cfg["second_rater_sample"])
    elif a.make_second_rater_sheet:
        if not make_second_rater_sheet(base, cfg["seed"]):
            print(f"{SECOND_RATER_SHEET} exists; left as it is")
    else:
        print(report(base).to_string(index=False))


if __name__ == "__main__":
    main()
