"""Attribution marks for published charts.

StatsBomb's licence requires their logo on anything published from analysis of their
data (decision 017), which includes every chart that shows premistats xG.
"""
from pathlib import Path

import matplotlib.image as mpimg

LOGO = Path(__file__).resolve().parent.parent / "docs" / "img" / "statsbomb_logo.png"
_logo = None


def add_statsbomb_logo(fig, right: float = 0.97, bottom: float = 0.015, width: float = 0.16) -> None:
    """Place the StatsBomb logo with its bottom-right corner at (right, bottom), in figure fractions."""
    global _logo
    if _logo is None:
        _logo = mpimg.imread(LOGO)
    img_h, img_w = _logo.shape[:2]
    fig_w, fig_h = fig.get_size_inches()
    height = width * (img_h / img_w) * (fig_w / fig_h)  # keep the logo's aspect ratio
    ax = fig.add_axes((right - width, bottom, width, height))
    ax.imshow(_logo)
    ax.axis("off")
