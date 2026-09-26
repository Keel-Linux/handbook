# Organization plan: the complete fork under the guidelines

Date: 2026-09-26. Guidelines: docs/decisions/0006. Milestones: BRIEF.md
section 9. Coverage: docs/coverage-baseline.md.

## 1. Inventory and roles

| Repository | Role | Upstream | Tests today | Our branches | Owner of the gate |
| --- | --- | --- | --- | --- | --- |
| keel | library and CLI (new code) | none | 206, 100 percent | main | 95 percent, active |
| .github | org profile, reusable workflows | none | n/a | main | n/a |
| tkldev | build host appliance and setup | turnkeylinux-apps/tkldev | 63 bats on branch | fix/build-missing-bootstrap, docs/coverage-baseline | baseline then 90 |
| fab | build tool | turnkeylinux/fab | 19 make checks on branch | feat/source-date-epoch, docs/coverage-baseline | baseline then 90 |
| buildtasks | build tasks (bt-*) | turnkeylinux/buildtasks | 40 paths on branch | feat/bt-layer | baseline then 90 |
| common | shared plans, overlays, conf | turnkeylinux/common (19.x) | 7 bats on branch | fix/postfix-local-fatal, docs/coverage-baseline | baseline then 90 |
| inithooks | first boot | turnkeylinux/inithooks | 68 bats + 146 pytest on branches | 4 branches + docs/coverage-baseline | baseline then 90 |
| confconsole | operator console | turnkeylinux/confconsole | none | none yet | baseline then 90 |
| webmin | web admin packaging | turnkeylinux/webmin | none | none yet | baseline then 90 |
| turnkey-chroot | chroot helper | turnkeylinux/turnkey-chroot | 40 pytest, 100 percent | fix/umount-in-lxc | 95 percent, active |
| tklbam, tklbam-profiles, tklbam-python-boto, turnkey-pylib | backup (deferred, 0002) | turnkeylinux/* | profile lint on branch | fix/moodle-dataroot | baseline, last |
| cdroots | ISO boot files | turnkeylinux/cdroots | none | none | baseline |
| bootstrap | Debian bootstrap builder (debootstrap + fab) | turnkeylinux/bootstrap | none | none | baseline; forked 2026-09-26 after the M0 run showed it missing |
| keel-core | base appliance | turnkeylinux-apps/core | none | none yet | build + boot test |
| keel-lamp, keel-lapp, keel-nginx-php-fastcgi | stacks | turnkeylinux-apps/* | none | none yet | build + boot test |
| keel-wordpress, keel-moodle, keel-odoo, keel-redis, keel-ejabberd | apps | turnkeylinux-apps/* | none | none yet | build + boot test |
| keel-ojs, keel-mastodon, keel-pdns-recursor, keel-coturn, keel-nat64 | apps, to create | none | none | maintainer's existing work | build + boot test |

"Build + boot test" for appliances means: the recipe builds on the runner
(bt-layer or make), the result boots in an LXC container, its first boot
completes headless from an instance spec, and its main service answers over
IPv6. Coverage of an appliance recipe is that test passing; conf.d scripts we
touch also get the 0004 treatment.

## 2. Automation, in order

1. **Reusable workflows in `.github`**: `test-python.yml` (pytest under
   coverage, `coverage report --fail-under=<input>`), `test-shell.yml` (bats
   under kcov, threshold script), `test-appliance.yml` (self-hosted runner
   label `keel-lxc`: `keel pull` and `keel verify` from
   `https://mirror.keellinux.org/layers`, `keel assemble`, container boot,
   the repository's `tests/boot-test.sh`, HTTP check over IPv6). Each
   repository adds a ten-line workflow that calls one of them with its
   threshold; an appliance repository adds a second job for the boot test.
   Done 2026-09-26; the appliance workflow fetches layers rather than
   building them, because the runner has no fab, deck or buildtasks.
2. **Branch protection on every default branch**: pull request required, the
   coverage check required, linear history, no force push, no deletion.
   Preferably one organization ruleset applied to all repositories, so a new
   repository is protected the day it is created.
3. **Self-hosted runner**: registered at organization level with the
   `keel-lxc` label, done 2026-09-26. Not an LXC container of the build
   cluster as planned here: `keel-lxc-1` runs on the public services VM
   (docs/releases-host.md), which has native systemd, LXC, kcov and bats and
   the outbound IPv4 the GitHub API still needs. It deliberately has no fab,
   deck or buildtasks, so it consumes published layers instead of building
   them.
4. **Coverage badge** from the workflow's own output (job summary and a
   committed shields endpoint JSON), no third-party coverage service, since
   the number is already computed by the gate.

Blocked today on token scopes (`workflow` to push workflow files, `admin:org`
for organization rulesets and runner registration); everything else in this
section is prepared and can be pushed the moment the scopes exist.

## 3. Bringing each repository up to the guidelines

Same sequence per repository, one pull request each, smallest first:

1. Merge `docs/coverage-baseline` (the honest number and the plan).
2. Add the workflow calling the reusable one with the measured threshold.
3. Enable protection with that check required.
4. Merge our fix branches (each already carries its tests).
5. Raise the threshold as tests land, per the COVERAGE.md plan, until 90.

Order: keel and turnkey-chroot (already at 100, protection first), inithooks,
tkldev, buildtasks, fab, common, then confconsole and webmin (no branches yet:
baseline job first), then the appliances once `test-appliance.yml` and the
runner exist, then the tklbam family last (0002).

State on 2026-09-26. The per-repository thresholds and run conclusions are in
docs/ci-cd.md section 3; this is where each one stands in the sequence above.

| Repository | Steps 1 and 2 | Step 3 (protection) | Required checks |
| --- | --- | --- | --- |
| keel | done | done | `tests / coverage` |
| turnkey-chroot, inithooks, tkldev, buildtasks, fab, common, tklbam-profiles | done | done | `tests / coverage` |
| confconsole, webmin | done | done | `tests / coverage` |
| keel-core | done; the appliance job added 2026-09-26 | done | `tests / coverage` and `appliance / build-and-boot`, both required |
| keel-nodebb | done; the appliance job added 2026-09-26 | done | `tests / coverage`; the appliance check waits on buildtasks issue 6 |
| keel-nodejs-nginx (the stack layer) | created 2026-09-26 with the appliance gate wired | not started | `appliance / build-and-boot`, skipping with a notice until its layer is published |
| keel-lamp, keel-lapp, keel-wordpress, keel-moodle, keel-odoo, keel-redis, keel-ejabberd, keel-nginx-php-fastcgi | not started | not started | the appliance job skips with a notice until each layer is published, so the gate can be added before the layer exists |
| tklbam, tklbam-python-boto, turnkey-pylib, cdroots, bootstrap | last, per 0002 | not started | n/a |
| keel-linux.github.io (the site) | done 2026-09-26 | done | `python / coverage`: tools/sitecheck.py, the checks a build step would have done |
| .github (the reusable workflows) | done 2026-09-26 | done | `actionlint`, pinned by digest, and `tests / coverage` over the tools it lends the others |
| apt (the archive and its tooling) | done 2026-09-26 | not possible while private | `tests / coverage` at 99 runs on every pull request, but branch protection on a private repository needs a paid plan, so the check cannot be required until the repository is public with the key rotation |
| handbook | n/a, no code | not possible while private | same limitation; nothing executable lives there |

The last two rows are not code repositories and have no coverage number, so
the honest equivalent of the coverage gate is a check of what they actually
are: the site is checked for links, fragments, assets and page shape, and the
workflow repository is linted, including shellcheck over every run block. The
rule the guidelines state is that every repository has a required check, not
that every repository reports a percentage.

The two appliances that are through the sequence are the two whose layers are
published (docs/releases-host.md, publishing a layer). For the rest, adding
the caller is safe at any time: `test-appliance.yml` passes with a notice
while the layer is missing, so the gate is in place the day the first build
lands instead of being retrofitted.

### The gate that measures whether a change can be installed

Added 2026-09-26 after the confconsole lesson: the Instance menu and the
console mark were merged with no entry in `debian/changelog`, so the newest
installable confconsole stayed at the previous version and neither change
reached an appliance. The code was on the default branch and the gate was
green. A coverage gate measures the code, not whether the code can be
installed.

`require-changelog.yml` closes that: a pull request touching a file the package
ships must add a changelog entry with a greater version, while tests,
documentation and CI are exempt. It is required on the four repositories that
produce packages (confconsole, inithooks, keel, keel-transition) as
`package / changelog`.

## 4. Code changes the guidelines require

- tkldev-setup: map appliance names to `keel-<app>` when the remote is the
  organization (`GIT_REMOTE_URL` set to github.com/keel-linux), keep upstream
  behaviour otherwise. On the tkldev fork, with its bats test.
- bt-layer and the M0 gate procedure: product paths follow the same mapping.
- Documentation: the org profile and the site list the prefix rule; every
  README of an appliance fork states "compatible with TurnKey Linux
  appliances" and the upstream it tracks.

## 5. Milestone mapping

- M0 (now): sections 2 and 3 for the infrastructure repositories; keel-core
  builds from the organization; both are the M0 gate of docs/m0-gate.md.
- M1 (19.1): appliances onboarded through `test-appliance.yml`; keel-transition
  and the keyring package get their own repositories (infrastructure, no
  prefix: `keel-transition` is a package name, the repository can be
  `transition`); confconsole and webmin baselines and first tests.
- M2 and M3: as in BRIEF section 9, each new repository created under the
  ruleset from day one.

## 6. Decisions still open for the maintainer

- Whether keel-core is an appliance (prefixed, as done) or infrastructure.
- Runner hosting: which node of the cluster, and who holds the runner token.
- Whether the appliance boot test counts as the 90 percent for recipes
  (proposed above) or a per-file measure of conf.d scripts is required.
