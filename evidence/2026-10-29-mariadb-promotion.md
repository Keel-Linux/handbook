# keel-mariadb 0.1.1 release test before the promotion to trixie (2026-10-29)

Date: 2026-10-29. The time zone is UTC. The maintainer approved the
path: (1) a release test of keel-mariadb 0.1.1 from `trixie-testing`,
(2) the promotion to `trixie`, (3) the mariadb layer on the stable-1
Core with `keel-release --no-index` (decision 0072).

No secret is in this file. Output is trimmed.

## Result

**FAIL. keel-mariadb is not promoted, and no layer is built or
published.**

| Part | Result |
| --- | --- |
| What keel-mariadb 0.1.1 promises (first boot, password, socket units, bind, the pair) | PASS |
| Data: acknowledged writes lost, in all rounds | 0 |
| Failover time for a client on a mesh node outside the pair | FAIL: about 10 s too long, keel#235 |
| The tested image is the stable-1 layer | NO: it is the CI build of the testing track (see "Image") |

Two things stop step 2:

1. **keel#235.** When the holder dies, the new holder tells the peers of
   its claim one at a time, and the dead old holder is first. That
   exchange waits 10 s for its timeout before the next peer hears of the
   claim. A node outside the pair (the witness here, an application node
   in production) routes the VIP to the dead node for that time. The
   layer would ship this, because it carries keel 0.23.61.
2. **The image is not the release image.** The layer to publish is built
   on the stable-1 Core (`1c5dc3b1`) from the pool `stable-1`. This test
   used the CI build of the testing track. So this run supports the
   package keel-mariadb 0.1.1 only. Step 3 needs its own run on the staged
   `--no-index` layer.

## Image

The CI build of `/srv/keel-ci/testing/20261029T164132Z` on the build
host. It has the same Keel packages as the planned layer.

| Item | Value |
| --- | --- |
| File | `debian-13-keel-mariadb_19.0-10_amd64.tar.zst`, copied as `..._19.0-10+ci20261029_...` |
| sha512 | `deec7e2edc479fc6e11701736081c4e17669a001ea7c9e1427b0bc4c7ffd7042ba6261d75be9e4ae7d6c64b788ccd12ec5082988248cc7631ba8d12fdeb3f691` (the same on the build host, BR1 and BR2) |
| Layer manifest | parent core `5a5ee466…` (testing Core, not stable-1 `1c5dc3b1…`), pool `2026-10-08`, keel-mariadb commit `864d7a4`, common `38cb871` |
| Packages | keel 0.23.61, keel-mariadb 0.1.1, keel-core 0.1.3, mariadb-server 1:11.8.6-0+deb13u1 |

## Topology

| CT | Host | Name | Overlay | Role |
| --- | --- | --- | --- | --- |
| 9310 | hw12-br1 | `mdbr-w` | `fde8:a481:26be::79f7` | witness, etcd member |
| 9311 | hw12-br1 | `mdbr-b` | `fde8:a481:26be::1` | pair, primary at installation |
| 9312 | nfs1-br2 | `mdbr-c` | `fde8:a481:26be::d1e1` | pair, replica at installation |

VIP `fde8:a481:26be::ffff:1`. `installation.mode: cloud_advanced`,
etcd of 3. CTs: unprivileged, `nesting=1`, 8 GB, 2 GB memory, 2 cores,
the BR1 and BR2 network patterns of earlier tests. The preseed
`/etc/inithooks.conf` (ROOT_PASS, DB_PASS, skips) was written on the
mounted rootfs, owned by the CT's root.

netem on the host side of the veth of C: `delay 250ms 25ms loss 1.5%`.
Overlay ping W to C: 232.6 / 257.2 / 283.0 ms (min / avg / max), 0 of 30
lost. W to B: 0.2 / 1.0 / 2.0 ms.

## First boot (headless, all 3 CTs)

