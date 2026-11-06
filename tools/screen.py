"""AI-assisted screening with two independent raters (plan §8.1 step 4, §8.6).

Both raters use the OpenAI-compatible chat API (ASI:One and Ollama), temperature 0.
Every decision is logged with model, prompt hash, timestamp and the raw reply.
CLI:
  python -m tools.screen rq1 --stage title_abstract --rater qwen [--limit 5]
  python -m tools.screen rq1 --stage title_abstract --merge
  python -m tools.screen rq1 --second-look                   # the author's sheet for rescued agreed excludes
  python -m tools.screen rq1 --stage full_text --rater asi   # contrast-table proposals; author confirms each
"""
import argparse
import datetime
import hashlib
import json
import math
import os
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from tools.common import ROOT, load_config, record_versions
from tools.kappa import SECOND_LOOK_SHEET

DECISIONS = {"include", "exclude", "unsure"}
LOG_COLUMNS = ["record_id", "rater", "model", "prompt_sha256", "timestamp", "decision", "reason", "raw"]
INSTRUCTION = (
    "You screen records for a systematic review. Apply the eligibility criteria above to the record "
    "the user gives you. Answer with JSON only, exactly in this form: "
    '{"decision": "include" | "exclude" | "unsure", "reason": "<one sentence>"}'
)


EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
EUTILS_TOOL = "convergence-to-consequence"
MIN_ARTICLE_CHARS = 3000  # shorter bodies are stubs that point to the publisher, not the paper
CONTRAST_TYPES = {"success", "recollection", "familiarity"}
CONTRAST_COLUMNS = ["record_id", "rater", "model", "timestamp", "eligible", "table", "contrast",
                    "contrast_type", "n", "reason", "raw"]
CONTRAST_INSTRUCTION = (
    "You read the full text of an fMRI/PET paper for a coordinate-based meta-analysis. Using the criteria "
    "above, say whether the paper is eligible and which table reports the retrieval-success contrast in "
    "healthy adults, and the sample size of that analysis. Do not list coordinates. Answer with JSON only: "
    '{"eligible": true | false, "table": "<table label>", "contrast": "<contrast as written>", '
    '"contrast_type": "success" | "recollection" | "familiarity", "n": <integer>, "reason": "<one sentence>"}'
)


def _clean(v):
    return "" if v is None or (isinstance(v, float) and math.isnan(v)) else str(v)


def build_messages(criteria, record):
    user = f"Title: {_clean(record.get('title'))}\nAbstract: {_clean(record.get('abstract')) or '(no abstract)'}"
    return [{"role": "system", "content": f"{criteria}\n\n{INSTRUCTION}"}, {"role": "user", "content": user}]


def _json(text):
    m = re.search(r"\{.*\}", text or "", re.S)
    try:
        return json.loads(m.group(0)) if m else None
    except json.JSONDecodeError:
        return None


def parse_reply(text):
    d = _json(text)
    if not isinstance(d, dict) or d.get("decision") not in DECISIONS:
        return None
    return {"decision": d["decision"], "reason": str(d.get("reason", ""))}


def parse_contrast(text):
    d = _json(text)
    if not isinstance(d, dict) or not isinstance(d.get("eligible"), bool):
        return None
    # an ineligible paper has no contrast to report, so only an eligible one must give a type and N
    if d["eligible"] and (d.get("contrast_type") not in CONTRAST_TYPES or type(d.get("n")) is not int):
        return None
    return {k: d.get(k, "") for k in ("eligible", "table", "contrast", "contrast_type", "n", "reason")}


def pdf_text(path):
    from pypdf import PdfReader
    return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)


def _ask(client, model, messages):
    resp = client.chat.completions.create(model=model, messages=messages, temperature=0)
    return resp.choices[0].message.content or ""


def screen_record(client, model, messages, parse=parse_reply):
    """One retry on an invalid reply, then 'unsure'. API/network errors propagate: a failed call
    must never be logged as a decision."""
    raw = ""
    for _ in range(2):
        raw = _ask(client, model, messages)
        parsed = parse(raw)
        if parsed is not None:
            return parsed | {"raw": raw}
    return {"decision": "unsure", "reason": "invalid reply", "raw": raw}


