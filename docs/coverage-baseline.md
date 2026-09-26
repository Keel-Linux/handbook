# Fork test coverage baseline

Date: 2026-09-24. Companion to decision 0003 (test coverage standard).
Each fork now carries a `COVERAGE.md` on branch `docs/coverage-baseline`,
created from the upstream default branch, with the measurement command,
the per-file plan and a size estimate per file.

Measurement: Python with `coverage run --branch` plus `pytest`; shell with
nothing, because no shell coverage tool is wired up yet (decision 0003 open
item). Where no test exists the baseline is 0 percent measured, not an
estimate. Line counts exclude blank and comment lines.

## Summary

| Repository | Upstream base | Measured baseline | Touched files with tests | Touched files without tests | Plan size |
|------------|---------------|-------------------|--------------------------|-----------------------------|-----------|
| tkldev | master 6b42342 | 0 percent, 5 shell files, 376 lines, no test | none | tkldev-setup | 1 large, 1 medium, 3 small |
| common | 19.x b60dd23 | 0 percent, 107 shell and 11 Python files, 3713 lines, no test | none | conf/turnkey.d/postfix-local | 1 large (bootstrap_apt), about 12 medium, about 100 small, quicktile.py vendored (exclude) |
| inithooks | master 33c43b8 | 0 percent on upstream (the only tests/ file is a manual launcher); on feat/declarative-instance 26 percent over libinithooks and bin, declarative.py 72 percent | libinithooks/declarative.py (72, below the 95 bar) | firstboot.d/01ipconfig, firstboot.d/29tagid, bin/turnkey-init-fence, bin/declarative.py, firstboot.d/00declarative | 3 large (dialog_wrapper, simplehttpd, turnkey-sudoadmin), 5 medium, about 25 small |
| tklbam-profiles | master 2e38ada | 0 percent, 2 shell hooks and 1 pypy2 script, 208 lines, 150 profile lists unchecked | none | moodle (profile list) | 1 large (per-appliance path check, open item), 1 medium (port make-profile), 3 small |
| turnkey-chroot | master 52bcfa6 | 44 percent (10 tests); 59 percent on fix/umount-in-lxc (13 tests), one file | chroot/__init__.py (59, below the 95 bar) | none | 1 medium, 4 small, about 15 to 20 tests |
| fab | master d7a314d | 0 percent, 16 Python, 6 shell, 1 Makefile include, 2719 lines; tests/regtest.sh is a root-and-network harness, not run | none | share/product.mk | 1 large (fab entry point), 6 medium, about 8 small |
| confconsole (2026-09-26) | master 0f37b48 (fork fast-forwarded from a2d9f70, 50 upstream commits, to pick up the IPv6-aware ifutil.py of upstream #109) | 0 percent, 20 Python files (3138 lines) and 7 shell files (575 lines), no test | none at fork time; ifutil.py 99.21 after PR #2 (103 tests) | none touched yet; ifutil.py is first because plan 04 section 3.2 changes it | 3 large (confconsole.py, ifutil.py, dehydrated-wrapper), about 6 medium, about 18 small |
| webmin (2026-09-26) | master 26ce63fd (equal to upstream, Webmin 2.660) | 0 percent, project code is 2 Python files (buildsrc, buildsrc_lib, 619 lines) and 6 shell and make files (124 lines), no test; 3561 vendored upstream Perl files (393130 lines) are not project code and not measured | none | none | 1 large in pieces (buildsrc_lib), 1 medium (plugins_deb_rules.sh, bats, when touched), 4 small; the package build and the boot test run on the LXC runner |

## Touched files against the 95 percent bar

Eleven code files are touched across nine branches. Two have automated
tests and neither reaches 95 percent:

- inithooks `libinithooks/declarative.py`: 31 tests, 72 percent line and
  branch (438 statements, 110 missed, 38 partial branches).
- turnkey-chroot `chroot/__init__.py`: 13 tests, 59 percent (156
  statements, 53 missed).

Nine have no automated test. Seven were verified by hand on a VM:
`tkldev-setup`, `postfix-local`, `01ipconfig`, `29tagid`,
`turnkey-init-fence`, the `moodle` profile and `product.mk`. Two are the
wrappers around the declarative module on feat/declarative-instance,
`bin/declarative.py` (0 percent) and `firstboot.d/00declarative` (shell,
no test). Documentation and packaging files on that branch (`README.rst`,
`debian/control`, `default/inithooks`, release notes) are not code.

## Order of work

1. Bring the two tested files to 95: declarative.py (medium: stub `ip`
   for the live-system readers, one test per validator error) and
   chroot/__init__.py (medium: `mount()` loop, `umount()` errors, `run()`
   branches).
2. Add tests for the nine untested touched files, smallest first:
   29tagid, postfix-local, 00declarative, bin/declarative.py, moodle,
   01ipconfig (small each); turnkey-init-fence, product.mk (medium);
   tkldev-setup (large, split helpers into a sourceable file first).
3. First-boot path in inithooks (`run`, `turnkey-init`, remaining hooks)
   and in common (14 overlay hooks, 6 inithooks Python helpers).
4. The rest per each repository's `COVERAGE.md`.

Shell coverage numbers cannot be reported until the decision 0003 open
item (kcov versus checklist) is settled; until then a shell file counts as
covered only by the explicit code-path checklist in its test file.

## Update 2026-09-25: first batch done

Every file we had touched without automated tests now has them, on the same
branches, following docs/decisions/0004 (logic split into a sourceable
library where needed, bats with PATH stubs, kcov on the build host, a
`tests/coverage.sh` per repository failing below 95). Behaviour unchanged;
the 01ipconfig static output was re-checked on the build host after the split
and is identical to the hand-verified one.

| Repository, branch | Tests | Coverage (kcov unless noted) | Merged into <default> (2026-09-26, docs/merge-log-2026-09-26.md) |
| --- | --- | --- | --- |
| inithooks fix/01ipconfig-static | 27 bats | 01ipconfig 23/23, lib/ipconfig.sh 25/25 | master, PR #1, 4e09d1e |
| inithooks fix/29tagid-inactive-fence | 14 bats | 29tagid 19/19, lib/tagid.sh 8/8 | master, PR #2, a20a94a |
| inithooks fix/fence-without-nat | 27 bats | turnkey-init-fence 28/28, lib/init-fence.sh 63/64 (98.4, multi-line command artefact) | master, PR #3, 8f77b85 (teardown fix added) |
| inithooks feat/declarative-instance | 146 pytest | 99 percent lines and branches (coverage.py) | master, PR #4, e133407 (merge of master for tests/README.md); python job and 98/95 thresholds in PR #5, f738762 |
| tkldev fix/build-missing-bootstrap | 63 bats | tkldev-setup 185/186 (99.5, continuation line artefact) | master, PR #1, 994ecf4 (COVERAGE_THRESHOLD fix added); threshold 99 in PR #2; keel-APP mapping in PR #3, bea8030 |
| common fix/postfix-local-fatal | 7 bats | postfix-local 17/17 | 19.x, PR #2, 5a0a381 (COVERAGE_THRESHOLD fix added); threshold 100 in PR #3 |
| fab feat/source-date-epoch | 19 TAP checks via make -n | 19/19 assertions (no line tool for make); 7 of them fail against the old product.mk | master, PR #1, e79be43 (COVERAGE_THRESHOLD fix added); threshold 100 in PR #2 |
| tklbam-profiles fix/moodle-dataroot | profile lint, 4 checks | 4/4; the stale profile fails 3 | master, PR #1, 71b3766 (COVERAGE_THRESHOLD fix added); threshold 100 in PR #2 |
| turnkey-chroot fix/umount-in-lxc | 40 pytest | 100 percent lines and branches (coverage.py) | master, PR #1, 0b1c044; COVERAGE.md baseline in PR #2; threshold stays 95 |
| buildtasks feat/bt-layer | tests/layer, 40 paths | layer-lib 183/183, bt-layer 99/100 | 19.x, PR #1, ad4e8fe (tests/coverage.sh added); threshold 99 and COVERAGE.md in PR #2 |
| confconsole test/ifutil (2026-09-26) | 103 pytest | ifutil.py 99.21 percent lines and branches (coverage.py); the 3 missed lines are an unused inner function | master, PR #2, 137e39c (COVERAGE.md baseline and placeholder caller in PR #1, efb7694); threshold 0 to 99 in PR #2 |
| webmin (2026-09-26) | none yet | 0 percent measured | master, PR #1, c5049d3 (COVERAGE.md and placeholder caller only) |

Two side effects worth knowing: tkldev-setup gained a `TKLBAM_PATH` override
(the hardcoded /turnkey/tklbam-profiles would otherwise be created on the
system running the tests) and a source guard so its functions can be loaded
without running the main body; the inithooks package now installs a `lib/`
directory. All pushed to the forks.

## Update 2026-09-26: confconsole and webmin onboarded

Both forks now carry a `COVERAGE.md`, the caller workflow and branch
protection on `master` (check `tests / coverage`, strict, admins enforced,
0 approvals, no force push, no deletion, merge commits). Each baseline
pull request created the check with the test-shell placeholder at 0,
because test-python cannot run without a test file; confconsole #2 then
added 103 tests for `ifutil.py` (99.21 percent) and switched its caller to
test-python at 99. The confconsole fork's `master` was fast-forwarded from
a2d9f70 to upstream 0f37b48 first (50 upstream commits, nothing lost), so
the tests target the IPv6-aware `ifutil.py` that plan 04 section 3.2
changes. webmin's project code is the Python update tool `buildsrc_lib`
(619 lines) plus 124 lines of packaging shell; the vendored Webmin Perl is
upstream code outside the floor, and what a test means there (unit tests
on `buildsrc_lib`, a control-file lint against `modules/`, `themes/` and
the appliance plans, the package build and the boot test on the LXC
runner) is written in its `COVERAGE.md`.

## Update 2026-09-26: all branches merged

Every branch of the table above is merged into its fork's default branch
(last column) and the workflow of each repository enforces the measured
number: turnkey-chroot 95, inithooks 98 (shell) and 95 (Python),
tkldev 99, common 100, fab 100, tklbam-profiles 100, buildtasks 99. Details,
including the kcov pipeline fix and the per-branch fixes, are in
docs/merge-log-2026-09-26.md.
