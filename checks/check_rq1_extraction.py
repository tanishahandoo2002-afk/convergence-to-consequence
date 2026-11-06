"""RQ1 extraction check (plan §8.1 steps 5-8, §12): sheet schema, one experiment per subject group,
foci inside the brain, experiment count, and the 20% coordinate spot-check.
CLI: python -m checks.check_rq1_extraction
"""
import sys

import pandas as pd
from nilearn.datasets import load_mni152_brain_mask

from checks.signoffs import SIGNOFFS, has_error, missing
from rq1_map.coords import outside_brain, to_mni
from rq1_map.import_sleuth import EXP_COLUMNS, SHEETS, UNVERIFIED, read_h1b_sheets
from rq1_map.spotcheck import SAMPLE
from tools.common import load_config

CONTRAST_TYPES = {"success", "recollection", "familiarity"}


def _fmt(v):
    return f"{float(v):g}"


def validate(experiments, coordinates, cfg, signoff_path=SIGNOFFS, sample_path=SAMPLE):
    errors, warnings = [], []
    exps = experiments.astype(str).replace("nan", "")
    absent = [c for c in EXP_COLUMNS if c not in exps.columns]
    if absent:
        return [f"experiments.csv lacks columns {absent}"], warnings

    def ids(mask):
        return sorted(exps.loc[mask, "exp_id"])

    if exps.exp_id.duplicated().any():
        errors.append(f"duplicate exp_id: {ids(exps.exp_id.duplicated())}")
    bad_n = ~exps.n.str.fullmatch(r"\d+") | (pd.to_numeric(exps.n, errors="coerce") < 5)
    if bad_n.any():
        errors.append(f"n must be an integer >= 5: {ids(bad_n)}")
    if (~exps.space.isin(["MNI", "TAL"])).any():
        errors.append(f"space must be MNI or TAL: {ids(~exps.space.isin(['MNI', 'TAL']))}")
    if (~exps.contrast_type.isin(CONTRAST_TYPES)).any():
        errors.append(f"contrast_type must be one of {sorted(CONTRAST_TYPES)}: {ids(~exps.contrast_type.isin(CONTRAST_TYPES))}")
    if (exps.contrast_verified_by.str.strip() == "").any():
        errors.append(f"contrast_verified_by is empty (author must confirm each contrast): {ids(exps.contrast_verified_by.str.strip() == '')}")
    dup = exps.subject_group[exps.subject_group.duplicated(keep=False)]
    if len(dup):
        errors.append(f"subject_group appears more than once (pool its contrasts into one experiment): {sorted(set(dup))}")

    no_foci = sorted(set(exps.exp_id) - set(coordinates.exp_id))
    if no_foci:
        errors.append(f"experiments with no foci: {no_foci}")
    unknown = sorted(set(coordinates.exp_id) - set(exps.exp_id))
    if unknown:
        errors.append(f"coordinates.csv references unknown exp_id: {unknown}")

    k = len(exps)
    if k < cfg["hard_min_experiments"]:
        errors.append(f"{k} experiments: fewer than {cfg['hard_min_experiments']}, ALE is underpowered")
    elif k < cfg["min_experiments"]:
        warnings.append(f"{k} experiments: below the target of {cfg['min_experiments']}")

    # Their papers cannot be read, so they cannot be signed off or spot-checked; say so instead of blocking (CHANGELOG 2026-11-07)
    unverified = set(exps.exp_id[exps.contrast_verified_by == UNVERIFIED])
    if unverified:
        warnings.append(f"{len(unverified)} experiments are not verified against their papers: {sorted(unverified)}")

    coords = coordinates[coordinates.exp_id.isin(exps.exp_id)].reset_index(drop=True)
    if len(coords):
        out = outside_brain(to_mni(exps, coords), load_mni152_brain_mask(resolution=2))
        items = [f"{r.exp_id}:{_fmt(r.x)},{_fmt(r.y)},{_fmt(r.z)}" for r in coords[out].itertuples()]
        unchecked = [i for i in items if i.split(":")[0] in unverified]
        if unchecked:
            warnings.append(f"foci outside the brain left unchecked in unverified experiments: {unchecked}")
        unsigned = missing("rq1_outlier_focus", [i for i in items if i not in unchecked], path=signoff_path)
        if unsigned:
            errors.append(f"foci outside the brain need an rq1_outlier_focus sign-off (check against the PDF): {unsigned}")

    sample = list(pd.read_csv(sample_path, dtype=str).exp_id) if sample_path.exists() else None
    if sample is None:
        errors.append("spot-check sample not drawn: python -m rq1_map.spotcheck")
    else:
        checkable = [e for e in exps.exp_id if e not in unverified]
        need = checkable if has_error("rq1_spotcheck", path=signoff_path) else sample
        unsigned = missing("rq1_spotcheck", need, path=signoff_path)
        if unsigned:
            scope = "every experiment (an error was found in the sample)" if len(need) > len(sample) else "the sample"
            errors.append(f"spot-check sign-offs missing for {scope}: {unsigned}")
    return errors, warnings


def validate_h1b(sheets, cfg, signoff_path=SIGNOFFS, sample_path=SAMPLE):
    """Errors in the H1b sheets. Below the size gate H1b is reported as not run, so there is nothing to check."""
    gate = cfg["h1b_min_per_group"]
    if min(len(e) for e, _ in sheets.values()) < gate:
        return []
    errors = []
    for contrast_type, (exps, coords) in sheets.items():
        found, _ = validate(exps, coords, cfg | {"hard_min_experiments": gate, "min_experiments": gate},
                            signoff_path, sample_path)
        wrong = sorted(exps.exp_id[exps.contrast_type != contrast_type])
        if wrong:
            found.append(f"contrast_type must be {contrast_type}: {wrong}")
        errors += [f"{contrast_type} sheet: {e}" for e in found]
    return errors


def main():
    exps = pd.read_csv(SHEETS / "experiments.csv", dtype=str).fillna("")
    coords = pd.read_csv(SHEETS / "coordinates.csv")
    cfg = load_config("rq1")
    errors, warnings = validate(exps, coords, cfg)
    errors += validate_h1b(read_h1b_sheets(), cfg)
    for w in warnings:
        print("WARNING:", w)
    for e in errors:
        print("FAIL:", e)
    if errors:
        sys.exit(1)
    print(f"extraction check OK: {len(exps)} experiments, {len(coords)} foci")


if __name__ == "__main__":
    main()
