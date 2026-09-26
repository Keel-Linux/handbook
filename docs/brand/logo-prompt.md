# Logo prompt: Keel Linux

Commercial name: **Keel Linux**. The word "TurnKeel" never appears in any
brand asset (nickname, and a trademark matter). Lineage is stated in prose
only, never in the mark.

## Concept in one line

A keel is the spine of a hull: the structural member everything else is built
on, the part that keeps the vessel upright and lets it hold a course. Keel
Linux is the base layer that appliances are built on, reproducible, signed,
reachable on its own address. The mark should read as structure and course,
not as sailing or leisure.

## Prompt (image model)

```
Minimal modern logo for "Keel Linux", an open-source Linux distribution for
system-container appliances. Design a geometric icon plus a wordmark.

Icon: an abstract keel seen from below or in cross-section: a single strong
vertical spine with three horizontal layers stacked on it, the layers slightly
offset like the strakes of a hull, suggesting "core, stack, app" built on one
backbone. The whole icon fits a square, works as a favicon at 16 px and as a
monochrome stamp. Straight lines and a few precise curves only; no gradients,
no shadows, no 3D, no realism.

Wordmark: "Keel" in a bold, low-contrast geometric sans-serif, "Linux" lighter
and smaller on the same baseline or beneath. Tight letterspacing, clean
terminals, no italic, no script.

Color: deep navy #0B1F3A as the base, one accent in signal teal #16A6A0 used
on a single layer of the icon; a white and a black single-color version. Flat
colors, high contrast, prints well in one ink.

Mood: engineering, sovereignty, calm reliability; the seriousness of a
shipyard blueprint, not the playfulness of a startup mascot.

Deliver: icon alone, wordmark alone, horizontal lockup, stacked lockup, each
on light and on dark background, transparent PNG and SVG.

Do not include: a penguin, a key, a keyhole, a padlock, a whale, a shipping
container, a cube, a hexagon cluster, waves, an anchor, a sailboat, a globe,
circuit traces, hexadecimal or binary text, any gradient or glow, any text
other than "Keel Linux".
```

## Notes for whoever runs the prompt

- Keep the two exclusions that matter for trademark distance: no key or
  keyhole (TurnKey), no whale or shipping container (a container runtime).
- Ask for the icon first and iterate on it alone; the wordmark is a typeface
  choice and is better set by hand afterwards (candidates: Inter, Manrope,
  Space Grotesk, all open licensed).
- Test the icon at 16 px and in a single color before accepting it; most
  results fail there.
- Final files go to `docs/brand/` with a short usage note; the colors above
  become the palette for confconsole and the web pages so the product and the
  mark match.

## Variant B: visibly nautical, still modern

The first variant reads as pure geometry because it bans every nautical cue.
This one keeps the hull and the waterline, which are structure, and still
leaves out anchors, sails and rope, which are decoration.

```
Minimal modern logo for "Keel Linux", an open-source Linux distribution for
system-container appliances. Geometric icon plus wordmark.

Icon: the cross-section of a ship's hull seen head-on, drawn as one continuous
bold line: a shallow U for the hull with a deep, straight keel fin dropping
from its centre, clearly a boat's underbody. A single straight horizontal line
crosses the hull as the waterline. Inside the hull, above the waterline, three
thin horizontal bands stacked on the keel line, like decks or strakes, hinting
at layers built on one backbone. The keel fin is the visual anchor of the
composition and is the only element in the accent color. Flat, symmetrical,
fits a square, legible at 16 px and as a one-color stamp. Precise lines, a few
controlled curves, no gradients, shadows, 3D or texture.

Wordmark: "Keel" bold geometric sans-serif, "Linux" lighter and smaller,
sharing the same baseline as the waterline in the horizontal lockup, so the
type sits on the water.

Color: deep navy #0B1F3A hull and type, signal teal #16A6A0 for the keel fin
only, off-white #F4F7FA background variant; also pure white-on-navy and
black-on-white single-color versions.

Mood: naval architecture drawing, shipyard blueprint, engineered calm;
maritime but industrial, never leisure or tourism.

Deliver: icon alone, wordmark alone, horizontal and stacked lockups, light and
dark backgrounds, transparent PNG and SVG.

Do not include: anchor, sail, mast, rope, life ring, lighthouse, compass rose,
seagull, stylized waves or splashes, wind lines, a whale, a shipping container,
a cube, a penguin, a key or keyhole, a padlock, any gradient or glow, any text
other than "Keel Linux".
```

If the results still lean abstract, add one sentence: "It must be
recognizable as the underside of a ship at first glance."
