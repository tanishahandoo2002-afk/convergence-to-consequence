import pytest

from tools.common import data_dir, load_config


def test_load_config_expands_env(tmp_path, monkeypatch):
    (tmp_path / "x.yaml").write_text('a: "${X}"\nb: [1, 2]\n')
    monkeypatch.setenv("X", "1")
    assert load_config("x", config_dir=tmp_path) == {"a": "1", "b": [1, 2]}


def test_load_config_missing_env_raises(tmp_path, monkeypatch):
    (tmp_path / "x.yaml").write_text('a: "${NOT_SET_C2C}"\n')
    monkeypatch.delenv("NOT_SET_C2C", raising=False)
    with pytest.raises(KeyError, match="NOT_SET_C2C"):
        load_config("x", config_dir=tmp_path)


def test_data_dir_requires_env(monkeypatch):
    monkeypatch.delenv("C2C_DATA", raising=False)
    with pytest.raises(RuntimeError):
        data_dir("rq1")


def test_data_dir_creates(tmp_path, monkeypatch):
    monkeypatch.setenv("C2C_DATA", str(tmp_path))
    assert data_dir("rq1", "pdfs") == tmp_path / "rq1" / "pdfs"
    assert (tmp_path / "rq1" / "pdfs").is_dir()
