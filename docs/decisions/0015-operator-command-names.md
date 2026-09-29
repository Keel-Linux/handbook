# 0015: Operator facing commands carry the Keel name, with the turnkey name kept

Date: 2026-09-28
Status: decided by the maintainer

## Decision

A command an operator types on a Keel appliance carries this project's name.
Where such a command already exists under a `turnkey-*` name:

- the **Keel name is the real command**: the file with the code in it;
- the **`turnkey-*` name is kept, as a symlink to it**;
- **both keep working**, and neither is documented as deprecated.

Two details, because the natural choice is wrong in one of them and unstated
in the other. The Keel name is the `turnkey-` prefix replaced by `keel-` and
nothing else: `turnkey-wp` becomes `keel-wp`, `turnkey-init` becomes
`keel-init`. And **the link is relative**: `turnkey-wp -> keel-wp`, not
`-> /usr/local/bin/keel-wp`. An absolute link does not resolve inside
`fab-chroot`, so a build time caller such as `conf.d/main` stops finding the
command; keel-wordpress asserts the relative form for exactly that reason, and
making it absolute fails three of that repository's tests.

This is a general policy, not a per-appliance choice. It applies to every
operator facing command a repository of this organization **writes and names
itself**: a file in an appliance overlay, a file in the `common` overlays, a
script installed by a package this project builds. It does not apply to a
command that only exists because some other project's package put it there;
that case is settled below.

The reason for keeping the old name is the same reason `/etc/turnkey_version`
keeps its name in 0014. Compatibility with TurnKey appliances is a stated
property of this project (0008: the fork is kept upstream-compatible on
purpose). An operator who pasted a command out of TurnKey's documentation, or
who wrote a script against `turnkey-wp` last year, must not silently lose it,
and a rename with no link is exactly that loss: it fails at the moment the
operator needs the command, with `command not found` and no hint of a new
name.

## What a `turnkey-*` name owned by somebody else's package does instead

Nothing in this note. This section is about a package **this project does not
build**; the distinction matters, and getting it the wrong way round is the
mistake the first version of this note made. A command from a package with a
`+keel` version is ours, the rule applies to it directly, and it is in the
table below. What follows is only about the rest.

`turnkey-sysinfo` and `turnkey-version` are shipped by
the Debian packages of the same name, and a dpkg-owned file cannot simply
become a symlink: the next upgrade of the package restores the file, and in
the meantime dpkg either reports the divergence or replaces the link without
asking. A wrapper alongside and a dpkg diversion were both on the table.

Neither is needed, because the maintainer decided on 2026-09-28 to **build and
own `keel-version` and `keel-sysinfo` as Keel's own Debian source packages**
rather than wrap or divert TurnKey's. A command in a package this project
builds is a command this project names, so the rule above applies to it
directly and there is no dpkg-owned case left to handle. That work is
Keel-Linux/tracker#13 and is not part of this note.

What makes owning the packages possible is that the pair is a closed set,
measured on the `wordpress-demo` container on 2026-09-28: `turnkey-sysinfo`
1.1.0 has **no reverse dependencies at all**, and the only reverse dependency
of `turnkey-version` 1.1.3 is `turnkey-sysinfo`. Nothing else in the archive
depends on either, so replacing them breaks nothing that we would then have to
go and fix.

One correction to the inventory that raised this, Keel-Linux/tracker#12:
`turnkey-sysinfo` ships **two** commands, not one. Its dpkg file list on the
`wordpress-demo` container is `/usr/bin/turnkey-sysinfo`,
`/usr/bin/turnkey-detect-virt`, the `libsysinfo` Python package it imports and
the motd fragment under `/usr/share/turnkey-sysinfo/contrib`.
`turnkey-detect-virt` was missed. tracker#13 has to cover both names, the
library and the motd fragment, because replacing only `turnkey-sysinfo`
leaves a `keel-sysinfo` calling a `turnkey-detect-virt` nobody owns.

## Which commands this changes now, and which wait

tracker#12 measured five commands on the `wordpress-demo` container. That
inventory is where this note started and it is **not** the scope: the rule
above is. Applying the rule to this organization's repositories on 2026-09-28
finds **fifteen** distinct `turnkey-*` names, **eleven of them ours**. The
tables below are the whole of what the rule reaches today, grouped by what
puts the file on the machine, because that is what decides when each one can
move.

### Written by an appliance overlay

| Command | Repository | When |
| --- | --- | --- |
| `/usr/local/bin/turnkey-wp` | `keel-wordpress`, `overlay/usr/local/bin` | **now** |
| `/usr/local/sbin/turnkey-wordpress-update` | `keel-wordpress`, `overlay/usr/local/sbin` | **now** |
| `/usr/local/bin/turnkey-mysql-install-perf-info-schemas` | `unit-mariadb`, `overlay/usr/local/bin` | with the `common` copy below |

The first two change now because the appliance's own overlay writes them and
no core rebuild is involved: the recipe is rebuilt, one layer is republished,
and the chain under it is untouched. That is Keel-Linux/keel-wordpress#7.

