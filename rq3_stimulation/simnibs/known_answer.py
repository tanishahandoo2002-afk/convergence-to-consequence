"""Known-answer checks for the field model (design §10), run with SimNIBS's Python on Ernie:
- linearity: the same F3-Fp2 layout at 2 mA gives twice the 1-mA field in both masks (within 1%);
- reference: F3-Fp2 at 1 mA, 35 cm2 pads, gives a 99th-percentile grey-matter field of 0.1-0.6 V/m, the range of
  published modelling and intracranial recordings per mA of conventional tDCS (e.g. Huang et al. 2017, eLife).
  simnibs_python -m rq3_stimulation.simnibs.known_answer
"""
import os
import sys
from pathlib import Path

import nibabel as nib
import numpy as np

from rq3_stimulation.simnibs.run_montages import HEADS, MASKS, frozen_ok, mask_mean, simulate

LOW, HIGH = 0.1, 0.6


def grey_matter_p99(out):
    """99th percentile of the field magnitude over grey-matter elements of the result mesh."""
    from simnibs import mesh_io
    msh = mesh_io.read_msh(next(out.glob("*.msh")))
    gm = msh.crop_mesh(tags=[2])
    return float(np.percentile(gm.field["magnE"].value, 99))


def main():
    frozen_ok()
    data = Path(os.environ["C2C_DATA"])
    m2m = data / HEADS["ernie"]
    runs = data / "rq3" / "simnibs" / "known_answer"
    f3fp2 = ([("eeg", "F3")], [("eeg", "Fp2")], 35.0)
    one = simulate(*f3fp2, m2m, runs / "f3fp2_1mA")
    p99 = grey_matter_p99(runs / "f3fp2_1mA")
    # a second run at 2 mA: scale the electrode currents by building the same layout twice over
    from simnibs import run_simnibs, sim_struct
    s = sim_struct.SESSION()
    s.subpath, s.pathfem, s.map_to_MNI, s.fields, s.open_in_gmsh = str(m2m), str(runs / "f3fp2_2mA"), True, "e", False
    tdcs = s.add_tdcslist()
    tdcs.currents = [2e-3, -2e-3]
    for ch, name in ((1, "F3"), (2, "Fp2")):
        el = tdcs.add_electrode()
        el.channelnr, el.shape, el.dimensions, el.thickness, el.centre = ch, "rect", [50.0, 70.0], 5, name
    run_simnibs(s)
    two = next((runs / "f3fp2_2mA" / "mni_volumes").glob("*magnE*.nii.gz"))
    failures = []
    for name, mask in MASKS.items():
        a, b = mask_mean(one, mask), mask_mean(two, mask)
        print(f"{name}: 1 mA {a:.4f} V/m, 2 mA {b:.4f} V/m, ratio {b / a:.4f}")
        if abs(b / a - 2) > 0.02:
            failures.append(f"linearity fails in {name}: ratio {b / a:.4f}")
    print(f"reference F3-Fp2 1 mA: 99th percentile grey-matter field {p99:.3f} V/m (expected {LOW}-{HIGH})")
    if not LOW <= p99 <= HIGH:
        failures.append(f"reference field {p99:.3f} V/m outside {LOW}-{HIGH}")
    for f in failures:
        print("FAIL:", f)
    print("known-answer checks OK" if not failures else "")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
