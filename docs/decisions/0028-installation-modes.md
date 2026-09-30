# 0028: Installation modes at first boot

Date: 2026-09-30
Status: **decided by the maintainer, 2026-09-30** (ADR-006).

## Decision

The installer uses two terms only: **simple installation** and **advanced
installation**. At first boot the operator chooses one of three modes:

1. **Simple installation.** Everything in one LXC. No mesh, no etcd.
2. **Advanced, cloud simple.** The database replicated from a primary to a
   replica; the application's files in a single LXC.
3. **Advanced, cloud advanced.** Three LXC at least, an etcd quorum, and
   directory replication (0032).

Cloud advanced assumes three distinct sites, or two plus an external
arbiter. When all three nodes share one host, the installer warns in one
line. In either cloud mode the primary generates the key, the password and
the WireGuard endpoint that the replica uses.

## What this amends

- **0013, "What the operator sees"**: the console's Standalone and Cloud
  (Primary, Replica) choice is folded into these modes. Standalone is the
  simple installation; primary and replica remain the roles within a cloud
  mode, in 0009's vocabulary.
- **0020**: the minimum of three for automatic failover is unchanged.
  Cloud simple has two nodes, so its failover is by hand; cloud advanced
  is the mode where 0020's election runs. The external arbiter is 0020's
  data-less voter.
- **0020, "Decided"** ("nothing assigns roles at installation from
  outside"): still true. The primary generates what the replica needs,
  and the replica is still configured on the replica.
