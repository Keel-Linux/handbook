# CI and CD

Date: 2026-09-26. Implements decision 0006 item 4 and org-plan.md sections 2
and 3. Coverage standard: decisions 0003 and 0004.

## 1. What runs where

| Piece | Where | State |
| --- | --- | --- |
| Reusable workflows | `keel-linux/.github`, `.github/workflows/` | `test-python.yml`, `test-shell.yml`, `test-appliance.yml`, `build-deb.yml`; documented in `profile/WORKFLOWS.md` |
| Unit tests and coverage gate | hosted `ubuntu-latest` runners (plain virtual machines, no `container:` jobs, no images) | active in eight repositories |
| Appliance build and boot, Debian packages | self-hosted runner `keel-lxc-1`, labels `self-hosted, keel-lxc`, on the public services VM (docs/releases-host.md) | online since 2026-09-26; `test-appliance.yml` must fetch layers from the mirror before its first run (section 6) |
| Site | GitHub Pages, `keel-linux/keel-linux.github.io`, branch `main`, path `/`; the same checkout served at `https://www.keellinux.org/` and the apex by the public services VM (pull every 15 minutes) | published |

Each repository carries one ten-line caller, `.github/workflows/tests.yml`,
that runs on every pull request and on every push to the default branch and
calls the reusable workflow with the repository's threshold. Nothing else is
duplicated per repository: a fix to a reusable workflow on `.github` `main`
applies everywhere on the next run.

## 2. Check names

GitHub names a check from a reusable workflow `<caller job id> / <reusable
job id>`. All callers use the job id `tests` and both test workflows use the
job id `coverage`, so the required check is exactly:

    tests / coverage

Renaming the caller job renames the check and silently detaches it from
protection, so the job id `tests` is part of the contract. The other names,
for later: `tests / build-and-boot` (test-appliance.yml) and `package / deb`
(build-deb.yml, caller job id `package`).

## 3. Per-repository thresholds

Bootstrap runs of 2026-09-26 (push to the default branch, run 1 in each
repository):

