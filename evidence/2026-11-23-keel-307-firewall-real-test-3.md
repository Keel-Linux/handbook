# Evidence: third real-node test of keel pull request 307, the firewall in every mode (decision 0097)

Date: 2026-11-23. Site: BR1, the BR1 test VM (nested Proxmox VE).
Status: draft. For decision 0097 (accepted), section D, and for `keel`
pull request 307.

## Question

The second test (`evidence/2026-11-23-keel-307-firewall-real-test-2.md`,
head `2120276`) failed the SSH, table loss and cut-file items. The third
review (at `fd16a68`) found F1 to F6. Head `023be97` says that it
corrects them. Does it work on published nodes, with the published specs
unchanged? The method and the probes are those of the second test. A
failure is a result. No code was changed.

## Tested head and package

- Tested head `023be97bfaa80db27a6b6c9041af76e7be5cf7b8`, the same as
  the head of the pull request on Forgejo before and after the run.
  Version 0.23.99.
- `keel_0.23.99_all.deb`, sha256
  `cddab77e61263a27ba115722640358515c8bbb776336bbfef8a8a7b3aa053236`,
  built from `git archive 023be97` with `dpkg-buildpackage -us -uc -b`,
  `SOURCE_DATE_EPOCH=1795470786`, debhelper 13.24.2. Installed with
  `dpkg -i` after `pct push` only. It went to no repository and no
  mirror.
- The maintainer scripts of the package: `postinst` enables
  `keel-firewall.service` and `keel-firewall-watch.timer` and starts
  neither; `preinst` has no line for either; `prerm` stops the watch
  timer on `remove` only.
- The CI check `tests / mariadb` is red at this head. This run does not
  depend on it. The promote measurement below is for it.

## Machines

Each CT is unprivileged, `nesting=1`, on the bridge `vmbr1` of the VM,
DHCPv4 and DHCPv6 from the dnsmasq of the VM. Templates as in the second
test (lnmp 19.0-7, lnpp 19.0-10, core 19.0-13; `sqv` exit 0,
`sha512sum -c` passed, sha256 the same). Each image has keel 0.23.96 and
`systemd-logind` active.

| CT | Image | Mode | Use |
| --- | --- | --- | --- |
| 9400 | core | simple | probe node, keel 0.23.96 kept |
| 9401 | lnmp | simple | items 1, 4, 5, 6, 10 |
| 9402 | lnpp | simple | items 1, 3, 10 |
| 9403 | core | simple | items 1, 10; then `apt remove keel` (item 3) |
| 9405 | lnmp | simple | items 2, 8, 10 |
| 9406 | core, **1 vCPU** | simple | items 9, 10; joiner of item 7 |
| 9407 | core | simple | the joiner of the mesh invite and join |
| 9420, 9421, 9422 | lnmp, lnmp, core witness | cloud_advanced | `keel-commission --pass cloud_advanced`: PASS |
| 9430, 9431 | lnmp, lnmp | cloud_simple | `keel-commission --pass cloud_simple`: PASS |

Every node except 9400 and 9407 was first upgraded to the published
keel 0.23.97 from the Keel apt channel (`apt-get install keel=0.23.97`),
then to the test package (item 10). The probes run from CT 9400 and
from the VM, on IPv6 and IPv4.

## Summary

