from pathlib import Path

import pandas as pd

from checks.check_rq1_extraction import validate
from rq1_map.coords import to_mni
from rq1_map.import_sleuth import read_sleuth
from rq1_map.spotcheck import make_sample

FIX = Path(__file__).parent / "fixtures"
CFG = {"min_experiments": 20, "hard_min_experiments": 17, "spotcheck_frac": 0.2, "seed": 1}
HEADER = "date,step,item,who,result,note\n"


def sheets(k=20, **override):
    exps = pd.DataFrame({
        "exp_id": [f"e{i}" for i in range(k)], "study_id": [f"s{i}" for i in range(k)], "doi": "",
        "subject_group": [f"g{i}" for i in range(k)], "table_or_figure": "Table 1", "contrast": "hits > CR",
        "contrast_type": "success", "n": "20", "mean_age": "24", "space": "MNI", "source": "table_tool",
        "contrast_verified_by": "TH"})
    for col, val in override.items():
        exps[col] = val
    coords = pd.DataFrame({"exp_id": exps.exp_id, "x": 0.0, "y": -20.0, "z": 10.0})
    return exps, coords


def run(exps, coords, tmp_path, signoffs="", sample=None):
    (tmp_path / "s.csv").write_text(HEADER + signoffs)
    sp = tmp_path / "sample.csv"
    pd.DataFrame({"exp_id": sample if sample is not None else []}).to_csv(sp, index=False)
    return validate(exps, coords, CFG, signoff_path=tmp_path / "s.csv", sample_path=sp)


def test_tal2mni_applied_only_to_tal():
    exps, coords = sheets(2)
    exps.loc[1, "space"] = "TAL"
    out = to_mni(exps, coords)
    assert tuple(out.loc[0, ["x", "y", "z"]]) == (0.0, -20.0, 10.0)
    assert tuple(out.loc[1, ["x", "y", "z"]]) != (0.0, -20.0, 10.0)


def test_duplicate_subject_group_error(tmp_path):
    exps, coords = sheets()
    exps.loc[3, "subject_group"] = "g2"
    errors, _ = run(exps, coords, tmp_path)
    assert any("g2" in e and "subject_group" in e for e in errors)


def test_n_must_be_int_ge_5(tmp_path):
    exps, coords = sheets()
    exps.loc[0, "n"], exps.loc[1, "n"] = "24 (12F)", "3"
    errors, _ = run(exps, coords, tmp_path)
    assert any("n must be an integer >= 5" in e and "e0" in e and "e1" in e for e in errors)


def test_experiment_without_foci_error(tmp_path):
    exps, coords = sheets()
    errors, _ = run(exps, coords[coords.exp_id != "e5"], tmp_path)
    assert any("no foci" in e and "e5" in e for e in errors)


def test_outside_brain_listed(tmp_path):
    exps, coords = sheets()
    coords = pd.concat([coords, pd.DataFrame({"exp_id": ["e0"], "x": [90.0], "y": [0.0], "z": [0.0]})])
    errors, _ = run(exps, coords, tmp_path)
    outside = [e for e in errors if "outside the brain" in e]
    assert len(outside) == 1 and "e0:90,0,0" in outside[0] and "0,-20,10" not in outside[0]
    errors, _ = run(exps, coords, tmp_path, signoffs="2026-10-18,rq1_outlier_focus,\"e0:90,0,0\",TH,pass,checked PDF\n")
    assert not any("outside the brain" in e for e in errors)


def test_count_thresholds(tmp_path):
    for k, n_err, n_warn in [(16, 1, 0), (18, 0, 1), (20, 0, 0)]:
        errors, warnings = run(*sheets(k), tmp_path)
        assert sum("experiments" in e and "fewer than" in e for e in errors) == n_err
        assert sum("experiments" in w for w in warnings) == n_warn


def test_unverified_contrast_error(tmp_path):
    exps, coords = sheets()
    exps.loc[4, "contrast_verified_by"] = ""
    errors, _ = run(exps, coords, tmp_path)
    assert any("contrast_verified_by" in e and "e4" in e for e in errors)


def test_spotcheck_error_requires_all(tmp_path):
    exps, coords = sheets()
    ok = "".join(f"2026-10-18,rq1_spotcheck,e{i},TH,pass,\n" for i in range(4))
    errors, _ = run(exps, coords, tmp_path, signoffs=ok, sample=["e0", "e1", "e2", "e3"])
    assert not any("spot-check" in e for e in errors)
    bad = ok + "2026-10-18,rq1_spotcheck,e1,TH,error,wrong z\n"
    errors, _ = run(exps, coords, tmp_path, signoffs=bad, sample=["e0", "e1", "e2", "e3"])
    assert any("spot-check" in e and "every experiment" in e for e in errors)


def test_make_sample_seeded_and_fixed(tmp_path):
    exps, _ = sheets()
    p = tmp_path / "sample.csv"
    ids = make_sample(exps, seed=1, frac=0.2, path=p)
    assert len(ids) == 4 and list(pd.read_csv(p).exp_id) == ids
    import pytest
    with pytest.raises(SystemExit):
        make_sample(exps, seed=1, frac=0.2, path=p)


def test_read_sleuth():
    e1, c1 = read_sleuth(FIX / "sleuth_mni.txt")
    e2, c2 = read_sleuth(FIX / "sleuth_tal.txt")
    assert list(e1.space) == ["MNI", "MNI"] and list(e2.space) == ["TAL"]
    assert list(e1.n) == ["16", "22"] and e1.contrast.iloc[1] == "Remember > Know"
    assert c1.groupby("exp_id").size().tolist() == [2, 1] and len(c2) == 1
    assert (e1.source == "brainmap").all() and (e1.contrast_verified_by == "").all()


def test_read_sleuth_joins_wrapped_and_pooled_contrasts():
    e, c = read_sleuth(FIX / "sleuth_wrapped.txt")
    assert list(e.study_id) == ["Lee T M C, 2002", "Smith A, 1999"]
    assert e.contrast.iloc[0] == ("Digit Memory Task - Answer Correctly vs. Feign Memory Impairment | "
                                  "Autobiographic Memory Task-Answer Correctly vs. Feign Memory Impairment")
    assert e.contrast.iloc[1] == "Hits vs. Correct Rejections"
    assert list(e.n) == ["6", "12"] and list(e.space) == ["TAL", "TAL"]
    assert c.groupby("exp_id").size().tolist() == [2, 1]


def test_drop_duplicate_blocks_keeps_distinct_groups():
    from rq1_map.import_sleuth import drop_duplicate_blocks
    exps = pd.DataFrame({"exp_id": ["a", "b", "c"], "study_id": ["S, 2003"] * 3, "n": ["12", "12", "12"],
                         "contrast": ["Hits > CR", "Hits > CR", "Older Normals"]})
    coords = pd.DataFrame({"exp_id": ["a", "a", "b", "b", "c"], "x": [1.0, 2, 1, 2, 9], "y": [0.0] * 5, "z": [0.0] * 5})
    e, c, removed = drop_duplicate_blocks(exps, coords)
    assert list(e.exp_id) == ["a", "c"] and removed == ["b"]          # b repeats a exactly; c is a different group
    assert sorted(c.exp_id.unique()) == ["a", "c"] and len(c) == 3
