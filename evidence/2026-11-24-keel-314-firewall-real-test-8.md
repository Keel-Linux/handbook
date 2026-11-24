# Evidence: real-node test of keel pull request 314, the firewall's copy, record and boot unit (keel#308, #309, #310)

Date: 2026-11-24. Site: BR1, the BR1 test VM (nested Proxmox VE).
Status: draft. For decision 0097 (accepted) and for `keel` pull request
314. This is the eighth real test of the firewall of decision 0097; the
seventh is `evidence/2026-11-24-keel-307-firewall-real-test-7.md`.

## Question

Pull request 307 is merged (keel main `f938037`, 0.23.99). The seventh
test found that a read-only state directory let an old copy reopen a
removed port, and that a full disk gave `not done` with exit 0. Pull
request 314 (keel 0.23.100) says:

- keel#308: the apply writes the last good copy and the record (with the
  hash of the new ruleset) before the ruleset file and its load; where
  the state directory cannot be written, no rule changes and the apply
  fails.
- keel#309: a ruleset that cannot be written fails the apply (exit not
  0).
- keel#310: a good run of the watch restarts a `keel-firewall.service`
  that failed at boot.

The method and the probes are those of the seventh test. A failure is a
result. No code was changed. Each statement was tested by action unless
it says "simulated" or "read from the code". Root acting against its own
node is outside the threat model.

## Tested head and packages

- Tested head `a13d73cdcec9da12ca91bd45d6bb40f3d3907219` (commits
  `3fe3bf5`, `40379f9`, `a13d73c` after main `f938037`). The Forgejo API
  gave the same head before the run (08:19 UTC) and after it (09:05 UTC),
  combined CI state `success` (13 contexts) both times.
- `keel_0.23.100_all.deb`, sha256
  `13e5e9e6e68ea908785cb7a5f13aba89dd37c8b60459efdc5e6e418c8e7a36eb`,
  from `git archive a13d73c`, `dpkg-buildpackage -us -uc -b`,
  `SOURCE_DATE_EPOCH=1795506655`, debhelper 13.24.2.
- For the upgrade from main: `keel_0.23.99_all.deb` from `git archive
  f938037`, sha256
  `081004a42c5fd78570d09c500d94cd60627ae3f4e0f0c280111fd6ceb81e563f`.
- Both built with `PATH=/usr/sbin:/usr/bin:/sbin:/bin`, installed with
  `dpkg -i` after `pct push` only; no repository, no mirror.

## Machines

Unprivileged CTs, `nesting=1`, 2 cores (9401 set to 1 core and rebooted
for the CPU cost), bridge `vmbr1`, DHCPv4 and DHCPv6. Templates lnmp
19.0-7 and core 19.0-13 (`sqv` exit 0, the same sha256 as in the seventh
test), keel 0.23.96 in each image.

