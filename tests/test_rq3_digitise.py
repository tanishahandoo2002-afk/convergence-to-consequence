import numpy as np
import pytest
from PIL import Image, ImageDraw

from rq3_stimulation.digitise import read_point, sd_from_bar


def plot():
    """Axis with ticks at value 0 (row 400) and 2 (row 100); a point at value 1.4 with bar 1.1 to 1.7."""
    im = Image.new("RGB", (300, 450), "white")
    d = ImageDraw.Draw(im)
    for row in (100, 400):
        d.line([(45, row), (52, row)], fill="black", width=1)
    row = lambda v: 400 - v * 150
    d.line([(150, row(1.7)), (150, row(1.1))], fill="black", width=2)
    d.ellipse([144, row(1.4) - 6, 156, row(1.4) + 6], fill="black")
    d.ellipse([160, 60, 170, 70], fill=(200, 200, 200))  # a grey data dot, not ink
    d.line([(200, row(1.2)), (200, row(0.4))], fill=(40, 160, 40), width=2)  # a green series point at 0.8 +- 0.4
    d.ellipse([194, row(0.8) - 6, 206, row(0.8) + 6], fill=(40, 160, 40))
    return im


def test_read_point_recovers_mean_and_sd():
    mean, sd = read_point(plot(), [[48, 102, 2], [48, 398, 0]], [151, 188], "sd", 20)
    assert mean == pytest.approx(1.4, abs=0.02) and sd == pytest.approx(0.3, abs=0.02)


def test_read_point_follows_a_series_colour():
    mean, sd = read_point(plot(), [[48, 102, 2], [48, 398, 0]], [201, 280], "sd", 20, color=[40, 160, 40])
    assert mean == pytest.approx(0.8, abs=0.02) and sd == pytest.approx(0.4, abs=0.02)


def test_read_point_bar_mode_uses_whisker_midpoint():
    im = Image.new("RGB", (120, 450), "white")
    d = ImageDraw.Draw(im)
    for row in (100, 400):
        d.line([(10, row), (16, row)], fill="black")
    d.rectangle([50, 400 - 1.0 * 150, 90, 400], fill=(90, 90, 90))           # a dark grey bar of height 1.0
    d.line([(70, 400 - 1.2 * 150), (70, 400 - 0.8 * 150)], fill="black", width=2)  # whisker 0.8 to 1.2
    mean, sd = read_point(im, [[13, 100, 2], [13, 400, 0]], [70, 250], "sd", 20, color=[0, 0, 0], centre="bar")
    assert mean == pytest.approx(1.0, abs=0.02) and sd == pytest.approx(0.2, abs=0.02)


def test_sd_from_se_and_ci():
    assert sd_from_bar(1.0, "se", 16) == pytest.approx(4.0)
    assert sd_from_bar(2.093, "ci95", 20) == pytest.approx(np.sqrt(20), rel=1e-3)
    with pytest.raises(ValueError):
        sd_from_bar(1.0, "iqr", 20)


def test_no_ink_near_point_fails():
    with pytest.raises(ValueError):
        read_point(plot(), [[48, 102, 2], [48, 398, 0]], [250, 300], "sd", 20)
