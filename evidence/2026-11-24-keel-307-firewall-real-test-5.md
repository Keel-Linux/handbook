# Evidence: fifth real-node test of keel pull request 307, the firewall in every mode (decision 0097)

Date: 2026-11-24. Site: BR1, the BR1 test VM (nested Proxmox VE).
Status: draft. For decision 0097 (accepted), section D, and for `keel`
pull request 307.

## Question

The fourth test (`evidence/2026-11-24-keel-307-firewall-real-test-4.md`,
head `e1402ea`) failed in part item 1 (the watch and the boot did not
write a lost file again) and item 2 (the file and the record lost at once
were silent, a planted record skipped rule B, the record followed a
symlink). Seven new commits say that they correct this:

- `625a890`: the record is trusted only as root's own regular file; an
  apply that finds a loaded table with policy drop keeps enforce.
- `fcced39`: `keel firewall repair`. The boot unit (`ExecStartPre`) and
  the watch run the firewall step of the apply, unattended, on an empty,
  cut or missing file of a node in enforce. Where that step cannot write
  the file, a closed fallback table is loaded and the run fails.
- `4e913c5`, `c22d585`, `1978dac`: the record is mode 0600 in a 0700
  directory, the directory is opened with `O_NOFOLLOW`, and the record is
  written by a rename.
- `2bb17e9`: a node with no evidence of a firewall (no file, no trusted
  record, no loaded table) is NOT APPLIED: the boot unit and the watch
  exit 0 and say nothing.
- `478f0c0`: changelog only.

This test runs items 1 to 6 of the task and tries to find one more way to
leave a node in enforce open or silent. The method and the probes are
those of the fourth test. A failure is a result. No code was changed.

## Tested head and package

- Tested head `478f0c0b00f93a3daadc0b367c9bc79a9fa01c65`. The Forgejo API
  gave the same head before the run (02:33 UTC) and after it
  (04:18 UTC), combined CI state `success` (13 contexts) both times.
  Version 0.23.99.
