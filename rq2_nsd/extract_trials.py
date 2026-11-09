"""NSD single-trial extraction, one session at a time (plan §8.2 step 4, spec §9).

Each session's betas are streamed from the public NSD bucket into memory (never written to disk),
z-scored per voxel within the session on mask voxels only, and averaged within each frozen mask.
Only the trial table is kept. Runs only after the NSD Data Access Agreement form is submitted.
CLI: python -m rq2_nsd.extract_trials --beta b3 [--subjects 1 2] [--pilot]
"""
import argparse
import datetime
import gzip
import io
import os
import sys
import time
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd
import requests
import scipy.io

from checks.check_rq2 import check_behaviour
from masks.build_masks import verify_frozen
from rq2_nsd.labels import label_trials
from tools.common import data_dir, load_config, record_versions

HIDDEN_IN_PILOT = ["is_old", "response_old", "outcome", "rt", "log_delay_s", "viewing", "memory_recent"]
DESIGN = "nsddata/experiments/nsd/nsd_expdesign.mat"
SCALE = 300  # NSD betas are stored as int16 percent signal change x 300


DROPPED = (requests.ConnectionError, requests.Timeout, requests.exceptions.ChunkedEncodingError)


def fetch(url, retries=3, wait_s=30):
    """GET a whole file. A dropped connection or a 5xx reply is retried, with a longer wait each time: one
    dropped download stopped the b2 run partway (CHANGELOG 2026-11-10). A 4xx reply fails at once."""
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, timeout=600)
            if r.status_code == 200:
                return r.content
            problem = f"status {r.status_code}"
            if r.status_code < 500:
                raise RuntimeError(f"GET {url} returned {r.status_code}")
        except DROPPED as e:
            problem = type(e).__name__
        if attempt == retries:
            raise RuntimeError(f"GET {url} failed {retries + 1} times, last with {problem}")
        print(f"retry {attempt + 1}/{retries} in {wait_s * (attempt + 1)} s after {problem}: {url}", flush=True)
        time.sleep(wait_s * (attempt + 1))


def cached(key, base, cache):
    """Small NSD support file, fetched once into the cache folder (betas are never cached)."""
    path = cache / key
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        part = path.with_name(path.name + ".part")
        part.write_bytes(fetch(base + key))
        part.replace(path)
    return path


def expected_images(design, subject, n_trials):
    """1-based 73k ids in viewing order for one subject: subjectim(subject, masterordering), per the Data Manual."""
    order = design["masterordering"].ravel()[:n_trials].astype(int) - 1
    return design["subjectim"][subject - 1, order]


def decode_betas(gz_bytes):
    return nib.Nifti1Image.from_bytes(gzip.decompress(gz_bytes))


def mask_means(betas_img, masks):
    data = np.asarray(betas_img.dataobj)
    out = {}
    for name, m in masks.items():
        x = data[m].astype(np.float32) / SCALE                      # voxels x trials
        sd = x.std(axis=1, keepdims=True)
        with np.errstate(invalid="ignore", divide="ignore"):
            z = (x - x.mean(axis=1, keepdims=True)) / sd
        z[(sd == 0).ravel()] = np.nan                               # constant voxels carry no signal
        finite = np.isfinite(z)
        n = finite.sum(axis=0)
        with np.errstate(invalid="ignore"):
            out[f"sig_{name}"] = np.where(n > 0, np.where(finite, z, 0).sum(axis=0) / n, np.nan)
        out[f"n_vox_{name}"] = n
    return pd.DataFrame(out)


def beta_key(subject, session, beta, cfg):
    return (f"nsddata_betas/ppdata/subj{subject:02d}/func1pt8mm/{cfg['beta_dirs'][beta]}/"
            f"betas_session{session:02d}.nii.gz")


def extract_session(subject, session, labels, masks, beta, cfg, fetch=fetch, pilot=False):
    n = cfg["trials_per_session"]
    lab = labels[labels.session == session].reset_index(drop=True)
    if len(lab) != n:
        raise ValueError(f"subject {subject} session {session}: {len(lab)} label rows, expected {n}")
    img = decode_betas(fetch(cfg["s3_base"] + beta_key(subject, session, beta, cfg)))
    if img.shape[-1] != n:
        raise ValueError(f"subject {subject} session {session}: {img.shape[-1]} beta volumes, expected {n}")
    out = pd.concat([lab, mask_means(img, masks)], axis=1).assign(subject=subject, beta=beta)
    return out.drop(columns=HIDDEN_IN_PILOT) if pilot else out


def done_sessions(manifest):
    if not Path(manifest).exists():
        return set()
    m = pd.read_csv(manifest)
    return set(zip(m.subject, m.session))


def write_session(df, out_dir, subject, session, manifest, key):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    final = out_dir / f"subj{subject:02d}_sess{session:02d}.csv"
    tmp = final.with_suffix(".csv.tmp")
    df.to_csv(tmp, index=False)
    os.replace(tmp, final)
    row = pd.DataFrame([[subject, session, key, len(df), datetime.datetime.now().isoformat(timespec="seconds")]],
                       columns=["subject", "session", "key", "n_trials", "timestamp"])
    row.to_csv(manifest, mode="a", header=not Path(manifest).exists(), index=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--beta", default="b3", choices=["b3", "b2"])
    ap.add_argument("--subjects", type=int, nargs="+")
    ap.add_argument("--pilot", action="store_true")
    a = ap.parse_args()
    cfg = load_config("rq2")
    changed = verify_frozen()
    if changed:
        sys.exit(f"frozen masks changed or missing: {changed}")
    # Spec §9: image order is checked against the experimental design before any session is extracted.
    design = scipy.io.loadmat(cached(DESIGN, cfg["s3_base"], data_dir("rq2", "nsd_support")))
    subjects = [cfg["pilot"]["subject"]] if a.pilot else (a.subjects or cfg["subjects"])
    out_dir = data_dir("rq2", "pilot" if a.pilot else a.beta)
    manifest = out_dir / "manifest.csv"
    done = done_sessions(manifest)
    for s in subjects:
        native = data_dir("rq2", "native_masks")
        paths = {m: native / f"subj{s:02d}_{m}.nii.gz" for m in cfg["masks"]}
        if not all(p.exists() for p in paths.values()):
            sys.exit(f"native masks for subject {s} missing in {native} (built by the nsdcode step)")
        masks = {m: np.asarray(nib.load(p).dataobj) > 0 for m, p in paths.items()}
        behav = pd.read_csv(io.BytesIO(fetch(cfg["s3_base"] + f"nsddata/ppdata/subj{s:02d}/behav/responses.tsv")), sep="\t")
        problems = check_behaviour(behav, cfg["behav_columns"], expected_images(design, s, len(behav)),
                                   trials_per_session=cfg["trials_per_session"])
        if problems:
            sys.exit(f"subject {s} responses.tsv fails the behaviour check:\n  " + "\n  ".join(problems))
        labels = label_trials(behav, cfg["behav_columns"])
        sessions = cfg["pilot"]["sessions"] if a.pilot else sorted(labels.session.unique())
        for ss in sessions:
            if (s, ss) in done:
                continue
            df = extract_session(s, int(ss), labels, masks, a.beta, cfg, pilot=a.pilot)
            write_session(df, out_dir, s, int(ss), manifest, beta_key(s, int(ss), a.beta, cfg))
            print(f"subject {s} session {ss}: {len(df)} trials")
    record_versions("rq2_pilot" if a.pilot else f"rq2_extract_{a.beta}")


if __name__ == "__main__":
    main()
