# Evidence: an etcd witness on BR3-THIN for the PostgreSQL pair

Date: 2026-10-15, 10:40 to 11:43 UTC.
Decision: 0057 (handbook#77), 0054, 0049, 0025.
Approval: the maintainer approved this test and the use of BR3-THIN.
Issues opened: Keel-Linux/keel#161 to #169. A comment on keel#156.

Machines:

| Site | Host | CT | Role | Overlay |
| --- | --- | --- | --- | --- |
| BR1 | hw12-br1 | 9054 | PostgreSQL pair node, root CA holder | `fd1a:bb4c:b407::1` |
| BR2 | nfs1-br2 | 9062 | PostgreSQL pair node | `fd1a:bb4c:b407::fc0a` |
| BR3 | BR3-THIN (`pve`) | 9071, new | etcd witness, no role | `fd1a:bb4c:b407::a237` |

- VIP: `fd1a:bb4c:b407::ffff:1`. keel 0.23.21 on the 3 CTs.
- No other CT or VM was changed. On the hosts, the test loaded
  `sch_netem` and removed it at the end.
- Output is trimmed. Times are Unix seconds of the CT clocks; in the
  tables, `2439.65` means `1792062439.65`. No secret is in this file.

## Summary

| Item | Result | Numbers |
| --- | --- | --- |
| Witness CT on BR3-THIN | PASS | Keel Core 19.0-10, 512 MB, 192 MB used; joined by `keel mesh invite` and `keel mesh join` in 11.3 s |
| Pair moves to `cloud_advanced` (0057) | PASS | `keel spec apply --system-only`: 7 changes, 0 failed on each node; VIP kept |
| etcd of 3 sites | PASS, with a false error | `keel mesh etcd form`: 3 voters healthy; exit 24, "not reached" (keel#162) |
| The claim made before etcd | FAIL | no lease after the form: no fence, no failover (keel#161) |
| Planned switchover | FAIL, then restored | 4.0 s, but the old primary diverged by its shutdown checkpoint (keel#163) |
| `keel-database-follow.path` | FAIL | triggers itself every 1 to 2 s; start limit hit (keel#164) |
| (c) automatic VIP failover, base | PARTIAL | VIP on B 20.7 s after the cut; writes wait until the operator (keel#165) |
| (c) operator promote, base | PASS, bound FAIL | 0 of 30 acknowledged ids lost; first write 11.9 s after the VIP (bound 5 s, keel#169) |
| (c) operator promote, netem 250 ms | PASS, bound FAIL | 0 of 20 lost; VIP on B 36.7 s after the cut; first write 12.9 s after the VIP (keel#169) |
| Automatic failover a 2nd time | FAIL | the rejoined node stays VIP-fenced (keel#166) |
| (e) old primary returns, base and netem | PASS | fenced, dumped and recorded after the heal; writable 3.8 s and 2.9 s before the fence (keel#156 comment) |
| Cut of BR3 (witness) | PASS, with a blip | writes go on; VIP off 2.3 s when the witness is the etcd leader (keel#167) |
| Cut of BR2 (standby) | PASS at base; 1 of 2 FAIL under netem | base: VIP kept, writes wait (0054); netem run 1: no etcd leader for 111 s, pair down 180 s (keel#167, #168) |
| End state | PASS | pair works, netem removed |

## 1. BR3-THIN: network and CT

BR3-THIN gets the public `/112` over the WireGuard interface `pop`.
`pop` is point to point, so the far end routes the whole `/112` to
the host, and no NDP proxy is necessary. The CT gets 1 address of it
on a host-only bridge. The host routes that `/128` to the bridge and
forwards.

```
# /etc/network/interfaces.d/vmbr1-keel-cts on BR3-THIN
auto vmbr1
iface vmbr1 inet6 manual
	bridge-ports none
	bridge-stp off
	bridge-fd 0
	mtu 1420
	post-up ip -6 addr add fe80::1/64 dev vmbr1 || true
	post-up ip -6 route replace 2804:710:d0:c::1:10/128 dev vmbr1

# /etc/sysctl.d/90-keel-ct-forward.conf
net.ipv6.conf.all.forwarding = 1
net.ipv6.conf.vmbr0.accept_ra = 2
```

The `wg-quick` rules of `pop` (`suppress_prefixlength 0`, then table
51820) send the forwarded packets of the CT out through `pop`. The
`/128` in the main table brings the return packets to `vmbr1`.

The image is the published Keel Core pre-release on git.pop.coop
(`keel-core` release `testing-19.0-10-step12-20261012`):

```
$ sha256sum debian-13-keel-core_19.0-10+step12_amd64.tar.zst     # on BR3-THIN and on BR1
7cdeea90b318d48a0cc1a45100bdf1fb1bbd3aef08da410d986325312a812676
$ pct create 9071 local:vztmpl/debian-13-keel-core_19.0-10+step12_amd64.tar.zst \
    --hostname keel-witness-br3 --cores 1 --memory 512 --swap 256 --rootfs local-lvm:4 \
    --unprivileged 1 --features nesting=1 \
    --net0 name=eth0,bridge=vmbr1,ip6=2804:710:d0:c::1:10/128,gw6=fe80::1,mtu=1420,type=veth
$ ping -6 -c3 2804:710:d0:2::12                  # in 9071
rtt min/avg/max/mdev = 31.176/33.300/36.690/2.422 ms
$ apt-get install -y keel                         # in 9071: 0.23.13 to 0.23.21
etcd-server 3.5.16-4, keel 0.23.21, keel-core 0.1.3, keel-overlay-etcd 0.4.0, keel-overlay-vip 0.2.0
```

`mtu=1420` on the CT keeps the outer packets of the mesh inside the
MTU of `pop`. The keel overlay `wg0` has MTU 1280. A ping with 1232
bytes and "do not fragment" passed between all 3 nodes.

The spec of the witness (0057, point 1):

```yaml
installation:
  mode: cloud_advanced
appliance:
  name: core
overlays: {installer: enabled, wireguard: enabled, etcd: enabled, crowdsec: enabled, vip: disabled}
```

Note: at the first start of the CT, `confconsole` failed on the console
with `dialog.DialogError` (status 3). The boot went on. This is the
known class of the headless first boot.

## 2. The pair moves to cloud advanced, and etcd forms

### The mode move (0057, point 3)

Each spec got `installation.mode: cloud_advanced` and every overlay of
the chain, with `etcd: enabled` and `vip: enabled`. The old spec is
`/root/instance.yaml.pre-advanced-20261015` on each node.

```
$ keel spec apply --system-only           # on 9054 at 1487.48, on 9062 at 1499.72
overlays.etcd: etcd waits for its cluster: it forms at the third cloud advanced member's join, or with keel mesh etcd form; nothing is started until then
overlays.vip: enable keel-vip.service ... done
apply --system-only: 7 change(s), 0 failed
```

On 9062, the VIP holder, a sampler saw the VIP on `wg0` in 68 of 68
samples (every 0.5 s) during the apply.

### The join of the witness

```
$ keel mesh invite --endpoint 2804:710:d0:5:6151:dafe:4c87:337c       # on 9054
invite e7115c1dd50defa5: fd1a:bb4c:b407::a237/64 reserved for the new node ...
$ keel mesh join --endpoint 2804:710:d0:c::1:10 -                       # on 9071, token on stdin, 1568.16 to 1579.46
joined the mesh: this node is fd1a:bb4c:b407::a237/64 on wg0
the mesh has 3 nodes: this node has them all as peers, and the inviter announces this node to the 1 other(s)
etcd: this node is ready; 2 of 3 ready members known, etcd forms at the third
```

9062 held no etcd certificate, so it was not "ready". Thus etcd did not
form at the join, and `keel mesh etcd form` ran on the root's holder.

### The form

```
$ keel mesh etcd form --dry-run                  # on 9054
would enroll fd1a:bb4c:b407::fc0a
would form a cluster of 3: this node and fd1a:bb4c:b407::fc0a, fd1a:bb4c:b407::a237
$ keel mesh etcd form                            # 1623.03 to 1661.01
etcd: a cluster of 3 formed from this node; keel mesh status shows its leader once a majority runs
etcd: not reached: fd1a:bb4c:b407::fc0a ([fd1a:bb4c:b407::fc0a]:51821 did not answer: timed out); run keel mesh etcd form again once they answer
rc=24
$ keel mesh status                               # 10 s later
etcd: 3 voter(s), 0 learner(s)
  keel-fd1a-bb4c-b407--fc0a  fd1a:bb4c:b407::fc0a  voter  healthy
  keel-fd1a-bb4c-b407--a237  fd1a:bb4c:b407::a237  voter  healthy
  keel-fd1a-bb4c-b407--1     fd1a:bb4c:b407::1     voter  healthy
```

9062 started etcd at 1627.99 and waited for a majority until 1658.20.
The answer to the holder came after the channel's timeout (keel#162).

**Where the etcd members live:** the member list, the certificates and
the formation record are state under `/var/lib/keel/etcd` on each
member, rendered into `/etc/default/etcd` (`ETCD_INITIAL_CLUSTER`). The
spec holds only `overlays.etcd: enabled` (0048, third round, point 2).

### The claim made before etcd (keel#161)

After the form and 1 run of `keel mesh etcd tend`, etcd held no key
under `/keel/<mesh>/vip/`. The state of 9062 had `"lease": null`, and
the VIP had `valid_lft forever`. `keel vip promote` on the holder says
"holds already". So the pair had etcd, but no lease fence and no
automatic failover.

### A planned switchover to get a lease (keel#163)

```
$ keel database promote                           # on 9054, 2057.44 to 2061.46
released by fd1a:bb4c:b407::fc0a
this node holds fd1a:bb4c:b407::ffff:1 at epoch 9, by etcd's lease 15095466573827747
$ ip -6 addr show wg0                             # on 9054
inet6 fd1a:bb4c:b407::ffff:1/128 scope global nodad deprecated dynamic  valid_lft 7sec
```

All 16 writes that 9062 acknowledged are on 9054. But 9062 stopped
after 9054 promoted, and its shutdown checkpoint is a record that 9054
never got:

```
00000003.history on 9054:  2  0/385CAB0  no recovery target specified
pg_controldata on 9062:    Latest checkpoint location: 0/385CAB0, TimeLineID 2
9062: refused: diverged: ... (timeline 2 against the holder's 3)
```

**Restore 1** (product path): `keel spec apply --system-only
--destroy-local-database` on 9062, 2264.36 to 2275.17 (10.8 s),
streaming 0.07 s later, `keel|streaming|sync` on 9054.

### The follow path (keel#164)

With etcd, `keel-database-follow.path` starts the follow service again
0.2 to 1 s after each run. On the replica it hits the start limit in a
few seconds, and the path stays `failed`. `keel spec apply` does not
start it, and `keel diff` shows no drift.

**Restore 2** (by hand, units only): `systemctl reset-failed
keel-database-follow.path keel-database-follow.service; systemctl start
keel-database-follow.path` on both nodes at 2815.51 and 2817.73. The
path failed again on the replica 8 s later. The rest of the test ran
with the path failed. The database watch (every 30 s) did the follow.

## 3. Network profiles

Overlay RTT, 50 pings each at base, 300 pings each under netem:

| Sites | Base | netem |
| --- | --- | --- |
| BR1 to BR2 | 4.3 ms (3.5 to 5.7) | 253.9 ms (233.3 to 278.0), 1.67 % loss |
| BR1 to BR3 | 42.6 ms (25.7 to 139.9) | 284.0 ms (258.1 to 326.3), 2 % loss |
| BR2 to BR3 | 44.6 ms (30.2 to 131.0) | 285.4 ms (260.9 to 326.7), 2 % loss |

netem: `tc qdisc add dev eth0 root netem delay 125ms 12ms loss 1%` in
each of the 3 CTs, half of the delay on each side, as on 2026-10-14.

## 4. The method

- **The writer.** `/root/writer.sh` on each pair node, as on
  2026-10-14. It writes through the local socket only while the node
  carries the VIP, counts a write as acknowledged only on a clean
  `INSERT 0 1`, and kills a write after 30 s with SIGKILL.
- **The VIP sampler.** `/root/vipwatch.sh` prints each change of the
  VIP on `wg0`, every 0.1 s, so the writer's 30 s waits do not hide a
  change.
- **The cut.** In the cut CT, an nft table `inet keeltest` drops UDP
  port 51820 in and out. The CT stays alive: this is a partition, not
  a stop. The heal is `nft delete table inet keeltest`.
- The logs go through `pct exec` and ssh to the workstation, so a cut
  CT keeps its log.

## 5. Case (c), base network

### Run 1: automatic failover (keel#165)

A = 9054 (primary, epoch 9), B = 9062 (standby). Cut of A at 2418.97.

| Time | From the cut | Event |
| --- | --- | --- |
| 2418.68 | | last acknowledged write on A (id 300036) |
| 2439.65 | 20.7 s | B: "claimed at epoch 10: the lease of epoch 9 is gone" |
| 2450.41 | 31.4 s | B out of recovery, by the watch (the path was failed) |
| 2450 to 2703 | | every write on B waits: `FIRST 1 (keel)`, no standby; 27 writes killed after 30 s |
| 2703.55 | | operator: `keel database promote --old-primary-gone` on B: "commits alone", 2.2 s |
| 2705.92 | | a write on B: `INSERT 0 1` in 0.07 s |

Acknowledged ids on A: 37 (300000 to 300036). All 37 are on B. Id
300037 had no ack, and it is only in A's dump. 6 writes on B that the
writer killed were committed when the promote released them.

### Run 2: the operator path of `docs/replication-postgresql.md` (keel#166, #169)

A = 9062 (primary, epoch 10), B = 9054 (standby, rejoined after run 1).
Cut of A at 2863.24.

| Time | From the cut | Event |
| --- | --- | --- |
| 2863.21 | | last acknowledged write on A (id 500029) |
| 2870.70 | 7.5 s | the VIP is off A (the kernel lifetime of the address) |
| 2870 to 2924 | | B does not claim: its state says `fenced` since run 1 (keel#166) |
| 2924.84 | 61.6 s | operator: `keel database promote --old-primary-gone` on B |
| 2927.87 | | the VIP on B, epoch 11 (3.0 s after the promote started) |
| 2939.45 | | B out of recovery |
| 2939.76 | | first write acknowledged on B: 11.9 s after the VIP (bound 5 s) |

Acknowledged ids on A: 30. All 30 are on B.

| What | etcd, base | etcd, netem | No etcd, 2026-10-14 | CI |
| --- | --- | --- | --- | --- |
| The VIP off the cut primary | 7.5 s | 7.4 s | never (it kept it) | - |
| Automatic claim by B | 20.7 s (run 1); none in run 2 (keel#166) | none (keel#166) | - | - |
| `promote --old-primary-gone`, to the VIP on B | 3.0 s | 29.7 s (the lease) | 30.8 s | - |
| The VIP on B, from the cut | 64.6 s (operator at 61.6 s) | 36.7 s | - | - |
| The first write, from the VIP on B | 11.9 s | 12.9 s | 0.83 s, 1.47 s | 1.1 to 1.9 s |
| Acknowledged ids lost | 0 of 37, 0 of 30 | 0 of 20 | 0 of 37 | none of 15 |

## 6. Case (e), the old primary returns after the heal

| | Run 1, base (A = 9054) | Run 2, base (A = 9062) | netem (A = 9054) |
| --- | --- | --- | --- |
| Heal | 2525.55 | 3003.84 | 4300.59 |
| A takes the newer claim | 2529.10 (epoch 10) | 3005.76 (epoch 11) | 4309.52 (epoch 12) |
| A's server unit starts, as a primary | 2545.10 | 3006.21 | 4316.20 |
| Stopped by the fence restart | 2547.97 | 3010.02 | 4319.09 |
| Fenced, dumped, recorded | 2551.56 (26.0 s) | 3014.54 (10.7 s) | 4325.85 (25.3 s) |
| Divergence record | timeline 3 against 4 | 4 against 5 | 5 against 6 |
| Acknowledged writes in the window | 0 | 0 | 0 |

In all runs A recorded the newer claim before its server started as a
primary. The server was writable for 2.9 to 3.8 s while the other node
held the VIP. The writer did not write, because A did not carry the
VIP. This is the window of keel#156, after a heal (comment on #156).

### (d), the confirmed reseed of the old primary

| | Run 1, base | Run 2, base | netem |
| --- | --- | --- | --- |
| `--destroy-local-database` apply | 7.0 s | 12.3 s | 103.9 s |
| Streaming after the apply | 0.06 s | 0.15 s | 0.09 s |
| `FIRST 1 (keel)` back on the primary | 22.6 s later | 23.4 s later | 4.6 s later |

2026-10-15 00:10 (no etcd): 10.1 s. 2026-10-14 under netem: 83.9 s.
CI: 98 to 129 s at 250 ms.

## 7. A cut of 1 site at a time

The primary was 9054 (BR1). Each cut lasted 60 to 72 s.

| Cut | Network | etcd leader at the cut | VIP on 9054 | Writes on 9054 |
| --- | --- | --- | --- | --- |
| BR3, witness | base | witness | off 2.3 s, 6.9 s after the cut | 171 acknowledged in the cut; mean 0.12 s, max 0.32 s |
| BR3, witness | netem | witness | off 2.3 s, 7.0 s after the cut | 111 acknowledged in the cut; mean 0.38 s, max 1.03 s |
| BR2, standby | base | 9062 | kept | wait for the standby (0054); 2 killed; the next ack 7.8 s after the heal |
| BR2, standby, run 1 | netem | 9062 | off from 7.6 s after the cut; back after the heal; server stopped | none; pair down 180 s |
| BR2, standby, run 2 | netem | 9062 | off 3.9 s, 7.0 s after the cut | - (no writer) |
| BR1, primary | base and netem | - | sections 5 and 6 | sections 5 and 6 |

With 2 of 3 sites up, the pair keeps working in these cases: a cut of
the witness, and a cut of the standby at base. A cut of the standby
stops the writes until the heal, by the design of 0054 (synchronous
commit with no timeout). This is not a loss of quorum.

The cut site held the etcd leader in 5 cuts. In 3 of them the VIP
holder lost the VIP for 2.3 to 3.9 s, and in 1 of them for the whole
cut (keel#167). At base, the new leader came 7.4 s after the cut.

### BR2 standby cut under netem, run 1 (keel#167, #168)

From 1792063802.26 to 1792063913.27 (111 s), 9054 and the witness
sent pre-votes and elected no leader:

```
9054:    [logterm: 6, index: 128, vote: 17ecc5d1c52beda2] rejected MsgPreVote from 4d056d928326e022 [logterm: 6, index: 126]
witness: (no message from 9054 until 1792063915.83, then a burst:)
         ignored a MsgPreVoteResp message with lower term from 97c4d26052cf0035 [term: 6]
```

The watch of 9054 stopped its server at 3852.35 ("not proven, the VIP
is not on wg0"). After the heal the VIP came back to 9054 (epoch 11,
same lease), but the server stayed stopped (keel#168).

**Restore 3** (product path): `keel database follow` on 9054 at
4029.50. The server started at 4032.37, and the standby streamed
again at 4039.00.

## 8. Restores

| # | What | How | Why |
| --- | --- | --- | --- |
| 1 | reseed 9062 | `keel spec apply --system-only --destroy-local-database` | the planned switchover diverged (keel#163) |
| 2 | start `keel-database-follow.path` | `systemctl reset-failed` and `start`, by hand | start limit hit (keel#164); it failed again |
| 3 | start the server on 9054 | `keel database follow` | the server stayed stopped (keel#168) |
| - | reseeds after each (e) | `keel spec apply --system-only --destroy-local-database` | case (d), the product path |

No keel file, unit file or configuration was edited by hand on a node.

## 9. State at the end

| | 9062 (BR2) | 9054 (BR1) | 9071 (BR3) |
| --- | --- | --- | --- |
| keel | 0.23.21 | 0.23.21 | 0.23.21 |
| etcd | voter, healthy, leader | voter, healthy | voter, healthy |
| VIP | primary, epoch 12, etcd lease | replica, `fenced` (keel#166) | not in the pair |
| Server | primary, `FIRST 1 (keel)`, standby `keel` sync | standby, streams over TLS, refuses writes | - |
| A write | `INSERT 0 1` in 0.23 s, seen on 9054 | `cannot execute INSERT in a read-only transaction` | - |
| `keel diff` | exit 0 | exit 0 | exit 0 |
| `keel-database-follow.path` | failed (keel#164) | failed (keel#164) | - |
| netem | removed | removed | removed |

`sch_netem` was unloaded on the 3 hosts. The test nft table is gone on
all CTs.

Left on the nodes:

- On BR3-THIN: CT 9071, `vmbr1`, the 2 files of section 1.
- On 9054 and 9062: `/root/instance.yaml.pre-advanced-20261015`,
  `/root/vipwatch.sh`, the database `pairtest`, and the dumps under
  `/var/backups/keel/postgresql/`.
- On 9071: `/root/instance.yaml.orig-20261015`.

Next: with this state, a failover needs the operator
(`keel database promote --old-primary-gone`), because of keel#165 and
#166. Fix keel#164 first. Then measure (c) again: keel#169 can be a
result of keel#164.