| Item | Result | Key facts |
| --- | --- | --- |
| 1. Regression | PASS | `enforce` on all 10 nodes (lnmp, lnpp, core; simple, cloud_simple, cloud_advanced) with no `firewall:` key. Probes: 36 of 36 rows as expected. Neighbour path closed, control open. Replication, failover (VIP moved in 26 s) and return (rejoined 65 s after the start) in enforce |
| 2. SSH | PASS | `SSHD_OPTS="-p 2200"`: 2200 open. sshd on 2222 with the file at 2333, no restart: 2222 open. F1: a www-data program named `sshd` on 4444 and a www-data process inside `ssh.service` on 4445: both `timeout` |
| 3. Timer | PASS | Active after `dpkg -i` over 0.23.99; a deleted table came back in 24 s. Masked timer: apply exit 0 and says so. `apt remove keel`: timer stopped, node `running` |
| 4. Check and repair | PASS | A swapped `tcp dport 1-65535 accept`: seen by `keel firewall check` at once, repaired in 15.8 s. Delete 25.0 s, flush 25.7 s, policy accept 18.8 s. An in-place edit with the same size and mtime: seen in 23 s |
| 5. Empty and cut file | **FAIL** in part | The next apply writes them again; apply and check agree. Reboot with an empty file: the unit fails, the node is degraded and fully open. But on a node in enforce with an undeclared listener, the file came back in **report** (`policy accept`) |
| 6. F3 | PASS | Broken file, then the table deleted: said 6 s later; the watch unit stayed failed for every run (more than 7 min). About 340 journal lines per hour while it lasts, 1 of them keel's |
| 7. F4 | **FAIL** | The invite admission answered busy in 8 s, and a VIP promote that needs B ended in 6 s. But the busy invite was spent: `expired unused` 1 s after the busy line, and the join again timed out (600 s). The etcd start message could not be made on a formed cluster |
| 8. Hand listener | PASS | `udp *:9999 of ev-udp.service (python3): listens, not declared, closed by the firewall` |
| 9. Cost, 1 vCPU | PASS | 35 ms CPU per run, about 4.2 s per hour (0.12 % of the core), 1 MiB peak, 0 journal lines in 20 min |
| 10. Upgrade from 0.23.97 | **not met** against 0073 | No rule loaded, nothing of the firewall started. But the upgrade enables the watch timer, reloads systemd 8 times and restarts keel's own path, timer, mesh and VIP units (list below), as before this pull request |
| Mesh invite and join under enforce | PASS | Join in 7 s through the invite port; the invite set empty after; the joiner stays in `enforce` |
| Promote write gap (pair) | measured | Longest gap between two writes at a planned promote: 5.219, 4.035, 3.308, 4.376, 3.813, 4.645 s |

## Item 1: regression (PASS)

`grep -c "^firewall:" /etc/keel/instance.yaml` gave 0 on each node.
`keel spec apply --system`, exit 0 on each node:

| Node | Plan text |
| --- | --- |
| 9401, 9405 lnmp; 9402 lnpp | `derived.firewall: enforce: each socket on an address that is not a loopback belongs to a unit of the manifests (decision 0097, B)`, `write ... (enforce): public tcp 22, 80, 443, 12321`, `start keel-firewall-watch.timer ...: done` |
| 9403, 9406 core | the same, `public tcp 22, 12321` |
| 9430, 9431 cloud_simple | `public tcp 22, 80, 443, 12321 and udp 51820, mesh tcp 3306, 22000 and udp 22000 on wg0` |
| 9420, 9421 cloud_advanced | `public tcp 22, 80, 443, 12321 and udp 51820, mesh tcp 2379, 2380, 3306, 22000 and udp 22000 on wg0` |
| 9422 witness | `public tcp 22, 12321 and udp 51820, mesh tcp 2379, 2380 on wg0` |

Probes with the listeners on TCP and UDP 9999 (logs 20, 25, 25b), 4 rows
per node (2 sources, 2 families):

| Port | lnmp, lnpp nodes | core nodes, witness |
| --- | --- | --- |
| TCP and UDP 9999, 9998 | timeout | timeout |
| TCP 22, 12321 | open | open |
| TCP 80, 443 | open | timeout |
| UDP 12321 | timeout | timeout |

The first rows of 9421 overlapped the control below (the table was
deleted on purpose at 22:55:34). 9421 was probed again: 4 of 4 rows as
above (log 25b).

Neighbour path (log 30): from CT 9400 through eth0, each mesh port
(3306, 2379, 2380, TCP and UDP 22000, 51821) on each wg0 address and
VIP of both pairs: `timeout`; TCP 22: `open`. Control on 9421 without
the table: 3306, 2379, 2380, 22000 `open` (log 31).

