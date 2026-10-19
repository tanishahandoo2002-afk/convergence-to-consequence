"""Second look: records the author excluded at title/abstract stage that an AI rater kept (include or
unsure). The AIs act as a safety net on the author's screening, not as a filter.

The author fills `resolution` (exclude_confirmed | include) in screening/second_look.csv. A record she
now includes also gets a new author row in human_decisions.csv (the latest row is her decision).
CLI: python -m tools.second_look rq1
"""
import argparse

import pandas as pd

from tools.common import ROOT
from tools.kappa import human

RATERS = ("gemini", "qwen")
COLUMNS = ["record_id", "title", "author", "gemini", "qwen", "gemini_reason", "qwen_reason", "resolution", "note"]
RESOLUTIONS = {"exclude_confirmed", "include"}


def _ai(base, rater):
    p = base / "screening" / f"ai_{rater}.csv"
    if not p.exists():
        return pd.DataFrame(columns=["decision", "reason"])
    return pd.read_csv(p, dtype=str).drop_duplicates("record_id", keep="last").set_index("record_id")[["decision", "reason"]]


def second_look(base):
    author = human(base, "author")
    excluded = author[author == "exclude"].index
    ai = {r: _ai(base, r) for r in RATERS}
    kept = set()
    for r in RATERS:
        kept |= set(ai[r].index[ai[r].decision.isin(["include", "unsure"])])
    ids = [i for i in excluded if i in kept]
    titles = pd.read_csv(base / "search" / "records.csv", dtype=str).set_index("record_id").title
    out = pd.DataFrame({"record_id": ids, "title": titles.reindex(ids).to_numpy(), "author": "exclude"})
    for r in RATERS:
        out[r] = ai[r].decision.reindex(ids).to_numpy()
        out[f"{r}_reason"] = ai[r].reason.reindex(ids).to_numpy()
    out["resolution"], out["note"] = "", ""
    return out[COLUMNS]


def write_second_look(base):
    """Write screening/second_look.csv, keeping any resolutions and notes already filled in."""
    path = base / "screening" / "second_look.csv"
    out = second_look(base)
    if path.exists():
        old = pd.read_csv(path, dtype=str, keep_default_na=False).set_index("record_id")
        for col in ("resolution", "note"):
            out[col] = out.record_id.map(old[col]).fillna("")
    out.to_csv(path, index=False)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rq", choices=["rq1", "rq3"])
    base = ROOT / {"rq1": "rq1_map", "rq3": "rq3_stimulation"}[ap.parse_args().rq]
    out = write_second_look(base)
    print(f"{len(out)} records for a second look ({int((out.resolution == '').sum())} unresolved)")


if __name__ == "__main__":
    main()
