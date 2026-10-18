from types import SimpleNamespace

import pandas as pd
import pytest

from tools.screen import build_messages, merge, parse_reply, run_rater, screen_record


class FakeClient:
    """Stands in for openai.OpenAI: returns scripted replies or raises."""

    def __init__(self, replies):
        self.replies, self.calls = list(replies), []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kw):
        self.calls.append(kw)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=reply))])


INC = '{"decision": "include", "reason": "hits > CR whole-brain"}'


def test_parse_reply_plain():
    assert parse_reply(INC) == {"decision": "include", "reason": "hits > CR whole-brain"}


def test_parse_reply_fenced():
    assert parse_reply("```json\n" + INC + "\n```")["decision"] == "include"


def test_parse_reply_bad_decision():
    assert parse_reply('{"decision": "maybe", "reason": "x"}') is None


def test_parse_reply_not_json():
    assert parse_reply("I think include") is None


def test_screen_record_retries_then_unsure():
    c = FakeClient(["nope", "still nope"])
    out = screen_record(c, "m", [{"role": "user", "content": "x"}])
    assert out["decision"] == "unsure" and out["reason"] == "invalid reply"
    assert len(c.calls) == 2 and all(k["temperature"] == 0 for k in c.calls)


def test_screen_record_api_error_propagates():
    with pytest.raises(RuntimeError):
        screen_record(FakeClient([RuntimeError("429")]), "m", [{"role": "user", "content": "x"}])


def test_merge_rule():
    idx = ["r1", "r2", "r3", "r4"]
    a = pd.Series(["include", "exclude", "include", "unsure"], index=idx)
    b = pd.Series(["include", "exclude", "exclude", "exclude"], index=idx)
    m = merge(a, b, seed=1, frac=1.0)
    assert list(m.merged) == ["include", "exclude", "unsure", "unsure"]
    assert m.needs_human.all()


def test_merge_exclude_sample_seeded():
    idx = [f"r{i}" for i in range(10)]
    ex = pd.Series(["exclude"] * 10, index=idx)
    m1, m2 = merge(ex, ex, seed=7, frac=0.2), merge(ex, ex, seed=7, frac=0.2)
    assert m1.needs_human.sum() == 2
    assert list(m1.index[m1.needs_human]) == list(m2.index[m2.needs_human])


def test_resume_skips_logged(tmp_path):
    recs = pd.DataFrame({"record_id": ["a", "b"], "title": ["T1", "T2"], "abstract": ["", ""]})
    log = tmp_path / "ai_qwen.csv"
    c = FakeClient([INC])
    run_rater(recs.iloc[:0], "qwen", c, "m", "crit", log)  # creates nothing
    pd.DataFrame([{"record_id": "a", "rater": "qwen", "model": "m", "prompt_sha256": "x", "timestamp": "t",
                   "decision": "exclude", "reason": "r", "raw": "{}"}]).to_csv(log, index=False)
    assert run_rater(recs, "qwen", c, "m", "crit", log) == 1
    assert len(c.calls) == 1 and "T2" in c.calls[0]["messages"][1]["content"]
    assert list(pd.read_csv(log).record_id) == ["a", "b"]


def test_api_error_writes_nothing(tmp_path):
    recs = pd.DataFrame({"record_id": ["a"], "title": ["T1"], "abstract": ["A"]})
    log = tmp_path / "ai_gemini.csv"
    with pytest.raises(RuntimeError):
        run_rater(recs, "gemini", FakeClient([RuntimeError("429")]), "m", "crit", log)
    assert not log.exists() or len(pd.read_csv(log)) == 0


def test_title_only_record():
    msgs = build_messages("CRITERIA", {"record_id": "a", "title": "Only a title", "abstract": float("nan")})
    assert "CRITERIA" in msgs[0]["content"] and '"decision"' in msgs[0]["content"]
    assert "Only a title" in msgs[1]["content"] and "None" not in msgs[1]["content"] and "nan" not in msgs[1]["content"]


from tools.screen import parse_contrast, pdf_text

CON = {"eligible": True, "table": "Table 2", "contrast": "hits > correct rejections",
       "contrast_type": "success", "n": 24, "reason": "whole-brain, MNI"}


def test_parse_contrast_valid():
    import json
    assert parse_contrast(json.dumps(CON)) == CON


def test_parse_contrast_bad_type():
    import json
    assert parse_contrast(json.dumps(CON | {"contrast_type": "encoding"})) is None


def test_parse_contrast_n_not_int():
    import json
    assert parse_contrast(json.dumps(CON | {"n": "24 (12F)"})) is None
    assert parse_contrast(json.dumps(CON | {"n": True})) is None


def test_pdf_text(tmp_path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig = plt.figure()
    fig.text(0.1, 0.5, "Table 2 hits versus correct rejections")
    fig.savefig(tmp_path / "p.pdf")
    assert "correct rejections" in pdf_text(tmp_path / "p.pdf")


def test_run_full_text_skips_missing_pdf_and_resumes(tmp_path):
    import json
    from tools.screen import run_full_text
    test_pdf_text(tmp_path)  # writes p.pdf
    (tmp_path / "p.pdf").rename(tmp_path / "pmid_1.pdf")
    out = tmp_path / "proposals.csv"
    c = FakeClient([json.dumps(CON)])
    assert run_full_text(["pmid:1", "pmid:2"], tmp_path, c, "m", "crit", out) == 1
    assert run_full_text(["pmid:1", "pmid:2"], tmp_path, c, "m", "crit", out) == 0
    assert len(c.calls) == 1 and "correct rejections" in c.calls[0]["messages"][1]["content"]


def test_run_rater_throttles_between_requests(tmp_path):
    recs = pd.DataFrame({"record_id": ["a", "b", "c"], "title": ["T1", "T2", "T3"], "abstract": ["", "", ""]})
    now, slept = [0.0], []

    def clock():
        return now[0]

    def sleep(s):
        slept.append(s)
        now[0] += s

    c = FakeClient([INC] * 3)
    run_rater(recs, "gemini", c, "m", "crit", tmp_path / "log.csv", min_interval=13, clock=clock, sleep=sleep)
    assert len(c.calls) == 3 and slept == [13, 13]          # no wait before the first request


def test_run_rater_no_throttle_by_default(tmp_path):
    recs = pd.DataFrame({"record_id": ["a", "b"], "title": ["T1", "T2"], "abstract": ["", ""]})
    slept = []
    run_rater(recs, "qwen", FakeClient([INC] * 2), "m", "crit", tmp_path / "log.csv", sleep=slept.append)
    assert slept == []