| Check in enforce (cloud_advanced) | Observed |
| --- | --- |
| Replication | a row written on 9420 arrived on 9421; etcd 3 voters; 3 Syncthing sessions on wg0 |
| Failover | `pct shutdown 9420` at 23:02:09; VIP on 9421 at 23:02:44; read_only 0; a row written |
| Return | `pct start 9420` at 23:02:55; `keel-firewall.service` before `network-pre.target` before `wg-quick@wg0`; `rejoined: no errant GTID, replicating from [...]:3306 over TLS` at 23:04:00; both rows |

## Item 2: SSH (PASS)

On 9405 in enforce, probes from CT 9400, both families (log 40).

| Case | Plan text | Observed |
| --- | --- | --- |
| `SSHD_OPTS="-p 2200"`, no `Port`, `ssh.socket` stopped | `SSH stays open: tcp 22, 2200`, `sshd listens now on tcp 2200, which its configuration (sshd -T) does not name: both stay open` | 2200 `open`, 9998 `timeout` |
| F1: a copy of python3 named `sshd`, run as www-data (uid 33), on TCP 4444; a www-data python3 moved into `ssh.service`'s cgroup, on TCP 4445 | `closes tcp *:4445 of ssh.service (python3)`, `tcp 0.0.0.0:4444 of no process ss could read (sshd): listens, not declared, closed by the firewall`; rule `tcp dport { 22, 80, 443, 2200, 12321 }` | 4444 `timeout`, 4445 `timeout`, 2200 `open` |
| sshd restarted on `Port 2222`, then the file changed to `Port 2333`, no restart | `SSH stays open: tcp 2222, 2333`, `sshd listens now on tcp 2222 ...: both stay open` | 2222 `open`, 2333 `refused` |
| Restored (socket mode, as the image) | | 22 `open` |

Notes: the www-data socket is named "of no process ss could read". With
the F1 processes running, `keel diff` said `enforce closes ... tcp
0.0.0.0:2200 of ssh.service (sshd)`, while the table opened 2200.

## Item 3: the timer (PASS)

On 9402 (log 50):

- `dpkg -i` of the same package over the running 0.23.99: the timer is
  `active enabled` after. `nft delete table inet keel`: the table came
  back after 24 s, `policy drop`.
- `systemctl mask keel-firewall-watch.timer`, then the apply (with an
  `allow` port to make a change): `apply exit 0`, `derived.firewall:
  keel-firewall-watch.timer is masked: left alone; a lost table comes
  back only by the drop-in of nftables.service, a reboot or the next
  apply`, `2 change(s), 0 failed`. The same with `state: report`.
  Unmasked, the next apply started it.

On 9403, a throwaway node (log 56): `apt-get remove -y keel` removed
keel and the packages that depend on it (`confconsole`, `keel-core`, the
overlays). After: the timer `inactive`, `systemctl is-system-running`:
`running`, no failed unit, also 70 s later. The drop-in directory of
`nftables.service` is gone; `table inet keel` stays loaded.

## Item 4: check and repair (PASS)

On 9401 in enforce, listener on TCP 9999, `fastprobe.py` from CT 9400
every 50 ms on IPv6 and IPv4 (logs 51, 52, 53). Times UTC.

| Change by hand | Seen | TCP 9999 open (IPv6 / IPv4) | Journal |
| --- | --- | --- | --- |
| `nft replace rule ... tcp dport 1-65535 accept` | `keel firewall check` at once: `Error: rule 8 of table inet keel is 'tcp dport 1-65535 accept', and the file says 'tcp dport { 22, 80, 443, 12321 } accept' (a rule edited by hand)`, exit 14 | 18.037 to 33.849: **15.8 s** / 15.8 s | `firewall-watch[...]: Warning: rule 8 ...: loaded again` |
| `nft delete table inet keel` | | **25.0 s** / 25.1 s | `table inet keel is not loaded; ... loaded again` |
| `nft flush ruleset` | | **25.7 s** / 25.6 s | the same line. `inet filter` does not come back |
| input policy to accept | | **18.8 s** / 18.9 s | `has policy accept, and the file says drop: loaded again` |
| the file edited in place, `12321` to `12322`, same size, mtime put back (`touch -r`) | 23 s later: `Error: the rules in the file are not the ones its digest names (..., a change by hand): keel spec apply --system writes it again; table inet keel holds ...`; the watch unit `failed`, node `degraded` | none: the loaded table stays correct | |

