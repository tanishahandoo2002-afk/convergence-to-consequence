"""PRISMA 2020 counts computed from the search and screening logs, never typed by hand.

CLI: python -m tools.prisma rq1   -> screening/prisma.png and prints the counts
"""
import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from tools.common import ROOT
from tools.kappa import human


def title_abstract_decisions(base):
    """Final title/abstract decision per record: the author's where present, otherwise the merged AI one."""
    merged = pd.read_csv(base / "screening" / "merged.csv", dtype=str).set_index("record_id").merged
    final = merged.copy()
    author = human(base, "author")
    final.loc[author.index.intersection(final.index)] = author
    return final


def counts(base):
    log = pd.read_csv(base / "search" / "search_log.csv", dtype=str)
    log.hits = log.hits.astype(int)
    records = pd.read_csv(base / "search" / "records.csv", dtype=str)
    ta = title_abstract_decisions(base).reindex(records.record_id)
    assessed = ta.index[ta != "exclude"]
    ft = human(base, "author", stage="full_text").reindex(assessed).dropna()
    return {
        "identified": int(log[log.source != "dedupe"].drop_duplicates("file", keep="last").hits.sum()),
        "duplicates_removed": int(log.loc[log.source == "dedupe", "hits"].iloc[-1]),
        "screened": len(records),
        "excluded_title_abstract": int((ta == "exclude").sum()),
        "full_text_assessed": len(assessed),
        "excluded_full_text": int((ft == "exclude").sum()),
        "included": int((ft == "include").sum()),
    }


def reconcile(c):
    errors = []
    if c["identified"] - c["duplicates_removed"] != c["screened"]:
        errors.append(f"identified {c['identified']} - duplicates {c['duplicates_removed']} != screened {c['screened']}")
    if c["screened"] - c["excluded_title_abstract"] != c["full_text_assessed"]:
        errors.append("screened - title/abstract exclusions != full texts assessed")
    if c["full_text_assessed"] - c["excluded_full_text"] != c["included"]:
        errors.append(f"full texts assessed {c['full_text_assessed']} - excluded {c['excluded_full_text']} "
                      f"!= included {c['included']} (full-text decisions missing?)")
    return errors


def draw(c, out):
    boxes = [("Records identified", c["identified"]), ("Records screened", c["screened"]),
             ("Full texts assessed", c["full_text_assessed"]), ("Studies included", c["included"])]
    side = [("Duplicates removed", c["duplicates_removed"]), ("Excluded (title/abstract)", c["excluded_title_abstract"]),
            ("Excluded (full text)", c["excluded_full_text"])]
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.axis("off")
    for i, (label, n) in enumerate(boxes):
        y = 0.9 - i * 0.27
        ax.text(0.3, y, f"{label}\n(n = {n})", ha="center", va="center", bbox=dict(boxstyle="round", fc="white"))
        if i < len(side):
            ax.annotate("", (0.3, y - 0.19), (0.3, y - 0.06), arrowprops=dict(arrowstyle="->"))
            ax.text(0.78, y - 0.13, f"{side[i][0]}\n(n = {side[i][1]})", ha="center", va="center",
                    bbox=dict(boxstyle="round", fc="#f2f2f2"))
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rq", choices=["rq1", "rq3"])
    base = ROOT / {"rq1": "rq1_map", "rq3": "rq3_stimulation"}[ap.parse_args().rq]
    c = counts(base)
    draw(c, base / "screening" / "prisma.png")
    print(c)


if __name__ == "__main__":
    main()
