"""PubMed search via NCBI E-utilities, logged for PRISMA and the registration.

CLI: python -m tools.pubmed_search rq1   (needs NCBI_EMAIL; NCBI_API_KEY optional)
"""
import argparse
import datetime
import os
import time
import xml.etree.ElementTree as ET

import pandas as pd
import requests

from tools.common import ROOT, load_config, record_versions
from tools.import_records import RECORD_COLUMNS, append_log, build_records, record_id

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
BATCH = 200


def _text(el):
    return " ".join("".join(el.itertext()).split()) if el is not None else ""


def parse_efetch(xml):
    out = []
    for art in ET.fromstring(xml).iter("PubmedArticle"):
        pmid = _text(art.find("MedlineCitation/PMID"))
        doi = _text(art.find(".//ArticleIdList/ArticleId[@IdType='doi']")) or \
            _text(art.find(".//ELocationID[@EIdType='doi']"))
        date = art.find(".//JournalIssue/PubDate")
        year = _text(date.find("Year")) if date is not None and date.find("Year") is not None else \
            _text(date.find("MedlineDate"))[:4] if date is not None else ""
        rec = {
            "source": "pubmed", "pmid": pmid, "doi": doi,
            "title": _text(art.find(".//ArticleTitle")),
            "abstract": " ".join(_text(a) for a in art.findall(".//Abstract/AbstractText")),
            "year": year,
        }
        rec["record_id"] = record_id(rec, "pubmed", len(out))
        out.append({c: rec[c] for c in RECORD_COLUMNS})
    return out


def search(query, email, api_key=None):
    params = {"db": "pubmed", "tool": "convergence-to-consequence", "email": email}
    if api_key:
        params["api_key"] = api_key
    pause = 0.11 if api_key else 0.34  # NCBI limits: 10/s with a key, 3/s without
    r = requests.get(EUTILS + "esearch.fcgi", params=params | {"term": query, "usehistory": "y", "retmode": "json"}, timeout=60)
    r.raise_for_status()
    res = r.json()["esearchresult"]
    count, webenv, key = int(res["count"]), res["webenv"], res["querykey"]
    records = []
    for start in range(0, count, BATCH):
        time.sleep(pause)
        r = requests.get(EUTILS + "efetch.fcgi", timeout=120, params=params | {
            "WebEnv": webenv, "query_key": key, "retstart": start, "retmax": BATCH, "retmode": "xml"})
        r.raise_for_status()
        records += parse_efetch(r.text)
    if len(records) != count:
        raise RuntimeError(f"PubMed reported {count} hits but {len(records)} were fetched")
    return records


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rq", choices=["rq1", "rq3"])
    a = ap.parse_args()
    cfg = load_config(a.rq)
    email = os.environ.get("NCBI_EMAIL")
    if not email:
        raise SystemExit("Set NCBI_EMAIL (NCBI asks every E-utilities user for a contact address)")
    search_dir = ROOT / {"rq1": "rq1_map", "rq3": "rq3_stimulation"}[a.rq] / "search"
    search_dir.mkdir(parents=True, exist_ok=True)
    query = " ".join(cfg["pubmed_query"].split())
    records = search(query, email, os.environ.get("NCBI_API_KEY"))
    out = f"pubmed_{datetime.date.today():%Y%m%d}.csv"
    pd.DataFrame(records, columns=RECORD_COLUMNS).to_csv(search_dir / out, index=False)
    append_log(search_dir, "pubmed", query, len(records), out)
    n, removed = build_records(search_dir)
    record_versions(f"{a.rq}_search")
    print(f"PubMed: {len(records)} hits -> {out}; records.csv: {n} ({removed} duplicates removed)")


if __name__ == "__main__":
    main()
