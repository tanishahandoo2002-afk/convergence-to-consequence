"""RQ2 check (plan §8.2, §12): native masks, trial counts per session and a data-quality report.
CLI: python -m checks.check_rq2 [--dir b3|b2|pilot]   -> rq2_nsd/results/data_quality_<dir>.csv (counts only)
     python -m checks.check_rq2 --native              -> native masks (design §9)
"""
import argparse
import sys
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd

from scipy.stats import spearmanr

from checks.check_masks import DISJOINT
from checks.signoffs import SIGNOFFS, missing
from masks.build_masks import verify_frozen
from rq2_nsd.labels import label_trials
from tools.common import ROOT, data_dir, load_config


def check_behaviour(behav, cols, expected_images=None, trials_per_session=750):
    """responses.tsv sanity: configured columns exist, 750 trials per session, image order matches the
    experimental design, is_old agrees with viewing history, delay agrees with NSD's memory_recent."""
    absent = [v for v in cols.values() if v not in behav.columns]
    if absent:
        return [f"responses.tsv lacks configured columns {absent}; real columns: {list(behav.columns)} "
                f"(fix behav_columns in config/rq2.yaml)"]
    errors = []
    lab = label_trials(behav, cols)
    for ss, n in lab.groupby("session").size().items():
        if n != trials_per_session:
            errors.append(f"session {ss}: {n} trials, expected {trials_per_session}")
    if expected_images is not None:
        diff = (lab.image.to_numpy() != pd.Series(expected_images).to_numpy())
        if diff.any():
            r = lab[diff].iloc[0]
            errors.append(f"image order differs from the design at session {r.session} run {r.run} trial {r.trial}")
    wrong_old = lab.is_old.astype(int) != (lab.viewing > 1).astype(int)
    if wrong_old.any():
        errors.append(f"is_old disagrees with viewing history on {int(wrong_old.sum())} trials")
    prev_session = lab.groupby("image").session.shift()
    within = lab[(prev_session == lab.session) & lab.log_delay_s.notna()]
    if len(within) >= 10:
        rho = spearmanr(within.log_delay_s, within.memory_recent).statistic
        if not rho >= 0.9:
            errors.append(f"computed delay and memory_recent disagree within sessions (Spearman rho = {rho:.2f})")
    return errors


def check_native(native_dir, cfg, signoffs=SIGNOFFS):
    """Frozen hashes match; every native mask exists and is non-empty; memory and control stay disjoint;
    the author has signed off each participant's overlay (step rq2_native_masks, item subjNN)."""
    errors = []
    changed = verify_frozen()
    if changed:
        errors.append(f"frozen masks changed or missing: {changed}")
    for s in cfg["subjects"]:
        on = {}
        for m in cfg["masks"]:
            p = Path(native_dir) / f"subj{s:02d}_{m}.nii.gz"
            if not p.exists():
                errors.append(f"{p.name} missing")
                continue
            on[m] = np.asarray(nib.load(p).dataobj) > 0
            if not on[m].any():
                errors.append(f"{p.name} is empty")
        for a, b in DISJOINT:
            if a in on and b in on and (on[a] & on[b]).any():
                errors.append(f"subject {s}: {a} and {b} overlap in {int((on[a] & on[b]).sum())} voxels")
    unsigned = missing("rq2_native_masks", [f"subj{s:02d}" for s in cfg["subjects"]], signoffs)
    if unsigned:
        errors.append(f"overlays not signed off (step rq2_native_masks): {unsigned}")
    return errors


def check_tables(out_dir, cfg):
    errors, rows = [], []
    for f in sorted(Path(out_dir).glob("subj*_sess*.csv")):
        df = pd.read_csv(f)
        if len(df) != cfg["trials_per_session"]:
            errors.append(f"{f.stem}: {len(df)} trials, expected {cfg['trials_per_session']}")
        sig = df.filter(like="sig_")
        rows.append({"file": f.name, "n_trials": len(df),
                     "n_missing_response": int(df.outcome.isna().sum()) if "outcome" in df else None,
                     "n_nan_signal": int(sig.isna().any(axis=1).sum()),
                     "n_extreme_signal": int((sig.abs() > cfg["extreme_z"]).any(axis=1).sum())})
    if not rows:
        errors.append(f"no session tables in {out_dir}")
    return errors, pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="b3", choices=["b3", "b2", "pilot"])
    ap.add_argument("--native", action="store_true")
    a = ap.parse_args()
    if a.native:
        errors = check_native(data_dir("rq2", "native_masks"), load_config("rq2"))
        for e in errors:
            print("FAIL:", e)
        if errors:
            sys.exit(1)
        print("RQ2 native-mask check OK")
        return
    errors, q = check_tables(data_dir("rq2", a.dir), load_config("rq2"))
    out = ROOT / "rq2_nsd" / "results"
    out.mkdir(parents=True, exist_ok=True)
    q.to_csv(out / f"data_quality_{a.dir}.csv", index=False)
    for e in errors:
        print("FAIL:", e)
    if errors:
        sys.exit(1)
    print(f"RQ2 check OK: {len(q)} sessions; data-quality report in {out}")


if __name__ == "__main__":
    main()
