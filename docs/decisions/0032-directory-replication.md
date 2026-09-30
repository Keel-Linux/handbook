# 0032: Directory replication is a generic mesh service

Date: 2026-09-30
Status: **decided by the maintainer, 2026-09-30** (ADR-010).

## Decision

- **Directory replication is a generic mesh service**, delivered by a
  Syncthing overlay.
- **Each appliance declares** `replicate:` (the paths of its durable
  state) and `exclude:` (sessions, caches, tmp, locks, logs, rebuildable
  indexes), in its manifest (0034).
- **Sessions go to the database or to Redis**, never to a replicated
  directory.
- **Data with its own replication is never replicated by file**:
  databases, search indexes.
- **Rejected: Lsyncd.**

Debian 13 (trixie) has `syncthing` 1.29.5 (checked against the archive,
2026-09-30).

## What this amends

- **0020, "Where each piece lives" and "What Debian 13 gives us"**: the
  file copy was rsync, pulled by each replica from the primary on a timer,
  and Syncthing was left out as "made for syncing both ways, which one
  writer does not want". Syncthing replaces the rsync pull. The one-writer
  rule is kept by the folder types under "Resolved" below.
- **0020, lsyncd**: rejected there and here, for 0013's reason (a pushing
  tool needs the primary to list its replicas) and now also because a
  generic service is wanted.
- **Brief section 4.2** (the mutable state map): the map becomes the
  `replicate:` and `exclude:` lists of the manifest.
- **0020, "The hard parts", item 3** (database and files promote
  together): unchanged, and the folder flip below is part of that one
  operation.

## Resolved (maintainer, 2026-09-30)

- **Syncthing stands, one way per role, as the implementation detail.**
  Syncthing in both directions produces conflict files
  (`*.sync-conflict-*`) when both sides change a file. With a hot standby
  (0031) there is one writer, so the folders are **send-only on the
  primary and receive-only on the standby**, and the types are flipped on
  promotion, in the same step that promotes the database. A receive-only
  folder that finds local changes reports them rather than sending them,
  which is also what 0020's rejoin needs to see. 0020's rsync pull is
  superseded.
- Object storage (0038) shrinks what is replicated by file to what an
  application insists on keeping on a filesystem.