## Item 5: empty and cut file (FAIL in part)

On 9401 (log 55).

| Case | Observed |
| --- | --- |
| Empty file | check: `Error: ... is empty or cut short (it loads no table): keel spec apply --system writes it again`. The apply: exit 0, `write /etc/keel/firewall/keel-manifest.nft (report) ...: done`, file 696 bytes, check `table inet keel is the one ... says` |
| Cut file (half its bytes) | the same lines |
| The state after the rewrite | **report**: `policy accept`, `keel-report` counter. The node was in enforce before. The listeners on TCP and UDP 9999 of item 4 were still running, so rule B held report: `enforce would close udp *:9999 of ev-udp.service (python3)` |
| The listeners stopped, apply | `enforce: each socket ... (decision 0097, B)`, `policy drop` |
| Reboot with an empty file, node in enforce | `keel-firewall: /etc/keel/firewall/keel-manifest.nft is empty or cut short; keel spec apply --system writes it again`, `keel-firewall.service: Failed with result 'exit-code'`, node `degraded`, failed units `keel-firewall.service` and `keel-firewall-watch.service`. Tables: `inet filter` only. Open: TCP 22, 80 `open`; TCP and UDP 9998, TCP 3306 `refused` (no filter); UDP 12321 `reply` on IPv4 |
| Apply after the reboot (no undeclared listener) | `enforce`, written and loaded |

The messages of the apply and of the check agree. The failure: an empty
or cut file loses the record that the node was in enforce, so the
rewrite goes through rule B again and can land in report.

## Item 6: F3, a broken file and a lost table (PASS)

On 9401 (log 54). The file edited in place (item 4) stayed; then `nft
delete table inet keel` at 22:42:41.

- 22:42:47 (6 s): `firewall-watch[...]: Error: the rules in the file are
  not the ones its digest names (..., a change by hand): keel spec apply
  --system writes it again; table inet k[eel is not loaded]`.
- Every 30 s sample from 22:43:11 to 22:49:56: `unit failed exit-code,
  node degraded, table absent` (one sample at 22:47:11 caught the unit
  while starting).
- Journal in 5 min: 28 lines, 1 of them keel's (rate-limited), 27 from
  systemd (`Main process exited`, `Failed with result`, `Failed to
  start`, at each run). Estimate: about 340 lines per hour while the
  problem lasts.
- The apply wrote the file again: `recovered: table inet keel is the one
  keel's file says again`.

## Item 7: F4, the lock on B (FAIL)

`holdlock.py` holds the lock of a person's apply (`keel.commands.
apply_lock`, the same call, named `keel spec apply`) on B for 60 to 150 s
(log 70, 71). The first try was void (the script was not in the CT).

| Case | Observed |
| --- | --- |
| VIP claim that needs B: B (9420, the VIP holder) holds the lock; `keel database promote` on 9421 | `promote exit 0 after 6 s`; B: `the database is read only before the release`, `released by this node`. 9421 read_only 0, VIP 1 |
| `keel mesh etcd form` on the root CA holder while B (9421) holds the lock | exit 0 after 0 s: `etcd: every ready member is in the cluster`. No message to B on a formed cluster, so the busy path of the etcd start was **not reached** |
| Invite admission: B (9420) holds the lock, `keel mesh invite` on B, `keel mesh join` from 9406 | `the inviter refused the join: busy: a keel spec apply or another keel mesh change holds this node's sync lock; send it again in a minute`, `join exit 24 after 8 s`. B: `invite ...: busy ...; the invite stays` at 23:13:40, then at 23:13:41 `Stopped keel-mesh-listen@...`, `invite ...: expired unused`. `pending invites: 0` |
| The same join line again, the lock free | `no answer from the inviter's port ...: timed out`, then `keel mesh accept ...` and `confirming over the overlay…`; `join exit 124 after 601 s` |

