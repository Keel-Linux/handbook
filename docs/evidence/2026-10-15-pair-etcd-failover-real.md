# Evidence: automatic failover of the PostgreSQL pair with etcd, on real nodes

Date: 2026-10-15, from 18:04 UTC.
Decisions: 0054 (amendments of 2026-10-14 and 2026-10-15), 0049
(amendment of 2026-10-15), 0057.
keel: 0.23.27, with Keel-Linux/keel#170 to #175 (keel#165, #169, #166,
#164, #167 and #168, #156).

Machines, as in `docs/evidence/2026-10-15-br3-thin-etcd-witness.md`:

| Site | Host | CT | Role | Overlay |
| --- | --- | --- | --- | --- |
| BR1 | hw12-br1 | 9054 | PostgreSQL pair node | `fd1a:bb4c:b407::1` |
| BR2 | nfs1-br2 | 9062 | PostgreSQL pair node | `fd1a:bb4c:b407::fc0a` |
| BR3 | BR3-THIN | 9071 | etcd witness, no role | `fd1a:bb4c:b407::a237` |

The VIP is `fd1a:bb4c:b407::ffff:1`. No other CT was changed. No
secret is in this file. Times are Unix seconds of the CT clocks; in the
tables, `7464.79` means `1792087464.79`.

## Pass criteria, written before the run

