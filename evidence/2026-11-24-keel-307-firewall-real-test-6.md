# Evidence: sixth real-node test of keel pull request 307, the firewall in every mode (decision 0097)

Date: 2026-11-24. Site: BR1, the BR1 test VM (nested Proxmox VE).
Status: draft. For decision 0097 (accepted), section D, and for `keel`
pull request 307.

## Question

The fifth test (`evidence/2026-11-24-keel-307-firewall-real-test-5.md`,
head `478f0c0`) found: a spec that does not parse turned off the repair
and the fallback; the text `state: off` anywhere in the spec silenced the
watch; a record directory owned by another user was never put right, and
with an empty file at boot the node went from enforce to report; the boot
unit stayed failed after an apply. Two new commits say that they correct
this:

- `8ce2911`: each apply keeps a last good copy of the ruleset
  (`/var/lib/keel/firewall/last-good.nft`); the record can say `off`; the
  apply puts keel's directory right; a successful apply restarts a
  `keel-firewall.service` that failed at boot.
- `e12665d`: a spec that cannot be parsed never turns off the repair of a
  node in enforce; the watch takes `off` from keel's record only.

The method and the probes are those of the fifth test. A failure is a
result. No code was changed. Each statement below was tested by action,
unless it says "read from the code".

## Tested head and package

- Tested head `e12665d1c7d968b78eb8cc4e8da91f1b3c82aca8`. The Forgejo API
  gave the same head before the run (04:54 UTC) and after it (06:03 UTC),
  combined CI state `success` (13 contexts) both times. Version 0.23.99.
- `keel_0.23.99_all.deb`, sha256
  `722c9ba25f98cb55a63f1b1077c712ceb28ba8137312d066ea37980d55ddba2a`,
  built from `git archive e12665d` with `dpkg-buildpackage -us -uc -b`,
  `SOURCE_DATE_EPOCH=1795494837` (the commit time), debhelper 13.24.2,
  `PATH=/usr/sbin:/usr/bin:/sbin:/bin`. Installed with `dpkg -i` after
  `pct push` only. It went to no repository and no mirror.

## Machines

Each CT is unprivileged, `nesting=1`, 2 cores (9401 set to 1 core for the
CPU cost), on the bridge `vmbr1` of the VM, DHCPv4 and DHCPv6 from the
dnsmasq of the VM. Templates as in the fifth test (lnmp 19.0-7, core
19.0-13; `sqv` exit 0, `sha512sum -c` passed, the same sha256). Each image
has keel 0.23.96.

| CT | Image | Mode | Use |
| --- | --- | --- | --- |
| 9400 | core | simple | probe node, keel 0.23.96 kept |
| 9401 | lnmp | simple | item 7 (upgrade window, probe table, CPU) |
| 9402 | lnmp | simple | item 1 (enforce), item 4, extra cases X3, X4 |
| 9403 | lnmp | simple | item 1 (a node in report) |
| 9404 | lnmp | simple | items 2 and 3, extra cases X1, X2 |
| 9405 | lnmp | simple | item 7 (new node), item 5, remove and purge |
| 9406 | core | simple | item 7, the joiner |
| 9420, 9421, 9422 | lnmp, lnmp, core witness | cloud_advanced | `keel-commission --pass cloud_advanced`: PASS, 117 checks; items 6 and 7 |

The runner is `.github` at `f75cfec` (main). Every node except 9400 and
9405 went to the published keel 0.23.97 (`apt-get install keel=0.23.97`),
then to the test package (`upgrade97.sh`). 9405 was made with
`inithooks.service` masked and got the test package before any apply.
The probes run from CT 9400 on IPv6 and IPv4. "Listener" means the units
`ev-tcp` and `ev-udp` (TCP and UDP 9999, enabled, no manifest declares
them).

## Summary

