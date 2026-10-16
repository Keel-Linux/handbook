# keel-lxc-2, the second CI runner host

**Status 2026-10-16:** the CI of Keel-Linux runs on the Forgejo
instances, see "Forgejo runner instances" below. A job of a pull request
from a fork runs only in a container, see "Fork pull requests run in a
container". The GitHub runner instances `keel-lxc-2-1` to `keel-lxc-2-8`
(`actions-runner@1` to `@8`) were stopped, disabled and removed from the
GitHub organization on 2026-10-15 (decision 0056). On 2026-10-16 their
users `runner1` to `runner8` were removed: linger off, the users and
their homes, their subordinate ids, `lxc-usernet` lines, slice drop-ins,
LXC templates and the `actions-runner@` units. No service used them. The
text about the GitHub instances is a record. Do not run
`keel-lxc-2-provision.pending` with its default `KEEL_RUNNERS=8` on this
VM: it makes the GitHub users again. Use `KEEL_RUNNERS=0`.

Provisioned on 2026-10-07. The second runner host of the Keel-Linux
organization, equivalent to keel-lxc-1 (docs/ci-cd.md section 6,
docs/releases-host.md section 7), so a `keel-lxc` job runs on either.
Unlike keel-lxc-1 it has a VM to itself: nothing else is served from it.
It runs eight instances, `keel-lxc-2-1` to `keel-lxc-2-8`, each as its own
user in its own limited slice (approved by the maintainer on 2026-10-07;
more may follow after measurement). The first provisioning ran a single
instance, `keel-lxc-2`, as the user `runner`; it is deregistered and the
script removes it.

## The VM

- Hostname `Keel-Linux-Runner`, Debian 13.7, KVM, 16 vCPU, 23 GB RAM,
  100 GB disk, kernel `6.12.111+deb13-cloud-amd64`.
- IPv6 `2804:710:d0:5::bbba` (static) on the public segment, IPv4
  `10.88.5.233` on the LAN behind NAT (the GitHub API needs IPv4).
- Access: root over SSH with a key only. The user `popsolutions` (sudo)
  came with the VM and is not used or changed by the runner.

## What is installed

All of it is written by `docs/infra/keel-lxc-2-provision.pending`, run as
root, idempotent. `KEEL_RUNNERS` sets the number of instances (default 8);
instance I is user `runnerI`, uid 1100+I, service `actions-runner@I`:

