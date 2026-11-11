# The OJS package prototype on a real node: install, upgrade, failures and restore

Date: 2026-11-11

This file is the evidence for the places marked "(package test)" in
decision note 0084. It covers the first prototype of the packages
`ojs-3.5` and `ojs-common` from the repository `Keel-Linux/ojs`. It
covers test 2 of the note and the package part of test 4. It is not a
commissioning test (0075). Nothing was published.

## The question

1. Do the packages install OJS, and does the first boot pass?
2. Does `apt-get upgrade` move a node from 3.5.0.5 to 3.5.0.6, and how
   long does the site answer 503?
3. When the migration fails or stops, do the marks, the alert,
   `ojs-upgrade --retry` and `ojs-upgrade --restore` work as the
   prototype says?
4. After a power loss during the migration or during the unpack, does
   the site stay closed, and how does the node get back to a good
   state?
5. When the unpack fails, or the preinst refuses, does dpkg give the
   site back in a known state?

## The machine

Two runs used one container each, on BR1. Each container started from
the same image and the same settings.

| Item | Run 1 | Run 2 |
|---|---|---|
| Container | CT 9367, host name `ojs-pkg-test` | CT 9368, host name `ojs-pkg2-test` |
| Snapshot for each test | `p1`: 3.5.0.5 installed, first boot done | `q1`: 3.5.0.5 installed from the test repository, first boot done |
| Time (UTC) | 15:17 to 15:38 | 17:05 to 18:55 |

| Item | Value |
|---|---|
| Container settings | unprivileged, nesting, 2 cores, 4096 MiB, swap 1024 MiB, root disk 16 GB |
| Image | `debian-13-keel-lnmp_19.0-6_amd64.tar.zst` |
| Keel packages | keel 0.23.96, keel-web 0.4.2 (0.4.3 after the run 2 upgrades), anubis 1.27.0-0+keel4 |
| PHP | 8.4.26 in the image. 8.4.27-1~deb13u1 after the install of `ojs-3.5`, which pulls the 7 PHP modules |
| MariaDB | 1:11.8.6-0+deb13u1 |
| nginx | 1.26.3-3+deb13u9 (1.26.3-3+deb13u10 after the run 2 upgrades) |
| Network | IPv6 by SLAAC and IPv4 by DHCP. The containers are not IPv6-only nodes |
| `ojs-3.5.0-6.tar.gz` | sha256 `f5b85703b06e45cc82e56ef72b0a8f42a2f75237e5204dbd0146d9730a627c97` (the pin of the source) |

`3.5.0.5+keel1` is test material only. It is the 3.5.0-5 tarball in the
same package, so that the tests can upgrade to 3.5.0.6. Keel never
publishes it (note 0084, "The answer for trixie").

## The packages

| Package file | sha256 | Built at | Used in |
|---|---|---|---|
| `ojs-3.5_3.5.0.5+keel1_all.deb` | `e35cd9cbaad5cf10e71428affcaeee0e6f06f83c0797fc79107b37d6a6b4654a` | `354ec52` or earlier | run 1 |
| `ojs-3.5_3.5.0.6+keel1_all.deb` | `8bddea59a2ee8bc0ae68a42d5c93bf884a395823b689c394394d3f7fa0ff9575` | `354ec52` or earlier | run 1 |
| `ojs-common_0.1.0_all.deb` | `b34a5a92152d20f484991cab737aa1faa6f6b991119ee0f8641d0f69c39a9917` | `354ec52` or earlier | run 1 |
| `ojs-3.5_3.5.0.5+keel1_all.deb` | `f6c3246523fca3c6ba71651ff92a4447901beb4681bcb5cee09a83d2ade29316` | `1d75cf1` | run 2 |
| `ojs-3.5_3.5.0.6+keel1_all.deb` | `729bca3dbc5b38d73fc8d310c97f5debb66f11c591fd131bd51a5ddd2d627b48` | `1d75cf1` | run 2 |
| `ojs-3.5_3.5.0.6+keel1_all.deb`, cut to 41943040 bytes | `247bcf27cc954b07347f0d4b2c24bdba7b7ae1c00eef486f2a98370af030d9ad` | (a copy of the file above) | run 2, test 44 |
| `ojs-common_0.1.0_all.deb` | `74701c5a4dd48c7a3059b7c85e90da922ce2ac3c9a4083327517ff8c0158da14` | `1d75cf1` | run 2, tests 10 and 20 |
| `ojs-common_0.1.0_all.deb` | `e1a54753acad5d03793395eaf88f22e2588d3f01089e7fdcf4a0115579c34cf9` | `9e9a5a7` | run 2, tests 25 to 45, snapshot `q1` |
| `ojs-common_0.1.0_all.deb` | `95809b41e8c9df9b4e35b79f35e6febbbc46a1b30a7d41b2210a782dc62a63ed` | `27916c3` | run 2, test 46 |

