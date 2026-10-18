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

## Amendment 2026-10-14: the new primary commits alone after `--old-primary-gone`

Decided by the coordinator under the maintainer's delegation. It follows
the maintainer's ceiling of 2026-10-14: after the VIP lands, writes must
resume within 5 s (Keel-Linux/keel#148).

Case (c) of the end to end test (Keel-Linux/keel#149) showed what the
no-timeout rule does after an unplanned failover. The new primary keeps
`FIRST 1 (keel)`. The old primary is gone, so every commit waits until the
operator confirms the reseed of the old primary. The first write came 202
to 216 s after the VIP landed.

The rule now has one exception. `keel database promote --old-primary-gone`
makes the new primary commit alone: it clears `synchronous_standby_names`
and reloads the server. The operator's flag is the human statement that
the old primary is gone, and this statement is what allows the change.
While the primary commits alone, the database watch alerts on each run.
When a standby streams again after the confirmed reseed, the converge
writes `FIRST 1 (keel)` back.

The cost, accepted: until the reseed, each commit is on one node only. A
loss of the new primary in that time loses those commits. A planned
promote and a replica cut (case (b)) do not change: commits still wait
for the standby, with no timeout.

## Amendment 2026-10-15: an expired lease counts as `--old-primary-gone`

Decided by the maintainer on 2026-10-15, in answer to the question of
Keel-Linux/keel#165. The maintainer's answer was: "sim".

With etcd, the other node of the pair claims the VIP only after the
lease of the old primary's claim expired (keel `docs/vip.md`). Case (c)
on real nodes showed that the VIP moved by itself, but the new primary
took no write until the operator ran `keel database promote
--old-primary-gone` (`docs/evidence/2026-10-15-br3-thin-etcd-witness.md`,
section 5).

The rule of the amendment of 2026-10-14 now has a second statement that
allows the exception:

- **The scope.** etcd is formed, and the VIP controller of the new
  primary claims because the lease of the newest claim expired. The
  controller saw that lease alive before, and the lease ended at its
  due time, not before it.
- **What keel does.** The controller records the statement before it
  records the claim. keel database follow then promotes the standby and
  empties `synchronous_standby_names`, the same as after `keel database
  promote --old-primary-gone`. The new primary commits alone.
- **What does not count.** A lease that ended before its due time was
  revoked, not expired. A lease that the controller never saw alive,
  for example after a restart of the controller, can be either. In
  these cases the new primary does not commit alone. Its commits wait
  for a standby or for the operator, as before.
- **The alert.** While the primary commits alone, the database watch
  alerts at each run. When a standby streams again after the confirmed
  reseed, keel writes `FIRST 1 (keel)` back.

The safety argument: a holder drops the VIP 10 s after its last renewal
that the majority confirmed, and etcd cannot expire the lease before
20 s after that renewal. Thus the old primary was cut off from the
majority, and it dropped the VIP before the new claim. Under
synchronous replication it cannot acknowledge a write without its
standby, and the standby is the new primary. The exception is a client
that sets `synchronous_commit` to `local` or `off` for its session
(Keel-Linux/keel#156): the old primary can acknowledge such a write in
the window before keel stops it.

The cost, accepted: until the reseed of the old primary, each commit is
on one node only. A loss of the new primary in that time loses those
commits.

## Amendment 2026-10-18: the old primary rejoins by `pg_rewind` when it can

Decided by the maintainer on 2026-10-18. The question came from the Odoo
release test (`evidence/2026-10-18-odoo-nginx-cross-site.md`, "A primary
that took no write"): should the PostgreSQL pair rejoin an old primary
without a full reseed, as the MariaDB pair does since keel 0.23.43
(Keel-Linux/keel#202)? The maintainer's answer was: "sim".

This amendment replaces two statements above: "Rejoin after a promotion
is a reseed, never a rewind" and "failback is a confirmed reseed". The
reseed stays, as the fallback.

The rule:

- **When.** An old primary returns, and keel fences it: a standby that
  follows nobody, with the VIP held by the other member. The holder
  answers over TLS.
- **What keel does.** keel keeps the dump of the old primary, as before.
  Then it stops the old primary cleanly and runs `pg_rewind` against the
  holder, the new primary. Then it writes the follow drop-in, starts the
  server as a standby, and the standby follows the new timeline through
  the pair's slot. No confirmation flag is needed: `pg_rewind` only
  discards on the old primary and never changes the holder.
- **What is lost, and what is not.** The rewind discards what the old
  primary wrote after the fence point, and this data never comes back.
  The rewind never changes the new primary, so every write that the new
  primary acknowledged stays. The dump that keel kept first holds what
  was discarded.
- **The checks before the copy.** keel runs `pg_rewind --dry-run` first.
  The dry run changes nothing. It proves that both clusters have the
  same system identifier, that the holder is a primary, that the old
  primary was shut down cleanly, and that `wal_log_hints` or data
  checksums are on.
- **The fallback.** If the dry run fails, keel changes nothing and the
  existing path applies: the divergence record, and the reseed only with
  `--destroy-local-database`. If the real run fails after the dry run
  passed, the copy is unusable. keel records this, never runs
  `pg_rewind` on that copy again, and the reseed with
  `--destroy-local-database` is the only path.
- **`wal_log_hints`.** The pair drop-in has written `wal_log_hints = on`
  on both nodes since 0054, so a node that keel converged already has
  it. keel reads the setting of the running server before the rewind.
  keel does not restart a primary that serves clients to change it. A
  node where the setting is off is not rewound. It takes the fallback,
  and the next apply restarts it as the converge did before.
- **`wal_keep_size`.** `pg_rewind` reads the WAL of the old primary back
  to its last checkpoint before the fork, and the server recycles that
  WAL at its shutdown checkpoint. The pair drop-in now sets
  `wal_keep_size = 256MB`. The server takes this setting on a reload, so
  an apply of the older drop-in writes the new line and reloads. It
  never restarts a primary that serves clients for this change.
- **The source role.** `pg_rewind` reads files of the holder through
  SQL. The holder grants the replication role the four functions that
  the PostgreSQL manual names for this, in the `postgres` database
  only. The role has the right to copy the whole cluster already. The
  functions also read files that are outside of the data directory, and
  the cost is accepted for that reason. A dedicated role would add a
  second secret to the pair for no gain.

The cost, accepted: the rewind needs the WAL of the old primary since the
fork point, and the holder must have made a checkpoint after its
promotion. When one of these is missing, `pg_rewind` refuses and the
fallback applies. The pair keeps up to 256 MB more WAL on each node.

The measured times of the rewind and of the reseed are in
`evidence/2026-10-18-postgresql-pg-rewind.md`.
