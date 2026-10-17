"""RQ1 ALE (plan §8.1 step 9-10): sample-size-weighted ALE, Monte Carlo cluster-level FWE,
cluster table with atlas labels, and a leave-one-experiment-out jackknife.
CLI: python -m rq1_map.run_ale
"""
import datetime
import json
import sys
from pathlib import Path

import nibabel as nib
import nimare
import numpy as np
import pandas as pd
from nilearn import datasets, image
from nilearn.reporting import get_clusters_table
from nimare.correct import FWECorrector
from nimare.dataset import Dataset
from nimare.diagnostics import Jackknife
from nimare.meta.cbma.ale import ALE, ALESubtraction

from checks.check_rq1_extraction import validate
from rq1_map.coords import random_in_brain, to_mni
from rq1_map.import_sleuth import SHEETS
from tools.common import load_config, record_versions

CLUSTER_MAP = "z_desc-size_level-cluster_corr-FWE_method-montecarlo"
LOGP_MAP = "logp_desc-size_level-cluster_corr-FWE_method-montecarlo"
SIG_MAP = "z_sig_cluster"
RESULTS = SHEETS / "results"


def build_dataset(experiments, coordinates_mni):
    """One NiMARE study per experiment; sample size drives the ALE kernel width."""
    d = {}
    for e in experiments.itertuples():
        c = coordinates_mni[coordinates_mni.exp_id == e.exp_id]
        d[e.exp_id] = {"contrasts": {"1": {
            "coords": {"space": "MNI", "x": c.x.tolist(), "y": c.y.tolist(), "z": c.z.tolist()},
            "metadata": {"sample_sizes": [int(e.n)]}}}}
    return Dataset(d)


def run(dset, ale_cfg, seed):
    np.random.seed(seed)
    result = ALE().fit(dset)
    corrector = FWECorrector(method="montecarlo", voxel_thresh=ale_cfg["voxel_thresh"],
                             n_iters=ale_cfg["n_iters"], n_cores=ale_cfg["n_cores"])
    cres = corrector.transform(result)
    if CLUSTER_MAP not in cres.maps:
        raise RuntimeError(f"NiMARE did not produce {CLUSTER_MAP}; available maps: {sorted(cres.maps)}")
    return cres


def significant_map(cres, alpha):
    """Cluster-FWE z map restricted to clusters with cluster-level p < alpha (zero elsewhere)."""
    z, logp = cres.get_map(CLUSTER_MAP), cres.get_map(LOGP_MAP)
    keep = np.asarray(logp.dataobj) > -np.log10(alpha)
    return nib.Nifti1Image(np.where(keep, np.asarray(z.dataobj), 0).astype("float32"), z.affine)


def _labeller():
    cort = datasets.fetch_atlas_harvard_oxford("cort-maxprob-thr25-2mm")
    sub = datasets.fetch_atlas_harvard_oxford("sub-maxprob-thr25-2mm")

    def label(xyz):
        for atlas in (cort, sub):
            img = image.load_img(atlas.maps)
            ijk = np.rint(np.linalg.inv(img.affine) @ np.r_[xyz, 1])[:3].astype(int)
            name = atlas.labels[int(np.asarray(img.dataobj)[tuple(ijk)])]
            # The subcortical atlas also labels whole-hemisphere cortex/white matter; skip those
            if name != "Background" and "Cerebral" not in name:
                return name
        return "unlabelled"
    return label


def cluster_table(cres, alpha):
    sig = significant_map(cres, alpha)
    cols = ["cluster", "peak_x", "peak_y", "peak_z", "peak_z_value", "size_mm3", "label"]
    if not np.any(np.asarray(sig.dataobj) > 0):
        return pd.DataFrame(columns=cols)
    t = get_clusters_table(sig, stat_threshold=1e-6, min_distance=1e6, two_sided=False)
    label = _labeller()
    return pd.DataFrame({
        "cluster": t["Cluster ID"].astype(str), "peak_x": t.X, "peak_y": t.Y, "peak_z": t.Z,
        "peak_z_value": t["Peak Stat"], "size_mm3": t["Cluster Size (mm3)"],
        "label": [label((x, y, z)) for x, y, z in zip(t.X, t.Y, t.Z)]})[cols]


def jackknife(cres, alpha):
    """Per-cluster contribution of each experiment (leave-one-out). One row per experiment."""
    ids = sorted({sid.rsplit("-", 1)[0] for sid in cres.estimator.dataset.ids})
    sig = significant_map(cres, alpha)
    if not np.any(np.asarray(sig.dataobj) > 0):
        return pd.DataFrame({"exp_id": ids})
    cres.maps[SIG_MAP] = cres.estimator.masker.transform(sig).squeeze()
    out = Jackknife(target_image=SIG_MAP, voxel_thresh=None).transform(cres)
    t = out.tables[f"{SIG_MAP}_diag-Jackknife_tab-counts_tail-positive"]
    t = t.rename(columns={"id": "exp_id"})
    t["exp_id"] = t.exp_id.str.rsplit("-", n=1).str[0]
    return t


