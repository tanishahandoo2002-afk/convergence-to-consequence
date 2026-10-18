import pandas as pd
import pytest

from tools.calibrate import label_template, report, sample_ids


def test_sample_ids_seeded_unique():
    ids = [str(i) for i in range(1681)]
    a, b = sample_ids(ids, 30, seed=7), sample_ids(ids, 30, seed=7)
    assert a == b and len(a) == 30 and len(set(a)) == 30 and set(a) <= set(ids)
    assert sample_ids(ids, 30, seed=8) != a


def test_label_template_blank_decisions(tmp_path):
    recs = pd.DataFrame({"record_id": ["pmid:1", "pmid:2"], "title": ["A", "B"], "abstract": ["x", ""]})
    out = tmp_path / "labels.csv"
    label_template(recs, out)
    t = pd.read_csv(out, keep_default_na=False)
    assert list(t.columns) == ["record_id", "title", "decision", "note"] and (t.decision == "").all()
    with pytest.raises(SystemExit):
        label_template(recs, out)  # never overwrite her labels


def write_log(path, decisions, model="m"):
    pd.DataFrame({"record_id": [f"pmid:{i}" for i in range(len(decisions))], "rater": "qwen", "model": model,
                  "decision": decisions}).to_csv(path, index=False)


def test_report_kappa_and_unsure_rate(tmp_path):
    pd.DataFrame({"record_id": [f"pmid:{i}" for i in range(4)], "title": "t",
                  "decision": ["include", "exclude", "include", ""], "note": ""}).to_csv(tmp_path / "labels.csv", index=False)
    write_log(tmp_path / "ai_qwen_a.csv", ["include", "exclude", "include", "exclude"], model="a")
    write_log(tmp_path / "ai_qwen_b.csv", ["unsure", "unsure", "include", "include"], model="b")
    r = report(tmp_path).set_index("model")
    assert r.loc["a", "kappa"] == 1.0 and r.loc["a", "n_labelled"] == 3
    assert r.loc["b", "unsure_rate"] == pytest.approx(2 / 3, abs=1e-3)
    assert r.loc["b", "agree_or_unsure"] == pytest.approx(1.0)


def test_report_rejects_bad_labels(tmp_path):
    pd.DataFrame({"record_id": ["pmid:0"], "title": "t", "decision": ["maybe"], "note": ""}).to_csv(tmp_path / "labels.csv", index=False)
    write_log(tmp_path / "ai_qwen_a.csv", ["include"])
    with pytest.raises(SystemExit, match="maybe"):
        report(tmp_path)
