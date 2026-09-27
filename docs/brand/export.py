#!/usr/bin/env python3
"""Re-export every raster brand file from the vector masters.

The masters are the five SVG files beside this script, which `trace.py`
traces from the drawing. Every PNG in this directory is produced from them
by this script and by nothing else: a raster is never retouched by hand,
because the next export would silently undo the retouch. Run it after any
change to a master.

    python3 -m venv /tmp/brand && /tmp/brand/bin/pip install cairosvg
    /tmp/brand/bin/python docs/brand/export.py

Needs cairosvg (which needs the system libcairo) and Pillow. No font is
needed: the wordmark is outlines, not text. No shape of a master is written
down here either: the proportion of the lockup is read out of its viewBox,
so a retrace at another size is an export and not an edit.
"""

import re
import sys
from pathlib import Path

try:
    import cairosvg
    from PIL import Image, ImageDraw
except ImportError as exc:
    sys.exit(f"missing dependency: {exc}. See the docstring of this file.")

HERE = Path(__file__).resolve().parent

NAVY = (11, 40, 71)
PAPER = (255, 255, 255)

MARK = HERE / "keel-mark.svg"
MARK_DARK = HERE / "keel-mark-dark.svg"
LOCKUP = HERE / "keel-lockup.svg"
LOCKUP_DARK = HERE / "keel-lockup-dark.svg"


def ratio(source: Path) -> float:
    """The height of `source` over its width, from its own viewBox, so
    every export of it keeps the proportion the master was traced at."""
    box = re.search(r'viewBox="([-\d.eE ]+)"', source.read_text())
    if not box:
        sys.exit(f"{source.name}: no viewBox to take the proportion from")
    _, _, width, height = (float(n) for n in box.group(1).split())
    return height / width


# Every lockup export keeps the proportion of the lockup master.
LOCKUP_RATIO = ratio(LOCKUP)


def render(source: Path, width: int, height: int) -> Image.Image:
    """`source` rasterised to `width` by `height`, transparent behind."""
    png = cairosvg.svg2png(
        url=str(source), output_width=width, output_height=height
    )
    return Image.open(__import__("io").BytesIO(png)).convert("RGBA")


def on_field(mark: Image.Image, size, colour) -> Image.Image:
    """`mark` centred on an opaque field of `size`."""
    field = Image.new("RGBA", size, colour + (255,))
    field.alpha_composite(
        mark, ((size[0] - mark.width) // 2, (size[1] - mark.height) // 2)
    )
    return field


def tile(source: Path, colour, border=None) -> Image.Image:
    """An application icon: the mark inset on a rounded square of `colour`."""
    edge = 1024
    radius = 180
    inset = 150  # clear space, one third of the mark's height on each side
    canvas = Image.new("RGBA", (edge, edge), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle(
        (0, 0, edge - 1, edge - 1),
        radius=radius,
        fill=colour + (255,),
        outline=(border + (255,)) if border else None,
        width=6 if border else 0,
    )
    inner = edge - 2 * inset
    mark = render(source, inner, inner)
    canvas.alpha_composite(mark, (inset, inset))
    return canvas


def save(image: Image.Image, name: str, flatten=False) -> None:
    if flatten:
        image = image.convert("RGB")
    image.save(HERE / name)
    print(f"  {name}: {image.width} by {image.height} {image.mode}")


def main() -> None:
    print("marks, transparent")
    for size in (16, 32, 64, 256, 512, 1024):
        save(render(MARK, size, size), f"keel-mark-{size}.png")

    print("marks, flattened onto a field")
    save(
        on_field(render(MARK, 1024, 1024), (1024, 1024), PAPER),
        "keel-mark-1024-light.png",
        flatten=True,
    )
    save(
        on_field(render(MARK_DARK, 1024, 1024), (1024, 1024), NAVY),
        "keel-mark-1024-dark.png",
        flatten=True,
    )

    print("application icons")
    save(tile(MARK_DARK, NAVY), "keel-icon.png")
    save(tile(MARK, PAPER, border=NAVY), "keel-icon-light.png")

    print("lockups")
    width = 1024
    height = round(width * LOCKUP_RATIO)
    save(
        on_field(render(LOCKUP, width, height), (width, height), PAPER),
        "keel-lockup-light.png",
        flatten=True,
    )
    save(
        on_field(render(LOCKUP_DARK, width, height), (width, height), NAVY),
        "keel-lockup-dark.png",
        flatten=True,
    )

    print("social card")
    card = Image.new("RGBA", (1200, 630), NAVY + (255,))
    tall = 470
    lockup = render(LOCKUP_DARK, round(tall / LOCKUP_RATIO), tall)
    card.alpha_composite(
        lockup, ((1200 - lockup.width) // 2, (630 - lockup.height) // 2)
    )
    save(card, "keel-social-1200x630.png", flatten=True)


if __name__ == "__main__":
    main()
