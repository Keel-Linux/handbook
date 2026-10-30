# keel 0.23.62: the new VIP holder tells each peer in its own thread (keel#235)

Date: 2026-10-29, 23:10 to 23:45 UTC.
Fix: keel#236 (merge `7e79af3`), keel 0.23.62.
Publication: apt#73 (merge `d2d1378`), `trixie-testing` only.
Baseline: `evidence/2026-10-29-mariadb-promotion.md` (handbook#147), the
same image, topology and rounds on keel 0.23.61.

## Result

PASS. A dead old holder does not delay the route on the other nodes.
After the claim, W learns the new holder in 0.6 s to 0.7 s, against
10.7 s and 11.7 s on 0.23.61. The first write through the VIP from W
comes 3.3 s to 3.4 s after the claim, against 13.0 s to 13.4 s. No
acknowledged write is lost.

| Round | Stopped holder | Claim on C | W learns | W routes to C | First write from W | Claim to first write |
| --- | --- | --- | --- | --- | --- | --- |
| baseline 4 (0.23.61) | B, etcd leader | +37.1 | +47.8 | | +50.1 | 13.0 s |
| A (0.23.62) | B, etcd leader | +38.2 | +38.9 | +39.2 | +41.6 | 3.4 s |
| baseline 5 (0.23.61) | B, etcd follower | +24.2 | +35.9 | +36.4 | +37.6 | 13.4 s |
| B (0.23.62) | B, etcd follower | +23.0 | +23.6 | +23.9 | +26.3 | 3.3 s |

Times are seconds after `pct stop` of the holder. The timeout of the
dead peer still comes 10 s after the claim (+48.2 in round A, +33.0 in
round B), but W already has the route.

## The defect and the fix

`Controller.announce` in `keel/mesh/vipetcd.py` sent the claim to the
peers one after the other. The dead old holder came first, so each other
peer waited for its 10 s timeout. A node outside the pair has no
`keel-vip-control` and learns the route only from this message.

In 0.23.62, `announce` starts one thread for each peer and waits for all
of them. Each exchange keeps its own timeout. The unit test
`test_a_dead_peer_does_not_delay_the_others` puts the dead peer first
and asserts that the live peer gets the claim within 2 s. It failed on
0.23.61 and passes on 0.23.62. CI of keel#236: 13 of 13 green.

## Package

```
build host: bin/build-package keel  -> keel_0.23.62_all.deb
            bin/publish             -> publish trixie-testing: keel 0.23.62 (0990487)
apt#73 CI: security 1m36s, tests 17m0s; merged d2d1378
workstation: bin/keel-publish-mirror --archive-only
  https://archive.keellinux.org trixie-testing verifies
InRelease sha256, build host = public:
  trixie-testing 9304cabb57e77d11ca9cfbd9f083e15ebeb1d912eea535f865d9d07abc2bef3c
  trixie         3af06c3016fc58bbefa848a26d72d16e03990c2dbda1052c99d235524d941e78 (not changed)
```

The stable-1 pool and `trixie` are not changed.

## Image

The baseline image: `debian-13-keel-mariadb_19.0-10_amd64.tar.zst` from
`/srv/keel-ci/testing/20261029T164132Z`, sha512 `deec7e2edc479fc6…`, the
same on the build host, BR1 and BR2. keel 0.23.61 at first boot, then
`apt-get install keel=0.23.62` from `trixie-testing` on each node. In
each node, `Controller.announce` has the per-peer thread.

## Topology

| CT | Host | Name | Overlay | Role |
| --- | --- | --- | --- | --- |
| 9310 | hw12-br1 | `k235-w` | `fd41:e1e4:281b::f908` | witness, etcd member, writer |
| 9311 | hw12-br1 | `k235-b` | `fd41:e1e4:281b::1` | pair, primary at installation |
| 9312 | nfs1-br2 | `k235-c` | `fd41:e1e4:281b::b481` | pair, replica at installation |

VIP `fd41:e1e4:281b::ffff:1`. `installation.mode: cloud_advanced`, etcd
of 3. CTs unprivileged, `nesting=1`, 8 GB, 2 GB memory, 2 cores, DHCP.
First boot headless with a preseed: `Inithooks run completed` on all
three, no failed units, `/etc/inithooks.conf` emptied by `98finalize`.

netem on the host side of the veth of C: `delay 250ms 25ms loss 1.5%`.
Overlay ping W to C: 231.8 / 256.0 / 275.5 ms (min / avg / max), 1 of 30
lost.

## The pair

Sequence: `keel mesh create` (B), `keel mesh invite` and `join` (W, then
C, token on standard input), `keel vip pair` on B and on C,
`keel spec apply --system-only` on B, `keel vip promote` on B,
`keel spec apply --system-only` on C.

```
[B] apply --system-only: 10 change(s), 0 failed
[B] this node holds fd41:e1e4:281b::ffff:1 at epoch 1
[B] vip ...ffff:1: fd41:e1e4:281b::b481: applied
[B] vip ...ffff:1: fd41:e1e4:281b::f908: applied
[C] Master_Host fd41:e1e4:281b::1, IO Yes, SQL Yes, SSL Yes; read_only 1
[W] routed to: <B>
```

## Rounds

A writer on W inserts one row each 0.1 s through the VIP, with a 3 s
connect timeout. An id counts as acknowledged only when the client
returned 0. A sampler on W reads `wg show wg0 allowed-ips` each 0.5 s
and records the peer that has the VIP.

### Round A: `pct stop` of B, holder and etcd leader

```
+0.0  stop B
+10.3 [C] etcd: became leader at term 3
+38.2 [C] vip ...ffff:1: claimed at epoch 2: the lease of epoch 1 is gone (expired at its due time ...)
+38.9 [W] vip ...ffff:1: epoch 2, held by <C> at fd41:e1e4:281b::b481
+39.2 [W] route to <C>
+41.6 [W] first write acknowledged
+48.2 [C] vip ...ffff:1: fd41:e1e4:281b::1 did not take the claim: [fd41:e1e4:281b::1]:51821 through wg0: timed out
```

64 acks, 13 errors, longest gap between acks 40.40 s. Acknowledged ids
missing: 0 of 64 on C, 0 on B after it started again. B said:

```
rejoined: no errant GTID, replicating from [fd41:e1e4:281b::b481]:3306 over TLS from 0-59708260-29
```

Then `keel vip promote` on B (epoch 3), so that B holds the VIP while C
is the etcd leader.

### Round B: `pct stop` of B, holder and etcd follower

```
+0.0  stop B
+23.0 [C] vip ...ffff:1: claimed at epoch 4: the lease of epoch 3 is gone (expired at its due time ...)
+23.6 [W] vip ...ffff:1: epoch 4, held by <C> at fd41:e1e4:281b::b481
+23.9 [W] route to <C>
+26.3 [W] first write acknowledged
+33.0 [C] vip ...ffff:1: fd41:e1e4:281b::1 did not take the claim: ... timed out
```

57 acks, 8 errors, longest gap between acks 24.45 s. Acknowledged ids
missing: 0 of 57 on C, 0 on B after it started again. B said:

```
rejoined: no errant GTID, replicating from [fd41:e1e4:281b::b481]:3306 over TLS from 0-59708260-250
```

## End state

| Check | B | C |
| --- | --- | --- |
| keel | 0.23.62 | 0.23.62 |
| Rows in `pairtest.t` | 362, sum of ids 1319703 | 362, sum of ids 1319703 |
| `gtid_binlog_state` | `0-59708260-250,0-2065378296-366` | the same |
| VIP | replica, fenced, epoch 4 | primary, epoch 4 |

## Not in this test

The time from the stop to the claim (23 s, and 38 s when the stopped
holder is the etcd leader) is the etcd lease TTL and a leader election.
That is the design of decision 0057 and not part of keel#235.

## Clean up

CTs 9310, 9311 (BR1) and 9312 (BR2) are destroyed. The template copies
are removed from BR1 and BR2. The netem qdisc went with CT 9312. The
test passwords were generated for this test only and are deleted.