The third is in this group by where it lives and in the next group by when it
moves. `unit-mariadb/overlay/usr/local/bin/turnkey-mysql-install-perf-info-schemas`
is a **byte-identical second copy** of the `common` file (the same git blob,
`c8f185b2`), so the two move in one change, or an appliance built from the
unit keeps the old name while one built from `common` does not. Anybody
renaming that command by following the `common` row alone will rename one of
two copies.

### Written by the `common` overlays

| Command | Overlay | Reached through | When |
| --- | --- | --- | --- |
| `/usr/local/bin/turnkey-php` | `overlays/php` | `php.mk` | next rebuild of the chain |
| `/usr/local/bin/turnkey-mysql-install-perf-info-schemas` | `overlays/mysql` | `mysql.mk` | next rebuild of the chain |
| `/usr/local/bin/turnkey-artisan` | `overlays/artisan` | `laravel.mk` | when something includes it |
| `/usr/local/bin/turnkey-composer` | `overlays/composer` | `composer.mk` | when something includes it |

The first two are a **correction to tracker#12's table**, which calls them
"inherited, build time". They are not inherited in the sense of being outside
this project's custody: both are ordinary tracked `100755` files in
`Keel-Linux/common`, a repository of this organization, reaching the image
through `COMMON_OVERLAYS` and `fab-apply-overlay`, and on the appliance
`dpkg -S` reports them owned by no package at all. The policy applies to them
in full. What makes them wait is not ownership but blast radius: `common` is
under every appliance, so renaming there is a rebuild of the whole chain and
belongs to a deliberate one. `turnkey-mysql-install-perf-info-schemas` also
has a caller inside `common` itself,
`overlays/mysql/usr/lib/confconsole/plugins.d/System_Settings/Mysql_perf_info.py`,
which moves in the same commit.

`turnkey-artisan` and `turnkey-composer` ship on no Keel appliance today,
because nothing includes `laravel.mk` or `composer.mk`. They are listed
anyway: `turnkey-artisan` is the same `runuser` shape as `turnkey-wp`, and a
name that is only found again when an appliance starts shipping it is a name
that gets shipped under the wrong one.

### Installed by a package this project builds

Versions are the ones installed on the `wordpress-demo` container on
2026-09-28; both repositories are already further ahead on `main`.

| Command | Package | Version on the appliance |
| --- | --- | --- |
| `/usr/sbin/turnkey-init` | `inithooks` | `2.3.6+keel4` |
| `/usr/sbin/turnkey-sudoadmin` | `inithooks` | `2.3.6+keel4` |
| `/usr/sbin/turnkey-install-security-updates` | `inithooks` | `2.3.6+keel4` |
| `/usr/lib/inithooks/bin/turnkey-init-fence` | `inithooks` | `2.3.6+keel4` |
| `/usr/bin/turnkey-lexicon` | `confconsole` | `2.2.3+keel2` |

**These are in scope and they were missing from the first version of this
note.** The third clause of the rule above is "a script installed by a package
this project builds", and both packages carry a `+keel` suffix: they are built
from `Keel-Linux/inithooks` and `Keel-Linux/confconsole`, whose trees hold
`turnkey-init`, `turnkey-sudoadmin`, `turnkey-install-security-updates`,
`bin/turnkey-init-fence` and `turnkey-lexicon` as their own source files, and
keel-wordpress's `Makefile` names both among "the project's own packages".
`turnkey-init` is the most operator-facing command on the machine: it is what
an operator types to run the first boot configuration again.

They wait on the same rebuild as `common`, and each needs more than a rename.
`turnkey-init-fence` is not on `PATH` and is not a command an operator types,
but the name is also `/etc/default/turnkey-init-fence`, the systemd unit
`turnkey-init-fence.service`, the firstboot hooks `30turnkey-init-fence` and
`97turnkey-init-fence-disable`, and a `htdocs` directory; the compatibility
rule covers the command, and the unit and conffile names are a packaging
question for whoever does that work, not something this note settles.

### Owned by a package somebody else builds

| Command | Package | Disposition |
| --- | --- | --- |
| `turnkey-sysinfo`, `turnkey-detect-virt` | `turnkey-sysinfo` 1.1.0 | tracker#13, by replacing the package |
| `turnkey-version` | `turnkey-version` 1.1.3 | tracker#13, by replacing the package |
| `/usr/bin/turnkey-make-ssl-cert` | `turnkey-ssl` 3.1.1 | **out of scope**, and stays as it is |

Neither `turnkey-sysinfo`, `turnkey-version` nor `turnkey-ssl` carries a
`+keel` suffix, so all three are somebody else's build and fall under the
carve-out. The first two are being replaced for the reasons in the previous
section. `turnkey-ssl` is not, and nothing in this note asks for it to be: it
is inherited surface and keeps its name until a decision says otherwise.

### If this table and the rule ever disagree

The rule wins. A table is a measurement of one day and this one has already
been corrected twice; the rule at the top of this note is the policy. A
command that meets it and is not listed here is in scope, and the right fix is
to add the row.

## How the symlink is made, and how that was checked

**In the overlay, committed to git.** Not `ln -s` in `conf.d/main`.

