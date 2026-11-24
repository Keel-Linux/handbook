# Evidence: seventh real-node test of keel pull request 307, the firewall in every mode (decision 0097)

Date: 2026-11-24. Site: BR1, the BR1 test VM (nested Proxmox VE).
Status: draft. For decision 0097 (accepted), section D, and for `keel`
pull request 307.

## Question

The sixth test (`evidence/2026-11-24-keel-307-firewall-real-test-6.md`,
head `e12665d`) found: a missing spec skipped both firewall units (open
and silent); the check passed while a restored copy hid a spec that did
not parse; a stale or report copy was restored with no signal; a record
`off` written by an unprivileged owner of keel's directory silenced the
watch; an apply failed while the watch repaired. One new commit says that
it corrects this:

- `fde4f7f`: the firewall units run with or without a spec; the copy is
  restored only when its sha256 is the one keel's record holds; the
  watch's shell trusts the record only as root's 0600 file in a 0700
  directory, else it goes to Python; the check fails while the spec does
  not parse; one lock (`/run/keel/firewall.lock`) for the apply and the
  repair; a successful apply clears a failed watch unit.

The method and the probes are those of the sixth test. A failure is a
result. No code was changed. Each statement below was tested by action,
unless it says "read from the code". Files that root plants against its
own node are outside the threat model; they are shown at most once and
not counted as failures.

## Tested head and package

- Tested head `fde4f7f8d28824c7ebba5bf25b4435aa07aaa0c3`. The Forgejo API
  gave the same head before the run (06:38 UTC) and after it (07:39 UTC),
  combined CI state `success` (13 contexts) both times. Version 0.23.99.
- `keel_0.23.99_all.deb`, sha256
  `f244d24d35ac7c869d6a71f27021dca35a0b12822f24cf65b15c1f05c0ac94ee`,
  built from `git archive fde4f7f` with `dpkg-buildpackage -us -uc -b`,
  `SOURCE_DATE_EPOCH=1795501071`, debhelper 13.24.2,
  `PATH=/usr/sbin:/usr/bin:/sbin:/bin`. For item 3 also the package of
  the sixth test (head `e12665d`, sha256 `722c9ba2...ba2a`). Installed
  with `dpkg -i` after `pct push` only; no repository, no mirror.

## Machines

Unprivileged CTs, `nesting=1`, 2 cores (9401 set to 1 core and rebooted
for the CPU cost), bridge `vmbr1`, DHCPv4 and DHCPv6. Templates lnmp
19.0-7 and core 19.0-13, as in the sixth test (`sqv` exit 0, the same
sha256). Each image has keel 0.23.96.

| CT | Image | Mode | Use |
| --- | --- | --- | --- |
| 9400 | core | simple | probe node, keel 0.23.96 kept |
| 9401 | lnmp | simple | item 7 (upgrade window, rule B, probe table), item 4 (CPU) |
| 9402 | lnmp | simple | items 1 and 2 (enforce) |
| 9403 | lnmp | simple | item 2 (a node in report) |
| 9404 | lnmp | simple | items 3 and 4; item 7 (off, then enforce) |
| 9405 | lnmp | simple | item 7 (new node); item 3 (record of `e12665d`) |
| 9406 | core | simple | item 7, the joiner |
| 9407 | lnmp | simple | items 5 and 6; item 8 (faults) |
| 9420, 9421, 9422 | lnmp, lnmp, core witness | cloud_advanced | `keel-commission --pass cloud_advanced`: PASS, 117 checks; item 7 |

Every node except 9400 and 9405 went to the published keel 0.23.97,
then to the test package (`upgrade97.sh`: 8 systemd reloads, no rule on
each). 9405 was made with `inithooks.service` masked and got the test
package before any apply. "Listener": the units `ev-tcp` and `ev-udp`
(TCP and UDP 9999, enabled, no manifest declares them). The probes run
from CT 9400 on IPv6 and IPv4.

## Summary

