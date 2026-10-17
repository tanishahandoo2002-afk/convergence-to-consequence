import gzip

import nibabel as nib
import numpy as np
import pandas as pd
import pytest

from checks.check_rq2 import check_tables
from rq2_nsd.extract_trials import decode_betas, done_sessions, extract_session, mask_means, write_session

CFG = {"trials_per_session": 750, "s3_base": "https://example.invalid/", "extreme_z": 6,
       "beta_dirs": {"b3": "betas_fithrf_GLMdenoise_RR"}}
T = 750


def volume(seed=0):
    rng = np.random.default_rng(seed)
    data = rng.integers(-3000, 3000, size=(4, 4, 4, T)).astype(np.int16)
    data[0, 0, 0] = 300 * np.arange(1, T + 1) % 32000          # known ramp
    data[1, 1, 1] = 600                                        # constant voxel
    return nib.Nifti1Image(data, np.eye(4))


def gz(img):
    return gzip.compress(img.to_bytes())


def mask(*voxels):
    m = np.zeros((4, 4, 4), bool)
    for v in voxels:
        m[v] = True
    return m


def labels(n=T, session=1):
    return pd.DataFrame({"session": session, "run": 1, "trial": range(1, n + 1), "image": range(n), "viewing": 1,
                         "is_old": 0, "response_old": 0, "outcome": "cr", "rt": 800.0, "log_delay_s": np.nan,
                         "memory_recent": 0})


def test_decode_roundtrip():
    img = volume()
    assert np.array_equal(np.asarray(decode_betas(gz(img)).dataobj), np.asarray(img.dataobj))


def test_mask_means_zscored():
    img = volume()
    ramp = (np.asarray(img.dataobj)[0, 0, 0] / 300).astype(np.float64)
    z = (ramp - ramp.mean()) / ramp.std()
    out = mask_means(img, {"memory": mask((0, 0, 0), (1, 1, 1))})
    assert np.allclose(out.sig_memory, z, atol=1e-5)
    assert (out.n_vox_memory == 1).all()


def test_all_nan_trial_mean_is_nan():
    out = mask_means(volume(), {"memory": mask((1, 1, 1))})
    assert out.sig_memory.isna().all() and (out.n_vox_memory == 0).all()


def test_extract_session_rejects_wrong_trial_count():
    with pytest.raises(ValueError, match="subject 3 session 2"):
        extract_session(3, 2, labels(749, session=2), {"memory": mask((0, 0, 0))}, "b3", CFG, fetch=lambda u: gz(volume()))


def test_extract_session_builds_key_and_joins():
    urls = []
    out = extract_session(1, 1, labels(), {"memory": mask((0, 0, 0))}, "b3", CFG,
                          fetch=lambda u: urls.append(u) or gz(volume()))
    assert urls == ["https://example.invalid/nsddata_betas/ppdata/subj01/func1pt8mm/"
                    "betas_fithrf_GLMdenoise_RR/betas_session01.nii.gz"]
    assert len(out) == T and {"subject", "session", "beta", "outcome", "sig_memory"} <= set(out.columns)


def test_pilot_drops_outcomes():
    out = extract_session(1, 1, labels(), {"memory": mask((0, 0, 0))}, "b3", CFG, fetch=lambda u: gz(volume()), pilot=True)
    hidden = {"is_old", "response_old", "outcome", "rt", "log_delay_s", "viewing", "memory_recent"}
    assert not hidden & set(out.columns) and "sig_memory" in out.columns


def test_write_session_atomic_and_manifest(tmp_path):
    man = tmp_path / "manifest.csv"
    write_session(labels(), tmp_path, 1, 1, man, "k")
    assert (tmp_path / "subj01_sess01.csv").exists() and not list(tmp_path.glob("*.tmp"))
    assert done_sessions(man) == {(1, 1)} and len(pd.read_csv(man)) == 1


def test_check_tables_quality_report(tmp_path):
    a = labels().assign(subject=1, sig_memory=0.1)
    a.loc[:2, "sig_memory"] = np.nan
    a.to_csv(tmp_path / "subj01_sess01.csv", index=False)
    labels(749).assign(subject=1, session=2, sig_memory=0.1).to_csv(tmp_path / "subj01_sess02.csv", index=False)
    errors, q = check_tables(tmp_path, CFG)
    assert any("subj01_sess02" in e and "749" in e for e in errors)
    assert q.set_index("file").loc["subj01_sess01.csv", "n_nan_signal"] == 3


def test_full_extraction_refused_until_design_check_exists(monkeypatch):
    import rq2_nsd.extract_trials as et
    monkeypatch.setattr(et, "verify_frozen", lambda: [])
    monkeypatch.setattr("sys.argv", ["extract_trials", "--beta", "b3"])
    with pytest.raises(SystemExit, match="design"):
        et.main()
