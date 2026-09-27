# Keel Linux brand manual

The mark, the colours, the sizes and the rules. Everything here is short on
purpose; if a question is not answered, the answer is "ask the maintainer",
not "improvise".

## 1. The mark

A keel seen head on. Two swept wings meet at a vertical mast, a horizontal
waterline crosses at the base of the wings, and the blade descends from it to
a point below. It reads as structure and course: the member a hull is built
on, the part that keeps a vessel upright and lets it hold a line. That is the
argument for the product as well, so the mark and the product say the same
thing.

The lineage is stated in prose, never in the mark. The nickname "TurnKeel"
appears in no asset.

## 2. The files

The vector masters are the source. Every raster in this directory is produced
from them by `export.py` and by nothing else.

| File | What it is |
| --- | --- |
| `keel-mark.svg` | the symbol, navy and blue, for a light ground |
| `keel-mark-dark.svg` | the symbol for a dark ground |
| `keel-mark-mono.svg` | the symbol in one ink, for a stencil, an engraving or a one colour print |
| `keel-lockup.svg` | symbol over the wordmark, for a light ground |
| `keel-lockup-dark.svg` | the same for a dark ground |
| `keel-mark-{16,32,64,256,512,1024}.png` | the symbol, transparent |
| `keel-mark-1024-light.png`, `keel-mark-1024-dark.png` | the symbol flattened onto its ground |
| `keel-icon.png`, `keel-icon-light.png` | application icon: the symbol inset on a rounded tile |
| `keel-lockup-light.png`, `keel-lockup-dark.png` | the lockup, flattened |
| `keel-social-1200x630.png` | the link preview card |
| `keel-logo-2026-09-27.webp` | the maintainer's drawing, the source the vectors were redrawn from |

The site (`keel-linux.github.io`) and the organization profile (`.github`)
carry copies under their own `assets/`. When a master changes here, those
copies are updated from here; they are not edited in place.

The wordmark is outlines, not text. No font is needed to render any file, and
none may be substituted.

## 3. Colours

Measured out of `keel-logo-2026-09-27.webp` with Pillow: the modal colour of
the stroke interiors, sampling only pixels whose whole neighbourhood is ink,
so antialiasing at the edges does not pull the value.

| Name | Hex | RGB | Where | Agreement |
| --- | --- | --- | --- | --- |
| Navy | `#0B2847` | 11, 40, 71 | wings, blade, KEEL | 99.9 percent of ink within 10 |
| Waterline blue | `#0170C5` | 1, 112, 197 | the waterline, nothing else | 96.1 percent within 10 |
| Grey | `#636E7C` | 99, 110, 124 | LINUX, nothing else | 92.3 percent within 10 |
| Paper | `#FFFFFF` | 255, 255, 255 | the ground it was drawn on | |

Contrast: navy on paper 14.9 to 1, grey on paper 5.2 to 1.

On a dark ground the symbol and KEEL are paper, LINUX is `#9AA7B4` (6.1 to 1
on navy) and the waterline is `#3EABFE` (6.0 to 1 on navy), which is the
waterline blue at the lightness it needs to stay a waterline instead of a
smudge. That substitution exists only inside the two dark masters. It is not
a licence to pick a blue.

## 4. Clear space and minimum size

Clear space on every side is one quarter of the symbol's height. Nothing
enters it: no text, no rule, no other logo, no photograph edge.

| | Minimum | Floor |
| --- | --- | --- |
| Symbol, screen | 24 px tall | 16 px, favicon only, where the mast slot closes |
| Symbol, print | 10 mm tall | |
| Lockup, screen | 140 px tall | 120 px, below which LINUX breaks up |
| Lockup, print | 25 mm tall | |

Use the symbol alone wherever the name is already on the page. The lockup is
for the places where it is not.

## 5. The console marks

An operator meets a Keel appliance on a console long before any web page, so
the console is a brand surface. Two ASCII marks are installed by the core
overlay, `/etc/keel/banner.txt` and `/etc/keel/banner-small.txt`, and both the
login banner and the confconsole usage screen read those same two files.

### The rules the art must obey

- **Plain ASCII only.** No box drawing, no colour escape, nothing above
  code point 126. A serial console, a recovery shell and `ssh -T` all have to
  render it.
- **The full mark: at most 12 rows by 38 columns.**
- **The small mark: at most 7 rows.**
- **It has to read at that size.** This is the real constraint. A mark that
  needs 19 rows to be recognisable is a mark that cannot go on a console, and
  the answer is a simpler drawing, not more rows.

