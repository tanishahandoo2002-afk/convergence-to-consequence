"""Build and freeze the RQ1 masks (plan §8.1 step 12). All masks are binary, MNI 2 mm, on the ALE grid.

  memory.nii.gz          significant ALE clusters (cluster-level FWE)
  memory_top50.nii.gz    memory voxels at or above the median ALE value within memory (RQ2 robustness)
  control_md.nii.gz      multiple-demand parcels (Fedorenko lab, allParcels-MD-HE197) minus memory  [primary]
  control_yeo.nii.gz     Yeo 2011 7-network salience/ventral attention + control (frontoparietal) minus memory
                         [sensitivity]; from the CBIG split-component 2 mm volume and its lookup table

Once frozen, hashes in masks/FROZEN.sha256 guard every downstream stage.
CLI: python -m masks.build_masks [--refreeze]
"""
import argparse
import datetime
import hashlib
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd
import requests
from nilearn import image, plotting

from rq1_map.run_ale import RESULTS
from tools.common import ROOT, data_dir, load_config

MASKS = Path(__file__).resolve().parent
FROZEN = MASKS / "FROZEN.sha256"
CHANGELOG = ROOT / "CHANGELOG.md"
NAMES = ["memory", "memory_top50", "control_md", "control_yeo"]


def _binary(data, ref):
    return nib.Nifti1Image(np.asarray(data, dtype="uint8"), ref.affine)


def _on(img):
    return np.asarray(img.dataobj) > 0


def top_half(stat_img, mask_img):
    stat, m = np.asarray(stat_img.dataobj), _on(mask_img)
    return _binary(m & (stat >= np.median(stat[m])), mask_img)


def subtract(a_img, b_img):
    return _binary(_on(a_img) & ~_on(b_img), a_img)


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def refreeze_allowed(refreeze, frozen_path=FROZEN, changelog=CHANGELOG):
    """Raise unless masks are unfrozen, or --refreeze is given with a CHANGELOG line dated today."""
    frozen_path = Path(frozen_path)
    if frozen_path.exists():
        if not refreeze:
            raise RuntimeError(f"masks are frozen ({frozen_path}); rebuilding needs --refreeze and a dated CHANGELOG entry")
        today = datetime.date.today().isoformat()
        log = Path(changelog).read_text() if Path(changelog).exists() else ""
        if not any(line.startswith(today) for line in log.splitlines()):
            raise RuntimeError(f"--refreeze needs a CHANGELOG.md line starting with {today} explaining why")


def freeze(paths, refreeze, frozen_path=FROZEN, changelog=CHANGELOG):
    refreeze_allowed(refreeze, frozen_path, changelog)
    Path(frozen_path).write_text("".join(f"{_sha(p)}  {Path(p).name}\n" for p in paths))


def verify_frozen(frozen_path=FROZEN):
    """Names of frozen files that are missing or whose hash changed (empty list = all intact)."""
    frozen_path = Path(frozen_path)
    bad = []
    for line in frozen_path.read_text().splitlines():
        digest, name = line.split("  ", 1)
        f = frozen_path.parent / name
        if not f.exists() or _sha(f) != digest:
            bad.append(name)
    return sorted(bad)


def fetch_source(url, expected=None):
    """Download a parcel file once into $C2C_DATA/parcels; record its hash in masks/sources.csv and
    refuse to continue if it differs from the recorded (or configured) hash."""
    path = data_dir("parcels") / url.rsplit("/", 1)[-1]
    if not path.exists():
        r = requests.get(url, timeout=120)
        r.raise_for_status()
        path.write_bytes(r.content)
    digest = _sha(path)
    sources = MASKS / "sources.csv"
    known = pd.read_csv(sources, dtype=str) if sources.exists() else pd.DataFrame(columns=["file", "url", "sha256", "date"])
    expected = expected or next(iter(known.loc[known.file == path.name, "sha256"]), None)
    if expected and expected != digest:
        raise RuntimeError(f"{path.name} hash {digest} differs from the recorded {expected}")
    if path.name not in set(known.file):
        row = pd.DataFrame([[path.name, url, digest, datetime.date.today().isoformat()]], columns=known.columns)
        pd.concat([known, row]).to_csv(sources, index=False)
    return path


def yeo_label_ids(lut_text):
    """Label ids of the salience/ventral-attention and control components in the 7-network lookup table."""
    ids = []
    for line in lut_text.splitlines():
        parts = line.split()
        if len(parts) >= 2 and ("_SalVentAttn_" in parts[1] or "_Cont_" in parts[1]):
            ids.append(int(parts[0]))
    return ids


def build(cfg):
    sig = image.load_img(RESULTS / "ale_cluster_fwe_z.nii.gz")
    stat = image.load_img(RESULTS / "ale_stat.nii.gz")
    memory = _binary(_on(sig), sig)
    if not _on(memory).any():
        raise SystemExit("the ALE map has no significant cluster; there is no memory mask to build (report this)")
    p = cfg["parcels"]
    md = image.resample_to_img(image.load_img(fetch_source(p["md_url"], p.get("md_sha256"))), sig,
                               interpolation="nearest", force_resample=True, copy_header=True)
    yeo = image.resample_to_img(image.load_img(fetch_source(p["yeo_url"])), sig,
                                interpolation="nearest", force_resample=True, copy_header=True)
    ids = yeo_label_ids(fetch_source(p["yeo_lut_url"]).read_text())
    yeo_net = _binary(np.isin(np.rint(np.asarray(yeo.dataobj)), ids), sig)
    return {"memory": memory, "memory_top50": top_half(stat, memory),
            "control_md": subtract(_binary(_on(md), sig), memory), "control_yeo": subtract(yeo_net, memory)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refreeze", action="store_true")
    a = ap.parse_args()
    refreeze_allowed(a.refreeze, FROZEN, CHANGELOG)  # before anything is overwritten
    masks = build(load_config("rq1"))
    (MASKS / "qc").mkdir(exist_ok=True)
    paths = []
    for name in NAMES:
        p = MASKS / f"{name}.nii.gz"
        masks[name].to_filename(p)
        paths.append(p)
        plotting.plot_roi(masks[name], title=name, display_mode="ortho", draw_cross=False).savefig(MASKS / "qc" / f"{name}.png")
        print(f"{name}: {int(_on(masks[name]).sum())} voxels")
    freeze(paths, a.refreeze)
    print(f"frozen: {FROZEN}. Review masks/qc/*.png, then add a masks_frozen sign-off.")


if __name__ == "__main__":
    main()