| Repository | Default branch | Reusable workflow | Threshold | Run conclusion | Protection |
| --- | --- | --- | --- | --- | --- |
| keel | main | test-python (`package: keel`) | 95 | success (206 tests, 100 percent) | protected since 2026-09-26, after the repository was made public |
| turnkey-chroot | master | test-python (`package: chroot`) | 95 | failure: 44 percent with the 10 upstream tests (expected, see below) | on |
| inithooks | master | test-shell | 0 | success (placeholder notice) | on |
| tkldev | master | test-shell | 0 | success (placeholder notice) | on |
| buildtasks | 19.x | test-shell | 0 | success (placeholder notice) | on |
| fab | master | test-shell | 0 | success (placeholder notice) | on |
| common | 19.x (created from upstream 19.x, made default; the fork's previous default was 18.x) | test-shell | 0 | success (placeholder notice) | on |
| tklbam-profiles | master | test-shell | 0 | success (placeholder notice) | on |
| confconsole | master (fast-forwarded to upstream 0f37b48 on 2026-09-26; the fork's tip a2d9f70 was 50 upstream commits behind) | test-python (`package: ifutil`), after a test-shell placeholder at 0 in the baseline pull request | 99 | success (103 tests, ifutil.py 99.21 percent) | on since 2026-09-26 |
| webmin | master (equal to upstream) | test-shell | 0 | success (placeholder notice; the project code is the Python update tool `buildsrc_lib`, and the first pytest switches the caller to test-python) | on since 2026-09-26 |
| .github | main | none (no code under test) | n/a | n/a | on, no required check |
| keel-linux.github.io | main | none (static site) | n/a | n/a | on, no required check |

`docs/coverage-baseline` (COVERAGE.md) was merged into the default branch of
turnkey-chroot, inithooks, tkldev, fab, common and tklbam-profiles with a
merge commit; buildtasks and keel never had that branch. confconsole and
webmin followed on 2026-09-26 (pull request #1 in each, COVERAGE.md and the
caller in the same branch, check green before protection was applied);
confconsole #2 added the first tests (ifutil.py) and switched the caller to
test-python at 99.

The check from the bootstrap placeholder and the check from test-python
carry the same name, `tests / coverage`, so switching a repository from
test-shell to test-python needs no change to its protection rule.

Rules for the number:

- The threshold is the measured baseline from the repository's `COVERAGE.md`
  and lives in the caller (`with: threshold:`), so raising it is a reviewed
  change in the repository, not a dashboard setting. Zero means "nothing is
  measured on this branch", and the caller says so in a comment.
- It is only ever raised, never lowered (decision 0006). Target: 90 for any
  repository, 95 for project-authored code (0003).
- turnkey-chroot is set to 95 on purpose: the one file we touch must reach
  the 95 bar and does so on `fix/umount-in-lxc` (100 percent, 40 tests), so a
  pull request from that branch passes while `master` alone fails. Until it
  merges, the red check on `master` is the honest state of the fork.
- Shell repositories: the gate runs `tests/coverage.sh` with the threshold in
  the environment variable `COVERAGE_THRESHOLD`. Until the script exists on
  the default branch and the threshold is 0, the job passes with a notice; a
  threshold above 0 without a script fails. When a fix branch brings the
  script, raise the threshold in the same pull request.
- Interface note for the fix branches: the `tests/coverage.sh` on inithooks
  reads `COVERAGE_THRESHOLD`; the ones on tkldev, fab and tklbam-profiles
  read the first positional argument and default to 95. Before those branches
  merge, their scripts need `threshold="${1:-${COVERAGE_THRESHOLD:-95}}"` so
  the number in the caller is the number enforced. One line each.
- inithooks will need a second job once `feat/declarative-instance` merges
  (pytest for `libinithooks`, via test-python.yml with `package:
  libinithooks`); its check name will be `<job id> / coverage` and must be
  added to the protection rule of `master`.

## 4. Onboarding a new repository

1. Copy the caller (ten lines) into `.github/workflows/tests.yml` on the
   default branch, with the branch name and the measured threshold:

        name: tests
        on:
          pull_request:
          push:
            branches: [master]
        jobs:
          tests:
            uses: keel-linux/.github/.github/workflows/test-shell.yml@main
            with:
              threshold: 0

   Python: `test-python.yml` with `package: <import name>`. Appliances:
   `test-appliance.yml` with `appliance:` and `parent:` (after the runner).
2. Push once to the default branch (allowed only before protection exists)
   and confirm the check `tests / coverage` appears on the commit:
   `GET /repos/keel-linux/<repo>/commits/<sha>/check-runs`.
3. Apply protection to the default branch:

        gh api -X PUT repos/keel-linux/<repo>/branches/<branch>/protection \
          --input protection.json

   with `protection.json`:

        {
          "required_status_checks": {"strict": true,
                                     "checks": [{"context": "tests / coverage"}]},
          "enforce_admins": true,
          "required_pull_request_reviews": {"dismiss_stale_reviews": true,
                                            "0 approvals while the organization has one maintainer (decision 0007)},
          "restrictions": null,
          "required_linear_history": true,
          "allow_force_pushes": false,
          "allow_deletions": false
        }

   Verified state on the nine protected branches (GET, 2026-09-26): checks
   `["tests / coverage"]`, strict true, enforce_admins true, approvals 1,
   dismiss_stale true, linear_history true, force_pushes false, deletions
   false (`.github` and `keel-linux.github.io`: same, with no required
   check).
4. From then on, every change is a pull request with 0 approvals while the organization has one maintainer (decision 0007) and a
   green `tests / coverage`, and the branch must be up to date with the base
   (strict) before merging.

## 5. What needs the maintainer

- **Organization ruleset.** The API answers 403 "Upgrade to GitHub Team to
  enable this feature" on the free plan, so per-repository branch protection
  is the mechanism. A ruleset that protects every repository the day it is
  created becomes an option only if the organization moves to the Team plan.
- **keel visibility, resolved 2026-09-26.** Branch protection on a private
  repository is refused on the free plan; the maintainer made `keel` public,
  consistent with decision 0006 (one public organization), and `main` now
  carries the same protection as the other repositories.
- **Runner registration**: done 2026-09-26, section 6.
- **Organization variable `KEEL_LXC_RUNNER`** was set to `true` on
  2026-09-26 after the runner showed online. Callers of `build-deb.yml` and
  `test-appliance.yml` gate on `if: vars.KEEL_LXC_RUNNER == 'true'` so no job
  sits queued for 24 hours against a label no runner carries; set it back to
  `false` if the runner goes away.
- Local clones: `Keel/repos/keel` (uncommitted work on `main`) and
  `Keel/repos/dot-github` were left on their checked-out branches and are
  behind `origin`; `git pull --ff-only` when convenient.

## 6. The self-hosted runner (what was done, 2026-09-26)

The runner was not put in an LXC container of the build cluster as first
planned; it runs on the public services VM (`keellinux.org`,
`2804:710:d0:5::13`, Debian 13, docs/releases-host.md), which has native
systemd, LXC for boot tests and outbound IPv4 for the GitHub API (which has
no IPv6). Commands as root unless stated.

1. Packages: `lxc lxc-templates kcov bats shellcheck python3-yaml zstd git
   curl libicu76 file`. User `runner` with sudo limited to `apt-get` and the
   `lxc-*` commands (`/etc/sudoers.d/runner`).
2. Runner 2.337.0 unpacked in `/home/runner/actions-runner` (tarball from
   `github.com/actions/runner/releases`, version read with
   `gh api repos/actions/runner/releases/latest --jq .tag_name`).
3. Registration token (valid one hour, admin:org), obtained on a workstation
   and piped to the VM in the same command, never stored:

        gh api -X POST orgs/keel-linux/actions/runners/registration-token --jq .token \
          | ssh -6 popsolutions@keellinux.org 'IFS= read -r T; cd /home/runner/actions-runner && \
            sudo -n -u runner ./config.sh --unattended --url https://github.com/keel-linux \
            --token "$T" --name keel-lxc-1 --labels keel-lxc --runnergroup Default --work _work --replace'

   GitHub adds `self-hosted`, `Linux`, `X64`; `keel-lxc` is the label the
   workflows target.
4. Service: the tarball no longer ships `svc.sh`, so the unit is written by
   hand, `/etc/systemd/system/actions-runner.service` (`User=runner`,
   `ExecStart=/home/runner/actions-runner/run.sh`, `Restart=always`,
   `KillMode=process`), enabled and active. Journal shows
   `Listening for Jobs`.
5. Verified with `gh api orgs/keel-linux/actions/runners`:
   `keel-lxc-1 online ["self-hosted","Linux","X64","keel-lxc"]`; then
   `KEEL_LXC_RUNNER` set to `true` with
   `gh api -X PATCH orgs/keel-linux/actions/variables/KEEL_LXC_RUNNER -f value=true`.

What the runner host deliberately lacks: fab, deck, buildtasks, the
`/turnkey/*` trees and `/mnt/builds/layers`. Layer builds stay on the build
host (docs/build-host.md). Consequences, to be done before the first
appliance job:

- `test-appliance.yml` must stop calling `bt-layer` and instead download
  `<appliance>.tar.zst` plus `.sha256` from
  `https://mirror.keellinux.org/layers/` over IPv6, verify the checksum, and
  run `keel verify` and `tests/boot-test.sh` against a local layers
  directory. Until then a caller fails at the build step on this runner.
- `build-deb.yml` needs `build-essential devscripts equivs fakeroot dpkg-dev`
  on the runner host; not installed yet.
- The `keel` command is not installed on the runner host either; the
  workflow should install it from the archive once `archive.keellinux.org`
  is signed, or check it out and run it from the tree.

## 7. CD: what is published where today

| Artifact | Published to | Mechanism | State |
| --- | --- | --- | --- |
| Organization site | `https://keel-linux.github.io/` | GitHub Pages from `main` at `/` (build type legacy, `.nojekyll`, HTTPS enforced); a push to `main` is the deployment | live, `GET /repos/keel-linux/keel-linux.github.io/pages` reports `status: built`. If it is ever disabled: `POST /repos/keel-linux/keel-linux.github.io/pages` with `{"source": {"branch": "main", "path": "/"}}` |
| Debian packages | workflow artifacts only (`build-deb.yml`, artifact `deb`, 30 days) | `dpkg-buildpackage -us -uc -b` on the LXC runner | inactive until the runner exists; nothing is signed |
| APT repository | `https://archive.keellinux.org/` (README only) | `bin/publish` in repos/apt, target to be switched from Pages to this host | blocked on the signing key (decision 0005) |
| Appliance layers and manifests | `https://mirror.keellinux.org/layers/` (staging, unsigned, header `X-Keel-Distribution`) | `keel-sync-layers` on the VM pulls from the build host's temporary mirror and verifies sha256 (docs/releases-host.md section 6) | staging layers served; signed manifests blocked on the key |

The APT repository, the keyring package and layer publication follow the
decision 0005 outcome; when it lands, the publication step is added to
`build-deb.yml` (upload of the signed `.deb` and `Release` to the chosen
host over IPv6, `archive.keellinux.org` at `[2804:710:d0:5::13]`), not to the
callers.
