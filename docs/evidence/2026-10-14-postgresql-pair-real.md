# Evidence: the PostgreSQL pair of 0054 on real nodes

Date: 2026-10-14, 20:26 to 21:25 UTC.
Decision: 0054 and its amendment of 2026-10-14 (commit alone after
`--old-primary-gone`).
Approval: the maintainer approved this test and the release on
2026-10-14.

Machines:

- Build host: `root@2804:710:d0:5:bb3f:380a:f07b:7951`. The publisher
  checkout is `/var/tmp/keel-testbuild/s3/apt`.
- Workstation: `/tmp/keel-apt-tooling` runs `keel-publish-mirror`.
- Node A: CT 9062 on nfs1-br2 (BR2). Public address
  `2804:7f0:9880:7:72ca:b870:706d:f47b`, overlay `fd1a:bb4c:b407::fc0a`.
- Node B: CT 9054 on hw12-br1 (BR1). Public address
  `2804:710:d0:5:6151:dafe:4c87:337c`, overlay `fd1a:bb4c:b407::1`.
- VIP: `fd1a:bb4c:b407::ffff:1`. The mesh and the VIP pair are the ones
  of `evidence/2026-10-13-step12-pair-br1-br2.md`.

A is the first primary. The task named 9054 as A. The roles changed
before case (a), because of the defect in section 3.

Both CTs are step 12 images (keel-postgresql 19.0-6), PostgreSQL 17.11.
The base RTT between the two regions is 4 ms on the overlay.

Output is trimmed. Times are Unix seconds of the CT clocks. Both hosts
are on NTP (offset under 1 ms). No secret is in this file.

## Summary

| Item | Result | Real (4 ms RTT) | CI (`postgres / trixie`, 250 ms) |
| --- | --- | --- | --- |
| 1. Release keel 0.23.18 | PASS | trixie-testing, then trixie. Signed with nobody at a keyboard. `verify-repo`: exit 0 for both suites. | - |
| 2. Upgrade the CTs | PASS | 0.23.13 to 0.23.18 on both | - |
| 3. Pair setup | FAIL, then PASS after an operator step | keel#152: both servers fenced, no keel command made one writable | - |
| (a) seed, sync commit, write and read, replica refuses | PASS | apply with seed 6.3 s; streams 0.10 s later; write 0.09 to 0.18 s; on B 0.01 to 0.07 s after the ack | 88 to 108 s; 0.5 s; 0.47 to 0.74 s; 0.17 to 0.36 s |
| (b) replica cut off | PASS | commit waited 76.4 s, no fallback; alert 58.4 s after the cut; ack 2.1 s after the heal | alert 13.5 to 20.5 s; ack 20.9 to 22.2 s |
| (c) unplanned failover, 4 ms | PASS | first write 0.83 s after the VIP on B (bound 5 s); 0 of 37 acknowledged ids lost | 1.1 to 1.9 s; none of 15 lost |
| (e) old primary back | FAIL (fence not automatic), PASS after `keel vip check` | keel#154: A did not learn the newer claim; fenced, dumped, recorded, alerted 9.25 s after `keel vip check`; 0 writes acknowledged | 8 s and 10 s from the VIP helper start |
| (d) confirmed reseed | FAIL, then PASS with a workaround | keel#153: 3 tries on 9062 (the copy broke, the apply refused, the copy broke); with the workaround 15.0 s, streams 0.29 s later, `FIRST 1 (keel)` back | 98 to 129 s; 0.2 to 0.8 s |
| (c) under netem, 250 ms | PASS | overlay 230 to 277 ms, 1.75 % loss; write 0.39 s mean; first write 1.47 s after the VIP on A; 0 of 37 acknowledged ids lost | 227 to 229 ms minimum, 3.25 to 5 % loss; 0.47 to 0.74 s; 1.1 to 1.9 s |
| (e) and (d) under netem | (e) as above; (d) FAIL, then PASS | keel#154 again, and 61 writes acknowledged with `synchronous_commit = local` (keel#156); keel#153 again; reseed 83.9 s with the workaround and the watch paused | 98 to 129 s |

Issues opened: Keel-Linux/keel#152, #153, #154, #155, #156.

## 1. Release of keel 0.23.18

