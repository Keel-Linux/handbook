# keel-lxc-2, the second CI runner host

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
