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
