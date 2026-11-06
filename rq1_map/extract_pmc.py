"""Read coordinates straight from PMC article tables into draft sheets, for the author to review.

Which rows hold each contrast is chosen in extraction_spec.yaml. The numbers come only from the table XML, so
no person or model retypes them. Nothing reaches experiments.csv until the author has answered the review sheet.
CLI: python -m rq1_map.extract_pmc
     python -m rq1_map.extract_pmc --apply "<who accepted>" <date>   # after the review sheets are answered
"""
import argparse
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd
import requests
import yaml
from nilearn.datasets import load_mni152_brain_mask

from rq1_map.coords import outside_brain, to_mni
from rq1_map.import_sleuth import EXP_COLUMNS
from tools.screen import EUTILS, EUTILS_TOOL

HERE = Path(__file__).resolve().parent
DRAFT = HERE / "pmc_draft"
NUMBER = r"-?\d+(?:\.\d+)?"
TRIPLE = rf"({NUMBER})[,\s]+({NUMBER})[,\s]+({NUMBER})"
REVIEW_COLUMNS = ["exp_id", "record_id", "study_id", "pmc", "table", "rows", "contrast", "contrast_type", "n", "space",
                  "n_foci", "outside_brain_mask", "what_to_check", "agree", "reason", "date"]


def clean(cell):
    """Printed minus signs become ASCII, with no gap after them; plus signs and thin spaces go."""
    return re.sub(r"[−–—-]\s*", "-", cell.replace("+", "").replace(" ", " ").replace("\xa0", " ")).strip()


def cell_text(cell):
    return re.sub(r"\s+", " ", "".join(cell.itertext())).strip()


def row_numbers(spec):
    """'1-3,7' -> [1, 2, 3, 7]"""
    out = []
    for part in str(spec).split(","):
        first, _, last = part.partition("-")
        out += range(int(first), int(last or first) + 1)
    return out


def foci_in_row(cells, col, mode):
    """(x, y, z) tuples from one row. A cell or row that does not hold exact coordinates raises."""
    if mode == "joint":
        text = clean(cells[col])
        found = re.findall(TRIPLE, text)
        if not found or re.sub(TRIPLE, "", text).strip(" ;"):
            raise ValueError(f"not coordinates: {cells[col]!r}")
    else:
        start = col if col >= 0 else len(cells) + col
        found = [tuple(clean(c).rstrip(",").strip() for c in cells[start:start + 3])]
        if len(found[0]) != 3 or not all(re.fullmatch(NUMBER, v) for v in found[0]):
            raise ValueError(f"not coordinates: {cells[start:start + 3]!r}")
    foci = [tuple(float(v) for v in f) for f in found]
    if any(abs(v) > 100 for f in foci for v in f):
        raise ValueError(f"out of range: {foci}")
    return foci


def find_table(article, label):
    norm = lambda s: re.sub(r"[.:\s]+", " ", s or "").strip().lower()
    tables = [t for t in article.iter("table-wrap") if norm(t.findtext("label")) == norm(label)]
    if len(tables) != 1:
        raise ValueError(f"expected one {label}, found {len(tables)}")
    return tables[0]


def table_foci(table, rows, col, mode):
    """Unique foci in the chosen rows, in table order; a peak listed twice (early and late HRF) counts once."""
    body = table.findall(".//tbody/tr")
    foci = []
    for i in row_numbers(rows):
        foci += foci_in_row([cell_text(c) for c in body[i]], col, mode)
    return list(dict.fromkeys(foci))


def first_author(article, year):
    author = article.find(".//contrib-group/contrib[@contrib-type='author']/name")
    surname = author.findtext("surname")
    initial = (author.findtext("given-names") or " ")[0]
    return f"{surname} {initial}, {year}".replace("  ", " ")


def fetch_article(pmc):
    r = requests.get(f"{EUTILS}/efetch.fcgi", params={"db": "pmc", "id": pmc, "retmode": "xml", "tool": EUTILS_TOOL}, timeout=120)
    r.raise_for_status()
    time.sleep(0.4)
    return ET.fromstring(r.content).find(".//article")


