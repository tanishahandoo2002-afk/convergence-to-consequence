"""RQ1 ALE check: outputs exist, parameters match config, jackknife covers every experiment,
versions recorded. An empty cluster table is reported, never failed (checks test process, not results).
CLI: python -m checks.check_rq1_ale
"""
import json
import sys

import pandas as pd

from rq1_map.import_sleuth import SHEETS
from tools.common import ROOT, load_config

OUTPUTS = ["ale_stat.nii.gz", "ale_cluster_fwe_z.nii.gz", "clusters.csv", "jackknife.csv", "params.json",
           "failsafe.csv", "h1b_status.txt"]


def check(results, cfg, experiments, versions=ROOT / "results" / "versions.txt"):
    missing = [f for f in OUTPUTS if not (results / f).exists()]
    if missing:
        return [f"missing outputs: {missing}"]
    errors = []
    used = json.loads((results / "params.json").read_text())["ale"]
    for k, v in cfg["ale"].items():
        if used.get(k) != v:
            errors.append(f"ALE parameter {k}: run used {used.get(k)}, config says {v}")
    jk = pd.read_csv(results / "jackknife.csv", dtype=str)
    absent = sorted(set(experiments.exp_id) - set(jk.exp_id))
    if absent:
        errors.append(f"jackknife lacks experiments {absent}")
    if (results / "h1b_status.txt").read_text().startswith("run") and not (results / "h1b_subtraction_z.nii.gz").exists():
        errors.append("H1b reported as run but h1b_subtraction_z.nii.gz is missing")
    if not versions.exists() or " rq1_ale " not in versions.read_text():
        errors.append("results/versions.txt has no rq1_ale entry")
    return errors


def main():
    results = SHEETS / "results"
    errors = check(results, load_config("rq1"), pd.read_csv(SHEETS / "experiments.csv", dtype=str))
    for e in errors:
        print("FAIL:", e)
    if errors:
        sys.exit(1)
    n = len(pd.read_csv(results / "clusters.csv"))
    print(f"ALE check OK ({n} significant clusters{'; empty map is a finding, report it' if n == 0 else ''})")


if __name__ == "__main__":
    main()