| Item | Result | Key facts |
| --- | --- | --- |
| 1. Missing or dangling spec, table lost | **PASS**, with a note | All 12 cases (missing, dangling; file sound, empty, missing; watch, reboot) and 2 with the copy lost: the units ran, the node closed (full ruleset from the file or the copy, else the fallback), 9999 `timeout` from outside, check exit 14, the watch unit failed. The spec put back: the watch cases cleared by themselves (`running`, check 0). In the 4 reboot cases with an empty or missing file, `keel-firewall.service` stayed failed until an apply (the apply cleared it) |
| 2. Spec that does not parse, copy restored | **PASS** | Enforce: the full last ruleset, check exit 14, `degraded`; the report node: the report copy, check 14, `degraded` (loud). The spec back: clears; after a reboot case an apply clears the boot unit |
| 3. Copy bound to the record hash | **PASS** | Old copy, report copy, one byte changed, a newline added, record with a zero hash, with no hash, with 63 digits, and a record written by `e12665d`: never restored; the fallback, check 14. Power cut (copy new, record old): file sound loads; file empty with a sound spec: the step writes it; with a spec that does not parse: the fallback. After each normal apply the record hash was the copy's |
| 4. Record trust in the shell watch | **PASS** | Directory of `nobody` with a planted `off`, a symlinked record, a 0660 record: the watch went to Python; the node closed (fallback, or the full ruleset), loud where the record was not trusted, and the directory put right. Watch CPU on 1 core: 31 to 49 ms a run (test 6: 34 to 44 ms) |
| 5. Apply after a fallback boot | **PASS** | `running` with no failed unit at +0 s after the apply (it took 7.5 s); the apply restarted the boot unit and cleared the watch unit |
| 6. Lock | **PASS** | 20 applies beside a loop that broke the file every 3 s and ran the watch's script: 0 failed, 1.6 to 2.3 s each. A lock holder killed with -9: the next apply took 2.0 s. A holder for 100 s: an apply waited 19 s and passed; with the file broken the node was open but `degraded` while the holder held |
| 7. Regression | **PASS** | Upgrade 9401 and the trio: NOT APPLIED, silent, `running`, 10 min. New node: the same. Rule B: report with the listener, enforce without. Probe table as before. Failover under enforce: VIP 32.1 s. Busy invite kept, the same line joined (6 s). Real `off`: record `off`, no table; `state: enforce` again: record and copy agree, `policy drop` |
| 8. One more way | **found** | A fault: with keel's state directory read-only, an apply that removed a port failed (exit 16, the copy not written); after a later loss of the file the repair restored the old copy and the **removed port was open again from outside**, check exit 0, `running`. Also: on a full disk an apply that could not write the ruleset said `not done` but exit 0 |

## Item 1: a missing spec or a dangling symlink in its place (PASS, with a note)

`case1.sh` on 9402 (enforce, listener up), logs 13 and 14. Watch mode:
the table is also deleted, then 45 s with only the watch. Reboot mode:
`pct reboot`, then 40 s. Then the spec is put back alone and the node is
read again after 40 s; then an apply.

| Spec | File | Mode | After the break | Spec back only, 40 s | After an apply |
| --- | --- | --- | --- | --- | --- |
| missing, dangling | sound, empty, missing | watch | `keel-manifest a08b...` (from the file or the copy), check 14, `degraded`, the watch unit failed, 9999 `timeout` | `running`, check 0 | `running` |
| missing, dangling | sound | reboot | the full ruleset, check 14, `degraded` | `running`, check 0 | `running` |
| missing, dangling | empty, missing | reboot | the full ruleset (the boot unit restored the copy), check 14, `degraded`, both units failed | **`degraded`** (boot unit still failed), check 0 | `running` |
| missing, copy lost | missing | reboot | `keel-fallback`, check 14, both units failed | `running` (the watch wrote the file), check 0 | `running` |
| dangling, copy lost | empty | watch | `keel-fallback`, check 14, `degraded` | `running`, check 0 | `running` |

The journal line: `Error: table inet keel is the one ... says; but
/etc/keel/instance.yaml cannot be read or parsed: the node keeps the
ruleset of its last apply, and this stays a failure until the spec is
put right and keel spec apply --system runs`. One sample in the dangling,
missing, watch case said `running` while the watch unit was activating;
the journal has the error. The text says an apply is needed; in the watch
cases it is not; in the reboot cases with a broken file it is (or
`systemctl reset-failed`).

## Item 2: a spec that does not parse, the copy restored (PASS)

Logs 16 (9402, enforce) and 17 (9403, report).