def extract(spec, screened):
    exps, coords, review = [], [], []
    for number, e in enumerate(spec["experiments"], 1):
        rec = screened.loc[e["record_id"]]
        pmc = re.search(r"PMC(\d+)", rec.pmc).group(1)
        article = fetch_article(pmc)
        foci, tables = [], []
        for part in e["tables"]:
            foci += table_foci(find_table(article, part["table"]), part["rows"], part["col"], part["mode"])
            tables.append(part["table"])
        foci = list(dict.fromkeys(foci))
        exp_id = f"pm{number:03d}"
        study = first_author(article, rec.year)
        group = f"{study} ({e['group']})" if e.get("group") else study
        exps.append({"exp_id": exp_id, "study_id": study, "doi": rec.doi, "subject_group": group, "table_or_figure": "; ".join(tables),
                     "contrast": e["contrast"], "contrast_type": e["contrast_type"], "n": e["n"], "mean_age": "", "space": e["space"],
                     "source": "pmc", "contrast_verified_by": ""})
        coords += [{"exp_id": exp_id, "x": x, "y": y, "z": z} for x, y, z in foci]
        review.append({"exp_id": exp_id, "record_id": e["record_id"], "study_id": study, "pmc": rec.pmc, "table": "; ".join(tables),
                       "rows": "; ".join(str(p["rows"]) for p in e["tables"]), "contrast": e["contrast"], "contrast_type": e["contrast_type"],
                       "n": e["n"], "space": e["space"], "n_foci": len(foci), "what_to_check": e["check"]})
    return pd.DataFrame(exps, columns=EXP_COLUMNS), pd.DataFrame(coords), pd.DataFrame(review)


def merge_accepted(review, draft_exps, draft_coords, exps, coords, verified_by):
    """Add the experiments answered yes to the analysis sheets, naming who accepted them. Returns the new sheets."""
    accepted = review.exp_id[(review.agree == "yes") & (review.exp_id != "")]
    already = set(accepted) & set(exps.exp_id)
    if already:
        raise SystemExit(f"already in experiments.csv: {sorted(already)}")
    new = draft_exps[draft_exps.exp_id.isin(accepted)].assign(contrast_verified_by=verified_by)
    return pd.concat([exps, new], ignore_index=True), pd.concat([coords, draft_coords[draft_coords.exp_id.isin(accepted)]], ignore_index=True)


def dropped_records(review):
    """Records with no accepted experiment. A paper giving two groups stays if either is accepted."""
    answered = review.groupby("record_id").agree.agg(lambda a: (a == "yes").any())
    return list(answered.index[~answered])


def apply_review(verified_by, date):
    """Move accepted experiments into the analysis sheets and mark dropped papers as excluded at full text."""
    read = lambda path: pd.read_csv(path, dtype=str, keep_default_na=False)
    review = read(DRAFT / "review.csv")
    exps, coords = merge_accepted(review, read(DRAFT / "experiments.csv"), read(DRAFT / "coordinates.csv"),
                                  read(HERE / "experiments.csv"), read(HERE / "coordinates.csv"), verified_by)
    brain = read(DRAFT / "brainmap_review.csv")
    exps.loc[exps.exp_id.isin(brain.exp_id[brain.agree == "yes"]), "contrast_verified_by"] = verified_by
    screened_path = HERE / "screening" / "full_text_check.csv"
    screened = read(screened_path)
    dropped = screened.record_id.isin(dropped_records(review))
    screened.loc[dropped, ["agree", "reason", "date"]] = ["no", "Dropped at extraction; see rq1_map/pmc_draft/review.csv", date]
    exps.to_csv(HERE / "experiments.csv", index=False)
    coords.to_csv(HERE / "coordinates.csv", index=False)
    screened.to_csv(screened_path, index=False)
    print(f"{len(exps)} experiments, {len(coords)} foci, {int(dropped.sum())} papers dropped")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", nargs=2, metavar=("VERIFIED_BY", "DATE"), help="move accepted rows into the analysis sheets")
    a = ap.parse_args()
    if a.apply:
        apply_review(*a.apply)
        return
    spec = yaml.safe_load((HERE / "extraction_spec.yaml").read_text())
    screened = pd.read_csv(HERE / "screening" / "full_text_check.csv", dtype=str, keep_default_na=False).set_index("record_id")
    exps, coords, review = extract(spec, screened)
    out = outside_brain(to_mni(exps, coords), load_mni152_brain_mask(resolution=2))
    outside = coords[out].groupby("exp_id").size()
    review["outside_brain_mask"] = review.exp_id.map(outside).fillna(0).astype(int)
    missing = pd.DataFrame([{"record_id": m["record_id"], "study_id": "", "pmc": screened.loc[m["record_id"], "pmc"], "n_foci": 0,
                             "what_to_check": m["reason"]} for m in spec["not_extracted"]])
    sheet = pd.concat([review, missing], ignore_index=True).reindex(columns=REVIEW_COLUMNS)
    for column in ("n", "n_foci", "outside_brain_mask"):  # unextracted rows leave blanks, which would turn these into floats
        sheet[column] = sheet[column].astype("Int64")
    DRAFT.mkdir(exist_ok=True)
    exps.to_csv(DRAFT / "experiments.csv", index=False)
    coords.to_csv(DRAFT / "coordinates.csv", index=False)
    review_path = DRAFT / "review.csv"
    if review_path.exists():  # her answers are never overwritten
        print(f"{review_path} exists; left as it is")
    else:
        sheet.to_csv(review_path, index=False)
    print(f"{len(exps)} experiments, {len(coords)} foci, {int(out.sum())} outside the brain mask, {len(missing)} papers not extracted")


if __name__ == "__main__":
    main()