Nothing stalled for 600 s, and busy came within about 5 s. But the
invite was spent: the plan line says "the invite stays", and the invite
service stopped 1 s later.

**Mesh invite and join under enforce (log 72).** A fresh invite on
9420, no lock: the set `mesh_invites` held `51820 timeout 1h`. 9407
(core, enforce) joined through standard input: `joined the mesh: this
node is ...::e282/64 on wg0`, `join exit 0 after 7 s`. After: 3 peers
on 9420, `mesh_invites` empty, 9407 `policy drop`, file `# state:
enforce`.

## Item 8: hand listener on a node in enforce (PASS)

On 9405 (log 41): `udp *:9999 of ev-udp.service (python3): listens, not
declared, closed by the firewall` and the same for TCP 9999; `policy
drop`.

## Item 9: cost of the watch on 1 vCPU (PASS)

9406, `pct set --cores 1`, `nproc` 1, node in enforce and all well, 20
min (log 90). `ExecStart=/usr/lib/keel/firewall-watch`.

| Measure | Value |
| --- | --- |
| Runs | 40 in 1200 s |
| CPU per run | mean 35 ms (28 to 34 ms in the first runs) |
| CPU per hour | about 4.2 s (0.12 % of the core) |
| Memory peak | 1 MiB |
| Run time | about 60 ms |
| Journal lines of the watch | 0 in 20 min |

The second test measured 549 ms per run on 2 vCPUs.

## Item 10: upgrade from 0.23.97 (not met against 0073)

`upgrade97.sh`: `apt-get install keel=0.23.97`, then `upgrade.sh`
(snapshot, `dpkg -i`, snapshot, links, systemd journal) on 5 simple
nodes, the pair and the trio (logs 10, 21, 41).

| Change | simple (5) | cloud_simple (2) | cloud_advanced (3) |
| --- | --- | --- | --- |
| Rule loaded | none (`inet filter` only) | none | none |
| Enabled | `timers.target.wants/keel-firewall-watch.timer` (new link), not started | the same | the same |
| `nftables.service` | drop-in `keel-firewall.conf` live, not run | the same | the same |
| systemd reloads | 8 | 8 | 8 |
| Restarted (stop and start) | `keel-mesh-members.path`, `keel-mesh-sync.timer`, `keel-mesh-etcd.timer`, `keel-database-follow.path`, `keel-database-watch.timer`, `keel-database-dump.timer`, `keel-database-position.timer` | the same, and `keel-mesh-members.service`, `keel-mesh-members-listen.service`; on the primary `keel-database-position.service` started | the same, and on 9420 and 9421 `keel-database-position.service`, `keel-vip.service`, `keel-vip-control.service`, `keel-vip-check.timer` |
| Runs triggered | | `keel-database-follow.service`, `keel-database-watch.service` | the same, `keel-mesh-etcd.service`, `keel-vip-check.service` |
| MariaDB, etcd, Syncthing, wg-quick, nginx | not restarted | not restarted | not restarted |

The restarts come from `dh_installsystemd` without
`--no-restart-after-upgrade` for keel's other units; they exist before
this pull request.

## Promote write gap on a real pair

The cloud_advanced pair 9420 and 9421 in enforce. A non-SUPER test user
`ev307w` (password made on the VM, never printed). `writer.py` on both
nodes inserts one row every 50 ms through the local socket; `read_only`
refuses it on the read-only node. `keel database promote` (planned) on
the target 5 s into each run (log 61). The gap is the longest time
between two successful writes on either node. Clients through the VIP
would add the routing time.