| Node | Case | After | Spec back |
| --- | --- | --- | --- |
| enforce | bad spec, empty file, watch | the full ruleset, check 14 (one sample `running` while the unit was activating) | `running`, check 0 |
| enforce | bad spec, missing file, reboot | full ruleset, check 14, `degraded` | `running` |
| enforce | unreadable spec (a directory), empty file, reboot | full ruleset, check 14, both units failed | `degraded` until the apply |
| report | bad spec, empty file, watch | the report copy (`policy accept`), check 14, `degraded` | `running` |
| report | bad spec, missing file, reboot | the same, both units failed | `degraded` until the apply |
| report | missing spec, missing file, reboot | the same | `degraded` until the apply |
| report | dangling spec, empty file, watch | the same, the watch failed | `running` |

## Item 3: the copy bound to the record hash (PASS)

`copybind.sh` on 9404 (log 31): the break, then the spec made invalid (so
only the copy or the fallback can act), file removed, table deleted, 45 s;
then the spec back and an apply.

| Case | Loaded | Node, check |
| --- | --- | --- |
| c0. The copy of the last apply (control) | the full ruleset | `degraded`, 14 (the spec) |
| c1. Old copy (8080, removed from the spec since) | `keel-fallback` | `degraded`, 14; `... last-good.nft is not the ruleset of the last apply (its hash is not the one keel's record holds): it is not restored` |
| c2. A sound report copy, root 0600 | `keel-fallback` | 14 |
| c3c. One byte changed on line 2 (a comment) | `keel-fallback` | 14 |
| c3b. A newline added at the end | `keel-fallback` | 14 |
| c4. Record with a hash of 64 zeros | `keel-fallback` | 14 |
| c5. Record with no hash | `keel-fallback` | 14 |
| c6. Record with 63 hex digits | `keel-fallback` | 14; plan of the next apply: `... state is not trusted (it is not a state keel writes)` |
| c7. Record written by `e12665d` (9405, log 33: `e12665d` installed, apply, record `enforce`; the test package installed, no apply) | `keel-fallback` | journal: `... last-good.nft is n(ot) ...`; the spec back: the watch wrote the file and the record `enforce <hash>`, no apply |

(c3 in the log is void: line 1 holds no `keel`, so the copy did not
change; c3c is the run.) After each apply the record hash was the hash of
the copy (`record hash = copy hash: yes`).

Power cut (log 32): 8080 allowed and applied (copy and record with 8080),
then the record of before put back (copy new, record old), `pct reboot`:

| File | Spec | At boot | 8080 from outside |
| --- | --- | --- | --- |
| sound | sound | the file loads (`keel-manifest a248...`), `running`, check 0 | open (declared) |
| empty | sound | the step writes the file from the spec, `running` | open (declared) |
| empty | does not parse | `... last-good.nft is not the ruleset of the last apply ...: it is not restored`, then the fallback; both units failed | timeout |

No case was found where a healthy node fails to restore its own copy
after a normal apply. A node whose record was written by an older keel
(no hash) gets the fallback until its next apply or repair writes the
hash (c7).

## Item 4: record trust in the shell watch (PASS)

9404 (log 40), file removed and table deleted, watch only.

| Case | Observed |
| --- | --- |
| t1. Directory of `nobody`; `nobody` replaces the record with `off` | sampled each 10 s: +10 s no table (the watch had not run yet), +20 to +50 s `keel-fallback`, `degraded`, the watch failed (`NOT APPLIED, the node keeps the firewall it has: keel's record is not trusted ...`), +60 s the full ruleset, the directory root 0700, `running`; 9999 `timeout` from outside |
| t2. The record a symlink to a file that says `off` | the full ruleset, 9999 `timeout` |
| t3. The record 0660 | the full ruleset, 9999 `timeout` |
| t4. Root plants `off`, 0600 (outside the threat model) | silent, no table, 9999 `open`; the next apply with the listener went to report (rule B, the record says off). Shown only |

Watch CPU on 1 core, the normal case (9401, `nproc` 1, log 72): 31.0,
37.9, 39.4, 35.4, 35.9, 39.5, 48.5, 35.7 ms a run. Test 6: 34 to 44 ms.

## Item 5: apply after a fallback boot (PASS)

9407 (log 45): spec invalid, copy removed, file emptied, `pct reboot`:
`degraded`, both units failed, `keel-fallback`. The spec back, apply
(7.5 s): `write`, `load`, `keep`, `restart keel-firewall.service, failed
since the boot ...`, `clear keel-firewall-watch.service ...`. At +0, +1,
+2, +5, +10 and +30 s: `running`, no failed unit.