| Part | What |
| --- | --- |
| Packages | `lxc lxc-templates lxcfs uidmap dnsmasq-base nftables apparmor apparmor-utils iproute2 kcov bats shellcheck python3-yaml zstd git curl wget gnupg ca-certificates libicu76 file rsync unattended-upgrades`; lxc 1:6.0.4-4+deb13u4, apparmor 4.1.0 |
| Updates | unattended-upgrades on (`APT::Periodic::Unattended-Upgrade "1"`), as the image shipped it |
| `lxcbr0` | `/etc/default/lxc-net`: IPv4 NAT on 10.0.3.0/24 and the same ULA prefix as keel-lxc-1, `fc42:5009:ba4b:5ab0::/64`, `ra-only`, masqueraded; DHCPv4 leases of 10 minutes (`LXC_DHCP_RANGE`), not dnsmasq's hour, so containers long gone do not hold the 253 addresses |
| lxcfs | enabled and started (it was enabled but not running after the first boot); a host service in `system.slice`, outside the runners' limits |
| Modules | `/etc/modules-load.d/keel-ci.conf`: `sch_netem` (tc netem, decision 0050) and `wireguard` (mesh tests); an unprivileged container cannot load them itself |
| Firewall | `/etc/nftables.conf`: keel-provision's rules without 80 and 443. Inbound SSH only; from `lxcbr0` only DNS and DHCP reach the host; forwarding from `lxcbr0` to the internet only, not private IPv4 (the LAN included), ULA, link local or `2804:710:d0:5::/64` |
| Users `runner1`-`runner8` | uids 1101-1108, no sudo, lingering user manager; subordinate ids fixed at `165536+(I-1)*65536`, 65536 each (`runner1` 165536-231071 ... `runner8` 624288-689823), set by the script, not by useradd, and checked for overlap with every range in `/etc/subuid` and `/etc/subgid`; `/etc/lxc/lxc-usernet` one line `runnerI veth lxcbr0 10` each |
| LXC defaults | `/home/runnerI/.config/lxc/default.conf`, from `/usr/local/share/keel-runner/lxc-default.runnerI.conf`: veth on `lxcbr0`, that user's idmap, profile `lxc-container-default-with-nesting` |
| AppArmor | `/etc/apparmor.d/lxc/lxc-default-with-nesting` with the two systemd 257 credentials mount rules (`mount fstype=ramfs,` and the read-only remount with `nosymfollow`, handbook#41), so journald runs in the CI containers |
| Scratch | `/var/tmp/keel-ci`, `root:root` mode 1777 as `/tmp`: every instance creates its trees there (the workflows hard code the path) and the sticky bit keeps them each user's own. Not a group directory: `bin/unprivileged-lxc cleanup` removes a tree from inside the job's user namespace, where only the user's own uid and gid are mapped, so a group write bit is refused there (mode 1771 `root:keel-ci` failed every job's cleanup on 2026-10-07) |
| Job hygiene | `/usr/local/libexec/keel-runner/job-reset.sh` and `job-reset-completed.sh`, `/usr/local/sbin/keel-runner-start-reset runnerI`, `/usr/local/share/keel-runner/`, drop-in `actions-runner@.service.d/keel-hardening.conf` |
| Runner | actions/runner 2.338.0 in `/home/runnerI/actions-runner`, template `actions-runner@.service` (`User=runner%i`, `run.sh`, `Restart=always`, `KillMode=process`, `OOMPolicy=continue`), the eight instances enabled |
| Limits | drop-in `actions-runner@I.service.d/keel-slice.conf` puts instance I in `user-(1100+I).slice`, the slice of its user manager; `user-UID.slice.d/90-keel-limits.conf` gives that slice `MemoryMax=2560M`, `MemorySwapMax=0`, `CPUWeight=100`, `TasksMax=8192` |

The appliance gate and job hygiene sections derive from
`keel-provision.pending`, so both hosts have the same profile, hooks and
resets, with one change: the hooks are per user. `job-reset.sh` takes its
user, home and subordinate range from whoever runs it, and
`keel-runner-start-reset` from its argument, instead of the fixed name
`runner`; each removes only its own user's home, user units and container
scopes, its own service's processes, and the files its uid or its
subordinate ids own in `/var/tmp/keel-ci`, `/tmp`, `/var/tmp` and
`/dev/shm`. With one instance named `runner` they do what keel-lxc-1's do,
so keel-lxc-1 can take them unchanged; until it does, a change to the
common parts is made in both files. Left out, because
they belong to the public services VM: the `site` user, `/srv` trees, the
site checkout, nginx, dehydrated, ports 80 and 443. Also not needed: the
hosts entry keel-lxc-1 relies on to reach archive.keellinux.org and the
mirror, which this VM reaches through public DNS.

The job hooks are set the way keel-lxc-1 sets them: `Environment=` lines in
the `keel-hardening.conf` drop-in, not the runner's `.env`, which the
resets overwrite with `/usr/local/share/keel-runner/runner.env`
(`LANG=C.UTF-8`) before every job.

## Why one user per instance, and what the instances share

The job hooks wipe their user's home cache, user units, containers and
work tree around every job, so two instances under one uid would wipe each
other's job: every instance has its own user, subordinate range, veth
quota, LXC defaults, work tree, service and slice. What they share:

- `lxcbr0` and its dnsmasq. Eight jobs of up to five containers each (the
  `BTN_MAX_NODES` ceiling of `lib/boot-test-nodes.sh` in
  Keel-Linux/.github) are 40 addresses of the 253, and the 10 minute leases
  free the addresses of containers that are gone. The IPv6 addresses come
  from SLAAC on the /64.
