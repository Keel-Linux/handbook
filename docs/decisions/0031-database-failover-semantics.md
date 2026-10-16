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

## Amendment 2026-10-16: the MariaDB timeout is 30 s, and a cut holder acknowledges no write

Decided by the coordinator under the maintainer's delegation, from the
cross-site release test of LNMP 19.0-3 and its rehearsals
(`docs/evidence/2026-10-16-lnmp-lnpp-19.0-3-cross-site.md`).
Implemented by Keel-Linux/keel#190 (keel#186, keel#193) and
Keel-Linux/keel#197 (keel#195).

**What changes.**

1. `rpl_semi_sync_master_timeout` is 30 s, not 10 s. This changes the
   maintainer's answer of 2026-10-03. The fallback to asynchronous
   commits when the replica is lost stays: it comes 30 s after the last
   acknowledgement.
2. The holder that loses the confirmation of its lease for 6 s turns
   its MariaDB server read only and ends the client connections, before
   it drops the VIP. It takes writes again at the next confirmed
   renewal.

**Why the current approach is not enough.** On a cut MariaDB primary,
acknowledged writes were lost. A write that waited for the replica
returned OK after the 10 s timeout, and the next writes returned OK at
once, until the old primary dropped the VIP at 15 s. MariaDB also
returns OK for a waiting write when the dump thread to the cut replica
ends, about 12.6 s after the cut. The new primary does not have these
writes. Rehearsal 1 lost 12 of 1906 acknowledged ids.

**Whether it can be made to work.** On real nodes on BR1 and BR2, the
fence at the doubt made the server read only 6.1 s to 8.8 s after a
cut, before the dump thread could end. The waiting write got an error,
not OK. In rehearsal 3, 0 acknowledged ids were lost in 2 network cuts
and 1 stop of a CT, at 5 ms and at 250 ms
RTT, with a writer on the local socket and a writer at the VIP. Two
quiet windows of 10 minutes gave no false doubt.

**Why this is better.** A cut of the primary site loses no write that a
client was told is stored, which the release test requires. With a 10 s
timeout, the worst case measured leaves 1.2 s. With 30 s, the fence has
room. The cost is that a lost replica holds the writes 30 s, not 10 s,
before the fallback, and an etcd re-election of more than 6 s holds the
writes of the MariaDB holder until it ends.

