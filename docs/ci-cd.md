# CI and CD

Date: 2026-09-26. Implements decision 0006 item 4 and org-plan.md sections 2
and 3. Coverage standard: decisions 0003 and 0004.

## 1. What runs where

| Piece | Where | State |
| --- | --- | --- |
| Reusable workflows | `keel-linux/.github`, `.github/workflows/` | `test-python.yml`, `test-shell.yml`, `test-appliance.yml`, `build-deb.yml`; documented in `profile/WORKFLOWS.md` |
| Unit tests and coverage gate | hosted `ubuntu-latest` runners (plain virtual machines, no `container:` jobs, no images) | active in eight repositories |
| Appliance boot test | self-hosted runner `keel-lxc-1`, labels `self-hosted, keel-lxc`, on the public services VM (docs/releases-host.md) | online since 2026-09-26. `test-appliance.yml` fetches the layers from `https://mirror.keellinux.org/layers`, verifies, assembles, boots in LXC and runs the repository's `tests/boot-test.sh`; it builds nothing, because the runner has no fab, deck or buildtasks. Callers: keel-core and keel-nodebb. First green CI run on keel-core 2026-09-26, 39 seconds; required on `master` since |
| Debian packages | the same runner | `build-deb.yml` unchanged and still inactive: `build-essential devscripts equivs fakeroot dpkg-dev` are not installed on the runner host |
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
protection, so the job id `tests` is part of the contract.

An appliance repository carries a second caller job, `appliance`, which calls
`test-appliance.yml` (job id `build-and-boot`), so its check is exactly:

    appliance / build-and-boot

The remaining name, for later: `package / deb` (build-deb.yml, caller job id
`package`).

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
| keel-core | master | test-shell (threshold 100) **plus** test-appliance (`appliance: core`, `parent: ""`) | 100 | both success: `tests / coverage` 2m41s, `appliance / build-and-boot` 39s (run 36272285880, container `keel-core-ci-36272285880-1`, `keel diff` 6 same and 0 drift) | on; **both** checks required since 2026-09-26 |
| keel-nodebb | main | test-shell **plus** test-appliance (`appliance: nodebb`, `parent: nodejs-nginx`) | 95, the lowest of the three measured shell files (`40nodebb` at 96.97; the other two at 100) | `tests / coverage` success. The boot test run by hand on the runner fails on a real defect of the published layer (buildtasks issue 6), so the appliance check stays advisory | on since 2026-09-26, `tests / coverage` required |
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

   Python: `test-python.yml` with `package: <import name>`. Appliances add a
   second job, `appliance`, calling `test-appliance.yml` with `appliance:`,
   `parent:` and `timeout:`, gated on `if: vars.KEEL_LXC_RUNNER == 'true'`;
   its check is `appliance / build-and-boot` and it is required only once it
   has passed once, because it depends on a layer being published.
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
- **Runner group: public repositories, opened 2026-09-26.** Runner group 1
  (`Default`) had `allows_public_repositories: false` while every repository
  of the organization is public, so GitHub accepted an
  `appliance / build-and-boot` job and then left it queued with `keel-lxc-1`
  online and idle. That was the one thing between the gate and its first real
  run. Opened with:

        echo '{"allows_public_repositories":true}' \
          | gh api --method PATCH /orgs/keel-linux/actions/runner-groups/1 --input -

  A self-hosted runner that serves public repositories must never run code
  from an unreviewed fork. Until 2026-10-01 the fork pull request policy
  only held back first-time contributors; it now requires approval for all
  outside contributors:

        gh api -X PUT orgs/keel-linux/actions/permissions/fork-pr-contributor-approval \
          -f approval_policy=all_external_contributors

  Every pull request until then came from a branch of the repository itself,
  not a fork, so nothing unreviewed has run. Section 6 says what else
  changed on the runner that day.
