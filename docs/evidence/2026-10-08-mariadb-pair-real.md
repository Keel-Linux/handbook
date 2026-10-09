# Evidence: MariaDB pair of keel 0.23.3 on real Proxmox nodes

Note: public uplink addresses are replaced by `<uplink>` in this copy.

Date: 2026-10-08 23:36 to 2026-10-09 00:00 UTC. Host: hw12-br1 (Proxmox).
Nodes: CT 9003 keel-db-1, CT 9004 keel-db-2 (db pair); CT 124 keel-web-1,
CT 125 keel-web-3 (BR1); keel-web-2 (BR2, reached over the overlay through
web-1). Mesh 9fe71b35, overlay fd11:a58a:88ef::/64.

Access to web-2: web-1 does not allow SSH TCP forwarding ("administratively
prohibited"). We used an SSH ProxyCommand that runs a small Python TCP relay in
CT 124 (`pct exec 124 -- python3 ...`) to `[fd11:a58a:88ef::2]:22`. We changed
nothing on web-1 for this.

Section 1 to 8 give the results. The appendix gives every command and its
trimmed output, in time order (`=== [target] UTC-time rc=N`, then `$ command`,
then the output). Secrets are not in this file: the app password is
`<redacted>`, the `repl` password hash is `<hash>`, and the replication secret
was only used through a shell variable.

## Summary

| Step | Result |
| --- | --- |
| 1. Upgrade web-1/2/3 to keel 0.23.3 | PASS. `keel --version` = 0.23.3 on all three. etcd 3 voters healthy before and after. The upgrade itself caused no etcd interruption. |
| 2. db nodes to keel 0.23.3 + keel-mariadb 0.1.0 | PASS. keel#96 fix works: `keel mesh sync` on db-1 added the missing db-2 peer. keel#99 NOT fixed: web-2 and web-3 do not become peers of the db nodes. |
| 3. Declare the pair, pair, apply | PASS WITH WORKAROUND. The database certificate fails in this topology (bug B1). We wrote the root holder address into a state file; then apply passed on both nodes. |
| 4. Verify | PASS: write at VIP, read on replica, replica refuses INSERT (root and app, 1290), semi-sync ON, TLS 1.3 with REQUIRE SUBJECT and ISSUER, credential shared over the members' channel. |
| 5. Failover | PASS WITH A SAFETY BUG. Planned: 1.34 s write gap, 0 acked rows lost. Unplanned (pct stop): 35.5 s write gap (the promote takes 30.5 s), 0 acked rows lost. Old primary rejoins by GTID. But the old primary is WRITABLE for about 31 s after boot (bug B2). |
| 6. `apt reinstall keel` on the primary | PASS. 0 failed writes, longest gap 0.20 s, VIP stayed on wg0 in all 250 samples. |
| 7. Site | Single-site test. Both db CTs are on BR1 (hw12-br1). No WAN latency between the pair. |

## 1. Upgrade of web-1, web-3, web-2

Before (all three): `keel 0.22.0`, `keel-overlay-etcd 0.4.0`,
`keel-overlay-vip 0.2.0`, `keel --version` printed `0.19.0` (keel#98).

Before, web-2 already had `keel-mesh-sync.service` failed (exit 21: "no member
completed a WireGuard handshake within the window"); it tried to add the db
peers.

Commands: `apt-get update && apt-get install -y --only-upgrade keel`.

| Node | Time (UTC) | After |
| --- | --- | --- |
| web-1 (CT 124) | 23:42:26 to 23:42:35 | keel 0.23.3, etcd 0.4.0, vip 0.2.0, `keel --version` 0.23.3 |
| web-3 (CT 125) | 23:42:48 to 23:42:57 | same |
| web-2 (BR2) | 23:43:01 to 23:43:40 | same |

`keel mesh status` after, on each: `etcd: 3 voter(s), 0 learner(s)`, all three
`voter healthy`, `leader: keel-fd11-a58a-88ef--2`.

etcd health monitor: on each web node a loop read
`http://[::1]:2381/health` every second from 23:42:16 to 00:00:03.

| Node | Samples | Not healthy |
| --- | --- | --- |
| web-1 | 1036 | 0 |
| web-2 | 1025 | 0 |
| web-3 | 1008 | 62, from 23:45:53 (see bug B4, not the upgrade) |

The 62 failures on web-3 started 3 min after its upgrade. They match two
`wg-quick down/up` of web-3 by `keel mesh sync` (bug B4), not the package
upgrade. No VIP existed on the web nodes during the upgrade.

The upgrade also enabled `keel-database-follow.path`,
`keel-database-follow.service` and `keel-database-watch.timer` on the web
nodes. The watch timer then logs "skipped, unmet condition" every 30 s (bug B9).

## 2. db-1 and db-2: install, keel#96, keel#99

Before: keel 0.23.0, no keel-mariadb, mariadb-server 1:11.8.6-0+deb13u1,
`keel --version` 0.19.0.

- db-1 `wg show`: only peer web-1. db-2 was in the spec but not on wg0
  (keel#96). `keel diff` rc=14: `peers.o9tG...endpoint: drift (declared ...,
  observed nothing)`.
- db-2 `wg show`: web-1 and db-1, no handshake with db-1.

`apt-get install -y keel keel-mariadb` on both (23:44:07 to 23:44:25): keel
0.23.3, keel-mariadb 0.1.0, `/usr/share/keel/appliances/mariadb.yaml` present.

`keel mesh sync` on db-1 (23:44:39 to 23:44:52):

```
the spec names 1 peer(s) that wg0 lacks: o9tGVm/...; the overlay is applied again (keel#96)
confirmed from a WireGuard handshake from o9tGVm/... (23:44:50 UTC)
sync rc=0
```

After: db-1 wg0 has web-1 and db-2, handshake 2 s. keel#96 fix: PASS.

`keel mesh sync` on db-2 and again on db-1: "no member this node does not
know: it is a peer of every admitted member its peers know". Both db nodes
have only 2 peers (web-1 and the other db node). web-2 and web-3 are not
peers. keel#99: NOT fixed (open). See bug B4 for the side effect on web-3.

## 3. The pair

Spec added on both nodes (db-1 role primary, db-2 role replica; listen = own
overlay address and `::1`):

```yaml
appliance:
  name: mariadb
  vip: fd11:a58a:88ef::ffff:1
installation:
  mode: cloud_simple
overlays: {installer: enabled, wireguard: enabled, etcd: disabled, crowdsec: disabled, vip: enabled}
database:
  server: {engine: mariadb, role: primary|replica, listen: [<own overlay address>, "::1"]}
```

`keel spec validate`: ok on both.

`keel vip pair fd11:a58a:88ef:0:cd53:dda9:f0cb:b889` on db-1 (23:46:28):
`fd11:a58a:88ef::ffff:1 is the VIP of li08... and o9tG..., signed by both`, rc=0.
The pair record is on both nodes. db-1 journal at 23:46:30: "the
database/replication secret given to o9tG...".

`keel spec apply --system-only` on db-1 (23:46:49), rc=16:

```
database.server: make or renew the database certificate ... failed: the root CA's holder at
fd11:a58a:88ef:0:cd53:dda9:f0cb:b889 did not sign the database certificate
([fd11:a58a:88ef:0:cd53:dda9:f0cb:b889]:51821 refused: this node does not hold the mesh's root CA)
apply --system-only: 5 change(s), 1 failed
```

Retry once (23:47:29): same failure. Cause: bug B1. Workaround (state file, no
code change): on both db nodes
`/var/lib/keel/etcd/holder` = `fd11:a58a:88ef::1` (0600, dir 0700).

Apply db-1 (23:47:41 to 23:47:44): `8 change(s), 0 failed`, rc=0. Certificate
signed by the mesh root, until 2026-11-07.
Apply db-2 (23:47:51 to 23:47:55): `10 change(s), 0 failed`, rc=0, "seeded
from [db-1]:3306 and replicating from it over TLS". It did not ask for
`--destroy-local-database` (db-2 held only the system databases).

Apply said "no claim of the VIP is known yet". `keel vip promote` on db-1
(23:48:02 to 23:48:03): "this node holds fd11:a58a:88ef::ffff:1 at epoch 1, on
wg0, taken by 2 of 2 peer(s)". web-1 routes the VIP to db-1
(`allowed ips ... fd11:a58a:88ef::ffff:1/128`).

`keel database status` after the pair: db-1 primary, 1 replica connected,
semi-sync master ON; db-2 replica, read_only true, IO Yes, SQL Yes, lag 0,
TLS Yes. `keel diff` on both: rc=14 with 2 drifts each:
`database.server.listen: drift (declared <addr>, ::1, observed *)` (bug B3) and
`overlays.vip: drift (declared enabled, observed keel-vip.service enabled and
inactive)` (bug B5). `database.server.semi_sync: same (on)` on the primary.

## 4. Verification

Writes at the VIP from db-2 as `app` (new connection each), read on db-2
(replica):

```
write 4: connect+commit at VIP 0.037 s; visible on replica 0.036 s after the ack
write 5: connect+commit at VIP 0.036 s; visible on replica 0.036 s after the ack
write 6: connect+commit at VIP 0.038 s; visible on replica 0.037 s after the ack
```

The row was there at the first read (0.036 s is the cost of one client start).

Replica refuses writes (db-2):

```
root (socket):            ERROR 1290 (HY000) ... --read-only option
app at own overlay addr:  ERROR 1290 (HY000) ... --read-only option
app at ::1:               ERROR 1290 (HY000) ... --read-only option
@@read_only = 1; READ_ONLY ADMIN held only by 'mysql'@'localhost'
```

Semi-sync on the primary: `Rpl_semi_sync_master_status ON`,
`Rpl_semi_sync_master_clients 1`, `yes_tx 16`, `no_tx 0`. Replica:
`Rpl_semi_sync_slave_status ON`. Drop-in: AFTER_SYNC, timeout 10000,
wait_no_slave OFF, slave_net_timeout 10, gtid_strict_mode ON, ROW.

TLS on the channel:

```
GRANT ... TO `repl`@`fd11:a58a:88ef:0:cd53:dda9:f0cb:b889` IDENTIFIED BY PASSWORD <hash>
  REQUIRE ISSUER '/CN=keel mesh 9fe71b35b8d35c58 etcd root' SUBJECT '/CN=keel-fd11-a58a-88ef-0-cd53-dda9-f0cb-b889 mariadb'
server.pem: CN=keel-fd11-a58a-88ef-0-382f-45b-553c-f11 mariadb, issuer the root, EKU serverAuth+clientAuth,
  SAN IP fd11:a58a:88ef:0:382f:45b:553c:f11, fd11:a58a:88ef::ffff:1, until Nov 7 2026
replica: Master_SSL_Allowed Yes, Master_SSL_Verify_Server_Cert Yes, Using_Gtid Slave_Pos
repl without TLS:                    ERROR 1045
repl with TLS, no client cert:       ERROR 1045
repl with db-2 database leaf:        OK, Ssl_cipher TLS_AES_256_GCM_SHA384, TLSv1.3
```

Not tested: `repl` with an etcd member leaf (we had no such leaf on the db
nodes and did not take keys from the web nodes).

Credential: `/var/lib/keel/database/replication.secret` 0600 root on both,
same sha256 prefix `c329d382fb7b27a7`, not in the spec. Given by db-1 over the
members' channel at 23:46:30 during `keel vip pair` (journal line above).

## 5. Failover

Writer: `/root/writer.sh`, one new `mariadb` connection to the VIP per INSERT,
0.1 s sleep, connect timeout 2 s. "Gap" = time between two acknowledged writes.

### 5a. Planned: `keel vip promote` on the replica db-2

Writer on db-1. Promote at 23:51:24.950, done 23:51:25.912 (epoch 2):
"released by fd11:a58a:88ef:0:382f:45b:553c:f11 ... taken by 2 of 2 peer(s)".

```
writes: 407 ok, 1 failed; longest gap: 1.34 s (seq 86 on keel-db-1 -> seq 88 on keel-db-2)
failed: seq 87 ERROR 1290 (read-only) on the old primary
acked 407, on new primary 407, on replica db-1 407; acked but missing: 0
```

db-1 followed: read_only 1, replica of db-2 over TLS, Using_Gtid Slave_Pos.

### 5b. Unplanned: `pct stop` of the primary, then promote on the other node

Run 1 (primary db-2 stopped, writer on db-1). `pct stop 9004` 23:52:52.6 to
23:52:56.1. We first ran `keel vip promote` without the flag to check the
refusal (23:52:57.4 to 23:53:17.9, rc=24, "did not release it ... Nothing was
changed ... run keel vip promote --old-primary-gone"). Then
`keel vip promote --old-primary-gone` 23:53:19.2 to 23:53:49.8, rc=0, epoch 3,
"taken by 1 of 1 peer(s)".

```
writes: 445 ok, 30 failed; longest gap 56.00 s (includes the 20.5 s refusal test)
acked 445; on new primary 445; acked and missing: 0
```

Run 2 (clean measure; primary db-1 stopped, writer on db-2, promote at once).
`pct stop 9003` 23:56:42.0 to 23:56:45.5; `keel vip promote --old-primary-gone`
23:56:46.8 to 23:57:17.3 (epoch 4).

```
writes: 458 ok, 19 failed; longest gap 34.67 s; last ok 23:56:43.427, first ok 23:57:18.970
acked 458, missing on db-2: 0
```

The promote itself takes 30.5 s: three 10 s timeouts to the dead node (epoch
query, release, claim) (bug B7).

### 5c. Old primary back

Run 1: `pct start 9004` 23:55:03 to 23:55:08. At 23:55:43 `keel vip check`
learned epoch 3; at 23:55:44 `keel database follow`: "a dump ... kept at
/var/backups/keel/mariadb/rejoin-20261008T235544Z.sql.zst", "rejoined: no
errant GTID, replicating from [db-1]:3306 over TLS from 0-650213503-511".
Row counts after: 868 = 868 on both. Semi-sync back: master_clients 1, ON.

Run 2 with a boot probe (test unit on db-1, `@@read_only` and VIP on wg0
every 0.5 s, removed after the test):

```
23:57:35.194 read_only=1 no-VIP
23:57:36.347 read_only=0 no-VIP      <- writable, VIP held by db-2 at epoch 4
23:58:07.753 read_only=1 no-VIP
journal: 23:57:36 keel[691]: database.server.role: set read_only OFF: this role takes the application's writes
         23:58:06 vip ...: epoch 4 ... this node no longer holds it
         23:58:07 rejoined: no errant GTID, replicating from [db-2]:3306 over TLS from 0-388044305-958
```

The same happened in run 1 (23:55:12 read_only OFF, 23:55:44 ON). See bug B2.
The VIP was not put back on wg0 of the old primary.

## 6. `apt reinstall keel` on the primary (db-2)

Writer on db-1; VIP and read_only probe on db-2 every 0.2 s (250 samples).
Reinstall 23:58:57.0 to 23:59:06.7, rc=0.

```
writes: 408 ok, 0 failed; longest gap 0.20 s
probe: VIP on wg0 = 1 and read_only = 0 in all 250 samples
after: keel vip status primary epoch 4; Rpl_semi_sync_master_status ON, clients 1;
       mariadb, keel-database-follow.path, keel-vip-check.timer active
```

## 7. Site

Both db CTs are on hw12-br1 (BR1). This is a single-site test: the pair link
has LAN latency, not the 250 ms design case of 0050. web-2 is on BR2 and was
part of the etcd checks only. A BR1/BR2 pair is still to test.

## 8. Bugs

| ID | Severity | Bug | Exact output |
| --- | --- | --- | --- |
| B1 | High | In a mesh whose root CA is held by a cloud advanced node (web-1), a cloud simple pair cannot get its database certificate. `/var/lib/keel/etcd/holder` is written only on etcd members, so the node asks the other pair member, which refuses. docs/replication.md covers only the case where a pair member made the mesh. | `the root CA's holder at fd11:a58a:88ef:0:cd53:dda9:f0cb:b889 did not sign the database certificate ([...]:51821 refused: this node does not hold the mesh's root CA)` |
| B2 | High | After a crash and boot, the old primary sets `read_only OFF` from its stale local claim, before `keel vip check` learns the newer epoch. It stays writable for about 31 s while the other node holds the VIP. A write to its own address in that window makes an errant GTID. Contradicts "read only at its first second" (docs/replication.md, measured case a). | `23:57:36 keel[691]: database.server.role: set read_only OFF: this role takes the application's writes` ... `23:58:07 set read_only ON`; probe `read_only=0` from 23:57:36.347 to 23:58:07.753 |
| B3 | High (security) | `mariadb.socket` (enabled since the CT was made from the image: in the etckeeper "initial commit", 2026-10-08 19:42) listens on `[::]:3306`, so `bind-address` has no effect. 3306 answers on the public uplink with no firewall (cloud simple). The manifest says `expose: mesh`, "never on the uplink". `keel diff` shows it as permanent drift. | `[::]:3306 mariadb.socket mariadb.service`; from the Proxmox host to db-1 uplink: `Host '<uplink>' is not allowed`; `database.server.listen: drift (declared ..., ::1, observed *)` |
| B4 | High | keel#99 is still open on 0.23.3. Because of it, the keel#96 repair in `keel mesh sync` on web-3 adds db-1 (no handshake, db-1 does not list web-3), runs `wg-quick down/up`, waits 120 s, reverts with a second `wg-quick down/up`, and exits 21. Each bounce cut web-3's etcd voter from the leader for about 25 s. It repeats ("a new member after an hour"). web-2 did the same at 23:34 (0.22.0). | `the spec names 1 peer(s) that wg0 lacks: li08...; the overlay is applied again (keel#96)` ... `no member completed a WireGuard handshake within the window: the change reverts by itself`; etcd web-3: `23:46:00 lost leader`, `23:46:18 elected leader`, `23:48:01 lost leader`, `23:48:19 elected leader`; 62 failed health samples |
| B5 | Medium | In cloud simple, `overlays.vip: enabled` is permanent drift: `keel-vip.service` has `ConditionPathExists=/var/lib/keel/etcd/cluster.json`, so it never starts. Every apply prints "start keel-vip.service: done". | `overlays.vip: drift (declared enabled, observed keel-vip.service enabled and inactive)`; `start condition unmet ... ConditionPathExists=/var/lib/keel/etcd/cluster.json was not met` |
| B6 | Medium | With the replica gone, `keel diff` on the primary says `semi_sync: same (on)`. MariaDB keeps `Rpl_semi_sync_master_status ON` with 0 clients (`wait_no_slave = OFF`), so commits are async and nothing reports it. | `database.server.semi_sync: same (on)`; `Rpl_semi_sync_master_status ON`, `Rpl_semi_sync_master_clients 0` |
| B7 | Medium | `keel vip promote --old-primary-gone` takes 30.5 s with the old primary dead (three 10 s timeouts), most of the 35 s write downtime. | 23:56:46.8 start, 23:57:17.3 end; `... :51821 through wg0: timed out` three times |
| B8 | Medium | etckeeper commits private keys into `/etc/.git` (0700 root): `wireguard/wg0.key` at the keel install, and `mysql/keel-tls/server.key` at the reinstall. The keys stay in git history after rotation. | `create mode 100644 wireguard/wg0.key`; `create mode 100644 mysql/keel-tls/server.key` |
| B9 | Low | `keel database status` line "the primary's address" always names the other member, also on the primary. | db-1 as primary: `the primary's address: fd11:a58a:88ef:0:cd53:dda9:f0cb:b889` (that is db-2) |
| B10 | Low | `keel database status` on the replica shows an empty "GTID IO position" right after the seed. | `TLS Yes; GTID IO position ` (empty) while `Gtid_IO_Pos: 0-388044305-16` |
| B11 | Low | `semi-synchronous ... N not`: commits applied while the node was a replica, or with no replica, are counted as "not acknowledged". It reads as lost acks. | `36 commits acknowledged, 112 not` 5 s after the planned promote |
| B12 | Low | keel 0.23.3 enables `keel-database-watch.timer` on nodes with no database; it logs "skipped, unmet condition" every 30 s. | `keel-database-watch.service ... skipped, unmet condition check ConditionPathExists=/var/lib/keel/database` |
| B13 | Low | web-2 warns at every keel command that `overlays.vip` is not declared (spec not written out after the chain gained `vip`). Known behavior, but web-2 still has it. | `Warning: /etc/keel/instance.yaml: overlays.vip: not declared (default: disabled) ...` |

## State at the end

- CT 9003 keel-db-1: running, replica, read_only 1, fenced (as docs say),
  replicating from db-2 over TLS.
- CT 9004 keel-db-2: running, primary, holds the VIP fd11:a58a:88ef::ffff:1 at
  epoch 4, semi-sync ON with 1 client.
- Changes we made on the db CTs: spec sections above (backup
  `/root/instance.yaml.before-pair`), `/var/lib/keel/etcd/holder` (workaround
  B1), database `keeltest` and user `app` (4 hosts), `/root/.app.cnf` (0600),
  `/root/writer.sh`, `/root/gap.py`, writer and probe logs in `/root/`. The
  boot probe unit is removed.
- web nodes: keel 0.23.3. The etcd health monitor units are stopped and their
  logs are deleted. Nothing else was changed on them.
- CT 9005 and 9006: not created.

## Appendix: commands and outputs

```text
=== [web2] 2026-10-08T23:41:22Z rc=0
$ hostname

keel-web-2

=== [124] 2026-10-08T23:41:31Z rc=0
$ hostname; dpkg-query -W keel keel-overlay-etcd keel-overlay-vip; keel --version; systemctl is-active etcd keel-vip.service keel-members 2>&1 | tr "\n" " "; echo; systemctl list-units "keel*" "etcd*" --no-legend --plain | awk "{print \$1, \$3, \$4}"
keel-web-1
keel	0.22.0
keel-overlay-etcd	0.4.0
keel-overlay-vip	0.2.0
0.19.0
active inactive inactive 
keel-mesh-members.path active running
etcd.service active running
keel-host-keys.service active exited
keel-mesh-members-listen.service active running
keel-mesh-members.service active running
keel-mesh-etcd.timer active waiting
keel-mesh-sync.timer active waiting
keel-overlay-coraza-logrotate.timer active waiting

=== [125] 2026-10-08T23:41:33Z rc=0
$ hostname; dpkg-query -W keel keel-overlay-etcd keel-overlay-vip; keel --version; systemctl is-active etcd keel-vip.service keel-members 2>&1 | tr "\n" " "; echo; systemctl list-units "keel*" "etcd*" --no-legend --plain | awk "{print \$1, \$3, \$4}"
keel-web-3
keel	0.22.0
keel-overlay-etcd	0.4.0
keel-overlay-vip	0.2.0
0.19.0
active inactive inactive 
keel-mesh-members.path active running
etcd.service active running
keel-host-keys.service active exited
keel-mesh-members-listen.service active running
keel-mesh-members.service active running
keel-mesh-etcd.timer active waiting
keel-mesh-sync.timer active waiting
keel-overlay-coraza-logrotate.timer active waiting

=== [web2] 2026-10-08T23:41:37Z rc=0
$ hostname; dpkg-query -W keel keel-overlay-etcd keel-overlay-vip; keel --version; systemctl is-active etcd keel-vip.service keel-members 2>&1 | tr "\n" " "; echo; systemctl list-units "keel*" "etcd*" --no-legend --plain | awk "{print \$1, \$3, \$4}"

keel-web-2
keel	0.22.0
keel-overlay-etcd	0.4.0
keel-overlay-vip	0.2.0
0.19.0
active inactive inactive 
keel-mesh-members.path active running
etcd.service active running
keel-host-keys.service active exited
keel-mesh-members-listen.service active running
keel-mesh-members.service active running
keel-mesh-sync.service failed failed
keel-mesh-etcd.timer active waiting
keel-mesh-sync.timer active waiting
keel-overlay-coraza-logrotate.timer active waiting

=== [web2] 2026-10-08T23:41:45Z rc=0
$ journalctl -u keel-mesh-sync.service -n 15 --no-pager -o short-iso; keel mesh status

2026-10-08T23:36:20+00:00 keel-web-2 keel[12940]: instance.fqdn: unchanged (/etc/hosts maps keel-web-2 to keel-web-2.pop.coop)
2026-10-08T23:36:20+00:00 keel-web-2 keel[12940]: derived.monit: unchanged (/etc/keel/monit/keel-manifest.conf, 5 unit(s) and 6 probe(s) of web, not included)
2026-10-08T23:36:20+00:00 keel-web-2 keel[12940]: overlays.anubis: unchanged (disabled: anubis@keel.service, /usr/lib/keel/overlays/anubis/state.d/50keel-web)
2026-10-08T23:36:20+00:00 keel-web-2 keel[12940]: overlays.vip: unchanged (disabled: keel-vip.service)
2026-10-08T23:36:20+00:00 keel-web-2 keel[12940]: overlays.crowdsec: unchanged (disabled: crowdsec.service, crowdsec-firewall-bouncer.service)
2026-10-08T23:36:20+00:00 keel-web-2 keel[12940]: overlays.etcd: unchanged (enabled: etcd.service)
2026-10-08T23:36:20+00:00 keel-web-2 keel[12940]: overlays.nginx: unchanged (enabled: nginx.service)
2026-10-08T23:36:20+00:00 keel-web-2 keel[12940]: overlays.coraza: unchanged (enabled: /usr/lib/keel/overlays/coraza/state)
2026-10-08T23:36:20+00:00 keel-web-2 keel[12940]: network.overlay: bring the overlay wg0 up on a new /etc/wireguard/wg0.conf (wg-quick down, then up); it reverts in 120 s unless `keel network confirm` is run from a new session, over the overlay or the uplink: done
2026-10-08T23:36:20+00:00 keel-web-2 keel[12940]: keel mesh: 1 change(s), 0 failed
2026-10-08T23:36:20+00:00 keel-web-2 keel[12940]: no member completed a WireGuard handshake within the window: the change reverts by itself, the spec is put back as it was, and keel mesh sync tries again (a new member after an hour)
2026-10-08T23:36:20+00:00 keel-web-2 systemd[1]: keel-mesh-sync.service: Main process exited, code=exited, status=21/n/a
2026-10-08T23:36:20+00:00 keel-web-2 systemd[1]: keel-mesh-sync.service: Failed with result 'exit-code'.
2026-10-08T23:36:20+00:00 keel-web-2 systemd[1]: Failed to start keel-mesh-sync.service - keel mesh: learn the members this node's peers know.
2026-10-08T23:36:20+00:00 keel-web-2 systemd[1]: keel-mesh-sync.service: Consumed 1.945s CPU time, 24M memory peak.
Warning: /etc/keel/instance.yaml: overlays.vip: not declared (default: disabled): the chain of web gained it after this spec was last applied, so it takes the manifest's default for cloud_advanced; write it out (decisions 0027, 0041)
this node: fd11:a58a:88ef::2/64 on wg0, WireGuard on UDP 51820
mesh identity: 9fe71b35b8d35c5869faacc57ed2bc30
public key: o+GK/71E+YK/TO/pUkonxFP0DLcFdpPEm2ZlxJJ/VBc=
peers: 2
  1bSgAuDppyY36XfEH2zxXeT5altQGehlT7Se2AVZyAg=  fd11:a58a:88ef::1/128  [<uplink>]:51820  handshake 79 s ago
  8Tjk29fOsZmTJ61L3LfEI2mm/LHFzAy+roHC49woQnc=  fd11:a58a:88ef:0:47d1:8a55:262c:33ed/128  [<uplink>]:51820  handshake 79 s ago
pending invites: 0
etcd: 3 voter(s), 0 learner(s)
  keel-fd11-a58a-88ef-0-47d1-8a55-262c-33ed  fd11:a58a:88ef:0:47d1:8a55:262c:33ed  voter  healthy
  keel-fd11-a58a-88ef--2  fd11:a58a:88ef::2  voter  healthy
  keel-fd11-a58a-88ef--1  fd11:a58a:88ef::1  voter  healthy
leader: keel-fd11-a58a-88ef--2
etcd: this member's certificate expires 2026-11-07 09:45 UTC
vip: none (this node declares no appliance.vip and routes no other pair's)

=== [124] 2026-10-08T23:41:47Z rc=0
$ keel mesh status | sed -n "/^peers/,/^pending/p"
peers: 4
  o+GK/71E+YK/TO/pUkonxFP0DLcFdpPEm2ZlxJJ/VBc=  fd11:a58a:88ef::2/128  [<uplink>]:51820  handshake 81 s ago
  8Tjk29fOsZmTJ61L3LfEI2mm/LHFzAy+roHC49woQnc=  fd11:a58a:88ef:0:47d1:8a55:262c:33ed/128  [<uplink>]:51820  handshake 112 s ago
  li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY=  fd11:a58a:88ef:0:382f:45b:553c:f11/128  [<uplink>]:51820  handshake 187 s ago
  o9tGVm/IKImyW2kgn22YjiWdEXpAr28T6WF9uc4yW1Q=  fd11:a58a:88ef:0:cd53:dda9:f0cb:b889/128  [<uplink>]:51820  handshake 36 s ago
pending invites: 0

=== [125] 2026-10-08T23:41:49Z rc=0
$ keel mesh status | sed -n "/^peers/,/^pending/p"
peers: 3
  1bSgAuDppyY36XfEH2zxXeT5altQGehlT7Se2AVZyAg=  fd11:a58a:88ef::1/128  [<uplink>]:51820  handshake 115 s ago
  o+GK/71E+YK/TO/pUkonxFP0DLcFdpPEm2ZlxJJ/VBc=  fd11:a58a:88ef::2/128  [<uplink>]:51820  handshake 84 s ago
  li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY=  fd11:a58a:88ef:0:382f:45b:553c:f11/128  [<uplink>]:51820  no handshake known
pending invites: 0

=== [124] 2026-10-08T23:41:57Z rc=0
$ keel mesh etcd --help 2>&1 | head -30; ls /etc/keel/etcd /var/lib/keel/etcd 2>&1 | head; cat /etc/default/etcd 2>/dev/null | grep -v PASS | head -30
usage: keel mesh etcd [-h] ACTION ...

positional arguments:
  ACTION
    form      ask every member, make the mesh's etcd CA if it has none, enroll
              the cloud advanced members and form the cluster at three; on a
              formed cluster, bring in what it lacks (root)
    tend      promote learners in sync, remove those that never started within
              an hour, renew this member's certificates; what keel-mesh-
              etcd.timer runs (root)
    gate      restart etcd one member at a time: `stop` waits until every
              other member is healthy and none restarts, and takes the restart
              lock; `started` waits until this member is back and releases it;
              what keel-overlay-etcd's drop-in of etcd.service runs (root)
    reissue   on the root CA's holder: move every member to a certificate the
              root signs, one at a time, revoke the members' intermediate CAs
              and enable etcd's auth (keel#83); safe to run again (root)

options:
  -h, --help  show this help message and exit
ls: cannot access '/etc/keel/etcd': No such file or directory
/var/lib/keel/etcd:
admin.crt
admin.key
cluster.json
crl.pem
epoch
formation.json
holder
issued.json
# Written by keel from /var/lib/keel/etcd (handbook decisions 0025, 0048);
# keel spec apply rewrites it.
ETCD_NAME=keel-fd11-a58a-88ef--1
ETCD_DATA_DIR=/var/lib/etcd/default
ETCD_LISTEN_PEER_URLS=https://[fd11:a58a:88ef::1]:2380
ETCD_INITIAL_ADVERTISE_PEER_URLS=https://[fd11:a58a:88ef::1]:2380
ETCD_LISTEN_CLIENT_URLS=https://[fd11:a58a:88ef::1]:2379,https://[::1]:2379
ETCD_ADVERTISE_CLIENT_URLS=https://[fd11:a58a:88ef::1]:2379
ETCD_INITIAL_CLUSTER=keel-fd11-a58a-88ef-0-47d1-8a55-262c-33ed=https://[fd11:a58a:88ef:0:47d1:8a55:262c:33ed]:2380,keel-fd11-a58a-88ef--1=https://[fd11:a58a:88ef::1]:2380,keel-fd11-a58a-88ef--2=https://[fd11:a58a:88ef::2]:2380
ETCD_INITIAL_CLUSTER_STATE=new
ETCD_INITIAL_CLUSTER_TOKEN=9fe71b35b8d35c5869faacc57ed2bc30
ETCD_HEARTBEAT_INTERVAL=300
ETCD_ELECTION_TIMEOUT=5000
ETCD_CERT_FILE=/etc/etcd/keel/member.crt
ETCD_KEY_FILE=/etc/etcd/keel/member.key
ETCD_TRUSTED_CA_FILE=/etc/etcd/keel/ca.crt
ETCD_CLIENT_CERT_AUTH=true
ETCD_PEER_CERT_FILE=/etc/etcd/keel/member.crt
ETCD_PEER_KEY_FILE=/etc/etcd/keel/member.key
ETCD_PEER_TRUSTED_CA_FILE=/etc/etcd/keel/ca.crt
ETCD_PEER_CLIENT_CERT_AUTH=true
ETCD_TLS_MIN_VERSION=TLS1.3
ETCD_ENABLE_GRPC_GATEWAY=false
ETCD_LISTEN_METRICS_URLS=http://[::1]:2381
ETCD_CLIENT_CRL_FILE=/etc/etcd/keel/crl.pem
ETCD_PEER_CRL_FILE=/etc/etcd/keel/crl.pem

=== [124] 2026-10-08T23:42:04Z rc=0
$ curl -s -m 2 http://[::1]:2381/health; echo; ETCDCTL_API=3 etcdctl version 2>&1 | head -1
{"health":"true","reason":""}
etcdctl version: 3.5.16

=== [125] 2026-10-08T23:42:06Z rc=0
$ curl -s -m 2 http://[::1]:2381/health; echo; ETCDCTL_API=3 etcdctl version 2>&1 | head -1
{"health":"true","reason":""}
etcdctl version: 3.5.16

=== [web2] 2026-10-08T23:42:09Z rc=0
$ curl -s -m 2 http://[::1]:2381/health; echo; ETCDCTL_API=3 etcdctl version 2>&1 | head -1

{"health":"true","reason":""}
etcdctl version: 3.5.16

=== [124] 2026-10-08T23:42:16Z rc=0
$ rm -f /root/etcdmon.log; systemd-run --unit=keeltest-etcdmon --collect bash -c "for i in \$(seq 1 1500); do h=\$(curl -s -m 1 http://[::1]:2381/health | grep -o true || echo FAIL); echo \"\$(date -u +%T) \$h\" >> /root/etcdmon.log; sleep 1; done"
Running as unit: keeltest-etcdmon.service; invocation ID: 9f7998371cca46f98e2ab7d9d6049f5c

=== [125] 2026-10-08T23:42:17Z rc=0
$ rm -f /root/etcdmon.log; systemd-run --unit=keeltest-etcdmon --collect bash -c "for i in \$(seq 1 1500); do h=\$(curl -s -m 1 http://[::1]:2381/health | grep -o true || echo FAIL); echo \"\$(date -u +%T) \$h\" >> /root/etcdmon.log; sleep 1; done"
Running as unit: keeltest-etcdmon.service; invocation ID: 2a1f9a6fb09c44b58d68009e5e25ed73

=== [web2] 2026-10-08T23:42:20Z rc=0
$ rm -f /root/etcdmon.log; systemd-run --unit=keeltest-etcdmon --collect bash -c "for i in \$(seq 1 1500); do h=\$(curl -s -m 1 http://[::1]:2381/health | grep -o true || echo FAIL); echo \"\$(date -u +%T) \$h\" >> /root/etcdmon.log; sleep 1; done"

Running as unit: keeltest-etcdmon.service; invocation ID: 14c76d0169c14319a31abac8efc90e36

=== [124] 2026-10-08T23:42:36Z rc=0
$ date -u +%T; apt-get update -q 2>&1 | tail -3; apt-cache policy keel | head -4; DEBIAN_FRONTEND=noninteractive apt-get install -y -q --only-upgrade keel 2>&1 | tail -15; date -u +%T; dpkg-query -W keel keel-overlay-etcd keel-overlay-vip; keel --version
23:42:26
Get:6 https://archive.keellinux.org trixie-testing/main amd64 Packages [15.2 kB]
Fetched 108 kB in 0s (665 kB/s)
Reading package lists...
keel:
  Installed: 0.22.0
  Candidate: 0.23.3
  Version table:
Preparing to unpack .../archives/keel_0.23.3_all.deb ...
Unpacking keel (0.23.3) over (0.22.0) ...
Setting up keel (0.23.3) ...
keel-mesh-sync.service is a disabled or a static unit not running, not starting it.
keel-mesh-etcd.service is a disabled or a static unit not running, not starting it.
Created symlink '/etc/systemd/system/multi-user.target.wants/keel-database-follow.path' → '/usr/lib/systemd/system/keel-database-follow.path'.
Created symlink '/etc/systemd/system/multi-user.target.wants/keel-database-follow.service' → '/usr/lib/systemd/system/keel-database-follow.service'.
Created symlink '/etc/systemd/system/timers.target.wants/keel-database-watch.timer' → '/usr/lib/systemd/system/keel-database-watch.timer'.
keel-database-watch.service is a disabled or a static unit not running, not starting it.
Processing triggers for keel-overlay-vip (0.2.0) ...
[master d040198] committing changes in /etc made by "apt-get install -y -q --only-upgrade keel"
 3 files changed, 3 insertions(+)
 create mode 120000 systemd/system/multi-user.target.wants/keel-database-follow.path
 create mode 120000 systemd/system/multi-user.target.wants/keel-database-follow.service
 create mode 120000 systemd/system/timers.target.wants/keel-database-watch.timer
23:42:35
keel	0.23.3
keel-overlay-etcd	0.4.0
keel-overlay-vip	0.2.0
0.23.3

=== [124] 2026-10-08T23:42:42Z rc=0
$ keel mesh status; systemctl is-active keel-database-follow.path keel-database-follow.service keel-database-watch.timer keel-mesh-members.service etcd; systemctl --failed --no-legend
this node: fd11:a58a:88ef::1/64 on wg0, WireGuard on UDP 51820
mesh identity: 9fe71b35b8d35c5869faacc57ed2bc30
public key: 1bSgAuDppyY36XfEH2zxXeT5altQGehlT7Se2AVZyAg=
peers: 4
  o+GK/71E+YK/TO/pUkonxFP0DLcFdpPEm2ZlxJJ/VBc=  fd11:a58a:88ef::2/128  [<uplink>]:51820  handshake 17 s ago
  8Tjk29fOsZmTJ61L3LfEI2mm/LHFzAy+roHC49woQnc=  fd11:a58a:88ef:0:47d1:8a55:262c:33ed/128  [<uplink>]:51820  handshake 48 s ago
  li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY=  fd11:a58a:88ef:0:382f:45b:553c:f11/128  [<uplink>]:51820  handshake 243 s ago
  o9tGVm/IKImyW2kgn22YjiWdEXpAr28T6WF9uc4yW1Q=  fd11:a58a:88ef:0:cd53:dda9:f0cb:b889/128  [<uplink>]:51820  handshake 92 s ago
pending invites: 0
etcd: 3 voter(s), 0 learner(s)
  keel-fd11-a58a-88ef-0-47d1-8a55-262c-33ed  fd11:a58a:88ef:0:47d1:8a55:262c:33ed  voter  healthy
  keel-fd11-a58a-88ef--2  fd11:a58a:88ef::2  voter  healthy
  keel-fd11-a58a-88ef--1  fd11:a58a:88ef::1  voter  healthy
leader: keel-fd11-a58a-88ef--2
etcd: this member's certificate expires 2026-11-07 09:45 UTC
vip: none (this node declares no appliance.vip and routes no other pair's)
active
inactive
active
active
active
● systemd-networkd-wait-online.service loaded failed failed Wait for Network to be Configured

=== [125] 2026-10-08T23:42:58Z rc=0
$ date -u +%T; apt-get update -q 2>&1 | tail -1; DEBIAN_FRONTEND=noninteractive apt-get install -y -q --only-upgrade keel 2>&1 | grep -E "Unpacking|Setting up|rror|arn"; date -u +%T; dpkg-query -W keel keel-overlay-etcd keel-overlay-vip; keel --version; keel mesh status 2>&1; systemctl --failed --no-legend
23:42:48
Reading package lists...
Unpacking keel (0.23.3) over (0.22.0) ...
Setting up keel (0.23.3) ...
23:42:57
keel	0.23.3
keel-overlay-etcd	0.4.0
keel-overlay-vip	0.2.0
0.23.3
this node: fd11:a58a:88ef:0:47d1:8a55:262c:33ed/64 on wg0, WireGuard on UDP 51820
mesh identity: 9fe71b35b8d35c5869faacc57ed2bc30
public key: 8Tjk29fOsZmTJ61L3LfEI2mm/LHFzAy+roHC49woQnc=
peers: 3
  1bSgAuDppyY36XfEH2zxXeT5altQGehlT7Se2AVZyAg=  fd11:a58a:88ef::1/128  [<uplink>]:51820  handshake 63 s ago
  o+GK/71E+YK/TO/pUkonxFP0DLcFdpPEm2ZlxJJ/VBc=  fd11:a58a:88ef::2/128  [<uplink>]:51820  handshake 32 s ago
  li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY=  fd11:a58a:88ef:0:382f:45b:553c:f11/128  [<uplink>]:51820  no handshake known
pending invites: 0
etcd: 3 voter(s), 0 learner(s)
  keel-fd11-a58a-88ef-0-47d1-8a55-262c-33ed  fd11:a58a:88ef:0:47d1:8a55:262c:33ed  voter  healthy
  keel-fd11-a58a-88ef--2  fd11:a58a:88ef::2  voter  healthy
  keel-fd11-a58a-88ef--1  fd11:a58a:88ef::1  voter  healthy
leader: keel-fd11-a58a-88ef--2
etcd: this member's certificate expires 2026-11-07 09:45 UTC
vip: none (this node declares no appliance.vip and routes no other pair's)
● systemd-networkd-wait-online.service loaded failed failed Wait for Network to be Configured

=== [web2] 2026-10-08T23:43:42Z rc=0
$ date -u +%T; apt-get update -q 2>&1 | tail -1; DEBIAN_FRONTEND=noninteractive apt-get install -y -q --only-upgrade keel 2>&1 | grep -E "Unpacking|Setting up|rror|arn"; date -u +%T; dpkg-query -W keel keel-overlay-etcd keel-overlay-vip; keel --version; keel mesh status 2>&1; systemctl --failed --no-legend

23:43:01
Reading package lists...
Unpacking keel (0.23.3) over (0.22.0) ...
Setting up keel (0.23.3) ...
23:43:40
keel	0.23.3
keel-overlay-etcd	0.4.0
keel-overlay-vip	0.2.0
0.23.3
Warning: /etc/keel/instance.yaml: overlays.vip: not declared (default: disabled): the chain of web gained it after this spec was last applied, so it takes the manifest's default for cloud_advanced; write it out (decisions 0027, 0041)
this node: fd11:a58a:88ef::2/64 on wg0, WireGuard on UDP 51820
mesh identity: 9fe71b35b8d35c5869faacc57ed2bc30
public key: o+GK/71E+YK/TO/pUkonxFP0DLcFdpPEm2ZlxJJ/VBc=
peers: 2
  1bSgAuDppyY36XfEH2zxXeT5altQGehlT7Se2AVZyAg=  fd11:a58a:88ef::1/128  [<uplink>]:51820  handshake 76 s ago
  8Tjk29fOsZmTJ61L3LfEI2mm/LHFzAy+roHC49woQnc=  fd11:a58a:88ef:0:47d1:8a55:262c:33ed/128  [<uplink>]:51820  handshake 76 s ago
pending invites: 0
etcd: 3 voter(s), 0 learner(s)
  keel-fd11-a58a-88ef-0-47d1-8a55-262c-33ed  fd11:a58a:88ef:0:47d1:8a55:262c:33ed  voter  healthy
  keel-fd11-a58a-88ef--2  fd11:a58a:88ef::2  voter  healthy
  keel-fd11-a58a-88ef--1  fd11:a58a:88ef::1  voter  healthy
leader: keel-fd11-a58a-88ef--2
etcd: this member's certificate expires 2026-11-07 09:45 UTC
vip: none (this node declares no appliance.vip and routes no other pair's)
● keel-mesh-sync.service               loaded failed failed keel mesh: learn the members this node's peers know
● systemd-networkd-wait-online.service loaded failed failed Wait for Network to be Configured

=== [9003] 2026-10-08T23:43:49Z rc=0
$ hostname; dpkg-query -W keel keel-mariadb keel-overlay-etcd keel-overlay-vip mariadb-server 2>&1; keel --version; wg show wg0 | grep -E "peer|allowed|handshake"; ip -6 -br addr show wg0; cat /etc/keel/instance.yaml
keel-db-1
dpkg-query: no packages found matching keel-mariadb
keel	0.23.0
keel-overlay-etcd	0.4.0
keel-overlay-vip	0.2.0
mariadb-server	1:11.8.6-0+deb13u1
0.19.0
peer: 1bSgAuDppyY36XfEH2zxXeT5altQGehlT7Se2AVZyAg=
  allowed ips: fd11:a58a:88ef::1/128
  latest handshake: 5 minutes, 10 seconds ago
wg0              UNKNOWN        fd11:a58a:88ef:0:382f:45b:553c:f11/64 
version: 1
instance:
  hostname: keel-db-1
  fqdn: keel-db-1.pop.coop
tls:
  acme:
    domains:
    - keel-db-1.pop.coop
network:
  overlay:
    wireguard:
      address: fd11:a58a:88ef:0:382f:45b:553c:f11/64
      peers:
      - public_key: 1bSgAuDppyY36XfEH2zxXeT5altQGehlT7Se2AVZyAg=
        endpoint: '[<uplink>]:51820'
        allowed_ips:
        - fd11:a58a:88ef::1/128
      - public_key: o9tGVm/IKImyW2kgn22YjiWdEXpAr28T6WF9uc4yW1Q=
        endpoint: '[<uplink>]:51820'
        allowed_ips:
        - fd11:a58a:88ef:0:cd53:dda9:f0cb:b889/128

=== [9004] 2026-10-08T23:43:51Z rc=0
$ hostname; dpkg-query -W keel keel-mariadb keel-overlay-etcd keel-overlay-vip mariadb-server 2>&1; keel --version; wg show wg0 | grep -E "peer|allowed|handshake"; ip -6 -br addr show wg0; cat /etc/keel/instance.yaml
keel-db-2
dpkg-query: no packages found matching keel-mariadb
keel	0.23.0
keel-overlay-etcd	0.4.0
keel-overlay-vip	0.2.0
mariadb-server	1:11.8.6-0+deb13u1
0.19.0
peer: 1bSgAuDppyY36XfEH2zxXeT5altQGehlT7Se2AVZyAg=
  allowed ips: fd11:a58a:88ef::1/128
  latest handshake: 2 minutes, 41 seconds ago
peer: li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY=
  allowed ips: fd11:a58a:88ef:0:382f:45b:553c:f11/128
wg0              UNKNOWN        fd11:a58a:88ef:0:cd53:dda9:f0cb:b889/64 
version: 1
instance:
  hostname: keel-db-2
  fqdn: keel-db-2.pop.coop
tls:
  acme:
    domains:
    - keel-db-2.pop.coop
network:
  overlay:
    wireguard:
      address: fd11:a58a:88ef:0:cd53:dda9:f0cb:b889/64
      peers:
      - public_key: 1bSgAuDppyY36XfEH2zxXeT5altQGehlT7Se2AVZyAg=
        endpoint: '[<uplink>]:51820'
        allowed_ips:
        - fd11:a58a:88ef::1/128
      - public_key: li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY=
        endpoint: '[<uplink>]:51820'
        allowed_ips:
        - fd11:a58a:88ef:0:382f:45b:553c:f11/128

=== [9003] 2026-10-08T23:43:58Z rc=0
$ keel diff 2>&1 | grep -vE ": same|unchanged" | head -40; echo "diff rc=${PIPESTATUS[0]}"
network.overlay.wireguard.peers.o9tGVm/IKImyW2kgn22YjiWdEXpAr28T6WF9uc4yW1Q=.endpoint: drift (declared [<uplink>]:51820, observed nothing)
network.overlay.wireguard.peers.o9tGVm/IKImyW2kgn22YjiWdEXpAr28T6WF9uc4yW1Q=.allowed_ips: drift (declared fd11:a58a:88ef:0:cd53:dda9:f0cb:b889/128, observed nothing)
network.managed_by: not declared (observed file)
network.interfaces.eth0.ipv4.method: not declared (observed dhcp)
network.interfaces.eth0.ipv6.method: not declared (observed auto)
network.nameservers: not declared (observed <uplink>)
network.overlay.wireguard.private_key.file: not declared (observed /etc/wireguard/wg0.key)
tls.acme.domains: not compared (tls.acme is off in the spec (enabled is not declared), so what it governs is not compared; it takes effect when enabled becomes true)
tls.acme.enabled: not declared (observed false)
hub.api_key: not declared (observed skip)
security.alerts: not declared (observed skip)
security.updates_at_first_boot: not declared (observed skip)
locale.timezone: not declared (observed Etc/UTC)
locale.lang: not declared (observed C.UTF-8)
database.server.engine: not declared (observed mariadb)
database.server.role: not declared (observed standalone)
database.server.listen: not declared (observed *)
monitor.enabled: not declared (observed false)
appliance.name: not declared (observed core)
diff: 7 same, 2 drift, 0 unknown, 16 not declared, 1 not compared; drift found
diff rc=14

=== [9004] 2026-10-08T23:44:00Z rc=0
$ keel diff 2>&1 | grep -vE ": same|unchanged" | head -40; echo "diff rc=${PIPESTATUS[0]}"
network.managed_by: not declared (observed file)
network.interfaces.eth0.ipv4.method: not declared (observed dhcp)
network.interfaces.eth0.ipv6.method: not declared (observed auto)
network.nameservers: not declared (observed <uplink>)
network.overlay.wireguard.private_key.file: not declared (observed /etc/wireguard/wg0.key)
tls.acme.domains: not compared (tls.acme is off in the spec (enabled is not declared), so what it governs is not compared; it takes effect when enabled becomes true)
tls.acme.enabled: not declared (observed false)
hub.api_key: not declared (observed skip)
security.alerts: not declared (observed skip)
security.updates_at_first_boot: not declared (observed skip)
locale.timezone: not declared (observed Etc/UTC)
locale.lang: not declared (observed C.UTF-8)
database.server.engine: not declared (observed mariadb)
database.server.role: not declared (observed standalone)
database.server.listen: not declared (observed *)
monitor.enabled: not declared (observed false)
appliance.name: not declared (observed core)
diff: 9 same, 0 drift, 0 unknown, 16 not declared, 1 not compared; no drift
diff rc=0

=== [9003] 2026-10-08T23:44:15Z rc=0
$ date -u +%T; apt-get update -q 2>&1 | tail -1; apt-cache policy keel-mariadb | head -3; DEBIAN_FRONTEND=noninteractive apt-get install -y -q keel keel-mariadb 2>&1 | grep -vE "^(Reading|Building|Get:|Fetched|Selecting|\(Reading)" | tail -25; date -u +%T; dpkg-query -W keel keel-mariadb keel-overlay-etcd keel-overlay-vip; keel --version; ls -l /usr/share/keel/appliances/
23:44:07
Reading package lists...
keel-mariadb:
  Installed: (none)
  Candidate: 0.1.0
The following NEW packages will be installed:
  keel-mariadb
The following packages will be upgraded:
  keel
1 upgraded, 1 newly installed, 0 to remove and 0 not upgraded.
Need to get 405 kB of archives.
After this operation, 55.3 kB of additional disk space will be used.
[master 241b788] saving uncommitted changes in /etc prior to apt run
 6 files changed, 31 insertions(+), 2 deletions(-)
 create mode 120000 systemd/system/multi-user.target.wants/wg-quick@wg0.service
 create mode 100644 wireguard/wg0.conf
 create mode 100644 wireguard/wg0.key
Preparing to unpack .../archives/keel_0.23.3_all.deb ...
Unpacking keel (0.23.3) over (0.23.0) ...
Preparing to unpack .../keel-mariadb_0.1.0_all.deb ...
Unpacking keel-mariadb (0.1.0) ...
Setting up keel (0.23.3) ...
keel-mesh-sync.service is a disabled or a static unit not running, not starting it.
keel-mesh-etcd.service is a disabled or a static unit not running, not starting it.
keel-database-watch.service is a disabled or a static unit not running, not starting it.
Setting up keel-mariadb (0.1.0) ...
Processing triggers for keel-overlay-vip (0.2.0) ...
23:44:15
keel	0.23.3
keel-mariadb	0.1.0
keel-overlay-etcd	0.4.0
keel-overlay-vip	0.2.0
0.23.3
total 8
-rw-r--r-- 1 root root 1533 Oct  7 23:17 core.yaml
-rw-r--r-- 1 root root 1238 Oct  8 22:05 mariadb.yaml

=== [9004] 2026-10-08T23:44:26Z rc=0
$ date -u +%T; apt-get update -q 2>&1 | tail -1; apt-cache policy keel-mariadb | head -3; DEBIAN_FRONTEND=noninteractive apt-get install -y -q keel keel-mariadb 2>&1 | grep -vE "^(Reading|Building|Get:|Fetched|Selecting|\(Reading)" | tail -25; date -u +%T; dpkg-query -W keel keel-mariadb keel-overlay-etcd keel-overlay-vip; keel --version; ls -l /usr/share/keel/appliances/
23:44:17
Reading package lists...
keel-mariadb:
  Installed: (none)
  Candidate: 0.1.0
The following NEW packages will be installed:
  keel-mariadb
The following packages will be upgraded:
  keel
1 upgraded, 1 newly installed, 0 to remove and 0 not upgraded.
Need to get 405 kB of archives.
After this operation, 55.3 kB of additional disk space will be used.
[master f4f5f22] saving uncommitted changes in /etc prior to apt run
 5 files changed, 35 insertions(+), 1 deletion(-)
 create mode 120000 systemd/system/multi-user.target.wants/wg-quick@wg0.service
 create mode 100644 wireguard/wg0.conf
 create mode 100644 wireguard/wg0.key
Preparing to unpack .../archives/keel_0.23.3_all.deb ...
Unpacking keel (0.23.3) over (0.23.0) ...
Preparing to unpack .../keel-mariadb_0.1.0_all.deb ...
Unpacking keel-mariadb (0.1.0) ...
Setting up keel (0.23.3) ...
keel-mesh-sync.service is a disabled or a static unit not running, not starting it.
keel-mesh-etcd.service is a disabled or a static unit not running, not starting it.
keel-database-watch.service is a disabled or a static unit not running, not starting it.
Setting up keel-mariadb (0.1.0) ...
Processing triggers for keel-overlay-vip (0.2.0) ...
23:44:25
keel	0.23.3
keel-mariadb	0.1.0
keel-overlay-etcd	0.4.0
keel-overlay-vip	0.2.0
0.23.3
total 8
-rw-r--r-- 1 root root 1533 Oct  7 23:17 core.yaml
-rw-r--r-- 1 root root 1238 Oct  8 22:05 mariadb.yaml

=== [9003] 2026-10-08T23:44:33Z rc=0
$ cat /usr/share/keel/appliances/mariadb.yaml; stat -c "%a %U %n" /etc/.git /etc/wireguard/wg0.key; cd /etc && git ls-files wireguard
manifest_version: 1
kind: appliance
name: mariadb
title: Keel MariaDB
summary: The MariaDB database layer on Keel Core, alone or as a replicated pair (0047, 0049)
base: core
# The overlays are Core's, inherited with their states (installer, wireguard,
# etcd, crowdsec, vip): this layer adds none, and a spec that names it writes
# all five out (0027).
processes:
  - name: mariadb
    unit: mariadb.service
    # ::1 and 127.0.0.1 as the layer ships it; on a pair database.server.listen
    # adds the node's overlay address and the VIP, so 3306 is a mesh port: on
    # the WireGuard interface in cloud advanced, never on the uplink.
    listen: [{port: 3306, protocol: tcp, expose: mesh}]
checks:
  - {name: mariadb, process: mariadb, type: protocol, protocol: mysql,
     address: loopback, port: 3306, on_failure: restart}
secrets:
  - name: db_password
    description: The MariaDB administrative account, set at the first boot from DB_PASS
    generate: allowed
    # the mysql database replicates with the rest: a pair holds one value
    shared: true
options:
  - name: db_user
    type: string
    default: admin
    # a name that needs no quoting in a GRANT, the rule of lib/mariadb.sh
    pattern: '^[A-Za-z_][A-Za-z0-9_-]*$'
700 root /etc/.git
600 root /etc/wireguard/wg0.key
wireguard/wg0.conf
wireguard/wg0.key

=== [9003] 2026-10-08T23:44:52Z rc=0
$ date -u +%T; timeout 300 keel mesh sync 2>&1 | tail -30; echo "sync rc=${PIPESTATUS[0]}"; date -u +%T; wg show wg0 | grep -E "peer|allowed|handshake"
23:44:39
member fd11:a58a:88ef:0:cd53:dda9:f0cb:b889 did not answer: [fd11:a58a:88ef:0:cd53:dda9:f0cb:b889]:51821 through wg0: timed out
the spec names 1 peer(s) that wg0 lacks: o9tGVm/IKImyW2kgn22YjiWdEXpAr28T6WF9uc4yW1Q=; the overlay is applied again (keel#96)
member o9tGVm/IKImyW2kgn22YjiWdEXpAr28T6WF9uc4yW1Q= applied again at fd11:a58a:88ef:0:cd53:dda9:f0cb:b889, through [<uplink>]:51820
confirming over the overlay…
confirmed from a WireGuard handshake from o9tGVm/IKImyW2kgn22YjiWdEXpAr28T6WF9uc4yW1Q= (23:44:50 UTC), a member of the changed overlay
the overlay was tested: a WireGuard handshake from o9tGVm/IKImyW2kgn22YjiWdEXpAr28T6WF9uc4yW1Q= (23:44:50 UTC), a member of the changed overlay arrived at fd11:a58a:88ef:0:382f:45b:553c:f11 on wg0, from fd11:a58a:88ef:0:cd53:dda9:f0cb:b889
wg-quick@wg0 enabled: the overlay comes back up at boot
the network change stays; the revert is cancelled
sync rc=0
23:44:52
peer: o9tGVm/IKImyW2kgn22YjiWdEXpAr28T6WF9uc4yW1Q=
  allowed ips: fd11:a58a:88ef:0:cd53:dda9:f0cb:b889/128
  latest handshake: 2 seconds ago
peer: 1bSgAuDppyY36XfEH2zxXeT5altQGehlT7Se2AVZyAg=
  allowed ips: fd11:a58a:88ef::1/128

=== [9004] 2026-10-08T23:45:00Z rc=0
$ date -u +%T; timeout 300 keel mesh sync 2>&1 | tail -30; echo "sync rc=${PIPESTATUS[0]}"; date -u +%T; wg show wg0 | grep -E "peer|allowed|handshake"; keel mesh status
23:45:00
no member this node does not know: it is a peer of every admitted member its peers know
sync rc=0
23:45:00
peer: 1bSgAuDppyY36XfEH2zxXeT5altQGehlT7Se2AVZyAg=
  allowed ips: fd11:a58a:88ef::1/128
  latest handshake: Now
peer: li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY=
  allowed ips: fd11:a58a:88ef:0:382f:45b:553c:f11/128
  latest handshake: 10 seconds ago
this node: fd11:a58a:88ef:0:cd53:dda9:f0cb:b889/64 on wg0, WireGuard on UDP 51820
mesh identity: 9fe71b35b8d35c5869faacc57ed2bc30
public key: o9tGVm/IKImyW2kgn22YjiWdEXpAr28T6WF9uc4yW1Q=
peers: 2
  1bSgAuDppyY36XfEH2zxXeT5altQGehlT7Se2AVZyAg=  fd11:a58a:88ef::1/128  [<uplink>]:51820  handshake 0 s ago
  li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY=  fd11:a58a:88ef:0:382f:45b:553c:f11/128  [<uplink>]:51820  handshake 10 s ago
pending invites: 0
etcd: not on this node (installation.mode not declared; etcd runs on cloud advanced members only)
vip: none (this node declares no appliance.vip and routes no other pair's)

=== [9003] 2026-10-08T23:45:03Z rc=0
$ timeout 300 keel mesh sync 2>&1 | tail -10; echo "sync rc=${PIPESTATUS[0]}"; keel mesh status
no member this node does not know: it is a peer of every admitted member its peers know
sync rc=0
this node: fd11:a58a:88ef:0:382f:45b:553c:f11/64 on wg0, WireGuard on UDP 51820
mesh identity: 9fe71b35b8d35c5869faacc57ed2bc30
public key: li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY=
peers: 2
  1bSgAuDppyY36XfEH2zxXeT5altQGehlT7Se2AVZyAg=  fd11:a58a:88ef::1/128  [<uplink>]:51820  handshake 8 s ago
  o9tGVm/IKImyW2kgn22YjiWdEXpAr28T6WF9uc4yW1Q=  fd11:a58a:88ef:0:cd53:dda9:f0cb:b889/128  [<uplink>]:51820  handshake 13 s ago
pending invites: 0
etcd: not on this node (installation.mode not declared; etcd runs on cloud advanced members only)
vip: none (this node declares no appliance.vip and routes no other pair's)

=== [125] 2026-10-08T23:45:16Z rc=0
$ systemctl list-timers keel-mesh-sync.timer --no-legend; journalctl -u keel-mesh-sync.service --since "-30min" --no-pager -o short-iso | grep -vE "unchanged" | tail -8
Thu 2026-10-08 23:45:26 UTC 10s Thu 2026-10-08 23:29:40 UTC 15min ago keel-mesh-sync.timer keel-mesh-sync.service
2026-10-08T23:15:52+00:00 keel-web-3 systemd[1]: Failed to start keel-mesh-sync.service - keel mesh: learn the members this node's peers know.
2026-10-08T23:15:52+00:00 keel-web-3 systemd[1]: keel-mesh-sync.service: Consumed 1.018s CPU time, 24.9M memory peak.
2026-10-08T23:29:40+00:00 keel-web-3 systemd[1]: Starting keel-mesh-sync.service - keel mesh: learn the members this node's peers know...
2026-10-08T23:29:51+00:00 keel-web-3 keel[90303]: member fd11:a58a:88ef:0:382f:45b:553c:f11 did not answer: [fd11:a58a:88ef:0:382f:45b:553c:f11]:51821 through wg0: timed out
2026-10-08T23:29:51+00:00 keel-web-3 keel[90303]: o9tGVm/IKImyW2kgn22YjiWdEXpAr28T6WF9uc4yW1Q= is tried again after 00:15 UTC: it did not answer the last time
2026-10-08T23:29:51+00:00 keel-web-3 keel[90303]: no member this node does not know: it is a peer of every admitted member its peers know
2026-10-08T23:29:51+00:00 keel-web-3 systemd[1]: keel-mesh-sync.service: Deactivated successfully.
2026-10-08T23:29:51+00:00 keel-web-3 systemd[1]: Finished keel-mesh-sync.service - keel mesh: learn the members this node's peers know.

=== [web2] 2026-10-08T23:45:20Z rc=0
$ systemctl list-timers keel-mesh-sync.timer --no-legend; journalctl -u keel-mesh-sync.service --since "-30min" --no-pager -o short-iso | grep -vE "unchanged" | tail -8

Thu 2026-10-08 23:49:20 UTC 3min 59s Thu 2026-10-08 23:33:51 UTC 11min ago keel-mesh-sync.timer keel-mesh-sync.service
2026-10-08T23:34:23+00:00 keel-web-2 keel[12940]: confirming over the overlay…
2026-10-08T23:36:20+00:00 keel-web-2 keel[12940]: network.overlay: bring the overlay wg0 up on a new /etc/wireguard/wg0.conf (wg-quick down, then up); it reverts in 120 s unless `keel network confirm` is run from a new session, over the overlay or the uplink: done
2026-10-08T23:36:20+00:00 keel-web-2 keel[12940]: keel mesh: 1 change(s), 0 failed
2026-10-08T23:36:20+00:00 keel-web-2 keel[12940]: no member completed a WireGuard handshake within the window: the change reverts by itself, the spec is put back as it was, and keel mesh sync tries again (a new member after an hour)
2026-10-08T23:36:20+00:00 keel-web-2 systemd[1]: keel-mesh-sync.service: Main process exited, code=exited, status=21/n/a
2026-10-08T23:36:20+00:00 keel-web-2 systemd[1]: keel-mesh-sync.service: Failed with result 'exit-code'.
2026-10-08T23:36:20+00:00 keel-web-2 systemd[1]: Failed to start keel-mesh-sync.service - keel mesh: learn the members this node's peers know.
2026-10-08T23:36:20+00:00 keel-web-2 systemd[1]: keel-mesh-sync.service: Consumed 1.945s CPU time, 24M memory peak.

=== [9003] 2026-10-08T23:45:21Z rc=0
$ systemctl list-timers keel-mesh-sync.timer --no-legend
Thu 2026-10-08 23:55:38 UTC 10min Thu 2026-10-08 23:40:25 UTC 4min 56s ago keel-mesh-sync.timer keel-mesh-sync.service

=== [125] 2026-10-08T23:45:40Z rc=0
$ journalctl -u keel-mesh-sync.service --since "23:45" --no-pager -o short-iso | grep -v unchanged | tail -8; wg show wg0 allowed-ips
-- No entries --
1bSgAuDppyY36XfEH2zxXeT5altQGehlT7Se2AVZyAg=	fd11:a58a:88ef::1/128
o+GK/71E+YK/TO/pUkonxFP0DLcFdpPEm2ZlxJJ/VBc=	fd11:a58a:88ef::2/128

=== [9003] 2026-10-08T23:45:43Z rc=0
$ keel inspect 2>/dev/null | sed -n "/^appliance/,/^[a-z]/p;/^installation/,/^[a-z]/p;/^overlays/,/^[a-z]/p;/^database/,/^[a-z]/p"
database:
  server:
    engine: mariadb
    role: standalone
    listen:
    - '*'
locale:
appliance:
  name: mariadb
overlays:
overlays:
  wireguard: enabled
  etcd: disabled
  crowdsec: disabled
  vip: disabled
firewall:

=== [125] 2026-10-08T23:45:50Z rc=0
$ systemctl list-timers keel-mesh-sync.timer --no-legend; grep -c public_key /etc/keel/instance.yaml; grep -A1 public_key /etc/keel/instance.yaml; journalctl --since "23:40" --no-pager -o short-iso | grep -iE "keel|wg|wireguard" | grep -v unchanged | tail -20
- - Thu 2026-10-08 23:45:40 UTC 9s ago keel-mesh-sync.timer keel-mesh-sync.service
3
      - public_key: 1bSgAuDppyY36XfEH2zxXeT5altQGehlT7Se2AVZyAg=
        endpoint: '[<uplink>]:51820'
--
      - public_key: o+GK/71E+YK/TO/pUkonxFP0DLcFdpPEm2ZlxJJ/VBc=
        endpoint: '[<uplink>]:51820'
--
      - public_key: li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY=
        endpoint: '[<uplink>]:51820'
2026-10-08T23:42:55+00:00 keel-web-3 systemd[1]: keel-database-watch.service - keel database: the semi-synchronous fallback, the certificate skipped, unmet condition check ConditionPathExists=/var/lib/keel/database
2026-10-08T23:42:55+00:00 keel-web-3 systemd[1]: Reload requested from client PID 91032 ('systemctl')...
2026-10-08T23:42:55+00:00 keel-web-3 systemd[1]: Reloading...
2026-10-08T23:42:55+00:00 keel-web-3 systemd[1]: Configuration file /usr/lib/systemd/system/container-getty@.service is marked world-inaccessible. This has no effect as configuration data is accessible via APIs without restrictions. Proceeding anyway.
2026-10-08T23:42:55+00:00 keel-web-3 systemd[1]: Configuration file /usr/lib/systemd/system/container-getty@.service is marked world-inaccessible. This has no effect as configuration data is accessible via APIs without restrictions. Proceeding anyway.
2026-10-08T23:42:55+00:00 keel-web-3 systemd[1]: Reloading finished in 237 ms.
2026-10-08T23:43:24+00:00 keel-web-3 systemd-networkd-wait-online[90945]: Timeout occurred while waiting for network connectivity.
2026-10-08T23:43:24+00:00 keel-web-3 apt-helper[90934]: E: Sub-process /lib/systemd/systemd-networkd-wait-online returned an error code (1)
2026-10-08T23:43:24+00:00 keel-web-3 systemd[1]: apt-daily.service: Deactivated successfully.
2026-10-08T23:43:24+00:00 keel-web-3 systemd[1]: Finished apt-daily.service - Daily apt download activities.
2026-10-08T23:43:29+00:00 keel-web-3 systemd[1]: keel-database-watch.service - keel database: the semi-synchronous fallback, the certificate skipped, unmet condition check ConditionPathExists=/var/lib/keel/database
2026-10-08T23:44:00+00:00 keel-web-3 systemd[1]: keel-database-watch.service - keel database: the semi-synchronous fallback, the certificate skipped, unmet condition check ConditionPathExists=/var/lib/keel/database
2026-10-08T23:44:35+00:00 keel-web-3 systemd[1]: keel-database-watch.service - keel database: the semi-synchronous fallback, the certificate skipped, unmet condition check ConditionPathExists=/var/lib/keel/database
2026-10-08T23:44:39+00:00 keel-web-3 etcd[79432]: {"level":"info","ts":"2026-10-08T23:44:39.715253Z","caller":"auth/store.go:832","msg":"granted/updated a permission to a user","user-name":"keel-member","permission-name":"READWRITE"}
2026-10-08T23:45:10+00:00 keel-web-3 systemd[1]: keel-database-watch.service - keel database: the semi-synchronous fallback, the certificate skipped, unmet condition check ConditionPathExists=/var/lib/keel/database
2026-10-08T23:45:10+00:00 keel-web-3 systemd[1]: Starting keel-mesh-etcd.service - keel mesh: tend etcd's learners and this member's certificates...
2026-10-08T23:45:11+00:00 keel-web-3 systemd[1]: keel-mesh-etcd.service: Deactivated successfully.
2026-10-08T23:45:11+00:00 keel-web-3 systemd[1]: Finished keel-mesh-etcd.service - keel mesh: tend etcd's learners and this member's certificates.
2026-10-08T23:45:40+00:00 keel-web-3 systemd[1]: keel-database-watch.service - keel database: the semi-synchronous fallback, the certificate skipped, unmet condition check ConditionPathExists=/var/lib/keel/database
2026-10-08T23:45:40+00:00 keel-web-3 systemd[1]: Starting keel-mesh-sync.service - keel mesh: learn the members this node's peers know...

=== [9003] 2026-10-08T23:46:05Z rc=0
$ cp -a /etc/keel/instance.yaml /root/instance.yaml.before-pair && ls -l /root/instance.yaml.before-pair; keel database status 2>&1 | head -20
-rw------- 1 root root 601 Oct  8 23:44 /root/instance.yaml.before-pair
pair: none (this node declares no appliance.vip); declared role none
server: standalone (mariadb --batch --execute SHOW REPLICA STATUS\G is empty, no replica is connected and no replication is granted from anywhere but this machine)
  read_only: false
  semi-synchronous: master OFF, slave OFF, 0 replica(s) acknowledging, 0 commits acknowledged, 0 not
  replicating from: nobody
  certificate: none
vip: none (this node declares no appliance.vip and routes no other pair's)

=== [9004] 2026-10-08T23:46:07Z rc=0
$ cp -a /etc/keel/instance.yaml /root/instance.yaml.before-pair && ls -l /root/instance.yaml.before-pair; keel database status 2>&1 | head -20
-rw------- 1 root root 601 Oct  8 20:05 /root/instance.yaml.before-pair
pair: none (this node declares no appliance.vip); declared role none
server: standalone (mariadb --batch --execute SHOW REPLICA STATUS\G is empty, no replica is connected and no replication is granted from anywhere but this machine)
  read_only: false
  semi-synchronous: master OFF, slave OFF, 0 replica(s) acknowledging, 0 commits acknowledged, 0 not
  replicating from: nobody
  certificate: none
vip: none (this node declares no appliance.vip and routes no other pair's)

=== [125] 2026-10-08T23:46:09Z rc=0
$ for i in $(seq 1 90); do systemctl is-active -q keel-mesh-sync.service || systemctl is-activating -q keel-mesh-sync.service 2>/dev/null || break; s=$(systemctl show -p ActiveState --value keel-mesh-sync.service); [ "$s" = activating ] || [ "$s" = active ] || break; sleep 2; done; date -u +%T; journalctl -u keel-mesh-sync.service --since "23:45:30" --no-pager -o cat | grep -v unchanged | tail -12; wg show wg0 allowed-ips; wg show wg0 latest-handshakes
23:46:09
Starting keel-mesh-sync.service - keel mesh: learn the members this node's peers know...
member fd11:a58a:88ef:0:382f:45b:553c:f11 did not answer: [fd11:a58a:88ef:0:382f:45b:553c:f11]:51821 through wg0: timed out
o9tGVm/IKImyW2kgn22YjiWdEXpAr28T6WF9uc4yW1Q= is tried again after 00:15 UTC: it did not answer the last time
the spec names 1 peer(s) that wg0 lacks: li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY=; the overlay is applied again (keel#96)
member li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY= applied again at fd11:a58a:88ef:0:382f:45b:553c:f11, through [<uplink>]:51820
confirming over the overlay…
1bSgAuDppyY36XfEH2zxXeT5altQGehlT7Se2AVZyAg=	fd11:a58a:88ef::1/128
o+GK/71E+YK/TO/pUkonxFP0DLcFdpPEm2ZlxJJ/VBc=	fd11:a58a:88ef::2/128
li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY=	fd11:a58a:88ef:0:382f:45b:553c:f11/128
1bSgAuDppyY36XfEH2zxXeT5altQGehlT7Se2AVZyAg=	1791503152
o+GK/71E+YK/TO/pUkonxFP0DLcFdpPEm2ZlxJJ/VBc=	1791503167
li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY=	0

=== [9003] 2026-10-08T23:46:19Z rc=0
$ cat >> /etc/keel/instance.yaml <<EOF
appliance:
  name: mariadb
  vip: fd11:a58a:88ef::ffff:1
installation:
  mode: cloud_simple
overlays:
  installer: enabled
  wireguard: enabled
  etcd: disabled
  crowdsec: disabled
  vip: enabled
database:
  server:
    engine: mariadb
    role: primary
    listen: [fd11:a58a:88ef:0:382f:45b:553c:f11, "::1"]
EOF
keel spec validate 2>&1; echo rc=$?
/etc/keel/instance.yaml: ok (secret files checked)
rc=0

=== [9004] 2026-10-08T23:46:21Z rc=0
$ cat >> /etc/keel/instance.yaml <<EOF
appliance:
  name: mariadb
  vip: fd11:a58a:88ef::ffff:1
installation:
  mode: cloud_simple
overlays:
  installer: enabled
  wireguard: enabled
  etcd: disabled
  crowdsec: disabled
  vip: enabled
database:
  server:
    engine: mariadb
    role: replica
    listen: [fd11:a58a:88ef:0:cd53:dda9:f0cb:b889, "::1"]
EOF
keel spec validate 2>&1; echo rc=$?
/etc/keel/instance.yaml: ok (secret files checked)
rc=0

=== [9003] 2026-10-08T23:46:29Z rc=0
$ date -u +%T; timeout 120 keel vip pair fd11:a58a:88ef:0:cd53:dda9:f0cb:b889 2>&1; echo rc=$?; ls -l /var/lib/keel/vip/
23:46:28
fd11:a58a:88ef::ffff:1 is the VIP of li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY= and o9tGVm/IKImyW2kgn22YjiWdEXpAr28T6WF9uc4yW1Q=, signed by both
rc=0
total 4
-rw------- 1 root root 498 Oct  8 23:46 fd11:a58a:88ef::ffff:1.pair

=== [9004] 2026-10-08T23:46:31Z rc=0
$ ls -l /var/lib/keel/vip/
total 4
-rw------- 1 root root 498 Oct  8 23:46 fd11:a58a:88ef::ffff:1.pair

=== [9003] 2026-10-08T23:46:37Z rc=0
$ keel spec apply --help 2>&1 | head -40
usage: keel spec apply [-h] [--spec FILE] [--conf FILE] [--non-interactive]
                       [--system | --system-only] [--dry-run]
                       [--destroy-local-database] [--defer-certificate]
                       [--network-window SECONDS] [--skip-network]
                       [--skip-uplink] [--root DIR]

options:
  -h, --help            show this help message and exit
  --spec FILE           instance spec to read (default: $KEEL_SPEC or
                        /etc/keel/instance.yaml)
  --conf FILE           conf file to write (default: $KEEL_CONF or
                        /etc/inithooks.conf)
  --non-interactive     never prompt (the default, accepted for callers that
                        pass it)
  --system              after the conf, converge the system state the spec
                        declares (the fully qualified name in /etc/hosts,
                        users with their authorized keys, locale, timezone);
                        root on the live system (default: the conf only)
  --system-only         the system state and nothing else: the conf is neither
                        read nor written and no secret is resolved, so a
                        generated password the hooks already applied is never
                        regenerated; for a machine whose conf phase has
                        already run (docs/apply.md)
  --dry-run             with --system or --system-only: print the plan and
                        change nothing, not even the conf
  --destroy-local-database
                        confirm, for this run only, that making this node a
                        replica of the declared primary may drop the databases
                        it holds; a replica is a copy of its primary, so there
                        is no other way. Without it apply refuses and changes
                        nothing, which is what a first boot gets
                        (docs/apply.md)
  --defer-certificate   with --system or --system-only: write tls.acme but ask
                        no certificate authority for a certificate in this
                        run; the first boot hook passes it, since DNS rarely
                        points at a machine that is still booting
                        (docs/apply.md)
  --network-window SECONDS
                        with --system or --system-only: how long a network
                        change waits for keel network confirm before it

=== [9003] 2026-10-08T23:46:44Z rc=0
$ keel spec apply --system-only --dry-run 2>&1 | grep -v unchanged | tail -40; echo rc=${PIPESTATUS[0]}
apply --system-only: /etc/inithooks.conf not read or written
database.server: would make or renew the database certificate for fd11:a58a:88ef:0:382f:45b:553c:f11 and fd11:a58a:88ef::ffff:1, signed by the mesh's root CA (here, or asked of its holder over the members' channel), under /etc/mysql/keel-tls
database.server: would write /etc/sysctl.d/90-keel-database.conf: both nodes bind the VIP (mode 0644)
database.server: would let the server bind the VIP before it carries it (sysctl -q -w net.ipv6.ip_nonlocal_bind=1)
database.server: would write /etc/mysql/mariadb.conf.d/99-keel-database.cnf: a paired node, server id 388044305, binary log, GTID strict, semi-synchronous replication, TLS, the VIP fd11:a58a:88ef::ffff:1 bound (mode 0644)
database.server: would restart the server, which is the only way these take effect (systemctl restart mariadb)
database.server.replication.allowed_from: would authorize replication from fd11:a58a:88ef:0:cd53:dda9:f0cb:b889 with the certificate /CN=keel-fd11-a58a-88ef-0-cd53-dda9-f0cb-b889 mariadb of the mesh's root, outside the binary log (runuser -u mysql -- mariadb --batch, 5 statement(s) on standard input)
database.server.role: no claim of fd11:a58a:88ef::ffff:1 is known yet, so the declared role, primary, stands until keel vip promote on the primary claims it
database.server.role: would make the server follow the pair's VIP (keel database follow): the holder writable, the other node read only and replicating from the holder over TLS, an old primary rejoined by GTID when it holds nothing the holder lacks
derived.monit: would write /etc/keel/monit/keel-manifest.conf: 5 unit(s) and 4 probe(s) of mariadb (mode 0600)
overlays.vip: would enable keel-vip.service: the overlay is enabled (systemctl enable keel-vip.service)
overlays.vip: would start keel-vip.service (systemctl start keel-vip.service)
dry run: 10 change(s) planned, nothing written
rc=0

=== [9003] 2026-10-08T23:46:51Z rc=0
$ date -u +%T; timeout 400 keel spec apply --system-only 2>&1 | grep -v unchanged | tail -40; echo rc=${PIPESTATUS[0]}; date -u +%T
23:46:49
apply --system-only: /etc/inithooks.conf not read or written
database.server: make or renew the database certificate for fd11:a58a:88ef:0:382f:45b:553c:f11 and fd11:a58a:88ef::ffff:1, signed by the mesh's root CA (here, or asked of its holder over the members' channel), under /etc/mysql/keel-tls: failed: the root CA's holder at fd11:a58a:88ef:0:cd53:dda9:f0cb:b889 did not sign the database certificate ([fd11:a58a:88ef:0:cd53:dda9:f0cb:b889]:51821 refused: this node does not hold the mesh's root CA)
database.server: skipped: write /etc/sysctl.d/90-keel-database.conf: both nodes bind the VIP (mode 0644)
database.server: skipped: let the server bind the VIP before it carries it (sysctl -q -w net.ipv6.ip_nonlocal_bind=1)
database.server: skipped: write /etc/mysql/mariadb.conf.d/99-keel-database.cnf: a paired node, server id 388044305, binary log, GTID strict, semi-synchronous replication, TLS, the VIP fd11:a58a:88ef::ffff:1 bound (mode 0644)
database.server: skipped: restart the server, which is the only way these take effect (systemctl restart mariadb)
database.server.replication.allowed_from: authorize replication from fd11:a58a:88ef:0:cd53:dda9:f0cb:b889 with the certificate /CN=keel-fd11-a58a-88ef-0-cd53-dda9-f0cb-b889 mariadb of the mesh's root, outside the binary log (runuser -u mysql -- mariadb --batch, 5 statement(s) on standard input): done
database.server.role: no claim of fd11:a58a:88ef::ffff:1 is known yet, so the declared role, primary, stands until keel vip promote on the primary claims it
database.server.role: make the server follow the pair's VIP (keel database follow): the holder writable, the other node read only and replicating from the holder over TLS, an old primary rejoined by GTID when it holds nothing the holder lacks: done
derived.monit: write /etc/keel/monit/keel-manifest.conf: 5 unit(s) and 4 probe(s) of mariadb (mode 0600): done
overlays.vip: enable keel-vip.service: the overlay is enabled (systemctl enable keel-vip.service): done
overlays.vip: start keel-vip.service (systemctl start keel-vip.service): done
apply --system-only: 5 change(s), 1 failed
rc=16
23:46:51

=== [9003] 2026-10-08T23:47:08Z rc=0
$ ls -la /var/lib/keel/etcd 2>&1; ls /var/lib/keel
ls: cannot access '/var/lib/keel/etcd': No such file or directory
database
mesh
network
role
vip

=== [124] 2026-10-08T23:47:09Z rc=0
$ cat /var/lib/keel/etcd/holder; echo; ls -l /var/lib/keel/etcd/
fd11:a58a:88ef::1

total 68
-rw------- 1 root root  648 Oct  8 09:45 admin.crt
-rw------- 1 root root  241 Oct  8 09:45 admin.key
-rw------- 1 root root 1048 Oct  4 23:07 cluster.json
-rw------- 1 root root  475 Oct  8 09:46 crl.pem
-rw------- 1 root root    2 Oct  4 23:07 epoch
-rw------- 1 root root 1048 Oct  4 23:07 formation.json
-rw------- 1 root root   18 Oct  8 09:45 holder
-rw------- 1 root root  879 Oct  8 09:45 issued.json
-rw------- 1 root root    3 Oct  8 23:44 learners.json
-rw------- 1 root root    0 Oct  4 23:07 lock
-rw------- 1 root root  753 Oct  8 09:45 member.crt
-rw------- 1 root root  241 Oct  4 23:07 member.key
-rw------- 1 root root  227 Oct  4 23:07 ready.json
-rw------- 1 root root    3 Oct  8 23:44 renewal.json
-rw------- 1 root root  217 Oct  8 09:46 revoked.json
-rw------- 1 root root  668 Oct  8 09:45 root.crt
-rw------- 1 root root  241 Oct  4 23:07 root.key
-rw------- 1 root root    8 Oct  8 09:46 started

=== [9003] 2026-10-08T23:47:30Z rc=0
$ date -u +%T; timeout 400 keel spec apply --system-only 2>&1 | grep -E "certificate|change\(s\)" | tail -5; echo rc=${PIPESTATUS[0]}
23:47:29
database.server: make or renew the database certificate for fd11:a58a:88ef:0:382f:45b:553c:f11 and fd11:a58a:88ef::ffff:1, signed by the mesh's root CA (here, or asked of its holder over the members' channel), under /etc/mysql/keel-tls: failed: the root CA's holder at fd11:a58a:88ef:0:cd53:dda9:f0cb:b889 did not sign the database certificate ([fd11:a58a:88ef:0:cd53:dda9:f0cb:b889]:51821 refused: this node does not hold the mesh's root CA)
database.server.replication.allowed_from: authorize replication from fd11:a58a:88ef:0:cd53:dda9:f0cb:b889 with the certificate /CN=keel-fd11-a58a-88ef-0-cd53-dda9-f0cb-b889 mariadb of the mesh's root, outside the binary log (runuser -u mysql -- mariadb --batch, 5 statement(s) on standard input): done
apply --system-only: 3 change(s), 1 failed
rc=16

=== [9003] 2026-10-08T23:47:38Z rc=0
$ install -d -m 0700 /var/lib/keel/etcd && printf "fd11:a58a:88ef::1\n" > /var/lib/keel/etcd/holder && chmod 600 /var/lib/keel/etcd/holder && ls -la /var/lib/keel/etcd
total 12
drwx------ 2 root root 4096 Oct  8 23:47 .
drwxr-xr-x 7 root root 4096 Oct  8 23:47 ..
-rw------- 1 root root   18 Oct  8 23:47 holder

=== [9004] 2026-10-08T23:47:39Z rc=0
$ install -d -m 0700 /var/lib/keel/etcd && printf "fd11:a58a:88ef::1\n" > /var/lib/keel/etcd/holder && chmod 600 /var/lib/keel/etcd/holder && ls -la /var/lib/keel/etcd
total 12
drwx------ 2 root root 4096 Oct  8 23:47 .
drwxr-xr-x 7 root root 4096 Oct  8 23:47 ..
-rw------- 1 root root   18 Oct  8 23:47 holder

=== [9003] 2026-10-08T23:47:44Z rc=0
$ date -u +%T; timeout 400 keel spec apply --system-only 2>&1 | grep -v unchanged | tail -30; echo rc=${PIPESTATUS[0]}; date -u +%T
23:47:41
database.server.tls: the database certificate for fd11:a58a:88ef:0:382f:45b:553c:f11 and fd11:a58a:88ef::ffff:1, signed by the mesh's root, until 2026-11-07
database.server.role: set read_only OFF: this role takes the application's writes
apply --system-only: /etc/inithooks.conf not read or written
database.server: make or renew the database certificate for fd11:a58a:88ef:0:382f:45b:553c:f11 and fd11:a58a:88ef::ffff:1, signed by the mesh's root CA (here, or asked of its holder over the members' channel), under /etc/mysql/keel-tls: done
database.server: write /etc/sysctl.d/90-keel-database.conf: both nodes bind the VIP (mode 0644): done
database.server: let the server bind the VIP before it carries it (sysctl -q -w net.ipv6.ip_nonlocal_bind=1): done
database.server: write /etc/mysql/mariadb.conf.d/99-keel-database.cnf: a paired node, server id 388044305, binary log, GTID strict, semi-synchronous replication, TLS, the VIP fd11:a58a:88ef::ffff:1 bound (mode 0644): done
database.server: restart the server, which is the only way these take effect (systemctl restart mariadb): done
database.server.replication.allowed_from: authorize replication from fd11:a58a:88ef:0:cd53:dda9:f0cb:b889 with the certificate /CN=keel-fd11-a58a-88ef-0-cd53-dda9-f0cb-b889 mariadb of the mesh's root, outside the binary log (runuser -u mysql -- mariadb --batch, 5 statement(s) on standard input): done
database.server.role: no claim of fd11:a58a:88ef::ffff:1 is known yet, so the declared role, primary, stands until keel vip promote on the primary claims it
database.server.role: make the server follow the pair's VIP (keel database follow): the holder writable, the other node read only and replicating from the holder over TLS, an old primary rejoined by GTID when it holds nothing the holder lacks: done
overlays.vip: start keel-vip.service (systemctl start keel-vip.service): done
apply --system-only: 8 change(s), 0 failed
rc=0
23:47:44

=== [9004] 2026-10-08T23:47:55Z rc=0
$ date -u +%T; timeout 400 keel spec apply --system-only 2>&1 | grep -v unchanged | tail -30; echo rc=${PIPESTATUS[0]}; date -u +%T
23:47:51
database.server.tls: the database certificate for fd11:a58a:88ef:0:cd53:dda9:f0cb:b889 and fd11:a58a:88ef::ffff:1, signed by the mesh's root, until 2026-11-07
database.server.role: seeded from [fd11:a58a:88ef:0:382f:45b:553c:f11]:3306 and replicating from it over TLS
apply --system-only: /etc/inithooks.conf not read or written
database.server: make or renew the database certificate for fd11:a58a:88ef:0:cd53:dda9:f0cb:b889 and fd11:a58a:88ef::ffff:1, signed by the mesh's root CA (here, or asked of its holder over the members' channel), under /etc/mysql/keel-tls: done
database.server: write /etc/sysctl.d/90-keel-database.conf: both nodes bind the VIP (mode 0644): done
database.server: let the server bind the VIP before it carries it (sysctl -q -w net.ipv6.ip_nonlocal_bind=1): done
database.server: write /etc/mysql/mariadb.conf.d/99-keel-database.cnf: a paired node, server id 650213503, binary log, GTID strict, semi-synchronous replication, TLS, the VIP fd11:a58a:88ef::ffff:1 bound (mode 0644): done
database.server: restart the server, which is the only way these take effect (systemctl restart mariadb): done
database.server.replication.allowed_from: authorize replication from fd11:a58a:88ef:0:382f:45b:553c:f11 with the certificate /CN=keel-fd11-a58a-88ef-0-382f-45b-553c-f11 mariadb of the mesh's root, outside the binary log (runuser -u mysql -- mariadb --batch, 5 statement(s) on standard input): done
database.server.role: no claim of fd11:a58a:88ef::ffff:1 is known yet, so the declared role, replica, stands until keel vip promote on the primary claims it
database.server.role: make the server follow the pair's VIP (keel database follow): the holder writable, the other node read only and replicating from the holder over TLS, an old primary rejoined by GTID when it holds nothing the holder lacks: done
derived.monit: write /etc/keel/monit/keel-manifest.conf: 5 unit(s) and 4 probe(s) of mariadb (mode 0600): done
overlays.vip: enable keel-vip.service: the overlay is enabled (systemctl enable keel-vip.service): done
overlays.vip: start keel-vip.service (systemctl start keel-vip.service): done
apply --system-only: 10 change(s), 0 failed
rc=0
23:47:55

=== [9003] 2026-10-08T23:48:03Z rc=0
$ keel vip status 2>&1; systemctl is-active keel-vip.service; date -u +%T; timeout 120 keel vip promote 2>&1; echo rc=$?; date -u +%T; keel vip status; ip -6 addr show wg0 | grep inet6
vip fd11:a58a:88ef::ffff:1: this node's appliance.vip
  role: replica
  holder: none known yet
  carried here: no
  routed to: no peer
inactive
23:48:02
  fd11:a58a:88ef:0:cd53:dda9:f0cb:b889: applied
  fd11:a58a:88ef::1: applied
this node holds fd11:a58a:88ef::ffff:1 at epoch 1, on wg0, taken by 2 of 2 peer(s)
rc=0
23:48:03
vip fd11:a58a:88ef::ffff:1: this node's appliance.vip
  role: primary
  epoch 1, held by li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY= at fd11:a58a:88ef:0:382f:45b:553c:f11
  carried here: yes
  routed to: no peer
    inet6 fd11:a58a:88ef::ffff:1/128 scope global nodad deprecated 
    inet6 fd11:a58a:88ef:0:382f:45b:553c:f11/64 scope global 

=== [9003] 2026-10-08T23:48:10Z rc=0
$ systemctl status keel-vip.service --no-pager 2>&1 | head -12; journalctl -u keel-vip.service --no-pager -o short-iso | tail -8; systemctl list-timers "keel-vip*" --no-legend
○ keel-vip.service - keel vip: the VIP's root helper with etcd
     Loaded: loaded (/usr/lib/systemd/system/keel-vip.service; enabled; preset: disabled)
     Active: inactive (dead)
  Condition: start condition unmet at Thu 2026-10-08 23:47:44 UTC; 26s ago
             └─ ConditionPathExists=/var/lib/keel/etcd/cluster.json was not met
       Docs: https://github.com/Keel-Linux/keel/blob/main/docs/vip.md

Oct 08 23:46:51 keel-db-1 systemd[1]: keel-vip.service - keel vip: the VIP's root helper with etcd skipped, unmet condition check ConditionPathExists=/var/lib/keel/etcd/cluster.json
Oct 08 23:47:30 keel-db-1 systemd[1]: keel-vip.service - keel vip: the VIP's root helper with etcd skipped, unmet condition check ConditionPathExists=/var/lib/keel/etcd/cluster.json
Oct 08 23:47:44 keel-db-1 systemd[1]: keel-vip.service - keel vip: the VIP's root helper with etcd skipped, unmet condition check ConditionPathExists=/var/lib/keel/etcd/cluster.json
2026-10-08T23:46:51+00:00 keel-db-1 systemd[1]: keel-vip.service - keel vip: the VIP's root helper with etcd skipped, unmet condition check ConditionPathExists=/var/lib/keel/etcd/cluster.json
2026-10-08T23:47:30+00:00 keel-db-1 systemd[1]: keel-vip.service - keel vip: the VIP's root helper with etcd skipped, unmet condition check ConditionPathExists=/var/lib/keel/etcd/cluster.json
2026-10-08T23:47:44+00:00 keel-db-1 systemd[1]: keel-vip.service - keel vip: the VIP's root helper with etcd skipped, unmet condition check ConditionPathExists=/var/lib/keel/etcd/cluster.json
Thu 2026-10-08 23:48:56 UTC 45s Thu 2026-10-08 23:47:56 UTC 14s ago keel-vip-check.timer keel-vip-check.service

=== [9003] 2026-10-08T23:48:18Z rc=0
$ keel database status 2>&1; keel vip status 2>&1 | tail -4
pair: VIP fd11:a58a:88ef::ffff:1; role here primary
  other member: fd11:a58a:88ef:0:cd53:dda9:f0cb:b889 (o9tGVm/IKImyW2kgn22YjiWdEXpAr28T6WF9uc4yW1Q=)
  the primary's address: fd11:a58a:88ef:0:cd53:dda9:f0cb:b889
server: primary (mariadb --batch --skip-column-names --execute SHOW REPLICA HOSTS lists 1 replica(s) connected)
  read_only: false
  semi-synchronous: master ON, slave OFF, 1 replica(s) acknowledging, 0 commits acknowledged, 0 not
  replicating from: nobody
  certificate: keel-fd11-a58a-88ef-0-382f-45b-553c-f11 mariadb, for fd11:a58a:88ef:0:382f:45b:553c:f11, fd11:a58a:88ef::ffff:1, until 2026-11-07T23:47:42Z
vip fd11:a58a:88ef::ffff:1: this node's appliance.vip
  role: primary
  epoch 1, held by li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY= at fd11:a58a:88ef:0:382f:45b:553c:f11
  carried here: yes
  routed to: no peer
  role: primary
  epoch 1, held by li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY= at fd11:a58a:88ef:0:382f:45b:553c:f11
  carried here: yes
  routed to: no peer

=== [9004] 2026-10-08T23:48:21Z rc=0
$ keel database status 2>&1; keel vip status 2>&1 | tail -4
pair: VIP fd11:a58a:88ef::ffff:1; role here replica
  other member: fd11:a58a:88ef:0:382f:45b:553c:f11 (li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY=)
  the primary's address: fd11:a58a:88ef:0:382f:45b:553c:f11
server: replica (mariadb --batch --execute SHOW REPLICA STATUS\G)
  read_only: true
  semi-synchronous: master ON, slave ON, 0 replica(s) acknowledging, 0 commits acknowledged, 0 not
  replicating from: [fd11:a58a:88ef:0:382f:45b:553c:f11]:3306; IO Yes, SQL Yes; lag 0; TLS Yes; GTID IO position 
  certificate: keel-fd11-a58a-88ef-0-cd53-dda9-f0cb-b889 mariadb, for fd11:a58a:88ef:0:cd53:dda9:f0cb:b889, fd11:a58a:88ef::ffff:1, until 2026-11-07T23:47:52Z
vip fd11:a58a:88ef::ffff:1: this node's appliance.vip
  role: replica
  epoch 1, held by li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY= at fd11:a58a:88ef:0:382f:45b:553c:f11
  carried here: no
  routed to: li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY=
  role: replica
  epoch 1, held by li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY= at fd11:a58a:88ef:0:382f:45b:553c:f11
  carried here: no
  routed to: li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY=

=== [124] 2026-10-08T23:48:23Z rc=0
$ wg show wg0 allowed-ips | grep -E "li08|o9tG"; keel vip status 2>&1
li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY=	fd11:a58a:88ef:0:382f:45b:553c:f11/128 fd11:a58a:88ef::ffff:1/128
o9tGVm/IKImyW2kgn22YjiWdEXpAr28T6WF9uc4yW1Q=	fd11:a58a:88ef:0:cd53:dda9:f0cb:b889/128
vip fd11:a58a:88ef::ffff:1: another pair's, routed
  epoch 1, held by li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY= at fd11:a58a:88ef:0:382f:45b:553c:f11
  carried here: no
  routed to: li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY=

=== [9003] 2026-10-08T23:48:32Z rc=0
$ keel diff 2>&1 | grep -vE "not declared \(observed|not compared \(tls" ; echo "diff rc=${PIPESTATUS[0]}"; keel inspect 2>/dev/null | sed -n "/^database:/,/^[a-z]/p" | head -60
instance.hostname: same (keel-db-1)
instance.fqdn: same (keel-db-1.pop.coop)
network.overlay.wireguard.interface: same (wg0)
network.overlay.wireguard.listen_port: same (51820)
network.overlay.wireguard.address: same (fd11:a58a:88ef:0:382f:45b:553c:f11/64)
network.overlay.wireguard.peers.1bSgAuDppyY36XfEH2zxXeT5altQGehlT7Se2AVZyAg=.endpoint: same ([<uplink>]:51820)
network.overlay.wireguard.peers.1bSgAuDppyY36XfEH2zxXeT5altQGehlT7Se2AVZyAg=.allowed_ips: same (fd11:a58a:88ef::1/128)
network.overlay.wireguard.peers.o9tGVm/IKImyW2kgn22YjiWdEXpAr28T6WF9uc4yW1Q=.endpoint: same ([<uplink>]:51820)
network.overlay.wireguard.peers.o9tGVm/IKImyW2kgn22YjiWdEXpAr28T6WF9uc4yW1Q=.allowed_ips: same (fd11:a58a:88ef:0:cd53:dda9:f0cb:b889/128)
database.server.engine: same (mariadb)
database.server.role: same (primary)
database.server.listen: drift (declared fd11:a58a:88ef:0:382f:45b:553c:f11, ::1, observed *)
database.server.read_only: same (false)
database.server.semi_sync: same (on)
appliance.name: same (mariadb)
appliance.vip: same (fd11:a58a:88ef::ffff:1)
installation: not compared (the mode is chosen once, at installation, and nothing on the machine records it (decision 0041))
overlays.installer: not compared (runs no unit, so nothing in systemd says whether it is on)
overlays.wireguard: not compared (runs no unit, so nothing in systemd says whether it is on)
overlays.etcd: same (disabled)
overlays.crowdsec: same (disabled)
overlays.vip: drift (declared enabled, observed keel-vip.service enabled and inactive)
derived.monit: same (the file apply renders from the manifests)
derived.monit.included: not compared (no monitor section: the include is left as an earlier apply set it)
diff: 18 same, 2 drift, 0 unknown, 13 not declared, 5 not compared; drift found
diff rc=14
database:
  server:
    engine: mariadb
    role: primary
    listen:
    - '*'
    replication:
      allowed_from:
      - fd11:a58a:88ef:0:cd53:dda9:f0cb:b889
locale:

=== [9004] 2026-10-08T23:48:36Z rc=0
$ keel diff 2>&1 | grep -vE "not declared \(observed|not compared \(tls" ; echo "diff rc=${PIPESTATUS[0]}"; keel inspect 2>/dev/null | sed -n "/^database:/,/^[a-z]/p" | head -60
instance.hostname: same (keel-db-2)
instance.fqdn: same (keel-db-2.pop.coop)
network.overlay.wireguard.interface: same (wg0)
network.overlay.wireguard.listen_port: same (51820)
network.overlay.wireguard.address: same (fd11:a58a:88ef:0:cd53:dda9:f0cb:b889/64)
network.overlay.wireguard.peers.1bSgAuDppyY36XfEH2zxXeT5altQGehlT7Se2AVZyAg=.endpoint: same ([<uplink>]:51820)
network.overlay.wireguard.peers.1bSgAuDppyY36XfEH2zxXeT5altQGehlT7Se2AVZyAg=.allowed_ips: same (fd11:a58a:88ef::1/128)
network.overlay.wireguard.peers.li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY=.endpoint: same ([<uplink>]:51820)
network.overlay.wireguard.peers.li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY=.allowed_ips: same (fd11:a58a:88ef:0:382f:45b:553c:f11/128)
database.server.engine: same (mariadb)
database.server.role: same (replica)
database.server.listen: drift (declared fd11:a58a:88ef:0:cd53:dda9:f0cb:b889, ::1, observed *)
database.server.read_only: same (true)
database.server.semi_sync: not compared (compared on the primary, whose commits wait for the replica; this node is the replica)
appliance.name: same (mariadb)
appliance.vip: same (fd11:a58a:88ef::ffff:1)
installation: not compared (the mode is chosen once, at installation, and nothing on the machine records it (decision 0041))
overlays.installer: not compared (runs no unit, so nothing in systemd says whether it is on)
overlays.wireguard: not compared (runs no unit, so nothing in systemd says whether it is on)
overlays.etcd: same (disabled)
overlays.crowdsec: same (disabled)
overlays.vip: drift (declared enabled, observed keel-vip.service enabled and inactive)
derived.monit: same (the file apply renders from the manifests)
derived.monit.included: not compared (no monitor section: the include is left as an earlier apply set it)
diff: 17 same, 2 drift, 0 unknown, 14 not declared, 6 not compared; drift found
diff rc=14
database:
  server:
    engine: mariadb
    role: replica
    listen:
    - '*'
    replication:
      primary:
        host: fd11:a58a:88ef:0:382f:45b:553c:f11
        port: 3306
locale:

=== [9003] 2026-10-08T23:48:43Z rc=0
$ ss -ltnp | grep 3306; mariadb -N -e "select @@bind_address, @@read_only, @@server_id, @@gtid_strict_mode, @@log_bin, @@binlog_format"; grep -rn "bind" /etc/mysql/ | grep -v "#"; cat /etc/mysql/mariadb.conf.d/99-keel-database.cnf; ls -l /etc/mysql/keel-tls; sysctl net.ipv6.ip_nonlocal_bind
LISTEN 0      4096                                          *:3306             *:*    users:(("mariadbd",pid=9513,fd=5),("systemd",pid=1,fd=136))
fd11:a58a:88ef:0:382f:45b:553c:f11,::1,fd11:a58a:88ef::ffff:1	0	388044305	1	1	ROW
/etc/mysql/mariadb.conf.d/50-server.cnf:27:bind-address            = 127.0.0.1
/etc/mysql/mariadb.conf.d/99-keel-database.cnf:5:bind-address = fd11:a58a:88ef:0:382f:45b:553c:f11,::1,fd11:a58a:88ef::ffff:1
/etc/mysql/mariadb.conf.d/99-keel-bind.cnf:17:bind-address = ::1,127.0.0.1
# Written by keel spec apply from database.server of the instance
# description. Edited by hand, it is overwritten on the next run.
[mysqld]
server_id = 388044305
bind-address = fd11:a58a:88ef:0:382f:45b:553c:f11,::1,fd11:a58a:88ef::ffff:1
skip_name_resolve = ON
log_bin = mariadb-bin
binlog_format = ROW
log_slave_updates = ON
gtid_strict_mode = ON
rpl_semi_sync_master_enabled = ON
rpl_semi_sync_slave_enabled = ON
rpl_semi_sync_master_wait_point = AFTER_SYNC
rpl_semi_sync_master_timeout = 10000
rpl_semi_sync_master_wait_no_slave = OFF
slave_net_timeout = 10
ssl_ca = /etc/mysql/keel-tls/ca.pem
ssl_cert = /etc/mysql/keel-tls/server.pem
ssl_key = /etc/mysql/keel-tls/server.key
ssl_crl = /etc/mysql/keel-tls/crl.pem
total 16
-rw-r--r-- 1 root root  668 Oct  8 23:47 ca.pem
-rw-r--r-- 1 root root  475 Oct  8 23:47 crl.pem
-rw-r----- 1 root mysql 241 Oct  8 23:46 server.key
-rw-r--r-- 1 root root  786 Oct  8 23:47 server.pem
net.ipv6.ip_nonlocal_bind = 1

=== [9003] 2026-10-08T23:48:51Z rc=0
$ systemctl list-sockets --no-legend | grep -i -E "3306|maria|mysql"; systemctl cat mariadb.socket 2>/dev/null | grep -vE "^#|^$" | head -20; ip -6 -br addr show eth0; nft list ruleset 2>/dev/null | head -5; ip6tables -S 2>/dev/null | head -5
@mariadb                            mariadb.socket                  mariadb.service
@mariadb-extra                      mariadb-extra.socket            mariadb.service
[::]:3306                           mariadb.socket                  mariadb.service
/run/mysqld/mysqld.sock             mariadb.socket                  mariadb.service
/run/mysqld/mysqld.sock-extra       mariadb-extra.socket            mariadb.service
[Unit]
Description=MariaDB 11.8.6 database server (socket activation)
Documentation=man:mariadbd(8)
Documentation=https://mariadb.com/kb/en/library/systemd/
[Install]
WantedBy=sockets.target
[Socket]
SocketUser=mysql
SocketMode=777
ListenStream=@mariadb
ListenStream=/run/mysqld/mysqld.sock
ListenStream=3306
eth0@if97        UP             <uplink>/64 fe80::be24:11ff:fe2a:a74e/64 
table inet filter {
	chain input {
		type filter hook input priority filter; policy accept;
	}

-P INPUT ACCEPT
-P FORWARD ACCEPT
-P OUTPUT ACCEPT

=== [host] 2026-10-08T23:48:51Z rc=0
$ timeout 5 bash -c "</dev/tcp/<uplink>/3306" && echo "3306 OPEN on db-1 uplink from host" || echo "3306 closed from host"
3306 OPEN on db-1 uplink from host

=== [9003] 2026-10-08T23:49:01Z rc=0
$ systemctl is-enabled mariadb.socket mariadb-extra.socket; ls -l /etc/systemd/system/sockets.target.wants/ 2>/dev/null; cd /etc && git log --oneline --diff-filter=A -- systemd/system/sockets.target.wants/mariadb.socket | tail -2; mariadb -N -e "select user,host from mysql.user"
enabled
enabled
total 0
lrwxrwxrwx 1 root root 36 Oct  7 23:17 acpid.socket -> /usr/lib/systemd/system/acpid.socket
lrwxrwxrwx 1 root root 39 Oct  7 23:17 dm-event.socket -> /usr/lib/systemd/system/dm-event.socket
lrwxrwxrwx 1 root root 44 Oct  8 19:42 mariadb-extra.socket -> /usr/lib/systemd/system/mariadb-extra.socket
lrwxrwxrwx 1 root root 38 Oct  8 19:42 mariadb.socket -> /usr/lib/systemd/system/mariadb.socket
lrwxrwxrwx 1 root root 34 Oct  8 19:42 ssh.socket -> /usr/lib/systemd/system/ssh.socket
lrwxrwxrwx 1 root root 53 Oct  8 19:42 systemd-journald-audit.socket -> /usr/lib/systemd/system/systemd-journald-audit.socket
lrwxrwxrwx 1 root root 48 Oct  8 19:42 systemd-pcrextend.socket -> /usr/lib/systemd/system/systemd-pcrextend.socket
lrwxrwxrwx 1 root root 45 Oct  8 19:42 systemd-sysext.socket -> /usr/lib/systemd/system/systemd-sysext.socket
88cccad initial commit
admin	127.0.0.1
admin	::1
repl	fd11:a58a:88ef:0:cd53:dda9:f0cb:b889
admin	localhost
mariadb.sys	localhost
mysql	localhost
root	localhost

=== [host] 2026-10-08T23:49:01Z rc=0
$ timeout 5 python3 -c "
import socket;s=socket.create_connection((\"<uplink>\",3306),3);print(repr(s.recv(80)[:60]))"
b"\\\x00\x00\x00\xffj\x04Host '<uplink>' is not allow"

=== [9003] 2026-10-08T23:49:26Z rc=0
$ umask 077; printf '[client]\nuser=app\npassword=%s\n' '<redacted>' > /root/.app.cnf; ls -l /root/.app.cnf
-rw------- 1 root root 60 Oct  8 23:49 /root/.app.cnf

=== [9004] 2026-10-08T23:49:27Z rc=0
$ umask 077; printf '[client]\nuser=app\npassword=%s\n' '<redacted>' > /root/.app.cnf; ls -l /root/.app.cnf
-rw------- 1 root root 60 Oct  8 23:49 /root/.app.cnf

=== [9003] 2026-10-08T23:49:29Z rc=0
$ mariadb <<EOF
CREATE DATABASE IF NOT EXISTS keeltest;
CREATE TABLE IF NOT EXISTS keeltest.t (id BIGINT AUTO_INCREMENT PRIMARY KEY, node VARCHAR(64), at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6), note VARCHAR(64));
EOF
P=$(sed -n "s/^password=//p" /root/.app.cnf)
for h in fd11:a58a:88ef:0:382f:45b:553c:f11 fd11:a58a:88ef:0:cd53:dda9:f0cb:b889 fd11:a58a:88ef::ffff:1 ::1; do mariadb -e "CREATE USER IF NOT EXISTS app@\`$h\` IDENTIFIED BY \"$P\"; GRANT SELECT,INSERT,UPDATE,DELETE ON keeltest.* TO app@\`$h\`;"; done
mariadb -N -e "select user,host from mysql.user where user=\"app\""
app	::1
app	fd11:a58a:88ef:0:382f:45b:553c:f11
app	fd11:a58a:88ef:0:cd53:dda9:f0cb:b889
app	fd11:a58a:88ef::ffff:1

=== [9004] 2026-10-08T23:49:38Z rc=0
$ for i in 1 2 3; do t0=$(date +%s.%N); mariadb --defaults-extra-file=/root/.app.cnf -h fd11:a58a:88ef::ffff:1 -N -e "INSERT INTO keeltest.t(node,note) VALUES (@@hostname,\"vip-write-$i\"); SELECT @@hostname, LAST_INSERT_ID();"; t1=$(date +%s.%N); for k in $(seq 1 200); do r=$(mariadb -N -e "select count(*) from keeltest.t where note=\"vip-write-$i\""); [ "$r" = 1 ] && break; sleep 0.01; done; t2=$(date +%s.%N); echo "write $i: commit at VIP $(echo "$t1-$t0"|bc) s, visible on replica $(echo "$t2-$t1"|bc) s after ack"; done; mariadb -N -e "select id,node,note from keeltest.t"
keel-db-1	1
bash: line 1: bc: command not found
bash: line 1: bc: command not found
write 1: commit at VIP  s, visible on replica  s after ack
keel-db-1	2
bash: line 1: bc: command not found
bash: line 1: bc: command not found
write 2: commit at VIP  s, visible on replica  s after ack
keel-db-1	3
bash: line 1: bc: command not found
bash: line 1: bc: command not found
write 3: commit at VIP  s, visible on replica  s after ack
1	keel-db-1	vip-write-1
2	keel-db-1	vip-write-2
3	keel-db-1	vip-write-3

=== [9004] 2026-10-08T23:49:46Z rc=0
$ for i in 4 5 6; do t0=$(date +%s.%N); mariadb --defaults-extra-file=/root/.app.cnf -h fd11:a58a:88ef::ffff:1 -N -e "INSERT INTO keeltest.t(node,note) VALUES (@@hostname,\"vip-write-$i\"); SELECT @@hostname, LAST_INSERT_ID();"; t1=$(date +%s.%N); for k in $(seq 1 200); do r=$(mariadb -N -e "select count(*) from keeltest.t where note=\"vip-write-$i\""); [ "$r" = 1 ] && break; sleep 0.01; done; t2=$(date +%s.%N); awk -v a=$t0 -v b=$t1 -v c=$t2 -v i=$i "BEGIN{printf \"write %s: connect+commit at VIP %.3f s; visible on replica %.3f s after the ack\n\", i, b-a, c-b}"; done; mariadb -N -e "select id,node,note from keeltest.t"
keel-db-1	4
write 4: connect+commit at VIP 0.037 s; visible on replica 0.036 s after the ack
keel-db-1	5
write 5: connect+commit at VIP 0.036 s; visible on replica 0.036 s after the ack
keel-db-1	6
write 6: connect+commit at VIP 0.038 s; visible on replica 0.037 s after the ack
1	keel-db-1	vip-write-1
2	keel-db-1	vip-write-2
3	keel-db-1	vip-write-3
4	keel-db-1	vip-write-4
5	keel-db-1	vip-write-5
6	keel-db-1	vip-write-6

=== [9004] 2026-10-08T23:49:55Z rc=0
$ mariadb -e "INSERT INTO keeltest.t(node,note) VALUES (@@hostname,\"root-on-replica\")"; echo "root rc=$?"; mariadb --defaults-extra-file=/root/.app.cnf -h fd11:a58a:88ef:0:cd53:dda9:f0cb:b889 -e "INSERT INTO keeltest.t(node,note) VALUES (@@hostname,\"app-on-replica\")"; echo "app(overlay) rc=$?"; mariadb --defaults-extra-file=/root/.app.cnf -h ::1 -e "INSERT INTO keeltest.t(node,note) VALUES (@@hostname,\"app-on-replica-lo\")"; echo "app(::1) rc=$?"; mariadb -N -e "select @@read_only; select grantee from information_schema.user_privileges where privilege_type=\"READ_ONLY ADMIN\"; select count(*) from keeltest.t where note like \"%replica%\""; cat /var/lib/keel/database/read-only-admin 2>&1 | head
--------------
INSERT INTO keeltest.t(node,note) VALUES (@@hostname,"root-on-replica")
--------------

ERROR 1290 (HY000) at line 1: The MariaDB server is running with the --read-only option so it cannot execute this statement
root rc=1
--------------
INSERT INTO keeltest.t(node,note) VALUES (@@hostname,"app-on-replica")
--------------

ERROR 1290 (HY000) at line 1: The MariaDB server is running with the --read-only option so it cannot execute this statement
app(overlay) rc=1
--------------
INSERT INTO keeltest.t(node,note) VALUES (@@hostname,"app-on-replica-lo")
--------------

ERROR 1290 (HY000) at line 1: The MariaDB server is running with the --read-only option so it cannot execute this statement
app(::1) rc=1
1
'mysql'@'localhost'
0
admin	localhost
admin	::1
admin	127.0.0.1
root	localhost

=== [9003] 2026-10-08T23:50:05Z rc=0
$ mariadb -N -e "show global status like \"Rpl_semi_sync%\"" | grep -E "master_status|master_clients|master_yes_tx|master_no_tx|slave_status|master_net_avg"; mariadb -e "show grants for repl@\`fd11:a58a:88ef:0:cd53:dda9:f0cb:b889\`" | sed -E "s/PASSWORD .\*[0-9A-F]+./PASSWORD <hash>/"; openssl x509 -in /etc/mysql/keel-tls/ca.pem -noout -subject -enddate; openssl x509 -in /etc/mysql/keel-tls/server.pem -noout -subject -issuer -enddate -ext subjectAltName,extendedKeyUsage; mariadb -N -e "select @@have_ssl, @@ssl_crl"
Rpl_semi_sync_master_clients	1
Rpl_semi_sync_master_net_avg_wait_time	0
Rpl_semi_sync_master_no_tx	0
Rpl_semi_sync_master_status	ON
Rpl_semi_sync_master_yes_tx	16
Rpl_semi_sync_slave_status	OFF
Grants for repl@fd11:a58a:88ef:0:cd53:dda9:f0cb:b889
GRANT SELECT, REPLICATION SLAVE, SHOW VIEW, EVENT, TRIGGER ON *.* TO `repl`@`fd11:a58a:88ef:0:cd53:dda9:f0cb:b889` IDENTIFIED BY PASSWORD <hash> REQUIRE ISSUER '/CN=keel mesh 9fe71b35b8d35c58 etcd root' SUBJECT '/CN=keel-fd11-a58a-88ef-0-cd53-dda9-f0cb-b889 mariadb'
subject=CN=keel mesh 9fe71b35b8d35c58 etcd root
notAfter=Sep 29 23:07:31 2046 GMT
subject=CN=keel-fd11-a58a-88ef-0-382f-45b-553c-f11 mariadb
issuer=CN=keel mesh 9fe71b35b8d35c58 etcd root
notAfter=Nov  7 23:47:42 2026 GMT
X509v3 Extended Key Usage: 
    TLS Web Server Authentication, TLS Web Client Authentication
X509v3 Subject Alternative Name: 
    IP Address:FD11:A58A:88EF:0:382F:45B:553C:F11, IP Address:FD11:A58A:88EF:0:0:0:FFFF:1
YES	/etc/mysql/keel-tls/crl.pem

=== [9004] 2026-10-08T23:50:06Z rc=0
$ mariadb -e "show replica status\G" | grep -E "Slave_IO_State|Master_Host|Master_User|IO_Running|SQL_Running:|Master_SSL_Allowed|Master_SSL_CA_File|Master_SSL_Cert|Master_SSL_Verify|Using_Gtid|Gtid_IO_Pos|Seconds_Behind|Last_IO_Error"; mariadb -N -e "show global status like \"Rpl_semi_sync_slave_status\"; select @@gtid_slave_pos, @@gtid_binlog_pos"
                Slave_IO_State: Waiting for master to send event
                   Master_Host: fd11:a58a:88ef:0:382f:45b:553c:f11
                   Master_User: repl
              Slave_IO_Running: Yes
             Slave_SQL_Running: Yes
            Master_SSL_Allowed: Yes
            Master_SSL_CA_File: /etc/mysql/keel-tls/ca.pem
               Master_SSL_Cert: /etc/mysql/keel-tls/server.pem
         Seconds_Behind_Master: 0
 Master_SSL_Verify_Server_Cert: Yes
                 Last_IO_Error: 
                    Using_Gtid: Slave_Pos
                   Gtid_IO_Pos: 0-388044305-16
Rpl_semi_sync_slave_status	ON
0-388044305-16	0-388044305-16

=== [9003] 2026-10-08T23:50:19Z rc=0
$ ls -l /var/lib/keel/database/; sha256sum /var/lib/keel/database/replication.secret | cut -c1-16; grep -c . /etc/keel/instance.yaml >/dev/null; grep -n "secret" /etc/keel/instance.yaml || echo "no secret in spec"
total 8
-rw------- 1 root root 44 Oct  8 23:46 replication.secret
-rw-r--r-- 1 root root 69 Oct  8 23:50 semi-sync
c329d382fb7b27a7
no secret in spec

=== [9004] 2026-10-08T23:50:21Z rc=0
$ ls -l /var/lib/keel/database/; sha256sum /var/lib/keel/database/replication.secret | cut -c1-16; grep -c . /etc/keel/instance.yaml >/dev/null; grep -n "secret" /etc/keel/instance.yaml || echo "no secret in spec"
total 12
-rw------- 1 root root 57 Oct  8 23:48 read-only-admin
-rw------- 1 root root 44 Oct  8 23:46 replication.secret
-rw-r--r-- 1 root root 69 Oct  8 23:50 semi-sync
c329d382fb7b27a7
no secret in spec

=== [9004] 2026-10-08T23:50:22Z rc=0
$ S=$(cat /var/lib/keel/database/replication.secret); mariadb -h fd11:a58a:88ef:0:382f:45b:553c:f11 -u repl -p"$S" --skip-ssl -e "select 1" 2>&1 | tail -1; mariadb -h fd11:a58a:88ef:0:382f:45b:553c:f11 -u repl -p"$S" --ssl --ssl-ca=/etc/mysql/keel-tls/ca.pem -e "select 1" 2>&1 | tail -1; mariadb -h fd11:a58a:88ef:0:382f:45b:553c:f11 -u repl -p"$S" --ssl-ca=/etc/mysql/keel-tls/ca.pem --ssl-cert=/etc/mysql/keel-tls/server.pem --ssl-key=/etc/mysql/keel-tls/server.key --ssl-verify-server-cert -N -e "select \"with db-2 database leaf:\", 1; show status like \"Ssl_cipher\"; show status like \"Ssl_version\"" 2>&1 | tail -3
ERROR 1045 (28000): Access denied for user 'repl'@'fd11:a58a:88ef:0:cd53:dda9:f0cb:b889' (using password: YES)
ERROR 1045 (28000): Access denied for user 'repl'@'fd11:a58a:88ef:0:cd53:dda9:f0cb:b889' (using password: YES)
with db-2 database leaf:	1
Ssl_cipher	TLS_AES_256_GCM_SHA384
Ssl_version	TLSv1.3

=== [9003] 2026-10-08T23:50:30Z rc=0
$ stat -c "%y %n" /var/lib/keel/database/replication.secret; journalctl --since "23:46" --until "23:48:30" --no-pager -o short-iso -u keel-mesh-members.service -u keel-mesh-members-listen.service | grep -v "^--" | tail -10
2026-10-08 23:46:30.140701434 +0000 /var/lib/keel/database/replication.secret
2026-10-08T23:46:30+00:00 keel-db-1 keel[8121]: vip fd11:a58a:88ef::ffff:1: the database/replication secret given to o9tGVm/IKImyW2kgn22YjiWdEXpAr28T6WF9uc4yW1Q=
2026-10-08T23:46:56+00:00 keel-db-1 keel[8121]: etcd: refused a message from o9tGVm/IKImyW2kgn22YjiWdEXpAr28T6WF9uc4yW1Q=: this node does not hold the mesh's root CA
2026-10-08T23:46:56+00:00 keel-db-1 python3[8152]: refused POST '/v1/etcd' from fd11:a58a:88ef:0:cd53:dda9:f0cb:b889: 409
2026-10-08T23:47:31+00:00 keel-db-1 keel[8121]: etcd: refused a message from o9tGVm/IKImyW2kgn22YjiWdEXpAr28T6WF9uc4yW1Q=: this node does not hold the mesh's root CA
2026-10-08T23:47:31+00:00 keel-db-1 python3[8152]: refused POST '/v1/etcd' from fd11:a58a:88ef:0:cd53:dda9:f0cb:b889: 409

=== [9004] 2026-10-08T23:50:32Z rc=0
$ stat -c "%y %n" /var/lib/keel/database/replication.secret; journalctl --since "23:46" --until "23:48:30" --no-pager -o short-iso -u keel-mesh-members.service -u keel-mesh-members-listen.service | grep -v "^--" | tail -10
2026-10-08 23:46:30.197508696 +0000 /var/lib/keel/database/replication.secret
2026-10-08T23:46:29+00:00 keel-db-2 keel[7865]: vip fd11:a58a:88ef::ffff:1: paired with li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY=
2026-10-08T23:46:44+00:00 keel-db-2 keel[7865]: etcd: refused a message from li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY=: this node does not hold the mesh's root CA
2026-10-08T23:46:44+00:00 keel-db-2 python3[7903]: refused POST '/v1/etcd' from fd11:a58a:88ef:0:382f:45b:553c:f11: 409
2026-10-08T23:46:50+00:00 keel-db-2 keel[7865]: etcd: refused a message from li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY=: this node does not hold the mesh's root CA
2026-10-08T23:46:50+00:00 keel-db-2 python3[7903]: refused POST '/v1/etcd' from fd11:a58a:88ef:0:382f:45b:553c:f11: 409
2026-10-08T23:47:18+00:00 keel-db-2 keel[7865]: etcd: refused a message from li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY=: this node does not hold the mesh's root CA
2026-10-08T23:47:18+00:00 keel-db-2 python3[7903]: refused POST '/v1/etcd' from fd11:a58a:88ef:0:382f:45b:553c:f11: 409
2026-10-08T23:47:30+00:00 keel-db-2 keel[7865]: etcd: refused a message from li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY=: this node does not hold the mesh's root CA
2026-10-08T23:47:30+00:00 keel-db-2 python3[7903]: refused POST '/v1/etcd' from fd11:a58a:88ef:0:382f:45b:553c:f11: 409
2026-10-08T23:48:02+00:00 keel-db-2 keel[7865]: vip fd11:a58a:88ef::ffff:1: epoch 1, held by li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY= at fd11:a58a:88ef:0:382f:45b:553c:f11

=== [9003] 2026-10-08T23:50:51Z rc=0
$ echo IyEvYmluL2Jhc2gKIyB3cml0ZXIuc2ggVEFHIFNFQ09ORFM6IG9uZSBuZXcgY29ubmVjdGlvbiBwZXIgd3JpdGUgdG8gdGhlIFZJUDsgbG9ncyBlcG9jaC1tcywgc2VxLCByYywgc2VydmVyClRBRz0kMTsgRFVSPSQyOyBPVVQ9L3Jvb3Qvd3JpdGVyLSRUQUcubG9nOyA6ID4gJE9VVAplbmQ9JCgoICQoZGF0ZSArJXMpICsgRFVSICkpOyBpPTAKd2hpbGUgWyAkKGRhdGUgKyVzKSAtbHQgJGVuZCBdOyBkbwogIGk9JCgoaSsxKSk7IHQ9JChkYXRlICslcyUzTikKICByPSQodGltZW91dCAxNSBtYXJpYWRiIC0tZGVmYXVsdHMtZXh0cmEtZmlsZT0vcm9vdC8uYXBwLmNuZiAtaCBmZDExOmE1OGE6ODhlZjo6ZmZmZjoxIC0tY29ubmVjdC10aW1lb3V0PTIgLU4gLWUgIklOU0VSVCBJTlRPIGtlZWx0ZXN0LnQobm9kZSxub3RlKSBWQUxVRVMgKEBAaG9zdG5hbWUsJyRUQUctJGknKTsgU0VMRUNUIEBAaG9zdG5hbWU7IiAyPiYxIHwgdHIgJ1xuJyAnICcpCiAgcmM9JD87IGU9JChkYXRlICslcyUzTikKICBlY2hvICIkdCAkZSAkaSAke1BJUEVTVEFUVVNbMF19ICRyIiA+PiAkT1VUCiAgc2xlZXAgMC4xCmRvbmUK | base64 -d > /root/writer.sh; chmod 700 /root/writer.sh; echo aW1wb3J0IHN5cwpvaz1bXTtmYWlsPTA7c2VydmVycz1bXQpmb3IgbCBpbiBvcGVuKHN5cy5hcmd2WzFdKToKICAgIHA9bC5zcGxpdChOb25lLDQpCiAgICB0MCx0MSxpLHJjPWludChwWzBdKSxpbnQocFsxXSkscFsyXSxwWzNdCiAgICBtc2c9cFs0XS5zdHJpcCgpIGlmIGxlbihwKT40IGVsc2UgJycKICAgIGlmIHJjPT0nMCc6IG9rLmFwcGVuZCgodDEsaSxtc2cpKQogICAgZWxzZTogZmFpbCs9MQpnYXBzPVsob2tba11bMF0tb2tbay0xXVswXSxva1trLTFdLG9rW2tdKSBmb3IgayBpbiByYW5nZSgxLGxlbihvaykpXQpnPW1heChnYXBzKQpwcmludChmIndyaXRlczoge2xlbihvayl9IG9rLCB7ZmFpbH0gZmFpbGVkOyBsb25nZXN0IGdhcCBiZXR3ZWVuIHR3byBhY2tub3dsZWRnZWQgd3JpdGVzOiB7Z1swXS8xMDAwOi4yZn0gcyAoc2VxIHtnWzFdWzFdfSBvbiB7Z1sxXVsyXX0gLT4gc2VxIHtnWzJdWzFdfSBvbiB7Z1syXVsyXX0pIikK | base64 -d > /root/gap.py; ls -l /root/writer.sh /root/gap.py
-rw-r--r-- 1 root root 477 Oct  8 23:50 /root/gap.py
-rwx------ 1 root root 570 Oct  8 23:50 /root/writer.sh

=== [9004] 2026-10-08T23:50:53Z rc=0
$ echo IyEvYmluL2Jhc2gKIyB3cml0ZXIuc2ggVEFHIFNFQ09ORFM6IG9uZSBuZXcgY29ubmVjdGlvbiBwZXIgd3JpdGUgdG8gdGhlIFZJUDsgbG9ncyBlcG9jaC1tcywgc2VxLCByYywgc2VydmVyClRBRz0kMTsgRFVSPSQyOyBPVVQ9L3Jvb3Qvd3JpdGVyLSRUQUcubG9nOyA6ID4gJE9VVAplbmQ9JCgoICQoZGF0ZSArJXMpICsgRFVSICkpOyBpPTAKd2hpbGUgWyAkKGRhdGUgKyVzKSAtbHQgJGVuZCBdOyBkbwogIGk9JCgoaSsxKSk7IHQ9JChkYXRlICslcyUzTikKICByPSQodGltZW91dCAxNSBtYXJpYWRiIC0tZGVmYXVsdHMtZXh0cmEtZmlsZT0vcm9vdC8uYXBwLmNuZiAtaCBmZDExOmE1OGE6ODhlZjo6ZmZmZjoxIC0tY29ubmVjdC10aW1lb3V0PTIgLU4gLWUgIklOU0VSVCBJTlRPIGtlZWx0ZXN0LnQobm9kZSxub3RlKSBWQUxVRVMgKEBAaG9zdG5hbWUsJyRUQUctJGknKTsgU0VMRUNUIEBAaG9zdG5hbWU7IiAyPiYxIHwgdHIgJ1xuJyAnICcpCiAgcmM9JD87IGU9JChkYXRlICslcyUzTikKICBlY2hvICIkdCAkZSAkaSAke1BJUEVTVEFUVVNbMF19ICRyIiA+PiAkT1VUCiAgc2xlZXAgMC4xCmRvbmUK | base64 -d > /root/writer.sh; chmod 700 /root/writer.sh; echo aW1wb3J0IHN5cwpvaz1bXTtmYWlsPTA7c2VydmVycz1bXQpmb3IgbCBpbiBvcGVuKHN5cy5hcmd2WzFdKToKICAgIHA9bC5zcGxpdChOb25lLDQpCiAgICB0MCx0MSxpLHJjPWludChwWzBdKSxpbnQocFsxXSkscFsyXSxwWzNdCiAgICBtc2c9cFs0XS5zdHJpcCgpIGlmIGxlbihwKT40IGVsc2UgJycKICAgIGlmIHJjPT0nMCc6IG9rLmFwcGVuZCgodDEsaSxtc2cpKQogICAgZWxzZTogZmFpbCs9MQpnYXBzPVsob2tba11bMF0tb2tbay0xXVswXSxva1trLTFdLG9rW2tdKSBmb3IgayBpbiByYW5nZSgxLGxlbihvaykpXQpnPW1heChnYXBzKQpwcmludChmIndyaXRlczoge2xlbihvayl9IG9rLCB7ZmFpbH0gZmFpbGVkOyBsb25nZXN0IGdhcCBiZXR3ZWVuIHR3byBhY2tub3dsZWRnZWQgd3JpdGVzOiB7Z1swXS8xMDAwOi4yZn0gcyAoc2VxIHtnWzFdWzFdfSBvbiB7Z1sxXVsyXX0gLT4gc2VxIHtnWzJdWzFdfSBvbiB7Z1syXVsyXX0pIikK | base64 -d > /root/gap.py; ls -l /root/writer.sh /root/gap.py
-rw-r--r-- 1 root root 477 Oct  8 23:50 /root/gap.py
-rwx------ 1 root root 570 Oct  8 23:50 /root/writer.sh

=== [9003] 2026-10-08T23:51:01Z rc=0
$ echo IyEvYmluL2Jhc2gKIyB3cml0ZXIuc2ggVEFHIFNFQ09ORFM6IG9uZSBuZXcgY29ubmVjdGlvbiBwZXIgd3JpdGUgdG8gdGhlIFZJUDsgbG9ncyBlcG9jaC1tcywgc2VxLCByYywgc2VydmVyCnNldCAtbyBwaXBlZmFpbDsgVEFHPSQxOyBEVVI9JDI7IE9VVD0vcm9vdC93cml0ZXItJFRBRy5sb2c7IDogPiAkT1VUCmVuZD0kKCggJChkYXRlICslcykgKyBEVVIgKSk7IGk9MAp3aGlsZSBbICQoZGF0ZSArJXMpIC1sdCAkZW5kIF07IGRvCiAgaT0kKChpKzEpKTsgdD0kKGRhdGUgKyVzJTNOKQogIHI9JCh0aW1lb3V0IDE1IG1hcmlhZGIgLS1kZWZhdWx0cy1leHRyYS1maWxlPS9yb290Ly5hcHAuY25mIC1oIGZkMTE6YTU4YTo4OGVmOjpmZmZmOjEgLS1jb25uZWN0LXRpbWVvdXQ9MiAtTiAtZSAiSU5TRVJUIElOVE8ga2VlbHRlc3QudChub2RlLG5vdGUpIFZBTFVFUyAoQEBob3N0bmFtZSwnJFRBRy0kaScpOyBTRUxFQ1QgQEBob3N0bmFtZTsiIDI+JjEgfCB0ciAnXG4nICcgJykKICByYz0kPzsgZT0kKGRhdGUgKyVzJTNOKQogIGVjaG8gIiR0ICRlICRpICRyYyAkciIgPj4gJE9VVAogIHNsZWVwIDAuMQpkb25lCg== | base64 -d > /root/writer.sh; chmod 700 /root/writer.sh


=== [9004] 2026-10-08T23:51:03Z rc=0
$ echo IyEvYmluL2Jhc2gKIyB3cml0ZXIuc2ggVEFHIFNFQ09ORFM6IG9uZSBuZXcgY29ubmVjdGlvbiBwZXIgd3JpdGUgdG8gdGhlIFZJUDsgbG9ncyBlcG9jaC1tcywgc2VxLCByYywgc2VydmVyCnNldCAtbyBwaXBlZmFpbDsgVEFHPSQxOyBEVVI9JDI7IE9VVD0vcm9vdC93cml0ZXItJFRBRy5sb2c7IDogPiAkT1VUCmVuZD0kKCggJChkYXRlICslcykgKyBEVVIgKSk7IGk9MAp3aGlsZSBbICQoZGF0ZSArJXMpIC1sdCAkZW5kIF07IGRvCiAgaT0kKChpKzEpKTsgdD0kKGRhdGUgKyVzJTNOKQogIHI9JCh0aW1lb3V0IDE1IG1hcmlhZGIgLS1kZWZhdWx0cy1leHRyYS1maWxlPS9yb290Ly5hcHAuY25mIC1oIGZkMTE6YTU4YTo4OGVmOjpmZmZmOjEgLS1jb25uZWN0LXRpbWVvdXQ9MiAtTiAtZSAiSU5TRVJUIElOVE8ga2VlbHRlc3QudChub2RlLG5vdGUpIFZBTFVFUyAoQEBob3N0bmFtZSwnJFRBRy0kaScpOyBTRUxFQ1QgQEBob3N0bmFtZTsiIDI+JjEgfCB0ciAnXG4nICcgJykKICByYz0kPzsgZT0kKGRhdGUgKyVzJTNOKQogIGVjaG8gIiR0ICRlICRpICRyYyAkciIgPj4gJE9VVAogIHNsZWVwIDAuMQpkb25lCg== | base64 -d > /root/writer.sh; chmod 700 /root/writer.sh


=== [9003] 2026-10-08T23:51:06Z rc=0
$ /root/writer.sh smoke 2; cat /root/writer-smoke.log; python3 /root/gap.py /root/writer-smoke.log
1791503464586 1791503464621 1 0 keel-db-1 
1791503464732 1791503464772 2 0 keel-db-1 
1791503464876 1791503464913 3 0 keel-db-1 
1791503465016 1791503465052 4 0 keel-db-1 
1791503465155 1791503465191 5 0 keel-db-1 
1791503465295 1791503465332 6 0 keel-db-1 
1791503465436 1791503465474 7 0 keel-db-1 
1791503465578 1791503465614 8 0 keel-db-1 
1791503465717 1791503465757 9 0 keel-db-1 
1791503465860 1791503465897 10 0 keel-db-1 
writes: 10 ok, 0 failed; longest gap between two acknowledged writes: 0.15 s (seq 1 on keel-db-1 -> seq 2 on keel-db-1)

=== [9003] 2026-10-08T23:51:13Z rc=0
$ systemd-run --unit=keeltest-writer-planned --collect /root/writer.sh planned 60
Running as unit: keeltest-writer-planned.service; invocation ID: 338ebf915e7f47999d712705ab7f873e

=== [9004] 2026-10-08T23:51:32Z rc=0
$ sleep 10; date -u +%T.%3N; timeout 120 keel vip promote 2>&1; echo rc=$?; date -u +%T.%3N; sleep 5; keel vip status; mariadb -N -e "select @@read_only"; keel database status
23:51:24.950
asking the primary, li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY= at fd11:a58a:88ef:0:382f:45b:553c:f11, to release fd11:a58a:88ef::ffff:1…
released by fd11:a58a:88ef:0:382f:45b:553c:f11
  fd11:a58a:88ef:0:382f:45b:553c:f11: applied
  fd11:a58a:88ef::1: applied
this node holds fd11:a58a:88ef::ffff:1 at epoch 2, on wg0, taken by 2 of 2 peer(s)
rc=0
23:51:25.912
vip fd11:a58a:88ef::ffff:1: this node's appliance.vip
  role: primary
  epoch 2, held by o9tGVm/IKImyW2kgn22YjiWdEXpAr28T6WF9uc4yW1Q= at fd11:a58a:88ef:0:cd53:dda9:f0cb:b889
  carried here: yes
  routed to: no peer
0
pair: VIP fd11:a58a:88ef::ffff:1; role here primary
  other member: fd11:a58a:88ef:0:382f:45b:553c:f11 (li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY=)
  the primary's address: fd11:a58a:88ef:0:382f:45b:553c:f11
server: primary (mariadb --batch --skip-column-names --execute SHOW REPLICA HOSTS lists 1 replica(s) connected)
  read_only: false
  semi-synchronous: master ON, slave OFF, 1 replica(s) acknowledging, 36 commits acknowledged, 112 not
  replicating from: nobody
  gtid binlog_pos: 0-650213503-148
  gtid slave_pos: 0-388044305-112
  gtid current_pos: 0-650213503-148
  gtid binlog_state: 0-388044305-112,0-650213503-148
  certificate: keel-fd11-a58a-88ef-0-cd53-dda9-f0cb-b889 mariadb, for fd11:a58a:88ef:0:cd53:dda9:f0cb:b889, fd11:a58a:88ef::ffff:1, until 2026-11-07T23:47:52Z
vip fd11:a58a:88ef::ffff:1: this node's appliance.vip
  role: primary
  epoch 2, held by o9tGVm/IKImyW2kgn22YjiWdEXpAr28T6WF9uc4yW1Q= at fd11:a58a:88ef:0:cd53:dda9:f0cb:b889
  carried here: yes
  routed to: no peer

=== [9003] 2026-10-08T23:52:14Z rc=0
$ while systemctl is-active -q keeltest-writer-planned; do sleep 2; done; python3 /root/gap.py /root/writer-planned.log; awk "\$4!=0" /root/writer-planned.log | head; awk "{print \$5}" /root/writer-planned.log | uniq -c; mariadb -N -e "select @@read_only"; mariadb -e "show replica status\G" | grep -E "Master_Host|IO_Running|SQL_Running:|SSL_Allowed|Using_Gtid|Last_.*Error:"; journalctl -u keel-database-follow.service --since "23:51" --no-pager -o short-iso | tail -8
writes: 407 ok, 1 failed; longest gap between two acknowledged writes: 1.34 s (seq 86 on keel-db-1 -> seq 88 on keel-db-2)
1791503485654 1791503486734 87 1 -------------- INSERT INTO keeltest.t(node,note) VALUES (@@hostname,'planned-87') --------------  ERROR 1290 (HY000) at line 1: The MariaDB server is running with the --read-only option so it cannot execute this statement 
     86 keel-db-1
      1 --------------
    321 keel-db-2
1
                   Master_Host: fd11:a58a:88ef:0:cd53:dda9:f0cb:b889
              Slave_IO_Running: Yes
             Slave_SQL_Running: Yes
                    Last_Error: 
            Master_SSL_Allowed: Yes
                 Last_IO_Error: 
                Last_SQL_Error: 
                    Using_Gtid: Slave_Pos
2026-10-08T23:51:26+00:00 keel-db-1 systemd[1]: Finished keel-database-follow.service - keel database: the server follows the pair's VIP.
2026-10-08T23:51:26+00:00 keel-db-1 systemd[1]: keel-database-follow.service: Consumed 1.042s CPU time, 37.7M memory peak.
2026-10-08T23:52:12+00:00 keel-db-1 systemd[1]: Starting keel-database-follow.service - keel database: the server follows the pair's VIP...
2026-10-08T23:52:13+00:00 keel-db-1 runuser[13615]: pam_unix(runuser:session): session opened for user mysql(uid=104) by (uid=0)
2026-10-08T23:52:13+00:00 keel-db-1 runuser[13615]: pam_unix(runuser:session): session closed for user mysql
2026-10-08T23:52:13+00:00 keel-db-1 keel[13574]: database.server.role: unchanged (a replica of [fd11:a58a:88ef:0:cd53:dda9:f0cb:b889]:3306)
2026-10-08T23:52:13+00:00 keel-db-1 systemd[1]: keel-database-follow.service: Deactivated successfully.
2026-10-08T23:52:13+00:00 keel-db-1 systemd[1]: Finished keel-database-follow.service - keel database: the server follows the pair's VIP.

=== [9003] 2026-10-08T23:52:23Z rc=0
$ awk "\$4==0{print \"planned-\"\$3}" /root/writer-planned.log | sort > /tmp/acked; mariadb -N -h fd11:a58a:88ef::ffff:1 --defaults-extra-file=/root/.app.cnf -e "select note from keeltest.t where note like \"planned-%\"" | sort > /tmp/onvip; mariadb -N -e "select note from keeltest.t where note like \"planned-%\"" | sort > /tmp/onreplica; echo "acked $(wc -l </tmp/acked), on primary(VIP) $(wc -l </tmp/onvip), on replica db-1 $(wc -l </tmp/onreplica); acked but missing on primary: $(comm -23 /tmp/acked /tmp/onvip | wc -l); on replica: $(comm -23 /tmp/acked /tmp/onreplica | wc -l)"
mariadb: unknown variable 'defaults-extra-file=/root/.app.cnf'
acked 407, on primary(VIP) 0, on replica db-1 407; acked but missing on primary: 407; on replica: 0

=== [9003] 2026-10-08T23:52:31Z rc=0
$ mariadb --defaults-extra-file=/root/.app.cnf -N -h fd11:a58a:88ef::ffff:1 -e "select note from keeltest.t where note like \"planned-%\"" | sort > /tmp/onvip; echo "acked $(wc -l </tmp/acked), on primary db-2 via VIP $(wc -l </tmp/onvip), on replica db-1 $(wc -l </tmp/onreplica); acked but missing on primary: $(comm -23 /tmp/acked /tmp/onvip | wc -l); on replica: $(comm -23 /tmp/acked /tmp/onreplica | wc -l); extra not acked on primary: $(comm -13 /tmp/acked /tmp/onvip | tr "\n" " ")"
acked 407, on primary db-2 via VIP 407, on replica db-1 407; acked but missing on primary: 0; on replica: 0; extra not acked on primary: 

=== [host] 2026-10-08T23:53:53Z rc=0
$ pct exec 9003 -- systemd-run --unit=keeltest-writer-crash --collect /root/writer.sh crash 120; sleep 10; echo "pct stop 9004 at $(date -u +%T.%3N)"; time pct stop 9004; echo "stopped at $(date -u +%T.%3N)"; pct exec 9003 -- bash -c "date -u +%T.%3N; timeout 120 keel vip promote 2>&1; echo rc=\$?; date -u +%T.%3N"; echo "--- now with --old-primary-gone"; pct exec 9003 -- bash -c "date -u +%T.%3N; timeout 120 keel vip promote --old-primary-gone 2>&1; echo rc=\$?; date -u +%T.%3N; sleep 3; mariadb -N -e \"select @@read_only\"; keel vip status"
Running as unit: keeltest-writer-crash.service; invocation ID: a679e056f5d04379a493441f61171f44
pct stop 9004 at 23:52:52.622

real	0m3.444s
user	0m1.209s
sys	0m0.207s
stopped at 23:52:56.068
23:52:57.410
  fd11:a58a:88ef:0:cd53:dda9:f0cb:b889: [fd11:a58a:88ef:0:cd53:dda9:f0cb:b889]:51821 through wg0: timed out
asking the primary, o9tGVm/IKImyW2kgn22YjiWdEXpAr28T6WF9uc4yW1Q= at fd11:a58a:88ef:0:cd53:dda9:f0cb:b889, to release fd11:a58a:88ef::ffff:1…
the primary at fd11:a58a:88ef:0:cd53:dda9:f0cb:b889 did not release it: [fd11:a58a:88ef:0:cd53:dda9:f0cb:b889]:51821 through wg0: timed out. Nothing was changed. Only you know whether that node is gone: if it is, run keel vip promote --old-primary-gone
rc=24
23:53:17.863
--- now with --old-primary-gone
23:53:19.229
  fd11:a58a:88ef:0:cd53:dda9:f0cb:b889: [fd11:a58a:88ef:0:cd53:dda9:f0cb:b889]:51821 through wg0: timed out
asking the primary, o9tGVm/IKImyW2kgn22YjiWdEXpAr28T6WF9uc4yW1Q= at fd11:a58a:88ef:0:cd53:dda9:f0cb:b889, to release fd11:a58a:88ef::ffff:1…
the primary at fd11:a58a:88ef:0:cd53:dda9:f0cb:b889 did not answer ([fd11:a58a:88ef:0:cd53:dda9:f0cb:b889]:51821 through wg0: timed out); --old-primary-gone: it will drop the VIP when it learns the newer claim
  fd11:a58a:88ef:0:cd53:dda9:f0cb:b889: unreachable: [fd11:a58a:88ef:0:cd53:dda9:f0cb:b889]:51821 through wg0: timed out
  fd11:a58a:88ef::1: applied
1 peer(s) did not take the claim now; each takes it at its next keel vip check, and routes the VIP to the old primary until then
this node holds fd11:a58a:88ef::ffff:1 at epoch 3, on wg0, taken by 1 of 1 peer(s)
rc=0
23:53:49.763
0
vip fd11:a58a:88ef::ffff:1: this node's appliance.vip
  role: primary
  epoch 3, held by li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY= at fd11:a58a:88ef:0:382f:45b:553c:f11
  carried here: yes
  routed to: no peer

=== [9003] 2026-10-08T23:54:43Z rc=0
$ while systemctl is-active -q keeltest-writer-crash; do sleep 2; done; python3 /root/gap.py /root/writer-crash.log; awk "\$4!=0{print \$1, \$3, \$4, substr(\$0, index(\$0,\"ERROR\"), 90)}" /root/writer-crash.log | awk "{ \$1=strftime(\"%T\", \$1/1000) \".\" (\$1%1000); print }" | head -5; echo ...; awk "\$4!=0" /root/writer-crash.log | wc -l; awk "{print \$5}" /root/writer-crash.log | uniq -c; awk "\$4==0" /root/writer-crash.log | awk "BEGIN{p=0}{ if (p && \$1-p>3000) print \"last ok before gap:\", strftime(\"%T\",p/1000)\".\"p%1000, \"first ok after:\", strftime(\"%T\",\$2/1000)\".\"\$2%1000; p=\$2}"; journalctl -u keel-database-follow.service --since "23:53:40" --no-pager -o cat | grep -v pam_unix | head -8
writes: 445 ok, 30 failed; longest gap between two acknowledged writes: 56.00 s (seq 78 on keel-db-2 -> seq 109 on keel-db-1)
23:52:54.97 79 1 ERROR 2013 (HY000): Lost connection to server at 'handshake: reading initial communication
23:52:54.213 80 1 ERROR 2002 (HY000): Can't connect to server on 'fd11:a58a:88ef::ffff:1' (110)
23:52:56.332 81 1 ERROR 2002 (HY000): Can't connect to server on 'fd11:a58a:88ef::ffff:1' (110)
23:52:58.450 82 1 ERROR 2002 (HY000): Can't connect to server on 'fd11:a58a:88ef::ffff:1' (110)
23:53:00.569 83 1 ERROR 2002 (HY000): Can't connect to server on 'fd11:a58a:88ef::ffff:1' (110)
...
30
     78 keel-db-2
     30 ERROR
    367 keel-db-1
last ok before gap: 23:52:53.992 first ok after: 23:53:49.993
database.server.role: drained and promoted: this node replicates from nobody and takes writes
database.server.role: READ_ONLY ADMIN given back to the accounts the replica took it from
keel-database-follow.service: Deactivated successfully.
Finished keel-database-follow.service - keel database: the server follows the pair's VIP.
Starting keel-database-follow.service - keel database: the server follows the pair's VIP...
database.server.role: unchanged (the primary, writable)
keel-database-follow.service: Deactivated successfully.
Finished keel-database-follow.service - keel database: the server follows the pair's VIP.

=== [9003] 2026-10-08T23:54:53Z rc=0
$ awk "\$4==0{print \"crash-\"\$3}" /root/writer-crash.log | sort > /tmp/acked; mariadb -N -e "select note from keeltest.t where note like \"crash-%\"" | sort > /tmp/on1; echo "acked $(wc -l </tmp/acked); on new primary db-1 $(wc -l </tmp/on1); acked and missing: $(comm -23 /tmp/acked /tmp/on1 | wc -l); present but not acked: $(comm -13 /tmp/acked /tmp/on1 | tr "\n" " ")"; mariadb -N -e "select @@gtid_binlog_pos, @@gtid_binlog_state"; keel database status
acked 445; on new primary db-1 445; acked and missing: 0; present but not acked: 
0-388044305-878	0-650213503-511,0-388044305-878
pair: VIP fd11:a58a:88ef::ffff:1; role here primary
  other member: fd11:a58a:88ef:0:cd53:dda9:f0cb:b889 (o9tGVm/IKImyW2kgn22YjiWdEXpAr28T6WF9uc4yW1Q=)
  the primary's address: fd11:a58a:88ef:0:cd53:dda9:f0cb:b889
server: primary (mariadb --batch --skip-column-names --execute SELECT Host FROM mysql.user WHERE Repl_slave_priv = 'Y': replication is granted from fd11:a58a:88ef:0:cd53:dda9:f0cb:b889)
  read_only: false
  semi-synchronous: master ON, slave OFF, 0 replica(s) acknowledging, 112 commits acknowledged, 766 not
  replicating from: nobody
  gtid binlog_pos: 0-388044305-878
  gtid slave_pos: 0-650213503-511
  gtid current_pos: 0-388044305-878
  gtid binlog_state: 0-650213503-511,0-388044305-878
  certificate: keel-fd11-a58a-88ef-0-382f-45b-553c-f11 mariadb, for fd11:a58a:88ef:0:382f:45b:553c:f11, fd11:a58a:88ef::ffff:1, until 2026-11-07T23:47:42Z
vip fd11:a58a:88ef::ffff:1: this node's appliance.vip
  role: primary
  epoch 3, held by li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY= at fd11:a58a:88ef:0:382f:45b:553c:f11
  carried here: yes
  routed to: no peer

=== [9003] 2026-10-08T23:55:02Z rc=0
$ keel diff 2>&1 | grep -E "database|appliance.vip|^diff"; mariadb -N -e "show global status like \"Rpl_semi_sync_master_status\"; show global status like \"Rpl_semi_sync_master_clients\""
database.server.engine: same (mariadb)
database.server.role: same (primary)
database.server.listen: drift (declared fd11:a58a:88ef:0:382f:45b:553c:f11, ::1, observed *)
database.server.replication.allowed_from: not declared (observed fd11:a58a:88ef:0:cd53:dda9:f0cb:b889)
database.server.read_only: same (false)
database.server.semi_sync: same (on)
appliance.vip: same (fd11:a58a:88ef::ffff:1)
diff: 18 same, 2 drift, 0 unknown, 13 not declared, 5 not compared; drift found
Rpl_semi_sync_master_status	ON
Rpl_semi_sync_master_clients	0

=== [host] 2026-10-08T23:55:07Z rc=0
$ echo "pct start 9004 at $(date -u +%T.%3N)"; pct start 9004; echo "started at $(date -u +%T.%3N)"
pct start 9004 at 23:55:03.164
started at 23:55:07.939

=== [9004] 2026-10-08T23:55:47Z rc=0
$ for i in $(seq 1 90); do s=$(mariadb -e "show replica status\G" 2>/dev/null | grep -E "Slave_SQL_Running:" | awk "{print \$2}"); [ "$s" = Yes ] && break; sleep 2; done; date -u +%T.%3N; uptime -s; mariadb -N -e "select @@read_only"; ip -6 addr show wg0 | grep inet6; keel vip status; keel database status; ls /var/backups/keel/mariadb/ 2>&1; journalctl -b -u keel-database-follow.service -u keel-vip-check.service --no-pager -o short-iso | grep -v pam_unix | grep keel\\[ | head -20; ls /var/lib/keel/database/
23:55:46.595
2026-10-08 23:55:06
1
    inet6 fd11:a58a:88ef:0:cd53:dda9:f0cb:b889/64 scope global 
vip fd11:a58a:88ef::ffff:1: this node's appliance.vip
  role: replica
  epoch 3, held by li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY= at fd11:a58a:88ef:0:382f:45b:553c:f11
  fenced: this node lost it while cut off or away, and takes it again only by keel vip promote here
  carried here: no
  routed to: li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY=
pair: VIP fd11:a58a:88ef::ffff:1; role here replica; fenced
  other member: fd11:a58a:88ef:0:382f:45b:553c:f11 (li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY=)
  the primary's address: fd11:a58a:88ef:0:382f:45b:553c:f11
server: replica (mariadb --batch --execute SHOW REPLICA STATUS\G)
  read_only: true
  semi-synchronous: master ON, slave ON, 0 replica(s) acknowledging, 0 commits acknowledged, 367 not
  replicating from: [fd11:a58a:88ef:0:382f:45b:553c:f11]:3306; IO Yes, SQL Yes; lag 0; TLS Yes; GTID IO position 0-388044305-878
  gtid binlog_pos: 0-388044305-878
  gtid slave_pos: 0-388044305-878
  gtid current_pos: 0-388044305-878
  gtid binlog_state: 0-650213503-511,0-388044305-878
  certificate: keel-fd11-a58a-88ef-0-cd53-dda9-f0cb-b889 mariadb, for fd11:a58a:88ef:0:cd53:dda9:f0cb:b889, fd11:a58a:88ef::ffff:1, until 2026-11-07T23:47:52Z
vip fd11:a58a:88ef::ffff:1: this node's appliance.vip
  role: replica
  epoch 3, held by li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY= at fd11:a58a:88ef:0:382f:45b:553c:f11
  fenced: this node lost it while cut off or away, and takes it again only by keel vip promote here
  carried here: no
  routed to: li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY=
rejoin-20261008T235544Z.sql.zst
2026-10-08T23:55:12+00:00 keel-db-2 keel[640]: database.server.role: set read_only OFF: this role takes the application's writes
2026-10-08T23:55:43+00:00 keel-db-2 keel[867]: vip fd11:a58a:88ef::ffff:1: epoch 3, held by li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY= at fd11:a58a:88ef:0:382f:45b:553c:f11; this node no longer holds it
2026-10-08T23:55:43+00:00 keel-db-2 keel[867]: vip fd11:a58a:88ef::ffff:1: took epoch 3, held by li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY=
2026-10-08T23:55:44+00:00 keel-db-2 keel[891]: database.server.role: set read_only ON: a replica takes no writes of its own
2026-10-08T23:55:44+00:00 keel-db-2 keel[891]: database.server.role: a dump of what this node holds is kept at /var/backups/keel/mariadb/rejoin-20261008T235544Z.sql.zst
2026-10-08T23:55:44+00:00 keel-db-2 keel[891]: database.server.role: rejoined: no errant GTID, replicating from [fd11:a58a:88ef:0:382f:45b:553c:f11]:3306 over TLS from 0-650213503-511
read-only-admin
replication.secret
semi-sync

=== [9004] 2026-10-08T23:55:58Z rc=0
$ journalctl -b --no-pager -o short-iso | grep -E "keel\[|mariadbd.*(ready|read)|keel-vip|keel-database" | grep -v pam_unix | grep -vE "unchanged|skipped, unmet" | head -40
2026-10-08T23:55:09+00:00 keel-db-2 systemd[1]: Started keel-database-follow.path - Run keel database follow when the pair's VIP moves.
2026-10-08T23:55:09+00:00 keel-db-2 systemd[1]: Started keel-database-watch.timer - keel database: watch a pair's replication regularly.
2026-10-08T23:55:09+00:00 keel-db-2 systemd[1]: Started keel-vip-check.timer - keel vip: check the VIPs at boot and every minute.
2026-10-08T23:55:11+00:00 keel-db-2 mariadbd[479]: 2026-10-08 23:55:11 0 [Note] Starting ack receiver thread
2026-10-08T23:55:11+00:00 keel-db-2 mariadbd[479]: 2026-10-08 23:55:11 0 [Note] /usr/sbin/mariadbd: ready for connections.
2026-10-08T23:55:11+00:00 keel-db-2 systemd[1]: Starting keel-database-follow.service - keel database: the server follows the pair's VIP...
2026-10-08T23:55:11+00:00 keel-db-2 keel[288]: the members' listener (pid 629, uid 61610) serves [fd11:a58a:88ef:0:cd53:dda9:f0cb:b889]:51821
2026-10-08T23:55:12+00:00 keel-db-2 keel[640]: database.server.role: set read_only OFF: this role takes the application's writes
2026-10-08T23:55:12+00:00 keel-db-2 systemd[1]: keel-database-follow.service: Deactivated successfully.
2026-10-08T23:55:12+00:00 keel-db-2 systemd[1]: Finished keel-database-follow.service - keel database: the server follows the pair's VIP.
2026-10-08T23:55:42+00:00 keel-db-2 systemd[1]: Starting keel-vip-check.service - keel vip: learn newer claims of the VIPs this node knows...
2026-10-08T23:55:43+00:00 keel-db-2 systemd[1]: Starting keel-database-follow.service - keel database: the server follows the pair's VIP...
2026-10-08T23:55:43+00:00 keel-db-2 keel[867]: vip fd11:a58a:88ef::ffff:1: epoch 3, held by li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY= at fd11:a58a:88ef:0:382f:45b:553c:f11; this node no longer holds it
2026-10-08T23:55:43+00:00 keel-db-2 keel[867]: vip fd11:a58a:88ef::ffff:1: took epoch 3, held by li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY=
2026-10-08T23:55:43+00:00 keel-db-2 systemd[1]: keel-vip-check.service: Deactivated successfully.
2026-10-08T23:55:43+00:00 keel-db-2 systemd[1]: Finished keel-vip-check.service - keel vip: learn newer claims of the VIPs this node knows.
2026-10-08T23:55:44+00:00 keel-db-2 mariadbd[479]: 2026-10-08 23:55:44 72 [Note] Slave I/O thread: Start semi-sync replication to master 'repl@fd11:a58a:88ef:0:382f:45b:553c:f11:3306' in log '' at position 4
2026-10-08T23:55:44+00:00 keel-db-2 mariadbd[479]: 2026-10-08 23:55:44 73 [Note] Slave SQL thread initialized, starting replication in log 'FIRST' at position 4, relay log './mysqld-relay-bin.000001' position: 4; GTID position '0-650213503-511'
2026-10-08T23:55:44+00:00 keel-db-2 keel[891]: database.server.role: set read_only ON: a replica takes no writes of its own
2026-10-08T23:55:44+00:00 keel-db-2 keel[891]: database.server.role: a dump of what this node holds is kept at /var/backups/keel/mariadb/rejoin-20261008T235544Z.sql.zst
2026-10-08T23:55:44+00:00 keel-db-2 keel[891]: database.server.role: rejoined: no errant GTID, replicating from [fd11:a58a:88ef:0:382f:45b:553c:f11]:3306 over TLS from 0-650213503-511
2026-10-08T23:55:44+00:00 keel-db-2 mariadbd[479]: 2026-10-08 23:55:44 72 [Note] Slave I/O thread: connected to master 'repl@fd11:a58a:88ef:0:382f:45b:553c:f11:3306',replication starts at GTID position '0-650213503-511'
2026-10-08T23:55:44+00:00 keel-db-2 systemd[1]: keel-database-follow.service: Deactivated successfully.
2026-10-08T23:55:44+00:00 keel-db-2 systemd[1]: Finished keel-database-follow.service - keel database: the server follows the pair's VIP.
2026-10-08T23:55:44+00:00 keel-db-2 systemd[1]: keel-database-follow.service: Consumed 1.034s CPU time, 38.5M memory peak.

=== [9003] 2026-10-08T23:56:11Z rc=0
$ mariadb -N -e "show global status where variable_name in (\"Rpl_semi_sync_master_status\",\"Rpl_semi_sync_master_clients\"); select count(*), max(id) from keeltest.t"; grep -iE "^Address|ffff" /etc/wireguard/wg0.conf
Rpl_semi_sync_master_clients	1
Rpl_semi_sync_master_status	ON
868	868
Address = fd11:a58a:88ef:0:382f:45b:553c:f11/64

=== [9004] 2026-10-08T23:56:13Z rc=0
$ mariadb -N -e "select count(*), max(id) from keeltest.t"; grep -iE "^Address|ffff" /etc/wireguard/wg0.conf; ls /var/lib/keel/vip/; cat /var/lib/keel/role
868	868
Address = fd11:a58a:88ef:0:cd53:dda9:f0cb:b889/64
AllowedIPs = fd11:a58a:88ef:0:382f:45b:553c:f11/128, fd11:a58a:88ef::ffff:1/128
fd11:a58a:88ef::ffff:1.json
fd11:a58a:88ef::ffff:1.pair
lock
role=replica
replicates=database
vip=fd11:a58a:88ef::ffff:1

=== [9003] 2026-10-08T23:56:25Z rc=0
$ cat > /root/probe.sh <<'EOF'
#!/bin/bash
# test instrumentation: at boot, log read_only and whether wg0 carries the VIP, every 0.5 s for 90 s
for i in $(seq 1 180); do
  ro=$(mariadb -N -e "select @@read_only" 2>/dev/null || echo down)
  vip=$(ip -6 addr show wg0 2>/dev/null | grep -q "ffff:1/128" && echo VIP-on-wg0 || echo no-VIP)
  echo "$(date -u +%T.%3N) read_only=$ro $vip" >> /root/probe-boot.log
  sleep 0.5
done
EOF
chmod 700 /root/probe.sh; rm -f /root/probe-boot.log
cat > /etc/systemd/system/keeltest-probe.service <<EOF
[Unit]
Description=test probe (remove after the test)
[Service]
Type=simple
ExecStart=/root/probe.sh
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload; systemctl enable keeltest-probe.service 2>&1 | tail -1
Created symlink '/etc/systemd/system/multi-user.target.wants/keeltest-probe.service' → '/etc/systemd/system/keeltest-probe.service'.

=== [host] 2026-10-08T23:57:17Z rc=0
$ pct exec 9004 -- systemd-run --unit=keeltest-writer-crash2 --collect /root/writer.sh crash2 100; sleep 10; echo "pct stop 9003 at $(date -u +%T.%3N)"; pct stop 9003; echo "stopped at $(date -u +%T.%3N)"; pct exec 9004 -- bash -c "date -u +%T.%3N; timeout 120 keel vip promote --old-primary-gone 2>&1; echo rc=\$?; date -u +%T.%3N"
Running as unit: keeltest-writer-crash2.service; invocation ID: c7eeaa7137c54b7b9f6a6c7ecf8df82e
pct stop 9003 at 23:56:42.015
stopped at 23:56:45.450
23:56:46.798
  fd11:a58a:88ef:0:382f:45b:553c:f11: [fd11:a58a:88ef:0:382f:45b:553c:f11]:51821 through wg0: timed out
asking the primary, li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY= at fd11:a58a:88ef:0:382f:45b:553c:f11, to release fd11:a58a:88ef::ffff:1…
the primary at fd11:a58a:88ef:0:382f:45b:553c:f11 did not answer ([fd11:a58a:88ef:0:382f:45b:553c:f11]:51821 through wg0: timed out); --old-primary-gone: it will drop the VIP when it learns the newer claim
  fd11:a58a:88ef:0:382f:45b:553c:f11: unreachable: [fd11:a58a:88ef:0:382f:45b:553c:f11]:51821 through wg0: timed out
  fd11:a58a:88ef::1: applied
1 peer(s) did not take the claim now; each takes it at its next keel vip check, and routes the VIP to the old primary until then
this node holds fd11:a58a:88ef::ffff:1 at epoch 4, on wg0, taken by 1 of 1 peer(s)
rc=0
23:57:17.333

=== [host] 2026-10-08T23:57:32Z rc=0
$ echo "pct start 9003 at $(date -u +%T.%3N)"; pct start 9003; echo "started at $(date -u +%T.%3N)"; for i in $(seq 1 60); do pct exec 9003 -- systemctl is-active -q keeltest-probe.service 2>/dev/null || break; sleep 2; done
pct start 9003 at 23:57:25.754
started at 23:57:30.782

=== [9003] 2026-10-08T23:57:33Z rc=0
$ grep -v "read_only=down no-VIP" /root/probe-boot.log | awk "{k=\$2\" \"\$3; if (k!=p) {print; p=k}}"; tail -1 /root/probe-boot.log; journalctl -b --no-pager -o short-iso | grep keel\\[ | grep -E "read_only|rejoin|epoch|holds|dump" | head
grep: /root/probe-boot.log: No such file or directory
tail: cannot open '/root/probe-boot.log' for reading: No such file or directory

=== [9004] 2026-10-08T23:58:13Z rc=0
$ while systemctl is-active -q keeltest-writer-crash2; do sleep 2; done; python3 /root/gap.py /root/writer-crash2.log; awk "\$4==0" /root/writer-crash2.log | awk "BEGIN{p=0}{ if (p && \$1-p>3000) print \"last ok before gap:\", strftime(\"%T\",p/1000)\".\"p%1000, \"first ok after:\", strftime(\"%T\",\$2/1000)\".\"\$2%1000; p=\$2}"; awk "\$4==0{print \"crash2-\"\$3}" /root/writer-crash2.log | sort > /tmp/a; mariadb -N -e "select note from keeltest.t where note like \"crash2-%\"" | sort > /tmp/b; echo "acked $(wc -l </tmp/a), missing on db-2: $(comm -23 /tmp/a /tmp/b | wc -l)"
writes: 458 ok, 19 failed; longest gap between two acknowledged writes: 34.67 s (seq 80 on keel-db-1 -> seq 100 on keel-db-2)
last ok before gap: 23:56:43.427 first ok after: 23:57:18.97
acked 458, missing on db-2: 0

=== [9003] 2026-10-08T23:58:21Z rc=0
$ uptime -s; systemctl status keeltest-probe.service --no-pager | head -5; ls -l /root/probe-boot.log; awk "{k=\$2\" \"\$3; if (k!=p) {print; p=k}}" /root/probe-boot.log; journalctl -b --no-pager -o short-iso | grep keel\\[ | grep -E "read_only|rejoin|epoch|holds|dump|diverg" | head
2026-10-08 23:57:29
● keeltest-probe.service - test probe (remove after the test)
     Loaded: loaded (/etc/systemd/system/keeltest-probe.service; enabled; preset: enabled)
     Active: active (running) since Thu 2026-10-08 23:57:32 UTC; 48s ago
 Invocation: 62e939e9e9d043e6b00592f0f3c9fcbb
   Main PID: 199 (probe.sh)
-rw-r--r-- 1 root root 2720 Oct  8 23:58 /root/probe-boot.log
23:57:35.194 read_only=1 no-VIP
23:57:36.347 read_only=0 no-VIP
23:58:07.753 read_only=1 no-VIP
2026-10-08T23:57:36+00:00 keel-db-1 keel[691]: database.server.role: set read_only OFF: this role takes the application's writes
2026-10-08T23:58:06+00:00 keel-db-1 keel[1188]: vip fd11:a58a:88ef::ffff:1: epoch 4, held by o9tGVm/IKImyW2kgn22YjiWdEXpAr28T6WF9uc4yW1Q= at fd11:a58a:88ef:0:cd53:dda9:f0cb:b889; this node no longer holds it
2026-10-08T23:58:06+00:00 keel-db-1 keel[1188]: vip fd11:a58a:88ef::ffff:1: took epoch 4, held by o9tGVm/IKImyW2kgn22YjiWdEXpAr28T6WF9uc4yW1Q=
2026-10-08T23:58:07+00:00 keel-db-1 keel[1218]: database.server.role: set read_only ON: a replica takes no writes of its own
2026-10-08T23:58:07+00:00 keel-db-1 keel[1218]: database.server.role: a dump of what this node holds is kept at /var/backups/keel/mariadb/rejoin-20261008T235807Z.sql.zst
2026-10-08T23:58:07+00:00 keel-db-1 keel[1218]: database.server.role: rejoined: no errant GTID, replicating from [fd11:a58a:88ef:0:cd53:dda9:f0cb:b889]:3306 over TLS from 0-388044305-958

=== [9003] 2026-10-08T23:58:32Z rc=0
$ cp /root/probe-boot.log /root/probe-boot-1.log; systemctl disable --now keeltest-probe.service 2>&1 | tail -1; rm -f /etc/systemd/system/keeltest-probe.service; systemctl daemon-reload; mariadb -N -e "select @@read_only"; mariadb -e "show replica status\G" | grep -E "Master_Host|IO_Running|SQL_Running:|SSL_Allowed|Using_Gtid"
Removed '/etc/systemd/system/multi-user.target.wants/keeltest-probe.service'.
1
                   Master_Host: fd11:a58a:88ef:0:cd53:dda9:f0cb:b889
              Slave_IO_Running: Yes
             Slave_SQL_Running: Yes
            Master_SSL_Allowed: Yes
                    Using_Gtid: Slave_Pos

=== [9004] 2026-10-08T23:58:34Z rc=0
$ keel database status | head -12
pair: VIP fd11:a58a:88ef::ffff:1; role here primary
  other member: fd11:a58a:88ef:0:382f:45b:553c:f11 (li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY=)
  the primary's address: fd11:a58a:88ef:0:382f:45b:553c:f11
server: primary (mariadb --batch --skip-column-names --execute SHOW REPLICA HOSTS lists 1 replica(s) connected)
  read_only: false
  semi-synchronous: master ON, slave OFF, 1 replica(s) acknowledging, 30 commits acknowledged, 795 not
  replicating from: nobody
  gtid binlog_pos: 0-650213503-1336
  gtid slave_pos: 0-388044305-958
  gtid current_pos: 0-650213503-1336
  gtid binlog_state: 0-388044305-958,0-650213503-1336
  certificate: keel-fd11-a58a-88ef-0-cd53-dda9-f0cb-b889 mariadb, for fd11:a58a:88ef:0:cd53:dda9:f0cb:b889, fd11:a58a:88ef::ffff:1, until 2026-11-07T23:47:52Z

=== [host] 2026-10-08T23:59:06Z rc=0
$ pct exec 9003 -- systemd-run --unit=keeltest-writer-reinstall --collect /root/writer.sh reinstall 60; pct exec 9004 -- systemd-run --unit=keeltest-vipwatch --collect bash -c "for i in \$(seq 1 250); do echo \"\$(date -u +%T.%3N) \$(ip -6 addr show wg0 | grep -c ffff:1/128) \$(mariadb -N -e \"select @@read_only\" 2>/dev/null || echo down)\" >> /root/vipwatch.log; sleep 0.2; done"; sleep 10; pct exec 9004 -- bash -c "date -u +%T.%3N; DEBIAN_FRONTEND=noninteractive apt-get reinstall -y -q keel 2>&1 | grep -vE \"^(Reading|Building|Get:|Fetched|\(Reading)\"; echo rc=\$?; date -u +%T.%3N"
Running as unit: keeltest-writer-reinstall.service; invocation ID: 198e2a6c078f465b862404b19d58ce6d
Running as unit: keeltest-vipwatch.service; invocation ID: e1ba83e89b244715a499eeeba3132d15
23:58:57.031
[master 5f4a2a0] saving uncommitted changes in /etc prior to apt run
 11 files changed, 195 insertions(+)
 create mode 100644 keel/monit/keel-manifest.conf
 create mode 100644 mysql/keel-tls/ca.pem
 create mode 100644 mysql/keel-tls/crl.pem
 create mode 100644 mysql/keel-tls/server.key
 create mode 100644 mysql/keel-tls/server.pem
 create mode 100644 mysql/mariadb.conf.d/99-keel-database.cnf
 create mode 100644 mysql/mariadb.conf.d/99-keel-role.cnf
 create mode 100644 sysctl.d/90-keel-database.conf
 create mode 120000 systemd/system/multi-user.target.wants/keel-vip.service
0 upgraded, 0 newly installed, 1 reinstalled, 0 to remove and 0 not upgraded.
Need to get 0 B/402 kB of archives.
After this operation, 0 B of additional disk space will be used.
Preparing to unpack .../archives/keel_0.23.3_all.deb ...
Unpacking keel (0.23.3) over (0.23.3) ...
Setting up keel (0.23.3) ...
keel-mesh-sync.service is a disabled or a static unit not running, not starting it.
keel-mesh-etcd.service is a disabled or a static unit not running, not starting it.
keel-database-watch.service is a disabled or a static unit not running, not starting it.
Processing triggers for keel-overlay-vip (0.2.0) ...
rc=0
23:59:06.722

=== [9003] 2026-10-08T23:59:46Z rc=0
$ while systemctl is-active -q keeltest-writer-reinstall; do sleep 2; done; python3 /root/gap.py /root/writer-reinstall.log; awk "{print \$5}" /root/writer-reinstall.log | uniq -c
writes: 408 ok, 0 failed; longest gap between two acknowledged writes: 0.20 s (seq 155 on keel-db-2 -> seq 156 on keel-db-2)
    408 keel-db-2

=== [9004] 2026-10-08T23:59:48Z rc=0
$ while systemctl is-active -q keeltest-vipwatch; do sleep 2; done; awk "{k=\$2\" \"\$3; if (k!=p) {print; p=k}}" /root/vipwatch.log; wc -l < /root/vipwatch.log; keel vip status; mariadb -N -e "show global status where variable_name in (\"Rpl_semi_sync_master_status\",\"Rpl_semi_sync_master_clients\")"; systemctl is-active mariadb keel-database-follow.path keel-vip-check.timer
23:58:45.718 1 0
250
vip fd11:a58a:88ef::ffff:1: this node's appliance.vip
  role: primary
  epoch 4, held by o9tGVm/IKImyW2kgn22YjiWdEXpAr28T6WF9uc4yW1Q= at fd11:a58a:88ef:0:cd53:dda9:f0cb:b889
  carried here: yes
  routed to: no peer
Rpl_semi_sync_master_clients	1
Rpl_semi_sync_master_status	ON
active
active
active

=== [124] 2026-10-08T23:59:58Z rc=0
$ systemctl stop keeltest-etcdmon.service; echo "samples $(wc -l < /root/etcdmon.log), from $(head -1 /root/etcdmon.log | cut -d" " -f1) to $(tail -1 /root/etcdmon.log | cut -d" " -f1); not healthy: $(grep -vc " true$" /root/etcdmon.log)"; grep -v " true$" /root/etcdmon.log | head -3; rm -f /root/etcdmon.log; curl -s -m 2 http://[::1]:2381/health; echo; keel mesh status | grep -E "etcd|voter|leader|vip|peers:"; wg show wg0 allowed-ips | grep -E "li08|o9tG" || echo "no db peer on wg0"
samples 1036, from 23:42:16 to 23:59:57; not healthy: 0
{"health":"true","reason":""}
peers: 4
etcd: 3 voter(s), 0 learner(s)
  keel-fd11-a58a-88ef-0-47d1-8a55-262c-33ed  fd11:a58a:88ef:0:47d1:8a55:262c:33ed  voter  healthy
  keel-fd11-a58a-88ef--2  fd11:a58a:88ef::2  voter  healthy
  keel-fd11-a58a-88ef--1  fd11:a58a:88ef::1  voter  healthy
leader: keel-fd11-a58a-88ef--2
etcd: this member's certificate expires 2026-11-07 09:45 UTC
vip fd11:a58a:88ef::ffff:1: another pair's, routed
li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY=	fd11:a58a:88ef:0:382f:45b:553c:f11/128
o9tGVm/IKImyW2kgn22YjiWdEXpAr28T6WF9uc4yW1Q=	fd11:a58a:88ef:0:cd53:dda9:f0cb:b889/128 fd11:a58a:88ef::ffff:1/128

=== [125] 2026-10-09T00:00:01Z rc=0
$ systemctl stop keeltest-etcdmon.service; echo "samples $(wc -l < /root/etcdmon.log), from $(head -1 /root/etcdmon.log | cut -d" " -f1) to $(tail -1 /root/etcdmon.log | cut -d" " -f1); not healthy: $(grep -vc " true$" /root/etcdmon.log)"; grep -v " true$" /root/etcdmon.log | head -3; rm -f /root/etcdmon.log; curl -s -m 2 http://[::1]:2381/health; echo; keel mesh status | grep -E "etcd|voter|leader|vip|peers:"; wg show wg0 allowed-ips | grep -E "li08|o9tG" || echo "no db peer on wg0"
samples 1008, from 23:42:18 to 00:00:00; not healthy: 62
23:45:53 FAIL
23:45:55 FAIL
23:45:57 FAIL
{"health":"true","reason":""}
peers: 3
etcd: 3 voter(s), 0 learner(s)
  keel-fd11-a58a-88ef-0-47d1-8a55-262c-33ed  fd11:a58a:88ef:0:47d1:8a55:262c:33ed  voter  healthy
  keel-fd11-a58a-88ef--2  fd11:a58a:88ef::2  voter  healthy
  keel-fd11-a58a-88ef--1  fd11:a58a:88ef::1  voter  healthy
leader: keel-fd11-a58a-88ef--2
etcd: this member's certificate expires 2026-11-07 09:45 UTC
vip: none (this node declares no appliance.vip and routes no other pair's)
no db peer on wg0

=== [web2] 2026-10-09T00:00:04Z rc=0
$ systemctl stop keeltest-etcdmon.service; echo "samples $(wc -l < /root/etcdmon.log), from $(head -1 /root/etcdmon.log | cut -d" " -f1) to $(tail -1 /root/etcdmon.log | cut -d" " -f1); not healthy: $(grep -vc " true$" /root/etcdmon.log)"; grep -v " true$" /root/etcdmon.log | head -3; rm -f /root/etcdmon.log; curl -s -m 2 http://[::1]:2381/health; echo; keel mesh status | grep -E "etcd|voter|leader|vip|peers:"; wg show wg0 allowed-ips | grep -E "li08|o9tG" || echo "no db peer on wg0"

samples 1025, from 23:42:20 to 00:00:03; not healthy: 0
{"health":"true","reason":""}
Warning: /etc/keel/instance.yaml: overlays.vip: not declared (default: disabled): the chain of web gained it after this spec was last applied, so it takes the manifest's default for cloud_advanced; write it out (decisions 0027, 0041)
peers: 2
etcd: 3 voter(s), 0 learner(s)
  keel-fd11-a58a-88ef-0-47d1-8a55-262c-33ed  fd11:a58a:88ef:0:47d1:8a55:262c:33ed  voter  healthy
  keel-fd11-a58a-88ef--2  fd11:a58a:88ef::2  voter  healthy
  keel-fd11-a58a-88ef--1  fd11:a58a:88ef::1  voter  healthy
leader: keel-fd11-a58a-88ef--2
etcd: this member's certificate expires 2026-11-07 09:45 UTC
vip: none (this node declares no appliance.vip and routes no other pair's)
no db peer on wg0

=== [125] 2026-10-09T00:00:16Z rc=0
$ journalctl -u keel-mesh-sync.service --since "23:45:30" --until "23:59" --no-pager -o short-iso | grep -v unchanged | grep -vE "^--" | tail -14; journalctl -u etcd --since "23:45:40" --until "23:50:30" --no-pager -o cat | grep -oE "\"ts\":\"[^\"]+\",\"caller\":\"[^\"]+\",\"msg\":\"[^\"]{0,90}" | sed -E "s/\"ts\":\"2026-10-08T([0-9:.]{12})[0-9]*Z\",\"caller\":\"[^\"]+\",\"msg\":\"/\1 /" | awk "{m=\$0; sub(/^[^ ]+ /,\"\",m); if (m!=p) {print; p=m}}" | head -25


=== [125] 2026-10-09T00:00:22Z rc=0
$ date; journalctl -u keel-mesh-sync.service -S "2026-10-08 23:45:30" -U "2026-10-08 23:59:00" --no-pager -o short-iso | grep -v unchanged | tail -14; echo ---; journalctl -u etcd -S "2026-10-08 23:45:40" -U "2026-10-08 23:50:30" --no-pager -o cat | wc -l
Fri Oct  9 12:00:22 AM UTC 2026
2026-10-08T23:45:40+00:00 keel-web-3 systemd[1]: Starting keel-mesh-sync.service - keel mesh: learn the members this node's peers know...
2026-10-08T23:45:51+00:00 keel-web-3 keel[92759]: member fd11:a58a:88ef:0:382f:45b:553c:f11 did not answer: [fd11:a58a:88ef:0:382f:45b:553c:f11]:51821 through wg0: timed out
2026-10-08T23:45:51+00:00 keel-web-3 keel[92759]: o9tGVm/IKImyW2kgn22YjiWdEXpAr28T6WF9uc4yW1Q= is tried again after 00:15 UTC: it did not answer the last time
2026-10-08T23:45:51+00:00 keel-web-3 keel[92759]: the spec names 1 peer(s) that wg0 lacks: li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY=; the overlay is applied again (keel#96)
2026-10-08T23:45:52+00:00 keel-web-3 keel[92759]: member li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY= applied again at fd11:a58a:88ef:0:382f:45b:553c:f11, through [<uplink>]:51820
2026-10-08T23:45:52+00:00 keel-web-3 keel[92759]: confirming over the overlay…
2026-10-08T23:47:52+00:00 keel-web-3 keel[92759]: network.overlay: bring the overlay wg0 up on a new /etc/wireguard/wg0.conf (wg-quick down, then up); it reverts in 120 s unless `keel network confirm` is run from a new session, over the overlay or the uplink: done
2026-10-08T23:47:52+00:00 keel-web-3 keel[92759]: keel mesh: 1 change(s), 0 failed
2026-10-08T23:47:52+00:00 keel-web-3 keel[92759]: no member completed a WireGuard handshake within the window: the change reverts by itself, the spec is put back as it was, and keel mesh sync tries again (a new member after an hour)
2026-10-08T23:47:52+00:00 keel-web-3 systemd[1]: keel-mesh-sync.service: Main process exited, code=exited, status=21/n/a
2026-10-08T23:47:52+00:00 keel-web-3 systemd[1]: keel-mesh-sync.service: Failed with result 'exit-code'.
2026-10-08T23:47:52+00:00 keel-web-3 systemd[1]: Failed to start keel-mesh-sync.service - keel mesh: learn the members this node's peers know.
2026-10-08T23:47:52+00:00 keel-web-3 systemd[1]: keel-mesh-sync.service: Consumed 1.007s CPU time, 26.7M memory peak.
---
410

=== [125] 2026-10-09T00:00:40Z rc=0
$ journalctl -u etcd -S "2026-10-08 23:45:40" -U "2026-10-08 23:50:30" --no-pager -o cat | python3 -c "
import sys,json
last=None
for l in sys.stdin:
    try: j=json.loads(l)
    except Exception: continue
    m=j.get(\"msg\",\"\")[:80]; peer=j.get(\"remote-peer-id\",j.get(\"peer-id\",\"\"))
    k=(m,peer)
    if k!=last: print(j.get(\"ts\",\"\")[11:23], j.get(\"level\"), m, peer); last=k
" | head -30
23:45:53.294 warn waiting for ReadIndex response took too long, retrying 
23:45:53.793 warn apply request took too long 
23:45:53.795 warn waiting for ReadIndex response took too long, retrying 
23:45:53.798 info trace[1181576741] range 
23:45:53.798 warn serving /health false; Range fails 
23:45:53.802 warn /health error 
23:45:54.295 warn waiting for ReadIndex response took too long, retrying 
23:45:55.813 warn apply request took too long 
23:45:55.814 info trace[664494740] range 
23:45:55.814 warn serving /health false; Range fails 
23:45:55.814 warn /health error 
23:45:56.298 warn waiting for ReadIndex response took too long, retrying 
23:45:57.833 warn apply request took too long 
23:45:57.833 info trace[737958253] range 
23:45:57.833 warn serving /health false; Range fails 
23:45:57.833 warn /health error 
23:45:58.302 warn waiting for ReadIndex response took too long, retrying 
23:45:59.854 warn apply request took too long 
23:45:59.854 info trace[2088220344] range 
23:45:59.854 warn serving /health false; Range fails 
23:45:59.854 warn /health error 
23:46:00.306 warn waiting for ReadIndex response took too long, retrying 
23:46:00.371 info 35a79755ebcad0f9 is starting a new election at term 5 
23:46:00.371 info 35a79755ebcad0f9 became pre-candidate at term 5 
23:46:00.371 info 35a79755ebcad0f9 received MsgPreVoteResp from 35a79755ebcad0f9 at term 5 
23:46:00.371 info 35a79755ebcad0f9 [logterm: 5, index: 1314] sent MsgPreVote request to 82c7157cb0 
23:46:00.372 info 35a79755ebcad0f9 [logterm: 5, index: 1314] sent MsgPreVote request to f7ef316bc9 
23:46:00.372 info raft.node: 35a79755ebcad0f9 lost leader 82c7157cb0ac8fe3 at term 5 
23:46:00.807 warn waiting for ReadIndex response took too long, retrying 
23:46:00.873 warn serving /health false; no leader 
Traceback (most recent call last):
  File "<string>", line 9, in <module>
    if k!=last: print(j.get("ts","")[11:23], j.get("level"), m, peer); last=k
                ~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
BrokenPipeError: [Errno 32] Broken pipe

=== [125] 2026-10-09T00:00:48Z rc=0
$ journalctl -u etcd -S "2026-10-08 23:45:40" -U "2026-10-08 23:50:30" --no-pager -o cat | python3 -c "
import sys,json
for l in sys.stdin:
    try: j=json.loads(l)
    except Exception: continue
    m=j.get(\"msg\",\"\")
    if any(s in m for s in (\"elected leader\",\"lost leader\",\"became leader\",\"became follower\",\"peer became\",\"lost TCP\",\"established TCP\")) or m.startswith(\"serving /health\"):
        print(j.get(\"ts\",\"\")[11:23], m[:90])
" 2>/dev/null | awk "{m=\$0; sub(/^[^ ]+ /,\"\",m); if (m!=p) {print; p=m}}" | head -30; journalctl -u etcd -S "2026-10-08 23:45:40" -U "2026-10-08 23:50:30" --no-pager -o cat | grep -c "serving /health false"; journalctl -u etcd -S "2026-10-08 23:45:40" -U "2026-10-08 23:50:30" --no-pager -o cat | grep "serving /health false" | tail -1 | cut -c1-60
23:45:53.798 serving /health false; Range fails
23:46:00.372 raft.node: 35a79755ebcad0f9 lost leader 82c7157cb0ac8fe3 at term 5
23:46:00.873 serving /health false; no leader
23:46:18.441 35a79755ebcad0f9 became follower at term 5
23:46:18.441 raft.node: 35a79755ebcad0f9 elected leader 82c7157cb0ac8fe3 at term 5
23:46:20.204 serving /health false; Range fails
23:46:57.799 peer became inactive (message send to peer failed)
23:46:57.800 lost TCP streaming connection with remote peer
23:46:57.806 peer became active
23:46:57.843 established TCP streaming connection with remote peer
23:47:54.329 serving /health false; Range fails
23:48:01.571 raft.node: 35a79755ebcad0f9 lost leader 82c7157cb0ac8fe3 at term 5
23:48:02.407 serving /health false; Range fails
23:48:03.425 serving /health false; no leader
23:48:19.273 35a79755ebcad0f9 became follower at term 5
23:48:19.273 raft.node: 35a79755ebcad0f9 elected leader 82c7157cb0ac8fe3 at term 5
62
{"level":"warn","ts":"2026-10-08T23:48:18.713310Z","caller":

=== [9003] 2026-10-09T00:01:03Z rc=0
$ keel diff 2>&1 | grep -E "drift|database|appliance|^diff|diverg"; echo "diff rc=${PIPESTATUS[0]}"; keel database status | head -6; ls /var/lib/keel/database/; cat /var/lib/keel/role
database.server.engine: same (mariadb)
database.server.role: not compared (the role is runtime state on a paired node (appliance.vip, decisions 0020 and 0049): the VIP makes this node the replica, the server is a replica, and the declared primary is the installation's; nothing converges it)
database.server.listen: drift (declared fd11:a58a:88ef:0:382f:45b:553c:f11, ::1, observed *)
database.server.replication.primary.host: not declared (observed fd11:a58a:88ef:0:cd53:dda9:f0cb:b889)
database.server.replication.primary.port: not declared (observed 3306)
database.server.read_only: same (true)
database.server.semi_sync: not compared (compared on the primary, whose commits wait for the replica; this node is the replica)
appliance.name: same (mariadb)
appliance.vip: same (fd11:a58a:88ef::ffff:1)
overlays.vip: drift (declared enabled, observed keel-vip.service enabled and inactive)
diff: 16 same, 2 drift, 0 unknown, 14 not declared, 7 not compared; drift found
diff rc=14
pair: VIP fd11:a58a:88ef::ffff:1; role here replica; fenced
  other member: fd11:a58a:88ef:0:cd53:dda9:f0cb:b889 (o9tGVm/IKImyW2kgn22YjiWdEXpAr28T6WF9uc4yW1Q=)
  the primary's address: fd11:a58a:88ef:0:cd53:dda9:f0cb:b889
server: replica (mariadb --batch --execute SHOW REPLICA STATUS\G)
  read_only: true
  semi-synchronous: master ON, slave ON, 0 replica(s) acknowledging, 0 commits acknowledged, 786 not
read-only-admin
replication.secret
semi-sync
role=replica
replicates=database
vip=fd11:a58a:88ef::ffff:1

=== [9004] 2026-10-09T00:01:06Z rc=0
$ keel diff 2>&1 | grep -E "drift|database|appliance|^diff|diverg"; echo "diff rc=${PIPESTATUS[0]}"; keel database status | head -6; ls /var/lib/keel/database/; cat /var/lib/keel/role
database.server.engine: same (mariadb)
database.server.role: not compared (the role is runtime state on a paired node (appliance.vip, decisions 0020 and 0049): the VIP makes this node the primary, the server is a primary, and the declared replica is the installation's; nothing converges it)
database.server.listen: drift (declared fd11:a58a:88ef:0:cd53:dda9:f0cb:b889, ::1, observed *)
database.server.replication.allowed_from: not declared (observed fd11:a58a:88ef:0:382f:45b:553c:f11)
database.server.read_only: same (false)
database.server.semi_sync: same (on)
appliance.name: same (mariadb)
appliance.vip: same (fd11:a58a:88ef::ffff:1)
overlays.vip: drift (declared enabled, observed keel-vip.service enabled and inactive)
diff: 17 same, 2 drift, 0 unknown, 13 not declared, 6 not compared; drift found
diff rc=14
pair: VIP fd11:a58a:88ef::ffff:1; role here primary
  other member: fd11:a58a:88ef:0:382f:45b:553c:f11 (li08e1grPY0Xz9OGzLYeJ56RX6C+jSZmB/I1tKq5lmY=)
  the primary's address: fd11:a58a:88ef:0:382f:45b:553c:f11
server: primary (mariadb --batch --skip-column-names --execute SHOW REPLICA HOSTS lists 1 replica(s) connected)
  read_only: false
  semi-synchronous: master ON, slave OFF, 1 replica(s) acknowledging, 438 commits acknowledged, 795 not
replication.secret
semi-sync
role=primary
replicates=database
vip=fd11:a58a:88ef::ffff:1

=== [host] 2026-10-09T00:01:08Z rc=0
$ pct list | grep -E "^(900[3-6]) "
9003       running                 keel-db-1           
9004       running                 keel-db-2           

```
