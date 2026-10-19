import pandas as pd

from tools.second_look import second_look, write_second_look

HUMAN_COLS = ["record_id", "stage", "rater", "decision", "reason", "date"]


def setup(base, gemini, qwen=None, author=None):
    (base / "search").mkdir(parents=True)
    (base / "screening").mkdir()
    ids = list(gemini)
    pd.DataFrame({"record_id": ids, "title": [f"title {i}" for i in ids]}).to_csv(base / "search" / "records.csv", index=False)
    for name, dec in (("gemini", gemini), ("qwen", qwen)):
        if dec:
            pd.DataFrame({"record_id": list(dec), "rater": name, "decision": list(dec.values()),
                          "reason": [f"{name} says {d}" for d in dec.values()]}).to_csv(base / "screening" / f"ai_{name}.csv", index=False)
    rows = [[r, "title_abstract", "author", d, "", "2026-10-19"] for r, d in (author or {}).items()]
    pd.DataFrame(rows, columns=HUMAN_COLS).to_csv(base / "screening" / "human_decisions.csv", index=False)


def test_lists_author_excludes_that_an_ai_kept(tmp_path):
    setup(tmp_path,
          gemini={"a": "include", "b": "exclude", "c": "unsure", "d": "include"},
          qwen={"a": "exclude", "b": "exclude", "c": "exclude", "d": "include"},
          author={"a": "exclude", "b": "exclude", "c": "exclude", "d": "include"})
    out = second_look(tmp_path)
    assert list(out.record_id) == ["a", "c"]                    # b: both AIs excluded; d: author included
    assert out.set_index("record_id").loc["a", "gemini_reason"] == "gemini says include"
    assert (out.resolution == "").all()


def test_works_with_one_ai_log(tmp_path):
    setup(tmp_path, gemini={"a": "include", "b": "exclude"}, author={"a": "exclude", "b": "exclude"})
    out = second_look(tmp_path)
    assert list(out.record_id) == ["a"] and out.qwen.isna().all()


def test_rerun_keeps_filled_resolutions(tmp_path):
    setup(tmp_path, gemini={"a": "include", "c": "unsure"}, author={"a": "exclude"})
    write_second_look(tmp_path)
    p = tmp_path / "screening" / "second_look.csv"
    df = pd.read_csv(p, dtype=str, keep_default_na=False)
    df.loc[df.record_id == "a", ["resolution", "note"]] = ["exclude_confirmed", "encoding only"]
    df.to_csv(p, index=False)
    hd = tmp_path / "screening" / "human_decisions.csv"
    pd.concat([pd.read_csv(hd), pd.DataFrame([["c", "title_abstract", "author", "exclude", "", "2026-10-20"]],
                                             columns=HUMAN_COLS)]).to_csv(hd, index=False)
    write_second_look(tmp_path)
    out = pd.read_csv(p, dtype=str, keep_default_na=False).set_index("record_id")
    assert out.loc["a", "resolution"] == "exclude_confirmed" and out.loc["a", "note"] == "encoding only"
    assert out.loc["c", "resolution"] == ""


def test_check_screening_requires_resolutions(tmp_path):
    from checks.check_screening import check_second_look
    setup(tmp_path, gemini={"a": "include", "c": "unsure"}, author={"a": "exclude", "c": "exclude"})
    write_second_look(tmp_path)
    errors = check_second_look(tmp_path)
    assert any("a" in e and "c" in e and "resolution" in e for e in errors)
    p = tmp_path / "screening" / "second_look.csv"
    df = pd.read_csv(p, dtype=str, keep_default_na=False)
    df["resolution"] = ["include", "exclude_confirmed"]          # a resolved include, but author's latest is still exclude
    df.to_csv(p, index=False)
    assert any("a" in e and "human_decisions" in e for e in check_second_look(tmp_path))
    hd = tmp_path / "screening" / "human_decisions.csv"
    pd.concat([pd.read_csv(hd), pd.DataFrame([["a", "title_abstract", "author", "include", "second look", "2026-10-20"]],
                                             columns=HUMAN_COLS)]).to_csv(hd, index=False)
    assert check_second_look(tmp_path) == []
