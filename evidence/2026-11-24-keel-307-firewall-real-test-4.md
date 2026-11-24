# Evidence: fourth real-node test of keel pull request 307, the firewall in every mode (decision 0097)

Date: 2026-11-24. Site: BR1, the BR1 test VM (nested Proxmox VE).
Status: draft. For decision 0097 (accepted), section D, and for `keel`
pull request 307.

## Question

The third test (`evidence/2026-11-23-keel-307-firewall-real-test-3.md`,
head `023be97`) failed item 5 (a repaired file came back in `report`)
and item 7 (a busy invite was spent). Three new commits say that they
correct them:

- `f28e4da`: keel records the state it last wrote in
  `/var/lib/keel/firewall/state`, apart from the file. `choose()` takes
  the state of the file, else that record (`keel/system/firewall.py:182`,
  `keel/system/fwstate.py`).
- `2b90c3f`: a busy admission answers 409, not 503, and the invite stays
  (`keel/mesh/admit.py:261`).
- `38679dd`: main merged, with keel 0.23.98.

This test is narrow. It runs the two failed items again, tries to break
the new record, and does a short regression. The method and the probes
are those of the third test. A failure is a result. No code was changed.

## Tested head and package

- Tested head `e1402eade4e9b267f8252430e079efe2f75410c4`, the same as
  the head of the pull request on Forgejo before the run (00:03 UTC) and
  after it (01:10 UTC). Version 0.23.99.
- `keel_0.23.99_all.deb`, sha256
  `b4a101a78e7bc282acfa9ff3f201b77ab91413fd088801419605ab185ff9c285`,
  built from `git archive e1402ea` with `dpkg-buildpackage -us -uc -b`,
  `SOURCE_DATE_EPOCH=1795477159`, debhelper 13.24.2. The package holds
  `refusal(409, sync.BUSY)` and `RECORD = "var/lib/keel/firewall/state"`.
  Installed with `dpkg -i` after `pct push` only. It went to no
  repository and no mirror.
- For item 2, the package of the third test (head `023be97`), sha256
  `cddab77e61263a27ba115722640358515c8bbb776336bbfef8a8a7b3aa053236`.
  Both packages have the version 0.23.99, thus for dpkg the move from
  one to the other is a reinstall of the same version.
- `git diff 023be97 e1402ea -- debian/` changes `debian/changelog`
  only. Thus the maintainer scripts are those of the third test.

## Machines

Each CT is unprivileged, `nesting=1`, on the bridge `vmbr1` of the VM,
DHCPv4 and DHCPv6 from the dnsmasq of the VM. Templates as in the third
test (lnmp 19.0-7, lnpp 19.0-10, core 19.0-13; `sqv` exit 0,
`sha512sum -c` passed, sha256 the same as in the third test). Each
image has keel 0.23.96.

| CT | Image | Mode | Use |
| --- | --- | --- | --- |
| 9400 | core | simple | probe node, keel 0.23.96 kept |
| 9401 | lnmp | simple | items 1, 4, 5 |
| 9402 | lnmp | simple | item 2: the move from the `023be97` package, the broken records, the spec against the record |
| 9403 | core | simple | item 2: a fresh node, first move; a planted record on a node in report |
| 9404 | lnmp | simple | item 2: a planted record on a fresh node; the file and the record lost |
| 9406 | core | simple | item 3, the joiner of the busy case |
| 9407, 9408, 9409 | core | simple | item 3, the first two tries of two joins at once |
| 9410, 9411 | core | simple | item 3, the loss cases (9410) and the clean try of two joins at once |
| 9420, 9421, 9422 | lnmp, lnmp, core witness | cloud_advanced | `keel-commission --pass cloud_advanced`: PASS, 117 checks |
| 9430, 9431 | lnmp, lnmp | cloud_simple | `keel-commission --pass cloud_simple`: PASS, 87 checks |

