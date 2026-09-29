# 0018: The network on a running machine

Date: 2026-09-29
Status: **proposed**. Design before code, as Keel-Linux/keel#35 asks for
the one field whose converge can cut off the operator who runs it.

## What is missing

`keel diff` compares `network.*`, and nothing converges it after the first
boot: the `01ipconfig` hook writes `/etc/network/interfaces` once, from the
`IP_*` and `IP6_*` variables the conf phase renders. A declared address that
differs from the machine is reported and stays wrong. The other fields of
keel#35 (alerts, hostname, tls.acme) are now converged by `apply --system`;
this is the last one.

## Two machines, not one

The spec already separates them with `network.managed_by`, and the converge
must too, because they have different owners.

**`managed_by: host`, the container.** The interfaces of an LXC system
container are configured by the host: Proxmox writes them into the container
config, and the container's own `/etc/network/interfaces` is at most a copy
the host regenerates. A converge from inside would edit a file the host
overwrites, or fight it. So `apply` does not converge a host managed network,
and never will from inside the container: it keeps comparing and warning, as
it does today, and the reason names the host as the owner. Changing a
container's addresses is the host's operation, which is the fleet tooling
brief section 2 puts outside this codebase and the maintainer has named as the
next project, the one that consumes Keel's spec.

**`managed_by: file`, a VM or an installed system.** Here the file is the
configuration, and `apply --system` converges it. The rest of this note is
about that case.

## The converge, and why it reverts by itself

Writing `/etc/network/interfaces` is the easy half. Bringing the interface up
on the new configuration is the half that can leave a machine unreachable:
a wrong gateway, a prefix length off by one, a nameserver that does not
answer, and the operator's SSH session, which is how `apply` was run, is gone
with no way back in except a console.

So the network is applied the way a remote change to a firewall is applied,
with a confirmation window:

1. The planner, pure as for every other field, compares the declared
   interfaces and nameservers with what inspect reads and plans the new
   `/etc/network/interfaces` stanza, rendered by the same code `01ipconfig`
   uses (`lib/ipconfig.sh`), so a first boot and a day two write the same
   file for the same spec.
2. Before touching anything, the run saves the current file and arms a
   revert: a transient systemd timer (`systemd-run --on-active=`) that
   restores the saved file and brings the interface up on it. The timer is
   armed first, so a run that dies half way still reverts.
3. The file is written and the interface is brought down and up
   (`ip link set down`, then `ifup`, as `01ipconfig` does; the image ships
   ifupdown-ng, which has no `ifreload`).
4. The run then waits for a confirmation that arrives **over the new
   configuration**: `keel spec apply --confirm-network`, run by the operator
   in a new session. That command cancels the timer. Nothing the old session
   does can confirm, because the old session is exactly what might be broken.
5. Without a confirmation within the window (proposed default 120 seconds,
   a flag to change it), the timer restores the previous file, and the next
   `keel diff` shows the declared network as drift again, with the reason.

A first boot is not a day two and keeps its hook: `01ipconfig` runs before
anything is reachable, so there is no session to lose and nothing to confirm.

## What it does not do

- Converge a host managed network, for the reason above.
- Touch more than one interface. `01ipconfig` configures one, and a spec
  declaring several already has "the last block wins" semantics (docs/spec.md
  in keel); the converge keeps them rather than inventing multi interface
  semantics here.
- Rename interfaces, create bridges or VLANs, or edit IPv4 when the spec has
  no `ipv4` block: IPv4 stays as the machine has it, IPv6 first.
- Run without a person able to confirm: `--dry-run` shows the plan;
  a run with no `--confirm-network` window armed refuses rather than
  changing the network unattended.

## How it is tested

The planner under `--root` like every other field. The revert on a real
machine: two LXC containers on the build host's bridge, one with
`managed_by: file`, where a test applies a wrong gateway, checks the
machine is unreachable from the other container, waits out the window, and
checks it is reachable again on the old address; and a correct change that
is confirmed from the other container over the new address and stays. No
Docker, native systemd, IPv6 first (brief section 10).

## Open for the maintainer

- The default window, 120 seconds.
- Whether the confirmation is `apply --confirm-network` or its own
  command (`keel network confirm`); the first keeps one entry point, the
  second is easier to type from a phone.
- Whether a VM without a console should refuse the converge unless
  `--i-have-a-console` is passed; the revert makes it safe without one,
  which is the point of the design, so the proposal is no.
