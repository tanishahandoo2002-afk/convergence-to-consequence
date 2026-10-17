"""Search check: every logged file exists with the logged number of rows; records.csv has no duplicates."""
import argparse
import sys

import pandas as pd

from tools.common import ROOT


def check(search_dir):
    errors = []
    log_path = search_dir / "search_log.csv"
    if not log_path.exists():
        return [f"{log_path} missing: run the search first"]
    log = pd.read_csv(log_path, dtype=str).fillna("")
    for _, row in log[log.source != "dedupe"].iterrows():
        f = search_dir / row.file
        if not f.exists():
            errors.append(f"logged file {row.file} is missing")
        elif len(pd.read_csv(f, dtype=str)) != int(row.hits):
            errors.append(f"{row.file}: logged {row.hits} hits but file has {len(pd.read_csv(f))} rows")
        if not row.date or (row.source == "pubmed" and not row.query):
            errors.append(f"{row.file}: log row lacks date or query")
    rec_path = search_dir / "records.csv"
    if not rec_path.exists():
        return errors + ["records.csv missing: run python -m tools.import_records <rq> --build"]
    rec = pd.read_csv(rec_path, dtype=str).fillna("")
    for col in ["record_id", "pmid", "doi"]:
        vals = rec.loc[rec[col] != "", col].str.lower() if col == "doi" else rec.loc[rec[col] != "", col]
        if vals.duplicated().any():
            errors.append(f"records.csv has duplicate {col}: {sorted(set(vals[vals.duplicated()]))[:5]}")
    return errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rq", choices=["rq1", "rq3"])
    a = ap.parse_args()
    errors = check(ROOT / {"rq1": "rq1_map", "rq3": "rq3_stimulation"}[a.rq] / "search")
    for e in errors:
        print("FAIL:", e)
    if errors:
        sys.exit(1)
    print("search check OK")


if __name__ == "__main__":
    main()
