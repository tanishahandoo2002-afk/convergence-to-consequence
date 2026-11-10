"""Build the one-page explainer from the result files: webpage/build/c2c.html (not committed).

Every number on the page is read here from the outputs of the stage scripts; the template only lays them out.
CLI: python -m webpage.build   (needs the rq1, masks, rq2, rq2-b2, rq3 and integration results)
"""
import base64
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.colors import ListedColormap
from nilearn import datasets, image, plotting

from tools.common import ROOT
from tools.prisma import counts

HERE = Path(__file__).resolve().parent
OUT = HERE / "build"
# Chart colours for the memory and control masks, light and dark (validated as a set for colour-blind contrast).
MEM = {"light": "#2a78d6", "dark": "#3987e5"}
CTL = {"light": "#eb6834", "dark": "#d95926"}
FACE = {"light": "#fcfcfb", "dark": "#1a1a19"}


def brain_images():
    """Glass brain of the memory mask and axial slices of memory vs control, light and dark."""
    mem = image.load_img(ROOT / "masks/memory.nii.gz")
    ctl = image.load_img(ROOT / "masks/control_md.nii.gz")
    template = datasets.load_mni152_template(resolution=1)
    pngs = {}
    for mode in ("light", "dark"):
        dark = mode == "dark"
        fig = plt.figure(figsize=(11, 3.4), facecolor=FACE[mode])
        plotting.plot_glass_brain(mem, display_mode="lyrz", colorbar=False, black_bg=dark, threshold=0.5,
                                  cmap=ListedColormap([MEM[mode]]), figure=fig)
        pngs[f"GLASS_{mode.upper()}"] = save(fig, f"glass_{mode}.png", mode)
        fig = plt.figure(figsize=(11, 3.2), facecolor=FACE[mode])
        d = plotting.plot_anat(template, display_mode="z", cut_coords=[-14, 2, 18, 32, 44], figure=fig,
                               black_bg=dark, draw_cross=False, dim=0.6 if dark else 0.2, colorbar=False)
        d.add_overlay(ctl, cmap=ListedColormap([CTL[mode]]), transparency=0.75)
        d.add_overlay(mem, cmap=ListedColormap([MEM[mode]]), transparency=0.9)
        pngs[f"MASKS_{mode.upper()}"] = save(fig, f"masks_{mode}.png", mode)
    return pngs


def save(fig, name, mode):
    path = OUT / name
    fig.savefig(path, dpi=110, facecolor=FACE[mode], bbox_inches="tight")
    plt.close(fig)
    return path


def records(df, cols=None):
    return json.loads((df if cols is None else df[cols]).to_json(orient="records"))


def page_data():
    rq1, r2, r3 = ROOT / "rq1_map/results", ROOT / "rq2_nsd/results", ROOT / "rq3_stimulation/results"
    d = {"prisma": {q: {k: int(v) for k, v in counts(ROOT / folder).items()}
                    for q, folder in (("rq1", "rq1_map"), ("rq3", "rq3_stimulation"))},
         "ale_params": json.loads((rq1 / "params.json").read_text()),
         "clusters": records(pd.read_csv(rq1 / "clusters.csv")),
         "clusters_verified": records(pd.read_csv(rq1 / "clusters_verified_only.csv")),
         "failsafe": records(pd.read_csv(rq1 / "failsafe.csv")),
         "h1b": (rq1 / "h1b_status.txt").read_text().strip(),
         "trial_counts": records(pd.read_csv(r2 / "trial_counts.csv", dtype={"outcome": str}).fillna({"outcome": "none"}))}
    keep = ["model", "subject", "term", "estimate", "se", "ci_low", "ci_high", "p", "formula_used", "converged", "singular"]
    for beta, folder in (("b3", r2), ("b2", r2 / "b2")):
        h2 = pd.read_csv(folder / "h2_results.csv", dtype={"subject": str})
        rob = pd.read_csv(folder / "h2_robustness.csv", dtype={"subject": str})
        d[f"h2_{beta}"] = records(h2[h2.term != "(Intercept)"], keep)
        d[f"rob_{beta}"] = records(rob[rob.term != "(Intercept)"], keep + ["variant"])
        d[f"perm_{beta}"] = records(pd.read_csv(folder / "permutation.csv", dtype={"subject": str}))
        d[f"delay_centre_{beta}"] = float((folder / "h2c_delay_centre.txt").read_text())
    d["effects"] = records(pd.read_csv(r3 / "effect_sizes_r0.5.csv"),
                           ["es_id", "study_id", "population", "design", "stim", "montage_id", "timing", "sessions",
                            "test_type", "yi", "vi", "n_active", "n_sham"])
    d["fields"] = records(pd.read_csv(ROOT / "rq3_stimulation/simnibs/fields.csv"))
    d["montages"] = records(pd.read_csv(ROOT / "rq3_stimulation/montages.csv"))
    d["h3"] = {r: records(pd.read_csv(r3 / f"h3_results_r{r}.csv")) for r in ("0.3", "0.5", "0.7")}
    d["bias"] = {r: records(pd.read_csv(r3 / f"bias_r{r}.csv")) for r in ("0.3", "0.5", "0.7")}
    rob2 = pd.read_csv(ROOT / "rq3_stimulation/rob2.csv")
    domains = ["d1_randomisation", "d2_deviations", "d3_missing", "d4_measurement", "d5_selection", "overall"]
    d["rob2"] = {c: {k: int(v) for k, v in rob2[c].value_counts().items()} for c in domains}
    d["rob2_n"] = len(rob2)
    d["integration"] = records(pd.read_csv(ROOT / "results/integration_table.csv"))
    return d


def main():
    OUT.mkdir(exist_ok=True)
    page = (HERE / "template.html").read_text()
    for key, path in brain_images().items():
        page = page.replace("{{%s}}" % key, "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode())
    page = page.replace("/*DATA*/null", json.dumps(page_data(), separators=(",", ":")))
    if "{{" in page or "/*DATA*/" in page:
        raise SystemExit("a template placeholder was not filled")
    (OUT / "c2c.html").write_text(page)
    print(f"page written to {OUT / 'c2c.html'} ({len(page) // 1024} KB)")


if __name__ == "__main__":
    main()
