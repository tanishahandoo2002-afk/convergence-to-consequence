"""Electric field of each RQ3 montage in the frozen masks (design §10).

Each distinct electrode layout is simulated once at 1 mA on a head model; the field is linear in the current, so a
montage's field is the 1-mA field times its current (tACS: peak amplitude). The field magnitude is mapped to MNI and
averaged inside each frozen mask. Montages missing a position or current get no value and a note.
Run with SimNIBS's Python:
  simnibs_python -m rq3_stimulation.simnibs.run_montages ernie          # all montages
  simnibs_python -m rq3_stimulation.simnibs.run_montages older --clinical-only
"""
import argparse
import csv
import hashlib
import math
import os
import re
import shutil
import sys
from pathlib import Path

import nibabel as nib
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SHEETS = ROOT / "rq3_stimulation"
FIELDS = SHEETS / "simnibs" / "fields.csv"
MASKS = {"field_map": ROOT / "masks" / "memory.nii.gz", "field_control": ROOT / "masks" / "control_md.nii.gz"}
HEADS = {"ernie": "rq3/simnibs/m2m_ernie", "older": "rq3/simnibs/m2m_OAS2_0181"}
# Off-head returns sit at the nearest point the head model has (team decision, CHANGELOG 2026-11-08): cheek and neck
# where they are; shoulder, deltoid, arm and wrist at the lowest lateral neck point. MNI millimetres, x positive = right.
OFF_HEAD = {"cheek": (60, 25, -45), "neck": (45, -45, -85), "shoulder": (60, -30, -95), "deltoid": (60, -30, -95),
            "arm": (60, -30, -95), "wrist": (60, -30, -95)}
FIELD_COLUMNS = ["montage_id", "head_model", "field_map", "field_control", "note"]


def frozen_ok():
    """Every mask used here must match its frozen hash."""
    frozen = dict(line.split()[::-1] for line in (ROOT / "masks" / "FROZEN.sha256").read_text().splitlines() if line.strip())
    for path in MASKS.values():
        if hashlib.sha256(path.read_bytes()).hexdigest() != frozen[path.name]:
            raise SystemExit(f"{path.name} does not match FROZEN.sha256")


def site(token, eeg_names):
    """('eeg', name) for a 10-10 position, ('mni', xyz) for an off-head site, or None if unknown."""
    token = token.strip()
    if token in eeg_names:
        return "eeg", token
    for word, (x, y, z) in OFF_HEAD.items():
        if word in token.lower():
            side = -1 if "left" in token.lower() else 1
            return "mni", (side * x, y, z)
    return None


def shape(area):
    """Electrode size from its area: small ones are discs; 35 and 42.3 cm2 are the usual rectangles; else square."""
    if area < 5:
        return "ellipse", [2 * math.sqrt(area / math.pi) * 10] * 2
    if abs(area - 35) < 0.5:
        return "rect", [50.0, 70.0]
    if abs(area - 42.3) < 0.5:
        return "rect", [47.0, 90.0]
    side = math.sqrt(area) * 10
    return "rect", [side, side]


def layout(m, eeg_names):
    """(anodes, cathodes, area) or a reason the montage cannot be simulated. Extra 10-10 names in
    other_electrodes are further anodes (e.g. two active sites against one return)."""
    anodes = [t for t in m["anode"].split(",") if t.strip()]
    cathodes = [t for t in m["cathode"].split(",") if t.strip()]
    anodes += [t for t in re.split(r"[,;]", m["other_electrodes"]) if t.strip() in eeg_names]
    if not anodes or not cathodes:
        return "electrode position missing"
    if not m["current_mA"]:
        return "current missing"
    sites_a, sites_c = [site(t, eeg_names) for t in anodes], [site(t, eeg_names) for t in cathodes]
    if None in sites_a + sites_c:
        return f"unknown electrode site in {m['anode']!r} / {m['cathode']!r}"
    area = float(m["size_cm2"]) if m["size_cm2"] else 25.0  # ponytail: unknown size taken as 5 x 5 cm, the commonest
    return sites_a, sites_c, area