def noise_experiments(k, template_n, foci_per_exp, seed):
    """k null experiments with random in-brain foci and sample sizes drawn from the real ones."""
    rng = np.random.default_rng(seed)
    mask = datasets.load_mni152_brain_mask(resolution=2)
    exps, rows = [], []
    for i in range(k):
        eid = f"noise{i:03d}"
        exps.append({"exp_id": eid, "n": str(int(rng.choice(template_n)))})
        rows += [{"exp_id": eid, "x": x, "y": y, "z": z} for x, y, z in random_in_brain(rng, foci_per_exp, mask)]
    return pd.DataFrame(exps), pd.DataFrame(rows)


def failsafe(experiments, coordinates_mni, clusters, cfg):
    """Does each cluster's peak survive adding N null experiments (Acar et al., 2018 approach)?"""
    # Simplification: fixed counts, not a search for the exact break point; add bisection if a reviewer asks for an exact FSN.
    rows = []
    foci = int(coordinates_mni.groupby("exp_id").size().median())
    ale_cfg = cfg["ale"] | {"n_iters": cfg["failsafe_n_iters"]}
    for count in cfg["failsafe_counts"]:
        ne, nc = noise_experiments(count, experiments.n.astype(int).tolist(), foci, cfg["seed"] + count)
        cres = run(build_dataset(pd.concat([experiments[["exp_id", "n"]], ne]), pd.concat([coordinates_mni, nc])),
                   ale_cfg, cfg["seed"])
        sig = significant_map(cres, cfg["ale"]["cluster_alpha"])
        inv, data = np.linalg.inv(sig.affine), np.asarray(sig.dataobj)
        for c in clusters.itertuples():
            ijk = np.rint(inv @ np.r_[c.peak_x, c.peak_y, c.peak_z, 1])[:3].astype(int)
            rows.append({"cluster": c.cluster, "noise_experiments": count, "survives": bool(data[tuple(ijk)] > 0)})
    return pd.DataFrame(rows, columns=["cluster", "noise_experiments", "survives"]).astype({"survives": bool})


def h1b(experiments, coordinates_mni, cfg, out_dir=RESULTS):
    """Recollection vs familiarity ALE subtraction, run only if each group is large enough."""
    k = {t: int((experiments.contrast_type == t).sum()) for t in ("recollection", "familiarity")}
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if min(k.values()) < cfg["h1b_min_per_group"]:
        status = (f"not run: recollection k={k['recollection']}, familiarity k={k['familiarity']} "
                  f"(each needs >= {cfg['h1b_min_per_group']})")
        (out_dir / "h1b_status.txt").write_text(status)
        return status
    groups = [experiments[experiments.contrast_type == t] for t in ("recollection", "familiarity")]
    dsets = [build_dataset(g, coordinates_mni[coordinates_mni.exp_id.isin(g.exp_id)]) for g in groups]
    res = ALESubtraction(n_iters=cfg["ale"]["n_iters"], n_cores=cfg["ale"]["n_cores"],
                         random_state=cfg["seed"]).fit(*dsets)
    res.get_map("z_desc-group1MinusGroup2").to_filename(out_dir / "h1b_subtraction_z.nii.gz")
    status = f"run: recollection k={k['recollection']} minus familiarity k={k['familiarity']}"
    (out_dir / "h1b_status.txt").write_text(status)
    return status


def main():
    cfg = load_config("rq1")
    exps = pd.read_csv(SHEETS / "experiments.csv", dtype=str).fillna("")
    coords = pd.read_csv(SHEETS / "coordinates.csv")
    errors, _ = validate(exps, coords, cfg)
    if errors:
        sys.exit("extraction check fails; fix it before running the ALE:\n  " + "\n  ".join(errors))
    coords_mni = to_mni(exps, coords)
    cres = run(build_dataset(exps, coords_mni), cfg["ale"], cfg["seed"])
    RESULTS.mkdir(exist_ok=True)
    alpha = cfg["ale"]["cluster_alpha"]
    cres.get_map("stat").to_filename(RESULTS / "ale_stat.nii.gz")
    significant_map(cres, alpha).to_filename(RESULTS / "ale_cluster_fwe_z.nii.gz")
    clusters = cluster_table(cres, alpha)
    clusters.to_csv(RESULTS / "clusters.csv", index=False)
    jackknife(cres, alpha).to_csv(RESULTS / "jackknife.csv", index=False)
    if len(clusters):
        failsafe(exps, coords_mni, clusters, cfg).to_csv(RESULTS / "failsafe.csv", index=False)
    else:
        pd.DataFrame(columns=["cluster", "noise_experiments", "survives"]).to_csv(RESULTS / "failsafe.csv", index=False)
    print(h1b(exps, coords_mni, cfg))
    params = {"date": datetime.date.today().isoformat(), "seed": cfg["seed"], "ale": cfg["ale"],
              "n_experiments": len(exps), "n_foci": len(coords), "nimare": nimare.__version__}
    (RESULTS / "params.json").write_text(json.dumps(params, indent=2))
    record_versions("rq1_ale")
    print(f"ALE done: {len(clusters)} significant clusters from {len(exps)} experiments")
    return cres, exps, coords_mni, clusters, cfg


if __name__ == "__main__":
    main()
