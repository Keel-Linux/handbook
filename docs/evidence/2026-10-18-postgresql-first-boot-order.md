# Evidence: the PostgreSQL first boot hooks, the image gate, and the light CI of five repositories

Date: 2026-10-18. The time zone is UTC. The maintainer approved the work
("continua o que temos pendente"). Test machine: `hw12-br1`. Build host:
`tkldev`. Decision 0061 (image per merge) and decision 0056 (light CI on
GitHub) apply.

No secret is in this file. Output is trimmed. Test passwords are random and
were never printed.

## Result

| Item | Result |
| --- | --- |
| 1. Image build 20261018T025251Z (common#51) | The build and the gate took 46 min. The boot gate failed at lnpp. Core, Web and LNMP passed. image-gate#12 is open. |
| 1. Retention of `/srv/keel-ci/testing` | Pruning exists and has a test. No change needed. |
| 2. keel-postgresql#20 cause | A race at the first boot. The cluster started before the snakeoil certificate existed. |
| 2. Fix | inithooks#57, package 2.3.6+keel27, in trixie-testing only. |
| 2. Real boot on BR1 | Without the fix 35pgsqlpass and 36pgsqlverify fail. With the fix both pass. |
| 3. Light CI of five repositories | All five merged on green. GitHub Actions are on for all five. |

## 1. The image build for common#51

The poll found `common` changed at 02:52:51 and built all seven layers.
The build, the staging signature and the hand-off took until about 03:31.
The gate run, `image-gate` run 12, ended at 03:38 with `failure`:

| Appliance | Boot test |
| --- | --- |
| core | passed (first boot 65 s) |
| web | passed (first boot 65 s) |
| lnmp | passed (first boot 55 s) |
| lnpp | failed |
| mariadb, postgresql, redis | not booted: the gate stops at the first failure |

The failure of lnpp, from the job log:

```
ERR: [35pgsqlpass] failed - exit code 1
ERR: [36pgsqlverify] failed - exit code 1
psql: error: connection to server at "::1", port 5432 failed: FATAL:  password authentication failed for user "postgres"
boot-test: the database refused the declared password
```

The build host opened image-gate#12 by itself. Nothing was promoted.
`latest-core` and `latest-web` still name the build of 2026-10-16.
Before this build, mariadb and postgresql never passed the gate (no
`latest-mariadb`, no `latest-postgresql`).

### Retention

Decision 0061 asks for the last 3 builds and for every build that a
`latest-*` link names. `imageci_retention` in `lib/imageci.sh` does this
for `staged` and for `testing`. The test "retention keeps the last builds
and every build a latest link names" in `tests/image-ci.bats` covers it.
The journal shows the pruning at work: `retention: removed
staged/20261016T211031Z` at the start of this build. `testing` holds 4
builds now. Two of them are older than the last 3 because `latest-core`,
`latest-web` and `latest-lnpp` still name them, which is the rule. So no
pruning code was added.

## 2. keel-postgresql#20

### Cause

The check `tests / appliance` of keel-postgresql#20 boots the published
layer of 2026-10-08 after an upgrade from Debian and trixie-testing. The
log of run 6 shows the same failure as the image gate:

```
INFO: [35pgsqlpass] running
ERR: [35pgsqlpass] failed - exit code 1
INFO: [36pgsqlverify] running
ERR: [36pgsqlverify] failed - exit code 1
```

On a CT of BR1 the journal of the first boot shows the order of events:

```
03:12:27 keel-host-keys.service starts (it writes the snakeoil certificate)
03:12:28 postgresql@17-main: FATAL: could not load server certificate file
         "/etc/ssl/certs/ssl-cert-snakeoil.pem": No such file or directory
03:12:35 35pgsqlpass runs: psql: connection ... .s.PGSQL.5432: No such file
03:12:36 postgresql@17-main starts again (too late)
```

`keel-host-keys.service` has `Before=postgresql.service`. That line does
not order the instance `postgresql@17-main.service`, which starts the
server. So the server and the key writer ran at the same time. When the
server lost, it failed, and `35pgsqlpass` found no socket. `36pgsqlverify`
failed because the role had no password. The race depends on timing: one
plain first boot of the new postgresql image passed, the image gate boot
of lnpp failed. The upgrade step of the CI masks `keel-host-keys.service`
on its first boot, so the real first boot always runs the race there.

The version of keel does not matter. The CT held keel 0.23.13 at the first
failure and keel 0.23.43 at the next ones.

### Fix and tests

The fix is in inithooks, the package that ships `keel-host-keys.service`:
inithooks#57 (merged) installs the drop-in
`/usr/lib/systemd/system/postgresql@.service.d/10-keel-host-keys.conf` with
`After=keel-host-keys.service`. The tests came first. Two tests in
`tests/test-packaging.bats` failed (drop-in missing, install line
missing). Then the drop-in and the install line went in, and the tests
passed. CI of inithooks#57: all four jobs green. The built `.deb` lists the
drop-in. A first version of the fix in the overlay of keel-postgresql
(keel-postgresql#21) was closed. The package route also fixes the boot
check, which upgrades the layer from trixie-testing, and every machine
that upgrades.

### Real boot on BR1

CT 9161 (new, mine) on `hw12-br1`, unprivileged, bridge `vtnet88`, from
the image `debian-13-keel-postgresql_19.0-7_amd64.tar.zst` of build
20261018T025251Z (sha512 `efc1b8db2ff1...`, copied from the build host).
The CI flow was copied: first boot units masked, upgrade, unmask, first
boot with `DB_PASS` in the conf. The CT was destroyed after each run.

| Run | inithooks | 35pgsqlpass | 36pgsqlverify | login with the declared password |
| --- | --- | --- | --- | --- |
| Layer of 2026-10-09 (keel 0.23.13), plain first boot, no fix | 2.3.6+keel23 | failed | failed | refused |
| Same layer, CI flow, upgraded to keel 0.23.43 | 2.3.6+keel26 | failed | failed | refused |
| Same layer, plain first boot, drop-in put in the rootfs by hand | 2.3.6+keel23 | passed | passed | works |
| Same layer, CI flow, with inithooks 2.3.6+keel27 | 2.3.6+keel27 | passed | passed | works |
| New image, CI flow, no fix | 2.3.6+keel26 | failed | failed | refused |
| New image, CI flow, with inithooks 2.3.6+keel27 | 2.3.6+keel27 | passed | passed | works |

The last two lines are the proof on a new image. One plain first boot of the
new image without the fix passed, because the race depends on timing. CT 9161 and the copy of
the image on BR1 are gone. No CT 9054 or 9062 or any other CT was touched.

### Publication

```
# build host, /srv/keel-apt/apt
$ bin/build-package inithooks master </dev/null
build-package: done: inithooks_2.3.6+keel27_amd64.changes in /srv/keel-apt/incoming
$ bin/publish </dev/null
publish: committed in /srv/keel-apt/apt: publish trixie-testing: inithooks 2.3.6+keel27
# apt#47 merged on green, then from the workstation
$ keel-publish-mirror --archive-only
keel-publish-mirror: https://archive.keellinux.org trixie verifies
keel-publish-mirror: https://archive.keellinux.org trixie-testing verifies
keel-publish-mirror: https://archive.keellinux.org trixie-security verifies
$ curl -s https://archive.keellinux.org/dists/trixie-testing/main/binary-amd64/Packages | grep -A1 '^Package: inithooks$'
Version: 2.3.6+keel27
$ curl -s https://archive.keellinux.org/dists/trixie/main/binary-amd64/Packages | grep -A1 '^Package: inithooks$'
Version: 2.3.6+keel26
```

`trixie` is not changed and the stable index is not touched.

### The check after the fix

The check `tests / appliance` of keel-postgresql#20 ran again. It took
3 min 6 s and passed. The log shows the upgrade to
`inithooks 2.3.6+keel27` from trixie-testing, then `35pgsqlpass` and
`36pgsqlverify` successfully completed and `postgresql boot test passed`.

## 3. The light CI of five repositories

| Repository | Pull request | What was needed |
| --- | --- | --- |
| keel-postgresql | #20 | the fix of section 2, then a new run: green, merged |
| keel-nodejs-nginx | #6 | #7, then merged |
| keel-nodebb | #21 | #22, then merged |
| keel-wordpress | #20 | #21, then merged |
| keel | #184 | see "Open" |

keel-nodejs-nginx, keel-nodebb and keel-wordpress have no layer on the
mirror. The check `appliance` of the full CI therefore failed on every
pull request ("Failing after 11 s"), also on pull requests that do not
touch it. The three pull requests #7, #22 and #21 set the documented
exemption `allow_unpublished: true` in the appliance job. The job then
says in its summary that it booted nothing, and it fails by itself when a
layer is published, so the line must go then. This is a real limit: until
the three appliances move to the current stack (decision 0059), no check
boots them.

For keel-postgresql, keel-nodejs-nginx, keel-nodebb and keel-wordpress
GitHub Actions are now on, the same way as for the other repositories:
actions enabled, allowed actions "selected" (GitHub owned only, set at the
organization), the default token read only, approval for all external
contributors. The mirror had the new `.github/workflows/tests.yml`
before the switch (same commit on both sides).

## Open

- keel#184 (light CI of keel): see the final status in the pull request.
  GitHub Actions of `keel` stay off until it merges.
- The image build for common#51 is not promoted. The layers hold
  inithooks 2.3.6+keel26. A build with keel27 in the
  captured pool is needed. No watched repository changes with the package,
  so the next merge in a watched repository starts a build.
- image-gate#12 stays open until a build passes the gate.
- mariadb and redis were not booted by the gate in this run.