def run_rater(records, rater, client, model, criteria, log_path, limit=None, min_interval=0,
              clock=time.monotonic, sleep=time.sleep):
    """Screen every record not yet in log_path, appending one row per decision. Returns the count.
    min_interval (seconds) spaces requests to respect an API's per-minute quota."""
    log_path = Path(log_path)
    done = set(pd.read_csv(log_path, dtype=str).record_id) if log_path.exists() else set()
    todo = records[~records.record_id.isin(done)]
    if limit:
        todo = todo.head(limit)
    n, last = 0, None
    for rec in todo.to_dict("records"):
        if min_interval and last is not None:
            wait = min_interval - (clock() - last)
            if wait > 0:
                sleep(wait)
        last = clock()
        messages = build_messages(criteria, rec)
        out = screen_record(client, model, messages)
        row = {"record_id": rec["record_id"], "rater": rater, "model": model,
               "prompt_sha256": hashlib.sha256(messages[0]["content"].encode()).hexdigest(),
               "timestamp": datetime.datetime.now().isoformat(timespec="seconds")} | out
        pd.DataFrame([row], columns=LOG_COLUMNS).to_csv(log_path, mode="a", header=not log_path.exists(), index=False)
        n += 1
    return n


def article_text(xml):
    """Body and floating tables of a PMC article, or None when PMC holds no real body for it."""
    article = ET.fromstring(xml).find(".//article")
    body = None if article is None else article.find("body")
    if body is None:
        return None
    parts = [body] + article.findall("floats-group")
    text = "\n".join("".join(part.itertext()) for part in parts)
    return text if len(text) >= MIN_ARTICLE_CHARS else None


def pmc_text(rid):
    """Open-access full text through NCBI's API, for records with a PMID. It is read here and not saved."""
    if not rid.startswith("pmid:"):
        return None
    link = requests.get(f"{EUTILS}/elink.fcgi", params={"dbfrom": "pubmed", "db": "pmc", "linkname": "pubmed_pmc",
                                                        "id": rid[5:], "tool": EUTILS_TOOL}, timeout=60)
    link.raise_for_status()
    pmc = ET.fromstring(link.content).findtext("LinkSet/LinkSetDb/Link/Id")
    time.sleep(0.4)  # NCBI allows 3 requests a second without a key
    if not pmc:
        return None
    r = requests.get(f"{EUTILS}/efetch.fcgi", params={"db": "pmc", "id": pmc, "retmode": "xml", "tool": EUTILS_TOOL}, timeout=120)
    r.raise_for_status()
    time.sleep(0.4)
    return article_text(r.content)


def run_full_text(record_ids, pdf_dir, client, model, criteria, out_path, fetch=lambda rid: None):
    """Propose the contrast table and N for each paper with a PDF, or else with text from `fetch`; resumable.
    Returns the count."""
    out_path = Path(out_path)
    done = set(pd.read_csv(out_path, dtype=str).record_id) if out_path.exists() else set()
    n = 0
    for rid in record_ids:
        if rid in done:
            continue
        pdf = Path(pdf_dir) / f"{rid.replace(':', '_').replace('/', '_')}.pdf"
        text = pdf_text(pdf) if pdf.exists() else fetch(rid)
        if not text:
            continue
        messages = [{"role": "system", "content": f"{criteria}\n\n{CONTRAST_INSTRUCTION}"},
                    {"role": "user", "content": text}]
        out = screen_record(client, model, messages, parse=parse_contrast)
        row = {"record_id": rid, "rater": "full_text", "model": model,
               "timestamp": datetime.datetime.now().isoformat(timespec="seconds")} | out
        pd.DataFrame([row], columns=CONTRAST_COLUMNS).to_csv(out_path, mode="a", header=not out_path.exists(), index=False)
        n += 1
    return n


def merge(a, b, seed, frac):
    """Both include -> include (human verifies); both exclude -> exclude, a seeded `frac` sample
    (rounded up) to the human; anything else -> unsure (human decides)."""
    m = pd.DataFrame({"asi": a, "qwen": b})
    m["merged"] = np.where(m.asi == m.qwen, m.asi, "unsure")
    m["needs_human"] = m.merged != "exclude"
    excl = m.index[m.merged == "exclude"]
    k = math.ceil(len(excl) * frac)
    sample = pd.Series(excl).sample(n=k, random_state=seed) if k else []
    m.loc[list(sample), "needs_human"] = True
    m.index.name = "record_id"
    return m


