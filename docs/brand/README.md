# The Keel Linux mark

The mark is a keel seen head on: two swept wings meeting at a mast, a
waterline crossing where they meet, and a blade descending to a point. It is
the part of a boat nobody sees and everything depends on, which is the claim
the distribution makes about itself.

Master: `keel-logo-2026-09-27.webp`, drawn by the maintainer, 1254 by 1254.
Every other file here is an export of it. A change to the mark is a new export,
never an edit of an export, and never a redraw by hand. `trace.py` takes the
vectors off the drawing and `export.py` takes the rasters off the vectors, so
a new drawing is two commands and no hand work at any step.

## Colours, measured from the master

| Role | Hex | Where |
|------|-----|-------|
| Navy | `#0B2847` | the symbol and the KEEL wordmark |
| Waterline | `#0072C9` | the horizontal band only |
| Grey | `#7F8D9D` | the LINUX subtitle only |

Measured, not chosen: these are the most frequent exact values in the symbol,
the band and the subtitle of the master file. The navy carries the mark. The
blue is an accent and appears once, in the waterline; a second blue element
breaks the drawing. The grey never carries the mark on its own.

Dark backgrounds use the light variant, which inverts the navy to white and
keeps the waterline. One colour surfaces, a stencil or an engraving, use the
mono variant, where the waterline is a gap rather than a colour.

## Clear space and minimum size

Clear space is the height of the waterline band on every side. Nothing enters
it, including the wordmark when the symbol is used alone.

The symbol alone reads down to 16 pixels. The lockup with KEEL and LINUX needs
120 pixels of width before the subtitle closes up; below that, use the symbol.

## The console mark

The console is where the mark is hardest, and where the budget is not ours to
choose. A confconsole dialog on a small virtual machine is 24 rows by 80
columns, and the operator needs the service list inside it: the site, the
admin URL, the web shell, Webmin and SSH, each on its own line, in both
address families. That is fifteen lines of text the operator came for.

### The art, in tiers

The console art is the maintainer's own drawing, decided on 2026-09-30 "in
layers". It replaced the first ASCII mark, which was drawn by hand from the
picture and read as a mess on the WordPress usage screen. Five files, kept
byte for byte as he drew them, installed by keel-core's overlay in
`/etc/keel/`:

| Tier | File | Rows | Columns | Characters |
|------|------|------|---------|------------|
| wide | `banner-wide.txt` | 16 | 150 | UTF-8 only: the mark, the KEEL LINUX lettering, the tagline and KEELLINUX.ORG |
| full | `banner-utf8.txt`, `banner.txt` | 12 | 29 | UTF-8 block characters, and the same drawing in `#` |
| small | `banner-small-utf8.txt`, `banner-small.txt` | 7 | 16 | the same, smaller |

The rule, the same on both surfaces: the largest tier that fits, in the order
wide, full, small, none. The UTF-8 files when the locale is UTF-8, the ASCII
files otherwise, so a serial console, a recovery shell and `ssh -T` in the C
locale still render it. There is no ASCII wide tier. No colour escapes
anywhere. Nothing records these sizes in code: both renderers measure each
file, so a new drawing needs no code change.

- The login banner (`/etc/update-motd.d/00-keel-banner`, keel-core) measures
  the terminal from `LINES` and `COLUMNS`, then `stty size`, then assumes 24
  by 80, and keeps room under the mark for the title and the addresses. The
  locale is `LC_ALL`, `LC_CTYPE`, `LANG`, then `/etc/default/locale`, because
  pam_motd runs the drop-ins with an empty environment.
- The confconsole usage screen (`keelbanner.py`) measures the room the dialog
  has: the screen less the backtitle and the shadow (four rows, four
  columns), and the usage text as dialog wraps it plus five rows of frame and
  button. The box widens for the wide tier. The locale is the one dialog
  inherits; Python coerces `LANG=C` to `C.UTF-8`, so only `LC_ALL=C` gets the
  ASCII tiers there.

What each surface shows, checked on a trixie container on 2026-10-01 with a
dual stack WordPress service list:

| Terminal | Login banner | Usage screen |
|----------|--------------|--------------|
| 80 by 24 | full | none: eleven rows of addresses leave no room |
| 100 by 30 | full | small |
| 160 by 45 | wide (UTF-8), full (ASCII) | wide (UTF-8), full (ASCII) |
| 200 by 50 | wide (UTF-8), full (ASCII) | wide (UTF-8), full (ASCII) |

On 80 by 24 the usage screen has a 20 row box, so the small mark fits only
above a usage text of seven rows or fewer, such as an IPv6 only appliance.
The login banner fits its own block, but the rest of the message of the day
(sysinfo, the confconsole line, uname) follows it and scrolls the top of the
mark off a 24 row screen.

### The budget of the first mark

What follows is the reasoning behind the first, hand-drawn mark, kept for its
measurements. The first mark had this ceiling:

| Mark | Rows | Columns |
|------|------|---------|
| full | 12 | 38 |
| small | 7 | 24 |

It was plain ASCII only. What that leaves on a 24 by 80 screen, with the full
mark and a real service list:

