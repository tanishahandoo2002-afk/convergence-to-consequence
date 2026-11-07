"""Read RQ3 means and SDs straight from PMC table XML into draft sheets, for the author to review.

extraction_spec.yaml names the table cell for each arm of each effect, and gives the study facts, montages and
RoB 2 ratings. The means and SDs come only from the table XML, so no person or model retypes them. For results
shown only in a figure, digitise.py measures the plotted point and error bar from approximate pixel positions. Nothing
reaches effects.csv until the author has answered the review sheet.
CLI: python -m rq3_stimulation.extract_pmc
     python -m rq3_stimulation.extract_pmc --apply "<who accepted>"   # after the review sheet is answered
"""
import io
import re
import sys
from pathlib import Path

import pandas as pd
import yaml

from rq1_map.extract_pmc import cell_text, clean, fetch_article, find_table, first_author
from rq3_stimulation.digitise import fetch_figure, read_point

HERE = Path(__file__).resolve().parent
DRAFT = HERE / "draft"
NUM = r"-?(?:\d+(?:[.,]\d+)?|[.,]\d+)"
# "12.3 (2.1)", "12.3 ± 2.1"; markers after the SD (*, Δ, letters) are footnotes, not data
MEAN_SD = re.compile(rf"^({NUM})\s*(?:\(\s*±?|±)\s*({NUM})\)?(?:[\s,]*[*Δa-zA-Z†‡§]+)*\s*$")
EFFECT_COLUMNS = ["es_id", "study_id", "population", "diagnostic_criteria", "design", "stim", "montage_id", "timing",
                  "sessions", "test_name", "test_type", "followup_days", "n_active", "n_sham", "m_active", "sd_active",
                  "m_sham", "sd_sham", "t_value", "higher_is_better", "reported_g", "extracted_by", "checked_by"]
MONTAGE_COLUMNS = ["montage_id", "anode", "cathode", "other_electrodes", "size_cm2", "current_mA", "type"]
ROB_COLUMNS = ["study_id", "d1_randomisation", "d1b_carryover", "d2_deviations", "d3_missing", "d4_measurement",
               "d5_selection", "overall"]
REVIEW_COLUMNS = ["es_id", "record_id", "study_id", "link", "table", "active_cell", "sham_cell", "test_name", "n_active",
                  "n_sham", "m_active", "sd_active", "m_sham", "sd_sham", "t_value", "what_to_check", "agree", "reason", "date"]
EXTRACTED_BY = "extract_pmc.py from AI-chosen table cells"
DIGITISED_BY = "digitise.py from AI-placed points on the figure"
TYPED_BY = "typed by an AI assistant from the text or PDF (location on the review sheet)"


def number(text):
    # a comma is a decimal mark here: thousands separators do not occur in these memory scores
    return float(text.replace(",", "."))


def mean_sd(cell):
    m = MEAN_SD.match(clean(re.sub(r"\+\s*/\s*[-−]", "±", cell)))
    if not m:
        raise ValueError(f"not a mean and SD: {cell!r}")
    return number(m.group(1)), number(m.group(2))


MEDIAN_IQR = re.compile(rf"^({NUM})\s*\[\s*({NUM})\s*\]$")


def median_iqr(cell):
    """Mean and SD approximated from 'median [IQR width]': mean = median, SD = IQR / 1.35, which assumes a roughly
    normal distribution (CHANGELOG 2026-11-08)."""
    m = MEDIAN_IQR.match(clean(cell))
    if not m:
        raise ValueError(f"not a median [IQR]: {cell!r}")
    return number(m.group(1)), round(number(m.group(2)) / 1.35, 4)


def table_cell(table, row, col):
    """Cell text at [row, col] of the table body, counting from 0 as the review sheet shows them."""
    return cell_text(list(table.findall(".//tbody/tr")[row])[col])


def arm_mean_sd(table, cells):
    """Mean and SD of one arm from [row, col], or from a list of cells when the test is reported only by
    within-subject sub-condition: then the means and the SDs are each averaged. Averaging SDs overstates the SD
    of the averaged score, so g is pulled towards zero (CHANGELOG 2026-11-08). A {mean: [r, c], sd: [r, c]}
    entry reads a table that puts the mean and the SD in separate columns."""
    if isinstance(cells, dict):
        return tuple(number(clean(table_cell(table, *cells[k]))) for k in ("mean", "sd"))
    if isinstance(cells[0], int):
        return mean_sd(table_cell(table, *cells))
    values = [arm_mean_sd(table, c) for c in cells]
    return tuple(round(sum(v[i] for v in values) / len(values), 4) for i in (0, 1))