## Item 6: one lock (PASS)

9407 (logs 50, 51).

| Case | Observed |
| --- | --- |
| `lockloop.sh`: 20 applies; beside them a loop that empties the file every 3 s and runs `/usr/lib/keel/firewall-watch` | 20 of 20 exit 0, 1.6 to 2.3 s each; 10 runs of the watch's script, all exit 0; 0 `skips its run` lines; at the end enforce, `policy drop`, `running`, check 0 |
| A kill -9 of `keel spec apply` after 1.2, 1.6, 2.0 s | the next apply exit 0 in 1.6 to 1.7 s; a repair by the watch's script exit 0 in 0.5 to 0.6 s |
| `holdfw.py`, which takes the lock with `fwlock.held`, killed with -9 | the next apply exit 0 in 2.0 s |
| `holdfw.py 100` (a hung apply), table deleted | the table came back from the sound file 20 s later (that path needs no lock); an apply during the hold waited 19.3 s and passed |
| `holdfw.py 100`, file emptied and table deleted | while held: no table (9999 `refused` from outside: no drop, no listener on 9407), `degraded`, the watch failed: `... an apply holds the firewall lock: this repair skips its run ...`; after the release the full ruleset, `running` |

The 120 s wait was never reached; the longest wait seen was 19.3 s, with
a holder held on purpose.

## Item 7: regression (PASS)

| Check | Observed |
| --- | --- |
| Upgrade 9401 | 10 min: `running`, 0 failed, 0 keel lines, `inet filter`, `NOT APPLIED ...`, exit 0 (log 70); then a reboot (1 core): the same |
| Upgrade 9420 to 9422 | 10 min: the same, with CrowdSec's tables (log 22) |
| New node 9405 | first boot with the test package, no apply, 9 min: `keel-firewall.service` active, `running`, 0 keel lines, `NOT APPLIED`, exit 0 (log 61) |
| Rule B (9401) | the listener up: `report: enforce waits ...`; stopped: `enforce: each socket ...` |
| Probe table (9401, 4 rows each) | TCP and UDP 9999 `timeout`; TCP 22, 80, 443, 12321 `open`; UDP 12321 and TCP 3306 `timeout` (log 71) |
| Failover under enforce (log 42) | `pct shutdown 9420`: VIP on 9421 32.1 s after the shutdown started; 9420 replicated again 70 s after its start (`rejoined: no errant GTID ...`) |
| Mesh (log 43) | the inviter holds the apply lock: `busy`, exit 24 after 7.5 s; `the invite stays`; `expired unused` 0; the same line: `joined the mesh`, exit 0 after 6 s; 9406 `policy drop`, record `enforce <hash>` |
| `off`, then enforce (9404, log 44) | `record ...: off ...`, `remove keel's table ...`; 35 s: no table, `running`. `state: enforce`: `write`, `load`, `record ...: enforce and the hash ...`; record hash = copy hash; 9999 `timeout`, 80 `open` |

## Item 8: one more way to leave a node in enforce open or silent

Tested by action, on 9407 (log 80):

1. **Read-only state directory (a fault), then the file lost: a removed
   port opens again.** 8080 allowed and applied (copy and record with
   8080). Then `/var/lib/keel/firewall` read-only (a read-only bind
   mount), 8080 removed from the spec, apply: `keep ... failed: the last
   good copy cannot be written: Read-only file system`, `2 change(s), 1
   failed`, exit 16; the loaded table has no 8080. The record was not
   written either, so record and copy still agree on the old ruleset. The
   file then emptied and the table deleted: the watch restored the copy;
   **TCP 8080 `open` from CT 9400** on both families, node `running`, no
   failed unit, check exit 0, still so 1 min later; only `keel diff` saw a
   drift. The apply that failed was loud once (exit 16). The other way
   (a port added, then the fault) closed the new port again in the same
   silent way.
2. **Full disk: an apply says `not done` with exit 0.** The root file
   system filled (`fallocate`, `dd`), 8080 added to the spec, apply:
   `write ... keel-manifest.nft ...: not done ...`, `0 change(s), 0
   failed`, exit 0; nothing changed (closed side). With the disk still
   full, file emptied and table deleted: `keel's last good copy is not
   restored: No space left on device`, then the fallback, `degraded`,
   check 14. Disk freed: the watch wrote the full ruleset.