The runner is `.github` at `f75cfec` (main). Every node except 9400 was
first upgraded to the published keel 0.23.97 from the Keel apt channel
(`apt-get install keel=0.23.97`), then to the test package. 9402 went
through the `023be97` package between the two. The probes run from CT
9400 and from the VM, on IPv6 and IPv4.

## Summary

| Item | Result | Key facts |
| --- | --- | --- |
| 1. Empty and cut file, enforce, undeclared listener | **FAIL** in part | The apply after an empty file and after a cut file (no policy line): `enforce, as keel's file already says`, `udp *:9999 of ev-udp.service (python3): listens, not declared, closed by the firewall`, `policy drop`, TCP and UDP 9999 `timeout` from outside. Reboot with an empty file, then the apply: the same. Not met: the watch alone never writes the file again (it fails each run, and with the table also lost the node is open until an apply), and the reboot alone leaves the node degraded and open until an apply |
| 2. The record, try to break it | **FAIL** in part | The move from `023be97`: stays in `enforce`, the record comes at the first apply. `report` and `off` in the spec win; `off` removes the record. An empty, garbage or unknown record counts as none. But: the file and the record lost at once is **not told** (check exit 0, watch silent, node `running`), and the apply then opens a closed node to `report`. A planted `enforce` record on a fresh node skips rule B. The record is read and written through a symlink, and its owner is not checked |
| 3. Busy, two joins, loss | **PASS** | Busy in 7.8 s with the inviter's reason, exit 24; the invite stays, its listener runs, no `expired unused`; the same line joined in 7 s. Two joins at once with two invites: both joined (8.1 s, 11.7 s). Root side killed: the same on `023be97` and on the test package (`the root side is gone`, exit 24, 3.0 to 5.6 s) |
| 4. Regression | **PASS** | `enforce` with no `firewall:` key on 1 simple, 2 cloud_simple and 3 cloud_advanced nodes. Probes as in the third test. SSH banner from outside on 6 nodes, both families. Failover: the VIP on 9421 30 s after the shutdown started; return rejoined 66 s after the start. Mesh invite and join under `enforce`: 5 joins |
| 5. Upgrade from 0.23.97 | **PASS** | No rule loaded. The restart list is the list of the third test: the watch timer enabled, not started; 8 systemd reloads; the same keel units restarted on simple, cloud_simple and cloud_advanced nodes. Note: the gap against 0073 that the third test found is unchanged |

## Item 1: empty and cut file on a node in enforce with an undeclared listener (FAIL in part)

9401 after the upgrade (item 5). The first apply with no listener:
`enforce: each socket on an address that is not a loopback belongs to a
unit of the manifests (decision 0097, B)`, then `record
/var/lib/keel/firewall/state: enforce, the state a broken file cannot
lose (mode 0644): done` (log 12). Then `listenunit.sh on`: TCP and UDP
9999 on all addresses, as enabled units `ev-tcp` and `ev-udp`, so that
they run again after a reboot. `ss` showed both before each apply.

| Case | Plan and state | From outside (CT 9400 and VM, IPv6 and IPv4) |
| --- | --- | --- |
| 1a. Empty file | check: `... is empty or cut short (it loads no table): keel spec apply --system writes it again`, exit 14. Apply exit 0: `enforce, as keel's file already says; firewall.state: report goes back`, `udp *:9999 of ev-udp.service (python3): listens, not declared, closed by the firewall`, the same for TCP, `write ... (enforce)`, `load it ...: done`. File 661 bytes, `# state: enforce`, `policy drop`. Check: `table inet keel is the one ... says` | 9999 TCP and UDP `timeout` (8 of 8); 22, 80, 443, 12321 `open`; UDP 12321 `timeout` |
| 1b. Cut file (the first 330 of 661 bytes, no policy line) | the same check line; the same plan lines; `enforce`, `policy drop` | the same |
| 1c. Empty file, no apply, the watch timer only | 27 s later: `firewall-watch[...]: Error: ... is empty or cut short ...; table inet keel holds a08b6b17d635a90b`, `keel-firewall-watch.service: Failed`, again 31 s later; node `degraded`. The loaded table stays `policy drop`. The file stays empty | (table loaded) |
| 1c2. And then the table deleted | 11 s later: the same error, `table inet keel is not loaded`; the unit fails each run; the table does not come back | 9999 TCP `open`, UDP `reply`: the node is open |
| 1c3. The apply after 1c2 | the same lines as 1a; `enforce`, `policy drop` | 9999 `timeout` again |
| 1d. Empty file, then `pct reboot` | `keel-firewall: ... is empty or cut short; keel spec apply --system writes it again`, `keel-firewall.service: Failed with result 'exit-code'`, node `degraded`, tables: `inet filter` only. The listener units run | 9999 TCP `open`, UDP `reply`, before the apply |
| 1d. The apply after the reboot | the same lines as 1a; `enforce`; check `table inet keel is the one ... says` | 9999 `timeout`; 22, 80, 443, 12321 `open` |

