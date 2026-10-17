import numpy as np
import pandas as pd
import pytest
from nilearn.datasets import load_mni152_brain_mask

from rq1_map.run_ale import build_dataset, cluster_table, jackknife, run, significant_map

ALE_CFG = {"voxel_thresh": 0.001, "cluster_alpha": 0.05, "n_iters": 100, "n_cores": 1}
PEAK = (-24.0, -18.0, -18.0)


def in_brain_points(rng, k):
    mask = load_mni152_brain_mask(resolution=2)
    ijk = np.argwhere(np.asarray(mask.dataobj) > 0)
    pick = ijk[rng.choice(len(ijk), k, replace=False)]
    return (mask.affine @ np.c_[pick, np.ones(k)].T)[:3].T


def synth(planted, seed=0, k=25):
    rng = np.random.default_rng(seed)
    exps, rows = [], []
    for i in range(k):
        eid = f"e{i}"
        exps.append({"exp_id": eid, "n": "20", "contrast_type": "success"})
        pts = list(in_brain_points(rng, 5 if planted else 8))
        if planted:
            pts += [np.array(PEAK) + rng.uniform(-4, 4, 3) for _ in range(3)]
        rows += [{"exp_id": eid, "x": p[0], "y": p[1], "z": p[2]} for p in pts]
    return pd.DataFrame(exps), pd.DataFrame(rows)


@pytest.fixture(scope="module")
def planted():
    exps, coords = synth(True)
    dset = build_dataset(exps, coords)
    return exps, run(dset, ALE_CFG, seed=1)


def value_at(img, xyz):
    ijk = np.rint(np.linalg.inv(img.affine) @ np.r_[xyz, 1])[:3].astype(int)
    return np.asarray(img.dataobj)[tuple(ijk)]


def test_planted_cluster_found(planted):
    _, cres = planted
    table = cluster_table(cres, alpha=0.05)
    assert len(table) >= 1
    assert value_at(significant_map(cres, 0.05), PEAK) > 0
    assert {"peak_x", "peak_y", "peak_z", "peak_z_value", "size_mm3", "label"} <= set(table.columns)


def test_noise_only_no_cluster():
    exps, coords = synth(False, seed=3)
    cres = run(build_dataset(exps, coords), ALE_CFG, seed=1)
    assert len(cluster_table(cres, alpha=0.05)) == 0


def test_jackknife_covers_all(planted):
    exps, cres = planted
    jk = jackknife(cres, alpha=0.05)
    assert sorted(jk.exp_id) == sorted(exps.exp_id)
    assert jk.shape[1] >= 2


def test_labels_cortical_and_subcortical():
    from rq1_map.run_ale import _labeller
    label = _labeller()
    assert label((-4, -56, 30)) == "Precuneous Cortex"
    assert label((-24, -18, -18)) == "Left Hippocampus"


def test_check_ale_flags_param_mismatch_and_missing_jackknife(tmp_path):
    import json
    from checks.check_rq1_ale import check
    for f in ["ale_stat.nii.gz", "ale_cluster_fwe_z.nii.gz", "clusters.csv"]:
        (tmp_path / f).write_text("x")
    (tmp_path / "params.json").write_text(json.dumps({"ale": ALE_CFG | {"n_iters": 5000}}))
    pd.DataFrame({"exp_id": ["e0"]}).to_csv(tmp_path / "jackknife.csv", index=False)
    (tmp_path / "versions.txt").write_text("2026-10-18 rq1_ale python=3.12\n")
    errors = check(tmp_path, {"ale": ALE_CFG}, pd.DataFrame({"exp_id": ["e0", "e1"]}), tmp_path / "versions.txt")
    assert any("n_iters" in e for e in errors)
    assert any("e1" in e and "jackknife" in e for e in errors)
