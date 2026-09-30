# 0025: etcd is the mesh registry, not only quorum

Date: 2026-09-30
Status: **decided by the maintainer, 2026-09-30** (ADR-003).

## Decision

- **Every appliance announces itself in etcd**: what it offers, where it
  is, and its site, which is the availability zone label.
- **etcd is control plane only.** It holds cluster state, never
  application data. A few writes a minute tolerate a 30 ms round trip.
- **Quorum needs an odd number of voters.** Two nodes cannot elect; a
  third vote is mandatory for automatic failover.
- **Site labels are enforced**: two replicas of the same data are never
  placed in the same site.
- **Corosync is not used across a WAN.**

## What this amends

- **0020, "Decided, second round"**: etcd was the store of one appliance's
  election lease, running on that appliance's nodes. It becomes the
  registry of the whole mesh, and the election of 0020 is one use of it.
  The data-less voter of 0020 is the external arbiter of 0028.
- **0020, "Where each piece lives"**: membership was Keel Cloud's; it is
  now the registry's, on the nodes. Keel Cloud keeps DNS with a health
  check.
- **0020 and 0013, minimum of three for automatic failover**: unchanged,
  and now stated for the whole mesh.
- **Brief section 2** (no fleet orchestration in this codebase): a
  registry the nodes write about themselves is not orchestration. What
  acts on it (the election, the VIP controller of 0029) stays in its own
  repository, as 0020 amended.

etcd ships stopped by default (0036), so a simple installation never runs
it.