`fab-apply-overlay` is `cp -TdR OVERLAY DEST` (`cmd_apply_overlay` in fab).
**`-R` copies a symlink as a symlink unless `-L` is given, and `-d`
additionally preserves hard links**, so a symlink in an overlay arrives in the
image as a symlink. Git stores it as a symlink too, mode `120000`, so the
repository says plainly what the appliance will have. The layer tarball is
created and extracted by `tar`, which carries symlinks natively.

The attribution matters, because a copy step is the kind of thing that gets
written again from a note like this one. `-P` is already the default under
`-R`; only `-L` dereferences. Measured with coreutils 9.7:

    cp -TR   →  link -> real     symlink kept, hard link split (nlink 1)
    cp -TdR  →  link -> real     symlink kept, hard link kept  (nlink 2)
    cp -TLR  →  link             a second regular file: this is the one that
                                 flattens

So what `-d` contributes to the overlay step is `--preserve=links`, which is
about **hard** links. The property this policy depends on is the absence of
`-L`. A note that said otherwise would get `-d` added where it does nothing,
or a sound mechanism rejected for lacking it.

This was checked by doing it, not by reading the flags, because
docs/traps.md records "asserting the configuration is not asserting the
behaviour" as a defect this project keeps repeating. `tests/wrappers.bats` of
keel-wordpress copies the overlay with the same `cp -TdR` the build runs,
**twice**: that recipe applies its overlay twice, once through
`COMMON_OVERLAYS` and once as the product-local `ROOT_OVERLAY`, and a second
copy over an existing link has to leave a link and not a copy of its target;
and then *runs the copied `turnkey-wp`* and checks the command it produced. A
further test pins the paragraph above rather than only asserting it in prose:
a plain `cp -TR`, without `-d`, still yields a working `turnkey-wp`, and
`cp -TLR` turns it into a second regular file.
`tests/v19.sh` does the same thing on a booted appliance: `turnkey-wp` is
asked for the core version and the site URL, each compared against a literal
the script already holds rather than against a second `keel-wp` call, and the
updater's root guard is required to hold under the old name too. Comparing two
command substitutions would have passed as `test "" = ""` with wp-cli broken
and both sides empty, which is the same trap in a smaller shape. `test -L`
says a link exists; it does not say the appliance still answers to the old
name.

The alternative, `ln -sf` in `conf.d/main`, was rejected for three reasons: it
puts the fact in a build script instead of in the tree the reader is looking
at; it runs only at build time, so a rebuild is needed to notice it is
missing; and it cannot be tested without a chroot, while an overlay file is
tested by copying a directory.

## Justification (three parts, brief section 10)

1. **Why the present state does not hold.** The appliance speaks another
   distribution's name in the commands an operator types every day, and most
   of those names are ours. The inventory below is fifteen distinct names
   across this organization's repositories, **eleven of them written or built
   by this project**: two by keel-wordpress's own overlay, four by `common`,
   five by `inithooks` and `confconsole`. Thirteen of the fifteen are present
   on a `wordpress-demo` container, nine of those ours, and `turnkey-init`
   (what an operator types to run the first boot configuration again) is one
   of them. That is not inherited surface, it is ours, and leaving it is a
   choice we would be making every release.
2. **Whether a plain rename would do.** No. It breaks every script written
   against the old name and every command in TurnKey's documentation, and it
   breaks them at a distance, long after the upgrade, with an error that does
   not name the replacement. The project's compatibility claim (0008) is not
   compatible with that. The opposite, keeping the `turnkey-*` name as the
   real command and adding a Keel alias, was also considered and rejected:
   two names with the wrong one authoritative means the documentation, the
   error messages and the tests all keep saying somebody else's name, which
   is the thing being fixed.
3. **Why this is better.** A symlink costs nothing at run time, nothing in the
   image and one line in the overlay. The Keel name is what the documentation,
   the recipes and the tests use, so the appliance describes itself by its own
   name; the old name stays a working entry point for as long as anyone points
   it at one. If the compatibility names are ever dropped, it is a deliberate
   decision with its own note and its own deprecation, not a side effect of a
   rename.

## Consequences

- Documentation, recipes, tests and error messages use the Keel name. A
  command that reports its own name reports the one that was typed, so an
  operator who ran `turnkey-wordpress-update` is not told about a command
  they did not run.
- A call site left on the old name still works, which is exactly why it is
  easy to miss and why the gate cannot catch it. Finding them is `grep -rn`
  over the repository (README, tests, `conf.d`, overlays) and not a green
  build.
- The compatibility names **must be covered** by tests that run them, in
  every repository that has a pair. A test that only reads the link does not
  discharge this note. Today keel-wordpress has such tests and nothing else
  does; the four in `common` and the five from `inithooks` and `confconsole`
  are owed them when they move.
- New commands get one name, the Keel one. This note is about names that
  already exist; nothing new is born with a `turnkey-*` alias.
- 0014 keeps `/etc/turnkey_version` for the same compatibility reason, and the
  changelog source names (`turnkey-wordpress-19.0`) are untouched here: they
  are what `make-release-deb.py` and `turnkey-version.py` read, so they belong
  to 0014's question and not to this one.
