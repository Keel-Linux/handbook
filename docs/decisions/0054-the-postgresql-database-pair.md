# 0054: The PostgreSQL database pair

Date: 2026-10-13
Status: **decided 2026-10-13** under the maintainer's standing delegation
of design calls. It is the design note for the second converge engine,
after MariaDB (0.23.x, Keel-Linux/keel#93, `docs/replication.md` in the
keel repository). It implements the PostgreSQL column of 0013's mode
table and answers the open implementation tasks of 0031 for this engine.
Found and asked for by the 2026-10-13 BR1+BR2 pair test
(`evidence/2026-10-13-step12-pair-br1-br2.md`): the cloud functions
worked on a pristine PostgreSQL pair, and `database.server` converge
answered "MariaDB is the first" (0013).

## Decision

- **The layout is a twin, not a framework.** `dbpostgres.py` is written
  as the pure twin of `dbmariadb.py`: one module of engine constants and
  pure functions per engine, side by side, as `inspect/dbengines.py`
  already holds `read_mariadb` and `read_postgresql`. The engine
  dispatch enters at the same gates MariaDB uses (`plan_database`,
  `observe_database`). `dbpair.py`, `dbsecret.py`, `dbready.py`,
  `actions.py` and `effects.py` stay untouched: they are already
  engine neutral. `dbtls.py` is parameterized (group, directory,
  certificate subject, client options) instead of forked; its PKI flow
  is the same for both engines.
- **Seeding is `pg_basebackup`.** 0013 already names it. The base
  backup copies the whole cluster, so there is no dump position to
  parse and no accounts alignment step: roles are cluster global and
  arrive with the copy. There is no `dbaccounts.py` twin in this
  version. The refuse-unless-empty-or-confirmed gate of 0013 stays.
- **Rejoin after a promotion is a reseed, never a rewind, in this
  version.** PostgreSQL has no GTID set. The divergence probe is the
  timeline: a promoted node is on a new timeline by definition, and a
  node whose timeline differs from the holder's has diverged.
  Timelines equal: resume streaming. Timelines differ: write the
  divergence record (same shape as MariaDB's, a dump is kept first)
  and reseed only through the confirmed-destroy gate.
- **Automatic failback is not implemented for PostgreSQL in this
  version.** 0031's hard condition is that the role returns only after
  the node fully caught up. After a timeline fork, "nothing to lose"
  cannot be proven without `pg_rewind` analysis, so the conservative
  answer to 0031 is: failback is a confirmed reseed. `pg_rewind`, with
  `wal_log_hints=on` in the pair drop-in, is the revisit path. The
  operator's 0020 choice and its manual default are unchanged.
- **Read-only enforcement is the standby itself.** A PostgreSQL
  standby refuses writes while it is in recovery, and 0031 already
  took the replica's reads away. There is no `READ_ONLY ADMIN` twin
  and no account revocation. Keel's own statements run as the
  `postgres` OS user through `runuser`; the appliance role is never
  made superuser.
- **Promotion drains, then promotes.** Drain is replay catch-up
  (`pg_last_wal_replay_lsn()` reaches `pg_last_wal_receive_lsn()`);
  promote is `SELECT pg_promote()`.
- **There is no `server_id`.** Identity for the pair is one replication
  slot named `keel` on the primary and a `repl` role with the
  `REPLICATION` attribute. `primary_conninfo` carries the pair secret
  and `application_name=keel`.
- **Synchronous commit follows 0031, with no timeout.** The pair
  drop-in sets `synchronous_standby_names='FIRST 1 (keel)'` and
  `synchronous_commit=on`: a commit is confirmed after the standby
  received and flushed it. While the replica is away the primary stops
  committing. There is no fallback to asynchronous, and the watch
  surfaces an alert. This answers the timeout policy item 0031 left
  open for PostgreSQL.
- **TLS is the mesh PKI, parameterized.** Same flow as MariaDB: leaf
  certificates from the mesh root over the members' channel, CRL
  renewal included. The directory, the file group `postgres`, the
  certificate subject `<member> postgresql` and the libpq option names
  differ; `pg_hba` `clientcert=verify-full` with
  `sslmode=verify-full` in `primary_conninfo` is the twin of MariaDB's
  `REQUIRE SUBJECT AND ISSUER`.
- **`pg_hba.conf` is the authorization surface.** A replication
  authorization is a line for the replication pseudo-database per
  origin of `replication.allowed_from`, as 0013's "Several replicas"
  has it. Names stay accepted and documented fragile (0013).
- **Testing mirrors the MariaDB build order.** Pure unit tests first,
  one concern at a time; the network-namespace pair harness
  (`tests/postgres_netns.py`, its own CI job) last, as the gate.
  0013's warning binds: if two containers cannot prove it in the
  gate, it does not ship.

## Why

The MariaDB pair works because every hard question has a small, checkable
answer: GTID proves divergence, `read_only` plus a privilege refusal
enforces the replica, semi-sync times out and reports. The twin is kept
honest the same way: the timeline answers divergence, the standby
mechanism answers enforcement, and the no-timeout answer removes a
silent downgrade. Where PostgreSQL has no cheap proof (failback without
rewind), the design says no instead of guessing.

## What this amends

- **0013**: the PostgreSQL column of the mode table (replication slot,
  replication role, `pg_hba` entry; `pg_basebackup` then
  `standby.signal` and `primary_conninfo`) is now the implementation
  contract.
- **0031**: the timeout policy item for PostgreSQL is resolved — no
  timeout, no fallback, the primary blocks and reports.
- **0049 (second and third rounds, failback)**: for PostgreSQL,
  failback in this version is a confirmed reseed only. Automatic
  failback waits on the `pg_rewind` revisit.

## When to revisit

- **`pg_rewind` failback**, with `wal_log_hints=on` in the pair
  drop-in, when reseeding a large cluster on every failback hurts.
- **Several replicas.** `FIRST 1 (keel)` names one standby. A larger
  set changes `synchronous_standby_names`, the slot story and the
  0031 commit contract.
