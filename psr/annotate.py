from __future__ import annotations
from typing import Optional, Tuple
from PIL import Image, ImageDraw


def mark_click(img: Image.Image, rel_xy: Optional[Tuple[int, int]]) -> Image.Image:

    if not rel_xy:
        return img

    x, y = rel_xy
    draw = ImageDraw.Draw(img)

    cross = 13

    draw.line((x - cross, y, x + cross, y), fill="red", width=3)
    draw.line((x, y - cross, x, y + cross), fill="red", width=3)

    return img