| Item | Result | Key facts |
| --- | --- | --- |
| 1. Spec unreadable, not parsed, or missing | **FAIL** | Unreadable (a directory) or invalid YAML: never open; the copy is restored (declared ports open, listener closed), or with the copy lost the closed fallback, unit failed, node degraded. But a **missing spec** (or a dangling symlink in its place) turns off the watch and the boot repair (`ConditionPathExists=/etc/keel/instance.yaml`): with the table lost the node is **open and silent** (`running`, no keel line), in the watch case even with a sound ruleset file. `keel firewall check` fails (exit 14) only in the missing-spec cases; with the copy restored it says exit 0 while the spec does not parse. On the report node the copy is restored, not a loud failure |
| 2. `state: off` | **PASS** | A comment does not turn the firewall off; the watch closed the node in 28 s. Another key with `state: off` is refused by the validator (exit 3), nothing changes. The real `firewall: state: off` removes file and table and writes the record `off`; watch and reboot load nothing, also with the spec then made invalid. Back to `state: enforce`: record `enforce`, and the watch closes a lost table again |
| 3. Last good copy | **FAIL** in part | Written only after a load that worked; hygiene holds (symlink, other owner, 0666, directory of another user: not trusted, the fallback, then put right by the next apply); a copy that a user `nobody` wrote is not loaded; a cut or edited copy is not loaded. `apt remove` keeps it, `apt purge` removes it. But a copy that differs from the spec is restored with no signal: a **stale copy reopened a removed port** (TCP 8080 `open` from outside, check exit 0, watch silent, only `keel diff` saw it) until the next apply; a sound **report copy on an enforce node** made the node `policy accept` (root planted it) |
| 4. Apply after a boot in the fallback | **PASS**, with a note | The apply restarts `keel-firewall.service` (`active`). The node stays `degraded` until the next run of the watch clears its own failure: 20 to 30 s |
| 5. Record directory of another user, empty file, boot | **PASS** | The boot unit: `NOT APPLIED, the node keeps the firewall it has: keel's record is not trusted ...`, then the closed fallback; the watch then wrote the full ruleset and put the directory right (root, 0700). No move to report |
| 6. Pair | **PASS** | With the copy: the standby restored it, the failover took 22.6 s, HTTP and HTTPS answer from outside (`https` 200). Bare fallback (copy lost): the failover took 22.3 s, the node holds the VIP, `https://localhost/` 200, but TCP 80 and 443 `timeout` from outside: the documented limit. Note: a standby whose spec does not parse did not take the VIP at all |
| 7. Regression | **PASS** | Upgrade from 0.23.97: NOT APPLIED, silent, `running` (simple 18 min with a reboot, the trio 10 min). New node before its first apply: the same. lnmp simple enforce probe table as before. Busy invite refused, kept, the same line joined (6 s) under enforce. Watch CPU on 1 core: 34 to 44 ms a run, as in test 5 |
| 8. One more way | **found** | Tested by action: a missing spec (item 1), a dangling symlink spec (X4), and a record `off` written by an unprivileged user who owns keel's directory (X2) leave the node open and silent; a stale or report copy changes the ruleset with no signal (item 3) |

## Item 1: a spec that cannot be read, does not parse, or is missing (FAIL)

`case1.sh` on 9402 (enforce, record `enforce`, copy root 0600, listener
up), logs 13 and 14. Spec: `unread` (the file replaced by a directory, so
`open()` fails), `bad` (a line `broken: [unclosed` added), `missing` (the
file moved away). The spec was moved or copied, never printed. Watch
mode: the table is also deleted, then only the watch acts for 45 s.
Reboot mode: `pct reboot`, then nothing for 40 s. Then the spec is put
back and `keel spec apply --system` runs.

### With the last good copy present

| Spec | File | Mode | Loaded after | Node | check | TCP 9999 / TCP 80 from outside |
| --- | --- | --- | --- | --- | --- | --- |
| unread | intact | watch | `keel-manifest a08b...` (`loaded again` from the file) | running | 0 | timeout / open |
| unread | empty, missing | watch | the same, `restored from keel's last good copy` | running | **0** | timeout / open |
| bad | intact, empty, missing | watch | the same | running | **0** | timeout / open |
| unread, bad | intact | reboot | the full ruleset (the boot unit loads the sound file) | running | 0 | timeout / open |
| unread, bad | empty, missing | reboot | the full ruleset, the boot unit: `restored from keel's last good copy` | running | **0** | timeout / open |
| **missing** | intact, empty, missing | watch | **no table** | **running** | 14 | **open / open** |
| missing | intact | reboot | the full ruleset (loaded by the `nftables.service` drop-in; the boot unit is skipped) | running | 0 | timeout / open |
| **missing** | empty, missing | reboot | **no table** | **running** | 14 | **open / open** |