The record kept `enforce` in every case. The fix of the third test's
item 5 works for the apply, before and after a reboot. The reboot
alone does not bring the file back: the node is degraded and open until
a person runs the apply, as in the third test.

The watch leg: the watch timer never writes the file again. It loads a
table only from a sound file (`firewall/firewall-watch`,
`keel/system/fwcheck.py`). With an empty file it tells and fails each
30 s; with the table also lost the node is fully open until a person
runs the apply. This is the behaviour of the third test, item 6. It
does not meet "the file comes back in enforce" for the watch path.

Note: the plan says `enforce, as keel's file already says` also when
the file is empty or absent and the state comes from the record.

## Item 2: the state record, try to break it (FAIL in part)

Each case (logs 20 to 25): the node in `enforce` first (unless said),
the listeners on TCP and UDP 9999 running, the break, then `keel spec
apply --system`. `fw.sh` shows the file's state line, the record
(content, owner, mode, type), the loaded policy and `keel diff`.

### The move from the `023be97` package (9402, log 20)

| Step | Observed |
| --- | --- |
| 0.23.97, then `dpkg -i` of the `023be97` package, apply (no listener) | `enforce: ... (decision 0097, B)`; file `# state: enforce`; record **absent** (that package has no record) |
| `dpkg -i` of the test package | record absent; file and table unchanged |
| The first apply on the test package, listener up | `enforce, as keel's file already says`, `listens, not declared, closed by the firewall` (both sockets), `unchanged (...)`, `record /var/lib/keel/firewall/state: enforce ...: done`, `1 change(s)`. `policy drop` |

The node stays in `enforce` and gets the record at its first apply.

The window before that first apply (log 21): the record removed (as
right after the `dpkg -i`), the file emptied, listener up, apply:
`report: enforce waits, because these sockets belong to no unit of the
manifests: udp *:9999 of ev-udp.service (python3); tcp *:9999 ...`,
`write ... (report)`, `record ...: report`. The loaded table went from
`policy drop` to `policy accept`. Thus on a node upgraded from a
package with no record, the protection starts only after one apply.

### Broken records (9402, log 22)

| Case | State chosen | Loaded after | Record after |
| --- | --- | --- | --- |
| a. Record empty, file emptied | `report: enforce waits ...` (rule B) | `policy accept` (was `drop`) | `report`, root 0644 |
| b. Record 40 random bytes, file emptied | the same | `policy accept` | `report`, root 0644 |
| e. Record `ENFORCE` (an unknown word), file emptied | the same | `policy accept` | `report`, root 0644 |
| c1. Record `enforce`, owner `nobody:nogroup`, mode 0666, file intact | `enforce, as keel's file already says`, `0 change(s)` | `policy drop` | unchanged: `nobody:nogroup`, 0666 |
| c2. The same record, file emptied | `enforce` (the record is used) | `policy drop` | unchanged: `nobody:nogroup`, 0666 |
| c3. Record `report`, `nobody:nogroup`, 0666, node in enforce, file intact | `enforce` (the file wins), `record ...: enforce ...: done` | `policy drop` | `enforce`, mode 0644, owner still `nobody:nogroup` |
| d1. Record a symlink to `/root/ev307r4/target` (`enforce`, mode 0600), file emptied | `enforce` (read through the link) | `policy drop` | the link stays |
| d2. The link kept, its target set to `report`, node in enforce | `enforce`, `record ...: enforce ...: done` | `policy drop` | the link stays; keel wrote `enforce` **into the target** and set the target to mode 0644 |

