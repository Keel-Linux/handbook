# 0029: Keel Core ships CrowdSec and WireGuard, and a VIP on the mesh

Date: 2026-09-30
Status: **decided by the maintainer, 2026-09-30** (ADR-007).

## Decision

- **Keel Core ships CrowdSec and WireGuard.**
- **Simple installation:** CrowdSec installed and disabled.
- **Advanced installation:** the installer opens CrowdSec's configuration,
  and configures a VIP over the WireGuard mesh that the active node
  assumes.
- **The VIP is for delivering the service only.** Replication and
  node-to-node traffic always use the nodes' real addresses, never the
  VIP.
- **Automatic VIP promotion only for database appliances.**

Amended by 0041 (2026-09-30): for now the VIP is configured for database appliances only, not in every advanced installation.

## What this amends

- **0020, "What Debian 13 gives us"**: keepalived was left out because a
  floating address needs a shared link layer. That reasoning holds for
  keepalived; the VIP here is not a link-layer address but a route on the
  mesh (see "Resolved"). 0020's DNS with a health check remains the
  way public clients find the service.
- **0018, for VIP moves**: 0018 puts every change to `/etc/wireguard/`
  under its confirmation window, so a VIP move would be reverted unless
  confirmed. That point of 0018 is amended: see "Resolved" below.

## Resolved (maintainer, 2026-09-30)

The decision stands as written; where it meets an earlier note, the
earlier note is superseded on that point.

- **An automatic VIP move is not under 0018's confirmation window.**
  0018's text covers the whole overlay (`/etc/wireguard/`), so this is an
  amendment of 0018 and not a reading of it: a change made by the VIP
  controller that touches only the VIP's `AllowedIPs` entry is applied
  without arming the revert timer and without `keel network confirm`.
  The reason the exemption is safe: the window protects a session from a
  change to the addresses and routes it runs over, and a VIP move changes
  neither the node's uplink nor its own overlay address; node-to-node
  and management traffic use real addresses, never the VIP. Every other
  overlay change (keys, endpoints, the node's own addresses, peers added
  or removed) stays under the window.
- **Implementation detail: WireGuard is layer 3 and has no ARP.** A VIP
  cannot be claimed by announcing it; moving it means changing
  `AllowedIPs` (the VIP as a `/128`) on every peer, so that the peers
  route it to the new active node. That needs a controller watching etcd
  and rewriting peers, built with the etcd phase of the roadmap.

## Packages (checked 2026-09-30 against the Debian archive and WNPP)

| Package | Debian 13 (trixie) | Note |
| --- | --- | --- |
| crowdsec | 1.4.6-10 | upstream is at 1.8.1 |
| crowdsec-firewall-bouncer | 0.0.25 | |
| wireguard-tools | 1.0.20210914 | |

Whether Core ships trixie's CrowdSec or a current one packaged by Keel
under 0039 is an implementation task of this decision.