```
+------------------------------------------------------------------------+
|                    WORDPRESS-DEMO appliance services                    |
|                                                                         |
|                  ....................                      <- 12 rows   |
|                  ....................                         and 38    |
|                  ....................                         columns,  |
|                  ....................                         centred   |
|                  ....................                                   |
|                  ....................                                   |
|                                                                         |
| Blog:      https://[2804:710:d0:5:e0fc:fc60:e690:1c25]                  |
| Admin:     https://[2804:710:d0:5:e0fc:fc60:e690:1c25]/wp-admin/        |
| Web shell: https://[2804:710:d0:5:e0fc:fc60:e690:1c25]:12320            |
| Webmin:    https://[2804:710:d0:5:e0fc:fc60:e690:1c25]:12321            |
| SSH/SFTP:  root@2804:710:d0:5:e0fc:fc60:e690:1c25 (port 22)             |
|                                                                         |
| Blog:      https://10.88.5.69                                           |
| Admin:     https://10.88.5.69/wp-admin/                                 |
| Web shell: https://10.88.5.69:12320                                     |
| Webmin:    https://10.88.5.69:12321                                     |
| SSH/SFTP:  root@10.88.5.69 (port 22)                                    |
+------------------------------------------------------------------------+
```

An IPv6 address line is 72 characters, which is why 38 columns is the ceiling
for the mark and why it is centred rather than left aligned.

Two things measured on a real appliance, 2026-09-27, that the numbers above
have to survive. The dialog draws a frame and padding, so the usable width is
four columns less than the screen: at 80 columns the mark has 76, and 38 is
comfortably inside it. And the longest service line, the admin URL, already
wraps at that width, which is a defect of the service list rather than of the
mark, recorded so that whoever shortens it does not blame the drawing.

At 80 by 24, with that oversized first art, the mark was dropped entirely and
the list still scrolled at 95 percent.

The rule the code keeps, and its tests hold: the addresses never scroll away.
As the screen shrinks the wide mark gives way to the full one, the full to
the small one, and the small one to nothing, before a single line of text is
lost. The code reads
the mark from its file and measures it, so a new drawing needs no code change,
and no size is assumed anywhere.

## The horizontal lockup

The site's header sets the symbol on its off-white plate beside "Keel
Linux" in bold, on one line. `site/keel-lockup-horizontal-light.png` (text
in the site's navy, `#0B1F3A`, for light backgrounds) and
`site/keel-lockup-horizontal-dark.png` (off-white text, `#F4F7FA`, for dark
ones; the plate stays off-white, as on the site) are that header at sixteen
times its size, with the site's own proportions: the symbol at 2rem on a plate
with a 0.4rem radius, a 0.6rem gap, the name at 1.05rem, weight 700. Both are
transparent PNGs, 2367 by 640, rendered with headless Chromium on 2026-09-30.

They live in `site/` because they are renders of the site, not exports of the
master: `export.py` makes every file at the top of this directory and needs no
font, and these could not be remade by it. The site sets the name in the
reader's system font (`system-ui`), so they carry the font of the machine that
rendered them (DejaVu Sans Bold), not one the brand chose.

Two navies sit side by side in them, as they do on the site: the symbol's
`#0B2847` and the site's text colour `#0B1F3A`. That is the site's choice,
recorded here rather than corrected in a render.

The horizontal lockup needs 140 pixels of width, the size the site header
shows it at; below that, use the symbol alone. A vector horizontal lockup,
with the name in a font the project picks, converted to outlines and in the
brand's navy, is the version to draw when one is needed for print.

## What not to do

- Do not recolour the mark, and do not add a second blue.
- Do not stretch it: the wings and the blade are one proportion.
- Do not edit the console art. The five banner files are the maintainer's
  drawing, installed byte for byte; a change is a new drawing from him, and
  only trailing spaces may be trimmed.
- Do not use the lockup where the symbol is meant, or the symbol where the
  product is being named for the first time.
- Do not put the mark in the footer of a page the operator publishes. The
  appliance's own pages are ours; their site is theirs. A default landing page
  shipped by the appliance, as LAMP has, is ours and carries the mark until
  they replace it.

## Files

| File | What it is |
|------|------------|
| `keel-logo-2026-09-27.webp` | the master, as drawn |
| `keel-mark.svg` | the symbol, vector, light backgrounds |
| `keel-mark-dark.svg` | the symbol for dark backgrounds |
| `keel-mark-mono.svg` | one colour, waterline as a gap |
| `keel-mark-*.png` | raster exports, 16 to 1024 |
| `keel-lockup-light.png`, `keel-lockup-dark.png`, `keel-lockup*.svg` | symbol with the wordmark, stacked |
| `site/keel-lockup-horizontal-light.png`, `site/keel-lockup-horizontal-dark.png` | symbol and "Keel Linux" side by side, the site header's lockup, 2367 by 640, transparent; renders of the site, not exports (see "The horizontal lockup" above) |
| `keel-social-1200x630.png` | link preview card |
| `banner-wide.txt`, `banner-utf8.txt`, `banner.txt`, `banner-small-utf8.txt`, `banner-small.txt` | the maintainer's console art, in keel-core's overlay (`overlay/etc/keel/`), see "The console mark" |
| `trace.py` | traces the vectors off the master |
| `export.py` | re-exports the rasters off the vectors |

The site, the organization profile and the appliance overlay reference these
names. Replacing a file's contents is the change; renaming one breaks them.
