import nibabel as nib
import numpy as np
import pytest

from rq2_nsd.to_native import OUTSIDE, left_share, map_volume, to_template


def test_map_volume_reads_1_based_coordinates_and_drops_outside():
    vol = np.zeros((5, 6, 7))
    vol[2, 3, 4] = 1
    transform = np.full((2, 1, 1, 3), OUTSIDE, dtype=float)
    transform[0, 0, 0] = [3.2, 3.9, 5.4]        # rounds to 1-based (3, 4, 5) = 0-based (2, 3, 4)
    out = map_volume(vol, transform)
    assert out[0, 0, 0] == 1 and out[1, 0, 0] == 0
    transform[1, 0, 0] = [3, 4, 4.5]            # a tie rounds up, as nsdcode's map_coordinates does: z = 5
    assert map_volume(vol, transform)[1, 0, 0] == 1
    transform[1, 0, 0] = [3, 4, 99]             # past the edge of the source grid
    transform[0, 0, 0] = [np.nan, 4, 5]
    assert not map_volume(vol, transform).any()


def test_to_template_matches_world_coordinates():
    mask = np.zeros((4, 4, 4))
    mask[1, 2, 3] = 1                            # 2-mm voxel at world (2, 4, 6)
    template = nib.Nifti1Image(np.zeros((8, 8, 8)), np.diag([1, 1, 1, 1.0]))
    out = to_template(nib.Nifti1Image(mask, np.diag([2, 2, 2, 1.0])), template)
    assert out[2, 4, 6] and out.sum() == 8       # one 2-mm voxel fills eight 1-mm voxels


def test_left_share_detects_a_left_right_flip():
    aff = np.diag([-1, 1, 1, 1.0])
    aff[0, 3] = 9.5                              # world x = 9.5 - i, so i >= 15 is x < -5 (left)
    template = nib.Nifti1Image(np.zeros((20, 2, 2)), aff)
    native = np.zeros((2, 1, 1, 3))
    native[0, 0, 0] = [18, 1, 1]                 # 1-based i = 18: left
    native[1, 0, 0] = [2, 1, 1]                  # 1-based i = 2: right
    lh, rh = np.array([[[1]], [[0]]]), np.array([[[0]], [[1]]])
    assert left_share(template, native, lh, rh) == pytest.approx(1.0)
    assert left_share(template, native, rh, lh) == pytest.approx(0.0)


def test_check_native_flags_empty_overlapping_and_unsigned(tmp_path):
    from checks.check_rq2 import check_native
    cfg = {"subjects": [1], "masks": ["memory", "control_md"]}
    mem, ctrl = np.zeros((3, 3, 3), np.uint8), np.zeros((3, 3, 3), np.uint8)
    mem[0, 0, 0], ctrl[2, 2, 2] = 1, 1
    for name, d in (("memory", mem), ("control_md", ctrl)):
        nib.save(nib.Nifti1Image(d, np.eye(4)), tmp_path / f"subj01_{name}.nii.gz")
    signoffs = tmp_path / "signoffs.csv"
    signoffs.write_text("date,step,item,who,result,note\n2026-11-08,rq2_native_masks,subj01,author,pass,overlay\n")
    assert check_native(tmp_path, cfg, signoffs) == []
    ctrl[0, 0, 0] = 1
    nib.save(nib.Nifti1Image(ctrl, np.eye(4)), tmp_path / "subj01_control_md.nii.gz")
    nib.save(nib.Nifti1Image(np.zeros((3, 3, 3), np.uint8), np.eye(4)), tmp_path / "subj01_memory.nii.gz")
    signoffs.write_text("date,step,item,who,result,note\n")
    errors = " | ".join(check_native(tmp_path, cfg, signoffs))
    assert "subj01_memory.nii.gz is empty" in errors and "not signed off" in errors
    nib.save(nib.Nifti1Image(ctrl, np.eye(4)), tmp_path / "subj01_memory.nii.gz")
    assert any("overlap" in e for e in check_native(tmp_path, cfg, signoffs))