| Check | Result |
| --- | --- |
| Inithooks | `[35mysqlpass] successfully completed`, `Inithooks run completed` |
| Failed units | none |
| The admin account | `mariadb -uadmin` with the declared DB_PASS: `11.8.6-MariaDB-0+deb13u1` |
| Socket units | `mariadb.socket` masked (keel-mariadb#29) |
| 3306 before the pair | `127.0.0.1` and `[::1]` only |
| The preseed after first boot | `/etc/inithooks.conf` emptied by `98finalize` (1 byte, root, 0600) |

## The pair

Sequence: `keel mesh create` (B), `keel mesh invite` and `join` (W, then
C), `keel vip pair` on B and on C, `keel spec apply --system-only` on B,
`keel vip promote` on B, `keel spec apply --system-only` on C.

```
[B] created the mesh: this node is fde8:a481:26be::1/64 on wg0
[C] etcd: this node forms with 2 other member(s)
[B] fde8:a481:26be::ffff:1 is the VIP of <B> and <C>, signed by both
[B] 99-keel-database.cnf: a paired node, server id 1796400172, binary log, GTID strict,
    semi-synchronous replication, TLS, the VIP fde8:a481:26be::ffff:1 bound
[B] apply --system-only: 10 change(s), 0 failed
[B] bind-address = fde8:a481:26be::1,::1,fde8:a481:26be::ffff:1
[C] replicating from: [fde8:a481:26be::1]:3306; IO Yes, SQL Yes; lag 0; TLS Yes
[C] root INSERT -> ERROR 1290 (read only)
[B] semi-synchronous: master ON, 1 replica(s) acknowledging
```

The bind has the overlay address, so the fix of keel#233 (keel#234) is
in 0.23.61.

## Rounds

A writer on W writes one row each 0.1 s through the VIP, with a 3 s
connect timeout. An id counts as acknowledged only when the client
returned 0. After each round, every acknowledged id was looked up on
both pair nodes.

| Round | Action (netem on C) | VIP move | Longest gap between acks | Acks | Acked ids missing |
| --- | --- | --- | --- | --- | --- |
| 1 | planned: `keel vip promote` on C (BR2) | epoch 2, promote 6.6 s | 4.61 s | 91 | 0 on B, 0 on C |
| 2 | planned failback: `keel vip promote` on B | epoch 3, promote 4.0 s | 2.76 s | 101 (5 refused) | 0 on B, 0 on C |
| 3 | `systemctl restart keel-vip.service` on holder B | VIP on wg0 at every 1 s sample | 0.89 s | 71 (0 errors) | 0 |
| 4 | `pct stop` of holder B, also the etcd leader | claim on C +37.1 s, C writable +38.8 s | 48.5 s | 60 | 0 on C, 0 on B after it rejoined |
| 5 | `pct stop` of holder B, etcd follower | claim on C +24.2 s, C writable +25.6 s | 36.0 s | 96 (12 errors) | 0 on C, 0 on B after it rejoined |

The first run of round 5 is void. A background loop kept the
`pct exec` session open, so the writer and the watcher ended before the
stop. That run still gives one number: with no writer, B claimed the
VIP 22.3 s after C stopped and took writes at 29.2 s.

After round 4 and round 5, B started again and said:

```
rejoined: no errant GTID, replicating from [fde8:a481:26be::d1e1]:3306 over TLS from 0-1796400172-336
rejoined: no errant GTID, replicating from [fde8:a481:26be::d1e1]:3306 over TLS from 0-1796400172-458
```

No reseed was necessary.

### The time after the claim (keel#235)

Round 5, times after the stop:

```
+24.2 mdbr-c vip ...ffff:1: claimed at epoch 6: the lease of epoch 5 is gone (expired at its due time ...)
+25.6 C writable
+34.2 mdbr-c vip ...ffff:1: fde8:a481:26be::1 did not take the claim: [fde8:a481:26be::1]:51821 through wg0: timed out
+35.9 mdbr-w keel: vip ...ffff:1: epoch 6, held by <C> at fde8:a481:26be::d1e1
+36.4 W routes the VIP to C (wg allowed-ips, sampled every 0.5 s)
+37.6 the first write from W is acknowledged
```

Round 4 shows the same: claim +37.1, timeout of the dead peer +47.1, W
learns +47.8, first write from W +50.1. The cause is `announce` in
`keel/mesh/vipetcd.py`. It sends the claim to each peer in turn. The
release tests before this one wrote on the pair nodes only, so they did
not see it.

### Round 4: the stopped holder was the etcd leader

etcd on W: `lost leader` at +6.8 s, W `became leader at term 3` at
+7.35 s. etcd gives every lease its full TTL again on a leader change.
The claim came at +37.1 s, about 30 s after the election, and round 5
(no leader change) claimed at +24.2 s. docs/vip.md says "25 s when the
majority elects a new leader". That figure does not count the time
before the new leader exists (about 7 s here). This is the design of
etcd leases and not a defect. The text of docs/vip.md can say it more
exactly.

## End state

| Check | W | B | C |
| --- | --- | --- | --- |
| `keel mesh upgrade-check` | other members healthy | other members healthy | holds the VIP, "upgrade it last" |
| Rows in `pairtest.t` | | 495, sum of ids 1592781 | 495, sum of ids 1592781 |
| `gtid_binlog_state` | | `0-1796400172-458,0-1383356428-499` | the same |
| 3306 listeners | loopback | own overlay, `::1`, VIP | own overlay, `::1`, VIP |
| `keel diff` | exit 14 | exit 14 | exit 14 |

The one drift on each node is `network.managed_by: drift (declared host,
observed file)`. The spec of this test declared `host`. The CI image has
no LXC marker (`/var/lib/turnkey-info/inithooks.service/lxc`), so
`keel inspect` reads `file`. Earlier release tests on released templates
got `keel diff` exit 0. This is a second difference between the CI build
and a release image. A test of the staged layer must check it.

Ports, probed with a TCP connect:

| From | To | Open | Closed |
| --- | --- | --- | --- |
| workstation | public address of B | 22, 12321 | 3306, 2379, 2380, 51821 |
| workstation | public address of C | 22 | 3306, 2379, 2380, 51821, 12321 (the upstream filter of BR2) |
| W | public addresses of B and C | | 3306, 2379, 2380, 51821 |
| W | overlay addresses of B and C | 3306, 2379, 2380, 51821 | |
| W | VIP | 3306 | 2379, 2380, 51821 |

The database port is not on the uplink. The nodes have no `inet keel`
table, which the LNMP 19.0-4 test had. The ports are closed because of
the bind addresses only.

## What a rerun needs

1. A fix of keel#235 in a keel release, published to `trixie-testing`
   and promoted to `trixie`.
2. keel 0.23.61 or later in the pool `stable-1`.
3. The mariadb layer built with `keel-release --no-index` on the stable-1
   Core, and this test run on the staged layer: the same rounds, with
   `keel diff` exit 0 and a writer on a node outside the pair.
4. Then the promotion of keel-mariadb to `trixie`, and the publish with
   `--no-channels`, with `aplinfo.dat` the same before and after.

## Clean up

CTs 9310, 9311 (BR1) and 9312 (BR2) are destroyed. The template copies
`debian-13-keel-mariadb_19.0-10+ci20261029_amd64.tar.zst` are removed
from BR1 and BR2. The netem qdisc went with CT 9312.