"Built at" for run 1 is the newest commit before the run. The run 1
logs do not name the commit. The version of `ojs-common` stayed 0.1.0
in each build, because no package is published. The build of
`ojs-3.5` 3.5.0.6 at `27916c3` gave the same sha256 `729bca3d…`.

`27916c3` changes `bin/ojs-preinst` only. Tests 30 to 45 did not run
again with that build.

Run 1 installed the packages from local files (`apt-get install
./FILE.deb`). Run 2 used a local HTTP apt repository in the container
(`127.0.0.1:8099`, `trusted=yes`, no signature), in three states:

| State | Content |
|---|---|
| A | `ojs-common` and `ojs-3.5` 3.5.0.5+keel1 |
| B | `ojs-common` and `ojs-3.5` 3.5.0.6+keel1 only. The old version is not in the index, as in the Keel repository |
| C | as B, but the file of `ojs-3.5` is cut, so the unpack fails |

Run 1 (log 34) showed that the Keel repository index holds one version
of each package: `apt-cache madison` gave keel-web 0.4.3 only, while
0.4.2 was installed.

## How a migration was made to fail

A second database session held row locks on the tables `versions` and
`email_templates_default_data` (`SELECT SLEEP(1800)` in an open
transaction). The migration then waited, or it failed with
`SQLSTATE[HY000]: General error: 1205 Lock wait timeout exceeded`.
This is a cause outside the backup. A power loss was `pct stop` of the
container. Each test started from the snapshot. A script polled `/`
one time each second. The 503 durations below count those polls.

## Results