def figure_href(article, label):
    norm = lambda t: re.sub(r"\s+", " ", t or "").strip()  # some labels use a non-breaking space
    figs = [f for f in article.iter("fig") if norm(f.findtext("label")) == norm(label)]
    if len(figs) != 1:
        raise ValueError(f"expected one {label}, found {len(figs)}")
    return figs[0].find("graphic").get("{http://www.w3.org/1999/xlink}href")


STATS = ("m_active", "sd_active", "m_sham", "sd_sham")


def arm_values(article, pmc, e):
    """Means and SDs (or a t value) from a table cell, a plotted point, or values typed from the text or a PDF
    where neither exists; the review sheet names where each typed value is. Returns (stats, source, extracted_by)."""
    if "typed" in e:
        stats = {k: float(v) for k, v in e["typed"].items()}
        if e.get("spread") == "se":
            stats["sd_active"] = round(stats["sd_active"] * e["n_active"] ** 0.5, 4)
            stats["sd_sham"] = round(stats["sd_sham"] * e.get("n_sham_group", e["n_sham"]) ** 0.5, 4)
        return stats, f"typed: {e['where']}", TYPED_BY
    if "table" in e:
        table = find_table(article, e["table"])
        # some papers give each arm its own table (e.g. paired pre/post statistics per group)
        sham_table = find_table(article, e["sham_table"]) if "sham_table" in e else table
        if e.get("spread") == "iqr":
            (m_a, s_a), (m_s, s_s) = median_iqr(table_cell(table, *e["active"])), median_iqr(table_cell(sham_table, *e["sham"]))
        else:
            (m_a, s_a), (m_s, s_s) = arm_mean_sd(table, e["active"]), arm_mean_sd(sham_table, e["sham"])
        if e.get("spread") == "se":  # the table gives SEs: SD = SE * sqrt(n)
            # a split sham n is for weighting; the SE was computed on the whole sham group
            s_a, s_s = round(s_a * e["n_active"] ** 0.5, 4), round(s_s * e.get("n_sham_group", e["n_sham"]) ** 0.5, 4)
        note = {"se": " (SE converted to SD)", "iqr": " (median and IQR converted to mean and SD)"}.get(e.get("spread"), "")
        source = e["table"] + note
        return dict(zip(STATS, (m_a, s_a, m_s, s_s))), source, EXTRACTED_BY
    image = fetch_figure(pmc, figure_href(article, e["figure"]))
    centre = e.get("centre", "marker")

    def arm(points, n, color, how):
        # a list of points is a test plotted by within-subject sub-condition: means and SDs are averaged, as for tables
        points = points if isinstance(points[0], list) else [points]
        # a point given as [x, y, mode] overrides the arm's mode, for bars of different fills in one arm
        read = [read_point(image, e["ticks"], p[:2], e["bar"], n, color, p[2] if len(p) > 2 else how) for p in points]
        return sum(r[0] for r in read) / len(read), sum(r[1] for r in read) / len(read)

    active = arm(e["active"], e["n_active"], e.get("active_color"), e.get("active_centre", centre))
    sham = arm(e["sham"], e.get("n_sham_group", e["n_sham"]), e.get("sham_color"), e.get("sham_centre", centre))
    values = (round(float(v), 3) for v in (*active, *sham))
    return dict(zip(STATS, values)), f"{e['figure']} (digitised, {e['bar']} bars)", DIGITISED_BY


def extract(spec, sheet):
    effects, montages, rob, review = [], [], [], []
    for s in spec["studies"]:
        rec = sheet.loc[s["record_id"]]
        m = re.search(r"PMC(\d+)", rec.link)
        # studies read from a free PDF have no PMC XML, so their values are typed and the spec names the study
        pmc, article = (m.group(1), fetch_article(m.group(1))) if m else (None, None)
        study = s.get("study_id") or first_author(article, rec.year)
        ids = {}
        for key, m in s["montages"].items():
            ids[key] = f"m{len(montages) + 1:03d}"
            montages.append({"montage_id": ids[key]} | m)
        rob.append({"study_id": study} | s["rob2"])
        for e in s["effects"]:
            stats, source, by = arm_values(article, pmc, e)
            es_id = f"es{len(effects) + 1:03d}"
            # stim follows the arm's montage, so a study with tDCS and tACS arms codes each arm correctly
            effects.append({"es_id": es_id, "study_id": study, "montage_id": ids[e["montage"]], "extracted_by": by,
                            "stim": s["montages"][e["montage"]]["type"]}
                           | stats
                           | {k: s[k] for k in ("population", "diagnostic_criteria", "design")}
                           | {"timing": e.get("timing", s["timing"])}  # experiments in one paper can differ
                           | {k: e[k] for k in ("sessions", "test_name", "test_type", "followup_days", "n_active",
                                                "n_sham", "higher_is_better")})
            review.append({"es_id": es_id, "record_id": s["record_id"], "study_id": study, "link": rec.link,
                           "table": source, "active_cell": str(e.get("active", "")), "sham_cell": str(e.get("sham", "")),
                           "what_to_check": "; ".join(filter(None, [s.get("check"), e.get("check")]))}
                          | {k: effects[-1].get(k) for k in ("test_name", "n_active", "n_sham", *STATS, "t_value")})
    return (pd.DataFrame(effects, columns=EFFECT_COLUMNS), pd.DataFrame(montages, columns=MONTAGE_COLUMNS),
            pd.DataFrame(rob, columns=ROB_COLUMNS), pd.DataFrame(review, columns=REVIEW_COLUMNS))


