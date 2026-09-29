# 0018: The network on a running machine

Date: 2026-09-29
Status: **decided 2026-09-29**. Design before code, as Keel-Linux/keel#35
asks for the one field whose converge can cut off the operator who runs it.
The maintainer settled the open points the same day; they are recorded under
"Decided" at the end, and the text below already reflects them.

## What is missing

`keel diff` compares `network.*`, and nothing converges it after the first
boot: the `01ipconfig` hook writes `/etc/network/interfaces` once, from the
`IP_*` and `IP6_*` variables the conf phase renders. A declared address that
differs from the machine is reported and stays wrong. The other fields of
keel#35 (alerts, hostname, tls.acme) are now converged by `apply --system`;
this is the last one.

## Two owners, split by interface

The spec already separates them with `network.managed_by`, and the converge
must too, because they have different owners. The split is by interface, not
by kind of machine: a standalone appliance and one taking part in a
replicated set (decision 0020) behave the same way, because what owns the
uplink does not change with the role.

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

**An overlay the appliance creates itself**, the WireGuard interface of
decision 0020, belongs to the appliance on either kind of machine: its
configuration lives in `/etc/wireguard/`, a file the host of a container
does not write or regenerate. It is converged from inside even when the
uplink is `managed_by: host`, with the same confirmation window below, whose
saved copy then covers `/etc/wireguard/` instead of the interfaces file,
because a management session can run over it. One thing it does need from
the host: an unprivileged container cannot load kernel modules, so the host
must have the `wireguard` module loaded, and inspect reports its absence
rather than failing half way. Its fields are 0020's to define; this note
only fixes who owns it.

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
2. Before touching anything, the run saves the current file under
   `/var/lib/keel/network/` with a pending marker, and arms a revert: a
   transient systemd timer (`systemd-run --on-active=`) that restores the
   saved file and brings the interface up on it. The timer is armed first,
   so a run that dies half way still reverts. A transient timer does not
   survive a reboot, so a unit shipped in the image also runs at boot,
   before networking (`DefaultDependencies=no`,
   `RequiresMountsFor=/var/lib/keel`, `Wants=` and `Before=`
   `network-pre.target`, and `Before=networking.service`; the overlay's
   restore relies on `network-pre.target`, which every `wg-quick@`
   instance follows through its `After=network-online.target`, since a
   template name cannot be ordered against): if the pending marker is
   there and no confirmation was recorded, it restores the saved file, or
   `/etc/wireguard/` for the overlay. A machine that reboots inside the
   window comes back on the old network. Confirming and reverting both
   remove the marker, and they exclude each other: both take the same lock
   on the marker, a confirmation refuses once a revert has started, and a
   revert does nothing once a confirmation is recorded. Stopping the timer
   alone would not stop a revert already running, and the operator would be
   told "confirmed" on the old network.
3. The interface is taken down on the outgoing configuration (`ifdown`, which
   also stops a DHCP client it started and withdraws its resolvconf
   entries), its addresses are flushed, since IPv4 addresses survive a link
   going down, the new file is written, and the interface comes up on it
   (`ifup`; the image ships ifupdown-ng, which has no `ifreload`). The revert
   is the same sequence in the other direction, so neither leaves an address
   or a DHCP client of the other behind. The overlay has no `ifdown`: its
   sequence is `wg-quick down` on the outgoing `/etc/wireguard/` file, then
   `wg-quick up` on the new one, both directions alike. Only when the
   interface is up again does the marker record the time of the change, on
   a clock that does not jump (the boot ID and the time since boot), which
   is what a session's age is compared with.
4. The run then waits for a confirmation that arrives **over the new
   configuration**: `keel network confirm`, its own command, run in a new
   session. That command cancels the timer and records the confirmation.
   It refuses unless it arrives over the new configuration. Over SSH, the
   session must have started after the change (its `sshd-session` process,
   the per-connection process of OpenSSH 10 in Debian 13, is younger than
   the time in the marker), and its local address must be one the
   change added or kept. The session is found from the process tree or
   `loginctl`, not from the environment, which `sudo` resets. On a console,
   recognised by its terminal (`tty1`, `ttyS0`, `hvc0`, `console`), it is
   accepted, since a person there has seen the machine. So a shell that
   survived the change, in tmux or under `sudo`, cannot confirm by accident.
   One limit is stated rather than hidden: a new session from a client on
   the same link does not use the gateway, so when the gateway changed,
   confirm checks that the route back to the client (`ip route get`) goes
   through the new gateway, and says so when it does not rather than
   claiming the gateway was tested. Being
   its own command, it can be run by a person from a new SSH session or by
   an agent that has just reached the machine again over the new addresses
   (the coordination of decision 0020); a flag on `apply` would serve only
   the first.
5. Without a confirmation within the window (default 120 seconds, a flag to
   change it), the timer restores the previous file, and the next `keel diff`
   shows the declared network as drift again, with the reason.

A first boot is not a day two and keeps its hook: `01ipconfig` runs before
anything is reachable, so there is no session to lose and nothing to confirm.

## What it does not do

- Converge a host managed network, for the reason above.
- Touch more than one uplink interface (the overlay of 0020 is its own
  interface, under its own file). `01ipconfig` configures one, and a spec
  declaring several already has "the last block wins" semantics (docs/spec.md
  in keel); the converge keeps them rather than inventing multi interface
  semantics here.
- Rename interfaces, create bridges or VLANs, or edit IPv4 when the spec has
  no `ipv4` block: IPv4 stays as the machine has it, IPv6 first.
- Change the network without arming the window: `--dry-run` shows the
  plan, and no run writes the file before the revert timer exists.

## How it is tested

The planner under `--root` like every other field. The revert on a real
machine: two LXC containers on the build host's bridge, one with
`managed_by: file`. On a shared bridge a wrong gateway does not cut two
neighbours apart, so the breaking change is a wrong address and prefix
outside the bridge's network: the test checks the machine is unreachable
from the other container, waits out the window, and checks it is reachable
again on the old address, with no address of the bad configuration left,
IPv4 included. A gateway-only change checks that a surviving session cannot
confirm and that an on-link confirm reports the gateway as untested. A
second run reboots the machine inside the window and checks the boot unit
reverted it. A correct change is confirmed from the other container over
the new address and stays; a confirmation from the old address is refused.
No Docker, native systemd, IPv6 first (brief section 10).

## Decided 2026-09-29

- **The window is 120 seconds** by default, with a flag to change it.
- **The confirmation is its own command, `keel network confirm`**, so that
  an agent reaching the machine again can confirm as well as a person.
- **A machine without a console does not refuse.** The revert is what makes
  the change safe without one; a VPS reached only over SSH is the case the
  design exists for.
- **Ownership is split by interface.** The uplink of a container stays the
  host's and is only compared; an overlay the appliance creates, the
  WireGuard interface of decision 0020, is converged from inside.