In each missing-spec case with no table: no failed unit, 0 lines of keel
in the journal of the firewall units. Both `keel-firewall.service` and
`keel-firewall-watch.service` have `ConditionPathExists=/etc/keel/
instance.yaml`, so systemd skips them (read from the unit files; the
skip is seen as 0 lines and no table). Only `keel firewall check`, when a
person runs it, says `no ruleset file, and keel's record says enforce
...; /etc/keel/instance.yaml cannot be read or parsed`, exit 14. In the
watch case with an intact file, the watch did not even load the table
again from the sound file.

With the spec unreadable or invalid and the copy restored, the node is
closed and correct, but `running`, the check exit 0, and the only signal
is one journal line at level warning. The task asks that the check fails
in these cases.

### With the last good copy lost

| Spec | File | Mode | Loaded after | Node, failed units | check | 9999 / 80 |
| --- | --- | --- | --- | --- | --- | --- |
| bad | empty, missing | watch | `keel-fallback` | degraded, `keel-firewall-watch.service` | 14 | timeout / timeout |
| bad | empty, missing | reboot | `keel-fallback` | degraded, both units | 14 | timeout / timeout |
| unread | missing | reboot | `keel-fallback` | degraded, both units | 14 | timeout / timeout |
| missing | missing | reboot, watch | **no table** | **running**, none | 14 | **open** / open |
| missing | intact | reboot | the full ruleset (drop-in) | running | 0 | timeout / open |

### A node in report (9403, log 15)

| Case | Observed |
| --- | --- |
| bad spec, empty file, watch, copy kept | the report copy restored (`policy accept`, counter `keel-report`), check exit 0, node `running`, 9999 `open` (report drops nothing) |
| bad spec, missing file, reboot | the same, by the boot unit |
| unread spec, empty file, reboot | the same |
| missing spec, missing file, reboot | no table; check exit 14; 0 keel lines; `running` |

The copy keeps the report node in report, which drops nothing anyway.
It is not the "loud failure, nothing loaded" that the task asks for.

## Item 2: `state: off` (PASS)

9404 (log 20).

| Case | Observed |
| --- | --- |
| 2a. A comment `# old note: firewall state: off ...` added (`keel spec validate` exit 0), file removed, table deleted | the watch restored the copy 28 s later, `policy drop`, 9999 `timeout` from outside |
| 2b. `firewall: {state: off}` under `appliance`, under `tls`, or a top-level `x_note: "firewall state: off"` | `keel spec validate` and the apply: `unknown key` / `unknown top level key`, exit 3; record `enforce`, `policy drop` unchanged |
| 2c. The real `firewall: {state: "off"}`, apply | `off in the spec ...`, `remove ... keel-manifest.nft ...: done`, `record ...: off, so the watch knows it from a file of keel's ...: done`, `remove keel's table ...: done`. Record `off`; 9999 and 80 `open` from outside |
| 2d. Off, watch 40 s | 0 lines; no table |
| 2e. Off, `pct reboot` | no table, node `running`, no failed unit |
| 2f. Off, the spec then made invalid, `pct reboot` | no table; check: `no ruleset of keel's, nothing to compare`, exit 0. The copy (still `enforce`, from before off) was **not** loaded |
| 2g. `firewall: {state: enforce}`, apply (listener up) | `write ... (enforce)`, `load it ...`, `record ...: enforce`; `policy drop` |
| 2h. Then file removed, table deleted | the watch restored the copy 29 s later, `policy drop`, 9999 `timeout` |

Note: after off, the copy of the enforce time stays on disk. It was not
loaded in 2d to 2f (the record `off` and the spec decide).

## Item 3: the last good copy (FAIL in part)

9404 (logs 30, 31, 52 on 9405).

