"""AI-assisted screening with two independent raters (plan §8.1 step 4, §8.6).

Both raters use the OpenAI-compatible chat API (Gemini and Ollama), temperature 0.
Every decision is logged with model, prompt hash, timestamp and the raw reply.
CLI:
  python -m tools.screen rq1 --stage title_abstract --rater qwen [--limit 5]
  python -m tools.screen rq1 --stage title_abstract --merge
"""
import argparse
import datetime
import hashlib
import json
import math
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd

from tools.common import ROOT, load_config, record_versions

DECISIONS = {"include", "exclude", "unsure"}
LOG_COLUMNS = ["record_id", "rater", "model", "prompt_sha256", "timestamp", "decision", "reason", "raw"]
INSTRUCTION = (
    "You screen records for a systematic review. Apply the eligibility criteria above to the record "
    "the user gives you. Answer with JSON only, exactly in this form: "
    '{"decision": "include" | "exclude" | "unsure", "reason": "<one sentence>"}'
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


def run_rater(records, rater, client, model, criteria, log_path, limit=None):
    """Screen every record not yet in log_path, appending one row per decision. Returns the count."""
    log_path = Path(log_path)
    done = set(pd.read_csv(log_path, dtype=str).record_id) if log_path.exists() else set()
    todo = records[~records.record_id.isin(done)]
    if limit:
        todo = todo.head(limit)
    n = 0
    for rec in todo.to_dict("records"):
        messages = build_messages(criteria, rec)
        out = screen_record(client, model, messages)
        row = {"record_id": rec["record_id"], "rater": rater, "model": model,
               "prompt_sha256": hashlib.sha256(messages[0]["content"].encode()).hexdigest(),
               "timestamp": datetime.datetime.now().isoformat(timespec="seconds")} | out
        pd.DataFrame([row], columns=LOG_COLUMNS).to_csv(log_path, mode="a", header=not log_path.exists(), index=False)
        n += 1
    return n


def merge(a, b, seed, frac):
    """Both include -> include (human verifies); both exclude -> exclude, a seeded `frac` sample
    (rounded up) to the human; anything else -> unsure (human decides)."""
    m = pd.DataFrame({"gemini": a, "qwen": b})
    m["merged"] = np.where(m.gemini == m.qwen, m.gemini, "unsure")
    m["needs_human"] = m.merged != "exclude"
    excl = m.index[m.merged == "exclude"]
    k = math.ceil(len(excl) * frac)
    sample = pd.Series(excl).sample(n=k, random_state=seed) if k else []
    m.loc[list(sample), "needs_human"] = True
    m.index.name = "record_id"
    return m


def client_for(cfg):
    from openai import OpenAI
    key = os.environ.get(cfg["api_key_env"]) if cfg["api_key_env"] else "ollama"
    if not key:
        raise SystemExit(f"Set {cfg['api_key_env']}")
    return OpenAI(base_url=cfg["base_url"], api_key=key)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rq", choices=["rq1", "rq3"])
    ap.add_argument("--stage", default="title_abstract", choices=["title_abstract"])
    ap.add_argument("--rater", choices=["gemini", "qwen"])
    ap.add_argument("--limit", type=int)
    ap.add_argument("--merge", action="store_true")
    a = ap.parse_args()
    base = ROOT / {"rq1": "rq1_map", "rq3": "rq3_stimulation"}[a.rq]
    scr = base / "screening"
    cfg = load_config("screening")
    records = pd.read_csv(base / "search" / "records.csv", dtype=str).fillna("")
    if a.rater:
        r = cfg["raters"][a.rater]
        n = run_rater(records, a.rater, client_for(r), r["model"], (scr / "criteria.md").read_text(),
                      scr / f"ai_{a.rater}.csv", a.limit)
        record_versions(f"{a.rq}_screen_{a.rater}")
        print(f"{a.rater}: screened {n} records")
    if a.merge:
        logs = {k: pd.read_csv(scr / f"ai_{k}.csv", dtype=str).set_index("record_id").decision for k in ("gemini", "qwen")}
        missing = {k: len(set(records.record_id) - set(v.index)) for k, v in logs.items()}
        if any(missing.values()):
            raise SystemExit(f"not every record screened yet: {missing}")
        m = merge(logs["gemini"].loc[records.record_id], logs["qwen"].loc[records.record_id],
                  cfg["seed"], cfg["human_exclude_sample"])
        m.to_csv(scr / "merged.csv")
        print(m.merged.value_counts().to_string(), f"\nneeds human: {int(m.needs_human.sum())}")


if __name__ == "__main__":
    main()