- Container names, which do not collide: LXC names a container by its
  lxcpath and name, and every job has its own lxcpath under
  `/var/tmp/keel-ci`. `lxc-trixie.yml` names it
  `keel-trixie-RUN_ID-ATTEMPT-RANDOM` (the random suffix separates two calls
  in one run), `test-appliance.yml` `keel-APPLIANCE-ci-RUN_ID-ATTEMPT`, its
  nodes `NAME-1`, `NAME-2`... Every lxc-trixie container is called `trixie`
  in its own path, so the hostnames in dnsmasq repeat; nothing resolves a
  container by that name.
- The CPU, by equal weights, and the memory, at most 2.5 GB per instance,
  about 3 GB of the 23 left to the host.

## Limits

`bin/unprivileged-lxc` of Keel-Linux/.github starts a container with
`systemd-run --user --scope -p Delegate=yes`, so the container runs in a
scope of its user's manager, `user@UID.service`, in `user-UID.slice`, not
in the runner's service. The job's own processes (the checkout, keel
assemble in the user namespace, tar) run in the service. Putting the service
in `user-UID.slice` as well puts both under the slice's limits:

    user.slice/user-1101.slice              MemoryMax=2560M MemorySwapMax=0 CPUWeight=100 TasksMax=8192
    ├─actions-runner@1.service              listener, worker, the job's steps
    └─user@1101.service/app.slice/run-*.scope
      └─lxc.payload.trixie                  the job's containers

`memory.current` counts the page cache too, which the kernel reclaims at the
limit before it kills anything. A job that still runs its slice out of
memory loses a process to the OOM killer and fails; `OOMPolicy=continue`
keeps the instance. lxcfs, dnsmasq, sshd and the rest of the host stay in
`system.slice`.

## Registration

Organization level, names `keel-lxc-2-1` to `keel-lxc-2-8`, label `keel-lxc` (GitHub adds
`self-hosted`, `Linux`, `X64`), runner group Default, which is restricted to
`lxc-trixie.yml` and `test-appliance.yml` of `Keel-Linux/.github` at
`refs/heads/main`. The tarball was checked against the SHA-256 in the
release notes, which matched the asset digest of the API:

    af4b794c1bc41d73d40535e3fe092a39f9679cd8d965954c2aca25a05ca41d32  actions-runner-linux-x64-2.338.0.tar.gz

## Verified on 2026-10-07