An empty, garbage or unknown record counts as no record: rule B decides
(`recorded_state()` accepts `enforce` and `report` only). keel reads
the record with no check of owner, mode or type, and writes it with
`open(O_WRONLY|O_CREAT|O_TRUNC)` and `chmod`, which follow a symlink
(`keel/system/effects.py:289`). It writes the record only when the word
differs, so a wrong owner or mode stays. Only root can write in
`/var/lib/keel/firewall/`, thus these cases need root. A record that
says `report` acts as no record: it never forces `report`.

### The spec against the record (9402, log 23)

| Case | Observed |
| --- | --- |
| f1. Record `enforce`, file emptied, spec `firewall: {state: report}` | `write ... (report)`, `record ...: report`; `policy accept`. The spec wins |
| f2. Record `enforce`, file intact, spec `state: report` | the same |
| f3. Record `enforce`, file intact, spec `state: off` | `off in the spec: no inbound rule of keel's protects this node`, `remove /etc/keel/firewall/keel-manifest.nft ...: done`, `remove /var/lib/keel/firewall/state: the firewall is off in the spec: done`, `remove keel's table ...: done`. File, record and table gone |

### Fresh nodes and a planted record (9403, 9404, log 24)

| Case | Observed |
| --- | --- |
| g1. 9403, fresh (no file, no record), listener up: the first automatic move | `report: enforce waits, because these sockets belong to no unit of the manifests: ...`, `write ... (report)`, `record ...: report`; `policy accept`. As 0097 says |
| g2. 9403 in report (file intact), a planted record `enforce`, listener up | `report: enforce waits ...`; `record ...: report`. The file wins |
| g3. 9404, fresh and never in enforce (no file), a planted record `enforce`, listener up | `enforce, as keel's file already says`, `udp *:9999 ...: listens, not declared, closed by the firewall` (both), `write ... (enforce)`; `policy drop` |

g3 is not what 0097 says. 0097, section 5, says that the first move
from no file is by rule B: `report` while an unknown process listens.
With a planted record, keel goes to `enforce` at once and closes the
listeners, and the plan names a file that does not exist. 0097 does not
name the record. The closed direction is the safe one. The record is
not a file of the package, and the `postrm` of the package (made by
debhelper) does not remove it, thus a record stays on disk after `apt
remove` and `apt purge` (read from the package, not tested). A node
that installs keel again with such a record would act as g3.

### The file and the record lost at once (9404, log 25)

The node in `enforce` (`policy drop`), listener up; both files removed.

| Step | Observed |
| --- | --- |
| `keel firewall check` | `/etc/keel/firewall/keel-manifest.nft: no ruleset of keel's, nothing to compare`, exit 0 |
| The watch, 70 s | no journal line (`firewall-watch` exits 0 when the file is absent) |
| `systemctl is-system-running` | `running` |
| `keel diff` | `derived.firewall: drift (declared ..., report, observed nothing)`, `derived.firewall.loaded: drift`, exit 14 |
| From outside, before the apply | 9999 `timeout` (the old table is still loaded) |
| The apply | `report: enforce waits, because these sockets belong to no unit of the manifests: ...`, `write ... (report)`, `record ...: report`. `policy drop` became `policy accept` |
| From outside, after the apply | 9999 TCP `open`, UDP `reply` |
| Again in enforce, both removed, then `pct reboot` | `keel-firewall.service`: `start condition unmet`, `inactive (dead)`; no failed unit; node `running`; tables `inet filter` only; check exit 0 as above |
| From outside, after the reboot | 9999 TCP `open`, UDP `reply` |

