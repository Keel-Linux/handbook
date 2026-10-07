# keel-lxc-2, the second CI runner

Provisioned on 2026-10-07. A second self-hosted runner of the Keel-Linux
organization, equivalent to keel-lxc-1 (docs/ci-cd.md section 6,
docs/releases-host.md section 7), so a `keel-lxc` job runs on either.
Unlike keel-lxc-1 it has a VM to itself: nothing else is served from it.

## The VM

- Hostname `Keel-Linux-Runner`, Debian 13.7, KVM, 16 vCPU, 23 GB RAM,
  100 GB disk, kernel `6.12.111+deb13-cloud-amd64`.
- IPv6 `2804:710:d0:5::bbba` (static) on the public segment, IPv4
  `10.88.5.233` on the LAN behind NAT (the GitHub API needs IPv4).
- Access: root over SSH with a key only. The user `popsolutions` (sudo)
  came with the VM and is not used or changed by the runner.

## What is installed

All of it is written by `docs/infra/keel-lxc-2-provision.pending`, run as
root, idempotent (run twice on 2026-10-07, the second time on the live
runner):

| Part | What |
| --- | --- |
| Packages | `lxc lxc-templates lxcfs uidmap dnsmasq-base nftables apparmor apparmor-utils iproute2 kcov bats shellcheck python3-yaml zstd git curl wget gnupg ca-certificates libicu76 file rsync unattended-upgrades`; lxc 1:6.0.4-4+deb13u4, apparmor 4.1.0 |
| Updates | unattended-upgrades on (`APT::Periodic::Unattended-Upgrade "1"`), as the image shipped it |
| `lxcbr0` | `/etc/default/lxc-net`: IPv4 NAT on 10.0.3.0/24 and the same ULA prefix as keel-lxc-1, `fc42:5009:ba4b:5ab0::/64`, `ra-only`, masqueraded |
| Modules | `/etc/modules-load.d/keel-ci.conf`: `sch_netem` (tc netem, decision 0050) and `wireguard` (mesh tests); an unprivileged container cannot load them itself |
| Firewall | `/etc/nftables.conf`: keel-provision's rules without 80 and 443. Inbound SSH only; from `lxcbr0` only DNS and DHCP reach the host; forwarding from `lxcbr0` to the internet only, not private IPv4 (the LAN included), ULA, link local or `2804:710:d0:5::/64` |
| User `runner` | uid 1001, subordinate ids `165536`-`231071`, no sudo, lingering user manager; `/etc/lxc/lxc-usernet` `runner veth lxcbr0 10` |
| LXC defaults | `/home/runner/.config/lxc/default.conf`: veth on `lxcbr0`, the idmap, profile `lxc-container-default-with-nesting` |
| AppArmor | `/etc/apparmor.d/lxc/lxc-default-with-nesting` with the two systemd 257 credentials mount rules (`mount fstype=ramfs,` and the read-only remount with `nosymfollow`, handbook#41), so journald runs in the CI containers |
| Scratch | `/var/tmp/keel-ci`, owned by `runner` |
| Job hygiene | `/usr/local/libexec/keel-runner/job-reset.sh` and `job-reset-completed.sh`, `/usr/local/sbin/keel-runner-start-reset`, `/usr/local/share/keel-runner/`, drop-in `actions-runner.service.d/keel-hardening.conf` |
| Runner | actions/runner 2.338.0 in `/home/runner/actions-runner`, `actions-runner.service` (`User=runner`, `run.sh`, `Restart=always`, `KillMode=process`), enabled |

The users, appliance gate and job hygiene sections are copied verbatim from
`keel-provision.pending`, so both runners have the same profile, hooks and
resets; a change to them is made there and copied here. Left out, because
they belong to the public services VM: the `site` user, `/srv` trees, the
site checkout, nginx, dehydrated, ports 80 and 443. Also not needed: the
hosts entry keel-lxc-1 relies on to reach archive.keellinux.org and the
mirror, which this VM reaches through public DNS.

The job hooks are set the way keel-lxc-1 sets them: `Environment=` lines in
the `keel-hardening.conf` drop-in, not the runner's `.env`, which the
resets overwrite with `/usr/local/share/keel-runner/runner.env`
(`LANG=C.UTF-8`) before every job.

## Registration

Organization level, name `keel-lxc-2`, label `keel-lxc` (GitHub adds
`self-hosted`, `Linux`, `X64`), runner group Default, which is restricted to
`lxc-trixie.yml` and `test-appliance.yml` of `Keel-Linux/.github` at
`refs/heads/main`. The tarball was checked against the SHA-256 in the
release notes, which matched the asset digest of the API:

    af4b794c1bc41d73d40535e3fe092a39f9679cd8d965954c2aca25a05ca41d32  actions-runner-linux-x64-2.338.0.tar.gz

## Verified on 2026-10-07

- `gh api orgs/Keel-Linux/actions/runners`: `keel-lxc-2 online
  self-hosted,Linux,X64,keel-lxc`, listed in runner group 1.
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

## Rebuild

1. A fresh Debian 13 VM with root SSH by key. Copy the script and run it:

        scp docs/infra/keel-lxc-2-provision.pending root@HOST:/usr/local/sbin/keel-lxc-2-provision
        ssh root@HOST 'chmod 0755 /usr/local/sbin/keel-lxc-2-provision && /usr/local/sbin/keel-lxc-2-provision'

2. The runner, latest release, checked against its release notes:

        gh api repos/actions/runner/releases/latest --jq .tag_name
        # on the VM, as root, with V and SHA from the release notes:
        sudo -u runner curl -fsSL -o /home/runner/r.tar.gz \
          https://github.com/actions/runner/releases/download/v$V/actions-runner-linux-x64-$V.tar.gz
        echo "$SHA  /home/runner/r.tar.gz" | sha256sum -c -
        sudo -u runner mkdir -p /home/runner/actions-runner
        sudo -u runner tar -C /home/runner/actions-runner -xzf /home/runner/r.tar.gz
        rm /home/runner/r.tar.gz

3. Registration, with a token (one hour, `admin:org`) piped from a
   workstation and never stored. Remove the old `keel-lxc-2` first in the
   organization settings, or add `--replace`:

        gh api -X POST orgs/Keel-Linux/actions/runners/registration-token --jq .token \
          | ssh root@HOST 'IFS= read -r T; cd /home/runner/actions-runner && \
            sudo -u runner ./config.sh --unattended --url https://github.com/Keel-Linux \
            --token "$T" --name keel-lxc-2 --labels keel-lxc --runnergroup Default --work _work'

4. Run the script again (it enables the service once `.runner` exists),
   then `systemctl start actions-runner` and check
   `gh api orgs/Keel-Linux/actions/runners`.

## What a job can still do

The same as on keel-lxc-1 (docs/ci-cd.md section 6, "What a job can still
do"): a job runs as uid 1001, the runner's own uid, so it can read the
registration in `.credentials` and modify the runner. It cannot become root,
reach the LAN or the host's sshd. The difference is what is next to it:
this VM serves nothing and holds no other service, so what the runner's uid
reaches here is the runner alone. The ephemeral runner options there apply
to both runners.