| CT | Use |
| --- | --- |
| 9400 (core) | probe node |
| 9401 (lnmp) | item 5: upgrade 0.23.97 to 0.23.100, enforce, probe table, CPU |
| 9402 (lnmp) | items 1 and 2: the fault orders |
| 9403 (lnmp) | item 3 (keel#310); item 6 (faults) |
| 9404 (lnmp) | item 4: kill -9 of the apply, then a reboot |
| 9405 (lnmp) | item 5: main 0.23.99 in enforce, then 0.23.100 |
| 9406 (lnmp) | item 6: `dpkg` killed during the upgrade |
| 9420, 9421, 9422 (lnmp, lnmp, core witness) | cloud_advanced, `keel-commission --pass cloud_advanced`: PASS, 117 checks; item 5 |

9401 to 9404, 9406 and the trio went to the published keel 0.23.97,
then to 0.23.100 (`upgrade97.sh`: 8 systemd reloads, no rule). On 9402
to 9404 the test spec `s8` allows TCP 8080 (`firewall.allow`), a unit
`ev-8080` listens on TCP 8080, and the spec `s0` is the same without
8080. "Removes a port" means an apply of `s0` on a node where `s8` was
applied.

## Summary

| Item | Result | Key facts |
| --- | --- | --- |
| 1. keel#308, the fault orders | **PASS**, with notes | State directory read-only or full (real: a read-only bind mount; a filled tmpfs of 8 KiB): the copy fails, apply exit 16, `0 change(s), 1 failed`, no rule changes: **TCP 8080 still answers from outside, the intended state**. Ruleset file lost: the repair restores the 8080 ruleset, the last complete apply. Fault removed, apply: 8080 `timeout`, all clear. Copy written and record not (simulated): the copy is not restored; the step or the fallback. Copy and record written, ruleset file not (real: read-only bind mount; filled tmpfs): exit 16, 8080 still answers; after a loss of the file the repair restores the **new** copy (8080 closed), as the PR says. The load fails (simulated with a failing `nft` in PATH): **apply exit 0**, check exit 14. Notes: after a failed apply, `keel firewall check` stays 0 and the node `running`; only the apply's exit and lines tell. The immutable flag cannot be set in an unprivileged CT (`chattr` absent) |
| 2. keel#309, ruleset path full | **PASS** | `/etc/keel/firewall` on a filled tmpfs of 4 KiB: `write ...: not done: No space left on device`, `2 change(s), 1 failed`, exit 16; the node stays closed (old ruleset, 9999 `timeout`) |
| 3. keel#310, the spec back after a boot with no spec | **PASS** | Empty and missing file: at boot the copy restored (full ruleset), `degraded`, check 14. The spec put back, no apply: `running` again 33 to 34 s later, at the next watch run (`keel-firewall.service restarted: it failed at boot, and the ruleset is sound now`); the ruleset is the full one (`keel-manifest a08b...`) |
| 4. Power cut at each step (kill -9, then reboot) | **PASS** | Killed after the copy, after the record, after the file: never open; after copy and after record the node boots on the old ruleset (8080 still answers) with no failure shown, and needs an apply; after the file it boots on the new ruleset with no apply |
| 5. Regression | **PASS** | Upgrade 0.23.97 to 0.23.100: NOT APPLIED, silent, `running` (9401 17 min, the trio 10 min). Upgrade main 0.23.99 (enforce) to 0.23.100 on 9405: no gap (`fastprobe` 50 s, 9999 always `timeout`). Enforce probe tables on simple and the trio as before. Failover under enforce: VIP 33.6 s. Watch CPU on 1 core: 31 to 36 ms a run |
| 6. One more try, by faults | **found** in part | A failed load (simulated) gives exit 0 when the spec does not say `firewall.state: enforce`. Nothing found that leaves a node open and silent: a cut record, a full ruleset directory and a killed `dpkg` all stay closed |

## Item 1: keel#308, the fault orders (PASS, with notes)

`f1.sh` on 9402 (log 20): start in `s8` (8080 loaded, file, copy and
record agree), the fault, an apply of `s0`, then the ruleset file lost
and the table deleted with the fault still there (45 s of the watch),
then the fault removed and an apply of `s0`. Probes of TCP 8080 and 9999
from CT 9400 on IPv6 and IPv4 at each of the three points.

| Fault order | Apply of `s0` under the fault | 8080 from outside | File lost, fault still there | 8080 | Fault removed, apply | 8080 |
| --- | --- | --- | --- | --- | --- | --- |
| F1a. State directory read-only (read-only bind mount) | `keep ...: failed: the last good copy cannot be written: Read-only file system`; `0 change(s), 1 failed`; exit 16. Loaded, file, copy and record unchanged (8080) | open | the copy restored (`restored from keel's last good copy`): 8080 ruleset, the last complete apply; check 0 | open | `4 change(s), 0 failed`; 8080 gone everywhere; record = copy = file | timeout |
| F1b. State directory full (tmpfs 8 KiB, filled) | `... failed: ... No space left on device`; `0 change(s), 1 failed`; exit 16; nothing changed | open | the 8080 copy restored | open | the same as F1a | timeout |
| F2. Copy written, record not (simulated: the `s0` copy put in place, the record of `s8` kept; log 21) | (the state of a cut between the two) | open | spec `s0` readable: the step wrote `s0`; spec invalid: `keel-fallback`, `degraded`, check 14 | timeout | apply: all clear | timeout |
| F3a. Ruleset directory read-only (read-only bind mount) | `keep ...: done`, `record ...: done`, `write ...: not done: Read-only file system`; `2 change(s), 1 failed`; exit 16. Loaded and file 8080; copy and record `s0` | open | the file could not be removed (read-only); the deleted table came back from the old file | open | `2 change(s), 0 failed`; all `s0` | timeout |
| F3b. Ruleset directory full (tmpfs 4 KiB, filled) | the same, `No space left on device`; exit 16 | open | the **new** copy restored (`s0`): 8080 closed; check 0 | timeout | apply: all clear | timeout |
| F4. The load fails (simulated: an `nft` first in PATH exits 1 for `nft -f` of keel's file only) | `keep: done`, `record: done`, `write: done`, `load it ...: not done: nft exited 1 ...; the node keeps the firewall it had ...`; **`3 change(s), 0 failed`, exit 0**; check: `table inet keel holds a248...; ... says a08b...`, exit 14 | open | the copy (`s0`) restored | timeout | `0 change(s)` | timeout |

What the apply of a removed port does under each fault:

- In F1 (state directory), nothing changes and the old port still
  answers. This is the intended state: the copy, the record, the file
  and the table all stay on the last complete apply, and a later repair
  restores exactly that.
- In F3 (ruleset path), the copy and the record already name the new
  ruleset, so a later repair restores the new one, as the PR
  description says.
- In both, the person who runs the apply sees exit 16 and the failed
  line. Afterwards nothing on the node says that the spec is not
  applied: `keel firewall check` exit 0, node `running`. `keel diff`
  shows the drift (seen in the seventh test).

F4 gives exit 0: when the spec does not say `firewall.state: enforce`,
the load is an `Attempt`, and a failed `Attempt` does not count as a
failure (`keel/system/execute.py`, `keel/system/firewall.py`, read from
the code). The check and the watch then show the difference between the
file and the table. With a real `nft` that refuses the file, the watch's
own load would fail too (read from the code, not tested).

The immutable flag was not tested: `chattr` is not in the image, and an
unprivileged CT cannot set it.

## Item 2: keel#309, a full ruleset path (PASS)

F3b above (log 20): `/etc/keel/firewall` on a tmpfs of 4 KiB, filled
(`df`: 100 %). Apply: `write /etc/keel/firewall/keel-manifest.nft
(enforce): ... not done: No space left on device; ...`, `apply --system:
2 change(s), 1 failed`, **exit 16**. The node stays closed: the old
table, 9999 `timeout`, 8080 still open as before the apply.

## Item 3: keel#310 (PASS)

9403 (log 30): the spec moved away, the ruleset file emptied (then, in a
second run, removed), `pct reboot`. After the boot: `degraded`,
`keel-firewall.service` failed, the full ruleset (`keel-manifest
a08b...`, restored from the copy), check 14. The spec put back at
08:34:26 (second run 08:37:14), no apply, sampled each 5 s:

| Seconds after the spec came back | Node | `keel-firewall.service` | Ruleset | check |
| --- | --- | --- | --- | --- |
| 5 to 28 | degraded | failed | full | 0 |
| 33 to 34 | running | active | full | 0 |
| up to 102 | running | active | full | 0 |

The watch at its next run: `keel-firewall.service restarted: it failed
at boot, and the ruleset is sound now`. From outside: 8080 and 9999
`timeout`, 80 `open`. No apply is needed.

## Item 4: a power cut at each step (PASS)

`item4.sh` with `killat.py` on 9404 (log 40): from `s8`, an apply of
`s0` that is killed with SIGKILL as soon as the named file changes
(polled each 1 ms), then `pct reboot`, then 40 s, then 40 s more with no
command, then an apply. This is a real kill -9; the reboot stands in for
the power cut.

| Killed right after | Before the reboot | After the reboot (40 s and 80 s) | 8080 from outside | Apply needed |
| --- | --- | --- | --- | --- |
| the copy (1.9 s) | copy new, record old, file and table old | old ruleset (8080), `running`, check 0 | open | yes: the apply closed 8080 (`7 change(s)`) |
| the record (1.6 s) | copy and record new, file and table old | old ruleset (8080), `running`, check 0 | open | yes (`6 change(s)`) |
| the file (1.8 s) | copy, record and file new, table still 8080 | new ruleset loaded at boot, `running`, check 0 | timeout | no (the apply after: `4 change(s)`, only state) |

No state was open. In the first two cases the node keeps the old ruleset
after the reboot and nothing says so (check 0, `running`); the apply
that was cut said nothing either, because it was killed. One sample in
the third case, taken before the reboot, said check 0 while the loaded
table still had 8080; it was not looked at further.

## Item 5: regression (PASS)

| Check | Observed |
| --- | --- |
| Upgrade 0.23.97 to 0.23.100, 9401 | 17 min: `running`, 0 failed, 0 keel lines, `inet filter`, `NOT APPLIED ...`, exit 0 (log 70) |
| The same, trio | 10 min: the same, with CrowdSec's tables (log 22) |
| Upgrade main 0.23.99 (enforce applied) to 0.23.100, 9405 (log 12) | `dpkg exit 0`, 8 reloads; the same keel timers restarted as in tests 3 to 7; `fastprobe` from CT 9400 on IPv6 and IPv4 for 50 s across the upgrade: TCP 9999 `timeout` from the first to the last try, 22 and 80 `open`; after it file, record and table unchanged, check 0 |
| Simple enforce (9401, log 71) | first apply `enforce: each socket ...`; TCP and UDP 9999 `timeout`, TCP 22, 80, 443, 12321 `open`, UDP 12321 and TCP 3306 `timeout`, 4 rows each |
| cloud_advanced (log 42) | first apply `enforce` on the three; 9420 and 9421: 22, 80, 443, 12321 `open`; 9999, 3306, 2379, 22000 `timeout`; witness 9422: 22, 12321 `open`, 80 and 443 `timeout` |
| Failover under enforce (log 43) | `pct shutdown 9420`: VIP on 9421 33.6 s after the shutdown started; 9420 replicated again 23 s after its start |
| Watch CPU, 1 core, the normal case (log 72) | 32.2, 34.2, 31.1, 35.3, 34.2, 36.1 ms a run (test 7: 31 to 49 ms) |

## Item 6: one more try, by faults

| Fault | Observed |
| --- | --- |
| A failed load (simulated, item 1 F4) | apply exit 0 when the spec does not say `firewall.state: enforce`; check exit 14 |
| A cut write of the record (the first 5 bytes, `enfor`), spec invalid, file removed, table deleted (9403, log 60) | `keel-fallback`, check 14 |
| The ruleset directory full (tmpfs 4 KiB), file emptied, table deleted, spec valid | `keel's last good copy is not restored: No space left on device`, then `keel-fallback`, `degraded`, check 14; 9999 and 80 `timeout`, 22 `open`. The fault removed: the full ruleset 35 s later, `running` |
| `dpkg -i` of 0.23.100 over 0.23.99 (enforce) killed with -9 after 1.0 s and 2.5 s (9406, log 61) | `install ok half-configured 0.23.100`; the table unchanged, `running`, check 0; 35 s later the same; `dpkg --configure -a` finished it; 9999 `timeout` from outside |

Nothing was found that leaves a node in enforce open and silent.

## What was not tested

- The ISO, two sites with netem, image builds, the other images.
- The immutable flag (not possible in an unprivileged CT).
- A real `nft` that refuses keel's file at load time (simulated).
- A real power cut (kill -9 and a reboot).

## Logs

On the maintainer's workstation in
`repos/evidence-0097-2026-11-23/pr314-run8/`. The runner records
(`runner-adv/`) are not copied here.

| Log | Content |
| --- | --- |
| `05-api-before`, `97-api-after` | head and CI state |
| `00-vm-baseline`, `99-vm-after`, `99-vm-diff`, `99-cleanup` | the VM before and after |
| `01-images`, `02-create-simple`, `04-push`, `20-adv-runner`, `10-upgrade-94NN`, `21-upgrade-942N`, `11-main-9405`, `13-setup`, `41-cloud-apply` | templates, CTs, upgrades, setup |
| `20-item1`, `21-item1-f2` | items 1 and 2 |
| `30-item3` | item 3 |
| `40-item4` | item 4 |
| `12-item5-upgrade-main`, `70-item5-window`, `22-item5-window-cloud`, `71-item5-simple`, `42-cloud-probe`, `43-failover`, `72-item5-cpu` | item 5 |
| `60-item6-faults`, `61-item6-dpkg` | item 6 |
| `98-secret-scan` | secret scan |

Secret handling: node secrets were made inside each stopped CT and never
printed; the spec was copied, never printed. Every `.log`, `.out`,
`.txt`, `.tsv` and `.md` file under `pr314-run8/` was scrubbed
(`scrub.sed`; control and non-ASCII bytes to `?`). The scan of log 98
over 126 files found no key, no join or accept line, no private key and
no token. The 4 `keel2:` hits are sed patterns in the scripts. The 3
`password` hits are screen control codes after the `password:` prompt in
the console transcripts. The same 8 patterns over this file: 2 lines
with the word `keel2:`, in this paragraph; no key, no join line, no
password, no token.

## Cleanup

CTs 9400 to 9406 and 9420 to 9422 were destroyed with `pct destroy
--purge`. The templates `ev314r8-*` and `/root/ev314r8` were removed; the
templates that were on the VM before were not touched. The Proxmox
firewall is `disabled/running` and `/etc/pve/firewall` is empty, as
before. The diff of the VM state before and after, without counters,
time stamps and veth peer indexes, is empty: `diff_exit=0 lines=0` (log
99). The runner worktree `worktrees/runner-ev314r8` was removed.
