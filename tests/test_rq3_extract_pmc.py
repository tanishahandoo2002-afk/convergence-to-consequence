import pytest

from rq3_stimulation.extract_pmc import mean_sd


@pytest.mark.parametrize("cell, expected", [
    ("1.66 (0.53)", (1.66, 0.53)),
    ("23,13 ± 3,60", (23.13, 3.60)),       # decimal commas
    (".87 (.09)", (0.87, 0.09)),           # no leading zero
    ("8.05 ± 2.28**ΔΔ", (8.05, 2.28)),     # footnote markers after the SD
    ("−0.50 (1.20)", (-0.50, 1.20)),       # printed minus sign
    ("2.5 ± 2.1 b , c", (2.5, 2.1)),       # spaced footnote letters
    ("43.58 (+/−1.49)", (43.58, 1.49)),   # plus-minus written out
])
def test_mean_sd_reads_table_cells(cell, expected):
    assert mean_sd(cell) == pytest.approx(expected)


@pytest.mark.parametrize("cell", ["0.64", "9/6", "21.0 [19.0, 23.0]", "1.66 (0.53) 1.70 (0.60)"])
def test_mean_sd_rejects_other_cells(cell):
    with pytest.raises(ValueError):
        mean_sd(cell)


def test_median_iqr_converts_to_mean_and_sd():
    from rq3_stimulation.extract_pmc import median_iqr
    assert median_iqr("12.58 [2.73]") == pytest.approx((12.58, 2.73 / 1.35), abs=1e-4)
    assert median_iqr("13[3]") == pytest.approx((13, 3 / 1.35), abs=1e-4)
    with pytest.raises(ValueError):
        median_iqr("13 (3)")


def test_merge_review_keeps_answers_and_adds_new_rows():
    import pandas as pd
    from rq3_stimulation.extract_pmc import merge_review
    old = pd.DataFrame({"es_id": ["es001", None], "record_id": ["pmid:1", "pmid:2"], "test_name": ["t", None],
                        "what_to_check": [None, "r"],
                        "m_active": ["1.0", None], "sd_active": ["1.0", None], "m_sham": ["0.5", None],
                        "sd_sham": ["1.0", None], "agree": ["yes", "yes"]})
    new = pd.DataFrame({"es_id": ["es001", "es002", None], "record_id": ["pmid:1", "pmid:2", "pmid:3"],
                        "what_to_check": [None, None, "r3"],
                        "test_name": ["t", "u", None], "m_active": ["1.0", "2.0", None], "sd_active": ["1.0", "1.0", None],
                        "m_sham": ["0.5", "1.0", None], "sd_sham": ["1.0", "1.0", None], "agree": [None, None, None]})
    merged = merge_review(old, new)
    # pmid:2 now has an effect, so its old not-extracted row goes; es001 keeps its answer; pmid:3 is new
    assert list(merged.es_id.fillna("")) == ["es001", "es002", ""] and merged.agree.iloc[0] == "yes"
    assert list(merged.record_id) == ["pmid:1", "pmid:2", "pmid:3"]
    reworded = pd.concat([old.assign(what_to_check=[None, "old reason"]).iloc[[1]].assign(record_id="pmid:4"),
                          new.iloc[[0]]], ignore_index=True)
    fresh = pd.concat([new.iloc[[0]], new.iloc[[2]].assign(record_id="pmid:4", what_to_check="new reason")], ignore_index=True)
    again = merge_review(reworded.assign(what_to_check=reworded.get("what_to_check")), fresh.assign(what_to_check=fresh.get("what_to_check")))
    assert again[again.record_id == "pmid:4"].agree.isna().all()  # a changed reason drops the old answer
    changed = new.copy()
    changed.loc[0, "m_active"] = "9.9"
    with pytest.raises(SystemExit):
        merge_review(old, changed)