Each item passes only with the keel CLI and no operator step. The test
changes only the network (nft, tc) and the power (`pct stop`, `pct
start`) of a CT, as a fault does. The confirmed reseed (`keel spec apply
--system-only --destroy-local-database`) is the product path of case
(d), and it counts as a keel CLI step. A planned `keel database promote`
is not used (keel#163).

| Item | Passes when |
| --- | --- |
| Upgrade | the 3 CTs run the new keel; `keel-database-follow.path` active on both pair nodes; the fence of 9062 cleared by the watch (keel#166) |
| Cut of BR3 (witness) | the VIP stays on the holder (no drop); writes go on |
| Cut of the standby site | the VIP stays on the holder; writes wait (0054, by design) and resume after the heal; the server of the holder is not stopped |
| (c) cut of the primary site | the VIP moves by itself; the first write is acknowledged at most 5 s after the VIP lands on the new primary; 0 acknowledged ids lost |
| (e) heal of the old primary | it takes no write; its server starts as a standby, never as a primary (keel#156); fenced, dumped, recorded |
| (d) reseed | streams again; `FIRST 1 (keel)` back; the VIP fence cleared within 2 watch runs |
| 2 failovers in a row | the 2nd cut of the primary also moves the VIP by itself, within the same bounds |
| (e) boot | after `pct stop` of the primary and `pct start`, the start of its server at boot is refused or fenced; 0 writes acknowledged on it |
| Follow path | active on both nodes during and after the test |
| End | a working pair, netem removed, the test nft table removed |

The VIP drop of keel#167 on a cut of the leader's site fails the witness
and standby items. A cut of the standby where writes wait is 0054's
design, not a failure. If any item fails, keel stays in trixie-testing.

## 1. Release and upgrade: keel 0.23.27

```
# build host, 18:03 UTC, /srv/keel-apt/apt after git pull --ff-only (03c30c6)
$ bin/build-package --native keel main </dev/null
build-package: done: keel_0.23.27_amd64.changes in /srv/keel-apt/incoming
$ dpkg-deb -f keel_0.23.27_all.deb Version
0.23.27
sha256 5bb2363b2b729d417cd2b5cfb4f0830e414280cea78b6f5220b9bbfe1aac11ff
./usr/lib/systemd/system/postgresql@.service.d/keel-guard.conf
$ bin/publish </dev/null
publish: signing trixie-testing with subkey 03041024F4B2C0C2F42DDDEA04906EAB77513310 of AD0964BE3F09DED469A3B6B2148E951314703180
publish: committed in /srv/keel-apt/apt: publish trixie-testing: keel 0.23.27
# workstation
$ keel-publish-mirror --archive-only
keel-publish-mirror: https://archive.keellinux.org trixie-testing verifies
EXIT=0
```

The signature ran over ssh with standard input from `/dev/null` and
nobody at a keyboard (decision 0055).

```
$ apt-get update; apt-get install -y keel        # 9062, 9054, 9071, 18:04 UTC
  Installed: 0.23.21
  Candidate: 0.23.27
keel	0.23.27
$ systemctl is-active keel-database-follow.path keel-vip   # 9062 and 9054
active active
$ systemctl show postgresql@17-main -p ExecStartPre | grep -o 'keel database guard'
keel database guard
```

On 9062 the watch cleared the VIP fence of the run of 2026-10-15
(keel#166), with no operator step:

```
7465.84 9062 keel: database.server.role: the VIP fence is cleared: this standby is the holder's copy and received everything the holder flushed, so it may take the VIP again when the lease of the holder expires (keel#166)
```

After the upgrade, `keel-database-follow.service` ran 2 times on 9054
and 1 time on 9062 in 4 min (keel#164: before, every 1 to 2 s).

## 2. Run 1 on 0.23.27, base network: FAIL

The method is the one of `docs/evidence/2026-10-15-br3-thin-etcd-witness.md`,
section 4: `/root/writer.sh` on both pair nodes writes only while the
node carries the VIP, `/root/vipwatch.sh` samples the VIP every 0.1 s,
and a cut is an nft table that drops UDP port 51820 in the cut CT.

| Cut | etcd leader | Result | Numbers |
| --- | --- | --- | --- |
| BR3, witness, 60 s | 9054 (holder) | PASS | VIP kept on 9054; 197 writes acknowledged, 0 killed |
| BR2, standby, 60 s | 9054 (holder) | PASS, by design | VIP kept; 2 writes waited and were killed after 30 s (0054); the next write acknowledged 0.32 s after the heal |
| BR1, primary, 90 s | 9054 (cut) | FAIL (keel#178) | 9062 claimed epoch 14 in etcd, but no node carried the VIP |

Neither cut of run 1 removed the etcd leader from a site that did not
hold the VIP. So run 1 did not test keel#167.

### The failure (keel#178)

The cut of 9054 began at 7979.98. 9062's controller claimed epoch 14
when the lease of epoch 13 expired. Its root half then wrote the
statement of keel#165, and the sandbox of keel-vip.service refused the
write:

```
8013.44 9062 python3[370035]: vip: [Errno 30] Read-only file system: '/var/lib/keel/database/old-primary-gone.new'
```

keel-vip.service has `ProtectSystem=strict` and
`ReadWritePaths=/var/lib/keel/vip /etc/wireguard`. The write failed
before the claim was recorded with its lease. The next turn took the
claim from the counter with no lease, and the controller carries only a
claim with a lease. 9062 stayed in recovery. CI did not see it, because
the netns harness gave the helper write access to the whole root of
the node.

What worked in the same run, on 9054 after the heal at 8071.71
(keel#156, keel#164):

```
8074.86 9054 keel: vip ...: epoch 14, held by EJIMTp... at fd1a:bb4c:b407::fc0a; this node no longer holds it
8075.59 9054 systemd: Starting postgresql@17-main.service
8076.22 9054 postgresql@17-main: keel database guard: starts as a standby that follows nobody: the newest claim of fd1a:bb4c:b407::ffff:1 is the other member's, so this server takes no write (standby.signal written, the follow drop-in removed; keel#156)
8078.59 9054 systemd: Started postgresql@17-main.service
8080.22 9054 keel: database.server.role: a dump of what this node holds is kept at /var/backups/keel/postgresql/rejoin-20261015T181439Z.sql.zst
8080.22 9054 keel: database.server.role: refused: diverged: ... (timeline 7 against the holder's 7)
```

The old primary never started as a primary after the heal. Before the
fix the server was writable 2.9 to 3.8 s at this point.

**Restore 1, an operator step:** `keel database promote
--old-primary-gone` on 9054, 8256.99 to 8262.30 (5.3 s). 9054 holds
epoch 15 with an etcd lease, 9062 streams as its synchronous standby,
and the watch cleared the VIP fence of 9062 again. Both nodes were on
timeline 7, so no reseed was necessary.

Acknowledged ids of run 1: 360. All 360 are in `t1` on 9054 and on 9062.

**Decision:** 0.23.27 stays in trixie-testing and does not go to
trixie. The fix is Keel-Linux/keel#179 (keel#178), released as 0.23.28.
The whole matrix runs again on 0.23.28.

## 3. Release and upgrade: keel 0.23.29

keel 0.23.28 is Keel-Linux/keel#176 (keel verify and the images key,
decision 0055), merged on main by other work on the same day. keel
0.23.29 adds the fix of keel#178 (Keel-Linux/keel#179). CI was green
on #179, with the netns helper now in the write paths of
keel-vip.service.

```
# build host, 20:02 UTC, /srv/keel-apt/apt
$ bin/build-package --native keel main </dev/null
build-package: done: keel_0.23.29_amd64.changes in /srv/keel-apt/incoming
sha256 7329e3d0592f4ee6ac838c3c2b99942e72b21dae929e56aae6e87d7aa28e4622  keel_0.23.29_all.deb
$ bin/publish </dev/null
publish: committed in /srv/keel-apt/apt: publish trixie-testing: keel 0.23.29
# workstation
$ keel-publish-mirror --archive-only
keel-publish-mirror: https://archive.keellinux.org trixie-testing verifies
EXIT=0
$ apt-get install -y keel                         # 9062 20:02:42, 9054 20:03:03
keel	0.23.29
```

9071 was not upgraded: BR3-THIN did not answer (section 4).

## 4. BR3-THIN offline

The last WireGuard handshake of 9054 with the witness was at 1792091681
(19:14:41 UTC). From 20:03 UTC the host BR3-THIN did not answer ssh or
ping. A traceroute stops after `2804:710:d0:c::ffff`, the far end of
the WireGuard link `pop`. etcd had 2 of 3 voters, 9054 and 9062, and the
pair worked: 9054 primary at epoch 15, 9062 streams as its synchronous
standby.

With 2 voters, a cut of either pair node leaves no quorum. So the
matrix cannot run on 0.23.29 until the witness is back. The test did
not change BR3-THIN.

## 5. Result against the criteria

| Item | 0.23.27 (run 1) | 0.23.29 |
| --- | --- | --- |
| Upgrade | PASS: follow path active on both; fence of 9062 cleared by the watch | 9054 and 9062 upgraded; 9071 not reached |
| Cut of BR3 (witness) | PASS at base, leader on the holder | not run, BR3-THIN offline |
| Cut of the standby site | PASS at base, by design, leader on the holder | not run, BR3-THIN offline |
| (c) cut of the primary site | FAIL (keel#178) | not run, BR3-THIN offline |
| (e) heal of the old primary | PASS for keel#156: started as a standby, fenced, dumped, recorded | not run, BR3-THIN offline |
| (d) reseed | not reached | not run, BR3-THIN offline |
| 2 failovers in a row | not reached | not run, BR3-THIN offline |
| (e) boot | not reached | not run, BR3-THIN offline |
| keel#167, a cut of the leader's site that does not hold the VIP | not tested | not run, BR3-THIN offline |
| netem profile | not run | not run, BR3-THIN offline |
| Follow path | PASS: active on both, 1 to 2 runs in 4 min | active on both |

**Decision:** keel stays in trixie-testing. Nothing goes to trixie:

```
$ curl -s https://archive.keellinux.org/dists/trixie/main/binary-amd64/Packages | grep -A1 '^Package: keel$'
Version: 0.23.21
$ curl -s https://archive.keellinux.org/dists/trixie-testing/main/binary-amd64/Packages | grep -A1 '^Package: keel$'
Version: 0.23.29
```

0.23.27 must never go to trixie (keel#178). 0.23.29 goes to trixie
only after the whole matrix passes on it, with BR3-THIN back.

## 6. State at the end

| | 9054 (BR1) | 9062 (BR2) | 9071 (BR3) |
| --- | --- | --- | --- |
| keel | 0.23.29 | 0.23.29 | 0.23.27, not reached since 19:14 UTC |
| VIP | primary, epoch 15, etcd lease | replica, not fenced | not in the pair |
| Server | primary, `keel\|streaming\|sync` | standby, streams over TLS | - |
| A write | `INSERT 0 1` | - | - |
| `keel-database-follow.path` | active | active | - |
| `keel diff` | exit 14: only the handshake of the witness (4707 s old) | exit 14: the same | - |
| nft table `inet keeltest` | none | none | none at the last heal (7754.07) |
| netem | none | none | never applied in this session |

The pair works with 2 of 3 etcd voters. While BR3-THIN is offline, the
loss of 9054 or 9062 stops the writes, and no failover is possible.

Outside the keel CLI, the test changed only these: the nft table of a
cut in the cut CT, the test tools under `/root/logs`, and the leader
helpers that only read etcd. Restore 1 (section 2) is the one operator
step.

Left on the nodes: the dumps under `/var/backups/keel/postgresql/` on
9054, the rows of the tests in `pairtest.t1`, and `/root/logs` on 9054
and 9062.