| Case | Observed |
| --- | --- |
| 3a. `allow` TCP 8080 added, a directory in place of the ruleset file, apply | apply exit 16 (`write ...: failed`); the copy unchanged (same sha256, no 8080). The directory removed, apply: `keep ... last-good.nft ...: done`; 8080 in the copy, root 0600 |
| 3d. Stale copy: 8080 removed from the spec and applied (copy without 8080), then the copy of the 8080 time put back (root 0600), file removed, table deleted | the watch: `restored from keel's last good copy`; loaded `tcp dport 8080 accept`; **TCP 8080 `open` from CT 9400** (a test listener), both families; check: `table inet keel is the one ... says`, **exit 0**; node `running`; watch silent after that. Only `keel diff`: `derived.firewall: drift (... observed a file that differs from it)`, exit 14. Still loaded 1.5 min later; removed only by the next apply |

Hygiene (`copyh.sh`): the break, then the spec made invalid (so the step
of the apply cannot run), file removed, table deleted, 45 s; then the spec
back and an apply.

| Case | Loaded after the break | After the apply |
| --- | --- | --- |
| h0. Sound copy, root 0600 (control) | `keel-manifest ...` (copy restored) | unchanged |
| h1. Copy a symlink to a sound report ruleset | `keel-fallback`, node degraded | regular file, root 0600 |
| h2. Copy owned by `nobody` | `keel-fallback` | root 0600 |
| h3. Copy 0666 | `keel-fallback` | root 0600 |
| h4. Directory owned by `nobody` | `keel-fallback` | directory root 0700 (plan: `... state is not trusted (its directory is not trusted ...)`) |
| h5b. The user `nobody` (owner of the directory) puts a sound report ruleset as the copy (`-rw-r--r-- nobody`) | `keel-fallback`: not loaded | root 0600, the enforce ruleset |
| h6. Copy cut to 300 bytes | `keel-fallback` | root 0600 |
| h7. Copy with `{ 22,` changed to `{ 2222,` | `keel-fallback` | root 0600 |
| h8. A sound **report** ruleset as the copy, root 0600, record `enforce` | **`policy accept`**, `restored from keel's last good copy`, node `running` | the enforce ruleset again |

(h5 is void in log 31: `nobody` could not read the source file; h5b is
the run.) No half ruleset was loaded in any case. h8 needs root; it shows
that the repair does not compare the copy with the record. A copy that is
not the last ruleset can come from a failed copy write after a load (read
from the code: the copy is written after the record).

Directory group: after `own_directory()` the directory of 9405 was
`root:nogroup` 0700 (the owner is set, the group is kept). With mode 0700
the group has no access.

`apt-get remove -y keel` (log 52, 13 packages removed): `last-good.nft`
and `state` kept. `apt-get purge -y keel`: `/var/lib/keel/firewall` gone.
The ruleset file `/etc/keel/firewall/keel-manifest.nft` stays.

## Item 4: an apply after a boot in the fallback (PASS, with a note)

9402 (log 40): spec invalid, copy removed, file emptied, `pct reboot`:
`degraded`, failed `keel-firewall-watch.service` and
`keel-firewall.service`, `keel-fallback`. The spec back, apply: `write`,
`load`, `keep`, `restart keel-firewall.service, failed since the boot
...: done`, exit 0.

| After the apply | Node | `keel-firewall.service` | Watch service |
| --- | --- | --- | --- |
| +0, +10, +20 s | degraded | active | failed |
| +30, +40 s | running | active | inactive |

The boot unit is cleared at once; the watch clears its own failure at its
next run.

## Item 5: record directory of another user and an empty file at boot (PASS)

9405 in enforce, listener up; directory chowned to `nobody`, file emptied,
`pct reboot` (log 50). The boot unit: `Error: derived.firewall: NOT
APPLIED, the node keeps the firewall it has: keel's record is not trusted
and the ruleset file is broken ...`, then `the closed fallback table is
loaded (drop; sshd's ports 22) ...`. 40 s after the reboot: the full
enforce ruleset (the watch wrote it), directory root 0700, node `running`;
from outside 9999 `timeout`, 22 and 80 `open`. No move to report.

## Item 6: the pair (PASS)

The trio after its first apply, all in enforce (log 60).

