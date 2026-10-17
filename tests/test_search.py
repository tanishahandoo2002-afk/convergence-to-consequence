from pathlib import Path

from tools.import_records import dedupe, read_ris
from tools.pubmed_search import parse_efetch

FIX = Path(__file__).parent / "fixtures"


def rec(**kw):
    base = {"record_id": "", "source": "t", "pmid": "", "doi": "", "title": "", "abstract": "", "year": ""}
    return base | kw


def test_parse_efetch():
    a, b = parse_efetch((FIX / "efetch_sample.xml").read_text())
    assert a["pmid"] == "11111111" and a["record_id"] == "pmid:11111111"
    assert a["doi"] == "10.1000/ABC.123"
    assert a["title"] == "Hippocampal activity during recollection."
    assert a["abstract"] == "First part. Second part."
    assert a["year"] == "2012"
    assert b["abstract"] == "" and b["doi"] == "" and b["year"] == "2015"


def test_dedupe_empty_doi_not_merged():
    out, removed = dedupe([rec(record_id="1", title="A study"), rec(record_id="2", title="Another study")])
    assert len(out) == 2 and removed == 0


def test_dedupe_same_doi_case_insensitive():
    out, removed = dedupe([rec(record_id="1", doi="10.1/AB", title="x"), rec(record_id="2", doi="10.1/ab", title="y")])
    assert [r["record_id"] for r in out] == ["1"] and removed == 1


def test_dedupe_same_pmid():
    out, removed = dedupe([rec(record_id="1", pmid="5", title="x"), rec(record_id="2", pmid="5", title="y")])
    assert removed == 1


def test_dedupe_title_needs_same_year():
    t = "Recollection: an fMRI study!"
    out, _ = dedupe([rec(record_id="1", title=t, year="2010"), rec(record_id="2", title=t.lower(), year="2012")])
    assert len(out) == 2
    out, removed = dedupe([rec(record_id="1", title=t, year="2010"), rec(record_id="2", title=t.lower(), year="2010")])
    assert removed == 1


def test_read_ris():
    a, b = read_ris(FIX / "sample.ris")
    assert a["title"] == "Angular gyrus and recollection" and a["doi"] == "10.2000/xyz" and a["year"] == "2019"
    assert a["abstract"] == "We scanned twenty adults." and a["record_id"] == "doi:10.2000/xyz"
    assert b["title"] == "Familiarity signals in perirhinal cortex" and b["year"] == "2008"
    assert b["record_id"].startswith("src:")


def test_check_search_detects_row_mismatch(tmp_path):
    from checks.check_search import check
    (tmp_path / "search_log.csv").write_text("date,source,query,hits,file\n2026-10-18,pubmed,q,3,p.csv\n")
    (tmp_path / "p.csv").write_text("record_id,source,pmid,doi,title,abstract,year\npmid:1,pubmed,1,,t,,2020\n")
    (tmp_path / "records.csv").write_text("record_id,source,pmid,doi,title,abstract,year\npmid:1,pubmed,1,,t,,2020\n")
    errors = check(tmp_path)
    assert len(errors) == 1 and "logged 3 hits" in errors[0]