- `keel_0.23.99_all.deb`, sha256
  `f0192a91549004c1a0c496575539124c7cf30a753367dc44ecc8148671116091`,
  built from `git archive 478f0c0` with `dpkg-buildpackage -us -uc -b`,
  `SOURCE_DATE_EPOCH=1795486376` (the commit time), debhelper 13.24.2,
  with `PATH=/usr/sbin:/usr/bin:/sbin:/bin` (a first try failed: a
  `python3.13` in the user's `~/.local/bin` had no `build` module). The
  package holds `keel/system/fwrepair.py`, `keel/system/fwrecord.py` and
  `debian/keel.postrm`. Installed with `dpkg -i` after `pct push` only.
  It went to no repository and no mirror.

## Machines

Each CT is unprivileged, `nesting=1`, 2 cores (one CT set to 1 core for
the CPU cost), on the bridge `vmbr1` of the VM, DHCPv4 and DHCPv6 from
the dnsmasq of the VM. Templates as in the fourth test (lnmp 19.0-7,
core 19.0-13; `sqv` exit 0, `sha512sum -c` passed, sha256 the same as in
the fourth test). Each image has keel 0.23.96.

| CT | Image | Mode | Use |
| --- | --- | --- | --- |
| 9400 | core | simple | probe node, keel 0.23.96 kept |
| 9401 | lnmp | simple | item 4 (upgrade, 20 min, reboot, rule B), item 6 (probes, CPU on 1 core) |
| 9402 | lnmp | simple | item 1; the extra case X1 |
| 9403 | lnmp | simple | item 2 (fallback, broken spec, SSH on 2222) |
| 9404 | lnmp | simple | item 3 |
| 9405 | lnmp | simple | item 4, new node (first boot with the test package); item 5 |
| 9406 | core | simple | item 6, the joiner of the plain join |
| 9407 | core | simple | item 6, the joiner of the busy case |
| 9420, 9421, 9422 | lnmp, lnmp, core witness | cloud_advanced | `keel-commission --pass cloud_advanced`: PASS, 117 checks |
| 9430, 9431 | lnmp, lnmp | cloud_simple | `keel-commission --pass cloud_simple`: PASS, 87 checks |

The runner is `.github` at `f75cfec` (main). Every node except 9400 and
9405 was first upgraded to the published keel 0.23.97 from the Keel apt
channel (`apt-get install keel=0.23.97`), then to the test package
(`upgrade97.sh`). 9405 went from 0.23.96 to the test package before its
first boot ran (item 4). The probes run from CT 9400 and from the VM, on
IPv6 and IPv4. "Listener" means the units `ev-tcp` and `ev-udp`
(`listenunit.sh`): TCP and UDP 9999 on all addresses, enabled, so that
they run again after a reboot; no manifest declares them.

## Summary

| Item | Result | Key facts |
| --- | --- | --- |
| 1. Enforce node, undeclared listener, file empty, cut or missing | **PASS** | The node closed by itself in each of 9 cases; no apply by a person. Watch only: check sound again 19 to 31 s after the break, the listener never reachable. Table also deleted: listener reachable 19 to 26 s, then closed by the watch. Reboot: the boot unit writes the file again before the network; the listener never reachable. SSH reachable in every case except while the CT was down |
| 2. Closed fallback | **FAIL** in part | The fallback works: by the watch (23 s) and at boot; only loopback, established, ICMPv6, IPv4 echo request, DHCP client and sshd's ports pass (2222 when sshd listens there); unit failed, node degraded. A pair node in the fallback keeps WireGuard, etcd (3 voters), replication and Syncthing; the failover to it took 22.4 s, with its HTTP and HTTPS closed. But: a spec that does not parse disables the repair and the fallback: with a missing file the node is **open and silent after a reboot**; with an empty file it is loud but open. After a boot in the fallback, the apply restores the ruleset but **`keel-firewall.service` stays failed** and the node degraded until a reboot or a `systemctl reset-failed` by hand |
| 3. File and record lost, table loaded | **PASS**, with a note | Check exit 14. The watch does not fail: it repairs in enforce from the loaded table (31 s). The apply keeps enforce and writes the record; drop never became accept. All three lost by a reboot: NOT APPLIED, open, check exit 0, no line: the documented limit. The next apply goes to report by rule B |
| 4. No-evidence node | **PASS** | Upgrade from 0.23.97 (1 simple, 2 cloud_simple, 3 cloud_advanced) and a new node's first boot: never degraded, no failed unit, no rule, 0 keel lines from the firewall units in 18 to 35 min with reboots, check `NOT APPLIED`, exit 0. The restart list is the list of tests 3 and 4. Rule B decides the first apply (report with the listener, enforce without), also in the first-boot scripts |
| 5. Record hygiene | **PASS**, with a finding | Symlink, wrong owner, mode 0666 or 0620, directory 0777: no record, a warning in the plan, written again by a rename; the link target never changed; a linked directory refuses the write (exit 16). `apt remove` keeps the record, `apt purge` removes it. Finding: a directory owned by another user is never corrected, and with it an empty file at boot moves an enforce node to report |
| 6. Regression | **PASS** | Enforce with no `firewall:` key on 1 simple, 2 cloud_simple, 3 cloud_advanced nodes; the probe table as in test 3; failover with the VIP 33.4 s after the shutdown started; mesh joins under enforce (9.3 s, 7 s); a busy invite stays valid and the same line joins on retry; watch CPU on 1 core: 32 to 48 ms a run (shell path), 0.88 to 1.03 s (repair) |
| One more way | **found** | A spec that does not parse (item 2); the text `state: off` anywhere in the spec, a comment included, which makes the watch skip a missing file (open and silent for the 2 min observed; a reboot would repair it, read from the code); an untrusted record directory and an empty file at boot (item 5: enforce to report) |

## Item 1: enforce node with an undeclared listener, file broken (PASS)

9402 in enforce after its first apply (`enforce: each socket ... (decision
0097, B)`, record `enforce`, root 0600), listener up. `item1.sh` for each
case: the break, then no command by a person; `fastprobe.py` from CT 9400
on IPv6 and IPv4 (TCP 9999 and 22, one round about each 0.15 s) for 120 s (150 s
with a reboot); `keel firewall check` each second until exit 0; then the
journal, `probe.py` from CT 9400 and from the VM, and a count of `keel
spec apply` lines in the journal (0 in each case). Cut file: the first 330
of 661 bytes (no policy line).

| Case | Check exit 0 again after the break | TCP/UDP 9999 from outside | What acted |
| --- | --- | --- | --- |
| a. Empty, watch only | 30.1 s | never reachable (table kept, `policy drop`) | the watch: `enforce, as keel's record says ...`, `udp *:9999 of ev-udp.service (python3): listens, not declared, closed by the firewall` (and TCP), `write ... (enforce) ...: done`, `load it ...: done`, `... written again by the firewall step of the apply` |
| a. Cut, watch only | 19.4 s | never reachable | the same |
| a. Missing, watch only | 25.7 s | never reachable | the same |
| c. Empty, and `nft delete table inet keel` | 24.2 s | open 19.2 s (03:00:57.5 to 03:01:16.7, both families), then `timeout` | the watch, the same lines |
| c. Cut, and the table deleted | 31.2 s | open 25.8 s, then `timeout` | the watch |
| c. Missing, and the table deleted | 27.5 s | open 24.1 s, then `timeout` | the watch |
| b. Empty, `pct reboot` | 15.5 s (reboot included) | never reachable | `keel-firewall.service` at boot: `keel[72]: derived.firewall: enforce, as keel's record says ...`, the same plan lines, `... written again ...`; unit `active` |
| b. Cut, `pct reboot` | 15.0 s | never reachable | the boot unit |
| b. Missing, `pct reboot` | 17.4 s | never reachable | the boot unit |

After each case: file `# state: enforce`, 661 bytes, `policy drop`, record
`enforce`; TCP and UDP 9999 `timeout` from CT 9400 and from the VM on both
families; TCP 22 and 80 `open`. SSH (TCP 22) answered in every case except
while the CT was down in a reboot. Node `running`, no failed unit.

In the three cases with the table deleted, the listener was reachable for
19 to 26 s, which is the bound of the watch (30 s period, 5 s accuracy).
In each reboot, the probes saw `refused` on 9999 and 22 for about
0.2 s while the CT shut down: the services were stopped, so nothing was
served, but no table dropped the packets at that moment.

## Item 2: closed fallback (FAIL in part)

9403 in enforce, listener up (logs 20 to 23).

### The fallback (a directory in place of the file)

A directory at `/etc/keel/firewall/keel-manifest.nft` makes the rename of
the step fail while the spec and the record are sound.

| Case | Observed |
| --- | --- |
| 2a. The directory, watch only | Fallback loaded 23 s later. The watch: `Error: ... cannot be read: Is a directory; derived.firewall: enforce, as keel's record says ...`, exit 14, `keel-firewall-watch.service: Failed`; node `degraded`. The table: `comment "keel-fallback"`, `policy drop`, `iif "lo" accept`, `ct state established,related accept`, `ct state invalid drop`, `meta l4proto ipv6-icmp accept`, `icmp type echo-request accept`, `ip6 saddr fe80::/10 udp dport 546 accept`, `udp dport 68 accept`, `tcp dport 22 accept`. From CT 9400 and the VM, both families: TCP 22 `open`; TCP and UDP 9999, TCP 80, 443, 12321 `timeout` |
| 2b. The directory kept, `pct reboot` | `keel-firewall.service`: `write ... not done: Is a directory; the node keeps the firewall it had`, `the node was in enforce and ... cannot be written again: the closed fallback table is loaded (drop; sshd's ports 22); the node stays degraded until keel spec apply --system`, exit 16, `Failed`. Node `degraded`, `keel-firewall.service` and `keel-firewall-watch.service` failed. `fastprobe` through the reboot: 9999 never reachable; 22 `open` again about 18 s after the reboot started |
| 2c. The directory removed, then `keel spec apply --system` | `enforce, as keel's record says ...`, `write ... (enforce) ...: done`, `load it ...: done`; check `table inet keel is the one ... says`. `keel-firewall-watch.service` is `inactive` again. But `keel-firewall.service` stays **failed** and the node stays **degraded** (35 s and again 2 min after the apply). It stayed failed until a `systemctl reset-failed` by hand (at the start of 2e, log 22) |

### SSH on a port that is not 22, and sshd's ports unknown

| Case | Observed |
| --- | --- |
| 2h1. `Port 2222` only (drop-in, `ssh.service` restarted), apply (`SSH stays open: tcp 2222, the ports sshd listens on (sshd -T)`), then the directory | Fallback: `tcp dport 2222 accept`, no 22. From CT 9400, both families: TCP 2222 `open` (banner `SSH-2.0-OpenSSH_10.0p2 Debian-7+deb13u4`), TCP 22 and 9999 `timeout` |
| 2h2, 2h3. sshd still on 2222, an unknown option added (`sshd -T` exit 255), file emptied | No fallback: the watch wrote the full ruleset again (`SSH stays open: tcp 2222, the ports sshd listens on (/etc/ssh/sshd_config)`). keel takes the port from the text of the file. This method does not make the step fail |

### A spec that cannot be read (invalid YAML)

One line `broken: [unclosed` added at the end of `instance.yaml` (a copy
kept; the spec was never printed). `keel spec validate` exit 2.

| Case | Observed |
| --- | --- |
| 2d. Invalid spec, file emptied, watch | The watch fails each run: `... is empty or cut short ...; table inet keel holds a08b6b17d635a90b`, node `degraded`. No repair, no fallback. The old table stays loaded |
| 2d2. And the table deleted | The watch fails each run (`table inet keel is not loaded`), node `degraded`. **No fallback.** From CT 9400: TCP 9999 `open`, UDP 9999 `reply`, both families |
| 2e. Invalid spec, file removed (record and table kept) | `keel firewall check`: `... no ruleset of keel's, nothing to compare`, **exit 0**. The watch: no line in 70 s, unit not failed, node `running` |
| 2f. The same, `pct reboot` | `keel-firewall.service` `active (exited)`, all three steps `status=0/SUCCESS`, no keel line in the journal; node `running`, no failed unit; tables: `inet filter` only; check exit 0 as in 2e; `keel diff` exit 2 (`not valid YAML`). From CT 9400 and the VM, both families: TCP 9999 `open`, UDP 9999 `reply`; UDP 12321 `reply` on IPv4. **The node is fully open and says nothing** |
| 2g. The spec put back | The watch wrote the file again in enforce within 20 s |

`keel firewall repair` reads the spec with `yaml.safe_load`; on any error
`spec_doc()` gives None, `wants_firewall(None)` is False, and the repair
returns OK with no line (`keel/system/fwrepair.py`, `repair()`). The check
of a missing file takes the same path (`fwcheck.missing()`). Thus a spec
that does not parse disables the repair and the fallback, and with a
missing file also the signal. The text of the PR says the fallback covers
"the spec unreadable".

### The pair with one node in the fallback

The cloud_advanced trio after the failover of item 6: 9421 primary with
the VIP, 9420 standby (log 25). `pairfb.sh`: the directory in place of
the file on 9420, the watch only.

| Step | Observed |
| --- | --- |
| Fallback on the standby 9420 | Loaded 34 s later. The table as in 2a, and `udp dport 51820 accept`, `iifname "wg0" accept` (the defaults: the spec has `network.overlay.wireguard` with `address` and `peers` only). Watch failed, node `degraded` |
| The pair, 80 s later | A row written on 9421 arrived on 9420; `Slave_IO_Running: Yes`, `Slave_SQL_Running: Yes`, `Seconds_Behind_Master: 0`; etcd `3 voter(s)`, all `healthy`; WireGuard handshakes 17 to 110 s old; 3 Syncthing sessions |
| From outside on 9420's eth0, both families | TCP 22 `open`; TCP 80, 443, 12321, 9999 `timeout` |
| Failover to the node in the fallback: `pct shutdown 9421` at 04:07:24.5 | VIP on 9420 at 04:07:46.9, 22.4 s after the shutdown started; `read_only` 0, a row written; the table stays `keel-fallback` |
| 9421 started again | `rejoined: no errant GTID, replicating from [...]:3306 over TLS` 77 s after the start; all 5 rows; `Seconds_Behind_Master: 0`; 9421 in enforce, `running` |
| 9420 as the primary in the fallback | the VIP on wg0; `curl https://localhost/` 200 on the node; from outside TCP 22 `open`, TCP 80 and 443 `timeout`: the application is not served on eth0 while the node is in the fallback |
| The directory removed, `keel spec apply --system` | the full ruleset in enforce, watch no longer failed, node `running` (no reboot was in this case, so `keel-firewall.service` had not failed) |

The fallback keeps the mesh, replication and the VIP, and the pair fails
over to a node in the fallback. A node in the fallback serves no
application port on its public address.

Note: while the watch is failed, each run makes the unit `activating`
for about 1 s; one sample of `systemctl is-system-running` taken at
04:09:16 said `running` while 9420 was still in the fallback. Samples
before and after said `degraded`.

## Item 3: the file and the record lost with the table loaded (PASS, with a note)

9404 in enforce, listener up (log 30).

| Case | Observed |
| --- | --- |
| 3a. Both removed, the watch timer running | `keel firewall check` at once: `Error: ... no ruleset file, and keel's record says enforce (or the loaded table does): keel spec apply --system writes it again`, **exit 14**. The watch did not fail: 31 s later it repaired, `enforce, as the loaded table inet keel says (policy drop): its file and keel's record are gone`, `write ... (enforce)`, `record ...: enforce ...: done`, `... written again ...` (journal level warning). Unit not failed, node `running` |
| 3b. The timer stopped, both removed, then `keel spec apply --system` | check exit 14 as above. The apply: `enforce, as the loaded table inet keel says (policy drop) ...`, `write ... (enforce)`, `load it ...`, `record ...: enforce ...: done`. `policy drop` kept; 9999 `timeout` from outside. drop never became accept |
| 3c. The timer stopped, both removed, `pct reboot` | `keel-firewall.service` `active`, no keel line; node `running`, no failed unit; tables `inet filter` only; check: `NOT APPLIED: ... is not there, and nothing says this node had a firewall of keel's; keel spec apply --system writes it`, exit 0; `keel diff`: `derived.firewall: drift (declared ..., report, observed nothing)`. From CT 9400: TCP 9999 `open`, UDP 9999 `reply`. This is the documented limit |
| 3d. The next apply after 3c | `report: enforce waits, because these sockets belong to no unit of the manifests: ...`; `policy accept`, record `report` |

Note: the watch does not "fail loudly" in 3a. It repairs from the loaded
table at its next run and writes warnings. The check fails loudly.

Also on the cloud_simple node 9431 in enforce (log 31): the watch timer
stopped, file and record removed, then `keel mesh sync` (unattended). It
did not touch the firewall (no member change): file and record absent,
`policy drop` kept. When the timer started again, the watch wrote both
again in enforce from the loaded table (`enforce, as the loaded table
inet keel says (policy drop) ...`).

## Item 4: no-evidence node (PASS)

### Upgrade from 0.23.97

`upgrade97.sh` on 9401 (simple), the cloud_advanced trio 9420 to 9422
and the cloud_simple pair 9430 and 9431 (logs 10, 11, 21).

| Change | simple (9401) | cloud_simple (9430, 9431) | cloud_advanced (9420, 9421, witness 9422) |
| --- | --- | --- | --- |
| Rule loaded | none (`inet filter` only) | none (`inet filter`, CrowdSec's two tables, as before) | the same |
| Enabled | `timers.target.wants/keel-firewall-watch.timer` (new link), not started | the same | the same |
| `nftables.service` | drop-in `keel-firewall.conf` live, not run | the same | the same |
| systemd reloads | 8 | 8 | 8 |
| Restarted (stop and start) | `keel-mesh-members.path`, `keel-mesh-sync.timer`, `keel-mesh-etcd.timer`, `keel-database-follow.path`, `keel-database-watch.timer`, `keel-database-dump.timer`, `keel-database-position.timer` | the same, and `keel-mesh-members.service`, `keel-mesh-members-listen.service`; `keel-database-position.service` started on both | the same, and on 9420 and 9421 `keel-database-position.service`, `keel-vip.service`, `keel-vip-control.service`, `keel-vip-check.timer` |
| Runs triggered | none | `keel-database-follow.service`, `keel-database-watch.service` | the same, `keel-vip-check.service`; on 9420 also `keel-mesh-etcd.service`, `keel-mesh-sync.service` |
| MariaDB, etcd, Syncthing, wg-quick, nginx | not restarted | not restarted | not restarted |

The restart list is the list of the third and fourth tests. The runs that the restarts triggered differ a little (here `keel-database-position.service` started on both cloud_simple nodes, in the fourth test only on 9431; `keel-mesh-sync.service` ran on 9420), as the timers fall. `keel diff` exit
changes from 0 to 14 (the firewall drift until the first apply), as the
PR says.

### The window with no apply

`window.sh` (logs 14, 21, 61): node state, failed units, the lines of
`keel-firewall.service` and `keel-firewall-watch.service` that are not
systemd's, the tables, `keel firewall check`.

| Node | Window | Node | Failed units | keel lines from the firewall units | Tables | `keel firewall check` |
| --- | --- | --- | --- | --- | --- | --- |
| 9401 simple | 20 min after the install, no reboot (watch timer not started) | `running` | 0 | 0 | `inet filter` | `NOT APPLIED: ... is not there, and nothing says this node had a firewall of keel's; keel spec apply --system writes it`, exit 0 |
| 9401 simple | then `pct reboot`; 15 min with the timer running (about 30 runs) | `running` | 0 | 0 | `inet filter` | the same |
| 9420 to 9422, 9430, 9431 | about 18 min after the install (not 20) | `running` | 0 | 0 | `inet filter` and CrowdSec's | the same |
| 9421, 9431 | `pct reboot` at 18 min, 3 min with the timer running | `running` | 0 | 0 | the same | the same |
| 9405 new node | the first boot with the test package, before any apply (below), 20 min | `running` | 0 | 0 | `inet filter` | the same |

`keel-firewall.service` ran at each of these boots (its condition is now
`/etc/keel/instance.yaml`): `ExecStartPre=keel firewall repair --boot`,
`ExecStart` and `ExecStartPost` all `status=0/SUCCESS`, unit
`active (exited)`, 0.64 s of CPU (Python). The watch unit logs nothing on
this path (`LogLevelMax=notice`); a run costs about 22 ms of CPU on 2
cores (`CPUUsageNSec`).

### New node, first boot before its first apply

`create_new.sh`: 9405 made from the lnmp template as the others, but with
`inithooks.service` masked (a link to `/dev/null` in its root file system)
before the first start. Then `dpkg -i` of the test package (0.23.96 to
0.23.99), `pct reboot`: this boot is the first boot of a node that has the
test package and has had no apply (log 60). Result in the table above.
Then the listener units enabled, `inithooks.service` unmasked, `pct
reboot`: the first-boot scripts ran once (`Inithooks run completed`: 1)
and their apply said `report: enforce waits, because these sockets belong
to no unit of the manifests: udp *:9999 of ev-udp.service (python3); tcp
*:9999 ...`, `write ... (report)`, `record ...: report`; `policy accept`
(log 62). The listeners removed, `keel spec apply --system`: `enforce:
each socket ... (decision 0097, B)`, `policy drop`.

### Rule B on the upgraded node

9401 after the window, listener up, the first apply: `report: enforce
waits, because these sockets belong to no unit of the manifests: ...`,
`write ... (report)`, `record ...: report`, `policy accept`. Listener
removed, the second apply: `enforce: each socket ... (decision 0097, B)`,
`policy drop`, record `enforce` (log 15). On the five cloud nodes (no
listener) the first apply went to `enforce` (log 41).

## Item 5: record hygiene (PASS, with a finding)

9405 in enforce. `rec.sh`: the break, the record and the target before,
`keel spec apply --system`, the record and the target after (log 50).

| Case | Plan | Record after | Note |
| --- | --- | --- | --- |
| 5a. Record a symlink to `/root/ev5t` (`report`, root 0644, mtime fixed) | `... is not trusted (it is not a regular file): it counts as no record; the next apply writes it again`, `record ...: enforce ... (mode 0600, by a rename): done` | regular file, root 0600, `enforce` | target unchanged: `report`, 0644, the same mtime |
| 5b. Owner `nobody:nogroup` | `... not trusted (root does not own it) ...`, `record ...: done` | root 0600 | |
| 5c. Mode 0666 | `... not trusted (group or others may write it) ...`, `done` | root 0600 | |
| 5d. Mode 0620 | the same | root 0600 | |
| 5e. Directory 0777 | `... not trusted (its directory is not trusted: group or others may write it) ...`, `done` | directory 0700 again | |
| 5f. Directory owned by `nobody:nogroup` | `... not trusted (its directory is not trusted: root does not own it) ...`, `record ...: done` | directory **still `nobody:nogroup`** | a second apply says the same: the record is never trusted again (5f3) |
| 5g. Directory a symlink to `/root/ev5d` (holds `report`) | `... not trusted (its directory is not a directory) ...`, `record ...: failed: /var/lib/keel/firewall is a link: the record is not written`, apply **exit 16** | link kept; `/root/ev5d/state` unchanged (`report`) | not followed, not written through |

`keel firewall check` gave exit 0 in each case: the check does not name an
untrusted record; only the plan does.

### An untrusted record and a broken file at boot

The directory of the record owned by `nobody` (as 5f: the apply does not
correct it, so the record stays untrusted), the node in enforce, listener
up, the watch timer stopped, then `pct reboot` (log 51).

| File | Observed after the reboot |
| --- | --- |
| Missing | NOT APPLIED: check exit 0, node `running`, no keel line, no table; TCP 9999 `open`, UDP 9999 `reply` from CT 9400. As the documented limit, but here the record exists and only its directory owner is wrong |
| Empty | The boot unit: `report: only an apply a person runs (keel spec apply --system) moves this node to enforce`, `enforce would close ... 9999 ...`, `... is not trusted ...`, `write ... (report)`, `record ...: report`; unit `active`, node `running`. `policy accept`; TCP 9999 `open`, UDP 9999 `reply`. **A node in enforce left enforce with no change of the spec**, and no failed unit |

(One run of the empty case started from `report` by mistake and is marked
void in log 51; the run above started from `policy drop`.)

### `apt remove` and `apt purge` (log 52)

`apt-get remove -y keel` removed keel and 12 packages that depend on it
(`keel-web`, `keel-core`, `confconsole` and the overlay packages). After
it: record kept (`/var/lib/keel/firewall/state`, root 0600, `enforce`),
the ruleset file kept, `table inet keel` still loaded, watch timer
`inactive`. `apt-get purge -y keel`: `/var/lib/keel/firewall` removed. The
ruleset file `/etc/keel/firewall/keel-manifest.nft` (enforce) stays after
the purge.

## Item 6: regression (PASS)

`grep -c "^firewall:" /etc/keel/instance.yaml` gave 0 on each node. The
first apply on each node (logs 15, 41):

| Node | Plan text |
| --- | --- |
| 9401 lnmp simple | `enforce: each socket ... (decision 0097, B)`, `public tcp 22, 80, 443, 12321` |
| 9430, 9431 cloud_simple | the same, `public tcp 22, 80, 443, 12321 and udp 51820, mesh tcp 3306, 22000 and udp 22000 on wg0` |
| 9420, 9421 cloud_advanced | the same, `... mesh tcp 2379, 2380, 3306, 22000 and udp 22000 on wg0` |
| 9422 witness | `public tcp 22, 12321 and udp 51820, mesh tcp 2379, 2380 on wg0` |

Probes with `listen.sh` (TCP and UDP 9999) on each node, 4 rows per node
and port (CT 9400 and the VM, IPv6 and IPv4), on the eth0 addresses (logs
40, 42):

| Port | 9401, 9420, 9421, 9430, 9431 | 9422 witness |
| --- | --- | --- |
| TCP and UDP 9999 | timeout | timeout |
| TCP 22, 12321 | open | open |
| TCP 80, 443 | open | timeout |
| UDP 12321 | timeout | timeout |
| TCP 3306 (9401 too), 2379, 2380, 22000, UDP 22000 (mesh, on eth0) | timeout | timeout |

SSH banner `SSH-2.0-OpenSSH_10.0p2 Debian-7+deb13u4` from 9401 on both
families.

| Check in enforce (cloud_advanced) | Observed |
| --- | --- |
| Replication | a row written on 9420 arrived on 9421; etcd 3 voters; WireGuard handshakes 35 s old |
| Failover (log 43) | `pct shutdown 9420` at 03:50:02.9 (returned 03:50:11.4); VIP on 9421 at 03:50:36.3, **33.4 s** after the shutdown started; `read_only` 0; a row written; `policy drop` |
| Return | `pct start 9420` at 03:50:47; `rejoined: no errant GTID, replicating from [...]:3306 over TLS` at 03:51:53; replicating 77 s after the start; both rows; `Seconds_Behind_Master: 0`; enforce |
| Mesh invite and join under enforce (log 44) | 9406 (core, simple, enforce) joined through an invite of 9420: `joined the mesh`, exit 0 after 9.3 s; 9406 stayed in enforce |
| Busy invite (log 46) | `holdlock.py 90` holds the apply lock on the inviter 9420. Join from 9407 at 04:13:52.8: `the inviter refused the join: busy: ...; send it again in a minute`, exit 24 after 7.7 s; the inviter: `invite ...: busy: ...; the invite stays`; invite and listener units `active running` 10 s later and after the lock was free; `expired unused` lines in 2 min: 0. The same line at 04:15:27: `joined the mesh`, exit 0 after 7 s; 9407 `policy drop`, file and record `enforce` |
| Watch CPU, 1 core (9401, `pct set --cores 1`, `nproc` 1; log 16) | shell path (sound file): 32.4, 38.0, 33.7, 46.8, 47.7, 36.8, 40.0, 35.4 ms a run; repair path (file emptied before each run): 910, 1026, 884 ms |

Void runs, kept in the logs: the first busy run (log 44) held no lock,
because `push.sh` skips file names that contain `dl` and so did not copy
`holdlock.py`; its first join is the plain join above. Its second join
used the spent line: `no answer from the inviter's port ...: timed out`,
then it waited for `keel mesh accept` to its timeout (exit 124 after
602 s), which is the behaviour of a spent invite. On 9431 `pct set
--cores 1` did not take effect live (`nproc` 2); its runs (35 to 47 ms)
are not counted as 1-core values.

## One more way to leave a node in enforce open or silent

Two ways were found, and one method that did not work.

1. **A spec that does not parse** (2d to 2f). With a missing file the node
   is silent; after a reboot it is fully open and silent (`running`, no
   failed unit, check exit 0). With an empty file it is loud but open, and
   no fallback loads.
2. **The text `state: off` anywhere in the spec** (case X1, log 80). The
   watch skips a missing file when `grep -Eq 'state:[[:space:]]*(off|false)\b'`
   matches the spec, and a comment matches too. 9402 in enforce, a comment
   `# old note: firewall state: off was the choice before 0097` added
   (`keel spec validate` exit 0), the file removed and the table deleted:
   `keel firewall check` exit 14, but the watch script exit 0 with no
   line; 90 s later the node was still `running`, no failed unit, no
   table, TCP 9999 `open` and UDP 9999 `reply` from CT 9400. At 03:37:41,
   2 min after the break, the comment was removed; the watch then wrote
   the file again within 40 s. Nothing under `/etc/monit` names
   `keel-firewall`: keel writes Monit's `keel-firewall` check into
   `/etc/keel/monit/keel-manifest.conf`, which Monit includes only while
   `monitor.enabled` is true (`keel/system/appliance.py`, read from the
   code); the test specs have no `monitor:` section, so no Monit check ran.
   The next boot would repair the node, because the boot unit parses the
   spec (read from the code, not tested). (Log 80 says "6 min after the
   break" at 03:37:41; that is wrong, it was 2 min.)
3. Also found: an untrusted record (directory owner wrong, which the apply
   does not correct) and an empty file at boot move the node from enforce
   to report (item 5).
4. Not found: making `sshd -T` fail does not hide sshd's port (keel reads
   it from the file).

## Against the fourth test

| Fourth test (head `e1402ea`) | This test (head `478f0c0`) |
| --- | --- |
| The watch never wrote a broken file again; with the table lost the node was open until an apply | the watch writes an empty, cut or missing file again in enforce within 19 to 31 s; with the table also deleted the listener was reachable 19 to 26 s |
| A reboot with an empty file left the node degraded and open until an apply | the boot unit writes the file again before the network; the listener was never reachable |
| The file and the record lost at once were silent | check exit 14; the watch and the apply keep enforce from the loaded table |
| The record was followed through a symlink, its owner not checked | not trusted, replaced by a rename; a linked directory refuses the write. New: a directory with a wrong owner is never corrected |
| (no fallback) | the fallback loads and keeps SSH (also on 2222); a spec that does not parse disables it |

## What was not tested

- The ISO, two sites with netem, image builds, the other images.
- The fallback when sshd's ports are truly unknown (no running sshd and an
  unreadable configuration).
- Monit's `keel-firewall` check (included only with `monitor.enabled`; the test specs had no `monitor:` section).
- The window with no apply on the cloud nodes was about 18 min, not 20 (install at 03:15, last reading at 03:33:50).
- The pair under writes during the upgrade.

## Logs

On the maintainer's workstation in
`repos/evidence-0097-2026-11-23/pr307-run5/`. The runner records
(`runner-adv/`, `runner-cs/`) hold console transcripts and are not copied
here.

| Log | Content |
| --- | --- |
| `05-api-before`, `97-api-after` | head and CI state before and after |
| `00-vm-baseline`, `99-vm-after`, `99-vm-diff`, `99-cleanup` | the VM before and after |
| `01-images`, `02-create-simple`, `03-firstboot-simple`, `04-push`, `06-create-new`, `07-create-joiner`, `08-create-joiner2`, `70-joiner-setup` | templates, CTs |
| `20-adv-runner`, `40-cs-runner` | commissioning |
| `10-simple-upgrade`, `11-simple-upgrade-9401`, `21-upgrade-94NN`, `14-item4-window-9401`, `21-item4-window-cloud`, `15-item4-ruleB-9401`, `41-cloud-apply`, `60-new-node`, `61-new-window`, `62-new-firstboot` | item 4 |
| `12-item1-apply`, `13-item1` | item 1 |
| `20-item2-setup`, `21-item2-fallback`, `22-item2-badspec`, `23-item2-ssh2222`, `24-adv-spec-shape`, `25-item2-pair-fallback` | item 2 |
| `30-item3`, `31-item3-meshsync` | item 3 |
| `50-item5`, `51-item5-untrusted-reboot`, `52-item5-remove-purge` | item 5 |
| `16-item6-cpu`, `45-item6-cpu-cs`, `40-item6-simple-probe`, `42-item6-cloud-probe`, `43-item6-failover`, `44-item6-busy-join`, `46-item6-busy-join-2` | item 6 |
| `80-extra-comment-off` | the extra case X1 |
| `98-secret-scan` | secret scan |

Secret handling: node secrets were made inside each stopped CT and never
printed. The spec was copied with `cp -a` before each change and never
printed. Join lines stayed in shell variables and went to the joiner by
standard input, never shown. Every `.log`, `.out`, `.txt`, `.tsv` and
`.md` file under `pr307-run5/`, the runner console transcripts included,
was scrubbed of WireGuard public keys, join lines and accept lines
(`scrub.sed`), and each control or non-ASCII byte in them was replaced by
`?`. The scan of log 98 over 160 files found no key, no join or accept
line, no private key and no token. The 4 `keel2:` hits are sed patterns
in the scripts. The 5 `password` hits are screen control codes after the
`password:` prompt in the console transcripts (9 lines). The same 8
patterns over this file: 2 lines with the word `keel2:`, in this paragraph; no key, no join line, no password, no token.

## Cleanup

CTs 9400 to 9407, 9420 to 9422, 9430 and 9431 were destroyed with `pct
destroy --purge`. The templates `ev307r5-*` and `/root/ev307r5` were
removed. The templates that were on the VM before were not touched. The
Proxmox firewall is `disabled/running` and `/etc/pve/firewall` is empty,
as before. The diff of the VM state before and after (the commands of
log 00 of the fourth test, and the list of `/var/lib/vz/template/cache`
and `/root`), without counters, time stamps and veth peer indexes, is
empty: `diff_exit=0 lines=0` (log 99). The runner worktree
`worktrees/runner-ev307r5` was removed.
