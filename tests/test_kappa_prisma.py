import pandas as pd
import pytest

from tools.kappa import kappa
from tools.prisma import counts


def test_kappa_perfect():
    s = pd.Series(["include", "exclude", "unsure"], index=list("abc"))
    assert kappa(s, s) == (1.0, 3)


def test_kappa_known():
    a = pd.Series([1, 1, 0, 0], index=list("abcd"))
    b = pd.Series([1, 0, 0, 0], index=list("abcd"))
    k, n = kappa(a, b)
    assert k == pytest.approx(0.5) and n == 4


def test_kappa_uses_overlap_only():
    a = pd.Series([1, 0, 1], index=list("abc"))
    b = pd.Series([1, 0, 0], index=list("abz"))
    assert kappa(a, b) == (1.0, 2)


def write_rq(base, human_rows):
    (base / "search").mkdir(parents=True)
    (base / "screening").mkdir()
    (base / "search" / "search_log.csv").write_text(
        "date,source,query,hits,file\n2026-10-18,pubmed,q,5,p.csv\n2026-10-18,scopus,q,2,s.csv\n"
        "2026-10-18,dedupe,,1,records.csv\n")
    pd.DataFrame({"record_id": list("abcdef")}).to_csv(base / "search" / "records.csv", index=False)
    pd.DataFrame({"record_id": list("abcdef"), "asi": ["include"] * 2 + ["exclude"] * 4,
                  "qwen": ["include"] * 2 + ["exclude"] * 4, "merged": ["include"] * 2 + ["exclude"] * 4,
                  "needs_human": [True, True, True, False, False, False]}).to_csv(base / "screening" / "merged.csv", index=False)
    pd.DataFrame(human_rows, columns=["record_id", "stage", "rater", "decision", "reason", "date"]).to_csv(
        base / "screening" / "human_decisions.csv", index=False)


def test_prisma_reconciles(tmp_path):
    write_rq(tmp_path, [
        ["a", "title_abstract", "author", "include", "", ""], ["b", "title_abstract", "author", "include", "", ""],
        ["c", "title_abstract", "author", "include", "AI wrong", ""],
        ["a", "full_text", "author", "include", "", ""], ["b", "full_text", "author", "exclude", "no coords", ""],
        ["c", "full_text", "author", "include", "", ""]])
    c = counts(tmp_path)
    assert c["identified"] == 7 and c["duplicates_removed"] == 1 and c["screened"] == 6
    assert c["excluded_title_abstract"] == 3 and c["full_text_assessed"] == 3
    assert c["excluded_full_text"] == 1 and c["included"] == 2
    assert c["identified"] - c["duplicates_removed"] == c["screened"]
    assert c["screened"] - c["excluded_title_abstract"] == c["full_text_assessed"]
    assert c["full_text_assessed"] - c["excluded_full_text"] == c["included"]


def test_check_screening_flags_missing_human(tmp_path):
    from checks.check_screening import check
    write_rq(tmp_path, [["a", "title_abstract", "author", "include", "", ""]])
    pd.DataFrame({"record_id": ["a"]}).to_csv(tmp_path / "screening" / "second_rater_sample.csv", index=False)
    errors = check(tmp_path)
    assert any("b" in e and "author decision" in e for e in errors)
    assert any("second rater" in e for e in errors)


def review_sheet(tmp_path):
    from tools.screen import merge, write_review_sheet
    write_rq(tmp_path, [])
    records = pd.DataFrame({"record_id": list("abcdef"), "title": list("ABCDEF"), "abstract": "x", "year": "2020", "doi": ""})
    suggestions = pd.DataFrame({"record_id": list("abcdef"), "ai_suggestion": ["include"] * 3 + ["exclude"] * 3,
                                "ai_confidence": "low", "ai_reasoning": "why"})
    a = pd.Series(["include"] * 2 + ["exclude"] * 4, index=list("abcdef"))
    m = merge(a, a, seed=1, frac=0.25)
    path = tmp_path / "screening" / "human_decisions.csv"
    path.unlink()
    assert write_review_sheet(m.index[m.needs_human], records, suggestions, path, seed=1)
    return m, records, suggestions, path


def test_review_sheet_shows_suggestions_not_raters_and_is_kept(tmp_path):
    from checks.check_screening import check
    from tools.screen import write_review_sheet
    m, records, suggestions, path = review_sheet(tmp_path)
    sheet = pd.read_csv(path, dtype=str)
    assert set(sheet.record_id) == set(m.index[m.needs_human])
    assert sheet.ai_reasoning.notna().all()
    assert not {"asi", "qwen", "merged", "needs_human"} & set(sheet.columns)
    # a blank row is not a decision, so the check still asks for it
    pd.DataFrame({"record_id": ["a"]}).to_csv(tmp_path / "screening" / "second_rater_sample.csv", index=False)
    assert any(f"{len(sheet)} records need an author decision" in e for e in check(tmp_path))
    # a rerun of the merge must not wipe her answers
    assert not write_review_sheet(m.index[m.needs_human], records, suggestions, path, seed=1)


def test_yes_keeps_the_suggestion_and_no_reverses_it(tmp_path):
    from tools.kappa import human
    _, _, _, path = review_sheet(tmp_path)
    sheet = pd.read_csv(path, dtype=str)
    answers = {"a": "yes", "b": " No ", "c": "maybe"}
    sheet["agree"] = sheet.record_id.map(answers)
    sheet.to_csv(path, index=False)
    assert human(tmp_path, "author").to_dict() == {"a": "include", "b": "exclude"}