### Why those numbers

The addresses are what the operator came for. The mark is dropped to the small
one, and then to nothing, before a single address line is lost, so a mark that
is too tall is not a bigger mark, it is no mark.

A console of 24 rows gives the dialog 20 rows once its frame and button are
paid for. One blank row separates the mark from the text. What is left is the
budget, and it depends on how much the appliance has to say.

Here is a 24 by 80 console on a core appliance. The service list is four
lines, so 9 rows are free and a 7 row mark fits with room to spare:

```
+-- core appliance services ---------------------------------------------------+
|                                                                              |
|                    ######################################                    |
|                    ######################################                    |
|                    ######################################                    |
|                    ## small mark, 7 rows by 38 columns ##                    |
|                    ######################################                    |
|                    ######################################                    |
|                    ######################################                    |
|                                                                              |
| Webmin:    https://[2001:db8:1::10]:12321                                    |
| SSH/SFTP:  root@2001:db8:1::10 (port 22)                                     |
|                                                                              |
| Webmin:    https://192.0.2.10:12321                                          |
| SSH/SFTP:  root@192.0.2.10 (port 22)                                         |
|                                                                              |
| TKLBAM: NOT INITIALIZED                                                      |
|                                                                              |
|          Keel appliance backup and migration                                 |
|              https://keellinux.org/backup                                    |
|                                                                              |
|                                                                              |
|                                    < OK >                                    |
+------------------------------------------------------------------------------+
```

The same console on a WordPress appliance. The service list is five lines in
each address family, which is 16 rows of text, so only 3 rows are free and no
mark fits at all. That is the correct outcome, and it is the reason the budget
is what it is:

```
+-- wordpress appliance services ----------------------------------------------+
|                                                                              |
| Blog:      https://[2001:db8:1::10]                                          |
| Admin:     https://[2001:db8:1::10]/wp-admin/                                |
| Web shell: https://[2001:db8:1::10]:12320                                    |
| Webmin:    https://[2001:db8:1::10]:12321                                    |
| SSH/SFTP:  root@2001:db8:1::10 (port 22)                                     |
|                                                                              |
| Blog:      https://192.0.2.10                                                |
| Admin:     https://192.0.2.10/wp-admin/                                      |
| Web shell: https://192.0.2.10:12320                                          |
| Webmin:    https://192.0.2.10:12321                                          |
| SSH/SFTP:  root@192.0.2.10 (port 22)                                         |
|                                                                              |
| TKLBAM: NOT INITIALIZED                                                      |
|                                                                              |
|          Keel appliance backup and migration                                 |
|              https://keellinux.org/backup                                    |
|                                                                              |
|                                                                              |
|                                                                              |
|                                                                              |
|                                    < OK >                                    |
+------------------------------------------------------------------------------+
```

The console height each mark needs, which is mark rows plus one blank row plus
the text plus four rows of frame:

| Mark | Rows | Core, 10 rows of text | WordPress, 16 rows of text |
| --- | --- | --- | --- |
| Full, budget | 12 | 27 | 33 |
| Small, budget | 7 | **22** | 28 |
| Full, as shipped today | 19 | 34 | 40 |
| Small, as shipped today | 11 | 26 | 32 |

That single bold number is the point of the exercise: at 7 rows the mark
appears on an ordinary 24 row console, and at 11 it never does.

Width: 38 columns fits a 60 column console (which gives 56) with 9 columns
either side, and is dropped below 42 columns. The renderer centres the block
on the width it is given, shifting every line by the same indent, so the art
must be drawn flush left in the file with no leading padding of its own.

## 6. What must not be done

- **Do not recolour.** The colours in section 3 are the colours. A tint, a
  gradient, a team colour or a seasonal variant is not a Keel mark.
- **Do not stretch.** Scale proportionally. If it has to fit a shape it does
  not fit, change the space, not the mark.
- **Do not redraw the ASCII by hand in the overlay.** The two mark files are
  exports of the design system. A change to the console mark is a new export
  committed as a whole file; an edit of a few characters in place drifts away
  from the vector and nobody notices until it looks wrong on a screenshot.
- **Do not use the lockup where the symbol alone is meant.** In a header, a
  favicon, an avatar or beside a page title that already says Keel, the
  wordmark repeats the name and shrinks the symbol for nothing.
- Do not rotate it, outline it, add a shadow, put it on a busy photograph, or
  rebuild it from the raster files. The vector masters are the source.
