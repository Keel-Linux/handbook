# 0015: Operator facing commands carry the Keel name, with the turnkey name kept

Date: 2026-09-28
Status: decided by the maintainer

## Decision

A command an operator types on a Keel appliance carries this project's name.
Where such a command already exists under a `turnkey-*` name:

- the **Keel name is the real command** — the file with the code in it;
- the **`turnkey-*` name is kept, as a symlink to it**;
- **both keep working**, and neither is documented as deprecated.

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
and a rename with no link is exactly that loss — it fails at the moment the
operator needs the command, with `command not found` and no hint of a new
name.

## What a `turnkey-*` name owned by a Debian package does instead

Nothing in this note. `turnkey-sysinfo` and `turnkey-version` are shipped by
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
build host is `/usr/bin/turnkey-sysinfo`, `/usr/bin/turnkey-detect-virt`, the
`libsysinfo` Python package it imports and the motd fragment under
`/usr/share/turnkey-sysinfo/contrib`. `turnkey-detect-virt` was missed, so the
table's five commands are really six. tracker#13 has to cover both names and
the library, because replacing only `turnkey-sysinfo` leaves a `keel-sysinfo`
calling a `turnkey-detect-virt` nobody owns.

## Which commands this changes now, and which wait

The five rows of tracker#12, re-measured:

| Command | Where it really comes from | When |
| --- | --- | --- |
| `/usr/local/bin/turnkey-wp` | `keel-wordpress`, `overlay/usr/local/bin` | **now** |
| `/usr/local/sbin/turnkey-wordpress-update` | `keel-wordpress`, `overlay/usr/local/sbin` | **now** |
| `/usr/local/bin/turnkey-php` | `common`, `overlays/php/usr/local/bin` | next rebuild of the chain |
| `/usr/local/bin/turnkey-mysql-install-perf-info-schemas` | `common`, `overlays/mysql/usr/local/bin` | next rebuild of the chain |
| `turnkey-sysinfo`, `turnkey-version`, `turnkey-detect-virt` | Debian packages `turnkey-sysinfo`, `turnkey-version` | tracker#13, by replacing the packages |

The two `keel-wordpress` ones change now because that appliance's own overlay
writes them, so they need no core rebuild: the recipe is rebuilt, one layer is
republished, and the chain under it is untouched.

The middle two are a **correction to tracker#12's table**, which calls them
"inherited, build time". They are not inherited in the sense of being outside
this project's custody. Both are ordinary files in `Keel-Linux/common`, a
repository of this organization, reaching the image through `COMMON_OVERLAYS`
(`php.mk` and `mysql.mk` each add their overlay) and `fab-apply-overlay`. The
policy applies to them in full. What makes them wait is not ownership but
blast radius: `common` is under every appliance, so renaming there is a
rebuild of the whole chain, and it is done as part of a deliberate rebuild
rather than on its own. `turnkey-mysql-install-perf-info-schemas` also has a
caller inside `common` itself,
`overlays/mysql/usr/lib/confconsole/plugins.d/System_Settings/Mysql_perf_info.py`,
which moves in the same commit.

## How the symlink is made, and how that was checked

**In the overlay, committed to git.** Not `ln -s` in `conf.d/main`.

`fab-apply-overlay` is `cp -TdR OVERLAY DEST` (`cmd_apply_overlay` in fab),
and `-d` is `--no-dereference --preserve=links`, so a symlink in an overlay
arrives in the image as a symlink. Git stores it as a symlink too, mode
`120000`, so the repository says plainly what the appliance will have. The
layer tarball is created and extracted by `tar`, which carries symlinks
natively.

This was checked by doing it, not by reading the flags, because
docs/traps.md records "asserting the configuration is not asserting the
behaviour" as a defect this project keeps repeating. `tests/wrappers.bats` of
keel-wordpress copies the overlay with the same `cp -TdR` the build runs,
**twice** — that recipe applies its overlay twice, once through
`COMMON_OVERLAYS` and once as the product-local `ROOT_OVERLAY`, and a second
copy over an existing link has to leave a link and not a copy of its target —
and then *runs the copied `turnkey-wp`* and checks the command it produced.
`tests/v19.sh` does the same thing on a booted appliance: `turnkey-wp` is
asked for the core version and the site URL that `keel-wp` has just reported,
and the updater's root guard is required to hold under the old name too.
`test -L` says a link exists; it does not say the appliance still answers to
the old name.

The alternative, `ln -sf` in `conf.d/main`, was rejected for three reasons: it
puts the fact in a build script instead of in the tree the reader is looking
at; it runs only at build time, so a rebuild is needed to notice it is
missing; and it cannot be tested without a chroot, while an overlay file is
tested by copying a directory.

## Justification (three parts, brief section 10)

1. **Why the present state does not hold.** The appliance speaks another
   distribution's name in the commands an operator types every day, and for
   two of them that name is written by this project, in this project's
   repository, by a recipe this project maintains. That is not inherited
   surface, it is ours, and leaving it is a choice we would be making every
   release.
2. **Whether a plain rename would do.** No. It breaks every script written
   against the old name and every command in TurnKey's documentation, and it
   breaks them at a distance, long after the upgrade, with an error that does
   not name the replacement. The project's compatibility claim (0008) is not
   compatible with that. The opposite — keeping the `turnkey-*` name as the
   real command and adding a Keel alias — was also considered and rejected:
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
  over the repository — README, tests, `conf.d`, overlays — and not a green
  build.
- The compatibility names are covered by tests that run them, in every
  repository that has a pair. A test that only reads the link does not
  discharge this note.
- New commands get one name, the Keel one. This note is about names that
  already exist; nothing new is born with a `turnkey-*` alias.
- 0014 keeps `/etc/turnkey_version` for the same compatibility reason, and the
  changelog source names (`turnkey-wordpress-19.0`) are untouched here: they
  are what `make-release-deb.py` and `turnkey-version.py` read, so they belong
  to 0014's question and not to this one.
