# Evidence: fork pull request jobs run only in a container

Date: 2026-10-16, 07:30 to 09:30 UTC.
Decision: 0056, amended 2026-10-16 by the maintainer. Rule:
docs/infra/keel-lxc-2.md, "Fork pull requests run in a container".
Changes: Keel-Linux/inithooks#49 (every job on `keel-container`), this
handbook pull request (the patch, the provisioning and the rule).

Machines:

- Runner VM: Keel-Linux-Runner, `root@2804:710:d0:5::bbba`.
- Forgejo: git.pop.coop, Forgejo 14.0.2.
- Throwaway accounts, deleted after the test: `keel-fork-probe` (not a
  member, opened the fork pull requests) and `keel-fork-approver`
  (write access to the two test repositories only, during each approval).
  The repositories `Keel-Linux/fork-gate-probe` and
  `Keel-Linux/container-options-probe` and both forks are deleted.
  inithooks#50 (the fork probe) is closed.

## Summary

| Item | Result | Numbers |
| --- | --- | --- |
| 1. Forgejo or forgejo-runner setting for the rule | None | Forgejo gives a job to any runner with the label. forgejo-runner 13.2.0 has no fork check. |
| 2. Trust gate unit test | PASS | `TestKeelTrustGate`: 13 cases. The other failures of `./internal/app/run/` are the same without the patch (no Docker or LXC on the workstation). |
| 3. Trusted run, push to the probe repository | PASS | run 1: `host`, `lxc` and `routed` on host instances, `container` on `keel-fj-16`. |
| 4. Fork run, `keel-host`, `keel-lxc` and a workflow changed to `keel-host` | PASS | run 2: 3 jobs refused by the trust gate before any step. |
| 5. Fork run, `keel-container` | PASS | run 2: the job ran in a container as uid 0 of the container, hostname a container id, no file of the host. |
| 6. Reach of a fork job | PASS | blocked: the sshd of the VM (IPv6 and IPv4), the LAN gateway, a LAN resolver on port 80, port 22 of git.pop.coop, `lxcbr0`, `host.containers.internal`. Open: git.pop.coop 443, deb.debian.org 443, pypi.org 443. |
| 7. Same-repository pull request | PASS | run 3: every job passed, the host jobs on host instances. |
| 8. Approval of each run | PASS | each fork run was `need_approval` until an approval "once". "Always trust" was not selected. |
| 9. inithooks#49, every job on `keel-container` | PASS | runs 33 and 34: security, tests, python, package green. Merged as 3b19630. |
| 10. Fork pull request on inithooks, inithooks#50 | PASS | runs 35 and 36: the 4 jobs green on `keel-fj-15` and `keel-fj-16`. |
| 11. Users `runner1` to `runner8` | Removed | No process but their idle user managers, no unit, no cron. |
| 12. `container:` and `services:` options of a job on `keel-container` | PASS | `-v /home:/h`, `--mount type=bind`, a service `-v /etc:/hostetc`: no mount in the job. `--network host`: the job stayed on its own network. Probes as in item 6. |
| 13. Reproducible build of the patched runner | PASS | a new clone of v13.2.0, the patch, the documented command: the same SHA256. |
| 14. Slice limits of the container instances | PASS | `memory.max` 2684354560 and `pids.max` 8192 for `user-1115.slice` and `user-1116.slice`. |

## 1. Why the rule is in the runner

A fork changes `.forgejo/workflows` in its pull request, so an `if:` or
a label in the workflow does not stop it. Forgejo 14.0.2
(`models/actions/task.go`, `CreateTaskForRunner`) gives a waiting job to
the first runner whose labels match `runs-on`. The scope of a runner is
a repository or an owner, and the run of a fork pull request is in the
base repository. forgejo-runner 13.2.0 has no check of the event. Thus
the trust gate is a patch of the runner, and it reads the event payload
that Forgejo sends with the task.

Before the change, inithooks#48 (a fork) ran its `keel` job with
`runs-on: keel-host` on `runner13` directly on the VM, after an approval.

## 2. The patch

`docs/infra/forgejo-runner-keel-trust-gate.patch` on v13.2.0. Build with
Go 1.26.8 (`CGO_ENABLED=0`, `-trimpath`, version `v13.2.0+keel1`):

    0e3a9b234d41a4e41797d79023348c949a0153f0bb4dc5d508305dab19f21870  forgejo-runner-13.2.0-keel1

Installed at 07:54 UTC with `mv` over `/usr/local/bin/forgejo-runner`.
The release binary is kept as `forgejo-runner-13.2.0.upstream`. A trusted
job of Keel-Linux/keel (run 2881) passed on the patched binary. The
check before the approvals: no `forgejo-runner one-job` process with
`(deleted)` in `readlink /proc/PID/exe`.

