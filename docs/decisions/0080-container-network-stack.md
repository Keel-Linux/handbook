# 0080: The network stack of a Keel container stays on ifupdown until Proxmox writes systemd-networkd for Debian

Date: 2026-11-06
Status: **decided by the maintainer, 2026-11-06** ("only when Proxmox
supports it; until then we use our package").

## What was found

Proxmox bug 6644 (https://bugzilla.proxmox.com/show_bug.cgi?id=6644, open,
"dualstack dhcp broken for Debian Trixie+"): for a Debian container,
`pct` writes one `inet dhcp` and one `inet6 dhcp` stanza in
`/etc/network/interfaces`. The ifupdown of Debian 13 with isc-dhcp-client
failed on that. Debian fixed ifupdown in 13.4. Proxmox writes a
systemd-networkd configuration only for Ubuntu containers.

A Keel container (Debian 13.7, BR2, 2026-11-06) does not have that
failure. It uses:

- ifupdown-ng 0.12.1, not the classic ifupdown;
- dhcpcd-base 10.1 as the DHCP client; isc-dhcp-client is removed;
- tkl-dhcpcd-ifupdown-glue 0.1.3+keel1, which keeps dhcpcd.conf in step
  with the stanzas Proxmox writes;
- systemd-networkd inactive.

With the two `dhcp` stanzas that Proxmox writes, eth0 gets its IPv4 lease,
a ULA and a global IPv6 address. Every commissioning pass of 2026-11-06 on
BR1 (`ip6=auto`) and BR2 (`ip=dhcp,ip6=dhcp`) ran on this stack.

## Decided

1. A Keel container keeps ifupdown-ng, dhcpcd-base and
   tkl-dhcpcd-ifupdown-glue.
2. Keel does not move to systemd-networkd until Proxmox writes a
   systemd-networkd configuration for Debian containers. Before that, the
   Network tab of the Proxmox web interface writes `/etc/network/interfaces`
   on every start, and a container on networkd would ignore it, or need a
   translator of its own.
3. The VM from the ISO stays on the same stack, so that one network stack
   is tested, not two.

## Why

- `network.managed_by: host` (spec.md) means that Proxmox decides the
  network of a container. The file Proxmox writes for Debian is
  `/etc/network/interfaces`.
- keel writes and reads that file: `keel spec apply` (network),
  `keel inspect`, the confirmation window of 0018, and the network screens
  of confconsole. A move to networkd changes all of them.
- The defect that made people ask for networkd is fixed on this stack, and
  proven on the real sites.

## When to look again

Look at this decision again when one of these is true:

- pve-container writes a systemd-networkd configuration for a Debian
  container (follow bug 6644 and the pve-container changelog);
- Debian drops ifupdown-ng or dhcpcd-base;
- a defect of this stack that the glue cannot fix.

Then write a new note with a real test of both stacks on BR1, BR2 and BR3
(LXC and the VM from the ISO), and move both together.

## Found beside this

The container's `/etc/network/interfaces` also has an `eth1` block with a
`hostname` line, which the build leaves. It does not change eth0, but it
is a leftover to remove.
