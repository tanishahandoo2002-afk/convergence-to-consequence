import nibabel as nib
import numpy as np
import pytest

from rq3_stimulation.simnibs.run_montages import layout, mask_mean, shape, site

EEG = {"F3", "Fp2", "P3", "P5", "AF4", "Cz"}


def montage(anode, cathode, other="", size="35", current="2"):
    return {"anode": anode, "cathode": cathode, "other_electrodes": other, "size_cm2": size, "current_mA": current}


def test_site_reads_eeg_names_and_off_head_returns():
    assert site("F3", EEG) == ("eeg", "F3")
    assert site("left shoulder", EEG) == ("mni", (-60, -30, -95))
    assert site("right cheek", EEG) == ("mni", (60, 25, -45))
    assert site("right amPFC", EEG) is None


def test_shape_uses_discs_for_small_electrodes_and_the_usual_rectangles():
    assert shape(35) == ("rect", [50.0, 70.0])
    form, dims = shape(1.13)
    assert form == "ellipse" and dims[0] == pytest.approx(12.0, abs=0.1)
    assert shape(25) == ("rect", [pytest.approx(50.0), pytest.approx(50.0)])


def test_layout_adds_listed_10_10_sites_as_anodes_and_notes_gaps():
    a, c, area = layout(montage("AF4", "Cz", other="P5; current is peak amplitude"), EEG)
    assert a == [("eeg", "AF4"), ("eeg", "P5")] and c == [("eeg", "Cz")] and area == 35
    assert layout(montage("", "Fp2"), EEG) == "electrode position missing"
    assert layout(montage("F3", "Fp2", current=""), EEG) == "current missing"
    assert "unknown electrode site" in layout(montage("F3", "right amPFC"), EEG)


def test_mask_mean_reads_the_field_under_the_mask(tmp_path):
    field = np.zeros((10, 10, 10))
    field[2:4, 2:4, 2:4] = 0.3
    mask = np.zeros((5, 5, 5))
    mask[1, 1, 1] = 1  # 2-mm voxel (1, 1, 1) is 1-mm voxel (2, 2, 2)
    nib.save(nib.Nifti1Image(field, np.eye(4)), tmp_path / "f.nii.gz")
    nib.save(nib.Nifti1Image(mask, np.diag([2, 2, 2, 1])), tmp_path / "m.nii.gz")
    assert mask_mean(tmp_path / "f.nii.gz", tmp_path / "m.nii.gz") == pytest.approx(0.3)


def test_field_check_flags_gaps_zeros_and_changed_masks():
    import hashlib
    from checks.check_rq3_fields import validate
    masks = {"memory.nii.gz": b"m", "control_md.nii.gz": b"c"}
    frozen = {k: hashlib.sha256(v).hexdigest() for k, v in masks.items()}
    row = lambda mid, a, b, note="": {"montage_id": mid, "head_model": "ernie", "field_map": a, "field_control": b, "note": note}
    good = [row("m1", "0.1", "0.05"), row("m2", "", "", "current missing")]
    assert validate({"m1", "m2"}, good, frozen, masks) == []
    errs = validate({"m1", "m2", "m3"}, [row("m1", "0", "0.05"), row("m2", "", "")], frozen, {**masks, "memory.nii.gz": b"x"})
    assert any("FROZEN" in e for e in errs) and any("m3" in e for e in errs)
    assert any("zero" in e for e in errs) and any("no note" in e for e in errs)
