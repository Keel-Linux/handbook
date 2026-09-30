# 0026: Installation by discovery, not by typing

Date: 2026-09-30
Status: **decided by the maintainer, 2026-09-30** (ADR-004).

## Decision

In an advanced installation the installer asks for two things: the address
of one node of the mesh and an entry secret. It queries etcd, lists what
exists ("found MariaDB, Redis and two Nginx") and the operator selects
what this machine consumes. Only the first appliance of a mesh needs real
effort; every later one is a selection.

## What this amends

- **0013, "What the operator sees"**: the replica screen asked for the
  primary's address and the replication password, typed. In an advanced
  installation they come from the registry instead. The rule that each
  screen configures only the machine it runs on stays: discovery reads
  the mesh, and what it writes is this machine's configuration.
- **0013, phase 1** (an application pointing at a remote database):
  becomes the normal case of an advanced installation, reached by
  selection rather than by typing an endpoint.
- **0020, "Where each piece lives"**: discovery was assigned to Keel Cloud
  so that the operator would not copy keys by hand. It now runs on the
  mesh itself (0025); Keel Cloud is not needed for it.

## Review notes (open points for the maintainer)

- [ ] The entry secret needs a lifetime and a scope: single use or
  reusable, and what it lets a joining node read or write in etcd before
  it is admitted. Not yet specified.
