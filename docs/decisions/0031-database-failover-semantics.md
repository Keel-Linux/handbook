# 0031: Database failover semantics

Date: 2026-09-30
Status: **decided by the maintainer, 2026-09-30** (ADR-009). The failback
point was refined by the maintainer the same day: see "Resolved".

## Decision

- **The replica is a hot standby and does not serve traffic.**
- **Replication is synchronous:** a commit is confirmed on the primary only
  after the replica has received it, for MariaDB and PostgreSQL alike. How
  each engine implements it is under "Resolved"; MariaDB's is
  semi-synchronous, and this note does not claim more.
- **Failback: the operator chooses, and Keel implements automatic.** The
  choice between automatic and manual failback stays the operator's, at
  installation, as 0020 decided. Keel builds automatic failback so that
  it is a real option, with one hard condition: the role returns to the
  original primary only after it has fully caught up with what the
  replica wrote while it was primary.

The source text says master and slave; this note uses 0009's and 0020's
vocabulary, primary and replica.

## What this amends

- **0020, "The hard parts", item 2**: "the database replication and the
  file pull are both asynchronous" becomes, for the database, synchronous
  on PostgreSQL and semi-synchronous on MariaDB (see "Resolved").
- **0020, "Decided, second round"**, the failback row: **not changed on
  the choice or the default.** Failback stays the operator's choice among
  automatic, manual and never, with **manual as the default**, as 0020
  states it. This note amends 0020 only by committing Keel to implement
  automatic failback, with the catch-up condition above, so that choosing
  it works.
- **0020, "One role"**: a replica's web tier was read-only; with a hot
  standby that serves no traffic, the replica serves nothing until it is
  promoted.
- **0013, "Several replicas"**: the client section's list of read
  endpoints no longer points at replicas in a paired set, since the
  replica serves no reads.

## Resolved (maintainer, 2026-09-30)

- **Synchrony follows the decision, implemented per engine:**
  - **MariaDB: semi-synchronous replication**, `rpl_semi_sync` with
    `rpl_semi_sync_master_wait_point=AFTER_SYNC`. The primary waits until
    the replica has *received* the transaction, not applied it, and falls
    back to asynchronous when no acknowledgement arrives within
    `rpl_semi_sync_master_timeout`. Every commit pays the round trip to the
    replica. MariaDB has no fully synchronous primary and replica
    replication; that is Galera (three nodes, multi-primary), 0013's phase
    4, a different topology and not what this note chooses.
  - **PostgreSQL: `synchronous_commit`** with the replica named in
    `synchronous_standby_names`. With one synchronous replica, the primary
    stops committing while the replica is away.
  - **The timeout policy is an implementation task** for both engines:
    how long MariaDB waits before falling back, what a primary that fell
    back reports, and what PostgreSQL does while its replica is gone.
- **Failback, as the maintainer put it:** "The user has to decide whether
  failback is automatic or manual. But let's work towards having
  automatic." So the operator's choice of 0020 stays, its default stays
  manual, and automatic failback after full catch-up is implemented
  (roadmap Phases 2 and 5). The rejoin choice of 0020, and its safeguard
  of a dump and a copy of the files, is unchanged.
- keel 0.11.x already has a read-only replica (see also tracker#26). A hot
  standby that serves no traffic goes further; the read-only mode stays
  useful as the state between promotion steps.