def write_review_sheet(record_ids, records, suggestions, path, seed):
    """The author's sheet, in the human_decisions format: shuffled, with an AI suggestion per record and
    without the raters' decisions. She answers yes or no in `agree`. Never overwritten, because it holds
    her answers. Returns whether it wrote."""
    if path.exists():
        return False
    sheet = records[records.record_id.isin(record_ids)].sample(frac=1, random_state=seed)
    sheet = sheet.merge(suggestions, on="record_id", how="left")
    if sheet.ai_suggestion.isna().any():
        raise SystemExit(f"no AI suggestion for: {list(sheet.record_id[sheet.ai_suggestion.isna()])[:10]}")
    sheet = sheet.assign(stage="title_abstract", rater="author", agree="", reason="", decision="", date="")
    sheet[["record_id", "stage", "rater", "year", "doi", "title", "abstract", "ai_suggestion", "ai_confidence",
           "ai_reasoning", "agree", "reason", "decision", "date"]].to_csv(path, index=False)
    return True


def client_for(cfg):
    from openai import OpenAI
    key = os.environ.get(cfg["api_key_env"]) if cfg["api_key_env"] else "ollama"
    if not key:
        raise SystemExit(f"Set {cfg['api_key_env']}")
    return OpenAI(base_url=cfg["base_url"], api_key=key)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rq", choices=["rq1", "rq3"])
    ap.add_argument("--stage", default="title_abstract", choices=["title_abstract", "full_text"])
    ap.add_argument("--rater", choices=["asi", "gemini", "qwen"])
    ap.add_argument("--limit", type=int)
    ap.add_argument("--merge", action="store_true")
    ap.add_argument("--second-look", action="store_true")
    a = ap.parse_args()
    base = ROOT / {"rq1": "rq1_map", "rq3": "rq3_stimulation"}[a.rq]
    scr = base / "screening"
    cfg = load_config("screening")
    records = pd.read_csv(base / "search" / "records.csv", dtype=str).fillna("")
    if a.stage == "full_text":
        from tools.common import data_dir
        from tools.prisma import title_abstract_decisions
        ta = title_abstract_decisions(base)
        r = cfg["raters"][a.rater or "asi"]
        kept = list(ta.index[ta != "exclude"])[:a.limit]
        out = scr / "contrast_proposals.csv"
        n = run_full_text(kept, data_dir(a.rq, "pdfs"), client_for(r), r["model"],
                          (scr / "criteria.md").read_text(), out, fetch=pmc_text)
        record_versions(f"{a.rq}_full_text_{a.rater or 'asi'}")
        print(f"full text: {n} proposals written; the author confirms each in experiments.csv")
        no_text = sorted(set(kept) - set(pd.read_csv(out, dtype=str).record_id if out.exists() else []))
        print(f"no full text found for {len(no_text)} of {len(kept)}")
        if not a.limit:  # PRISMA counts this list, so a partial run must not replace it
            pd.DataFrame({"record_id": no_text}).to_csv(scr / "full_text_not_retrieved.csv", index=False)
        return
    if a.rater:
        r = cfg["raters"][a.rater]
        n = run_rater(records, a.rater, client_for(r), r["model"], (scr / "criteria.md").read_text(),
                      scr / f"ai_{a.rater}.csv", a.limit, min_interval=r.get("min_interval_s", 0))
        record_versions(f"{a.rq}_screen_{a.rater}")
        print(f"{a.rater}: screened {n} records")
    if a.merge:
        logs = {k: pd.read_csv(scr / f"ai_{k}.csv", dtype=str).set_index("record_id").decision for k in ("asi", "qwen")}
        missing = {k: len(set(records.record_id) - set(v.index)) for k, v in logs.items()}
        if any(missing.values()):
            raise SystemExit(f"not every record screened yet: {missing}")
        m = merge(logs["asi"].loc[records.record_id], logs["qwen"].loc[records.record_id],
                  cfg["seed"], cfg["human_exclude_sample"])
        m.to_csv(scr / "merged.csv")
        print(m.merged.value_counts().to_string(), f"\nneeds human: {int(m.needs_human.sum())}")
        if not (scr / "ai_suggestions.csv").exists():
            print("ai_suggestions.csv missing; review sheet not written")
        elif not write_review_sheet(m.index[m.needs_human], records, pd.read_csv(scr / "ai_suggestions.csv", dtype=str),
                                    scr / "human_decisions.csv", cfg["seed"]):
            print("human_decisions.csv exists; left as it is")
    if a.second_look:
        s = pd.read_csv(scr / "ai_suggestions_unseen.csv", dtype=str)
        print(s.groupby(["ai_suggestion", "ai_confidence"]).size().to_string())
        if not write_review_sheet(s.record_id[s.ai_suggestion == "include"], records, s,
                                  scr / SECOND_LOOK_SHEET, cfg["seed"]):
            print(f"{SECOND_LOOK_SHEET} exists; left as it is")


if __name__ == "__main__":
    main()