3. A package upgrade of nftables (`apt-get install --reinstall
   nftables`): `nftables.service` restarted; `fastprobe` saw TCP 9999
   `open` for one round (about 0.15 s, 07:35:24.707 to .858), then
   `timeout`: the drop-in loads keel's file after the restart, as the PR
   says.
4. An unprivileged user (`nobody`): `/run/keel/firewall.lock`, the
   record, the ruleset file: `Permission denied`; `/run/keel`,
   `/var/lib/keel/firewall`, `/etc/keel/firewall`: not writable. The
   watch's mark (`/run/keel/firewall-watch.ok`, 0644) can be opened and
   locked; that has no effect on the watch (read from the code: the shell
   only reads it). Nothing found.
5. A hung apply that holds the lock (item 6): open while it holds, but
   loud.
6. Not tested: a clock change (an unprivileged CT cannot set the time); a
   half-done package removal.

Test slip, kept in log 80: while the disk was full, a copy of the spec
came out empty and was copied back; the spec was then put back from the
copy of item 5 and the apply passed.

## Against the sixth test

| Sixth test (head `e12665d`) | This test (head `fde4f7f`) |
| --- | --- |
| A missing spec skipped both units: open and silent | the units run; closed and loud |
| Check exit 0 while a copy hid a spec that does not parse | check 14, `degraded` |
| A stale or report copy restored with no signal | not restored unless its hash is in the record. New: a failed apply on a read-only state directory leaves record and copy of the old ruleset, and a later repair restores it |
| A record `off` from an unprivileged owner of the directory silenced the watch | the shell goes to Python; closed, loud, put right |
| An apply failed while the watch repaired | one lock: 20 of 20 applies passed |

## What was not tested

- The ISO, two sites with netem, image builds, the other images.
- A real power cut (simulated by the record put back).
- A clock change; a half-done package removal.

## Logs

On the maintainer's workstation in
`repos/evidence-0097-2026-11-23/pr307-run7/`. The runner records
(`runner-adv/`) hold console transcripts and are not copied here.

| Log | Content |
| --- | --- |
| `05-api-before`, `97-api-after` | head and CI state |
| `00-vm-baseline`, `99-vm-after`, `99-vm-diff`, `99-cleanup` | the VM before and after |
| `01-images`, `02-create-simple`, `04-push`, `20-adv-runner`, `10-upgrade-94NN`, `21-upgrade-942N`, `12-setup`, `41-cloud-apply` | templates, CTs, upgrades, first applies |
| `13-item1`, `14-item1-nocopy` | item 1 |
| `16-item2`, `17-item2-report` | item 2 |
| `30-item3`, `31-item3-bind`, `32-item3-powercut`, `33-item3-oldrecord` | item 3 |
| `40-item4-trust`, `72-item7-cpu` | item 4 |
| `45-item5` | item 5 |
| `50-item6-lock`, `51-item6-kill` | item 6 |
| `60-new-node`, `61-new-window`, `70-item7-window`, `22-item7-window-cloud`, `71-item7-ruleB-probe`, `42-item7-failover`, `43-item7-join`, `44-item7-off` | item 7 |
| `80-extra` | item 8 |
| `98-secret-scan` | secret scan |

Secret handling: node secrets were made inside each stopped CT and never
printed. The spec was moved or copied, never printed. Join lines stayed
in shell variables and went to the joiner by standard input. Every
`.log`, `.out`, `.txt`, `.tsv` and `.md` file under `pr307-run7/` was
scrubbed (`scrub.sed`; control and non-ASCII bytes to `?`). The scan of
log 98 over 131 files found no key, no join or accept line, no private
key and no token. The 4 `keel2:` hits are sed patterns in the scripts.
The 3 `password` hits are screen control codes after the `password:`
prompt in the console transcripts (5 lines). The same 8 patterns over
this file: 2 lines with the word `keel2:`, in this paragraph; no key, no
join line, no password, no token.

## Cleanup

CTs 9400 to 9407 and 9420 to 9422 were destroyed with `pct destroy
--purge`. The templates `ev307r7-*` and `/root/ev307r7` were removed; the
templates that were on the VM before were not touched. The Proxmox
firewall is `disabled/running` and `/etc/pve/firewall` is empty, as
before. The diff of the VM state before and after, without counters,
time stamps and veth peer indexes, is empty: `diff_exit=0 lines=0` (log
99). The runner worktree `worktrees/runner-ev307r7` was removed.
