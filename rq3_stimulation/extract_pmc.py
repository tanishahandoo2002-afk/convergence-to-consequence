"""Read RQ3 means and SDs straight from PMC table XML into draft sheets, for the author to review.

extraction_spec.yaml names the table cell for each arm of each effect, and gives the study facts, montages and
RoB 2 ratings. The means and SDs come only from the table XML, so no person or model retypes them. Nothing
reaches effects.csv until the author has answered the review sheet.
CLI: python -m rq3_stimulation.extract_pmc
"""
import re
from pathlib import Path

import pandas as pd
import yaml

from rq1_map.extract_pmc import cell_text, clean, fetch_article, find_table, first_author

HERE = Path(__file__).resolve().parent
DRAFT = HERE / "draft"
NUM = r"-?(?:\d+(?:[.,]\d+)?|[.,]\d+)"
# "12.3 (2.1)", "12.3 ± 2.1"; markers after the SD (*, Δ, letters) are footnotes, not data
MEAN_SD = re.compile(rf"^({NUM})\s*(?:\(|±)\s*({NUM})\)?(?:\s*[*Δa-zA-Z†‡§]*)$")
EFFECT_COLUMNS = ["es_id", "study_id", "population", "diagnostic_criteria", "design", "stim", "montage_id", "timing",
                  "sessions", "test_name", "test_type", "followup_days", "n_active", "n_sham", "m_active", "sd_active",
                  "m_sham", "sd_sham", "t_value", "higher_is_better", "reported_g", "extracted_by", "checked_by"]
MONTAGE_COLUMNS = ["montage_id", "anode", "cathode", "other_electrodes", "size_cm2", "current_mA", "type"]
ROB_COLUMNS = ["study_id", "d1_randomisation", "d1b_carryover", "d2_deviations", "d3_missing", "d4_measurement",
               "d5_selection", "overall"]
REVIEW_COLUMNS = ["es_id", "record_id", "study_id", "link", "table", "active_cell", "sham_cell", "test_name", "n_active",
                  "n_sham", "m_active", "sd_active", "m_sham", "sd_sham", "what_to_check", "agree", "reason", "date"]
EXTRACTED_BY = "extract_pmc.py from AI-chosen table cells"


def number(text):
    # a comma is a decimal mark here: thousands separators do not occur in these memory scores
    return float(text.replace(",", "."))


def mean_sd(cell):
    m = MEAN_SD.match(clean(cell))
    if not m:
        raise ValueError(f"not a mean and SD: {cell!r}")
    return number(m.group(1)), number(m.group(2))


def table_cell(table, row, col):
    """Cell text at [row, col] of the table body, counting from 0 as the review sheet shows them."""
    return cell_text(list(table.findall(".//tbody/tr")[row])[col])


def extract(spec, sheet):
    effects, montages, rob, review = [], [], [], []
    for s in spec["studies"]:
        rec = sheet.loc[s["record_id"]]
        article = fetch_article(re.search(r"PMC(\d+)", rec.link).group(1))
        study = first_author(article, rec.year)
        ids = {}
        for key, m in s["montages"].items():
            ids[key] = f"m{len(montages) + 1:03d}"
            montages.append({"montage_id": ids[key]} | m)
        rob.append({"study_id": study} | s["rob2"])
        for e in s["effects"]:
            table = find_table(article, e["table"])
            m_active, sd_active = mean_sd(table_cell(table, *e["active"]))
            m_sham, sd_sham = mean_sd(table_cell(table, *e["sham"]))
            es_id = f"es{len(effects) + 1:03d}"
            effects.append({"es_id": es_id, "study_id": study, "montage_id": ids[e["montage"]],
                            "m_active": m_active, "sd_active": sd_active, "m_sham": m_sham, "sd_sham": sd_sham,
                            "extracted_by": EXTRACTED_BY}
                           | {k: s[k] for k in ("population", "diagnostic_criteria", "design", "stim", "timing")}
                           | {k: e[k] for k in ("sessions", "test_name", "test_type", "followup_days", "n_active",
                                                "n_sham", "higher_is_better")})
            review.append({"es_id": es_id, "record_id": s["record_id"], "study_id": study, "link": rec.link,
                           "table": e["table"], "active_cell": str(e["active"]), "sham_cell": str(e["sham"]),
                           "what_to_check": "; ".join(filter(None, [s.get("check"), e.get("check")]))}
                          | {k: effects[-1][k] for k in ("test_name", "n_active", "n_sham", "m_active", "sd_active",
                                                         "m_sham", "sd_sham")})
    return (pd.DataFrame(effects, columns=EFFECT_COLUMNS), pd.DataFrame(montages, columns=MONTAGE_COLUMNS),
            pd.DataFrame(rob, columns=ROB_COLUMNS), pd.DataFrame(review, columns=REVIEW_COLUMNS))


def main():
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
    if review_path.exists():  # her answers are never overwritten
        print(f"{review_path} exists; left as it is")
    else:
        pd.concat([review, missing], ignore_index=True).reindex(columns=REVIEW_COLUMNS).to_csv(review_path, index=False)
    print(f"{len(effects)} effects from {effects.study_id.nunique()} studies, {len(montages)} montages, "
          f"{len(missing)} studies not extracted")


if __name__ == "__main__":
    main()