def test_review_sheet_refuses_a_missing_suggestion(tmp_path):
    from tools.screen import merge, write_review_sheet
    records = pd.DataFrame({"record_id": ["a"], "title": "A", "abstract": "x", "year": "2020", "doi": ""})
    a = pd.Series(["include"], index=["a"])
    empty = pd.DataFrame(columns=["record_id", "ai_suggestion", "ai_confidence", "ai_reasoning"], dtype=str)
    m = merge(a, a, seed=1, frac=0.2)
    with pytest.raises(SystemExit):
        write_review_sheet(m.index[m.needs_human], records, empty, tmp_path / "h.csv", seed=1)


def second_look(tmp_path, agree):
    """Record f is an agreed exclude outside the author's sample that the second look suggests keeping."""
    write_rq(tmp_path, [[r, "title_abstract", "author", "include", "", ""] for r in "abc"])
    pd.DataFrame({"record_id": ["a"]}).to_csv(tmp_path / "screening" / "second_rater_sample.csv", index=False)
    scr = tmp_path / "screening"
    pd.DataFrame({"record_id": ["e", "f"], "ai_suggestion": ["exclude", "include"]}).to_csv(
        scr / "ai_suggestions_unseen.csv", index=False)
    pd.DataFrame({"record_id": ["f"], "stage": "title_abstract", "rater": "author", "ai_suggestion": "include",
                  "agree": [agree], "decision": [""]}).to_csv(scr / "human_decisions_second_look.csv", index=False)


def test_second_look_yes_goes_on_to_full_text(tmp_path):
    from tools.prisma import title_abstract_decisions
    second_look(tmp_path, "yes")
    assert title_abstract_decisions(tmp_path)["f"] == "include"
    assert title_abstract_decisions(tmp_path)["e"] == "exclude"


def test_second_look_no_stays_excluded(tmp_path):
    from tools.prisma import title_abstract_decisions
    second_look(tmp_path, "no")
    assert title_abstract_decisions(tmp_path)["f"] == "exclude"


def test_second_look_answers_stay_out_of_ai_author_kappa(tmp_path):
    from tools.kappa import report
    second_look(tmp_path, "yes")
    out = report(tmp_path).set_index("pair").n
    assert out["asi-author"] == 3 and out["qwen-author"] == 3


def test_check_asks_for_second_look_decisions(tmp_path):
    from checks.check_screening import check
    second_look(tmp_path, "")
    assert any("f" in e and "author decision" in e for e in check(tmp_path))
    second_look_answered = tmp_path / "answered"
    second_look(second_look_answered, "yes")
    assert not any("author decision" in e for e in check(second_look_answered))


def test_second_rater_sheet_is_blind_kept_and_counted(tmp_path):
    from tools.kappa import SECOND_RATER_SHEET, human, make_second_rater_sheet
    write_rq(tmp_path, [])
    scr = tmp_path / "screening"
    pd.DataFrame({"record_id": list("abcdef"), "title": list("ABCDEF"), "abstract": "x", "year": "2020", "doi": ""}).to_csv(
        tmp_path / "search" / "records.csv", index=False)
    pd.DataFrame({"record_id": ["a", "e"]}).to_csv(scr / "second_rater_sample.csv", index=False)
    assert make_second_rater_sheet(tmp_path, seed=1)
    sheet = pd.read_csv(scr / SECOND_RATER_SHEET, dtype=str)
    assert set(sheet.record_id) == {"a", "e"} and (sheet.rater == "second").all()
    assert not {"asi", "qwen", "merged", "needs_human", "ai_suggestion", "ai_confidence", "ai_reasoning", "agree"} & set(sheet.columns)
    assert human(tmp_path, "second").empty
    sheet.loc[sheet.record_id == "a", "decision"] = "include"
    sheet.to_csv(scr / SECOND_RATER_SHEET, index=False)
    assert human(tmp_path, "second").to_dict() == {"a": "include"}
    assert not make_second_rater_sheet(tmp_path, seed=1)
    assert human(tmp_path, "second").to_dict() == {"a": "include"}


def test_low_kappa_does_not_make_the_author_screen_everything(tmp_path):
    """The author reviews AI includes, unsures and a sample of excludes (CHANGELOG 2026-10-27); kappa is reported only."""
    from checks.check_screening import check
    write_rq(tmp_path, [[r, "title_abstract", "author", "exclude", "", ""] for r in "abc"])  # disagrees with the AIs on a and b
    pd.DataFrame({"record_id": ["a"]}).to_csv(tmp_path / "screening" / "second_rater_sample.csv", index=False)
    errors = check(tmp_path)
    assert not any("kappa" in e for e in errors)


def test_rerun_search_logged_twice_counts_once(tmp_path):
    from tools.import_records import build_records
    d = tmp_path / "search"
    d.mkdir()
    (d / "p.csv").write_text("record_id,source,pmid,doi,title,abstract,year\npmid:1,pubmed,1,,A,,2020\npmid:2,pubmed,2,,B,,2021\n")
    (d / "search_log.csv").write_text("date,source,query,hits,file\n2026-10-18,pubmed,q,2,p.csv\n2026-10-18,pubmed,q,2,p.csv\n")
    n, removed = build_records(d)
    assert (n, removed) == (2, 0)
    write_rq(tmp_path / "rq", [])
    log = tmp_path / "rq" / "search" / "search_log.csv"
    log.write_text(log.read_text() + "2026-10-18,pubmed,q,5,p.csv\n")
    assert counts(tmp_path / "rq")["identified"] == 7