## 3 to 8. The probe repository

The probe workflow had 4 jobs: `host` (`keel-host`), `lxc` (`keel-lxc`),
`routed` (an expression on the event) and `container` (`keel-container`,
checkout and network probes). The fork changed `routed` to
`runs-on: keel-host`.

Fork run 2, log of the `host` job (the `lxc` and `routed` jobs are the
same):

    Runner ... (version:v13.2.0+keel1) received task 8257 of job host, triggered by event: pull_request
    refused by the Keel trust gate: event pull_request: the pull request is from
    keel-fork-probe/fork-gate-probe, not from Keel-Linux/fork-gate-probe; a pull
    request from a fork runs only on a container runner (runs-on: keel-container),
    see handbook docs/infra/keel-lxc-2.md

Fork run 2, `container` job:

    uid 0 root host 9047927d2ed5
    2804:710:d0:5::bbba port 22: blocked
    10.88.5.233 port 22: blocked
    10.88.5.254 port 80: blocked
    10.88.16.53 port 80: blocked
    2804:710:d0:5::20 port 22: blocked
    2804:710:d0:5::20 port 443: open
    10.0.3.1 port 53: blocked
    host.containers.internal port 22: blocked
    deb.debian.org port 443: open
    pypi.org port 443: open
    Job succeeded

The probe ran as uid 0 because the image had no `USER` then. The image
now runs the steps as `node`.

## 9 and 10. inithooks

First attempt, `runs-on` with an expression on the event: the fork jobs
of inithooks#50 (runs 21 and 22) got `keel-host`, and the trust gate
refused all 4. Forgejo evaluates `runs-on` without the github context
when it makes the run (`services/actions/notifier_helper.go`, no
`WithGitContext`). The gate held, and inithooks#49 changed to
`runs-on: keel-container` for every job.

Second attempt, `keel-container`: the inner jobs of the reusable
workflows keep `runs-on: keel-host`, so forgejo-runner used its built-in
image `node:22-bookworm` (runs 23 and 24, `keel-need-packages: command
not found`). The fix: that name is a second tag of `keel-ci` on the
container runners.

Third attempt: the shell tests failed as root (test 81, a directory with
mode 555) and without `iptables` (tests 96 to 103, the fence in a
network namespace). The fix: the image has `iproute2`, `iptables` and
`nftables`, and its steps run as `node`. A nested user namespace works
for `node` in rootless podman: `unshare -rn --mount`, then `iptables -t
nat -L` and `ip6tables -t nat -L`, exit 0.

Fourth attempt: inithooks#49 runs 33 and 34 green, and the fork
inithooks#50 runs 35 and 36 green, each job on `keel-fj-15` or
`keel-fj-16`.

## 11. runner1 to runner8

Before: 8 users in `loginctl list-users`, `LINGER yes`; 5 of them had a
user manager that ran for 8 days, and nothing else. No `actions-runner@`
unit enabled. Done, as root, for each user: `loginctl disable-linger`,
stop `user@UID`, `userdel -r`, remove the lines in `/etc/subuid`,
`/etc/subgid` and `/etc/lxc/lxc-usernet`, `user-UID.slice.d`,
`actions-runner@I.service.d` and `lxc-default.runnerI.conf`; then the
`actions-runner@.service` unit and its drop-in. After: `loginctl` lists
`runner9` to `runner14` (and `runner15`, `runner16`, the container
instances), no file of the removed users outside the removed homes.

## 12. Job container options

A trusted push to the throwaway repository `container-options-probe`
(the runner code is the same for a fork job). The job had
`container: { image: localhost/keel-ci:trixie, options: -v /home:/h
--mount type=bind,src=/run/user,dst=/s --privileged --network host }`
and a service with `options: -v /etc:/hostetc`. Run 2:

    [/home] is not a valid volume, will be ignored
    uid=1000(node) gid=1000(node) groups=1000(node)
    ls: cannot access '/h': No such file or directory
    ls: cannot access '/s': No such file or directory
    cat: /h/runner15/actions-runner/.runner: No such file or dir
    ls: cannot access '/hostetc': No such file or directory
    eth0@if5         UP             10.89.0.3/24 fd2d:23ee:5bff:62db::3/64
    127.0.0.1 port 22: blocked
    2804:710:d0:5::bbba port 22: blocked
    10.88.5.254 port 80: blocked
    2804:710:d0:5::20 port 443: open
    pypi.org port 443: open
