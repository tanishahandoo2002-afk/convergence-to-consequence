"""Build the one-page explainer and the README figures from the result files, into webpage/build/ (not committed).

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
STANDALONE_HEAD = ('<!doctype html>\n<html lang="en">\n<meta charset="utf-8">\n'
                   '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                   '<meta name="description" content="An ALE map of the episodic-retrieval network, tested on single '
                   '7T fMRI trials and against tDCS/tACS trials with modelled electric fields.">\n'
                   '<style>body { margin: 0; } img { max-width: 100%; } [hidden] { display: none !important; }</style>\n')


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


INK = {"light": ("#101720", "#7b8490", "#dde2e8"), "dark": ("#eef1f4", "#8a929c", "#282e36")}  # text, muted, grid
CLIN = {"light": "#1baf7a", "dark": "#199e70"}
OTHER = {"light": "#9aa2ad", "dark": "#6d7580"}


def results_figure(d):
    """README figure: the pooled RQ2 estimates (b3 and b2) next to RQ3 effect size against field in the map."""
    h2 = {beta: {(r["model"], r["term"]): r for r in d[f"h2_{beta}"] if r["subject"] == "all"} for beta in ("b3", "b2")}
    rows = [("H2a  map signal", "H2a", "sig_memory", MEM), ("H2b  map signal", "H2b", "z_memory", MEM),
            ("H2b  control signal", "H2b", "z_control", CTL), ("H2b  map − control", "H2b", "z_memory - z_control", MEM),
            ("H2c  map × log delay", "H2c", "sig_memory:log_delay_c", MEM)]
    ernie = {f["montage_id"]: f["field_map"] for f in d["fields"] if f["head_model"] == "ernie"}
    control = {f["montage_id"]: f["field_control"] for f in d["fields"] if f["head_model"] == "ernie"}
    eff = [e for e in d["effects"] if e["sessions"] is not None and ernie.get(e["montage_id"]) is not None
           and control.get(e["montage_id"]) is not None]
    h3a = {r["term"]: r for r in d["h3"]["0.5"] if r["model"] == "H3a"}
    paths = {}
    for mode in ("light", "dark"):
        ink, muted, grid = INK[mode]
        fig, (a, b) = plt.subplots(1, 2, figsize=(12, 4.2), facecolor=FACE[mode], gridspec_kw={"width_ratios": [1, 1.1]})
        for ax in (a, b):
            ax.set_facecolor(FACE[mode])
            ax.tick_params(colors=muted, labelsize=9)
            for side in ("top", "right", "left"):
                ax.spines[side].set_visible(False)
            ax.spines["bottom"].set_color(grid)
            ax.grid(axis="x", color=grid, linewidth=0.8)
            ax.set_axisbelow(True)
        for i, (label, model, term, colour) in enumerate(rows):
            for beta, dy, hollow in (("b3", -0.13, False), ("b2", 0.13, True)):
                r = h2[beta][(model, term)]
                a.plot([r["ci_low"], r["ci_high"]], [i + dy] * 2, color=colour[mode], linewidth=2, solid_capstyle="round")
                a.plot(r["estimate"], i + dy, "o", markersize=6.5, color=colour[mode],
                       markerfacecolor=FACE[mode] if hollow else colour[mode], markeredgewidth=2)
        a.axvline(0, color=muted, linewidth=1)
        a.set_yticks(range(len(rows)), [r[0] for r in rows], color=ink, fontsize=9.5)
        a.tick_params(axis="y", length=0)
        a.invert_yaxis()
        a.set_xlabel("log-odds per SD of mask signal, 95% CI  (filled: b3 betas, open: b2)", color=muted, fontsize=9)
        a.set_title("RQ2 · single 7T fMRI trials, 8 participants", color=ink, fontsize=11, loc="left", pad=10)
        for clinical, marker, colour in ((False, "o", OTHER), (True, "D", CLIN)):
            pts = [e for e in eff if (e["population"] != "healthy") == clinical]
            b.scatter([ernie[e["montage_id"]] for e in pts], [e["yi"] for e in pts], s=[min(140, 6 / e["vi"]) for e in pts],
                      marker=marker, color=colour[mode], edgecolors=FACE[mode], linewidths=1, alpha=0.9,
                      label="MCI or early AD" if clinical else "healthy adults")
        x = [0, max(ernie[e["montage_id"]] for e in eff)]
        slope, start = h3a["field_map"], h3a["intrcpt"]["estimate"] + h3a["sessions"]["estimate"]
        b.plot(x, [start + slope["estimate"] * v for v in x], color=ink, linewidth=2)
        b.axhline(0, color=muted, linewidth=1)
        b.set_xlabel("modelled field in the memory map (V/m, Ernie head)", color=muted, fontsize=9)
        b.set_ylabel("Hedges' g", color=muted, fontsize=9)
        b.set_title(f"RQ3 · {len(eff)} stimulation effects; H3a slope {slope['estimate']:.2f} g per V/m "
                    f"[{slope['ci_low']:.1f}, {slope['ci_high']:.1f}]", color=ink, fontsize=11, loc="left", pad=10)
        b.legend(frameon=False, fontsize=9, labelcolor=ink, loc="upper right")
        fig.tight_layout(w_pad=3)
        paths[mode] = save(fig, f"results_{mode}.png", mode)
    return paths


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
    data = page_data()
    results_figure(data)
    page = page.replace("/*DATA*/null", json.dumps(data, separators=(",", ":")))
    if "{{" in page or "/*DATA*/" in page:
        raise SystemExit("a template placeholder was not filled")
    (OUT / "c2c.html").write_text(page)
    # The artifact viewer wraps c2c.html in a document head; GitHub Pages serves index.html as it is.
    (OUT / "index.html").write_text(STANDALONE_HEAD + page)
    print(f"page written to {OUT} as c2c.html and index.html ({len(page) // 1024} KB)")


if __name__ == "__main__":
    main()
