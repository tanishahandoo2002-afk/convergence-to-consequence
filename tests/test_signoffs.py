from checks.signoffs import has_signoff, missing


def test_signoffs(tmp_path):
    p = tmp_path / "s.csv"
    p.write_text("date,step,item,who,result,note\n2026-10-18,s,a,TH,pass,\n")
    assert has_signoff("s", "a", path=p)
    assert not has_signoff("s", "b", path=p)
    assert missing("s", ["a", "b"], path=p) == ["b"]


def test_signoff_error_result_does_not_count(tmp_path):
    p = tmp_path / "s.csv"
    p.write_text("date,step,item,who,result,note\n2026-10-18,s,a,TH,error,wrong z\n")
    assert not has_signoff("s", "a", path=p)
