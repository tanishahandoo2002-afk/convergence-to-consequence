"""Mask check (plan §8.1 step 12): binary, non-empty, inside the brain, memory and control disjoint,
hashes intact, freeze signed off by the author.
CLI: python -m checks.check_masks
"""
import sys
from pathlib import Path

import numpy as np
from nilearn import image
from nilearn.datasets import load_mni152_brain_mask

from checks.signoffs import SIGNOFFS, has_signoff
from masks.build_masks import MASKS, NAMES, verify_frozen

MIN_INSIDE = 0.95  # parcels from other templates may graze the brain edge by a voxel


def check(masks_dir=MASKS, signoff_path=SIGNOFFS):
    masks_dir = Path(masks_dir)
    absent = [n for n in NAMES if not (masks_dir / f"{n}.nii.gz").exists()]
    if absent:
        return [f"missing masks: {absent} (python -m masks.build_masks)"]
    errors, data = [], {}
    first = image.load_img(masks_dir / f"{NAMES[0]}.nii.gz")
    brain = np.asarray(image.resample_to_img(load_mni152_brain_mask(resolution=2), first, interpolation="nearest",
                                             force_resample=True, copy_header=True).dataobj) > 0
    for n in NAMES:
        d = np.asarray(image.load_img(masks_dir / f"{n}.nii.gz").dataobj)
        if not set(np.unique(d)) <= {0, 1}:
            errors.append(f"{n} is not binary")
        on = d > 0
        if not on.any():
            errors.append(f"{n} is empty")
        elif (on & brain).sum() / on.sum() < MIN_INSIDE:
            errors.append(f"{n}: only {(on & brain).sum() / on.sum():.0%} of voxels inside the MNI brain mask")
        data[n] = on
    for ctrl in ("control_md", "control_yeo"):
        if (data["memory"] & data[ctrl]).any():
            errors.append(f"memory and {ctrl} overlap in {int((data['memory'] & data[ctrl]).sum())} voxels")
    if not (masks_dir / "FROZEN.sha256").exists():
        errors.append("masks are not frozen (FROZEN.sha256 missing)")
    else:
        changed = verify_frozen(masks_dir / "FROZEN.sha256")
        if changed:
            errors.append(f"masks changed since freezing: {changed}")
    if not has_signoff("masks_frozen", "all", path=signoff_path):
        errors.append("no masks_frozen sign-off: review masks/qc/*.png, then add a row (step masks_frozen, item all)")
    return errors


def main():
    errors = check()
    for e in errors:
        print("FAIL:", e)
    if errors:
        sys.exit(1)
    print("mask check OK")


if __name__ == "__main__":
    main()