| Case | Observed |
| --- | --- |
| 6a-2. Standby 9420, spec valid, copy kept, file removed, table deleted | the watch restored the copy 30 s later, node `running` |
| Failover to it: `pct shutdown 9421` | VIP on 9420 **22.6 s** after the shutdown started; `read_only` 0, a row written; 9421 replicated again 71 s after its start |
| From CT 9400 to 9420 | TCP 80 and 443 `open`, `https` 200, 9999 `timeout`, both families |
| 6b. Standby 9421, copy removed, a directory in place of the file | fallback after 17 s: `tcp dport 22`, `udp dport 51820`, `iifname "wg0" accept`; degraded |
| Failover to it: `pct shutdown 9420` | VIP on 9421 **22.3 s** after the shutdown started; `read_only` 0; `https://localhost/` 200 on the node; from CT 9400 TCP 22 `open`, **TCP 80 and 443 `timeout`** (the limit as the PR writes it); 9420 replicated again 71 s after its start |
| Restore | the directory removed, apply: full ruleset, node `running` |

Void run, kept in the log (6a): to force the copy path, the spec of the
standby 9421 was first made invalid. The copy was restored, but at the
failover (`pct shutdown 9420`, 05:40:51) the VIP never came to 9421 in
120 s; `keel-vip-check`, `keel-mesh-etcd` and `keel-mesh-sync` failed
with `vip: /etc/keel/instance.yaml: not valid YAML`; 9421 stayed
`read_only` 1. 9420, started again, rejoined as a replica of 9421, so the
pair had no writer from 05:40:51 until the spec of 9421 was put back
(05:49:16; VIP on 9421 at the next check, 05:50:24). This is not a
firewall result, but a spec that does not parse also stops the failover.

## Item 7: regression (PASS)

| Check | Observed |
| --- | --- |
| Upgrade 9401 (simple) | 8 systemd reloads, no rule, `inet filter` only. 12 min with no reboot, then `pct reboot`, 6 min more: `running`, 0 failed, 0 keel lines, check `NOT APPLIED ...` exit 0 (log 70) |
| Upgrade 9420 to 9422 (cloud_advanced) | no rule (`inet filter`, CrowdSec's tables); 10 min: `running`, 0 failed, 0 keel lines, `NOT APPLIED`, exit 0 (log 22) |
| New node 9405, first boot with the test package, no apply | `keel-firewall.service` `active`, `running`, 0 failed, 0 keel lines, `inet filter`, `NOT APPLIED`, exit 0; still so at 10 min (log 61) |
| First applies | 9401, 9402, 9405, 9406 and the trio: `enforce: each socket ... (decision 0097, B)`; 9403 with the listener: `report: enforce waits ...` |
| lnmp simple probe table (9401, listener up, 4 rows each) | TCP and UDP 9999 `timeout`; TCP 22, 80, 443, 12321 `open`; UDP 12321 `timeout`; TCP 3306 `timeout` (log 71) |
| Busy invite and join under enforce (log 73) | the inviter 9420 holds the apply lock: `the inviter refused the join: busy: ...`, exit 24 after 7.5 s; `invite ...: busy: ...; the invite stays`; `expired unused`: 0; the same line after the lock: `joined the mesh`, exit 0 after 6 s; 9406 `policy drop`, file and record `enforce` |
| Watch CPU, 1 core (9401 after `pct reboot` with `--cores 1`, `nproc` 1; log 72) | shell path: 36.7, 33.6, 44.0 ms a run and more in the log; test 5: 32 to 48 ms. Repair path (file emptied): 553 and 675 ms (test 5: 884 to 1026 ms) |

Note: `pct set --cores 1` did not take effect on the running CT (the
first 6 runs had `nproc` 2); the values above are after a reboot.

## Item 8: one more way to leave a node in enforce open or silent

Tested by action:

1. **A missing spec** (item 1): both firewall units are skipped; with the
   table lost the node is open, `running`, with no line.
2. **X4, a dangling symlink in place of the spec** (log 80, 9402): the
   same: no table after 45 s, `running`, 0 watch lines, check exit 14,
   TCP 9999 `open` from outside.
3. **X2, a record `off` written by an unprivileged user** (log 80, 9404):
   keel's directory owned by `nobody` (the case of test 5), the user
   `nobody` replaces `state` with `off` (`-rw-r--r-- nobody`), file
   removed, table deleted. 70 s later: no table, `running`, 0 failed, 0
   watch lines; TCP 9999 `open`, UDP 9999 `reply` from outside. The
   watch's shell reads the record with `cat` and no trust check
   (`firewall/firewall-watch`, read from the code). `keel firewall check`
   still says exit 14 (Python treats the record as not trusted). A boot
   would repair (read from the code, not tested).
4. **A copy that differs from the spec** (item 3, 3d and h8): the repair
   loads it with no signal; a removed port opens again, or the node goes
   to report.
5. Also seen: an apply by a person ran at the same moment as a repair of
   the watch; the apply said `write ... failed` and `0 change(s), 1
   failed`, the watch's repair succeeded (log 31, h7; 05:25:50). The
   repair does not take the apply's lock (read from the code: no lock in
   `fwrepair`).
