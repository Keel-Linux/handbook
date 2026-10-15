# Evidence: the fixes of the PostgreSQL pair on real nodes

Date: 2026-10-15, 00:10 to 00:24 UTC.
Issues: Keel-Linux/keel#153, #152 and #154, found in
`docs/evidence/2026-10-14-postgresql-pair-real.md`.
Decision: 0054.

Machines: the same as in the evidence of 2026-10-14.

- Node A: CT 9062 on nfs1-br2 (BR2), overlay `fd1a:bb4c:b407::fc0a`.
- Node B: CT 9054 on hw12-br1 (BR1), overlay `fd1a:bb4c:b407::1`.
- VIP: `fd1a:bb4c:b407::ffff:1`. 2 nodes, `installation.mode:
  cloud_simple`, no etcd. The base RTT on the overlay is 4 ms.
- No other CT or VM was changed.

Output is trimmed. Times are Unix seconds of the CT clocks. No secret
is in this file.

## Summary

| Item | Result | Numbers |
| --- | --- | --- |
| keel#153, #152, #154 | 3 PRs, merged on green checks | keel#157, #158, #159 |
| Release | PASS | keel 0.23.21 in trixie-testing, then in trixie, signed with nobody at a keyboard |
| Upgrade of the CTs | PASS | 0.23.18 to 0.23.21 on 9062 and 9054 |
| (c) as a prelude | PASS | `keel database promote --old-primary-gone` on B: 34.1 s, epoch 7 |
| (e) old primary back, no etcd | PASS, no operator step | the boot follow learned epoch 7 2.5 s after the server started; the server stopped 3.4 s after it started; fenced, dumped and recorded 18.8 s after `pct start`; 0 of 1 write acknowledged; no start and stop cycle |
| (d) confirmed reseed, watch running | PASS at the first try | 10.1 s; streaming 0.15 s after the apply; 0 "pid file is invalid" lines; `FIRST 1 (keel)` back 12.6 s later |
| Setup from a fresh pair (keel#152 reproduction) | PASS, keel CLI only | the fenced VIP holder took writes 1.5 s after `keel vip promote` returned; the other node seeded after the confirm in 6.0 s, streaming 0.07 s later |

## 1. The PRs

Each PR was test first: unit tests red before the fix, then green.

| PR | Issue | Version | What changes |
| --- | --- | --- | --- |
| keel#157 | #153 | 0.23.19 | Each stop and start names `postgresql@17-main`, not the umbrella `postgresql`. The seed waits until the postmaster of `postmaster.pid` is gone. `standby.signal` goes into the copy before the copy moves. A PostgreSQL start holds the lock of the replication. |
| keel#158 | #152 | 0.23.20 | A fenced holder takes writes with no drain when it never had a role in the pair, when its divergence record shows 2 system identifiers, or after `--old-primary-gone`. |
| keel#159 | #154 | 0.23.21 | Without etcd, `keel database follow` asks the other members for a newer claim when its own claim is not proven. It does not start the server of an unproven claim. |

The changelog gate of each PR needs a new and greater version. Thus
each PR has its own version, and the release is 0.23.21. It holds the
3 fixes. 0.23.19 and 0.23.20 were not published.

Checks: each PR had all checks green before the merge. The known flake
"vip-upgrade holder try-restart drop" failed on each PR. It passed on
a re-run: 1 re-run on #157 and #158, 2 re-runs on #159. On #158 the
job `mariadb / trixie` also failed in the runner's reset script, before
the test started. On #159 the job `tests / coverage` failed once in a
gpg step of `test_cli_channel`. Both passed on the re-run.

The push run on main after the merge of #157 failed in
`postgres / trixie`: case (c) got "etcd did not answer: etcdctl get:
context deadline exceeded" 3 times. This is the class of keel#94 (etcd
under the design case). The same job passed on the PR run of #157, and
on the PR runs of #158 and #159. The PRs do not change the etcd path.

## 2. Release of keel 0.23.21