| Run | Promote to | Promote command | Longest gap |
| --- | --- | --- | --- |
| 1a | 9420 | 23:04:26.390 to 23:04:35.612 | 5.219 s |
| 1b | 9421 | 23:05:22.644 to 23:05:29.230 | 4.035 s |
| 2a | 9420 | 23:06:09.230 to 23:06:15.880 | 3.308 s |
| 2b | 9421 | 23:06:56.562 to 23:07:03.811 | 4.376 s |
| 3a | 9420 | 23:07:44.418 to 23:07:51.366 | 3.813 s |
| 3b | 9421 | 23:08:31.619 to 23:08:39.152 | 4.645 s |

On one bridge (no netem) the gap was 3.3 to 5.2 s. The old primary
turns read only before the release; the new one takes writes some
seconds later.

## Against the second test

| Second test (head `2120276`) | This test (head `023be97`) |
| --- | --- |
| SSH lock-outs: `SSHD_OPTS` and a port changed with no restart | both stay open; F1 cases stay closed |
| A swapped wider rule never seen | seen at once, repaired in 15.8 s |
| A reinstall of keel stopped the timer | the timer stays active |
| A masked timer: apply exit 16 | exit 0, said |
| An empty or cut file not written again; empty file loaded with success at boot | written again; the boot unit fails. New: the rewrite can land in report |
| Watch cost 549 ms per run | 35 ms per run on 1 vCPU |

## What was not tested

- The ISO, two sites with netem, image builds, the other 10 images.
- The etcd start message under the lock (not reachable on a formed
  cluster).
- The review's F2 (a change between two listings in the same
  milliseconds).
- `ssh -R` with `GatewayPorts`.
- The pair under writes during the upgrade.

## Logs

On the maintainer's workstation in
`repos/evidence-0097-2026-11-23/pr307-run3/`. The runner records
(`runner-adv/`, `runner-cs/`) hold console transcripts and are not
copied here.

| Log | Content |
| --- | --- |
| `00-vm-baseline`, `99-vm-after`, `99-vm-diff`, `99-cleanup` | the VM before and after |
| `01-images`, `02-create-simple`, `03-firstboot-simple`, `04-push` | templates, CTs |
| `10-simple-upgrade`, `21-adv-upgrade`, `41-cs-upgrade` | item 10 |
| `12-simple-apply`, `23-adv-apply`, `42-cs-apply`, `20-simple-enforce-probe`, `25-cloud-enforce-probe`, `25b-9421-reprobe`, `30-neighbour`, `31-neighbour-control`, `32-adv-mesh`, `33-adv-failover` | item 1 |
| `40-ssh` | item 2 |
| `50-timer`, `56-apt-remove` | item 3 |
| `51-check-repair`, `52-hand-loss`, `53-inplace-edit` | item 4 |
| `55-empty-cut` | item 5 |
| `54-f3` | item 6 |
| `70-f4`, `71-invite-join`, `72-join-fresh` | item 7, invite and join |
| `41-hand-listener` | item 8 |
| `90-timer-cost-1cpu` | item 9 |
| `60-promote`, `61-promote-gap` | promote write gap |
| `98-secret-scan` | secret scan |

Secret handling: node secrets were made inside each stopped CT and never
printed. Join lines stayed in shell variables and went to the joiner by
standard input or argument, never shown. One accept line printed by the
failed join was scrubbed from the log. The scan of log 98 over 169 files
found no key, no join or accept line, no private key, no password and
no token (the 2 `keel2:` hits are sed patterns in the scripts).

## Cleanup

CTs 9400 to 9403, 9405 to 9407, 9420 to 9422, 9430 and 9431 were
destroyed with `pct destroy --purge`. The templates `ev307r3-*` and
`/root/ev307r3` (with the test user's password file) were removed. The
templates that were on the VM before were not touched. The Proxmox
firewall is `disabled/running` and `/etc/pve/firewall` is empty, as
before. The diff of the VM state before and after (the commands of log
00), without counters, time stamps and veth peer indexes, is empty:
`diff_exit=0 lines=0` (log 99).
