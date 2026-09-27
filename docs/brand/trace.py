#!/usr/bin/env python3
"""Re-trace the vector masters from the drawing.

`keel-logo-2026-09-27.webp` is the drawing; the five SVG files beside this
script are traced from it by this script and by nothing else, so a redrawn
logo is a re-run rather than an edit of a path. Nothing here is typed in by
hand: the shapes are the boundaries of the drawing's own ink, the colours
are the ones the manual measured, and every dimension, down to the clear
space and the size of the canvas, is read off the drawing.

    python3 -m venv /tmp/brand && /tmp/brand/bin/pip install pillow numpy
    /tmp/brand/bin/python docs/brand/trace.py

Run `export.py` afterwards to bring the rasters up with the vectors.
"""

import sys
from collections import defaultdict
from pathlib import Path

try:
    import numpy as np
    from PIL import Image
except ImportError as exc:
    sys.exit(f"missing dependency: {exc}. See the docstring of this file.")

HERE = Path(__file__).resolve().parent
MASTER = HERE / "keel-logo-2026-09-27.webp"

# The colours the manual measured in the drawing. They are written here
# rather than sampled because the manual is the contract: a drawing that
# stopped carrying them is a drawing to send back, not a palette to follow.
NAVY = "#0B2847"
WATERLINE = "#0072C9"
GREY = "#7F8D9D"
PAPER = "#FFFFFF"

# Ink is separated from paper at half coverage, which is where an
# antialiased edge crosses and so where the drawn boundary lies. The
# midpoint between a colour and the paper, as a luminance:
#
#   navy #0B2847 -> 40.7, grey #7F8D9D -> 141.7, paper -> 254.3
INK = (40.7 + 254.3) / 2
INK_GREY = (141.7 + 254.3) / 2

# The waterline is told from the navy by hue, not by luminance: both are
# dark, but only the blue is far more green than red. Navy's own green
# lead is 29, the waterline's is 114, and a blend of the waterline with
# the paper keeps a lead above this until it has all but faded out.
GREEN_LEAD = 40

# Distance, in drawing pixels, that a traced outline may stand from the
# boundary it came from. Under a pixel: the smoothing takes out the stair
# steps of the pixel grid and leaves the drawn edges where they were.
TOLERANCE = 0.9

SVG_HEAD = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}"'
    ' width="{w}" height="{h}" role="img" aria-label="{label}">\n'
    "  <title>{label}</title>\n"
    "  <desc>{desc}</desc>\n"
)

SYMBOL_DESC = (
    "A keel seen head on: two swept wings meeting at a mast, the waterline "
    "crossing where they meet, and the blade descending to a point below it."
)
LOCKUP_DESC = (
    SYMBOL_DESC + " Under it, KEEL in a heavy face with LINUX letterspaced "
    "beneath."
)
MONO_DESC = (
    "A keel seen head on: two swept wings meeting at a mast and the blade "
    "descending to a point, in one colour, with the waterline left as the "
    "gap between them."
)


def bands(rows):
    """The runs of consecutive True values in `rows`, as (start, stop)."""
    out = []
    start = None
    for i, on in enumerate(rows):
        if on and start is None:
            start = i
        elif not on and start is not None:
            out.append((start, i))
            start = None
    if start is not None:
        out.append((start, len(rows)))
    return out


def ink_masks(path):
    """The drawing separated into its navy, waterline and grey ink.

    The subtitle is grey, and a navy edge fading into the paper passes
    through the same greys, so the two cannot be told apart by colour. They
    are told apart by where they are: the subtitle is the last band of ink
    on the page, with clear paper above it, and that band is found here
    rather than written down.
    """
    pixels = np.asarray(Image.open(path).convert("RGB")).astype(int)
    red, green, blue = pixels[:, :, 0], pixels[:, :, 1], pixels[:, :, 2]
    luminance = pixels.mean(axis=2)

    water = ((green - red) > GREEN_LEAD) & (blue > 140)
    any_ink = (luminance < INK_GREY) | water
    ink_bands = bands(any_ink.any(axis=1).tolist())
    if len(ink_bands) < 2:
        sys.exit(f"{path.name}: expected a subtitle under the drawing")
    subtitle = np.zeros(luminance.shape, bool)
    subtitle[ink_bands[-1][0]:, :] = True

    navy = (luminance < INK) & ~water & ~subtitle
    grey = (luminance < INK_GREY) & subtitle
    return navy, water, grey


def outlines(mask):
    """The closed boundaries of `mask`, as rings of (x, y) pixel corners.

    Every side of a set pixel whose neighbour is clear is one step of a
    boundary, taken in a consistent direction; the steps chain head to tail
    into one ring per shape. The drawing has no counters, so no ring lies
    inside another and a shape is one ring.
    """
    padded = np.zeros((mask.shape[0] + 2, mask.shape[1] + 2), bool)
    padded[1:-1, 1:-1] = mask
    steps = defaultdict(list)
    ys, xs = np.nonzero(padded)
    for y, x in zip(ys.tolist(), xs.tolist()):
        if not padded[y - 1, x]:
            steps[(x, y)].append((x + 1, y))
        if not padded[y, x + 1]:
            steps[(x + 1, y)].append((x + 1, y + 1))
        if not padded[y + 1, x]:
            steps[(x + 1, y + 1)].append((x, y + 1))
        if not padded[y, x - 1]:
            steps[(x, y + 1)].append((x, y))
    rings = []
    while steps:
        start = next(iter(steps))
        ring = [start]
        here = start
        while True:
            onward = steps.get(here)
            if not onward:
                break
            onward_to = onward.pop()
            if not onward:
                del steps[here]
            here = onward_to
            if here == start:
                break
            ring.append(here)
        if len(ring) > 3:
            rings.append([(x - 1, y - 1) for x, y in ring])
    return rings