The node is not told plainly. The check passes, the watch is silent,
the node is `running`, and after a reboot it is fully open with no
message. Only `keel diff` shows a drift. The apply then writes `report`
and opens a node that was closed, and its plan does not say that the
loaded table was `policy drop`.

## Item 3: busy, two joins at once, a loss of the root side (PASS)

### Busy (log 70)

`holdlock.py 90` holds the lock of a person's apply on 9420 (the
inviter; `sync.BUSY_WAIT` is 5 s). `keel mesh invite` on 9420, then
`keel mesh join -` on 9406, the line through standard input.

| Step | Observed |
| --- | --- |
| Join while the lock is held, 00:53:34.4 | `the inviter refused the join: busy: a keel spec apply or another keel mesh change holds this node's sync lock; send it again in a minute`, `join exit 24 after 7.8 s` |
| The inviter | 00:53:42.09 `invite c8e5...: busy: ...; the invite stays`. After the answer, 10 s later and after the lock was free: `keel-mesh-invite@c8e5...` and `keel-mesh-listen@c8e5...` `active running`; the `mesh_invites` set holds `51820`; `expired unused` lines in 2 min: 0 |
| The joiner after the busy answer | no wg0 |
| The same line again, 00:55:08, the lock free | `joined the mesh: this node is ...::21b4/64 on wg0`, `the mesh has 4 nodes`, `join exit 0 after 7 s`. The invite units ended; 9406 `policy drop`, file and record `enforce` |

### Two joins at once with two invites (log 71)

A second invite on the same port is refused: `Error: invite ... is
pending on TCP port 51820 until ...: give this one another with --port,
or wait`. Thus the second invite needs `--port`.

| Try | Observed |
| --- | --- |
| 1 | The second invite was refused as above; 9407 joined with the first in 7.2 s. Void for the case |
| 2 | Void: spoiled by this test (see the side finding below). 9409 joined through the invite on 51830 in 6.5 s |
| 3, clean: invites on 51860 and 51861, joins from 9410 and 9411 started at 01:09:28.1 | 9410 `joined the mesh`, exit 0 after 8.1 s; 9411 `joined the mesh`, exit 0 after 11.7 s. The inviter: `join from` at 01:09:30.98 and 01:09:34.06, each `peer applied` and `the revert is cancelled`; no busy line. No invite unit left; 7 peers on 9420; both joiners `policy drop`, record `enforce` |

The second admission waited for the first one's lock for less than
5 s, thus it did not answer busy.

