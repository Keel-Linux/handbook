# mariadb layer 19.0-10 on the stable 1 core: release test and publication (2026-10-30)

Date: 2026-10-30. The time zone is UTC. This is stage 3 of the mariadb
path that the maintainer approved: (1) keel 0.23.62 and keel-mariadb 0.1.1
promoted to `trixie` (apt#74), (2) both in the pool `stable-1` and the
layer built with `keel-release --no-index` (apt#76, decision 0072), (3) this
release test on the staged layer, then the publication with
`--no-channels`.

No secret is in this file. The passwords were made on the workstation,
given to the CTs in the preseed only, and removed after the test. Output is
trimmed.

## Result

**PASS. The layer is published. The Proxmox index and the stable pointer
did not change.**

| Item | Result |
| --- | --- |
| Tested image | the staged release template, not a CI build (sha512 checked on BR1 and BR2) |
| First boot, 3 CTs | `Inithooks run completed`, 0 failed units, admin login with DB_PASS |
| Bind address (keel#233) | overlay address bound, with `listen: ["::1"]` only |
| Pair | TLS with server certificate check, semi-sync (1 client), GTID strict, `Using_Gtid: Slave_Pos` |
| Planned failover to BR2 and failback | pass, 0 acknowledged writes lost |
| VIP during `systemctl restart keel-vip` | on wg0 in 20 of 20 samples, 0 write errors |
| `pct stop` of the holder, etcd leader | 0 acknowledged writes lost; the witness learns 0.6 s after the claim |
| `pct stop` of the holder, etcd follower | 0 acknowledged writes lost; the witness learns 0.7 s after the claim |
| Rejoin after each stop | by GTID, no errant GTID, no reseed |
| `keel mesh upgrade-check` | exit 0 on all 3; the holder says "upgrade it last" |
| Database and etcd ports on the uplink | closed |
| `keel diff` | exit 0 on all 3 with `network.managed_by: file`; see keel#238 |
| Publication | exit 0 in 19 s; `aplinfo.dat` and `layers/stable` the same before and after |
| Appliance gate | pass on keel-mariadb#37 (run 21), no change to branch protection |

## The image

`/srv/keel-release/2026-10-30/` on the build host. MANIFEST: `release
2026-10-30`, `revision 1`, `appliances mariadb`, `index none`, signed with
the two release subkeys.

| File | sha256 |
| --- | --- |
| `layers/mariadb.tar.zst` | `4f63bbeef5752433308eaab2f8dcfa1c6edde6a62f89bba311ab10bdf88d0e9f` |
| `layers/mariadb.manifest` | `a251a2e0c879571ba84a41715600cbcb6665a8fba7eefaa13bbb21bc64528386` |
| `layers/core.tar.zst` | `1c5dc3b1f5edece31b15e84576fa62dba0e38986d85913e4de059c58c984c7a7` |
| `images/debian-13-keel-mariadb_19.0-10_amd64.tar.zst` | `ca5b384433f84aa4d0b5d1a2543e0154984c8ef0b90a937ecc0cdf631d29d2a3` |

The layer manifest: `parent core`, `parent_sha256 1c5dc3b1…`, `pool
stable-1`, keel-mariadb commit `864d7a4`, common `84ff6a2`. Packages:
keel 0.23.62, keel-mariadb 0.1.1, keel-core 0.1.3, mariadb-server
1:11.8.6-0+deb13u1.

The template went from the build host to `hw12-br1` and `nfs1-br2` as
`debian-13-keel-mariadb_19.0-10+stage20261030_amd64.tar.zst`. The sha512
on both hosts is the one in the release:
`5cf23377…72e5fd9`.

## Topology

| CT | Host | Name | Overlay | Role |
| --- | --- | --- | --- | --- |
| 9310 | hw12-br1 | `s3-w` | `fd99:10bb:519a::16db` | witness, etcd member, writer |
| 9311 | hw12-br1 | `s3-b` | `fd99:10bb:519a::1` | pair, primary at installation |
| 9312 | nfs1-br2 | `s3-c` | `fd99:10bb:519a::907c` | pair, replica at installation |

VIP `fd99:10bb:519a::ffff:1`. `installation.mode: cloud_advanced`, etcd of
3. CTs: unprivileged, `nesting=1`, 8 GB, 2 GB memory, 2 cores. Preseed
`/etc/inithooks.conf` (ROOT_PASS, DB_PASS, HUB_APIKEY, SEC_ALERTS and
SEC_UPDATES skipped) written on the mounted rootfs, owned by the CT's
root (100000:100000, 0600).

netem on the host side of the veth of C:

```
qdisc netem 802f: root refcnt 21 limit 1000 delay 250ms  25ms loss 1.5%
W -> C over the overlay: 29 of 30 received, rtt 232.2/261.0/279.0 ms
W -> B over the overlay: 30 of 30 received, rtt 0.19/0.51/2.04 ms
```

## First boot

On each of the 3 CTs:

```
[98finalize] successfully completed
Inithooks run completed
Confconsole started, Inithooks exiting
failed:            (no failed unit)
keel 0.23.62, keel-mariadb 0.1.1
admin login ok 11.8.6-MariaDB-0+deb13u1 from Debian
-rw------- 1 root root 1 /etc/inithooks.conf   (emptied by 98finalize)
```

The apt sources: `trixie` enabled, `trixie-testing` present with
`Enabled: no`, the 990 pin on `o=Keel Linux`.

## Mesh, etcd and the pair

Sequence, all with `keel` commands: `keel mesh create` on B, `keel mesh
invite --endpoint <B uplink>` and `keel mesh join -` (token on standard
input) on W, then on C, `keel vip pair` on B and on C, `keel spec apply
--system-only` on B, `keel vip promote` on B, `keel spec apply
--system-only` on C.

```
[B] created the mesh: this node is fd99:10bb:519a::1/64 on wg0, WireGuard on UDP 51820
[C] etcd: this node forms with 2 other member(s)
etcd: 3 voter(s), 0 learner(s), all healthy, leader keel-fd99-10bb-519a--1
[C] fd99:10bb:519a::ffff:1 is the VIP of <C> and <B>, signed by both
[B] apply --system-only: 10 change(s), 0 failed
[B] this node holds fd99:10bb:519a::ffff:1 at epoch 1
[C] apply --system-only: 10 change(s), 0 failed
```

The spec of both pair nodes declares `listen: ["::1"]`, with no overlay
address, on purpose:

```
B: bind-address = ::1,fd99:10bb:519a::1,fd99:10bb:519a::ffff:1
C: bind-address = ::1,fd99:10bb:519a::907c,fd99:10bb:519a::ffff:1
gtid_strict_mode = ON, rpl_semi_sync_master_wait_point = AFTER_SYNC
ssl_ca, ssl_cert, ssl_key, ssl_crl in /etc/mysql/keel-tls
B: read_only=OFF, Rpl_semi_sync_master_clients 1
C: Master_Host fd99:10bb:519a::1, IO Yes, SQL Yes, Master_SSL_Allowed Yes,
   Master_SSL_Verify_Server_Cert Yes, Using_Gtid Slave_Pos, Seconds_Behind_Master 0
```

## Rounds

A writer on W writes one row each 0.1 s through the VIP, with a 3 s
connect timeout. An id counts as acknowledged only when the client
returned 0. After each round, every acknowledged id was looked up on both
pair nodes (`comm -23` of the sorted lists).

| Round | Action | VIP | Acks (errors) | Longest gap between acks | Acked ids missing |
| --- | --- | --- | --- | --- | --- |
| 1 | `keel vip promote` on C (BR2), 04:00:31 | epoch 2, B follows C over TLS | 52 (1) | 4.56 s | 0 on B, 0 on C |
| 2 | `keel vip promote` on B, 04:01:48, returned in 4.8 s | epoch 3, C follows B | 98 (7) | 3.55 s | 0 on B, 0 on C |
| 3 | `systemctl restart keel-vip.service` on holder B | epoch 3, on wg0 in 20 of 20 samples | 74 (0) | 0.45 s | 0 on B, 0 on C |
| 4 | `pct stop 9311`, holder and etcd leader, 04:04:27.6 | epoch 4 on C | 56 (14) | 44.25 s | 0 on C, 0 on B after it rejoined |
| 5 | `pct stop 9311`, holder and etcd follower, 04:09:05.9 | epoch 6 on C | 55 (8) | 23.70 s | 0 on C, 0 on B after it rejoined |

Round 1 has 53 rows for 52 acks: one insert committed, but the client
timed out before the answer. Before round 5, `keel vip promote` on B
moved the VIP back to B (epoch 5); C was the etcd leader then.

### Times after the stop (rounds 4 and 5)

Times are from the start of `pct stop` (it returned after 3.9 s and 3.8
s).

| Event | Round 4 (leader stopped) | Round 5 (follower stopped) |
| --- | --- | --- |
| etcd: lost leader (C and W) | +8.2 s | no leader change |
| etcd: C became leader | +14.4 s | |
| C: claimed the VIP | +42.1 s | +22.7 s |
| W: learns the new holder | +42.7 s | +23.4 s |
| W: routes the VIP to C (wg allowed-ips, each 0.5 s) | +43.2 s | +23.4 s |
| W: first acknowledged write after the cut | +45.6 s | +24.9 s |
| C: "did not take the claim" for the dead B | +52.1 s | +32.7 s |

The keel#235 fix works on the release layer: W learns the new holder 0.6
s (round 4) and 0.7 s (round 5) after the claim. The release test before
the fix (handbook#147) gave 10.7 s and 11.7 s. The timeout of the
exchange with the dead B (10 s) comes after W already writes. The claim
in round 4 comes later than in round 5 because etcd gives every lease its
full TTL again when the leader changes; handbook#147 saw the same.

Journal of C, round 5:

```
+22.7 vip fd99:10bb:519a::ffff:1: claimed at epoch 6: the lease of epoch 5 is gone (expired at its due time: the old primary is gone, so a PostgreSQL primary commits alone, decision 0054)
+29.6 database.server.role: drained and promoted: this node replicates from nobody and takes writes
+32.7 vip fd99:10bb:519a::ffff:1: fd99:10bb:519a::1 did not take the claim: [fd99:10bb:519a::1]:51821 through wg0: timed out
```

The claim message names PostgreSQL on a MariaDB pair. The text is fixed
in `keel/mesh/vipetcd.py:110`. Filed as keel#237 (text only).

### Rejoin

B started again after each stop. 70 s after `pct start` it said:

```
rejoined: no errant GTID, replicating from [fd99:10bb:519a::907c]:3306 over TLS from 0-64468245-261
rejoined: no errant GTID, replicating from [fd99:10bb:519a::907c]:3306 over TLS from 0-64468245-315
```

After each rejoin B was a replica, fenced ("takes it again only by keel
vip promote here"), and had every acknowledged id. No reseed was
necessary.

## End state

| Check | W | B | C |
| --- | --- | --- | --- |
| `keel mesh upgrade-check` | exit 0 | exit 0 | exit 0, "this node holds it; upgrade it last" |
| Rows in `pairtest.t` | | 340, sum of ids 716691 | 340, sum of ids 716691 |
| `gtid_binlog_state` | | `0-64468245-315,0-1551637544-344` | the same |
| Failed units | none | none | none |
| `keel diff`, spec with `managed_by: host` | | exit 14, 1 drift | exit 14, 1 drift |
| `keel diff`, spec with `managed_by: file` | exit 0, no drift | exit 0, no drift | exit 0, no drift |

The one drift is `network.managed_by: drift (declared host, observed
file)`. keel reads `host` only when the LXC marker
`/var/lib/turnkey-info/inithooks.service/lxc` exists. `tar -t` on the
build host shows that no released template has it: core 19.0-11,
postgresql 19.0-7 and this mariadb 19.0-10. Only the boot tests write it.
This is not a defect of this layer. Filed as keel#238.

Ports, probed with a TCP connect (3 s timeout):

| From | To | Open | Closed |
| --- | --- | --- | --- |
| workstation | uplink of B and of C | 22 | 3306, 2379, 2380, 51821 |
| W | uplink of B and of C | 22 | 3306, 2379, 2380, 51821 |
| W | overlay of B and of C | 3306, 2379, 2380, 51821 | |
| W | VIP | 3306 | 2379, 2380, 51821 |

## Publication

From the workstation, `bin/keel-publish-mirror --no-channels 2026-10-30`
(apt `e3d0e72`), exit 0 in 19 s:

```
keel-publish-mirror: checking every staged file against the MANIFEST
keel-publish-mirror: checking that the staged Proxmox index was merged onto the one the mirror serves
blob 1c5dc3b1…: already published, left as it is
blob 4f63bbee…: published for mariadb
published release 2026-10-30 from root@<build host> to popsolutions@keellinux.org, signed: yes
keel-publish-mirror: keel verify checked the layers served by https://mirror.keellinux.org
keel-publish-mirror: https://archive.keellinux.org trixie verifies
keel-publish-mirror: https://archive.keellinux.org trixie-testing verifies
keel-publish-mirror: https://archive.keellinux.org trixie-security verifies
```

| sha256 | Before (04:13 UTC) | After (04:14 UTC) |
| --- | --- | --- |
| `releases.keellinux.org/pve/aplinfo.dat` | `6bb9c0fb…d890a5` | `6bb9c0fb…d890a5` |
| `mirror.keellinux.org/layers/stable` | `055bc034…6c7613` | `055bc034…6c7613` |
| `layers/mariadb.manifest` | `ddcf75be…` (old parent) | `a251a2e0…`, the same as the build host |
| `layers/mariadb.tar.zst` | `85253405…` | `4f63bbee…`, the same as the build host |
| `layers/core.manifest` | `4729a156…` | `4729a156…` |

The published manifest says `parent_sha256 1c5dc3b1…` and `pool
stable-1`. The template is on `mirror.keellinux.org/images/` (HTTP 200).
`aplinfo.dat` has no mariadb record.

## The appliance gate

No PR was open on keel-mariadb. keel-mariadb#37, one empty commit on the
Keel-Linux branch `ci/appliance-recheck-20261030`, ran the gate. Branch
protection was not changed.

```
keel-mariadb run 21: the gate recorded published=true
  manifest says parent core, the caller declares core
  04:20:13 boot-test: mariadb boot test passed on 2 nodes, replication included
```

| Check | Result |
| --- | --- |
| packages / appliance | success in 3m29s |
| packages / build | success in 2m5s |
| tests / package | success in 5s |
| tests / tests | success in 51s |

keel-mariadb#37 is closed without merge, and its branch is deleted.

## Clean up

CTs 9310, 9311 (BR1) and 9312 (BR2) are destroyed (`pct destroy
--purge`). The template copies are removed from both hosts. The netem
qdisc went with the veth of CT 9312. The preseed passwords on the
workstation are removed. CTs 9300-9309 were not touched.

## Open

- keel#237: the claim message names PostgreSQL on a MariaDB pair.
- keel#238: the released templates have no LXC marker, so a spec that
  declares `network.managed_by: host` drifts on a real Proxmox CT.