def merge_review(old, new):
    """Keep every answered row; add rows for new effects and newly listed studies; drop a study's
    not-extracted row once it has effects, and replace one whose reason has changed. Raises if an answered effect no longer matches its values, which
    would mean es_ids shifted."""
    keys = ["test_name", "m_active", "sd_active", "m_sham", "sd_sham"]
    new_fx, old_fx = new[new.es_id.notna()], old[old.es_id.notna()]
    both = old_fx.merge(new_fx, on="es_id", suffixes=("", "_new"))
    for k in keys:
        changed = both[both[k].astype(str) != both[k + "_new"].astype(str)]
        if len(changed):
            raise SystemExit(f"answered rows changed ({k}): {list(changed.es_id)[:5]}")
    extracted = set(new_fx.record_id)
    # a not-extracted row keeps its answer only while its reason is unchanged; a new reason needs a new answer
    reasons = dict(zip(new.record_id[new.es_id.isna()], new.what_to_check[new.es_id.isna()]))
    old_missing = old[old.es_id.isna() & ~old.record_id.isin(extracted)]
    old_missing = old_missing[old_missing.what_to_check == old_missing.record_id.map(reasons)]
    new_missing = new[new.es_id.isna() & ~new.record_id.isin(set(old_missing.record_id))]
    added = pd.concat([new_fx[~new_fx.es_id.isin(set(old_fx.es_id))], new_missing], ignore_index=True)
    return pd.concat([old_fx, added[added.es_id.notna()], old_missing, added[added.es_id.isna()]], ignore_index=True)


def apply_review(accepted_by):
    """Copy the effects answered yes, with their montages and RoB 2 rows, into the analysis sheets."""
    read = lambda f: pd.read_csv(DRAFT / f, dtype=str, keep_default_na=False)
    review = read("review.csv")
    yes = set(review.es_id[(review.agree == "yes") & (review.es_id != "")])
    effects = read("effects.csv")
    effects = effects[effects.es_id.isin(yes)].assign(checked_by=accepted_by)
    montages = read("montages.csv")
    rob = read("rob2.csv")
    effects.to_csv(HERE / "effects.csv", index=False)
    montages[montages.montage_id.isin(set(effects.montage_id))].to_csv(HERE / "montages.csv", index=False)
    rob[rob.study_id.isin(set(effects.study_id))].to_csv(HERE / "rob2.csv", index=False)
    print(f"{len(effects)} accepted effects from {effects.study_id.nunique()} studies copied to the analysis sheets")


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--apply":
        apply_review(sys.argv[2])
        return
    spec = yaml.safe_load((HERE / "extraction_spec.yaml").read_text())
    sheet = pd.read_csv(HERE / "screening" / "full_text_check.csv", dtype=str, keep_default_na=False).set_index("record_id")
    effects, montages, rob, review = extract(spec, sheet)
    missing = pd.DataFrame([{"record_id": m["record_id"], "link": sheet.loc[m["record_id"], "link"],
                             "what_to_check": m["reason"]} for m in spec.get("not_extracted", [])])
    DRAFT.mkdir(exist_ok=True)
    effects.to_csv(DRAFT / "effects.csv", index=False)
    montages.to_csv(DRAFT / "montages.csv", index=False)
    rob.to_csv(DRAFT / "rob2.csv", index=False)
    review_path = DRAFT / "review.csv"
    sheet_new = pd.concat([review, missing], ignore_index=True).reindex(columns=REVIEW_COLUMNS)
    if review_path.exists():  # her answers are kept; only new rows are added
        old = pd.read_csv(review_path, dtype=str, keep_default_na=False).replace("", None)
        # a CSV round trip puts the new rows in the same text form as the saved sheet
        roundtrip = pd.read_csv(io.StringIO(sheet_new.to_csv(index=False)), dtype=str, keep_default_na=False).replace("", None)
        sheet_new = merge_review(old, roundtrip)
    sheet_new.to_csv(review_path, index=False)
    print(f"{len(effects)} effects from {effects.study_id.nunique()} studies, {len(montages)} montages, "
          f"{len(missing)} studies not extracted")


if __name__ == "__main__":
    main()
