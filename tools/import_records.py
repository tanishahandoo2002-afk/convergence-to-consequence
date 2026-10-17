"""Bibliographic records: RIS import, de-duplication and the combined records.csv.

Every source is written with RECORD_COLUMNS so screening sees one format.
CLI:
  python -m tools.import_records rq1 <file.ris> --source scopus --query "<string used>"
  python -m tools.import_records rq1 --build      # dedupe all logged sources -> records.csv
"""
import argparse
import datetime
import re
from pathlib import Path

import pandas as pd

from tools.common import ROOT

RECORD_COLUMNS = ["record_id", "source", "pmid", "doi", "title", "abstract", "year"]
LOG_COLUMNS = ["date", "source", "query", "hits", "file"]


def record_id(rec, source, row):
    if rec.get("pmid"):
        return f"pmid:{rec['pmid']}"
    if rec.get("doi"):
        return f"doi:{rec['doi'].lower()}"
    return f"src:{source}:{row}"


def read_ris(path, source="ris"):
    tags = {"TI": "title", "T1": "title", "AB": "abstract", "N2": "abstract", "DO": "doi",
            "PY": "year", "Y1": "year", "AN": "pmid"}
    records, cur = [], {}
    for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        m = re.match(r"^([A-Z][A-Z0-9])  - ?(.*)$", line)
        if not m:
            continue
        tag, value = m.group(1), m.group(2).strip()
        if tag == "ER":
            records.append(cur)
            cur = {}
        elif tag in tags and not cur.get(tags[tag]):
            cur[tags[tag]] = value
    out = []
    for i, r in enumerate(records):
        r["year"] = r.get("year", "")[:4]
        if not r.get("pmid", "").isdigit():
            r["pmid"] = ""
        rec = {c: r.get(c, "") for c in RECORD_COLUMNS} | {"source": source}
        rec["record_id"] = record_id(rec, source, i)
        out.append(rec)
    return out


def _norm_title(t):
    return re.sub(r"[^a-z0-9]", "", t.lower())


def dedupe(records):
    """Keep the first of each duplicate. Duplicate = same non-empty PMID, same non-empty DOI
    (case-insensitive), or same normalised title and same year. Returns (kept, n_removed)."""
    seen, kept = set(), []
    for r in records:
        keys = set()
        if r.get("pmid"):
            keys.add(("pmid", r["pmid"]))
        if r.get("doi"):
            keys.add(("doi", r["doi"].lower()))
        if _norm_title(r.get("title", "")):
            keys.add(("title", _norm_title(r["title"]), r.get("year", "")))
        if keys & seen:
            continue
        seen |= keys
        kept.append(r)
    return kept, len(records) - len(kept)


def append_log(search_dir, source, query, hits, file):
    log = Path(search_dir) / "search_log.csv"
    row = pd.DataFrame([[datetime.date.today().isoformat(), source, query, hits, file]], columns=LOG_COLUMNS)
    row.to_csv(log, mode="a", header=not log.exists(), index=False)


def build_records(search_dir):
    search_dir = Path(search_dir)
    log = pd.read_csv(search_dir / "search_log.csv", dtype=str).fillna("")
    files = log.loc[log.source != "dedupe", "file"].drop_duplicates()  # a same-day re-run logs a file twice
    records = []
    for f in files:
        records += pd.read_csv(search_dir / f, dtype=str).fillna("").to_dict("records")
    kept, removed = dedupe(records)
    pd.DataFrame(kept, columns=RECORD_COLUMNS).to_csv(search_dir / "records.csv", index=False)
    append_log(search_dir, "dedupe", "", removed, "records.csv")
    return len(kept), removed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rq", choices=["rq1", "rq3"])
    ap.add_argument("file", nargs="?")
    ap.add_argument("--source")
    ap.add_argument("--query", default="")
    ap.add_argument("--build", action="store_true")
    a = ap.parse_args()
    search_dir = ROOT / {"rq1": "rq1_map", "rq3": "rq3_stimulation"}[a.rq] / "search"
    search_dir.mkdir(parents=True, exist_ok=True)
    if a.file:
        recs = read_ris(a.file, source=a.source or "ris")
        out = f"{a.source or 'ris'}_{datetime.date.today():%Y%m%d}.csv"
        pd.DataFrame(recs, columns=RECORD_COLUMNS).to_csv(search_dir / out, index=False)
        append_log(search_dir, a.source or "ris", a.query, len(recs), out)
        print(f"{len(recs)} records -> {out}")
    if a.build:
        n, removed = build_records(search_dir)
        print(f"records.csv: {n} records ({removed} duplicates removed)")


if __name__ == "__main__":
    main()
