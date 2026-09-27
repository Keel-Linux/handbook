# The Keel Linux mark

The mark is a keel seen head on: two swept wings meeting at a mast, a
waterline crossing where they meet, and a blade descending to a point. It is
the part of a boat nobody sees and everything depends on, which is the claim
the distribution makes about itself.

Master: `keel-logo-2026-09-27.webp`, drawn by the maintainer, 1254 by 1254.
Every other file here is an export of it. A change to the mark is a new export,
never an edit of an export, and never a redraw by hand.

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

So the budget, and it is a ceiling rather than a target:

| Mark | Rows | Columns |
|------|------|---------|
| full | 12 | 38 |
| small | 7 | 24 |

Plain ASCII only. No box drawing characters and no colour escapes, so a serial
console, a recovery shell and `ssh -T` all render it. What that leaves on a 24
by 80 screen, with the full mark and a real service list:

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

The rule the code keeps, and its tests hold: the addresses never scroll away.
As the screen shrinks the full mark gives way to the small one, and the small
one gives way to nothing, before a single line of text is lost. The code reads
the mark from its file and measures it, so a new drawing needs no code change,
and no size is assumed anywhere.

## What not to do

- Do not recolour the mark, and do not add a second blue.
- Do not stretch it: the wings and the blade are one proportion.
- Do not redraw the ASCII by hand from the picture. Export it, check it at 24
  by 80 and at 24 by 60, and commit the file.
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
| `keel-lockup-*.png` | symbol with the wordmark |
| `keel-social-1200x630.png` | link preview card |
| `banner.txt`, `banner-small.txt` | the console marks, in keel-core's overlay |

The site, the organization profile and the appliance overlay reference these
names. Replacing a file's contents is the change; renaming one breaks them.
