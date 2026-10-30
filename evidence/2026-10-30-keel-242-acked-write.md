# keel#242: an acknowledged MariaDB write lost after a primary crash

Date: 2026-10-30
Defect: keel#242. Fix: keel#243, merge `bdecb3b`, keel 0.23.63.
Released: keel 0.23.65 (with keel#240 and keel#241) in `trixie-testing`
only, apt#80, merge `f42bfbf`. `trixie` is not changed (keel 0.23.62).

## Summary

| Item | Result |
| --- | --- |
| Cause | a primary whose server restarted while it held the VIP took writes before its replica connected again; `wait_no_slave = OFF` acknowledged them with no copy |
| Proof of the cause | journal of the failing run: no `binlog_dump` to the replica between the restart and the cut, `read_only = OFF` before the acknowledgement |
| Unit tests | 3 new tests in `tests/test_system_dbfollow.py`: fail on main, pass with the fix |
| CI job `tests / mariadb`, unchanged, on main | 2 of 5 runs lost 1 acknowledged row (CI: runs 452 and 482 also) |
| Same job, forced timing, on main | 3 of 3 runs lost 1 acknowledged row |
| Same job, forced timing, with the fix | 3 of 3 runs: 0 lost |
| Same job, unchanged, with the fix | 10 of 10 runs: 0 lost (2 of them hit the race) |
| Real nodes, 2 BR1 + 1 BR2, netem 250 ms | 11 holder crashes (SIGKILL of mariadbd), 1897 acknowledged writes, 0 lost on either node |
| The test harness | correct: a write counts as acknowledged only when the client exits 0 after the INSERT (autocommit) |

## Where it failed in CI

`tests/test_mariadb_netns.py`, `test_the_unplanned_write_downtime_and_no_acked_row_lost`
(k108) and `test_a_crashed_primary_boots_read_only_and_follows_the_new_one`
(k104):

| Run | Head | Lost row | First acknowledged write after the kill | Promote started |
| --- | --- | --- | --- | --- |
| 452 | main 5587850 | `crash-9` | +3.55 s | +3.96 s |
| 482 | #240 2cdc37e | `crash-6` | +2.39 s | +3.70 s |

In the passing runs (472 to 484) the first acknowledged write after the
kill comes at +23 s to +43 s, when the new primary is writable. In the
failing runs a write was acknowledged before the promote started, so a
server on the old primary took it. k104 then refused A's rejoin:
`this node holds 1 transaction(s) the holder ... lacks (... up to sequence 27)`.

## Reproduction

A Proxmox CT on hw12-br1 (CT 9310, Debian 13, unprivileged, nesting), the
packages of the CI job, MariaDB 11.8.6-0+deb13u1, keel main `7e79af3`,
the job's command: `KEEL_MARIADB_NETNS=1 python3 -m pytest -q -s
tests/test_mariadb_netns.py`. The harness had timing marks only (the
kill's return time, each write's start and end relative to the kill, the
GTID positions of B); the product code was not changed.

| Runs | Code | Lost acknowledged rows |
| --- | --- | --- |
| 5 natural | main | 2 runs (run 2: `crash-7`, run 4: `crash-9`) |
| 3 forced | main | 3 runs (`crash-5` each) |
| 3 forced | fix | 0 |
| 10 natural | fix | 0 |

### Timeline of natural run 2 on main

Journal of the node's units and the writer, times from the SIGKILL:

```
+0.01  systemd: mariadb-keel-A.service: Sent signal SIGKILL to main process 22700
+0.15  B: Slave I/O thread: Failed reading log event, reconnecting to retry
+0.39  B: error reconnecting to master ... retry-time: 2 ... Connection refused
+1.15  systemd: Starting mariadb-keel-A.service       (started by A's follow)
+1.45  mariadbd: ready for connections
+1.36  writer: crash-7 started
+1.98  runuser -u mysql (follow's statement: SET GLOBAL read_only = OFF)
+2.72  writer: crash-7 acknowledged
+3.3   A's VIP helper stopped, A cut off; no "Start semi-sync binlog_dump"
       to B in A's journal between +1.45 and the cut
```

B lacked `0-558875284-27` (A's server id, the row `crash-7`). The VIP
helper's stop took 3.3 s and A kept the VIP during it, so A's follow
started the server (`observe_database(start=...)` when the VIP is on
wg0) and turned it writable at once.

### Forced timing

The harness started A's server and ran A's follow right after the kill,
waited for the first write acknowledged after the kill, then cut A.

| Run | Code | follow returned | First ack after follow | Cut | Lost |
| --- | --- | --- | --- | --- | --- |
| 1 | main | +1.61 s | +0.60 s | +2.22 s | `crash-5` |
| 2 | main | +1.41 s | +0.65 s | +2.06 s | `crash-5` |
| 3 | main | +1.17 s | +0.86 s | +2.03 s | `crash-5` |
| 1 | fix | +7.95 s | +0.82 s | +8.77 s | none |
| 2 | fix | +9.45 s | +2.34 s | +11.79 s | none |
| 3 | fix | +8.47 s | +1.36 s | +9.83 s | none |

With the fix, follow waits until the replica is connected (6 s to 9 s,
the replica's next try and its TLS handshake over 250 ms), so the write
it then acknowledges is on the replica before the cut.

### Natural runs with the fix

10 of 10 passed (11 tests each). In runs 1 and 8 A's server was started
again before the cut (+2.86 s and +2.91 s); the first acknowledged write
after the kill came only from B, at +21.0 s and +22.3 s.

## The fix

`keel/system/dbfollow.py`, `_primary`: on a holder that is read only and
replicates from nobody (its server restarted, or it was fenced), follow
waits until `Rpl_semi_sync_master_clients` is 1 or more and
`Rpl_semi_sync_master_status` is `ON`, for 30 s at most (the
semi-synchronous timeout), then reads the VIP's proof again and stays
read only if the VIP is gone. A promoted replica does not wait.
`docs/replication.md` has the paragraph.

Unit tests (`tests/test_system_dbfollow.py`, `TestThePrimary`):

```
test_a_restarted_holder_takes_no_write_before_its_replica_is_back
test_a_holder_whose_replica_stays_away_takes_writes_after_the_wait
test_a_holder_that_lost_the_vip_while_it_waited_stays_read_only
main: 3 failed; fix: 61 passed (the whole file); database suites: 835 passed
```

CI: keel#243, keel#240 and keel#241 each 13 of 13 green before their
merge (merge commits `bdecb3b`, `2deeb99`, `99c1e85`). The first run of keel#243 (488) had `mesh` and `vip-upgrade`
red in tests that do not import the changed module; filed as keel#245 and
keel#244, `mariadb` passed in that run too.

## Real nodes

The published image `debian-13-keel-mariadb_19.0-10_amd64.tar.zst`
(sha256 `ca5b3844…` on hw12-br1 and nfs1-br2, as the release), keel
0.23.65 installed from the public `trixie-testing` on each CT.

| CT | Host | Name | Overlay | Role |
| --- | --- | --- | --- | --- |
| 9313 | hw12-br1 | k242-w | `fd4a:faa5:2fdb::758b` | etcd member, writer |
| 9314 | hw12-br1 | k242-b | `fd4a:faa5:2fdb::1` | pair, primary at installation |
| 9315 | nfs1-br2 | k242-c | `fd4a:faa5:2fdb::c2ea` | pair, replica at installation |

VIP `fd4a:faa5:2fdb::ffff:1`, `cloud_advanced`, etcd of 3, netem on the
host side of C's veth: `delay 250ms 25ms loss 1.5%`. Set up with keel
commands only (`keel mesh create`, `invite`, `join`, `keel vip pair`,
`keel spec apply --system-only`, `keel vip promote`). Before the rounds:
B `read_only=OFF`, `Rpl_semi_sync_master_clients 1`; C replicating over
TLS; `keel diff` exit 0 with `network.managed_by: host` (keel#238).

A round: `kill -9` of the holder's mariadbd. `mariadb.service` starts it
again after 5 s (`Restart=on-abnormal`). From round 4 a script on the
holder ran `keel database follow` the moment the server answered, which
is the worst case (keel-database-watch.timer runs it every 30 s). The
holder was cut (netem loss 100% on its veth) 0 s to 3 s after
`read_only` went off; the other node took the VIP by the etcd lease;
then the holder was healed and rejoined. A writer on W wrote one row
each 0.1 s through the VIP (connect timeout 3 s, `timeout 15` from round
5); an id counts as acknowledged only when the client returned 0.

| Round | Holder | Cut after OFF | Server up | Replica connected (`binlog_dump`) | follow done | Other node writable | Acked missing |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | C | 0 s | +6.3 s | +11.6 s | (watch) +11.9 s | +45.1 s | 0 |
| 2 | B | 0 s | +5.9 s | +11.6 s | (from the driver) after +15.0 s | +51.5 s | 0 |
| 3 | C | 0.5 s | +6.5 s | +11.9 s | (from the driver) after +13.6 s | no (fenced, see below) | 0 |
| 4 | B | 0 s | +6.2 s | +11.6 s | +12.0 s | +43.8 s | 0 |
| 5 | B | 0 s | +5.8 s | +11.7 s | +12.5 s | +45.8 s | 0 |
| 6 | C | 0 s | +6.5 s | +11.7 s | +12.3 s | +43.0 s | 0 |
| 7 | B | 1 s | +6.2 s | +11.6 s | +12.9 s | +46.7 s | 0 |
| 8 | C | 1 s | +6.5 s | +11.5 s | +12.0 s | +43.3 s | 0 |
| 9 | B | 2 s | +3.9 s | +9.8 s | +10.9 s | +46.2 s | 0 |
| 10 | C | 2 s | +6.2 s | +11.9 s | +12.3 s | +44.8 s | 0 |
| 11 | B | 3 s | +6.3 s | +11.7 s | +12.1 s | +45.2 s | 0 |

Times from the SIGKILL, from the holder's journal and the script's
marks. In every round `read_only` went off after the replica connected:
follow waited 5.6 s to 7.0 s after the server answered. Round 1, journal
of C:

```
16:32:19.916 systemd: mariadb.service: Main process exited, code=killed, status=9/KILL
16:32:26.264 systemd: Started mariadb.service
16:32:31.543 mariadbd: Start semi-sync binlog_dump to slave (server_id: 1339943068)
16:32:31.851 keel: database watch: ... keel database follow
16:32:31.851 keel:   set read_only OFF: this role takes the application's writes
```

After each round the healed node rejoined by itself: `rejoined: no errant
GTID, replicating from ... over TLS`. No reseed was needed.

Final check, every id acknowledged in all rounds against both nodes:

```
acked total 1897
9314: rows 1907, acked missing 0
9315: rows 1907, acked missing 0
gtid_binlog_pos 0-830641549-1911 on both
```

The 10 rows more than the acknowledged ids were committed while their
client gave up (no OK); they are not acknowledged writes.

### What the rounds also showed

- **Round 3, no failover for 15 min.** B had rejoined in round 2 about one
  minute before, and its VIP fence (keel#192) clears only when it proves
  that it applied everything the holder logged. C was cut before B could
  read C's position, so B stayed fenced and did not claim until C was
  healed. This is the fence doing its work, with no row lost; from round
  4 a round starts only after "the VIP fence is cleared" on the other
  node.
- **Rounds of the first attempt are not counted.** A first attempt
  (round 0) ran with broken quoting in the round script, and a first set
  of rounds 5 to 11 ran while the writer hung on one INSERT to a cut node
  (no read timeout in the client), so they checked no new write. The
  writer got `timeout 15` and those rounds were run again; the table has
  only the valid runs.
- **A client of a cut node hangs.** The fence ends the connection on the
  node, but the end does not reach a client across the cut, so the
  client waits for TCP to give up. It gets no OK, so nothing is lost; an
  application needs a read timeout.

## Not done here

- `trixie` still has keel 0.23.62, and the published stable-1 mariadb
  layer 19.0-10 carries it. Promotion and a new layer are the
  maintainer's decision.
- keel#244 (`vip-upgrade`) and keel#245 (`mesh`) are open.

## Clean up

CTs 9310, 9313, 9314 and 9315 are destroyed, the template copies and the
plain Debian template are removed from both hosts, and the local
passwords are deleted.