| Test | Log | Result |
|---|---|---|
| Install 3.5.0.5 from local files | run 1, `10-install-3.5.0.5.log` | apt code 0 in 36 s |
| Install 3.5.0.5 from the repository | run 2, `10-install-3.5.0.5.log` | apt code 0 in 38 s. The dpkg trigger reloaded nginx: the same main process, new worker processes. `/` gave 503 before the first boot, `/keel-health` 204. The file of the package was kept in `/var/lib/ojs/packages` |
| First boot | run 1, `20-firstboot.log`, `21-state-after-firstboot.log` | Code 0 in 110 s. 132 tables, core version 3.5.0.5, `utf8mb4_unicode_ci`. The config is read-only for www-data. `/config.inc.php`, `/tools/upgrade.php`, `/.git/config` gave 403. `pdf.mjs` came as `text/javascript` |
| First boot | run 2, `20-firstboot.log` | Code 0 in 111 s, with the message "cannot empty /var/cache/ojs as www-data". This is defect 1 |
| Reboot after the first boot | run 1, `23-after-reboot.log` | The worker and the timer are active, `/` gives 200 |
| Upgrade 3.5.0.5 to 3.5.0.6 | run 1, `30-upgrade-3.5.0.6.log`, `31-state-after-upgrade.log`, `32-after-upgrade-checks.log` | apt code 0 in 26 s. 503 for 4 s (this build closed the site in the postinst). The page generator says 3.5.0.6. Backup 152 MB with its `complete` stamp |
| Upgrade with `apt-get upgrade` | run 2, `30-upgrade-3.5.0.6.log` | 10 packages in one run, `ojs-3.5`, nginx and keel-web included. apt code 0 in 32 s. 503 for about 21 s, from the preinst to the end of the configure. The migration took less than 1 s. Backup 226 MB: it holds the 77 MB file of the old package |
| Downgrade with a newer database | run 1, `33-downgrade-refused.log` | The preinst refused: "the database is at 3.5.0.6, newer than the code 3.5.0.5". apt code 100. The package stays 3.5.0.6, the site gives 200 |
| Failed migration, then `--retry` | run 1, `40-failed-migration-retry.log` | `upgrade.php` code 2. The alert went to stderr, to the journal (`ojs-upgrade`) and to the hook in `/etc/ojs/alert.d`. apt code 0. The site gave 503, the worker and the timer stayed stopped. A second apt run: check 0 refused, apt code 100. `ojs-upgrade --retry`: code 0 in 12 s, the site open |
| Failed migration, then `--restore` | run 2, `40-failed-migration-restore.log` | The same failure and alert. The repository had 3.5.0.6 only. `--restore` installed the old package from the file in the backup: code 0 in 22 s. After it: `ojs-3.5` 3.5.0.5+keel1, core version 3.5.0.5, 132 tables, the site open, the worker and the timer active, the 3.5.0.5 file kept again |
| `kill -9` of `upgrade.php`, then `--retry` | run 2, `41-kill-migration-retry.log` | The alert names code 137. dpkg shows `ii`. A second apt run does nothing. `dpkg --configure -a` code 0. `--retry`: code 0 in 9 s |
| Power loss during the migration | run 2, `42-power-loss-migration.log` | After the boot: `ojs-3.5` 3.5.0.6+keel1 `iF`. The maintenance mark and the incomplete mark exist. The worker did not start (the unit condition). `/` gives 503. apt code 100. `dpkg --configure -a`: the postinst runs no migration and sends the alert, the package becomes `ii`. `--retry`: code 0 in 14 s |
| Power loss during the unpack, run 1 | run 1, `42-power-loss.log` | After the boot: `iHR`, no maintenance mark, `/` gives 200, the worker active. The tree was mixed: `version.xml` says 3.5.0.5, and the 3.5.0.6 migration `I13283` exists. After `dpkg --configure -a` (the package stayed `iHR`), `apt-get install` of the 3.5.0.6 file repaired the tree and migrated: code 0 in 23 s. This finding is the cause of `5dcb9c8` |
| Power loss during the unpack, run 2 | run 2, `43-power-loss-unpack.log` | Before the stop: the mark `state=unpack` `workers=stopped` and the token. After the boot: `iHR`, the same mark, no token, `/` gives 503, the worker did not start, apt code 100. `dpkg --configure -a` configured nginx, and `ojs-3.5` stayed `iHR`. `apt-get install --reinstall ojs-3.5`: the preinst said "an earlier unpack or configure ... did not end", then the configure migrated. Code 0 in 27 s, the site open |
| Failed unpack (a cut file) | run 2, `44-failed-unpack.log` | dpkg-deb stopped with "unexpected end of file". dpkg called the old postinst with `abort-upgrade`. The token was there, so the site opened: "the upgrade was aborted and dpkg put the old code back; the site is open". 503 for 4 s. apt code 100. `ojs-3.5` stays 3.5.0.5+keel1 `ii`. No alert, as the prototype says. keel-web and libnginx-mod-stream of the same apt run stay unpacked and not configured |
| Refused preinst after a power loss during the unpack | run 2, `45-refused-after-power.log` | The database was stopped. The preinst refused (check 5), apt code 100, `ojs-3.5` `iH`, the mark `state=unpack-interrupted`, `/` gives 503. No alert left the node. This is defect 2. With the database up, the reinstall passed |
| The same, with the fix | run 2, `46-refused-after-power-alert.log` | The preinst sent the alert: "the install of the OJS code 3.5.0.6 was refused after an unpack that did not end. The site stays in maintenance ...". The hook got it. With the database up, the reinstall passed, the site open |
| The worker and the scheduler after the upgrade | run 1, `43-scheduler-worker-3.5.0.6.log` | The timer started the scheduler each minute, and it ended with code 0. The worker started at 15:36:47. 0 jobs, 0 failed jobs |

In each restore and retry above, the state after was compared by the
core row of `versions`, the count of tables, the release in
`version.xml`, the marks, the units and the HTTP answers. No test
compared the full content of the database and of the files. The third
test did that for the restore method by hand
(`2026-11-10-ojs-3.3-to-3.5-upgrade-and-restore.md`).

## The defects that the runs found

