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
    pd.DataFrame({"record_id": list("abcdef"), "gemini": ["include"] * 2 + ["exclude"] * 4,
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
    errors = check(tmp_path, kappa_min=0.6)
    assert any("b" in e and "author decision" in e for e in errors)
    assert any("second rater" in e for e in errors)


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
