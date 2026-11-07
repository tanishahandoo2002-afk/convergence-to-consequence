import pytest

from rq3_stimulation.extract_pmc import mean_sd


@pytest.mark.parametrize("cell, expected", [
    ("1.66 (0.53)", (1.66, 0.53)),
    ("23,13 ± 3,60", (23.13, 3.60)),       # decimal commas
    (".87 (.09)", (0.87, 0.09)),           # no leading zero
    ("8.05 ± 2.28**ΔΔ", (8.05, 2.28)),     # footnote markers after the SD
    ("−0.50 (1.20)", (-0.50, 1.20)),       # printed minus sign
    ("2.5 ± 2.1 b , c", (2.5, 2.1)),       # spaced footnote letters
    ("43.58 (+/−1.49)", (43.58, 1.49)),   # plus-minus written out
])
def test_mean_sd_reads_table_cells(cell, expected):
    assert mean_sd(cell) == pytest.approx(expected)


@pytest.mark.parametrize("cell", ["0.64", "9/6", "21.0 [19.0, 23.0]", "1.66 (0.53) 1.70 (0.60)"])
def test_mean_sd_rejects_other_cells(cell):
    with pytest.raises(ValueError):
        mean_sd(cell)