| Defect | Found in | Fix | Shown fixed in |
|---|---|---|---|
| A power loss during the unpack left a mixed code tree that answered 200, with the worker active | run 1, log 42 | `5dcb9c8`: the preinst closes the site and stops the worker before the unpack. The units have `ConditionPathExists=!/var/lib/ojs/maintenance`. The token `/run/ojs/unpack` decides if an aborted upgrade opens the site. Each configure keeps the package file, and each backup holds the old one. `1d75cf1` came from the review of it | run 2, logs 43 and 44 |
| `cache_clear` ran `find` as www-data from `/root`. GNU find 4.10 removed the files, then exited 1, because it could not go back to `/root` | run 2, logs 20 and 24 | `9e9a5a7`: `find` runs from `/` | run 2, log 25 |
| A refused preinst after a power loss during the unpack sent no alert. dpkg calls no postinst of a half-installed old package | run 2, log 45 | `27916c3`: the preinst sends the alert itself | run 2, log 46 |

Each fix adds bats tests to the repository.

## Other facts from the logs

- etckeeper commits `/etc/ojs/config.inc.php` and `/etc/ojs/app_key`
  into `/etc/.git` before and after each apt run (run 1, logs 30 and
  40). These files hold secrets. `/etc/.git` is root 0700, but its
  history keeps each old value. This is an open item.
- OJS 3.5.0.5 prints a `TypeError` trace on the command line
  (`Locale::setDefault()`, while the GoogleAnalytics plugin
  registers). The preinst runs `jobs.php restart` with the old code,
  so the trace is in the apt output of each upgrade from 3.5.0.5 (run
  2, logs 30, 40 and 44). The preinst continued. On 3.5.0.6 code,
  `jobs.php total` printed no trace, with a full and with an empty
  cache (run 2, log 31, the block at 18:14:16 only: the later blocks
  of that log ran after a rollback to 3.5.0.5).
- OJS makes `/var/cache/ojs/opcache` as the web user (run 2, logs 21
  and 30). It is not one of the directories that `ojs-common` makes.
- `systemctl start` of a unit with a failed condition returns 0, and
  the unit stays inactive (run 2, logs 42 and 43).
- After a power loss during an apt run, each apt command returns 100
  until `dpkg --configure -a` runs (run 1, log 42, run 2, logs 42
  and 43).
- The scheduler timer is active after a boot with the maintenance
  mark, but its service does not start (run 2, logs 42 and 43).
- `apt-get upgrade` configured nginx and keel-web while the site was
  in maintenance (run 2, log 30).
- The install log `/var/log/ojs/install-*.log` (root 0600) has 14
  lines that match "password" or "app_key". The upgrade logs have 0
  (run 1, logs 21 and 32).

## What this does not show

- Test 6 of the note: a pair, the writable gate, a promote, Syncthing
  and a slow link (netem). Each run used one container on BR1, not the
  0075 topology.
- Test 7: a journal of about 10 GB, and the disk check with real
  sizes. No test made the disk check refuse.
- Test 8: a line change, `install` of a new line, and `abort-remove`.
- The 3.3 import with the package (a 3.3 database and `ojs-3.5`).
- The Anubis front. `anubis@keel-web` was inactive in both containers.
- Plugin packages, and a plugin migration that fails.
- The PKP checklist on a node that the package installed.
- A standby node, and `--restore` of an import from outside Keel.
- An IPv6-only node. Both containers had IPv4.
- A signed repository. The test repository had `trusted=yes`.
- The comparison of the tarball with the git tag (not built).
- Tests 30 to 45 with the build of `27916c3`.

## Deviations

- Run 1 and run 2 used different builds (see "The packages"). In run
  2, `ojs-common` was built three times with the same version 0.1.0.
- In run 1, log 43 queried a table `scheduled_tasks`, which does not
  exist in OJS 3.5. The error is a fault of the test script, not a
  result.
- In run 1, log 22, `/` gave 502 directly after the start from the
  snapshot, while the services started. Log 23 shows 200 after the
  boot ended.

## State after the test

CT 9367 (snapshot `p1`) and CT 9368 (snapshot `q1`) stay on BR1. Their
config files hold test passwords and keys. Remove them after this file
is merged. The command logs are with the coordinator
(`repos/ojs-hand-tests/pkg1/` and `pkg2/`). This file holds the lines
that the note uses. The coordinator compared each line of this file
with the logs. No package was published, and no tag was made.
