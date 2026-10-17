import datetime
import math

import nibabel as nib
import numpy as np
import pytest

from masks.build_masks import freeze, subtract, top_half, verify_frozen

AFF = np.eye(4)


def img(data):
    return nib.Nifti1Image(np.asarray(data, dtype="float32"), AFF)


def rand_mask(seed, p=0.3):
    return img(np.random.default_rng(seed).random((10, 10, 10)) < p)


def test_top_half_at_most_half():
    mask = rand_mask(0)
    stat = img(np.random.default_rng(1).random((10, 10, 10)))
    out = np.asarray(top_half(stat, mask).dataobj) > 0
    m = np.asarray(mask.dataobj) > 0
    assert out.sum() <= math.ceil(m.sum() / 2) and out.sum() > 0
    assert not (out & ~m).any()


def test_subtract_disjoint():
    a, b = rand_mask(2, 0.5), rand_mask(3, 0.5)
    out = np.asarray(subtract(a, b).dataobj) > 0
    assert not (out & (np.asarray(b.dataobj) > 0)).any()
    assert set(np.unique(np.asarray(subtract(a, b).dataobj))) <= {0, 1}


@pytest.fixture
def files(tmp_path):
    paths = []
    for i in range(2):
        p = tmp_path / f"m{i}.nii.gz"
        rand_mask(i).to_filename(p)
        paths.append(p)
    return tmp_path, paths


def test_freeze_refuses_second_run(files):
    d, paths = files
    freeze(paths, refreeze=False, frozen_path=d / "FROZEN.sha256", changelog=d / "CHANGELOG.md")
    with pytest.raises(RuntimeError, match="frozen"):
        freeze(paths, refreeze=False, frozen_path=d / "FROZEN.sha256", changelog=d / "CHANGELOG.md")


def test_refreeze_requires_changelog_today(files):
    d, paths = files
    frozen, log = d / "FROZEN.sha256", d / "CHANGELOG.md"
    freeze(paths, refreeze=False, frozen_path=frozen, changelog=log)
    log.write_text("# Changelog\n2020-01-01 old entry\n")
    with pytest.raises(RuntimeError, match="CHANGELOG"):
        freeze(paths, refreeze=True, frozen_path=frozen, changelog=log)
    log.write_text(f"# Changelog\n{datetime.date.today().isoformat()} masks rebuilt because ...\n")
    freeze(paths, refreeze=True, frozen_path=frozen, changelog=log)


def test_verify_detects_change(files):
    d, paths = files
    frozen = d / "FROZEN.sha256"
    freeze(paths, refreeze=False, frozen_path=frozen, changelog=d / "CHANGELOG.md")
    assert verify_frozen(frozen_path=frozen) == []
    rand_mask(9).to_filename(paths[1])
    assert verify_frozen(frozen_path=frozen) == ["m1.nii.gz"]
    paths[0].unlink()
    assert verify_frozen(frozen_path=frozen) == ["m0.nii.gz", "m1.nii.gz"]


def test_check_masks_flags_overlap_and_missing_signoff(tmp_path):
    from nilearn.datasets import load_mni152_brain_mask
    from checks.check_masks import check
    brain = load_mni152_brain_mask(resolution=2)
    on = np.asarray(brain.dataobj) > 0
    region = np.zeros(on.shape, bool)
    region[40:50, 50:60, 40:50] = True
    region &= on
    for name in ["memory", "memory_top50", "control_md", "control_yeo"]:
        nib.Nifti1Image(region.astype("uint8"), brain.affine).to_filename(tmp_path / f"{name}.nii.gz")
    freeze([tmp_path / f"{n}.nii.gz" for n in ["memory", "memory_top50", "control_md", "control_yeo"]],
           refreeze=False, frozen_path=tmp_path / "FROZEN.sha256", changelog=tmp_path / "CHANGELOG.md")
    (tmp_path / "s.csv").write_text("date,step,item,who,result,note\n")
    errors = check(tmp_path, signoff_path=tmp_path / "s.csv")
    assert any("control_md" in e and "overlap" in e for e in errors)
    assert any("masks_frozen" in e for e in errors)


def test_yeo_label_ids_selects_ventral_attention_and_control():
    from masks.build_masks import yeo_label_ids
    lut = ("  0  NONE   0 0 0 0\n  1  7Networks_LH_Vis 120 18 134 0\n"
           "  6  7Networks_LH_SalVentAttn_ParOper 196 58 250 0\n 14  7Networks_LH_Cont_Par 230 148 34 0\n"
           " 23  7Networks_LH_Default_Par 205 62 78 0\n 40  7Networks_RH_Cont_Temp 230 148 35 0\n")
    assert yeo_label_ids(lut) == [6, 14, 40]