- **A queued job carries the workflow definition it was queued with.** The
  runs that had piled up against the closed runner group were expanded from
  the old `test-appliance.yml` and ran `bt-layer` when they were finally let
  through. Cancel stale queued runs after changing a reusable workflow and
  trigger a fresh one; the check is only meaningful on a run created after
  the change.
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
   curl libicu76 file`, and `uidmap` since 2026-10-01. User `runner`, which
   had sudo for `apt-get` and the `lxc-*` commands until 2026-10-01 and has
   none now (see "Without sudo" below).
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
host (docs/build-host.md). What that cost, and how it was settled on
2026-09-26:

- `test-appliance.yml` was rewritten (`.github` pull request #3) and no
  longer calls `bt-layer`. It probes
  `https://mirror.keellinux.org/layers/<appliance>.manifest` over IPv6,
  checks the published `parent` against the caller's `parent` input, runs
  `keel pull` into a scratch cache and `keel verify` (0, 8 and 9 pass; 6 and
  7 fail), then hands the assemble, the boot and the checks to the
  repository's `tests/boot-test.sh`, run as root through
  `/usr/local/sbin/keel-ci-boot-test` until 2026-10-01 and as root of a user
  namespace through `bin/unprivileged-lxc` of `keel-linux/.github` since
  (see "Without sudo" below). Every run gets its own container name
  and scratch tree, `keel-<appliance>-ci-<run id>-<attempt>`, and a cleanup
  step with `if: always()` destroys both. When the manifest is not on the
  mirror the job passes with a notice and an "Appliance test skipped"
  section in the job summary, so a repository whose layer was never
  published does not fail forever. Only a 404 is a skip: a name that does
  not resolve, a refused connection or a 5xx fails the job, because a skip
  on an outage is a green check that tested nothing. That distinction was
  added after a rehearsal on the runner skipped for the wrong reason
  (`.github` pull request #4).
- `keel` comes from a checkout of `keel-linux/keel` at `main`, not from a
  package: decision 0005 is open, nothing is signed and
  `archive.keellinux.org` has no keel package, so there is nothing to
  install. The checkout needs only python3 and PyYAML, both on the runner,
  and the job summary records the commit it resolved to. When the archive is
  signed, the two lines that clone become an `apt-get install keel`.
- `build-deb.yml` still needs `build-essential devscripts equivs fakeroot
  dpkg-dev` on the runner host; not installed.
- What the runner needed beyond the packages it already had, on
  2026-09-26: `apparmor` (4.1.0, already present); `/var/tmp/keel-ci` owned
  by `runner`; two root-owned entry points, `keel-ci-boot-test` and
  `keel-ci-cleanup`, added to `/etc/sudoers.d/runner` next to `apt-get` and
  the `lxc-*` commands. That sudo policy was root-equivalent, and on
  2026-10-01 it was removed together with both entry points (below).
- Address family for the mirror: the probe and `keel pull` let the resolver
  choose rather than forcing IPv6. The mirror is served by the same VM the
  runner runs on, and that VM resolves its own public names to itself
  (`resolvectl query mirror.keellinux.org` answers `127.0.1.1`, `Data from:
  synthetic`), so there is no AAAA record there to force and `curl -6` cannot
  resolve the name at all. The transfer never leaves the machine. Anywhere
  the name has an AAAA record, which is everywhere else, it goes over IPv6.
- Container networking: `lxcbr0`, whose dnsmasq advertises the ULA prefix
  `fc42:5009:ba4b:5ab0::/64` with `ra-only`, so a container has a global
  scope IPv6 address about five seconds after `lxc-start` and the host can
  reach it, which the HTTP checks of an appliance need. A macvlan interface
  on `eth0` would give a public address but a host cannot reach its own
  macvlan children.

### What one real run does

`core`, run 36272285880 of keel-core, the first `appliance / build-and-boot`
in CI: **39 seconds**, every step green. The probe answered 200, the published
parent `none` matched the caller, `keel pull` took the layer from the mirror,
`keel verify` passed, the chain assembled into
`/var/tmp/keel-ci/keel-core-ci-36272285880-1/lxc/...`, the container
`keel-core-ci-36272285880-1` started on `lxcbr0` and had the address
`fc42:5009:ba4b:5ab0:3a3c:c7b3:c779:316f` five seconds later, the first boot
finished five seconds after that, `keel diff` reported 6 same and 0 drift, and
`keel-ci-cleanup` removed the container and the scratch tree. The unit test
job on the hosted runner took 2m41s, four times as long as the boot test.

The same sequence replayed by hand beforehand, as the `runner` user, from a
clean clone of `master`: clone, keel checkout, manifest 200, published parent
`none` matching the caller, `keel pull` 3 s (the mirror is the same host),
`keel verify` exit 9 (every layer matches; the packages half is not
implemented, and `core` no longer carries a `.hash` file, so it is 9 rather
than 8), assemble 13 s, container started with a global IPv6 address in 5 s,
first boot finished 5 s later, `keel diff` 6 same, 0 drift, 2 unknown
(`instance.fqdn` and the IPv6 method, neither readable from an offline root),
exit 13. **30 seconds for the whole job**, then `keel-ci-cleanup` removed the
container and the scratch tree.

`nodebb`: `keel pull` of the three layers, 598 MB, 7 s; `keel verify` exit 8;
assemble 43 s; container up with an address in 5 s; then the first boot stops
in `10regen-sshkeys` because the published layer still carries the build time
wrappers `/usr/local/bin/systemctl` and `/usr/local/bin/service`, which call
each other in a loop outside a build chroot. `core` and `nodejs-nginx` do not
carry them, so it is `bt-layer` adding `LAYER_CHILD_OVERLAYS` to a child
build and not stripping the finished layer: buildtasks issue #6. The gate
found a real defect on its first run, which is what it is for; until the
layer is rebuilt, `appliance / build-and-boot` is not a required status on
keel-nodebb.

### Without sudo (2026-10-01)

Every command the runner could run through sudo was root-equivalent:
`apt-get` installs any `.deb`, `lxc-start` takes a config that mounts any
host path, `lxc-attach` enters whatever it is pointed at. So any job on
`keel-lxc-1` could become root on the VM that serves keellinux.org, the
archive, the mirror and the releases. The runner now has no sudo at all and
boots unprivileged containers. Commands as root on the VM.

What changed on the host, file by file (backups of every file before the
change in `/root/keel-runner-hardening-2026-10-01/`, with `dpkg -l` and the
linger state as they were):

| Path | Change |
| --- | --- |
| `/etc/sudoers.d/runner` | removed; `sudo -l -U runner` answers "not allowed to run sudo" |
| `/usr/local/sbin/keel-ci-boot-test`, `keel-ci-cleanup` | removed |
| `/usr/local/sbin/keel-provision` | the users and appliance gate sections no longer write the sudoers file and the helpers; they remove them and write what follows. `docs/infra/keel-provision.pending` carries the same change |
| `/etc/subuid`, `/etc/subgid` | unchanged: `runner:165536:65536` was already there, given by `useradd` |
| `/etc/lxc/lxc-usernet` | new, `runner veth lxcbr0 10` |
| `/home/runner/.config/lxc/default.conf` | new: veth on `lxcbr0`, `lxc.idmap` u and g `0 165536 65536`, `lxc.apparmor.profile = lxc-container-default-with-nesting` |
| `/var/lib/systemd/linger/runner` | `loginctl enable-linger runner`, so `user@1001.service` runs without a login and its cgroup is delegated to `runner` |
| `actions-runner.service` | unchanged, never restarted |

Installed: `uidmap` (and its library `libsubid5`), nothing else.
`dbus-user-session` is not needed: LXC's own attempt to create a scope over
D-Bus fails harmlessly, and the scope comes from `systemd-run --user`,
which talks to the user manager over its private socket. None of the build
packages (`build-essential devscripts equivs fakeroot dpkg-dev lintian
git-buildpackage pristine-tar autopkgtest`) is on the host; package builds
belong in unprivileged containers.

Three things an unprivileged container needs here, each found by failing:

- The AppArmor profile. `/etc/lxc/default.conf` says `generated`, which
  needs `mac_admin`; `lxc-container-default-cgns` loads but denies the
  `rbind` mounts systemd uses to sandbox its services, so networkd,
  resolved and udevd fail and the container has no DNS.
  `lxc-container-default-with-nesting`, preloaded by `apparmor.service`,
  allows exactly those. What still fails in the container is the usual set
  for an unprivileged one (`dev-mqueue`, `run-lock`, `sys-kernel-config`,
  `sys-kernel-debug` and `tmp` mounts), so it reports `degraded`.
- A cgroup it may write. The runner's jobs live in
  `system.slice/actions-runner.service`, owned by root. `lxc-start` runs in
  `systemd-run --user --scope -p Delegate=yes`, and `lxc-attach` in
  `systemd-run --user --scope`, because attaching moves the process into
  the container's cgroup and that needs write access to a common ancestor.
  `XDG_RUNTIME_DIR=/run/user/1001` is all the job needs to reach the user
  manager.
- Device nodes. A user namespace may not `mknod`, so the extract of a layer
  fails on the nine nodes under `/dev`. LXC mounts its own `/dev` over the
  rootfs, so they are never seen.

The appliance boot test. Each of the nine appliance repositories carries its
own `tests/boot-test.sh`, and every one insists on root. Rather than change
nine repositories, `test-appliance.yml` runs the test through
`bin/unprivileged-lxc` of `keel-linux/.github` (`profile/WORKFLOWS.md`
there, "Without root on the runner"): the test is root in a user namespace
mapped onto `165536`-`231071` plus the runner's own uid at 65536, so the
assembled rootfs has the owners the container sees; its `lxc-*` commands
are forwarded to a broker outside the namespace that adds the idmap and the
profile to `lxc-start`; and `tar` forgives only the device node refusal.

Proof, in this order:

- A Debian trixie container made with `lxc-create -t download -- -d debian
  -r trixie -a amd64` as `runner` booted systemd (`degraded`, for the mounts
  above), got `fc42:5009:ba4b:5ab0:308a:4aff:febd:97ed/64` by SLAAC, with
  DNS from the bridge, and ran `apt-get install hello`. The container ran
  as uid 165536 under `lxc-container-default-with-nesting (enforce)`.
- keel-core's `tests/boot-test.sh` by hand as `runner`, against the published
  `core` layer: passed in 27 s, `keel diff` 6 same, 0 drift.
- keel-core run 36814690796, a temporary caller pointed at the
  `ci/unprivileged-boot-test` branch of `keel-linux/.github`, with sudo
  still in place and unused: `appliance / boot-published-layer` green in
  44 s.
- The sudoers file and the helpers removed, then keel-core run 36814955977,
  same caller: green in 44 s, address in 6 s, first boot 5 s later, 0
  monitors left, scratch tree gone.

GitHub settings changed the same day: the fork pull request policy (section
5). Runner group 1 already has `visibility: all`, which for an organization
runner group means every repository of the organization and nothing else;
the API also offers `private` (private repositories only, which would shut
out the 40 public ones), `selected` with an explicit list of repositories,
and `restricted_to_workflows` with a list of workflow refs. None of those was
applied: a hand-kept list breaks the gate of every new repository.

What could not be done unprivileged: nothing the appliance gate needs.
`build-deb.yml` still calls `sudo apt-get` for build dependencies; nothing
calls it, and it has to move into an unprivileged container before anything
does.

Rollback, as root on the VM, if the unprivileged path has to be abandoned:

    D=/root/keel-runner-hardening-2026-10-01
    install -m 0440 -o root -g root $D/etc/sudoers.d/runner /etc/sudoers.d/runner && visudo -c
    install -m 0755 -o root -g root $D/usr/local/sbin/keel-ci-boot-test $D/usr/local/sbin/keel-ci-cleanup /usr/local/sbin/
    install -m 0755 -o root -g root $D/usr/local/sbin/keel-provision /usr/local/sbin/keel-provision
    rm -f /etc/lxc/lxc-usernet /home/runner/.config/lxc/default.conf
    loginctl disable-linger runner
    apt-get purge uidmap libsubid5

and revert the `keel-linux/.github` pull request that introduced
`bin/unprivileged-lxc`, since the workflow before it calls the helpers
through sudo. The fork pull request policy is independent and should stay.

## 7. CD: what is published where today

| Artifact | Published to | Mechanism | State |
| --- | --- | --- | --- |
| Organization site | `https://keel-linux.github.io/` | GitHub Pages from `main` at `/` (build type legacy, `.nojekyll`, HTTPS enforced); a push to `main` is the deployment | live, `GET /repos/keel-linux/keel-linux.github.io/pages` reports `status: built`. If it is ever disabled: `POST /repos/keel-linux/keel-linux.github.io/pages` with `{"source": {"branch": "main", "path": "/"}}` |
| Debian packages | workflow artifacts only (`build-deb.yml`, artifact `deb`, 30 days) | `dpkg-buildpackage -us -uc -b` on the LXC runner | inactive until the runner exists; nothing is signed |
| APT repository | `https://archive.keellinux.org/` (README only) | `bin/publish` in repos/apt, target to be switched from Pages to this host | blocked on the signing key (decision 0005) |
| Appliance layers and manifests | `https://mirror.keellinux.org/layers/` (staging, unsigned, header `X-Keel-Distribution`) | staged on the build host and published by `bin/keel-publish-mirror` (docs/releases-host.md section 6, publishing a layer) | `core`, `lamp`, `nodejs-nginx` and `nodebb` served; `nodebb` published 2026-09-26 so the appliance gate had something to boot; signed manifests blocked on the key |

The APT repository, the keyring package and layer publication follow the
decision 0005 outcome; when it lands, the publication step is added to
`build-deb.yml` (upload of the signed `.deb` and `Release` to the chosen
host over IPv6, `archive.keellinux.org` at `[2804:710:d0:5::13]`), not to the
callers.