keel main at 62759e9 (it includes keel#157 to #159).

```
# build host, 00:10:55
$ bin/build-package --native keel main </dev/null
build-package: done: keel_0.23.21_amd64.changes in /srv/keel-apt/incoming
$ dpkg-deb -f keel_0.23.21_all.deb Version Depends
Version: 0.23.21
Depends: python3 (>= 3.12), python3-yaml, zstd, gpgv, openssl, python3:any
sha256 8889face51e042ac3090213ecb17882c38f326b146bf29d7cb0df67bd5cb363a
$ bin/publish </dev/null                     # 00:11:17
publish: committed in /var/tmp/keel-testbuild/s3/apt: publish trixie-testing: keel 0.23.21
rc=0
# workstation
$ /tmp/keel-apt-tooling/bin/keel-publish-mirror --archive-only
EXIT=0
```

The changelog warning of 0.23.18 is gone: the entries 0.23.17 and
0.23.18 have their trailer lines now (keel#155, item 3).

The promotion came after the tests of sections 4 to 6:

```
$ bin/promote keel=0.23.21 </dev/null          # plan first
would copy from trixie-testing into trixie:
  keel 0.23.21 all (was 0.23.18)
$ bin/promote --yes keel=0.23.21 </dev/null    # 00:23:22
promoted into trixie: keel
rc=0
$ git log --oneline -2
2b84bf5 promote trixie: keel 0.23.21
1ae369a publish trixie-testing: keel 0.23.21
# workstation
$ keel-publish-mirror --archive-only
keel-publish-mirror: https://archive.keellinux.org trixie verifies
keel-publish-mirror: https://archive.keellinux.org trixie-testing verifies
keel-publish-mirror: https://archive.keellinux.org trixie-security verifies
EXIT=0
$ curl -s https://archive.keellinux.org/dists/trixie/main/binary-amd64/Packages
Package: keel
Version: 0.23.21
```

Both signatures ran over ssh with no terminal and with standard input
from `/dev/null` (decision 0055).

## 3. Upgrade of the CTs

```
$ apt-get update; apt-get install -y keel        # on 9062, then on 9054
  Installed: 0.23.18
  Candidate: 0.23.21
keel	0.23.21
```

After the upgrade, A was the primary with `FIRST 1 (keel)` and B
streamed (`keel|streaming|sync`). The upgrade fenced nothing.

## 4. Case (c) as a prelude, then case (e) without etcd (keel#154)

### (c)

```
$ pct stop 9062                       # A: issued 1792023168.21, returned 1792023172.43
$ keel database promote --old-primary-gone      # on B, at 1792023174.13
this node holds fd1a:bb4c:b407::ffff:1 at epoch 7, on wg0, taken by 0 of 0 peer(s)
database promote: 1 change(s), 0 failed
rc=0 promote end 1792023208.23
$ psql -c "select pg_is_in_recovery()" -c "show synchronous_standby_names"
f
(empty: B commits alone, 0054)
```

### (e)

A writer on A sent INSERTs from the boot, whatever the VIP, with the
default `synchronous_commit` (one write every 0.5 s, 120 s).

```
$ pct start 9062                      # issued 1792023220.21, returned 1792023225.07
```

A's journal (the boot):

```
1792023227.42 systemd: Starting postgresql@17-main.service
1792023227.72 systemd: Finished wg-quick@wg0.service
1792023227.74 systemd: Starting keel-database-follow.service
1792023230.82 systemd: Started postgresql@17-main.service              # as a primary
1792023233.28 keel: vip fd1a:bb4c:b407::ffff:1: epoch 7, held by e59FVo... at fd1a:bb4c:b407::1; this node no longer holds it
1792023234.20 systemd: Stopping postgresql@17-main.service             # the fence restart
1792023237.49 systemd: Started postgresql@17-main.service              # a standby
1792023238.96 keel: database.server.role: vip fd1a:bb4c:b407::ffff:1: took epoch 7, held by e59FVo...
1792023238.96 keel: database.server.role: fenced: the other member holds the VIP and this server held data and took writes ...
1792023238.96 keel: database.server.role: a dump of what this node holds is kept at /var/backups/keel/postgresql/rejoin-20261015T001357Z.sql.zst
1792023238.96 keel: database.server.role: refused: diverged: this node holds transactions the holder at fd1a:bb4c:b407::1 lacks (timeline 3 against the holder's 4)
1792023238.96 keel: database.server.role: database-rejoin: the old primary diverged and stays read only; no alert sent (/etc/keel/monitor.json: secret file not found)
```

The writer:

```
server answers 1792023228.96
noack 8000000 1792023228.97 ... [WARNING:  canceling the wait for synchronous replication and terminating connection due to administrator command]
noack 8000001 1792023234.89 ... [psql: error: connection to server on socket ... failed: No such file]
noack 8000002 .. 8000173 [ERROR:  cannot execute INSERT in a read-only transaction]   # from 1792023235.51
end 1792023347.24
```

The record and the rows:

```
$ cat /var/lib/keel/database/diverged
{"at": "2026-10-15T00:15:54Z", "dump": ".../rejoin-20261015T001357Z.sql.zst", "holder": "fd1a:bb4c:b407::1",
 "holder_system": "7695587285373820964", "holder_timeline": "4",
 "own_system": "7695587285373820964", "own_timeline": "3"}
$ zstdcat rejoin-20261015T001357Z.sql.zst | grep -cP '^80000[0-9]{2}\t'     # on A
1
$ psql -d pairtest -c "select count(*) from t1 where id >= 8000000"         # on B
0
```

Row 8000000 got no ack: its wait was cancelled by the fence restart, so
it was committed on A only. The dump holds it, and B does not.

After the fence, each watch run (1792023291.97, 1792023325.31,
1792023354.79) said "the dump ... is kept" and "refused: diverged".
No watch run started or stopped the server.

| What | 0.23.21, real | 0.23.18, real (2026-10-14) | CI |
| --- | --- | --- | --- |
| A learns the newer claim by itself | yes, in its boot follow | no; only after `keel vip check` by the operator | yes (etcd) |
| The new claim learned, from the server start | 2.5 s | - | - |
| The server writable at boot | 3.4 s (1792023230.82 to 1792023234.20) | 17.4 s, then 6 more windows of about 17 s | - |
| Fenced, dumped, recorded, from `pct start` | 18.8 s (13.9 s from its return) | 9.25 s after `keel vip check` | 8 s and 10 s from the VIP helper start |
| Writes from the boot to the fence | 2 tried, 0 acknowledged; 1 "committed locally" by the stop | 47 tried, 0 acknowledged | 7 and 8 tried, 0 acknowledged |
| Server starts after the fence | 0 | 6 starts and 6 stops | - |

Result: PASS. The boot window of keel#156 still exists (3.4 s here). A
client with `synchronous_commit = local` can get an acknowledged write
in it. This test did not use such a client.

## 5. Case (d), the confirmed reseed (keel#153)

`keel-database-watch.timer` and `keel-database-follow.path` stayed
active. A watch run started at the same second as the apply.

```
$ systemctl is-active keel-database-watch.timer keel-database-follow.path      # on A
active
active
$ keel spec apply --system-only --destroy-local-database      # on A, at 1792023383.57
database.server.role: the dump of what this node holds is kept at .../rejoin-20261015T001357Z.sql.zst (this node took no write since: it is in recovery)
database.server.role: confirmed with --destroy-local-database: what this node holds is discarded (timeline 3 against the holder's 4)
database.server.role: seeded from [fd1a:bb4c:b407::1]:5432 and streaming from it over TLS
apply --system-only: 4 change(s), 0 failed
rc=0 end 1792023393.64
streaming 1792023393.79
$ journalctl --since "-5 min" | grep -c "pid file is invalid"
0
1792023383.57 systemd: Starting keel-database-watch.service
1792023390.09 systemd: Stopping postgresql@17-main.service
1792023390.48 systemd: Stopped postgresql@17-main.service
1792023390.68 systemd: Starting postgresql@17-main.service
1792023393.41 systemd: Started postgresql@17-main.service
$ psql -c "select status, sender_host, slot_name, conninfo ~ 'sslmode=verify-full' from pg_stat_wal_receiver"
streaming|fd1a:bb4c:b407::1|keel|t
$ ls /var/lib/keel/database
follow.lock  replication.secret  semi-sync          # no "diverged"
```

The stop names the cluster's unit. The umbrella `postgresql.service`
does not stop, and the start comes 0.2 s after the stop ended.

On B:

```
1792023406.35 keel: database-sync-commit: the standby acknowledges the primary's commits again; no alert sent
1792023406.42 keel: database watch: a standby streams again; synchronous again: ... (FIRST 1 (keel), reloaded)
$ psql -c "show synchronous_standby_names" -c "select application_name, sync_state from pg_stat_replication"
FIRST 1 (keel)
keel|sync
```

The rows agree: `select count(*), sum(id) from t1` gives
`1627|5782660735` on A and on B.

| What | 0.23.21, real | 0.23.18, real | CI |
| --- | --- | --- | --- |
| The confirmed reseed by the product path | PASS at the first try, 10.1 s | FAIL, 3 of 3 tries | 98 to 129 s (250 ms) |
| The standby streams after the apply | 0.15 s | 0.29 s (with the workaround) | 0.2 to 0.8 s |
| "pid file is invalid" | 0 | 1 per try | - |
| The watch during the reseed | active | stopped by the operator | - |
| `FIRST 1 (keel)` back | 12.6 s after the standby streams | 11.9 s | at once |

Result: PASS.

## 6. Setup from a fresh pair (keel#152)

### Test preparation (not a product step)

Both CTs went back to the state of a new node. The script ran on each
CT:

1. Stop `keel-database-watch.timer` and `keel-database-follow.path`.
2. Keep the spec as `/root/instance.yaml.pre-fresh-20261015`, and
   remove the `database` section from `/etc/keel/instance.yaml`.
3. Stop `postgresql@17-main`. Move the data directory to
   `/var/lib/postgresql/17/main.pre-fresh-20261015`.
4. Remove keel's PostgreSQL files: the drop-ins `98-keel-pair.conf`,
   `99-keel-database.conf`, `99-keel-follow.conf`, `keel-pg_hba.conf`,
   `keel-pg_ident.conf`, `/etc/postgresql/keel-tls`,
   `/etc/sysctl.d/90-keel-database.conf`, `/var/lib/keel/database` and
   `/var/lib/keel/role`.
5. Run `initdb` (UTF8, local peer, host scram-sha-256), start the
   server, and run `CREATE DATABASE root`, as the image has it.
6. Start the 2 units again.

The mesh and the VIP pair stayed. The VIP was on B (epoch 7).

Note: on a new node `/var/lib/keel/database` does not exist, so
`keel-database-watch.service` skips (`ConditionPathExists`) until the
first follow or apply makes it. The watch thus did not fence A from
the spec file alone. The test ran `keel database follow` on A to get
the state of keel#152.

### The reproduction, keel CLI only

X is B (the holder), Y is A.

```
# on A (Y): declare database.server (engine postgresql, role primary), at 1792023476.81
$ keel database follow                                 # on A, at 1792023710.27
database.server.role: fenced: the other member holds the VIP and this server held data and took writes, so it is a standby that follows nobody now ...
database.server.role: refused: the other node of the pair holds no replication credential yet: keel spec apply --system on the primary makes it
$ psql -c "select pg_is_in_recovery()"
t
$ ls /var/lib/keel/role
ls: cannot access '/var/lib/keel/role': No such file or directory

# on B (X): declare database.server (role replica), at 1792023725.97
# on A (Y):
$ keel vip promote                                     # 1792023727.48 to 1792023728.90
released by fd1a:bb4c:b407::1
this node holds fd1a:bb4c:b407::ffff:1 at epoch 8, on wg0, taken by 1 of 1 peer(s)
```

What followed by itself (keel-database-follow.path on both nodes):

```
# A
1792023730.44 keel: database.server.role: promoted with no drain: this node holds the VIP as a fenced standby that follows nobody, and this node never had a role in the pair, so nothing of the pair is lost
1792023731.04 keel: database watch: the database certificate for fd1a:bb4c:b407::fc0a and fd1a:bb4c:b407::ffff:1, signed by the mesh's root, until 2026-11-14
1792023731.04 keel:   unchanged (the primary, writable)
$ psql -c "select pg_is_in_recovery()"
f
# B
1792023729.24 systemd: Stopping postgresql@17-main.service
1792023731.70 keel: database.server.role: fenced: the other member holds the VIP ...
1792023731.70 keel: database.server.role: refused: the other node of the pair holds no replication credential yet ...
```

Then the 2 applies:

```
$ keel spec apply --system-only                        # on A, 1792023748.82 to 1792023754.75
database.server: write .../99-keel-database.conf ... done
database.server: write .../98-keel-pair.conf ... done
database.server: restart the server, which is the only way these take effect (systemctl restart postgresql): done
database.server.replication.allowed_from: ensure the replication slot of the pair exists on the primary ...
database.server.replication.allowed_from: ensure the replication role holds the pair's password ...
apply --system-only: 9 change(s), 0 failed
$ psql: pg_is_in_recovery f; synchronous_standby_names FIRST 1 (keel); slots pg_receivewal_service, keel

$ keel spec apply --system-only                        # on B, 1792023765.50 to 1792023770.38
database.server.role: the dump of what this node holds is kept at .../rejoin-20261015T002237Z.sql.zst
database.server.role: refused: diverged: this node holds transactions the holder at fd1a:bb4c:b407::fc0a lacks (timeline 1 against the holder's 2) ...
apply --system-only: 8 change(s), 1 failed
$ cat /var/lib/keel/database/diverged
{... "holder_system": "7696682057460043118", ..., "own_system": "7696682105477044571", "own_timeline": "1"}

$ keel spec apply --system-only --destroy-local-database      # on B, 1792023770.39 to 1792023776.42
database.server.role: confirmed with --destroy-local-database: what this node holds is discarded (timeline 1 against the holder's 2)
database.server.role: seeded from [fd1a:bb4c:b407::fc0a]:5432 and streaming from it over TLS
apply --system-only: 4 change(s), 0 failed
streaming 1792023776.49
"pid file is invalid" lines: 0
```

The pair works:

```
$ psql -c "select application_name, state, sync_state from pg_stat_replication"      # on A
keel|streaming|sync
$ psql -c "create database freshtest"; psql -d freshtest -c "create table t(v int); insert into t values (1)"
INSERT 0 1                                             # 0.19 s, with runuser and psql
$ psql -d freshtest -c "select count(*) from t"        # on B
1
$ psql -d freshtest -c "insert into t values (2)"      # on B
ERROR:  cannot execute INSERT in a read-only transaction
$ keel diff                                            # on A and on B
exit 0
```

The 2 system identifiers in B's record differ (2 `initdb` runs). Thus
if the VIP had moved back to B before the reseed, B could also have
taken writes (keel#158, rule 2).

| What | 0.23.21 | 0.23.18 |
| --- | --- | --- |
| The fenced VIP holder takes writes | by itself, 1.5 s after `keel vip promote` returned | never; the operator removed `standby.signal` |
| `keel spec apply --system-only` on the holder | 9 changes, 0 failed, 5.9 s | refused, "cannot be drained" |
| The other node | the confirm gate (it holds `root`), seed 6.0 s, streaming 0.07 s later | reseed with the workaround |
| Operator steps outside the keel CLI | 0 | 2 |

Result: PASS.

## 7. Notes

1. **The watch skips on a new node.** `keel-database-watch.service`
   has `ConditionPathExists=/var/lib/keel/database`. That directory
   comes with the first follow or apply. This is safe, but the trap
   "the watch fences from the spec file" of 2026-10-14 needs a node
   that ran keel database code before.
2. **A minor text.** The apply on the holder says "the role is the
   VIP's: primary here (epoch known, held at fd1a:bb4c:b407::1)". The
   address is the other member's, not the holder's. It is only a
   message.
3. **The inithooks ran again at the boot of 9062.** The hostname was
   `keel-postgres-br2` during the boot and `postgresql-br2` after it
   (keel#155, item 6).
4. **pg_receivewal@17-main fails on B** after the reseed: the image's
   `pg_receivewal_service` slot is not on the copy (keel#155, item 5).

## 8. State at the end

| | A, CT 9062 (BR2) | B, CT 9054 (BR1) |
| --- | --- | --- |
| keel | 0.23.21 | 0.23.21 |
| VIP | primary, epoch 8, carried | replica, epoch 8 |
| Server | primary, `FIRST 1 (keel)`, standby `keel` sync | standby, streams over TLS, refuses writes |
| `keel diff` | no drift | no drift |

Left on the CTs:

- `/var/lib/postgresql/17/main.pre-fresh-20261015` on both CTs (the
  data directories before section 6), and the directories
  `main.broken-20261014` and `main.broken2-20261014` of 2026-10-14.
- `/root/instance.yaml.pre-fresh-20261015` on both CTs.
- The dumps under `/var/backups/keel/postgresql/`.
- The test database `freshtest` (1 row).

No defect was patched by hand on a node. No restore step was
necessary.
