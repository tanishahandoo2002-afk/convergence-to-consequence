"""Read a mean and SD from a plotted point and its error bar, for studies that report results only in figures.

The spec gives approximate pixel positions of two labelled axis ticks and of each point; the code snaps each to
the dark pixels of the tick mark, marker or error bar, and maps pixel rows to axis values. The figure is read
from the PMC CDN in memory and is not saved.
"""
import io
import re
import time

import numpy as np
import requests
from PIL import Image
from scipy.stats import t as t_dist

from tools.screen import EUTILS_TOOL

DARK = 100        # luminance below this is ink; light grey individual-data dots stay out
SEARCH = 4        # pixels either side of a given position to look for ink
MARKER_WIDTH = 5  # a row this wide in ink belongs to the marker, not the thin error bar
COLOR_TOLERANCE = 90  # summed RGB distance; JPEG edges blur a series colour by roughly this much


def fetch_figure(pmc, href):
    """The figure image from the article page's CDN link, held in memory."""
    stem = re.escape(href.rsplit(".", 1)[0])
    for attempt in range(6):  # the page often comes back without its figure links for a while; retry patiently
        page = requests.get(f"https://pmc.ncbi.nlm.nih.gov/articles/PMC{pmc}/", timeout=60,
                            headers={"User-Agent": EUTILS_TOOL})
        page.raise_for_status()
        m = re.search(rf'https://cdn\.ncbi\.nlm\.nih\.gov/pmc/blobs/[^"]*/{stem}\.\w+', page.text)
        if m:
            break
        time.sleep(20)
    else:
        raise ValueError(f"no CDN link for {href} on PMC{pmc}")
    r = requests.get(m.group(0), timeout=60, headers={"User-Agent": EUTILS_TOOL})
    r.raise_for_status()
    return Image.open(io.BytesIO(r.content)).convert("RGB")


def ink(image, color=None):
    """Dark pixels, or with a colour the pixels close to it, for plots whose series differ only by colour. A number
    instead of a colour is a luminance cut-off, for figures drawn in mid-grey."""
    if color is None or isinstance(color, (int, float)):
        return np.asarray(image.convert("L")) < (color or DARK)
    return np.abs(np.asarray(image, dtype=int) - np.array(color)).sum(axis=2) < COLOR_TOLERANCE


def _near(mask, x, y):
    """The inked pixel closest to (x, y) within SEARCH, or an error."""
    ys, xs = np.nonzero(mask[y - SEARCH:y + SEARCH + 1, x - SEARCH:x + SEARCH + 1])
    if not len(xs):
        raise ValueError(f"no ink near ({x}, {y})")
    i = np.argmin((xs - SEARCH) ** 2 + (ys - SEARCH) ** 2)
    return x - SEARCH + xs[i], y - SEARCH + ys[i]


def tick_row(mask, x, y):
    """Centre row of a horizontal tick mark near (x, y)."""
    x, y = _near(mask, x, y)
    rows = [r for r in range(y - SEARCH, y + SEARCH + 1) if mask[r, x - 1:x + 2].any()]
    return float(np.mean(rows))


def _run(mask, x, y, step):
    """Last row of the inked vertical run from (x, y) going up (-1) or down (+1); one-pixel gaps are bridged."""
    r = y
    while 0 <= r + step < mask.shape[0] and (mask[r + step, x - 1:x + 2].any() or mask[r + 2 * step, x - 1:x + 2].any()):
        r += step
    return r


def bar_ends(mask, x, y):
    """Top and bottom rows of the error bar through the marker near (x, y)."""
    x, y = _near(mask, x, y)
    return _run(mask, x, y, -1), _run(mask, x, y, 1)


def marker_row(mask, x, y):
    """Centre row of the marker near (x, y): the rows where the ink is wider than the error bar."""
    x, y = _near(mask, x, y)
    rows = []
    for r in range(y - 4 * SEARCH, y + 4 * SEARCH + 1):
        left = right = x
        while left > 0 and mask[r, left - 1]:
            left -= 1
        while right < mask.shape[1] - 1 and mask[r, right + 1]:
            right += 1
        if mask[r, x] and right - left + 1 >= MARKER_WIDTH:
            rows.append(r)
    if not rows:
        raise ValueError(f"no marker near ({x}, {y})")
    return float(np.mean(rows))


def axis(ticks):
    """Map a pixel row to a value from two (row, value) ticks."""
    (r1, v1), (r2, v2) = ticks
    return lambda row: v1 + (row - r1) * (v2 - v1) / (r2 - r1)


def sd_from_bar(half_width, kind, n):
    """SD from half an error bar: an SD bar is the SD; an SE bar times sqrt(n); a 95% CI bar via the t quantile."""
    if kind == "sd":
        return half_width
    if kind == "se":
        return half_width * np.sqrt(n)
    if kind == "ci95":
        return half_width / t_dist.ppf(0.975, n - 1) * np.sqrt(n)
    raise ValueError(f"unknown error bar: {kind}")


def read_point(image, ticks, point, kind, n, color=None, centre="marker"):
    """(mean, sd) of one plotted point. ticks: [[x, y, value], [x, y, value]]; point: [x, y] on the error bar;
    color: the colour of the marker and bar when they are not dark (or of a black whisker on a dark bar fill).
    centre "marker" takes the mean from the marker; "bar" takes it as the midpoint of a symmetric whisker, for
    bar charts, where the bar top has no marker."""
    # a tick given as [x, y, value, "exact"] is used as placed: for pale ticks or axes labelled without tick marks
    to_value = axis([(float(t[1]) if len(t) > 3 else tick_row(ink(image), t[0], t[1]), t[2]) for t in ticks])
    mask = ink(image, color)
    top, bottom = bar_ends(mask, *point)
    if centre == "bar_top":  # dark bar fill hides the lower whisker: mean at the bar's top edge, spread from the upper whisker
        mean_row = bar_top(mask, point[0], top)
        return to_value(mean_row), sd_from_bar(abs(to_value(top) - to_value(mean_row)), kind, n)
    if centre == "upper":  # the fill hides the lower whisker, so the visible whisker ends at the bar's top edge
        return to_value(bottom), sd_from_bar(abs(to_value(top) - to_value(bottom)), kind, n)
    half = abs(to_value(top) - to_value(bottom)) / 2
    mean = to_value((top + bottom) / 2) if centre == "bar" else to_value(marker_row(mask, *point))
    return mean, sd_from_bar(half, kind, n)


def bar_top(mask, x, top):
    """First row below the whisker top where the ink is as wide as a bar."""
    for r in range(int(top) + 3, mask.shape[0]):  # skip the whisker cap, which is also wide
        left = right = x
        while left > 0 and mask[r, left - 1]:
            left -= 1
        while right < mask.shape[1] - 1 and mask[r, right + 1]:
            right += 1
        if mask[r, x] and right - left + 1 >= 3 * MARKER_WIDTH:
            return float(r)
    raise ValueError(f"no bar below ({x}, {top})")
