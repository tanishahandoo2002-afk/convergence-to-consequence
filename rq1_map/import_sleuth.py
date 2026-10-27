"""Convert a BrainMap Sleuth / GingerALE text export into the two extraction sheets.

Format: first line '// Reference=MNI|TAL|Talairach'; each experiment is a block of '//' header lines
('// Author, Year: contrast', '// Subjects=N') followed by tab-separated x y z lines.
CLI: python -m rq1_map.import_sleuth <export.txt> [<export.txt> ...]
     Appends to experiments.csv / coordinates.csv. A block that repeats another exactly (same study, N,
     contrasts and foci, e.g. found by two Sleuth searches) is kept once.
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
                cur = {"exp_id": f"bm{start + len(exps) + 1:03d}", "_has_foci": False, "n": "", "labels": []}
                exps.append(cur)
            m = re.match(r"Subjects\s*=\s*(\d+)", body)
            if m:
                cur["n"] = m.group(1)
            elif re.match(r"^.+?, \d{4}[a-z]?:", body) or not cur["labels"]:
                cur["labels"].append(body)
            else:  # Sleuth wraps long contrast names onto the next // line
                cur["labels"][-1] = f"{cur['labels'][-1]} {body}"
        else:
            x, y, z = (float(v) for v in re.split(r"[\s,]+", ln)[:3])
            coords.append({"exp_id": cur["exp_id"], "x": x, "y": y, "z": z})
            cur["_has_foci"] = True
    rows = []
    for e in (e for e in exps if e["_has_foci"]):  # Sleuth writes an empty block for each hidden contrast
        parts = [label.partition(":") for label in e["labels"]]
        study = parts[0][0].strip()
        contrast = " | ".join(" ".join(c.split()) for _, _, c in parts)  # several contrasts = one pooled subject group
        rows.append({"exp_id": e["exp_id"], "study_id": study, "subject_group": study,
                     "contrast": contrast, "n": e["n"], "space": space, "source": "brainmap"})
    return pd.DataFrame(rows).reindex(columns=EXP_COLUMNS).fillna(""), pd.DataFrame(coords, columns=["exp_id", "x", "y", "z"])


def drop_duplicate_blocks(experiments, coordinates):
    """Remove experiments identical to an earlier one in study, N, contrasts and foci. Returns
    (experiments, coordinates, removed exp_ids). Different groups with the same N are kept for the author."""
    foci = coordinates.assign(xyz=list(zip(coordinates.x.astype(float).round(1), coordinates.y.astype(float).round(1),
                                           coordinates.z.astype(float).round(1))))
    foci = foci.groupby("exp_id").xyz.apply(frozenset)
    key = experiments.apply(lambda r: (r.study_id, str(r.n), frozenset(r.contrast.split(" | ")), foci.get(r.exp_id)), axis=1)
    dup = key.duplicated()
    removed = list(experiments.exp_id[dup])
    return (experiments[~dup].reset_index(drop=True), coordinates[~coordinates.exp_id.isin(removed)].reset_index(drop=True),
            removed)


def main():
    exp_path, coord_path = SHEETS / "experiments.csv", SHEETS / "coordinates.csv"
    all_e = [pd.read_csv(exp_path, dtype=str).fillna("")]
    all_c = [pd.read_csv(coord_path)]
    start = int(all_e[0].exp_id.str.startswith("bm").sum())
    for f in sys.argv[1:]:
        e, c = read_sleuth(f, start=start)
        start += len(e)
        all_e.append(e)
        all_c.append(c)
    e, c, removed = drop_duplicate_blocks(pd.concat(all_e, ignore_index=True), pd.concat(all_c, ignore_index=True))
    e.to_csv(exp_path, index=False)
    c.to_csv(coord_path, index=False)
    print(f"{len(e)} experiments, {len(c)} foci in the sheets; {len(removed)} exact duplicate blocks dropped: {removed}")
    print("Next by hand: confirm subject groups, set contrast_type and contrast_verified_by, exclude ineligible rows")


if __name__ == "__main__":
    main()
