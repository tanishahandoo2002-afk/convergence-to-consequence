import numpy as np
import pytest
from PIL import Image, ImageDraw

from rq3_stimulation.digitise import ink, read_point, sd_from_bar


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
    return ink(im)


def test_read_point_recovers_mean_and_sd():
    mean, sd = read_point(plot(), [[48, 102, 2], [48, 398, 0]], [151, 188], "sd", 20)
    assert mean == pytest.approx(1.4, abs=0.02) and sd == pytest.approx(0.3, abs=0.02)


def test_sd_from_se_and_ci():
    assert sd_from_bar(1.0, "se", 16) == pytest.approx(4.0)
    assert sd_from_bar(2.093, "ci95", 20) == pytest.approx(np.sqrt(20), rel=1e-3)
    with pytest.raises(ValueError):
        sd_from_bar(1.0, "iqr", 20)


def test_no_ink_near_point_fails():
    with pytest.raises(ValueError):
        read_point(plot(), [[48, 102, 2], [48, 398, 0]], [250, 300], "sd", 20)