- `gh api orgs/Keel-Linux/actions/runners`: `keel-lxc-2 online
  self-hosted,Linux,X64,keel-lxc`, listed in runner group 1 (the single
  instance; see "Eight instances" below for today's state).
- `sudo -l -U runner`: "not allowed to run sudo".
- Real jobs, green on keel-lxc-2: `install / trixie` of Keel-Linux/common
  run 37649420763 (the first job it took, a minute after registration), and
  `etcd / trixie` of Keel-Linux/keel pull request #81, run 37644733310,
  job 112904805995: 7 passed in 327 s on netem legs of 125 ms, 12.5 ms
  jitter and 2% loss, both job hooks in the log.
- By hand as `runner`: a trixie container from the download template
  booted `degraded` (the usual unprivileged mounts) with `systemd-journald`
  active, `/dev/log` present and a `logger` line in the journal; it got
  `fc42:5009:ba4b:5ab0:.../64` by SLAAC; `tc qdisc add ... netem delay
  100ms loss 2%` worked inside it; github.com:443 reachable, the LAN and the
  host's sshd not.

## Eight instances, verified on 2026-10-07

- `gh api orgs/Keel-Linux/actions/runners`: `keel-lxc-2-1` to
  `keel-lxc-2-8` online with `self-hosted,Linux,X64,keel-lxc`, all in
  runner group Default; `keel-lxc-2` deleted, no runner left offline.
- Containers of a job run in `user.slice/user-UID.slice/user@UID.service/
  app.slice/run-*.scope/lxc.payload.trixie`, under the slice's limits, with
  the runner service beside them in the same slice.
- The hooks touch only their own user's things: `job-reset.sh` run as
  runner1 removed runner1's tree in `/var/tmp/keel-ci` and left the five of
  the other instances, and a file of runner3 in `/tmp` survived both
  runner1's hook and `keel-runner-start-reset runner1`.
- Seven jobs at once on seven instances, 19:58 to 20:06 UTC, all green:
  three `etcd / trixie` and one `vip / trixie` of Keel-Linux/keel (netem
  legs of 125 ms, 12.5 ms jitter and 2% loss, a measured RTT of 267 ms;
  7 passed in 365 s and 10 passed in 223 s), next to three `build / trixie`
  of turnkey-netinfo and tkl-dhcpcd-ifupdown-glue. Jobs 112988325980,
  112988326501 (run 37674781181), 112988309593 (run 37667358811),
  112988295632 (run 37665525005).
- Peak `memory.peak` per instance slice 1210 to 1636 MiB (page cache
  included) against the 2560 MiB limit, no `oom_kill`; at most 9.6 GB in
  the eight slices together and 3.8 GB used on the host (`free`).
- The first round of the same jobs failed only in their cleanup, with
  every test green: the scratch root was `root:keel-ci` 1771, and the
  removal from inside the user namespace was refused (see the Scratch row
  above). With mode 1777 they passed.

## Rebuild

1. A fresh Debian 13 VM with root SSH by key. Copy the script and run it
   (`KEEL_RUNNERS=N` in front of the script for another number of
   instances):

        scp docs/infra/keel-lxc-2-provision.pending root@HOST:/usr/local/sbin/keel-lxc-2-provision
        ssh root@HOST 'chmod 0755 /usr/local/sbin/keel-lxc-2-provision && /usr/local/sbin/keel-lxc-2-provision'

2. The runner, one tarball for every instance, checked against the
   release notes and the asset digest of the API:

        gh api repos/actions/runner/releases/latest --jq .tag_name
        gh api repos/actions/runner/releases/tags/v$V \
          --jq ".assets[]|select(.name==\"actions-runner-linux-x64-$V.tar.gz\")|.digest"
        # on the VM, as root, with V and SHA from the release notes:
        install -d -m 0755 /var/cache/keel-runner
        curl -fsSL -o /var/cache/keel-runner/actions-runner-linux-x64-$V.tar.gz \
          https://github.com/actions/runner/releases/download/v$V/actions-runner-linux-x64-$V.tar.gz
        echo "$SHA  /var/cache/keel-runner/actions-runner-linux-x64-$V.tar.gz" | sha256sum -c -

3. Registration of the eight, with one token (one hour, `admin:org`, it
   registers any number of runners) piped from a workstation and never
   stored or printed. `--replace` takes over a registration of the same
   name left by a previous VM:

        gh api -X POST orgs/Keel-Linux/actions/runners/registration-token --jq .token \
          | ssh root@HOST 'IFS= read -r T; V=2.338.0; for i in 1 2 3 4 5 6 7 8; do \
              u=runner$i; d=/home/$u/actions-runner; sudo -u $u mkdir -p $d; \
              sudo -u $u tar -C $d -xzf /var/cache/keel-runner/actions-runner-linux-x64-$V.tar.gz; \
              (cd $d && sudo -u $u ./config.sh --unattended --url https://github.com/Keel-Linux \
                --token "$T" --name keel-lxc-2-$i --labels keel-lxc --runnergroup Default \
                --work _work --replace >/dev/null) && echo "$u registered"; done'

4. Run the script again (it enables each instance once its `.runner`
   exists), then `systemctl start actions-runner@{1..8}` and check
   `gh api orgs/Keel-Linux/actions/runners`.

To take an instance out, stop it only while it is idle and kill the whole
unit: `KillMode=process` makes a plain `systemctl stop` end `run.sh` only,
and the listener left behind takes the next job (it did on 2026-10-07):

    systemctl kill -s KILL actions-runner@I; systemctl disable --now actions-runner@I
    gh api -X DELETE orgs/Keel-Linux/actions/runners/ID

## Forgejo runner instances (decision 0056)

Since 2026-10-14 the VM also runs Forgejo runners for the organization
`Keel-Linux` on git.pop.coop, beside the GitHub instances. They are
written by `docs/infra/keel-fj-provision.pending`, run as root,
idempotent. Do not run it while a job runs: its `systemctl daemon-reload`
stopped two jobs on 2026-10-14.

| Part | What |
| --- | --- |
| Instances | `FJ_RUNNERS` (6 by default) users `runner9` to `runner14`, uid 1109 to 1114, the same subordinate range scheme (`runner9` 689824-755359 ...), LXC defaults, `lxc-usernet` quota and slice limits as `runner1` to `runner8` |
| Runner | `forgejo-runner` 13.2.0 with the trust gate in `/usr/local/bin`, checked against its SHA256; the release binary stays as `forgejo-runner-13.2.0.upstream`; state and `config.yml` in `/home/runnerI/actions-runner`, work trees in its `_work` |
| Service | `forgejo-runner@I`: `forgejo-runner one-job --wait`, one job for each start, `Restart=always`. Before each job, `keel-runner-start-reset` (as root) and `job-reset.sh`; after it, `job-reset-completed.sh`: the same resets as the GitHub job hooks |
| Labels | `keel-host`, `keel-lxc`, `self-hosted`, all of the host executor, registered with the registration token of the organization (not of the server), so jobs of other organizations do not come here |
| Trust gate | `forgejo-runner` is the 13.2.0 release with the patch `docs/infra/forgejo-runner-keel-trust-gate.patch` (`v13.2.0+keel1`): it refuses a job of a fork pull request, see "Fork pull requests run in a container" |
| Node | `/opt/keel-node24`, node 24 (24.21.0) first in `PATH`, for the JavaScript actions. It came from the GitHub runner; a rebuild takes the release tarball of nodejs.org |
| Packages | what the GitHub jobs installed on ubuntu-latest with sudo (jq, python3-venv, cmake and the kcov build libraries, reprepro, debhelper, devscripts, lintian, redis-server masked, ...); the Debian kcov is 43, the pinned version |
| `keel-need-packages` | `/usr/local/bin/keel-need-packages PKG...`: the Forgejo jobs run it in place of `sudo apt-get install`; it fails and names the packages the host does not have |

Registration, with a token of
`GET /api/v1/orgs/Keel-Linux/actions/runners/registration-token` (a site
or organization administrator), for instance I:

    cd /home/runnerI/actions-runner
    runuser -u runnerI -- forgejo-runner register --no-interactive \
      --instance https://git.pop.coop --token TOKEN --name keel-fj-I \
      --labels keel-lxc:host,self-hosted:host,keel-host:host -c config.yml
    systemctl enable --now forgejo-runner@I

Instances: `runner9` to `runner14` (6 instances, `FJ_RUNNERS=6`) run
since 2026-10-15, after the GitHub instances were retired. Their limits
are 15 GB of the 23 GB VM.

A job that writes no log line for 10 minutes fails. git.pop.coop keeps
Forgejo's default `ZOMBIE_TASK_TIMEOUT` of 10 minutes: the server then
archives the log and marks the job failed, while the commands still run
on the runner. The runner's journal says `ReportLog error: already_exists:
log file has been archived` (Keel-Linux/keel#177: "mesh / trixie" of
keel runs 94 and 102). The reusable `lxc-trixie.yml` of
Keel-Linux/.github prints a line each minute while its commands run
(.github#25). A job of another workflow that can be silent for 10
minutes must do the same.

## Fork pull requests run in a container

Decided by the maintainer on 2026-10-16: a job of a pull request from a
fork never runs on the VM itself. It runs only in a new container, which
the runner removes after the job. Forgejo still holds every such run
until a maintainer approves it (decision 0056, "Known gaps"). Approve
each run after you read its workflow change, and do not select "always
trust".

### Why a workflow rule is not enough

A fork can change `.forgejo/workflows` in its pull request, so the fork
selects the `runs-on` label of its jobs. Forgejo 14.0.2 gives a job to
any runner that has the label, and a runner of the organization takes
jobs of every repository of the organization. Forgejo has no setting
that keeps a fork job off a label, and forgejo-runner 13.2.0 has no
setting that refuses a fork job. Thus the rule is in the runner, and it
reads the data that Forgejo sends with the job, not the workflow file.

### The trust gate

`docs/infra/forgejo-runner-keel-trust-gate.patch` adds
`internal/app/run/trust.go` to forgejo-runner 13.2.0, with its tests. The
runner calls it when it receives a job, before it parses the workflow or
runs a step:

- A job is untrusted when its event is `pull_request...` and the pull
  request does not come from a branch of the same repository. The test
  uses the event payload: `pull_request.flow` must be 0 (not AGit) and
  `pull_request.head.repo.full_name` must be the repository of the run.
  A payload that does not have these fields is untrusted.
- A runner refuses an untrusted job unless every label of the runner
  uses the `docker` backend. The job fails, and its log says why and
  points to this section.
- The rule is compiled in. No file that the runner user can write turns
  it off.

The six host instances (`keel-fj-9` to `keel-fj-14`) have only host
labels, so they refuse every fork job, on `keel-host`, `keel-lxc` and
`self-hosted`. `keel-lxc` is a host label too: the steps of a `keel-lxc`
job run on the VM, and only the containers that the job starts are
containers.

Build, on a workstation with Go 1.26.8 (the toolchain of `go.mod`):

    git clone --branch v13.2.0 https://code.forgejo.org/forgejo/runner.git
    cd runner
    git apply /path/to/handbook/docs/infra/forgejo-runner-keel-trust-gate.patch
    go test ./internal/app/run/ -run TestKeelTrustGate
    CGO_ENABLED=0 go build -trimpath -tags 'netgo osusergo' \
      -ldflags '-s -w -X "code.forgejo.org/forgejo/runner/v13/internal/pkg/ver.version=v13.2.0+keel1"' \
      -o forgejo-runner-13.2.0-keel1 .
    sha256sum forgejo-runner-13.2.0-keel1

The build of 2026-10-16 has the SHA256
`0e3a9b234d41a4e41797d79023348c949a0153f0bb4dc5d508305dab19f21870`. Copy
it to the VM, then replace the binary with `mv`, not `cp`: a waiting
instance keeps its open file, and each instance starts the new binary at
its next job (`one-job`). No `daemon-reload` is necessary. An instance
that waits for a long time keeps the old binary: restart the idle
instances, then check that no `forgejo-runner one-job` process shows
`(deleted)` in `readlink /proc/PID/exe`.

Caution: if you upgrade forgejo-runner, apply the patch to the new
release first. The release binary has no trust gate.

### The container instances

`docs/infra/keel-ctr-provision.pending`, run as root, idempotent, writes
the container instances:

| Part | What |
| --- | --- |
| Instances | `CTR_RUNNERS` (2 by default) users `runner15` and `runner16`, uid 1115 and 1116, subordinate ids `1083040`-`1148575` and `1148576`-`1214111`, the same slice limits as the host instances |
| Label | `keel-container:docker://localhost/keel-ci:trixie` only, names `keel-fj-15` and `keel-fj-16`, registered to the organization |
| Engine | rootless podman 5.4 of the instance user, through its `podman.socket`; cgroupfs, because the user managers have no D-Bus session bus. A container stays under the limits of the user slice |
| Image | `localhost/keel-ci:trixie`, built for each user from `/usr/local/share/keel-runner/keel-ci/Containerfile`: `node:24-trixie` with the packages of `keel-fj-provision`, `iproute2`, `iptables`, `nftables` and `keel-need-packages`; the steps run as the user `node`. Also tagged `node:22-bookworm`, see "The workflows" |
| Runner | `config.yml`: cache off, no volume, no Docker socket in the job, not privileged, IPv6 on |
| Service | `forgejo-runner-ctr@I`: `one-job`, and before each job `keel-ctr-start-reset` (as root) removes every container, pod, volume, network and image of the user except `keel-ci`, and writes the home again from root's files |
| Firewall | the `output` chain sends the traffic of uids 1115-1116 and their subordinate ids to the chain `container_runners`: DNS, `git.pop.coop` on 443 and the internet; no service of the VM, no private IPv4 range, no ULA, no link local and no other host of `2804:710:d0:5::/64` |

The firewall rule is necessary because rootless podman sends the traffic
of a container from a host process, not through `lxcbr0`.

The image does not update itself. To refresh it, stop the two
instances, then remove the image and run the script again:

    systemctl stop forgejo-runner-ctr@15 forgejo-runner-ctr@16
    for u in runner15 runner16; do (cd /tmp && runuser -u $u -- env XDG_RUNTIME_DIR=/run/user/$(id -u $u) podman rmi -f localhost/keel-ci:trixie docker.io/library/node:22-bookworm); done
    /usr/local/sbin/keel-ctr-provision
    systemctl start forgejo-runner-ctr@15 forgejo-runner-ctr@16

Registration is the same as for the host instances, with
`--name keel-fj-I --labels keel-container:docker://localhost/keel-ci:trixie`,
then `systemctl enable --now forgejo-runner-ctr@I`.

### The workflows

A repository whose jobs do not need the LXC of the VM selects
`runs-on: keel-container` for every job, on push and on pull request.
Inithooks does so since inithooks#49. A fork job of such a repository
runs and can pass.

A repository that needs the LXC of the VM keeps `keel-host` or
`keel-lxc`. The runner refuses its fork jobs, so their checks are red,
and the pull request cannot merge on them (decision 0053). Read the
change, then push the branch of the fork to a branch of the repository:
that run is trusted and runs on the host.

Do not select the label with an expression on the event, such as
`runs-on: ${{ github.event.pull_request.head.repo.full_name == github.repository && 'keel-host' || 'keel-container' }}`.
Forgejo 14 evaluates `runs-on` without the github context when it makes
the run. On 2026-10-16 such an expression gave `keel-host` to the jobs of
a fork, and the trust gate refused them.

Forgejo runs a reusable workflow inline. The inner job keeps its own
`runs-on` (`keel-host` in Keel-Linux/.github), and the container runner
has no label of that name. Then forgejo-runner uses its built-in image
`node:22-bookworm`. On the container runners that name is a second tag
of `keel-ci`, so the inner job also runs in `keel-ci`. The log shows
`Start image=node:22-bookworm`. If an upgrade of forgejo-runner changes
the built-in image, change `DEFAULT_IMAGE` in `keel-ctr-provision`.

The steps run as the user `node` (uid 1000) of the image, not as root,
as they do as `runnerI` on the host. A nested user namespace works for
that user, so the tests that use a network namespace of their own
(`tests/netns-sandbox` of inithooks) run in the container.

### What a fork job can and cannot do

- It runs as `node` in a user namespace of `runner15` or `runner16`. On
  the VM that is one of the subordinate ids of the instance user, with
  no access to the runner state of the host instances.
- It reaches the internet, DNS and `git.pop.coop`, not the VM, its
  sshd, the LAN or the other hosts of the segment.
- It cannot run a workflow that needs the LXC of the VM
  (`lxc-trixie.yml`, `test-appliance.yml`). These run after the merge,
  or on a branch of the repository that a member pushes.
- A container escape gives the instance user. That user can read the
  registration of its instance and change the `keel-ci` image of its
  instance for later fork jobs. Fork jobs have no secrets, and the host
  instances are other users.
- `keel-ctr-start-reset` removes everything of a job except the image.
  It does not check the image layers.

The test of 2026-10-16 is `docs/evidence/2026-10-16-fork-jobs-in-container.md`.

## What a job can still do

The same as on keel-lxc-1 (docs/ci-cd.md section 6, "What a job can still
do"): a job runs as its instance's uid, the runner's own, so it can read the
registration in `.credentials` and modify that instance. It cannot reach
another instance's files: the homes are each user's own, and the scratch
trees are protected by the sticky bit. It cannot become root,
reach the LAN or the host's sshd. The difference is what is next to it:
this VM serves nothing and holds no other service, so what the runner's uid
reaches here is the runner alone. The ephemeral runner options there apply
to both runners.