def simulate(sites_a, sites_c, area, m2m, out):
    """1 mA split evenly over anodes and over cathodes; returns the MNI magnE volume path."""
    from simnibs import run_simnibs, sim_struct
    from simnibs.utils.transformations import mni2subject_coords
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    s = sim_struct.SESSION()
    s.subpath, s.pathfem, s.map_to_MNI, s.fields, s.open_in_gmsh = str(m2m), str(out), True, "e", False
    tdcs = s.add_tdcslist()
    electrodes = [(p, 1e-3 / len(sites_a)) for p in sites_a] + [(p, -1e-3 / len(sites_c)) for p in sites_c]
    tdcs.currents = [c for _, c in electrodes]
    form, dims = shape(area)
    for channel, ((kind, where), _) in enumerate(electrodes, 1):
        el = tdcs.add_electrode()
        el.channelnr, el.shape, el.dimensions, el.thickness = channel, form, dims, 5
        el.centre = where if kind == "eeg" else list(mni2subject_coords(where, str(m2m)))
    run_simnibs(s)
    return next((out / "mni_volumes").glob("*magnE*.nii.gz"))


def mask_mean(field_path, mask_path):
    """Mean field magnitude over mask voxels, read from the field volume by nearest voxel."""
    field, mask = nib.load(field_path), nib.load(mask_path)
    ijk = np.argwhere(mask.get_fdata() > 0)
    xyz = nib.affines.apply_affine(mask.affine, ijk)
    vox = np.rint(nib.affines.apply_affine(np.linalg.inv(field.affine), xyz)).astype(int)
    data = np.squeeze(field.get_fdata())
    inside = np.all((vox >= 0) & (vox < data.shape[:3]), axis=1)
    return float(data[tuple(vox[inside].T)].mean())


def key(sites_a, sites_c, area):
    return hashlib.sha1(repr((sites_a, sites_c, round(area, 2))).encode()).hexdigest()[:10]


def run(head, clinical_only):
    frozen_ok()
    data = Path(os.environ["C2C_DATA"])
    m2m = data / HEADS[head]
    cap = m2m / "eeg_positions" / "EEG10-10_UI_Jurak_2007.csv"
    eeg_names = {row[4] for row in csv.reader(cap.open()) if len(row) > 4}
    montages = list(csv.DictReader((SHEETS / "montages.csv").open()))
    if clinical_only:
        clinical = {r["montage_id"] for r in csv.DictReader((SHEETS / "effects.csv").open()) if r["population"] != "healthy"}
        montages = [m for m in montages if m["montage_id"] in clinical]
    runs = data / "rq3" / "simnibs" / f"runs_{head}"
    rows, cache = [], {}
    for m in montages:
        plan = layout(m, eeg_names)
        if isinstance(plan, str):
            rows.append({"montage_id": m["montage_id"], "head_model": head, "field_map": "", "field_control": "", "note": plan})
            continue
        k = key(*plan)
        if k not in cache:
            out = runs / k
            vol = next((out / "mni_volumes").glob("*magnE*.nii.gz"), None) if out.exists() else None
            if vol is None:
                shutil.rmtree(out, ignore_errors=True)
                vol = simulate(*plan, m2m, out)
                for msh in out.glob("*.msh"):  # meshes are large; the MNI volume is all the analysis needs
                    msh.unlink()
            cache[k] = {name: mask_mean(vol, path) for name, path in MASKS.items()}
        current = float(m["current_mA"])
        off = [p for p in plan[0] + plan[1] if p[0] == "mni"]
        rows.append({"montage_id": m["montage_id"], "head_model": head, "note": "off-head return placed on the model" if off else "",
                     **{name: round(v * current, 5) for name, v in cache[k].items()}})
    return rows


def write(rows, head):
    old = [r for r in csv.DictReader(FIELDS.open())] if FIELDS.exists() else []
    keep = [r for r in old if r["head_model"] != head]
    with FIELDS.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELD_COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(keep + rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("head", choices=sorted(HEADS))
    ap.add_argument("--clinical-only", action="store_true")
    a = ap.parse_args()
    rows = run(a.head, a.clinical_only)
    write(rows, a.head)
    done = [r for r in rows if r["field_map"] != ""]
    print(f"{a.head}: {len(done)} of {len(rows)} montages have fields; {len(rows) - len(done)} noted as incomplete")


if __name__ == "__main__":
    sys.exit(main())
