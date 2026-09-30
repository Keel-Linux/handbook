# 0031: Database failover semantics

Date: 2026-09-30
Status: **decided by the maintainer, 2026-09-30** (ADR-009).

## Decision

- **The replica is a hot standby and does not serve traffic.**
- **Replication is synchronous:** a commit is confirmed on the primary only
  after the replica has received it, for MariaDB and PostgreSQL alike.
- **Failback is automatic:** the role returns to the original primary, but
  only after it has fully caught up with what the replica wrote while it
  was primary.

The source text says master and slave; this note uses 0009's and 0020's
vocabulary, primary and replica.

## What this amends

- **0020, "The hard parts", item 2**: "the database replication and the
  file pull are both asynchronous" becomes, for the database, synchronous
  (see the review notes for what each engine can promise).
- **0020, "Decided, second round"**, the failback row: failback was the
  operator's choice among automatic, manual and never, with **manual** as
  the default. This note makes failback automatic, after catch-up.
- **0020, "One role"**: a replica's web tier was read-only; with a hot
  standby that serves no traffic, the replica serves nothing until it is
  promoted.
- **0013, "Several replicas"**: the client section's list of read
  endpoints no longer points at replicas in a paired set, since the
  replica serves no reads.

## Review notes (open points for the maintainer)

- [ ] **MariaDB has no truly synchronous primary and replica
  replication.** Its semi-synchronous replication (`rpl_semi_sync`, with
  `rpl_semi_sync_master_wait_point=AFTER_SYNC`) makes the primary wait
  until the replica has *received* the transaction, not applied it, and
  falls back to asynchronous when no acknowledgement arrives within
  `rpl_semi_sync_master_timeout`. Every commit also pays the round trip to
  the replica. Truly synchronous MariaDB is Galera: three nodes,
  multi-primary, which is 0013's phase 4 and a different topology. The
  note should say **semi-synchronous for MariaDB, plus the timeout
  policy**: how long to wait, and whether a primary that fell back to
  asynchronous raises an alert, refuses writes, or carries on.
- [ ] **PostgreSQL can do it** with `synchronous_commit` and
  `synchronous_standby_names` (`on` waits for the replica to flush,
  `remote_apply` for it to apply). With one replica named as synchronous,
  the primary stops committing while the replica is away, so PostgreSQL
  needs the same policy: what happens when the replica is gone.
- [ ] **Automatic failback supersedes 0020's operator choice with a manual
  default.** This should be confirmed: whether the choice disappears or
  stays with automatic as the new default, and whether 0020's rejoin
  safeguard (a dump and a copy of the files before replacing a node's
  data) still applies to the node that fails back.
- [ ] keel 0.11.x already has a read-only replica (see also
  tracker#26). A hot standby that serves no traffic goes further; the
  read-only mode stays useful as the state between promotion steps.