keel main at 80fb17e (it includes keel#149).

```
# build host, 20:26:22
$ bin/build-package --native keel main
dpkg-parsechangelog: warning: .../keel/debian/changelog(l72): found start of entry where expected more change data or trailer
build-package: done: keel_0.23.18_amd64.changes in /srv/keel-apt/incoming
$ dpkg-deb -f keel_0.23.18_all.deb Version Depends
Version: 0.23.18
Depends: python3 (>= 3.12), python3-yaml, zstd, gpgv, openssl, python3:any
sha256 0edbbabf9e032a86a6445ef84c60d2e662d9dd5e1db477f6b350b97cad0a0350
```

The changelog warning: the 0.23.18 entry has no trailer line (keel#155,
item 3). The build did not stop.

```
# build host, 20:26:52; ssh with no terminal, standard input /dev/null
$ bin/publish </dev/null
publish: signing subkey 03041024F4B2C0C2F42DDDEA04906EAB77513310 expires on 2028-09-26, in 712 days
publish: signing trixie-testing with subkey 03041024...3310 of AD0964BE3F09DED469A3B6B2148E951314703180
publish: committed in /var/tmp/keel-testbuild/s3/apt: publish trixie-testing: keel 0.23.18
rc=0

$ bin/promote keel=0.23.18 </dev/null          # plan first
would copy from trixie-testing into trixie:
  keel 0.23.18 all (was 0.3.5)
$ bin/promote --yes keel=0.23.18 </dev/null    # 20:27:04
promote: signing trixie with subkey 03041024...3310 of AD0964BE...3180
promoted into trixie: keel
$ git log --oneline -2
95ef0a0 promote trixie: keel 0.23.18
dc1ea80 publish trixie-testing: keel 0.23.18
```

This is the first keel release that was signed with nobody at a
keyboard (decision 0055). The signing ran over ssh with no terminal and
with standard input from `/dev/null`. No passphrase prompt and no agent
question occurred, and each step gave exit 0.

trixie had keel 0.3.5 before. The 5 dependencies of 0.23.18 are Debian
trixie packages, so a machine with trixie only can install it.

```
# workstation, 20:27:08
$ /tmp/keel-apt-tooling/bin/keel-publish-mirror --archive-only
keel-publish-mirror: https://archive.keellinux.org trixie-testing verifies
keel-publish-mirror: https://archive.keellinux.org trixie-security verifies
EXIT=0
```

Verification from outside, with a fresh clone of keel-keys (59edc21)
and the apt verifier on the workstation:

```
$ verify-repo --dist trixie --keyring keys/keel-trixie-main.asc https://archive.keellinux.org
verify-repo: InRelease and Release.gpg: good signatures with .../keel-trixie-main.asc
verify-repo: sha256 of main/binary-amd64/Packages matches Release
keel 0.23.18 all
exit=0
$ verify-repo --dist trixie-testing --keyring keys/keel-trixie-main.asc https://archive.keellinux.org
(same 3 lines)
exit=0
```

## 2. Upgrade of the CTs

```
$ apt-get update; apt-get install -y keel        # on 9054 and on 9062
Unpacking keel (0.23.18) over (0.23.13) ...
Setting up keel (0.23.18) ...
$ dpkg-query -W keel postgresql-17
keel           0.23.18
postgresql-17  17.11-0+deb13u1
```

Both CTs have trixie and trixie-testing, with the pin 990 on
`o=Keel Linux`. The candidate was 0.23.18.

## 3. Pair setup and the first defect (keel#152)

### What the test used

- The mesh and the VIP pair of 2026-10-13 stayed. There are 2 nodes,
  `installation.mode: cloud_simple`, and no etcd. CI uses 3 nodes,
  cloud_advanced and etcd.
- The appliance manifest is the harness stand-in
  `/usr/share/keel/appliances/postgresql.yaml` of 2026-10-13 (dpkg does
  not own it; the image ships no manifest). CI declares
  `appliance.name: core` with the VIP. A spec with `core` also
  validates. The test kept the stand-in, because it declares port 5432
  for the mesh.
- The spec on each node: `database.server` with `engine: postgresql`,
  the role, and `listen: [<own overlay address>, "::1"]`, as CI has it.

### What occurred

1. The package upgrade restarted the watch on 9054. Its spec from
   2026-10-13 still declared `database.server`, and the VIP was on 9062.
   3 s later the watch fenced the server of 9054:

   ```
   20:27:42 keel: database watch: the server does not match the VIP's role; keel database follow
   20:27:42 keel:   fenced: the other member holds the VIP and this server held data and took writes, so it is a standby that follows nobody now
   20:27:42 keel:   refused: the other node of the pair holds no replication credential yet
   ```

2. `keel vip promote` on 9054 moved the VIP to it (epoch 3). Then
   `keel spec apply --system-only` on 9054 refused:

   ```
   database.server.role: refused: the standby receives nothing from its primary, so it cannot be drained: the primary is unreachable. Nothing was changed
   apply --system-only: 10 change(s), 1 failed
   ```

3. The roles were then changed: 9062 is A (primary), 9054 is B. The
   test added `database.server` on 9062 while the VIP was still on
   9054. 25 s later the watch fenced 9062 too (20:31:47). `keel vip
   promote` on 9062 took the VIP (epoch 4). `keel spec apply` and
   `keel database promote` on 9062 both refused with the same
   "cannot be drained" line.

Both servers were standbys that follow nobody. No keel command made a
server writable. Neither fence took a dump or wrote a divergence
record, because the next follow step refused.

Why CI does not see this: the CI cluster is a fresh initdb with no user
database. The real image has a user database `root`, so each new node
"held data and took writes", and the fence condition is true.

Rule learned: do not declare `database.server` on a node while the
other member holds the VIP, unless that node must be fenced and
reseeded.

### The operator step (outside the CLI)

On A (9062, the VIP holder) only, at 20:37:33:

```
$ rm /var/lib/postgresql/17/main/standby.signal; systemctl restart postgresql
$ psql -c "select pg_is_in_recovery(), timeline_id from pg_control_checkpoint()"
f|1
$ keel spec apply --system-only
database.server.replication.allowed_from: ensure the replication slot of the pair exists on the primary: done
database.server.replication.allowed_from: ensure the replication role holds the pair's password: done
apply --system-only: 4 change(s), 0 failed
$ psql: pg_is_in_recovery f; synchronous_standby_names FIRST 1 (keel); synchronous_commit on
  slots: pg_receivewal_service, keel; role repl with REPLICATION
```

This first full apply on 9062 also set the hostname from its spec
(`postgresql-br2`) and registered CrowdSec with its central API.

The slot `pg_receivewal_service` comes from the image. It is inactive
and keeps all WAL from 0/1000000 (keel#155, item 5).

On B (9054), the next watch run (20:37:57) dumped the server and
recorded the divergence:

```
keel:   a dump of what this node holds is kept at /var/backups/keel/postgresql/rejoin-20261014T203756Z.sql.zst
keel:   refused: diverged: this node holds transactions the holder at fd1a:bb4c:b407::fc0a lacks (timeline 1 against the holder's 1)
keel:   database-rejoin: the old primary diverged and stays read only; no alert sent (/etc/keel/monitor.json: secret file not found)
```

Alerts: no node has `/etc/keel/monitor.json`. The watch raises each
alert and writes it to the journal, but it does not send it. This file
counts an alert when the journal has its line.

## 4. Case (a)

The confirmed seed of B, at 20:38:12:

```
$ keel spec apply --system-only --destroy-local-database      # on B
database.server.role: the dump of what this node holds is kept at /var/backups/keel/postgresql/rejoin-20261014T203756Z.sql.zst (this node took no write since: it is in recovery)
database.server.role: confirmed with --destroy-local-database: what this node holds is discarded (timeline 1 against the holder's 1)
database.server.role: seeded from [fd1a:bb4c:b407::fc0a]:5432 and streaming from it over TLS (the pair's slot keeps the primary's WAL while this node is away)
apply --system-only: 4 change(s), 0 failed
took 6.3 s; streaming after 0.10 s
$ psql -c "select status, sender_host, slot_name, conninfo ~ 'sslmode=verify-full' from pg_stat_wal_receiver"
streaming|fd1a:bb4c:b407::fc0a|keel|t
```

On A:

```
$ psql -c "select r.application_name, r.state, r.sync_state, s.ssl, s.version, r.client_addr
           from pg_stat_replication r join pg_stat_ssl s using (pid)"
keel|streaming|sync|t|TLSv1.3|fd1a:bb4c:b407::1
```

The writer is co-located, as in CI. pg_hba.conf keeps the `all` rules
on the loopback by design, so a client on another host cannot write
through the VIP. The test did not change pg_hba.conf. Each write runs
`psql` as `postgres` on the local socket of the node. The write time
includes the start of `runuser` and `psql`.

| Write | Connect and commit on A | Visible on B after the ack |
| --- | --- | --- |
| 1 | 0.094 s | 0.067 s |
| 2 | 0.182 s | 0.013 s |
| 3 | 0.179 s | 0.015 s |

B polled every 20 ms. B refused a write:

```
$ psql -d pairtest -c "insert into t1 values (99,'b')"      # on B
ERROR:  cannot execute INSERT in a read-only transaction       (SQLSTATE 25006)
```

`keel diff` on both nodes: "0 drift" (exit 0).

There is no etcd here, so the CI check "B's etcd member leaf refused"
does not apply.

`keel database status` prints "server: no MariaDB server installed
here" on both nodes, and no PostgreSQL state (keel#155, items 1 and 2).

Result: PASS.

## 5. Case (b), the replica cut off

The cut is on B (9054), inside the CT. It drops all WireGuard packets,
so B loses the overlay in both directions:

```
$ nft -f - <<EOF                                            # on B, at 1792010393.96
table inet keeltest {
  chain in  { type filter hook input  priority -10; udp sport 51820 drop; udp dport 51820 drop; }
  chain out { type filter hook output priority -10; udp sport 51820 drop; udp dport 51820 drop; }
}
EOF
$ psql -d pairtest -c "insert into t1 (id, src) values (10, 'written-during-cut')"   # on A, at 1792010422.44
$ psql -c "select pid, wait_event from pg_stat_activity where wait_event='SyncRep'"
91877|SyncRep
```

A's watch (every 30 s on a machine; 10 s in CI):

```
1792010417.45 keel: database watch: role primary, synchronous commit flowing (was flowing)
1792010452.41 keel: database-sync-commit: the primary's commits wait for the standby; no alert sent (/etc/keel/monitor.json: secret file not found)
1792010452.46 keel: database watch: role primary, synchronous commit waiting (was flowing): no standby streams from it
1792010487.04 keel: database watch: role primary, synchronous commit waiting (was waiting): no standby streams from it
```

The heal, at 1792010496.72: `nft delete table inet keeltest`.

```
id 10 start 1792010422.44 end 1792010498.82 out [INSERT 0 1]
$ psql -c "select application_name, state, sync_state from pg_stat_replication"    # on A
keel|streaming|sync
1792010522.56 keel: database-sync-commit: the standby acknowledges the primary's commits again; no alert sent
1792010522.68 keel: database watch: role primary, synchronous commit flowing (was waiting)
$ psql -d pairtest -c "select id, src from t1 where id=10"     # on B
10|written-during-cut
```

| What | Real | CI |
| --- | --- | --- |
| The cut | 102.8 s | 40 s |
| The commit on A | waited 76.4 s, all the cut; no timeout, no fallback | waits the whole cut |
| A's alert "commits wait" | 58.4 s after the cut | 13.5 to 20.5 s |
| The ack after the heal | 2.1 s | 20.9 to 22.2 s |
| The end alert | 25.8 s after the heal (next watch run) | at the next watch |
| A kept the VIP | yes, epoch 4 | yes |

The alert came later than in CI for 2 reasons. The timer runs every
30 s, and the first run after the cut (23.5 s) still saw the walsender.

Result: PASS.

## 6. Case (c), the unplanned failover (4 ms RTT)

The writer on each node (`/root/writer.sh`) writes only while the node
carries the VIP. It counts a write as acknowledged only when `psql`
gives exactly `INSERT 0 1` and no warning. A write that waits more than
30 s is stopped with SIGKILL, never with a cancel. The loop takes about
0.35 s. The writers send their lines through `pct exec` and ssh to the
workstation, so A's log stays after `pct stop`.

```
$ pct stop 9062                       # A, on nfs1-br2: issued 1792010581.51, returned 1792010586.11
$ keel database promote --old-primary-gone      # B, at 1792010599.59
database.server.role: commits alone: keel database promote --old-primary-gone says the old primary is gone, so this primary takes commits with no standby (synchronous_standby_names empty, reloaded) until a standby streams again
asking the primary, EJIMTpFX... at fd1a:bb4c:b407::fc0a, to release fd1a:bb4c:b407::ffff:1...
the primary at fd1a:bb4c:b407::fc0a did not answer ([fd1a:bb4c:b407::fc0a]:51821 through wg0: timed out); --old-primary-gone: it will drop the VIP when it learns the newer claim
1 peer(s) did not take the claim now; each takes it at its next keel vip check, and routes the VIP to the old primary until then
this node holds fd1a:bb4c:b407::ffff:1 at epoch 5, on wg0, taken by 0 of 0 peer(s)
database promote: 1 change(s), 0 failed
rc=0 promote end 1792010632.61
```

B's writer:

```
vip yes 1792010630.38
noack 2000000 ... [ERROR:  cannot execute INSERT in a read-only transaction ]
recovery f 1792010631.07
ack 2000001 1792010631.07 1792010631.21
ack 2000002 ...
```

| What | Real | CI |
| --- | --- | --- |
| The last ack on A | id 1036 at 1792010583.22 | - |
| `keel database promote --old-primary-gone` on B | 33.0 s | 35.0 to 43.8 s |
| The VIP on B, from the promote start | 30.8 s | - |
| B out of recovery, from the VIP on B | 0.69 s | 0.3 to 1.4 s |
| The first write on B, from the VIP on B | 0.83 s (bound 5 s) | 1.1 to 1.9 s |
| The write downtime, from the last ack on A | 48.0 s; 31.6 s from the promote start | 24.6 to 40.7 s |
| Acknowledged ids on A | 37 (1000 to 1036) | 15 |
| Acknowledged ids missing on B | 0 | none |
| Rows on B that A did not acknowledge | 0 | - |
| B commits alone; its watch alerts | 1792010655.90 and 1792010691.08 (each run) | at each run |
| B's timeline | 2 | 2 |

Why the promote time differs from CI: CI waits for A's etcd lease
(0049). Here there is no etcd. `vipnode.GONE_BOUND` (1.5 s) applies
only with etcd, so each ask of A waits for the members' channel
timeout (about 10 s), 3 times. The downtime from the last ack also
includes 13.5 s of operator time between the stop and the promote.

B's writer made 924 acknowledged writes and 1 refused write (25006,
before the promotion) in 400 s.

Result: PASS.

## 7. Case (e), the old primary back (keel#154)

```
$ pct start 9062                       # issued 1792010701.11, returned 1792010706.99
```

A writer on A tried writes from the boot, whatever the VIP:

```
1792010721.31 systemd: Started postgresql@17-main.service       # as a primary
noack 3000000 ... 1792010729.44 []                               # waited 10 s, SIGKILL
1792010738.72 keel: database.server.role: stopped: this node's claim of fd1a:bb4c:b407::ffff:1 is not proven (the VIP is not on wg0), and a server that is not a standby can only be kept from writes by stopping it
noack 3000001 ... [WARNING:  canceling the wait for synchronous replication and terminating connection due to administrator command]
noack 3000002 .. 3000046 [psql: error: connection to server on socket ... failed: No such file]
```

The boot follow stopped the server 17.4 s after it started. Then A did
not learn B's newer claim. 4 minutes later `keel vip status` on A still
said "role: primary, epoch 4". Each watch run started the server again,
and its follow stopped it about 17 s later: 6 starts and 6 stops. In
each window the server was a writable primary. Its commits waited for
the standby, so none was acknowledged.

Cause: nothing runs `keel vip check` in a pair without etcd.
`keel-vip-check.timer` is static and `PartOf=keel-vip.service`, and
`keel-vip.service` needs `/var/lib/keel/etcd/cluster.json`.

The operator then ran the documented command:

```
$ keel vip check                                   # on A, at 1792010936.52
vip fd1a:bb4c:b407::ffff:1: epoch 5, held by e59FVo... at fd1a:bb4c:b407::1; this node no longer holds it
vip fd1a:bb4c:b407::ffff:1: took epoch 5, held by e59FVo...
1792010941.57 systemd: Stopping postgresql@17-main.service       # the fence restart
1792010945.78 keel: database.server.role: fenced: the other member holds the VIP and this server held data and took writes, so it is a standby that follows nobody now
1792010945.78 keel: database.server.role: a dump of what this node holds is kept at /var/backups/keel/postgresql/rejoin-20261014T204905Z.sql.zst
1792010945.78 keel: database.server.role: refused: diverged: this node holds transactions the holder at fd1a:bb4c:b407::1 lacks (timeline 1 against the holder's 2)
1792010945.78 keel: database.server.role: database-rejoin: the old primary diverged and stays read only; no alert sent
$ cat /var/lib/keel/database/diverged
{"at": "2026-10-14T20:49:06Z", "dump": ".../rejoin-20261014T204905Z.sql.zst", "holder": "fd1a:bb4c:b407::1", "holder_timeline": "2", "own_timeline": "1"}
$ psql -d pairtest -c "insert into t1 values (4000000, 'x')"
ERROR:  cannot execute INSERT in a read-only transaction
```

The dump holds the rows that A did not acknowledge, and B does not
have them:

```
$ zstdcat rejoin-20261014T204905Z.sql.zst | grep -P '^(1036|1037|300000[0-9])\t'
1036  postgresql-br2  ...
1037  postgresql-br2  ...       # in flight at pct stop
3000000  a-after-boot  ...
3000001  a-after-boot  ...      # "committed locally" by the stop
$ psql -d pairtest -c "select id from t1 where id in (1037, 3000000, 3000001)"     # on B
(0 rows)
```

2 watch runs later (1792010973.65 and 1792011006.57): 1 dump file and
1 "database-rejoin" alert.

| What | Real | CI |
| --- | --- | --- |
| A's boot follow | the server stopped, 17.4 s after its start | the server stopped |
| A learns the newer claim by itself | no (keel#154) | yes |
| Fenced, dumped, recorded, alerted | 9.25 s after `keel vip check` | 8 s and 10 s from the VIP helper start |
| Writes on A from its boot to the fence | 47 tried, 0 acknowledged; 1 "committed locally" | 7 and 8 tried, 0 acknowledged; 3 "committed locally" |
| The dump; the alert | holds A's unacknowledged rows; 1 dump and 1 alert after 2 more runs | the same |

Result: FAIL for the automatic fence (keel#154). PASS for the fence,
the dump, the record, the alert and the refusal after `keel vip check`.

## 8. Case (d), the confirmed reseed (keel#153)

### Try 1, on the fenced old primary

```
$ keel spec apply --system-only --destroy-local-database     # on A, at 1792011048.61
database.server.role: confirmed with --destroy-local-database: what this node holds is discarded (timeline 1 against the holder's 2)
database.server.role: refused: the copy of [fd1a:bb4c:b407::1]:5432 is in place and its walreceiver does not stream after 60 s
apply --system-only: 3 change(s), 1 failed                   # 69.3 s
```

The journal and the server log:

```
1792011055.165 systemd: Stopping postgresql@17-main.service
1792011055.468 postgresql@17-main: Error: pid file is invalid, please manually kill the stale server process.
20:50:55.479 [3218] LOG:  received smart shutdown request
20:50:55.479 [3218] LOG:  could not open file "postmaster.pid": No such file or directory
20:50:55.567 [3218] LOG:  database system is shut down
20:50:55.928 [3633] LOG:  starting backup recovery with redo LSN 0/4000028, checkpoint LSN 0/4000080, on timeline ID 2
20:50:55.928 [3633] FATAL:  requested timeline 2 does not contain minimum recovery point 0/34388D0 on timeline 1
$ pg_controldata /var/lib/postgresql/17/main
Database cluster state:               shut down in recovery
pg_control last modified:             Wed 14 Oct 2026 08:50:55 PM UTC
Latest checkpoint's TimeLineID:       1
Minimum recovery ending location:     0/34388D0
```

`backup_label` is B's copy (timeline 2), but `pg_control` is the old
server's. After this, every watch run started the server, and it
stopped again with the same FATAL.

### Try 2

`keel spec apply --system-only --destroy-local-database` refused: "the
server is not answering ... its configuration was not written and
nothing was restarted". No keel command could reseed the node.

### Operator step, and try 3

The broken directory went to
`/var/lib/postgresql/17/main.broken-20261014`. An empty cluster
(`initdb`) took its place, and `systemctl start postgresql` started it.
Then the confirmed reseed ran again (1792011591.54, 127.9 s) and failed
the same way:

```
20:59:58 systemd: Stopped postgresql.service - PostgreSQL RDBMS.
20:59:58 systemd: Stopping postgresql@17-main.service - PostgreSQL Cluster 17-main...
20:59:58 postgresql@17-main: Error: pid file is invalid, please manually kill the stale server process.
FATAL:  database system identifier differs between the primary and standby
```

Inferred cause (not proven in the code): keel stops the umbrella unit
`postgresql`. `postgresql@17-main` is `PartOf=` and `Before=` it, so
systemd stops the umbrella first, and `systemctl stop postgresql`
returns before the cluster stops. keel then moves the new copy in under
the running server, and the old server writes its `pg_control` into the
new copy. The reseed of B in case (a) worked with the same code.

### Try 4, with the workaround

The second broken directory went to
`/var/lib/postgresql/17/main.broken2-20261014`, and a new empty cluster
took its place. The product reads the unit name from the environment
variable `KEEL_POSTGRES_SERVICE` (the CI harness sets it):

```
$ KEEL_POSTGRES_SERVICE=postgresql@17-main keel spec apply --system-only --destroy-local-database   # 1792011802.85
database.server.role: seeded from [fd1a:bb4c:b407::1]:5432 and streaming from it over TLS
apply --system-only: 4 change(s), 0 failed                  # 15.0 s
streaming at 1792011818.15                                  # 0.29 s after the apply
"pid file is invalid" lines: 0
$ ls /var/lib/keel/database
follow.lock  replication.secret  semi-sync                   # no "diverged"
```

On B:

```
1792011829.99 keel: database-sync-commit: the standby acknowledges the primary's commits again; no alert sent
1792011830.05 keel: database watch: a standby streams again; synchronous again: a standby streams, so the pair's line is back (FIRST 1 (keel), reloaded) and each commit waits for it (0054)
$ psql -c "show synchronous_standby_names" -c "select application_name, sync_state from pg_stat_replication"
FIRST 1 (keel)
keel|sync
```

The rows agree: `select count(*), sum(id) from t1` gives
`965|1848465032` on A and on B. A refuses a write (25006). A streams
with `sslmode=verify-full` on the slot `keel`.

| What | Real | CI |
| --- | --- | --- |
| The confirmed reseed of the diverged node | FAIL, 3 tries (keel#153) | 98 to 129 s |
| The reseed with `KEEL_POSTGRES_SERVICE=postgresql@17-main` | 15.0 s | - |
| A streams after the apply | 0.29 s | 0.2 to 0.8 s |
| `FIRST 1 (keel)` back on B, the end alert | 11.9 s after A streams (next watch run) | at once |
| The rows of A and B | equal | equal |

Result: FAIL for the product path (keel#153). PASS with the workaround.

## 9. Case (c) under netem, with (e) and (d)

tc netem can give the design case. `sch_netem` was not loaded on the
hosts, and an unprivileged CT cannot load it, so the test loaded it on
both hosts (`modprobe sch_netem`) and removed it at the end. The qdisc
is on `eth0` in each CT, half of the delay on each side:

```
$ tc qdisc add dev eth0 root netem delay 125ms 12ms loss 1%      # in 9062 and in 9054
$ ping6 -c 100 -i 0.2 -q fd1a:bb4c:b407::1                       # on 9062, over the overlay
rtt min/avg/max/mdev = 233.915/255.438/277.377/9.086 ms, 0% packet loss
$ ping6 -c 400 -i 0.05 -q fd1a:bb4c:b407::1
rtt min/avg/max/mdev = 230.505/253.399/276.332/9.930 ms, 1.75% packet loss
```

The roles were the opposite of section 6: 9054 was the primary, and
9062 was its synchronous standby. The test stopped 9054 and promoted
9062.

```
$ pct stop 9054                      # issued 1792012121.21, returned 1792012124.73
$ keel database promote --old-primary-gone      # on 9062, at 1792012126.66
the primary at fd1a:bb4c:b407::1 did not answer ([fd1a:bb4c:b407::1]:51821 through wg0: timed out); --old-primary-gone: it will drop the VIP when it learns the newer claim
this node holds fd1a:bb4c:b407::ffff:1 at epoch 6, on wg0, taken by 0 of 0 peer(s)
database promote: 1 change(s), 0 failed
rc=0 promote end 1792012160.23
# the writer on 9062
vip yes 1792012157.79
noack 6000000 ... [ERROR:  cannot execute INSERT in a read-only transaction ]
ack 6000001 1792012158.74 1792012159.26
```

| What | Real, netem | Real, 4 ms | CI |
| --- | --- | --- | --- |
| A write on the primary: connect and the synchronous commit | 0.39 s mean (0.32 to 0.71 s) | 0.19 s mean (0.07 to 0.36 s) | 0.47 to 0.74 s |
| `keel database promote --old-primary-gone` | 33.6 s | 33.0 s | 35.0 to 43.8 s |
| The VIP on the new primary, from the promote start | 31.1 s | 30.8 s | - |
| The first write, from the VIP on the new primary | 1.47 s (bound 5 s) | 0.83 s | 1.1 to 1.9 s |
| The write downtime, from the last ack on the old primary | 37.2 s; 32.6 s from the promote start | 48.0 s; 31.6 s | 24.6 to 40.7 s |
| Acknowledged ids on the old primary; missing on the new primary | 37; 0 | 37; 0 | 15; none |
| The new primary commits alone; its watch alerts | at each run (4 runs, 1792012192 to 1792012298) | at each run | at each run |

Id 5000037 is on the new primary, but its client got no ack. The
standby flushed it, and the old primary stopped before it answered.
This is correct for a synchronous commit.

After `--old-primary-gone`, the new primary commits alone. Thus netem
changes only the commit cost before the stop and the seed time. The
promote time does not change, because it is 3 timeouts of the members'
channel (section 6).

Result: PASS.

### (e) under netem

```
$ pct start 9054; pct exec 9054 -- tc qdisc add dev eth0 root netem delay 125ms 12ms loss 1%
                                    # started 1792012196.89, netem at 1792012198.43
```

This time the writer on 9054 sent `SET synchronous_commit = local`
before each INSERT:

```
server answers 1792012201.05
ack 7000000 1792012201.06 1792012201.46
...
ack 7000074 ... 1792012244.77            # 61 acknowledged in 45 s
1792012218.25 keel: database.server.role: stopped: this node's claim of fd1a:bb4c:b407::ffff:1 is not proven
1792012226.03 systemd: Starting postgresql@17-main.service    # the watch starts it again (keel#154)
$ keel vip status                        # at 1792012256
  role: primary
  epoch 5, held by e59FVo... at fd1a:bb4c:b407::1
$ keel vip check                         # at 1792012269.56
vip fd1a:bb4c:b407::ffff:1: took epoch 6, held by EJIMTpFX...
1792012281.21 keel: database.server.role: fenced: ...
1792012281.21 keel: database.server.role: a dump of what this node holds is kept at /var/backups/keel/postgresql/rejoin-20261014T211119Z.sql.zst
1792012281.21 keel: database.server.role: refused: diverged: ... (timeline 2 against the holder's 3)
$ zstdcat rejoin-20261014T211119Z.sql.zst | grep -cP '^70000[0-9]{2}\t'
61
```

A client that sets `synchronous_commit = local` gets acknowledged
writes on a returned old primary until the fence. The fence put all 61
rows in the dump, and the new primary does not have them. With the
default client settings, 0 writes were acknowledged (section 7).

The 61 writes came in 2 kinds of window:

- 29 in the boot window (from the boot to 1792012218.25, when the boot
  follow stopped the server). This window is in the design of case (e),
  with etcd and in CI too: keel#156.
- 32 after the watch started the server again (1792012226): keel#154.

Fenced, dumped, recorded and alerted 11.65 s after `keel vip check`.

### (d) under netem

```
$ keel spec apply --system-only --destroy-local-database        # on 9054, at 1792012292.83
database.server.role: refused: the copy of [fd1a:bb4c:b407::fc0a]:5432 is in place and its walreceiver does not stream after 60 s
apply --system-only: 3 change(s), 1 failed                       # 134.2 s
21:12:45 systemd: Stopped postgresql.service - PostgreSQL RDBMS.
21:12:45 systemd: Stopping postgresql@17-main.service - PostgreSQL Cluster 17-main...
21:12:45 postgresql@17-main: Error: pid file is invalid, please manually kill the stale server process.
FATAL:  requested timeline 3 does not contain minimum recovery point 0/9013040 on timeline 2
```

This is the third occurrence of keel#153, on the other node. Then the
operator step of section 8 (move aside, `initdb`, start) and the
workaround failed 1 more time. The watch's own follow seeded the empty
cluster at the same time, with the umbrella stop ("pid file is
invalid" at 1792012546.58, then "database system identifier differs").
The reseed worked with the 2 watch units stopped while it ran:

```
$ systemctl stop keel-database-watch.timer keel-database-follow.path
$ (move aside, initdb, systemctl start postgresql)
$ KEEL_POSTGRES_SERVICE=postgresql@17-main keel spec apply --system-only --destroy-local-database   # 1792012724.12
database.server.role: seeded from [fd1a:bb4c:b407::fc0a]:5432 and streaming from it over TLS
apply --system-only: 4 change(s), 0 failed                      # 83.9 s
streaming at 1792012808.15                                      # 0.16 s after
$ systemctl start keel-database-follow.path keel-database-watch.timer
# on 9062
1792012818.25 keel: database watch: a standby streams again; synchronous again: ... (FIRST 1 (keel), reloaded)
$ psql -c "show synchronous_standby_names" -c "select application_name, sync_state from pg_stat_replication"
FIRST 1 (keel)
keel|sync
```

The rows agree: `1627|5782660735` on both nodes. 9054 refuses a write
(25006).

| What | Real, netem | CI |
| --- | --- | --- |
| The confirmed reseed by the product path | FAIL (keel#153) | 98 to 129 s |
| The reseed with the workaround, the watch paused | 83.9 s | - |
| The standby streams after the apply | 0.16 s | 0.2 to 0.8 s |
| `FIRST 1 (keel)` back, the end alert | 10.1 s after the standby streams | at once |

## 10. Traps

1. **The watch fences from the spec file (keel#152).** It does not wait
   for an apply. Declare `database.server` only on the node that holds
   the VIP, or on a node that you will reseed.
2. **A new real node holds data.** The image has the user database
   `root`, so the fence and the confirm gate apply to every new node.
   CI does not see this.
3. **Applications stay on the loopback.** A client on another host
   cannot write through the VIP, by design. Tests must use a writer on
   the node that carries the VIP.
4. **The loopback asks for a password.** `psql -h ::1` as `postgres`
   asks for one (scram-sha-256). The test used the local socket (peer).
5. **The watch runs every 30 s on a machine, 10 s in CI.** Cut for at
   least 90 s, and expect alerts later than the CI numbers.
6. **No etcd, no `keel vip check` (keel#154).** Run `keel vip check` on
   the old primary after its boot.
7. **The reseed stops the umbrella unit (keel#153).** On Debian, set
   `KEEL_POSTGRES_SERVICE=postgresql@17-main` until this is fixed.
8. **`$$` in a shell string.** The PID replaces it. Write a SQL text
   with `$$` quotes only in a file or in a quoted here-document.
9. **`bash -c` through `pct exec` on nfs1-br2.** A quoting error gave
   an interactive shell, and confconsole started on it. Send the script
   on standard input (`pct exec <ct> -- bash -s`).
10. **A reboot of 9062 ran the first-boot inithooks again.** The SSH
    host keys and the root password changed (keel#155, item 6). The
    test reached the CTs only through `pct exec`.
11. **No alert channel.** No node has `/etc/keel/monitor.json`, so the
    watch raises alerts but does not send them.
12. **`sch_netem` is not loaded on the hosts.** An unprivileged CT
    cannot load it.
13. **The watch runs its own seed.** On an empty cluster with a
    divergence record, the watch's follow seeds the node by itself, with
    the umbrella stop. Stop `keel-database-watch.timer` and
    `keel-database-follow.path` during a manual recovery.
14. **A reboot of 9054 also ran the first-boot inithooks.** Its
    hostname is `postgres` now, but its spec says `postgresql`.
    `keel diff` does not compare it ("5 not compared").

## 11. State at the end

The pair works. A (9062) is the primary and B (9054) is its
synchronous standby:

| | A, CT 9062 (BR2) | B, CT 9054 (BR1) |
| --- | --- | --- |
| keel | 0.23.18 | 0.23.18 |
| VIP | primary, epoch 6, carried | replica, epoch 6 |
| Server | primary, `FIRST 1 (keel)`, standby `keel` sync | standby, streams over TLS, refuses writes |
| `keel diff` | no drift | no drift |
| netem | removed | removed |
| Hostname | `postgresql-br2` (from its spec) | `postgres` (from the inithooks run at boot; the spec says `postgresql`) |
| `passwd -S root` after the inithooks run | L (locked) | P |

The hosts: `sch_netem` unloaded on both. No nft table and no qdisc
remain. No other CT or VM was changed.

Left on the CTs for the investigation of keel#152 to #156:

- `/var/lib/postgresql/17/main.broken-20261014` and
  `main.broken2-20261014` on both CTs (15 MB each on A, 54 MB each on
  B): the broken copies of keel#153.
- `/var/backups/keel/postgresql/rejoin-*.sql.zst`: the dumps of the
  fences (1 on A, 2 on B).
- `/root/instance.yaml.pre-20261014` (the specs before this test),
  `/root/writer.sh`, and on A `/root/one-commit.sh` and
  `/root/b-commit.log`.
- The test database `pairtest` (table `t1`), 1627 rows.
- The stand-in manifest `/usr/share/keel/appliances/postgresql.yaml`
  of 2026-10-13.
- No `/etc/keel/monitor.json`: alerts stay in the journal.
