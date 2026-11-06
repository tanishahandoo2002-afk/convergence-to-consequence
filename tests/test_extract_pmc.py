import xml.etree.ElementTree as ET

import pandas as pd
import pytest

from rq1_map.extract_pmc import dropped_records, find_table, foci_in_row, merge_accepted, row_numbers, table_foci


def test_separate_cells_handle_printed_minus_signs_and_commas():
    assert foci_in_row(["Precuneus", "− 24", "–16,", "+36", "5.4"], 1, "sep") == [(-24.0, -16.0, 36.0)]


def test_negative_column_counts_from_the_right_when_cells_are_merged():
    assert foci_in_row(["", "−9", "−45", "+30", "5.02"], -4, "sep") == [(-9.0, -45.0, 30.0)]


def test_joint_cell_with_two_peaks():
    assert foci_in_row(["Calcarine", "−2,−62,18;2,−62,18"], 1, "joint") == [(-2.0, -62.0, 18.0), (2.0, -62.0, 18.0)]


def test_joint_cell_with_spaces():
    assert foci_in_row(["36 −90 −3"], 0, "joint") == [(36.0, -90.0, -3.0)]


@pytest.mark.parametrize("cells, col, mode", [(["Left", "5.4", "x", "3"], 1, "sep"), (["no peak"], 0, "joint"), (["10, 20"], 0, "joint"),
                                              (["-10, 20, 30 and more"], 0, "joint"), (["400", "20", "30"], 0, "sep")])
def test_anything_else_raises_rather_than_guessing(cells, col, mode):
    with pytest.raises(ValueError):
        foci_in_row(cells, col, mode)


def test_row_numbers():
    assert row_numbers("1-3,7") == [1, 2, 3, 7] and row_numbers(5) == [5]


def table():
    return ET.fromstring("<article><table-wrap><label>Table 2.</label><table><tbody>"
                         "<tr><td>Early</td></tr><tr><td>A</td><td>1</td><td>2</td><td>3</td></tr>"
                         "<tr><td>Late</td></tr><tr><td>B</td><td>1</td><td>2</td><td>3</td></tr>"
                         "<tr><td>C</td><td>4</td><td>5</td><td>6</td></tr></tbody></table></table-wrap></article>")


def test_chosen_rows_only_and_repeats_count_once():
    t = find_table(table(), "Table 2")
    assert table_foci(t, "1,3-4", 1, "sep") == [(1.0, 2.0, 3.0), (4.0, 5.0, 6.0)]
    assert table_foci(t, "4", 1, "sep") == [(4.0, 5.0, 6.0)]


def review_rows():
    return pd.DataFrame({"exp_id": ["pm001", "pm002", "pm003", ""], "record_id": ["a", "a", "b", "c"], "agree": ["no", "yes", "no", "no"]})


def test_only_accepted_experiments_are_merged_and_named():
    draft = pd.DataFrame({"exp_id": ["pm001", "pm002", "pm003"], "contrast_verified_by": ""})
    draft_coords = pd.DataFrame({"exp_id": ["pm001", "pm002"], "x": ["1", "2"]})
    exps, coords = merge_accepted(review_rows(), draft, draft_coords, pd.DataFrame({"exp_id": ["bm001"], "contrast_verified_by": ""}),
                                  pd.DataFrame({"exp_id": ["bm001"], "x": ["0"]}), "Someone")
    assert list(exps.exp_id) == ["bm001", "pm002"] and exps.contrast_verified_by.iloc[1] == "Someone" and exps.contrast_verified_by.iloc[0] == ""
    assert list(coords.exp_id) == ["bm001", "pm002"]
    with pytest.raises(SystemExit):  # running it twice must not add rows twice
        merge_accepted(review_rows(), draft, draft_coords, exps, coords, "Someone")


def test_a_paper_stays_if_either_of_its_groups_is_accepted():
    assert dropped_records(review_rows()) == ["b", "c"]


def test_missing_table_raises():
    with pytest.raises(ValueError):
        find_table(table(), "Table 9")
