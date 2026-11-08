"""Frozen MNI masks into each NSD participant's func1pt8mm space, nearest neighbour (design §9).

The arithmetic is nsdcode's volume-to-volume case (transform_data, casenum 1): MNI-to-func1pt8.nii.gz holds, for
every func1pt8mm voxel, 1-based voxel coordinates into NSD's 1-mm MNI template, and 9999 where there is none.
nsdcode itself is not installed: its only release pins scikit-learn 0.23.2 and nibabel 3.1.0, which this Python
cannot use (CHANGELOG 2026-11-08). The output was compared with nsdcode's own code on the real files.
Support files (transform, template, mean EPI, hemisphere ROIs) are cached in $C2C_DATA/rq2/nsd_support.
CLI: python -m rq2_nsd.to_native [--subjects 1 2]
"""
import argparse
import sys

import nibabel as nib
import numpy as np
from nilearn.image import resample_to_img

from masks.build_masks import verify_frozen
from rq2_nsd.extract_trials import fetch
from tools.common import ROOT, data_dir, load_config

OUTSIDE = 9999
TEMPLATE = "nsddata/templates/MNI152_T1_1mm.nii.gz"


def support_keys(subject):
    p = f"nsddata/ppdata/subj{subject:02d}"
    return {"transform": f"{p}/transforms/MNI-to-func1pt8.nii.gz", "mean": f"{p}/func1pt8mm/mean.nii.gz",
            "lh": f"{p}/func1pt8mm/roi/lh.HCP_MMP1.nii.gz", "rh": f"{p}/func1pt8mm/roi/rh.HCP_MMP1.nii.gz"}


def cached(key, base, cache):
    path = cache / key
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        part = path.with_name(path.name + ".part")
        part.write_bytes(fetch(base + key))
        part.replace(path)
    return path


def to_template(mask_img, template_img):
    """A frozen 2-mm mask on NSD's 1-mm MNI template grid, matched by world coordinates."""
    return np.asarray(resample_to_img(mask_img, template_img, interpolation="nearest").dataobj) > 0


def map_volume(vol, transform):
    """`vol` (on the MNI template grid) read at each func1pt8mm voxel; 0 where the transform has no source."""
    inside = np.all(np.isfinite(transform) & (transform != OUTSIDE), axis=-1)
    # Half rounds up, as scipy's order-0 map_coordinates does in nsdcode; np.rint would round half to even.
    idx = np.floor(np.where(inside[..., None], transform, 1) - 0.5).astype(int)
    inside &= np.all((idx >= 0) & (idx < np.array(vol.shape)), axis=-1)
    idx[~inside] = 0
    return np.where(inside, vol[idx[..., 0], idx[..., 1], idx[..., 2]], 0)


def left_share(template_img, transform, lh, rh):
    """Share of the mapped left-MNI half that lands in NSD's own left-hemisphere ROI rather than the right one.
    Near 1 means left stays left; a left-right flip in the mapping would give near 0."""
    aff = template_img.affine
    if np.count_nonzero(aff[:3, :3] - np.diag(np.diag(aff[:3, :3]))):
        raise ValueError("template affine is rotated; the x coordinate needs the full affine")
    x = aff[0, 0] * np.arange(template_img.shape[0]) + aff[0, 3]
    left = np.broadcast_to((x < -5)[:, None, None], template_img.shape[:3])
    native_left = map_volume(left, transform) > 0
    n_lh, n_rh = int((native_left & (lh > 0)).sum()), int((native_left & (rh > 0)).sum())
    return n_lh / (n_lh + n_rh)


def overlay(mean_img, native, png):
    from nilearn import plotting
    d = plotting.plot_anat(mean_img, display_mode="z", cut_coords=8, draw_cross=False, annotate=False)
    for name, colour in (("memory", "red"), ("control_md", "deepskyblue")):
        d.add_contours(native[name], levels=[0.5], colors=colour, linewidths=0.8)
    d.savefig(str(png), dpi=150)
    d.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subjects", type=int, nargs="+")
    a = ap.parse_args()
    cfg = load_config("rq2")
    changed = verify_frozen()
    if changed:
        sys.exit(f"frozen masks changed or missing: {changed}")
    out, cache, qc = data_dir("rq2", "native_masks"), data_dir("rq2", "nsd_support"), data_dir("rq2", "native_masks", "qc")
    template = nib.load(cached(TEMPLATE, cfg["s3_base"], cache))
    mni = {m: to_template(nib.load(ROOT / "masks" / f"{m}.nii.gz"), template) for m in cfg["masks"]}
    for s in a.subjects or cfg["subjects"]:
        files = {k: cached(key, cfg["s3_base"], cache) for k, key in support_keys(s).items()}
        transform = nib.load(files["transform"]).get_fdata()
        mean = nib.load(files["mean"])
        if transform.shape[:3] != mean.shape[:3]:
            sys.exit(f"subject {s}: transform grid {transform.shape[:3]} differs from mean EPI {mean.shape[:3]}")
        native = {}
        for m, vol in mni.items():
            data = map_volume(vol, transform).astype(np.uint8)
            native[m] = nib.Nifti1Image(data, mean.affine)
            nib.save(native[m], out / f"subj{s:02d}_{m}.nii.gz")
            print(f"subject {s} {m}: {int(data.sum())} native voxels")
        share = left_share(template, transform, np.asarray(nib.load(files["lh"]).dataobj),
                           np.asarray(nib.load(files["rh"]).dataobj))
        print(f"subject {s}: {share:.3f} of the left-MNI half lands in the left-hemisphere ROI")
        overlay(mean, native, qc / f"subj{s:02d}_overlay.png")


if __name__ == "__main__":
    main()
