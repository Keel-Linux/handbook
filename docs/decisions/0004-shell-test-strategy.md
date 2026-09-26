# 0004: How shell code is tested and measured

Date: 2026-09-25
Status: decided by the maintainer (closes the open item of 0003)

## Decision

Shell code in the project (first-boot hooks, bt-* build tools, setup scripts,
conf scripts we touch) is tested and measured as follows:

1. **Logic apart from effect.** Every script we write or touch is split: pure
   functions (parsing, decisions, rendering) in a sourceable library file with
   no side effects; the executable is a thin main that calls them. Same rule
   the brief applies to confconsole (section 6).
2. **bats for tests, PATH stubs for the world.** Tests are bats files
   (Debian package `bats`, 1.11 in Trixie). External commands (`systemctl`,
   `ip`, `ip6tables`, `wget`, `make`, `apt-get`, `postconf`) are replaced by
   stubs placed first in PATH that record their arguments and return what the
   test case dictates; system paths are replaced by scratch directories through
   the variables the scripts already read. Nothing in a unit test touches the
   live system.
3. **kcov for coverage, same threshold.** `kcov` (Debian package, 43 in
   Trixie) measures executed bash lines and exports a report; the 95 percent
   bar of 0003 applies to lines, and "branch coverage" for shell means every
   arm of every `if`, `case` and `||` chain has an executed line, which kcov
   shows. The number is checked by a small script committed in each repository
   and quoted in the PR.
4. **Integration on LXC remains the acceptance test.** A full build plus a
   first boot in a container proves the appliance works; unit coverage does not
   substitute for it and it does not count toward the unit number.

## Pragmatic limits

- Build-time conf scripts (`conf.d`, `conf/turnkey.d`) run inside a chroot with
  absolute paths and package tools. Refactoring them wholesale would be a
  rewrite, which the brief forbids. The ones we touch get the split and stubs;
  the rest are measured in a later phase by running kcov inside the build
  chroot during a real build.
- The strategic answer is to shrink shell: each time logic moves into the
  `keel` library (100 percent covered), the hook becomes a thin caller, as
  `00declarative` already is. Shell coverage work must not compete with that
  port; when a hook is about to be replaced by a library call, the test goes
  on the library, not on the shell.

## Justification (three parts, brief section 10)

1. Why the previous state does not work: the forks ship 0 percent measured
   coverage, and the seven fixes made this week were verified by hand on a VM,
   which is not repeatable and not reviewable.
2. Whether it could be made to work otherwise: hand verification could be
   scripted as integration runs only, but those need root, a build host and
   minutes per run, so they would never cover error paths (the missing nat
   table, the inactive unit, the 404) where this week's bugs lived.
3. Why this is better: stubs reach every error path in milliseconds without
   root; kcov gives a real number instead of a checklist; the split keeps
   upstream behaviour intact while making each script reviewable; and it lines
   up with the port, since the split logic is what later moves to Python.

## First batch

The nine touched files without automated tests (docs/coverage-baseline.md):
inithooks `01ipconfig`, `29tagid`, `bin/turnkey-init-fence`, `00declarative`,
`bin/declarative.py`; tkldev `tkldev-setup`; common `postfix-local`;
tklbam-profiles `moodle`; fab `share/product.mk`. Plus the two tested files
below the bar: turnkey-chroot `chroot/__init__.py` (59) and inithooks
`libinithooks/declarative.py` (72).