def _thin(points, tolerance):
    """`points` with every corner nearer than `tolerance` to the line
    through the ends dropped, and the rest kept, applied recursively."""
    if len(points) < 3:
        return points
    (ax, ay), (bx, by) = points[0], points[-1]
    dx, dy = bx - ax, by - ay
    span = (dx * dx + dy * dy) ** 0.5
    worst, at = -1.0, 0
    for i in range(1, len(points) - 1):
        px, py = points[i]
        if span == 0:
            far = ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
        else:
            far = abs(dy * px - dx * py + bx * ay - by * ax) / span
        if far > worst:
            worst, at = far, i
    if worst <= tolerance:
        return [points[0], points[-1]]
    return _thin(points[: at + 1], tolerance)[:-1] + _thin(points[at:],
                                                           tolerance)


def thin_ring(ring, tolerance):
    """A closed ring thinned to its corners.

    The thinning needs two ends that are certainly corners, or it would be
    free to cut across the shape; the two points furthest apart on the ring
    are taken, and the two arcs between them are thinned separately.
    """
    points = np.array(ring, float)
    first = int(np.argmax(((points - points.mean(axis=0)) ** 2).sum(axis=1)))
    turned = ring[first:] + ring[:first]
    spread = ((np.array(turned, float) - turned[0]) ** 2).sum(axis=1)
    second = int(np.argmax(spread))
    near = _thin(turned[: second + 1], tolerance)
    far = _thin(turned[second:] + [turned[0]], tolerance)
    return near[:-1] + far[:-1]


def box(rings):
    """The (x0, y0, x1, y1) all of `rings` stand in."""
    points = np.array([point for ring in rings for point in ring])
    return (points[:, 0].min(), points[:, 1].min(),
            points[:, 0].max(), points[:, 1].max())


def number(value):
    """A coordinate, without the trailing zero an integer would carry."""
    rounded = round(value, 1)
    return f"{rounded:g}"


def path(rings, dx, dy):
    """`rings` as one SVG path, moved by (dx, dy)."""
    parts = []
    for ring in rings:
        moves = [f"{number(x + dx)} {number(y + dy)}" for x, y in ring]
        parts.append("M" + "L".join(moves) + "Z")
    return "".join(parts)


def group(rings, colour, dx, dy, indent="  "):
    return f'{indent}<path fill="{colour}" d="{path(rings, dx, dy)}"/>\n'


def write(name, width, height, body, label="Keel Linux", desc=SYMBOL_DESC):
    text = SVG_HEAD.format(w=number(width), h=number(height), label=label,
                           desc=desc) + body + "</svg>\n"
    (HERE / name).write_text(text)
    print(f"  {name}: {number(width)} by {number(height)},"
          f" {len(text)} bytes")


def main():
    navy_mask, water_mask, grey_mask = ink_masks(MASTER)
    navy = [thin_ring(r, TOLERANCE) for r in outlines(navy_mask)]
    water = [thin_ring(r, TOLERANCE) for r in outlines(water_mask)]
    subtitle = [thin_ring(r, TOLERANCE) for r in outlines(grey_mask)]

    # The symbol is the navy that starts at or above the waterline, the
    # wings and the blade; the wordmark is the navy below it. Which shape is
    # which is decided by where it stands in the drawing, never by a count.
    water_bottom = box(water)[3]
    symbol = [r for r in navy if box([r])[1] <= water_bottom]
    wordmark = [r for r in navy if box([r])[1] > water_bottom]
    if not symbol or not wordmark or not subtitle or len(water) != 1:
        sys.exit(f"{MASTER.name}: the drawing is not the one this traces")

    # Clear space is the height of the waterline band, which the band is
    # measured for rather than asked about.
    x0, y0, x1, y1 = box(symbol + water)
    clear = box(water)[3] - box(water)[1]
    side = max(x1 - x0, y1 - y0) + 2 * clear
    dx, dy = (side - (x1 - x0)) / 2 - x0, (side - (y1 - y0)) / 2 - y0

    print(f"drawing: symbol {x1 - x0} by {y1 - y0}, waterline {clear} tall,"
          f" canvas {number(side)}")

    print("the symbol")
    write("keel-mark.svg", side, side,
          group(symbol, NAVY, dx, dy) + group(water, WATERLINE, dx, dy))
    write("keel-mark-dark.svg", side, side,
          group(symbol, PAPER, dx, dy) + group(water, WATERLINE, dx, dy))
    # One colour: the waterline is dropped, and the paper between the wings
    # and the blade is what is left of it.
    write("keel-mark-mono.svg", side, side, group(symbol, NAVY, dx, dy),
          desc=MONO_DESC)

    print("the lockup")
    lx0, ly0, lx1, ly1 = box(symbol + water + wordmark + subtitle)
    lw, lh = lx1 - lx0, ly1 - ly0
    for name, ink, water_ink in (("keel-lockup.svg", NAVY, WATERLINE),
                                 ("keel-lockup-dark.svg", PAPER, WATERLINE)):
        write(name, lw, lh,
              group(symbol + wordmark, ink, -lx0, -ly0)
              + group(water, water_ink, -lx0, -ly0)
              + group(subtitle, GREY, -lx0, -ly0),
              desc=LOCKUP_DESC)


if __name__ == "__main__":
    main()