6. Not found: X1, a spec that parses but has an unknown key (log 80):
   the watch's repair wrote the enforce ruleset from it (the validator
   is not used); closed. X3, an empty spec file: the copy was restored;
   closed.

## Against the fifth test

| Fifth test (head `478f0c0`) | This test (head `e12665d`) |
| --- | --- |
| An invalid spec turned off the repair; open and silent after a reboot | an invalid or unreadable spec: copy or fallback, never open. New: a missing spec still turns off both units |
| `state: off` in a comment silenced the watch | the watch reads `off` from the record; a comment has no effect. New: a record `off` that an unprivileged user writes silences it |
| A record directory of another user was never put right; empty file at boot gave report | put right by the next write; at boot NOT APPLIED and the fallback |
| The boot unit stayed failed after an apply | restarted by the apply |
| (no copy) | the copy keeps declared ports open; a stale or report copy is loaded with no signal |

## What was not tested

- The ISO, two sites with netem, image builds, the other images.
- A reboot in case X2 (the boot repair, read from the code only).
- A copy write that fails after a successful load (the way a stale copy
  comes by itself).
- Monit's `keel-firewall` check (only with `monitor.enabled`).

## Logs

On the maintainer's workstation in
`repos/evidence-0097-2026-11-23/pr307-run6/`. The runner records
(`runner-adv/`) hold console transcripts and are not copied here.

| Log | Content |
| --- | --- |
| `05-api-before`, `97-api-after` | head and CI state |
| `00-vm-baseline`, `99-vm-after`, `99-vm-diff`, `99-cleanup` | the VM before and after |
| `01-images`, `02-create-simple`, `04-push`, `20-adv-runner`, `10-upgrade-94NN`, `21-upgrade-942N`, `12-setup`, `41-cloud-apply` | templates, CTs, upgrades, first applies |
| `13-item1`, `14-item1-nocopy`, `15-item1-report` | item 1 |
| `20-item2-off` | item 2 |
| `30-item3-copy`, `31-item3-hygiene`, `52-item3-remove-purge` | item 3 |
| `40-item4` | item 4 |
| `50-item5` | item 5 |
| `60-item6-pair` | item 6 |
| `60-new-node`, `61-new-window`, `70-item7-window`, `22-item7-window-cloud`, `71-item7-probe`, `72-item7-cpu`, `73-item7-join` | item 7 |
| `80-extra` | X1 to X4 |
| `98-secret-scan` | secret scan |

Secret handling: node secrets were made inside each stopped CT and never
printed. The spec was moved or copied with `cp -a`, never printed. Join
lines stayed in shell variables and went to the joiner by standard input.
Every `.log`, `.out`, `.txt`, `.tsv` and `.md` file under `pr307-run6/`
was scrubbed of WireGuard public keys, join and accept lines
(`scrub.sed`), and each control or non-ASCII byte was replaced by `?`.
The scan of log 98 over 123 files found no key, no join or accept line, no
private key and no token. The 4 `keel2:` hits are sed patterns in the
scripts. The 3 `password` hits are screen control codes after the
`password:` prompt in the console transcripts (5 lines). The same 8
patterns over this file: 2 lines with the word `keel2:`, in this
paragraph; no key, no join line, no password, no token.

## Cleanup

CTs 9400 to 9406 and 9420 to 9422 were destroyed with `pct destroy
--purge`. The templates `ev307r6-*` and `/root/ev307r6` were removed; the
templates that were on the VM before were not touched. The Proxmox
firewall is `disabled/running` and `/etc/pve/firewall` is empty, as
before. The diff of the VM state before and after, without counters,
time stamps and veth peer indexes, is empty: `diff_exit=0 lines=0` (log
99). The runner worktree `worktrees/runner-ev307r6` was removed.
