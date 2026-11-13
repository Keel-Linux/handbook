# Evidence: the upgrade test of decision 0090 for keel 0.23.97 and confconsole 2.2.3+keel25

Date: 2026-11-13. Site: BR1 (hw12-br1). Status: draft.

## Question

Does the upgrade to `keel` 0.23.97 and `confconsole` 2.2.3+keel25 change an
installed node of a published application? Decision 0090 requires this test
before the two packages go from `trixie-testing` to `trixie`.

## What changed in the candidate

- `keel` 0.23.97 (keel#305, for keel#304): when Redis runs beside exactly
  one engine that keel pairs (MariaDB or PostgreSQL), `keel inspect`
  records that engine as `database.server`, and writes a report line
  `database.server.others`. In `keel/system/database.py` and
  `keel/spec/constants.py` only a constant moves (`PAIR_ENGINES`); the
  converge does the same as before.
- `confconsole` 2.2.3+keel25 (confconsole#42): the mesh role screen shows
  "No database to pair" and stops when a Primary or Replica node has a
  MariaDB or PostgreSQL server and keel finds no engine to pair.

Package contents (log 19, made on CT 9451 from the archive pool; each
sha256 is the same as the sha256 in the `Packages` index):

- `keel`: 4 Python files differ (`__init__.py`, `inspect/database.py`,
  `spec/constants.py`, `system/database.py`), the dist-info name and the
  changelog. The file list has no other change. `preinst`, `postinst`,
  `prerm` and `postrm` are the same as in 0.23.96. The `postinst` restarts
  the keel timers and path units (`keel-database-*`, `keel-mesh-*`), as
  every keel upgrade does.
- `confconsole`: 3 Python files differ (`dbscreen.py`, `keelfirstboot.py`,
  `meshscreen.py`) and the changelog. The maintainer scripts and the
  dependencies are the same.

## Machines

All CTs are on BR1: unprivileged, `nesting=1`, 2 cores, bridge `vtnet88`
tag 5, nameserver `2606:4700:4700::1111`, rootfs on `local-lvm`. The
sha512 of each template on BR1 is the same as the sha512 on
mirror.keellinux.org (log 00).

| CT | Application | Template (published, stable) | sha512 (start) | Mode |
|---|---|---|---|---|
| 9451 | core | keel-core 19.0-13 | 1fea094b012d500d | cloud_simple, one node, no mesh |
| 9452 | web | keel-web 19.0-14 | 457f8794deb1b023 | cloud_simple, one node, no mesh |
| 9453 | lnmp | keel-lnmp 19.0-7 | c6bfc21f532814a0 | cloud_simple, mariadb primary, one node |
| 9454 | lnpp | keel-lnpp 19.0-10 | b80bd253ebfe0601 | cloud_simple, postgresql primary, one node |
| 9455 | laravel | keel-laravel 19.0-8 | ab19250aee37e790 | cloud_simple, mariadb primary, one node |
| 9456 | ntfy | keel-ntfy 19.0-7 | 08ad5209948d1b88 | simple (see below) |
| 9457 | mariadb | keel-mariadb 19.0-12 | b70aaa703df8b633 | cloud_simple, mariadb primary, one node |
| 9458 | postgresql | keel-postgresql 19.0-9 | f9a74ac207ab54a6 | cloud_simple, postgresql primary, one node |
| 9459 | redis | keel-redis 19.0-13 | 34411e78d60979f0 | simple (see below) |
| 9460, 9461 | wordpress | keel-wordpress 19.0-22 | 4fbd8cfb74041ab5 | cloud_simple pair: 9460 primary, 9461 replica |
| 9462, 9463 | odoo | keel-odoo 19.0-19 | b8ecc1d2b37f40c7 | cloud_simple pair: 9462 primary, 9463 replica |
| 9464 | wordpress | keel-wordpress 19.0-22 | 4fbd8cfb74041ab5 | cloud_simple, mariadb primary, one node (web path checks) |
| 9465 | odoo | keel-odoo 19.0-19 | b8ecc1d2b37f40c7 | cloud_simple, postgresql primary, one node, 4 GiB (web path checks) |

CTs 9464 and 9465 use the instance descriptions of the first test
(`preseed-wordpress`, `preseed-odoo` of 2026-11-12, the same host names
ut-wp and ut-odoo), so that `wp_check.py` and `odoo_check.py` of the first
test run on them with no change.

One-node CTs (9451-9459): we put `/etc/keel/instance.yaml` and the secret
files into the stopped CT before the first boot, as in the first test
(2026-11-12). `make_preseed.py` makes each description from the
`instance` section of the application's `tests/commission.yaml`. For
cloud_simple it turns on the cloud overlays that the contract names
(wireguard, crowdsec, nginx, coraza, anubis, syncthing) and keeps etcd and
vip off. The secrets are made on the BR1 host inside the CT's file system
and are never printed. Each first boot completed with no failed hook
(log 02).

- ntfy and redis: their manifests have `modes: [simple]`, and their
  contracts have no cloud nodes. The redis contract also checks that the
  mode is `simple`. Thus these two nodes are in simple mode. This is a
  deviation from item 2.1 of 0090, because no cloud mode exists for them.
- core and web in cloud_simple with no database: the first boot logs "75keel-role
  not asked ... keel-init asks it". The role question waits for keel-init.
  The node runs.

Pairs (9460-9463): `keel-commission` of Keel-Linux/.github main 34c69b8
made each pair with `--pass cloud_simple --keep`, from the contract of the
application (`contracts/wordpress-pair.yaml`, `contracts/odoo-pair.yaml`:
the cloud_simple nodes of the contract only, with the replica on site
`br1`). The environment is `pair.env`: the image round file
`specs/common.env`, with site br2 pointed at BR1. Thus both nodes of each
pair are on BR1, not on two sites. The runner answered the screens on the
console, formed the mesh and the pair, and ran every check of the
contract (record in `runner-wordpress/`, `runner-odoo/`).

The runner keeps no secret. After the runner, `pair_secrets.sh` set a new
root password on each pair node and a new administrator password of the
application on the primary (WordPress: `wp user update`; Odoo: the
`res_users` hash, pbkdf2_sha512). The replica got the application
password by database replication (logs 20, 30). The values are only on the
nodes, in `/root/ut-secrets/`. The `db` secret was not set again, so the
`db` proof is "not run" on the pair nodes.

## Method

Stages, the same on each node:

- A: the node as made from the published image (keel 0.23.96,
  confconsole 2.2.3+keel24).
- B: `apt-get update` and `apt-get upgrade` from the suites that are on
  (`trixie`, Debian). `trixie-testing` is off. This is what an installed
  node gets today.
- C: the candidate only. `upgrade.sh C` turns on `trixie-testing` for this
  step, runs `apt-get -s install keel=0.23.97 confconsole=2.2.3+keel25`,
  stops when the simulation names any other package, installs the two
  packages, and turns `trixie-testing` off again. No `apt-get upgrade` ran
  while testing was on.

On a pair, the replica was upgraded first, then the primary, in B and in
C. `watch_pair.sh` recorded the VIP holder and the replication state
during each upgrade.

In each stage, on each node:

- `facts.sh`: package versions; `keel inspect` (exit code, the `database`
  section, the report lines on `database`); `keel diff`; `keel spec apply
  --system-only --non-interactive --skip-network`; failed units; Monit
  (`systemctl is-active monit`, `monit -t`, error lines in monit.log);
  `nginx -t`; confconsole on a terminal (`script` gives it a 24x80
  terminal; `confconsole --usage` draws the usage box and waits; `timeout`
  ends it, exit 124); a compile of the confconsole Python files; the role
  screen decision (`meshscreen.node_of` with `keelmode.facts_of`, for the
  node's own description and for the description without `database`, as
  primary and as replica).
- `contract_checks.py`: the contract's `services`, `urls`, `proofs` and
  `forbidden`, as `lib/commission/checks.sh` of the runner does them, with
  the node's own secret files.
- Pairs only, in A and in C: `cross_replay.py` runs every `cloud.checks`
  item of cloud_simple again, in the contract's order, with the semantics
  of the runner: VIP holder, the replica holds the primary's data, a row
  written and replicated, Syncthing folder types, a planned promote of the
  replica, a login on the new primary, the old primary follows, the
  return, no failed units. For Odoo also: the standby stops, the primary
  falls back to asynchronous and the alert comes on the ntfy topic, the
  standby comes back, the old primary rejoins.

`keel spec apply` ran in stage A too. On a new node it changed
`derived.monit` once (see "Findings that are not the candidate").

## Packages

| Stage | One-node CTs | Pair CTs |
|---|---|---|
| B, stable | Debian security only: apt 3.0.4, zlib1g, vim; nginx 1.26.3-3+deb13u10 (web stacks); PHP 8.4.27 (lnmp, laravel); PostgreSQL 17.12 (lnpp, postgresql); libcares2 (laravel). No Keel package | 0 packages (the first boot of the runner had already installed them) |
| C, testing | 2 packages: keel 0.23.96 to 0.23.97, confconsole 2.2.3+keel24 to 2.2.3+keel25 | the same 2 packages |

On each of the 15 nodes the simulation of stage C named only `keel` and
`confconsole`, and `apt list --upgradable` with testing on showed only
these two. No conffile prompt came. After stage C `trixie-testing` is
`Enabled: no` again on each node (logs 1x-C-upgrade, 25, 35, 63, 65), and
`dpkg --audit` is empty on CTs 9451-9463 (log 41).

## Results: one-node CTs

"Checks" is the count of contract checks (services, urls, proofs,
forbidden) that passed; there was no failure. `database.server` is
`engine/role` from `keel inspect`, or "none" when inspect writes no
`database` section.

| App (CT) | Mode | Checks A | Checks B | Checks C | database.server A | database.server C | keel diff drift, A first run | keel diff drift, B and C | apply changes B, C | Logs |
|---|---|---|---|---|---|---|---|---|---|---|
| core (9451) | cloud_simple | 11/11 | 11/11 | 11/11 | none | none | derived.monit | none | 0, 0 | 10 |
| web (9452) | cloud_simple | 15/15 | 15/15 | 15/15 | none | none | derived.monit, filesync folder, filesync.peer | filesync folder, filesync.peer | 0, 0 | 11 |
| lnmp (9453) | cloud_simple | 21/21 | 21/21 | 21/21 | mariadb/standalone | mariadb/standalone | role, derived.monit, filesync folder, filesync.peer | role, filesync folder, filesync.peer | 0, 0 | 12 |
| lnpp (9454) | cloud_simple | 16/16 | 16/16 | 16/16 | postgresql/standalone | postgresql/standalone | role, derived.monit, filesync folder, filesync.peer | role, filesync folder, filesync.peer | 0, 0 | 13 |
| laravel (9455) | cloud_simple | 24/24 | 24/24 | 24/24 | mariadb/standalone | mariadb/standalone | role, derived.monit, filesync folder, filesync.peer | role, filesync folder, filesync.peer | 0, 0 | 14 |
| ntfy (9456) | simple | 28/28 | 28/28 | 28/28 | none | none | none | none | 0, 0 | 15 |
| mariadb (9457) | cloud_simple | 14/14 | 14/14 | 14/14 | mariadb/standalone | mariadb/standalone | role, derived.monit | role | 0, 0 | 16 |
| postgresql (9458) | cloud_simple | 11/11 | 11/11 | 11/11 | postgresql/standalone | postgresql/standalone | role, derived.monit | role | 0, 0 | 17 |
| redis (9459) | simple | 18/18 | 18/18 | 18/18 | redis/standalone | redis/standalone | none | none | 0, 0 | 18 |

On each of the nine nodes, B and C give the same output (log 40):

- `keel diff` output: identical.
- `keel inspect` description (`inspect.yaml`): identical.
- `keel inspect` report (`inspect.err`, with GTID values left out): identical.
- `keel spec apply` change count: identical (0).
- contract checks: identical; A and C identical too.

Other results after stage C, on each of the nine nodes:

- Failed units: 0. Monit active, `Control file syntax OK`, no error line
  in monit.log (other than the lines that our own `monit summary` call
  made in stage A: "HTTP interface is not enabled").
- `nginx -t`: successful on web, lnmp, lnpp, laravel, ntfy. core, mariadb,
  postgresql and redis have no nginx.
- confconsole: the usage box is drawn on a terminal, no "Caught
  exception", no Traceback; 16 Python files compile.
- Role screen decision: `refused=no` on every node, for both
  descriptions and both roles. The engine that confconsole finds is the
  same as in stage A (mariadb on lnmp, laravel, mariadb; postgresql on
  lnpp, postgresql; none on core, web, ntfy, redis).
  `dbscreen.servers_installed` (new in keel25) names mariadb on lnmp,
  laravel, mariadb, postgresql on lnpp, postgresql, and nothing on core,
  web, ntfy, redis.
- No node has a `database.server.others` line (no published application
  runs Redis beside MariaDB or PostgreSQL).

### Redis alone (CT 9459)

`keel inspect` says the same before and after the upgrade:
`database.server.engine: redis (from /usr/bin/redis-server)`,
`database.server.role: standalone (from redis-cli INFO replication:
role:master with connected_slaves:0 ...)`, `listen: 127.0.0.1, ::1`.
`keel diff`: no drift. There is no `others` line. Redis alone has one
server, so the new code path (`_described` with more than one server)
does not apply. The redis contract checks (ACL login, NOPERM, WRONGPASS,
persistence across a restart, Monit command check) pass in A, B and C.

## Results: pairs

| App | Node | Checks A | Checks C | database.server A | database.server C | keel diff A, C | apply changes A, C | Cross checks A | Cross checks C | Logs |
|---|---|---|---|---|---|---|---|---|---|---|
| wordpress | 9460 primary | 15 pass, 1 not run | 15 pass, 1 not run | mariadb/primary | mariadb/primary | no drift, no drift | 3, 3 | 17/17 | 17/17 | 21, 23, 26, 29 |
| wordpress | 9461 replica | 15 pass, 1 not run | 15 pass, 1 not run | mariadb/replica | mariadb/replica | no drift, no drift | 3, 3 | (pair) | (pair) | 22, 27 |
| odoo | 9462 primary | 19 pass, 1 not run | 19 pass, 1 not run | postgresql/primary | postgresql/primary | no drift, no drift | 5, 5 | 26/26 | 26/26 | 31, 33, 36, 39 |
| odoo | 9463 replica | 19 pass, 1 not run | 19 pass, 1 not run | postgresql/replica | postgresql/replica | no drift, no drift | 5, 5 | (pair) | (pair) | 32, 37 |

After stage C, on each of the four pair nodes: `nginx -t` successful,
Monit active with `Control file syntax OK`, confconsole draws the usage box
with no exception, the role screen decision is `refused=no` for both
descriptions and both roles, and `dbscreen.servers_installed` names
mariadb (WordPress) or postgresql (Odoo).

"1 not run" is the `db` proof (no `db` secret on the pair nodes). Stage B
installed no package on the pair nodes, so the B checks were not run
again; B has the A results.

The runner record before our stages: WordPress 82 pass, Odoo 99 pass; in
each, 2 failures: `web.screenshots` on each node ("the browser opened no
DevTools port"). The headless browser of the workstation did not start.
The screenshots are not a check of 0090. Every other check of the runner
passed, with all 17 (WordPress) and 26 (Odoo) cross checks.

The `apply` changes on a pair node are actions that apply does at each
run on a pair (re-authorize replication from the peer, make the server
follow the VIP, the Syncthing role). The count is the same before and
after the upgrade, and `keel diff` shows no drift.

Comparison A to C on each pair node (logs 28, 38): `inspect.yaml`
identical (WordPress: with the GTID lines left out), checks identical.
`keel diff` and the `inspect` report differ only in values that change
with time: the WireGuard handshake age, the semi-sync counters, and the VIP
epoch (3 in A, 5 in C, because the cross checks of stage A promoted the
replica and returned). After the cross checks of stage C, `keel inspect`
says `mariadb primary` / `mariadb replica` and `postgresql primary` /
`postgresql replica` again, and no unit has failed.

During the upgrades (logs 24, 25, 34, 35; one sample each 8 s): the primary
carried the VIP and the replica did not, in every sample. Replication ran
in every sample (MariaDB `Yes/Yes/0`, PostgreSQL `in recovery, streaming`).
In one sample (WordPress, 16:06:57, while dpkg replaced keel on the
primary) the `keel vip status` call on the primary gave no output. The
next sample, 8 s later, says "carried here: yes", and the epoch stayed 5
through both upgrades. The VIP did not move.

## Results: login, write and upload through the web front

Item 2 of 0090 names these checks: the site answers, a login, a write, an
upload. The contract checks above log in by a command on the node (for
example `wp user check-password`), not through nginx. Thus CTs 9464 and
9465 ran the scripts of the first test, unchanged. Each script runs inside
the CT and connects to the global IPv6 address of the CT on port 443 with
the Host header of the application. The request goes through nginx,
Coraza and Anubis. The scripts read the admin secret from
`/etc/keel/secrets/app_password` and do not print it. These two nodes had
stage A and stage C only (no stage B): the candidate went onto the
published image directly.

WordPress (CT 9464, logs 62, 63):

| # | Check | A | C |
|---|---|---|---|
| 1 | GET /wp-login.php | 200 | 200 |
| 2 | Coraza probe (XSS in the query) | 403 | 403 |
| 3 | Admin login, form POST | 302 to /wp-admin/ | 302 |
| 4, 5 | Editor and media pages, nonces | 200 | 200 |
| 6, 7 | Publish a post (REST JSON), read it | 201, text found | 201, text found |
| 8 | Media upload, PNG 5.6 MiB | 200, success | 200, success |
| 9 | Media upload, ZIP 20 MiB | 200, success | 200, success |
| 10 | Post 300 KiB, REST JSON | 201 | 201 |
| 11 | Post 300 KiB, urlencoded | 413 | 413 |
| 12 | Post 300 KiB, multipart text part | 413 | 413 |
| 13 | Media upload with a 300 KiB text field | 413 | 413 |
| 14 | admin-ajax heartbeat | 200 | 200 |
| 15 | Logout page with no nonce | 403 (page of WordPress) | 403 |

Odoo (CT 9465, logs 64, 65):

| # | Check | A | C |
|---|---|---|---|
| 1 | GET /web/login | 200 | 200 |
| 2 | Coraza probe (XSS in the query) | 403 | 403 |
| 3 | Admin login, form POST | 303 to /odoo | 303 |
| 4 | GET /odoo, web client, uid 2 | 200 | 200 |
| 5, 6 | JSON-RPC create a contact, HTML note 100 KiB and 300 KiB | 200, 200 | 200, 200 |
| 7 | Read back the 100 KiB note | same length | same length |
| 8, 9 | Multipart attachment 20 MiB, size and sha1 | 200, sha1 same | 200, sha1 same |
| 10 | Multipart, text field 300 KiB and a small file | 413 | 413 |
| 11 | Multipart, text field 200 KiB and a small file | 200 | 200 |
| 12 | CSV import, 307 KiB file part | 200 | 200 |
| 13 | PDF report | 200, PDF 266 KB | 200, PDF |
| 14 | Websocket /websocket (bus) | 101 | 101 |
| 15 | Logout | 303 | 303 |

Each status is the same in A and in C. The 413 answers come from Coraza
(keel-overlay-coraza 0.1.5), as in stage C of the first test; the
candidate does not change them.

The other results of these two nodes are as for the one-node CTs above:
`database.server` mariadb/standalone (9464) and postgresql/standalone
(9465) in A and in C; `inspect.yaml`, the inspect report and the contract
checks identical in A and C; `keel diff` differs only in `derived.monit`,
which the stage A `keel spec apply` repaired (log 66); no failed unit;
`nginx -t` successful; confconsole draws its usage box; `refused=no`.

On CT 9464 the contract proof `proof2.db.mysql` fails in A and in C. The
contract logs in as `admin` with the db secret. The description of the
first test sets `db_user: wordpress`, and the db secret is the password of
the account `wordpress`: a login as `wordpress` with it works, a login as
`admin` fails (log 62). This is the setup of the test, not the candidate.

## Findings that are not the candidate

1. `derived.monit` drift on a new one-node node, before any upgrade:
   core, web, lnmp, lnpp, laravel, mariadb, postgresql (not on ntfy and
   redis, which are in simple mode). The first `keel spec apply` changed 1
   item and then the drift was gone. It did not come back after B or C.
   The first test (2026-11-12) did not look at this. It is a finding about
   the first boot of a cloud_simple node with no pair, to follow up.
2. `database.server.role: drift (declared primary, observed standalone)`
   on each one-node database node. The description declares a primary, and
   no replica is connected. This is the setup of the test (one node, no
   pair), the same in A, B and C.
3. `filesync` folder and peer drift on the one-node web stacks: the folder
   is paused because the node has no peer. The same in A, B and C.
4. The runner's web screenshots did not start on the workstation (see
   above).

## Not tested

- cloud_advanced, a witness, etcd and a failover that is not planned.
  Only cloud_simple pairs, with a planned promote and return.
- A pair across two sites. Both nodes of each pair were on BR1.
- A pair of lnmp, lnpp, laravel, mariadb, postgresql, core and web. These
  were one node each, with no mesh.
- ntfy and redis in a cloud mode: their manifests have no cloud mode.
- The `db` proof on the pair nodes (not run, see above).
- The runner's screenshots (failed on the workstation, see above).
- The role screen drawn on a console with keys. We called the decision
  (`meshscreen.node_of`) directly and drew the usage box only. The
  "No database to pair" box was not drawn, because no published
  application gives a node with no engine and a pair server.
- The keel#304 case (Redis beside MariaDB, Nextcloud). No published
  application has it. The fix itself is not proved here.
- Stage B checks on the pair nodes (B installed nothing there), and
  stage B on CTs 9464 and 9465.
- A login, a write and an upload through the web front on core, web,
  lnmp, lnpp, laravel, ntfy, mariadb, postgresql and redis, and on the
  pair nodes. On these nodes the checks are the contract's (urls through
  nginx on the loopback, logins by a command on the node, rows written by
  `mysql` and `psql`), and for the pairs the cross checks (the WordPress
  login on the promoted replica goes through nginx). The web front
  checks ran on one WordPress node and one Odoo node (9464, 9465). No
  upload ran on any other node. core, mariadb, postgresql and redis have
  no web application.
- A browser that solves the Anubis challenge (as in the first test).
- A VM made from an ISO. Only LXC templates.

## Notes

- cron-apt: each node has its own random time. Its install action reads
  only `security.sources`, so it cannot see `trixie-testing`. On CT 9457
  (mariadb) it ran at about 16:01 UTC, after stage C, and changed nothing
  ("0 upgraded"). On no other node did it run during the test (log 41).
- The first creation of the nine CTs (15:42 UTC) stopped in our own
  script (a pipe got SIGPIPE under `pipefail`) before the first boot. We
  destroyed the nine CTs and made them again (log 01).
- The first run of `upgrade.sh B` stopped at its own guard (it read the
  wrong line of `keel.sources`) and changed nothing. The second run is the
  result (logs 1x-B-upgrade).
- The first stage A run on CT 9451 used `confconsole --usage` with no
  terminal: confconsole showed "Caught exception" because dialog has no
  terminal there. The second run uses `script` to give it a terminal
  (log 10).
- Log 28 holds a first comparison on CT 9461 that ran before the stage C
  of that node (an order error of our commands): it shows whole files as
  removed. The second comparison in log 28 is the result. In the same
  way, the first stage C of CT 9465 did not start; log 65 holds the run
  that did.
- Secrets: CTs 9451-9463 compared their own secret values (the
  preseeded files and `/root/ut-secrets`) with all the logs of that time,
  and the ntfy publish token and read header were compared on the
  workstation: no file holds one (log 42). The runner makes its own
  first-boot secrets, keeps none, and masks them in its record; nobody can
  compare them. A pattern scan of all files (passwords, tokens, keys,
  nonces) found nothing. Two WordPress nonces in logs 62 and 63 are
  masked.
- All CTs were destroyed at the end; `pct list` shows no CT in 9451-9479
  on BR1 and none in 9470-9479 on BR2 (log 50).

## Verdict

On every published application, the node made from the published image
gave the same results after the upgrade to keel 0.23.97 and confconsole
2.2.3+keel25 as before it. `database.server` did not change on any node.
`keel diff` and `keel spec apply` show no new drift. Replication, the VIP,
a planned promote and its return work on a MariaDB pair (WordPress) and
on a PostgreSQL pair (Odoo) after the upgrade. A login, a write and an
upload through the web front give the same results on WordPress and Odoo.
No unit failed. nginx, Monit and confconsole work. The limits are in "Not
tested": the web front checks ran on WordPress and Odoo only, and ntfy
and redis ran in simple mode.

VERDICT: PASS

## Promotion

The test passed, so the operator promoted the two packages on 2026-11-13.
The maintainer approved the promotion on 2026-11-13, on the condition
that this test passes.

- `bin/promote --yes keel=0.23.97 confconsole=2.2.3+keel25` on the build
  host, on a branch. It copied the two packages from `trixie-testing`
  into `trixie` (keel was 0.23.96, confconsole was 2.2.3+keel24).
- apt#123: the checks `security` and `tests` passed. It was merged at
  16:52:54 UTC (merge commit `5ca6f70`).
- `keel-publish-mirror --archive-only` from the workstation, exit 0 at
  16:53:08 UTC. `verify-repo` on the public name lists keel 0.23.97 and
  confconsole 2.2.3+keel25 in `trixie` and in `trixie-testing`. The suites
  `trixie`, `trixie-testing` and `trixie-security` verify.

The published images hold keel 0.23.96 until an image is built again. A
node gets 0.23.97 by its apt upgrade.

## Logs

All logs are in `repos/upgrade-test-2026-11-13/`, numbered:
00 host and template sums, 01 create, 02 first boot,
10-18 the one-node CTs (core, web, lnmp, lnpp, laravel, ntfy, mariadb,
postgresql, redis): `NN-APP-A.log`, `-B-upgrade`, `-B-checks`,
`-C-upgrade`, `-C-checks`; 19 package contents; 20-29 WordPress pair
(20 secrets, 21-22 A, 23 A cross, 24 B, 25 C upgrade, 26-27 C, 28 compare,
29 C cross); 30-39 Odoo pair (the same order); 40 compare B to C of the
one-node CTs; 41 final state and cron-apt; 42 secret scan; 50 cleanup;
60-66 the web front checks (60-61 create and first boot, 62-63
WordPress A and C, 64-65 Odoo A and C, 66 compare A to C);
`runner-wordpress/`, `runner-odoo/` the runner records. Scripts: `x.sh`,
`push.sh`, `create_ct.sh`, `make_preseed.py`, `facts.sh`,
`contract_checks.py`, `upgrade.sh`, `stage.sh`, `pair_secrets.sh`,
`watch_pair.sh`, `cross_replay.py`, `pair.env`, `wp_check.py` and
`odoo_check.py` (copies of the first test); contracts in
`contracts/` (copies from each repository's default branch, commits in
`contracts/SOURCES.txt`), descriptions in `preseed/`.
