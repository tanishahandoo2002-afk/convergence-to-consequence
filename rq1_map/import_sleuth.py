"""Convert a BrainMap Sleuth / GingerALE text export into the two extraction sheets.

Format: first line '// Reference=MNI|TAL|Talairach'; each experiment is a block of '//' header lines
('// Author, Year: contrast', '// Subjects=N') followed by tab-separated x y z lines.
CLI: python -m rq1_map.import_sleuth <export.txt>   (appends to experiments.csv / coordinates.csv)
"""
import re
import sys
from pathlib import Path

import pandas as pd

EXP_COLUMNS = ["exp_id", "study_id", "doi", "subject_group", "table_or_figure", "contrast", "contrast_type",
               "n", "mean_age", "space", "source", "contrast_verified_by"]
SHEETS = Path(__file__).resolve().parent


def read_sleuth(path, start=0):
    lines = [ln.strip() for ln in Path(path).read_text().splitlines()]
    space = lines[0].replace(" ", "").replace("//Reference=", "")
    space = {"MNI": "MNI", "TAL": "TAL", "Talairach": "TAL"}.get(space)
    if not space:
        raise ValueError(f"{path}: first line must be '// Reference=MNI' or '// Reference=Talairach'")
    exps, coords, cur = [], [], None
    for ln in lines[1:]:
        if not ln:
            continue
        if ln.startswith("//"):
            body = ln[2:].strip()
            if cur is None or cur["_has_foci"]:
                cur = {"exp_id": f"bm{start + len(exps) + 1:03d}", "_has_foci": False, "n": "", "label": ""}
                exps.append(cur)
            m = re.match(r"Subjects\s*=\s*(\d+)", body)
            if m:
                cur["n"] = m.group(1)
            else:
                cur["label"] = body
        else:
            x, y, z = (float(v) for v in re.split(r"[\s,]+", ln)[:3])
            coords.append({"exp_id": cur["exp_id"], "x": x, "y": y, "z": z})
            cur["_has_foci"] = True
    rows = []
    for e in exps:
        study, _, contrast = e["label"].partition(":")
        rows.append({"exp_id": e["exp_id"], "study_id": study.strip(), "subject_group": study.strip(),
                     "contrast": contrast.strip(), "n": e["n"], "space": space, "source": "brainmap"})
    return pd.DataFrame(rows).reindex(columns=EXP_COLUMNS).fillna(""), pd.DataFrame(coords, columns=["exp_id", "x", "y", "z"])


def main():
    exp_path, coord_path = SHEETS / "experiments.csv", SHEETS / "coordinates.csv"
    old_e = pd.read_csv(exp_path, dtype=str).fillna("")
    old_c = pd.read_csv(coord_path, dtype=str)
    e, c = read_sleuth(sys.argv[1], start=int(old_e.exp_id.str.startswith("bm").sum()))
    pd.concat([old_e, e]).to_csv(exp_path, index=False)
    pd.concat([old_c, c]).to_csv(coord_path, index=False)
    print(f"added {len(e)} experiments, {len(c)} foci; set subject_group, contrast_type and contrast_verified_by by hand")


if __name__ == "__main__":
    main()
