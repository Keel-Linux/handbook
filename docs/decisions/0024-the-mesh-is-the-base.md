# 0024: The mesh is the base, not an extra

Date: 2026-09-30
Status: **decided by the maintainer, 2026-09-30** (ADR-002).

## Decision

- **WireGuard ships in Keel Core.** Every appliance can join a mesh, even
  when it is alone.
- **Tunnels are always initiated from inside to outside**, so a node behind
  NAT or a firewall needs only outbound UDP.
- **IPv6 first.** Native IPv6 goes direct between nodes. IPv4-only nodes
  enter through a rendezvous point that translates (Tayga, NAT64).
- **Rendezvous points are hosted by nodes with a real edge and fixed
  addressing.** Which nodes, and how many, is an operational matter and is
  not recorded here.

Debian 13 (trixie) carries both pieces: `wireguard-tools 1.0.20210914`
and `tayga 0.9.2` (checked against the archive, 2026-09-30).

## What this amends

- **0020, "Where each piece lives" and "Order"**: the WireGuard overlay
  was step 2 of that order, after milestone M3, and key exchange was one
  of Keel Cloud's jobs. The overlay is now part of Core from the start,
  and in cloud mode the primary hands the replica its endpoint and key at
  installation (0028). Keel Cloud keeps DNS with a health check; membership
  moves to etcd (0025).
- **0018** is unchanged and still governs: the overlay is converged from
  inside, under the confirmation window, and the host of a container must
  have the `wireguard` module loaded.

## Review notes (open points for the maintainer)

- [ ] The DNS successor for nodes behind NAT whose IPv6 prefix changes
  (HubDNS today) is not decided. A PowerDNS overlay fed from etcd is the
  likely shape; it is tracked as an open architecture item of the
  roadmap.
