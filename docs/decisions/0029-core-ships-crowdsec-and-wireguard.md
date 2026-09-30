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

## What this amends

- **0020, "What Debian 13 gives us"**: keepalived was left out because a
  floating address needs a shared link layer. That reasoning holds for
  keepalived; the VIP here is not a link-layer address but a route on the
  mesh (see the review note). 0020's DNS with a health check remains the
  way public clients find the service.
- **0018**: governs every change to `/etc/wireguard/`, including those a
  VIP move makes (see the review note).

## Review notes (open points for the maintainer)

- [ ] **WireGuard is layer 3 and has no ARP.** A VIP cannot be claimed by
  announcing it; moving it means changing `AllowedIPs` (the VIP as a
  `/128`) on every peer, so that the peers route it to the new active
  node. That needs a controller watching etcd and rewriting peers. It
  belongs with the etcd phase of the roadmap, not with the first
  WireGuard work.
- [ ] **0018's confirmation window and an automatic VIP move.** 0018
  reverts any overlay change that is not confirmed over the new
  configuration within 120 seconds. A controller moving the VIP must
  either confirm its own change (0018 already allows an agent to) or be
  exempted for `AllowedIPs`-only changes. To be decided with the
  controller.
- [ ] CrowdSec in Debian 13 is `1.4.6-10+b4`, well behind upstream's
  current series (see 0030's notes). Shipping a current CrowdSec means a
  Keel package under 0039.