Side finding (pre-existing, not from this change). In try 2, an invite
that this test had stopped by hand (`systemctl stop
keel-mesh-invite@3c2f...`) left its unprivileged listener running, on
TCP 51820. The next invite on 51820 then failed: its listener ended
with a traceback, `OSError: [Errno 98] Address already in use`, and the
invite said `expired unused` at once. The join with that line ran to
its 600 s timeout (exit 124) and left a half-made overlay on 9408 (wg0
up, the address in its spec, a revert timer of 15 min). The plan of
an admission also lists the invite's own listener as `listens, not
declared, closed by the firewall`, while the invite set opens its port.

### A real loss of the root side (log 72)

`joinloss.sh`: an invite on a cloud_simple node; `kill -9` of the
MainPID of `keel-mesh-invite@ID`, before the joiner 9410 sends, or 1 s
after it starts (the join request arrives first). The same steps on the
`023be97` package (`refusal(503, sync.BUSY)`) and on the test package
(`refusal(409, sync.BUSY)`).

| Case | Package | Joiner | The inviter after |
| --- | --- | --- | --- |
| L1, kill before | test | `the inviter refused the join: the root side is gone: [Errno 32] Broken pipe`, exit 24 after 5.6 s | listener stopped 5 s later; the invite stays pending to its hour; a new invite on the port is refused; the set element stays |
| L2, kill before | `023be97` | the same text, exit 24 after 5.6 s | the same |
| L3, kill during | `023be97` | `the inviter refused the join: the root side is gone`, exit 24 after 3.1 s | the same; the inviter's spec keeps a peer entry for the joiner's address, wg0 does not have it |
| L4, kill during (inviter 9431) | test | the same text, exit 24 after 3.0 s | the same as L3 |

No regression: a lost root side gives the same answer, the same exit
code and the same inviter state on both packages. The 503 path of
`listener.py` still ends the listener. The pending invite, the open set
element and the half-added peer after a kill are as before this change.

## Item 4: regression (PASS)

`grep -c "^firewall:" /etc/keel/instance.yaml` gave 0 on each node.
`keel spec apply --system`, exit 0 on each node (logs 12, 23, 42):

| Node | Plan text |
| --- | --- |
| 9401 lnmp simple | `enforce: each socket ... (decision 0097, B)`, `public tcp 22, 80, 443, 12321`, `record ...: enforce` |
| 9430, 9431 cloud_simple | the same, `public tcp 22, 80, 443, 12321 and udp 51820, mesh tcp 3306, 22000 and udp 22000 on wg0` |
| 9420, 9421 cloud_advanced | the same, `... mesh tcp 2379, 2380, 3306, 22000 and udp 22000 on wg0` |
| 9422 witness | `public tcp 22, 12321 and udp 51820, mesh tcp 2379, 2380 on wg0` |

Probes with the listeners on TCP and UDP 9999 (logs 13, 30), 4 rows per
node and port (2 sources, 2 families), on the eth0 addresses:

| Port | 9401, 9420, 9421, 9430, 9431 | 9422 witness |
| --- | --- | --- |
| TCP and UDP 9999 | timeout | timeout |
| TCP 22, 12321 | open | open |
| TCP 80, 443 | open | timeout |
| UDP 12321 | timeout | timeout |
| TCP 3306, 2379, 2380, 22000, UDP 22000 (mesh, on eth0) | timeout (not probed on 9401) | timeout |

SSH (log 31): from CT 9400, `SSH-2.0-OpenSSH_10.0p2 Debian-7+deb13u4`
from 9401, 9420, 9421, 9422, 9430 and 9431, on IPv6 and IPv4.

| Check in enforce (cloud_advanced) | Observed |
| --- | --- |
| Replication | a row written on 9420 arrived on 9421; etcd 3 voters; 3 Syncthing sessions |
| Failover | `pct shutdown 9420` at 00:51:06 (returned 00:51:14); VIP on 9421 at 00:51:36; read_only 0; a row written; `policy drop` |
| Return | `pct start 9420` at 00:51:49; `keel-firewall.service` before `network-pre.target` before `wg-quick@wg0`; `rejoined: no errant GTID, replicating from [...]:3306 over TLS` at 00:52:55; both rows; `Seconds_Behind_Master: 0`; file and record `enforce` |

Mesh invite and join under enforce: 9406, 9407, 9409, 9410 and 9411
joined 9420 in `enforce` (item 3); each stayed in `enforce`.

## Item 5: upgrade from 0.23.97 (PASS)

`upgrade97.sh` (logs 10, 21, 41): on 9401, the pair 9430 and 9431, and
the trio 9420 to 9422.

| Change | simple (9401) | cloud_simple (2) | cloud_advanced (3) |
| --- | --- | --- | --- |
| Rule loaded | none (`inet filter` only) | none (`inet filter` and CrowdSec's tables, as before) | the same |
| Enabled | `timers.target.wants/keel-firewall-watch.timer` (new link), not started | the same | the same |
| `nftables.service` | drop-in `keel-firewall.conf` live, not run | the same | the same |
| systemd reloads | 8 | 8 | 8 |
| Restarted (stop and start) | `keel-mesh-members.path`, `keel-mesh-sync.timer`, `keel-mesh-etcd.timer`, `keel-database-follow.path`, `keel-database-watch.timer`, `keel-database-dump.timer`, `keel-database-position.timer` | the same, and `keel-mesh-members.service`, `keel-mesh-members-listen.service`; on 9431 `keel-database-position.service` started | the same, and on 9420 and 9421 `keel-database-position.service`, `keel-vip.service`, `keel-vip-control.service`, `keel-vip-check.timer` |
| Runs triggered | | `keel-database-follow.service`, `keel-database-watch.service` | the same, `keel-mesh-etcd.service`, `keel-vip-check.service` (9421) |
| MariaDB, etcd, Syncthing, wg-quick, nginx | not restarted | not restarted | not restarted |

The list is the list of the third test. The record is not written by
the upgrade; it comes at the first apply. The gap against 0073 that the
third test found (the restarts of keel's other units) is unchanged.

## Against the third test

| Third test (head `023be97`) | This test (head `e1402ea`) |
| --- | --- |
| An empty or cut file came back in `report` on a node in enforce with an undeclared listener | comes back in `enforce`, before and after a reboot; the listener is closed from outside |
| A busy invite was spent (`expired unused` 1 s later), the same line timed out | the invite stays, its listener runs, the same line joins in 7 s |
| (no record) | new: the file and the record lost at once are silent, and the apply then opens the node; a planted record skips rule B; the record follows a symlink |

## What was not tested

- The ISO, two sites with netem, image builds, the other images.
- A loss of the record during a reboot of a node with an empty file
  (each was tested apart).
- The etcd start message under the lock (not reachable on a formed
  cluster, as in the third test).
- The pair under writes during the upgrade.

## Logs

On the maintainer's workstation in
`repos/evidence-0097-2026-11-23/pr307-run4/`. The runner records
(`runner-adv/`, `runner-cs/`) hold console transcripts and are not
copied here.

| Log | Content |
| --- | --- |
| `00-vm-baseline`, `99-vm-after`, `99-vm-diff`, `99-cleanup` | the VM before and after |
| `01-images`, `02-create-simple`, `03-firstboot-simple`, `04-push`, `50-joiners-setup` | templates, CTs |
| `20-adv-runner`, `40-cs-runner` | commissioning |
| `10-simple-upgrade`, `21-adv-upgrade`, `41-cs-upgrade` | item 5 |
| `12-simple-apply`, `13-item1-empty-cut`, `14-item1-watch`, `15-item1-reboot` | item 1 |
| `20-item2-upgrade-023be97`, `21-item2-window`, `22-item2-record-breaks`, `23-item2-spec-wins`, `24-item2-fresh`, `25-item2-both-lost` | item 2 |
| `70-item3-busy`, `71-item3-two`, `72-item3-loss` | item 3 |
| `23-adv-apply`, `42-cs-apply`, `30-item4-probe`, `31-item4-ssh`, `32-adv-mesh`, `33-adv-failover` | item 4 |
| `98-secret-scan` | secret scan |

Secret handling: node secrets were made inside each stopped CT and never
printed. Join lines stayed in shell variables and went to the joiner by
standard input, never shown. Every `.log`, `.out`, `.txt`, `.tsv` and
`.md` file under `pr307-run4/`, the runner console transcripts
included, was scrubbed of WireGuard public keys and join lines
(`scrub.sed`), and each control or non-ASCII byte in them (the garbage
record of item 2, the escape codes of the consoles) was replaced by
`?`. The scan of log 98 over 145 files found no key, no join or accept
line, no private key, no password and no token. The 4 `keel2:` hits
are sed patterns in the scripts. The 5 `password` hits are screen
control codes after the `password:` prompt in the console transcripts.
The same 8 patterns over this file: 2 lines with the word `keel2:`, in this
paragraph; no key, no join line, no password, no token.

## Cleanup

CTs 9400 to 9404, 9406 to 9411, 9420 to 9422, 9430 and 9431 were
destroyed with `pct destroy --purge`. The templates `ev307r4-*` and
`/root/ev307r4` were removed. The templates that were on the VM before
were not touched. The Proxmox firewall is `disabled/running` and
`/etc/pve/firewall` is empty, as before. The diff of the VM state before
and after (the commands of log 00), without counters, time stamps and
veth peer indexes, is empty: `diff_exit=0 lines=0` (log 99).
