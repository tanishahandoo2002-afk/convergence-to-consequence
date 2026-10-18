"""Screening calibration (before the RQ1 registration): a seeded random sample of records from the
registered PubMed query, labelled by the author, against which each AI rater (model + criteria wording)
is compared. Used to choose the local model and finalise the criteria wording, not to screen.

CLI:
  python -m tools.calibrate rq1 --draw [--n 30]          # sample records + blank labels.csv (never overwritten)
  python -m tools.calibrate rq1 --rater qwen [--model M]  # AI decisions on the sample -> ai_<rater>_<model>.csv
  python -m tools.calibrate rq1 --report                  # kappa etc. per AI log vs the author's labels
"""
import argparse
import datetime
import os
import random
import re

import pandas as pd
import requests

from tools.common import ROOT, load_config
from tools.import_records import RECORD_COLUMNS
from tools.kappa import kappa
from tools.pubmed_search import EUTILS, parse_efetch
from tools.screen import DECISIONS, client_for, run_rater

LABELS = {"include", "exclude", "unsure"}


def sample_ids(ids, n, seed):
    return random.Random(seed).sample(sorted(ids), n)


def label_template(records, path):
    if path.exists():
        raise SystemExit(f"{path} exists; the author's labels are never overwritten")
    t = records[["record_id", "title"]].assign(decision="", note="")
    t.to_csv(path, index=False)


def report(cal_dir):
    labels = pd.read_csv(cal_dir / "labels.csv", dtype=str, keep_default_na=False)
    bad = sorted(set(labels.decision) - LABELS - {""})
    if bad:
        raise SystemExit(f"labels.csv decisions must be include/exclude/unsure (or blank): found {bad}")
    lab = labels[labels.decision != ""].set_index("record_id").decision
    rows = []
    for log in sorted(cal_dir.glob("ai_*.csv")):
        ai = pd.read_csv(log, dtype=str).drop_duplicates("record_id", keep="last").set_index("record_id")
        a = ai.decision.reindex(lab.index).dropna()
        h = lab.loc[a.index]
        k, n = kappa(a, h) if len(a) >= 2 else (float("nan"), len(a))
        rows.append({"log": log.name, "model": ai.model.iloc[0], "n_labelled": n, "kappa": round(k, 3),
                     "agreement": round(float((a == h).mean()), 3) if n else float("nan"),
                     "unsure_rate": round(float((a == "unsure").mean()), 3) if n else float("nan"),
                     "agree_or_unsure": round(float(((a == h) | (a == "unsure")).mean()), 3) if n else float("nan"),
                     "wrong_exclude": int(((a == "exclude") & (h == "include")).sum())})
    out = pd.DataFrame(rows)
    out.to_csv(cal_dir / "kappa.csv", index=False)
    return out


def _draw(rq, base, n, seed):
    q = " ".join(load_config(rq)["pubmed_query"].split())
    params = {"db": "pubmed", "tool": "convergence-to-consequence", "email": os.environ.get("NCBI_EMAIL", "")}
    res = requests.get(EUTILS + "esearch.fcgi", params=params | {"term": q, "retmode": "json", "retmax": 10000},
                       timeout=60).json()["esearchresult"]
    ids = sample_ids(res["idlist"], n, seed)
    xml = requests.get(EUTILS + "efetch.fcgi", params=params | {"id": ",".join(ids), "retmode": "xml"}, timeout=120).text
    recs = pd.DataFrame(parse_efetch(xml), columns=RECORD_COLUMNS)
    if len(recs) != n:
        raise SystemExit(f"fetched {len(recs)} of {n} sampled records")
    base.mkdir(parents=True, exist_ok=True)
    if (base / "records.csv").exists():
        raise SystemExit(f"{base / 'records.csv'} exists; the calibration sample is drawn once")
    recs.to_csv(base / "records.csv", index=False)
    (base / "draw_log.txt").write_text(f"date={datetime.date.today()} seed={seed} n={n} total_hits={res['count']}\n"
                                       f"query={q}\n")
    label_template(recs, base / "labels.csv")
    print(f"sampled {n} of {res['count']} records -> {base}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rq", choices=["rq1", "rq3"])
    ap.add_argument("--draw", action="store_true")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--rater", choices=["gemini", "qwen"])
    ap.add_argument("--model", help="override the configured model, e.g. qwen2.5:7b-instruct")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    base = ROOT / {"rq1": "rq1_map", "rq3": "rq3_stimulation"}[a.rq] / "screening" / "calibration"
    if a.draw:
        _draw(a.rq, base, a.n, load_config("screening")["seed"])
    if a.rater:
        r = load_config("screening")["raters"][a.rater]
        model = a.model or r["model"]
        criteria = (base.parent / "criteria.md").read_text()
        log = base / f"ai_{a.rater}_{re.sub(r'[^A-Za-z0-9.]+', '-', model)}.csv"
        recs = pd.read_csv(base / "records.csv", dtype=str).fillna("")
        print(f"{a.rater} ({model}): screened {run_rater(recs, a.rater, client_for(r), model, criteria, log)} records")
    if a.report:
        print(report(base).to_string(index=False))


if __name__ == "__main__":
    main()
