import pandas as pd

from checks.check_rq3_extraction import validate


def sheets(k=5):
    eff = pd.DataFrame({
        "es_id": [f"e{i}" for i in range(k)], "study_id": [f"s{i}" for i in range(k)], "population": "healthy",
        "diagnostic_criteria": "", "design": "parallel", "stim": "tDCS", "montage_id": "m1", "timing": "offline",
        "sessions": 1, "test_name": "RAVLT", "test_type": "recall", "followup_days": 0, "n_active": 20,
        "n_sham": 20, "m_active": 10.0, "sd_active": 2.0, "m_sham": 9.0, "sd_sham": 2.0, "t_value": None,
        "higher_is_better": 1, "reported_g": None, "extracted_by": "TH", "checked_by": ["R2"] + [""] * (k - 1)})
    mont = pd.DataFrame({"montage_id": ["m1"], "anode": ["P3"], "cathode": ["Fp2"], "other_electrodes": [""],
                         "size_cm2": [25], "current_mA": [2.0], "type": ["tDCS"]})
    rob = pd.DataFrame({"study_id": eff.study_id, "d1_randomisation": "low", "d1b_carryover": "",
                        "d2_deviations": "low", "d3_missing": "some", "d4_measurement": "low",
                        "d5_selection": "low", "overall": "some"})
    return eff, mont, rob


def test_valid_sheets_pass():
    assert validate(*sheets())[0] == []


def test_row_without_means_or_t_error():
    eff, mont, rob = sheets()
    eff.loc[1, ["m_active", "sd_active"]] = None
    errors, _ = validate(eff, mont, rob)
    assert any("e1" in e and "means" in e for e in errors)
    eff.loc[1, "t_value"] = 1.2
    assert not any("e1" in e and "means" in e for e in validate(eff, mont, rob)[0])


def test_unknown_montage_error():
    eff, mont, rob = sheets()
    eff.loc[0, "montage_id"] = "m9"
    assert any("m9" in e for e in validate(eff, mont, rob)[0])


def test_crossover_needs_d1b():
    eff, mont, rob = sheets()
    eff.loc[2, "design"] = "crossover"
    assert any("s2" in e and "d1b" in e for e in validate(eff, mont, rob)[0])
    rob.loc[2, "d1b_carryover"] = "low"
    assert not any("d1b" in e for e in validate(eff, mont, rob)[0])


def test_checked_by_20_percent():
    eff, mont, rob = sheets(10)
    assert any("checked_by" in e for e in validate(eff, mont, rob)[0])
    eff.loc[1, "checked_by"] = "R2"
    assert not any("checked_by" in e for e in validate(eff, mont, rob)[0])


def test_sd_must_be_positive_and_enums():
    eff, mont, rob = sheets()
    eff.loc[3, "sd_sham"] = 0
    eff.loc[4, "test_type"] = "working memory"
    errors, _ = validate(eff, mont, rob)
    assert any("e3" in e and "SD" in e for e in errors) and any("e4" in e and "test_type" in e for e in errors)
