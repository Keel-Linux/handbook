# 0091: Two Node.js bases, LNMN on LNMP and LNPN on LNPP, for an application of the user

Date: 2026-11-12
Status: **proposed.** The maintainer decided on 2026-11-12 that Keel
publishes two base stacks for Node.js before more Node.js applications:
nginx, Node.js and MariaDB, and nginx, Node.js and PostgreSQL. Each base is
also a product: a user puts their own Node.js application on it. This note
answers how. The questions at the end are open. Nothing in it is built or
published. The prototypes are two local repositories, `keel-lnmn` and
`keel-lnpn`, with no remote.

The evidence is `evidence/2026-11-12-nodejs-bases-hand-test.md`: a test by
hand on two containers of BR1, one on the published `lnmp` image and one on
the published `lnpp` image, with the files of the prototypes.

## What was asked

1. Which layer is the parent of each Node.js base, and what does each
   option cost?
2. What are the names of the layers and of the repositories?
3. What is the contract of a language base: the runtime, the service, the
   route, the gate, the replicated files, the database, the logs and the
   upgrades?
4. What does a user do to put an application on the base, and what does
   the first boot ask?
5. What does the same model need for Ruby, and for Go and Rust?

## Facts checked

Read in the repositories on 2026-11-12 (`main`, or `master` for
keel-web).

| Item | Fact | Source |
| --- | --- | --- |
| `web` | nginx, Coraza, Anubis and Syncthing on Core. No database. Replicates `/var/www/keel-default` | `keel-web/packages/keel-web/manifest.yaml`, `plan/main` |
| `lnmp` | `web` plus MariaDB (`turnkey/mysql`, `mariadb-client`) and PHP-FPM 8.4 (`php-fpm`, `php-mysql`). Processes `mariadb` and `php-fpm` (`php8.4-fpm.service`). Check page `/keel-check/` in PHP | `keel-lnmp/plan/main`, `overlay/usr/share/keel/appliances/lnmp.yaml`, `overlay/etc/nginx/keel-default.d/50-keel-lnmp.conf` |
| `lnpp` | `web` plus PostgreSQL 17, `python3`, `gunicorn`, `python3-psycopg`. No PHP. Process `postgresql` only. The check page is a gunicorn socket unit, not a process | `keel-lnpp/plan/main`, `overlay/usr/share/keel/appliances/lnpp.yaml` |
| `mariadb`, `postgresql` | the database on Core (`base: core`). No nginx | `keel-mariadb/plan/main`, `keel-postgresql/overlay/usr/share/keel/appliances/postgresql.yaml` |
| Python in Core | `keel` depends on `python3 (>= 3.12)` and `python3-yaml` | `keel/debian/control` |
| The database half | `lnmp` and `lnpp` copy the files of the database layers (0059, point 3): `99-keel-bind.cnf`, `35mysqlpass`, `dbpass.py`, `lib/mariadb.sh`, the socket masks; `36pgsqlverify`, `lib/postgresql.sh`, the `listen_addresses` and `PASSWORD NULL` steps | `keel-lnmp/overlay`, `keel-lnmp/conf.d/main`, `keel-lnpp/overlay`, `keel-lnpp/conf.d/main` |
| `unit-mariadb`, `unit-postgresql` | the TurnKey component only (`plans/turnkey/mysql`, `conf/mysql`, `overlays/mysql`). Not the Keel files of the row above | `unit-mariadb/README.rst`, `unit-postgresql` tree |
| A child manifest | "a child only adds": it cannot remove a process of its parent | `keel/keel/manifest/resolve.py`; `docs/manifest-v1.md`, "Resolution" |
| Replicated paths | `state` adds up along the chain | `keel/keel/manifest/resolve.py`, `_application` |
| Spec | no field for a replicated path | `keel/keel/spec/` |
| Owner of a received file | each Syncthing folder sets `copyOwnershipFromParent` | `keel/keel/system/filesync.py` |
| Role file | `/var/lib/keel/role`, lines `role=` and `vip=` | `keel-nextcloud/overlay/usr/lib/inithooks/lib/nextcloud.sh`, `keel/keel/system/filesync.py` |
| Node.js package | `keel-nodejs-24` 24.22.3+keel1 in `trixie-testing`. `Provides` and `Conflicts` `keel-nodejs`. Links in `/usr/bin`. No maintainer script | `keel-nodejs/packages/keel-nodejs/debian/control`, `keel-nodejs-24.links`; 0083, amendment |
| NodeBB | a layer on `lnpp` with the apt pin of line 24, a path unit on the node binary, its own watcher `serve.py`, routes in `keel-default.d` and `keel-front.d` | `keel-nodebb` (branch `feat/nodebb-on-lnpp`), `overlay/etc/apt/preferences.d/keel-nodebb-nodejs`, `overlay/usr/lib/systemd/system/nodebb-nodejs.path` |
| Nextcloud | the gate of 0087: `read_only = 0`, `role=primary`, the VIP on the node, at each address event and every 5 s | `keel-nextcloud/overlay/usr/lib/keel-nextcloud/keel-nextcloud-gate` |
| `keel-nodejs-nginx` | a layer on Core: `nodejs`, `npm`, `redis-server` of Debian, `turnkey/nginx.mk`. No Keel Web, no manifest, no tests | `keel-nodejs-nginx/plan/main`, `Makefile` (main `07facd5`) |
| Published images | core, web, lnmp 19.0-6, lnpp 19.0-9, mariadb, postgresql, redis, ntfy, wordpress, laravel, odoo | mirror.keellinux.org/images/ |
| Layers on `lnmp` | wordpress, laravel (published); nextcloud, pixelfed, loops, ojs (in work) | the `base:` of each manifest; 0084 |
| Layers on `lnpp` | odoo (published); nodebb (in work) | the same |

## What the hand test showed

1. **Unused PHP costs a running service.** On the `lnmp` node,
   `php8.4-fpm.service` used 20.6 MB (cgroup) at idle, the `php*` packages
   use 23.9 MB of disk, and 6 of them waited for a Debian security update
   in the stable image. Monit watches `php-fpm` when keel renders the
   monitor, because it is a process of `lnmp`.
2. **Unused Python costs nearly nothing.** On the `lnpp` node, `gunicorn`
   and `python3-psycopg` use 761 kB of disk. Python 3 is in Core. Nothing
   runs after the layer removes the check page.
3. **Two steps put an application on the base.** Copy the code into
   `/srv/app`, then run `keel-app-install`. `npm ci` took about 1 s.
4. **Socket authentication works with both drivers.** `mariadb` 3.5.5 over
   `unix_socket` and `pg` 8.23.1 over `peer`, with no password anywhere.
5. **The route carries everything.** Through nginx: the health path, a
   write and a read, an upload of 200,000 bytes with the same sha256 back,
   server-sent events with no buffer, a websocket (101 and an echo).
6. **The path unit restarts the application on a new binary.** Without it,
   the process keeps the deleted binary. It fired twice for one reinstall.
7. **The gate works on both engines.** A read-only MariaDB and a
   PostgreSQL in recovery closed the route in 4.3 to 4.6 s (one tick of the
   timer). A writable database opened it again in 1.3 to 2.6 s. The first
   run showed one 502; the gate now waits until the application listens.
8. **Idle memory.** node with the `mariadb` driver: 27.9 MB (cgroup),
   72.0 MB RSS. node with `pg`: 17.2 MB, 56.7 MB RSS.

## Why (brief section 10)

1. **Why the current approach is not enough.** Keel has no Node.js stack.
   0082 put NodeBB on `lnpp`, with its Node.js setup in the NodeBB layer.
   A user who wants to run their own Node.js application must copy that
   setup. Each later Node.js layer (Ghost, Mastodon streaming) would copy
   it again.
2. **Whether it can be made to work.** It can, with parts that exist and
   passed tests: `keel-nodejs-24` (0083), the stacks `lnmp` and `lnpp` with
   their pairs, the route directory of keel-web (0059, point 4), the gate of
   0087. The hand test ran the prototype on the published images.
3. **Why this is better.** The service, the route, the gate, the restart on
   a new runtime and the database account are written and tested once. An
   application layer or a user adds only what is their own (0089).

## Decision (proposed)

### 1. The parent of each base

The answer is not the same for the two engines:

- **PostgreSQL: `lnpp` gives it.** `lnpp` has nginx, PostgreSQL, the pair
  and the cloud modes, and no PHP. Its Python is in Core already. What
  `lnpp` adds and the Node.js base does not use is `gunicorn` and
  `python3-psycopg`, 761 kB of disk, and a check page that the base
  removes.
- **MariaDB: no layer gives it.** `web` has no database, `mariadb` has no
  nginx, and `lnmp` carries PHP-FPM, which runs and which Monit watches.

| Option | What changes | Images to build and to commission (0075 on BR1 and BR2) | Other cost |
| --- | --- | --- | --- |
| A. New parents `web` plus MariaDB and `web` plus PostgreSQL, under the PHP stacks, the Python stack and the Node.js stacks | the chain of `lnmp` and `lnpp`, and of every layer on them | 9: the 2 parents, `lnmp`, `lnpp`, wordpress, laravel, odoo, and the 2 Node.js bases. The 5 layers in work (nextcloud, pixelfed, loops, ojs, nodebb) test again on the new chain | The manifests are files of the image, so an installed node keeps its old chain. Two chains exist in the field |
| B. **The Node.js bases on `lnmp` and `lnpp`** | nothing that exists | 2 | On LNMN: PHP-FPM runs, 20.6 MB at idle, 23.9 MB of disk, Debian security updates of PHP, a Monit process. No route reaches PHP: the only `fastcgi_pass` lines left are comments of Debian's `sites-available/default`, which is not enabled (evidence, result 1). On LNPN: 761 kB of disk, nothing runs |
| C. The Node.js bases on `web`, each with a copy of the database half | nothing that exists | 2 | A third copy of the MariaDB half and of the PostgreSQL half (the files of "Facts checked"). A fix of one copy must go to three |
| D. One overlay package for each engine first (0059, point 3), then C with no copy | the database layers and the stacks use the packages | 9: mariadb, postgresql, `lnmp`, `lnpp`, wordpress, laravel, odoo, and the 2 Node.js bases. Also 2 new packages | the largest work before the first Node.js base |

**Recommendation: B.** It changes nothing that is published and needs 2
commissionings. The cost of PHP on LNMN is measured and small, and the
layer removes the only route to it. When the packages of D exist, a later
note can move the Node.js bases to `web`, with a new commissioning.

### 2. Names

The letters follow LNMP and LNPP: Linux, nginx, the database, the language.

| Layer | Chain | Repository | Image |
| --- | --- | --- | --- |
| `lnmn` | Core, Web, LNMP, LNMN | `Keel-Linux/keel-lnmn` | `debian-13-keel-lnmn_19.0-N_amd64` |
| `lnpn` | Core, Web, LNPP, LNPN | `Keel-Linux/keel-lnpn` | `debian-13-keel-lnpn_19.0-N_amd64` |

The repositories are not created. Ruby would be `lnmr` and `lnpr`.

### 3. The contract of a language base

The names are general. No file of the base names an application (0089). A
test of each prototype fails when a line that is not a comment contains a
name of `tests/application-names`.

| Part | The contract | File of the prototype |
| --- | --- | --- |
| Runtime | `keel-nodejs-24` from the plan. No other Node.js | `plan/main` |
| Line pin | `keel-nodejs-24` at 500, `keel-nodejs` and `keel-nodejs-*` at -1. A record of a named package wins over the general records of `preferences.d/keel` in any order of the files (evidence, result 2) | `overlay/etc/apt/preferences.d/keel-nodejs-line` |
| User | `app`, a system user, no shell, home `/var/lib/keel-app`, made at build time, so it has the same uid on each node of one image. Syncthing gives a received file the owner of its folder | `conf.d/main` |
| Code | `/srv/app`, read-only for the service (`ProtectSystem=strict`). `keel-app-install` makes it `app:app` and runs `npm ci --omit=dev` from the committed `package-lock.json` (0083). Dependencies with no lock file are refused | `overlay/usr/lib/keel-app/keel-app-install` |
| Service | `keel-app.service`: `User=app`, `WorkingDirectory=/srv/app`, `HOST=127.0.0.1`, `PORT=3000`, `NODE_ENV=production`, then `EnvironmentFile=/etc/keel-app/database.env` and `-/etc/keel-app/app.env`, `ExecStart=keel-app-run` (node runs the file `KEEL_APP_MAIN`, default `server.js`), `Restart=on-failure`, `ReadWritePaths=/var/lib/keel-app`. No `[Install]`: the gate starts it. Not a process of the manifest, for the Monit reason of 0082 | `overlay/usr/lib/systemd/system/keel-app.service`, `overlay/usr/lib/keel-app/keel-app-run` |
| Restart on a new runtime | `keel-runtime-restart.path` watches `/usr/lib/keel-nodejs/bin/node` and runs `systemctl try-restart keel-runtime.target`. A unit joins with `PartOf=keel-runtime.target`. A unit that does not run stays stopped (evidence, result 6) | `keel-runtime.target`, `keel-runtime-restart.path`, `keel-runtime-restart.service` |
| Route | `keel-default.d/60-keel-app.conf`: `location ~ ^/`, because keel-web owns `location /`. `proxy_pass http://127.0.0.1:3000`, HTTP/1.1, `Upgrade` and `Connection` on every path, read timeout 3600 s. Server-sent events pass when the application sends `X-Accel-Buffering: no`. The application adds its own lines in `/etc/nginx/keel-app.d/*.conf` (the body limit is there, 16 MB). In the cloud modes the front site of keel-web reads a request first, with a limit of 1 MB: `keel-front.d/60-keel-app-body.conf` gives it the same 16 MB. Anubis challenges every path in the cloud modes. A path that a client with no browser uses (an API, a webhook) passes Anubis only with a location of the application in `keel-front.d`, as Nextcloud does (0087, section 7) | `overlay/etc/nginx/keel-default.d/60-keel-app.conf`, `conf.d/keel-app.conf`, `keel-app.d/10-keel-app-body.conf`, `keel-front.d/60-keel-app-body.conf` |
| Gate | `keel-app-gate` every 5 s and at each address event. The application declares `KEEL_APP_SERVE` in `app.env`: `writer` (the default) or `all`. `writer`: the node serves when the first boot is done, the main file is there, the role file is absent or says `role=primary`, its VIP is on the node, and the database takes writes (`read_only = 0`; `pg_is_in_recovery()` false and read-write). `all`: every ready node serves, and the application must accept a read-only database. "Open": start the service, wait until port 3000 accepts, then write `/run/keel-app/open`. "Closed": remove the mark, then stop the service. nginx answers 503 with a notice while the mark is absent. `keel-app-gate --state` prints why | `overlay/usr/lib/keel-app/keel-app-gate`, `lib/keel-app.sh` |
| Replicated files | the base declares `state.replicate: [/var/lib/keel-app/files]`, given to the application as `KEEL_APP_FILES`. The application makes subdirectories there. A layer on the base, or a manifest of the user with `base: lnmn` (evidence, result 10), adds paths. The spec cannot | `overlay/usr/share/keel/appliances/lnmn.yaml`, `lnpn.yaml` |
| Database | the first boot makes the database `app` and the account `app` on the node that takes writes, with socket authentication (`unix_socket`, `peer`) and rights on `app` only, so `read_only` stops it. A replica gets them from the primary. `/etc/keel-app/database.env` (0640, `root:app`) gives `KEEL_DB_ENGINE`, `KEEL_DB_NAME`, `KEEL_DB_USER`, `KEEL_DB_SOCKET`, `DATABASE_URL`, and for PostgreSQL `PGHOST`, `PGUSER`, `PGDATABASE`. It holds no secret | `overlay/usr/lib/inithooks/firstboot.d/42keel-app` |
| Logs | the journal: `journalctl -u keel-app`, and the tag `keel-app` for the gate. No log file | `keel-app.service` |
| Upgrade within the line | `apt upgrade` brings the new `keel-nodejs-24` through the Keel channel. The path unit restarts the application (measured with a reinstall; it restarts twice) | `keel-runtime-restart.path` |
| Upgrade to the next line | the pin refuses it. The operator edits the pin, installs `keel-nodejs-26` (it removes line 24, `Conflicts`), runs `keel-app-install` to build native modules for the new ABI, and tests. Not measured: no package of line 26 exists | README of each prototype |
| Upgrade of the application | new code in `/srv/app`, then `keel-app-install`. If `npm ci` fails, the service keeps the code it runs. Not measured | `keel-app-install` |

The base removes the check page of its parent, as keel-odoo and keel-nodebb
remove the page of `lnpp`. The check page of the base itself (0059, point
6: a read-only Node.js page that reads a row of the first boot) and the
contract `tests/commission.yaml` (0075) are not in the prototypes.

### 4. What the user does, and what the first boot asks

1. Copy the code into `/srv/app`: the main file, `package.json` and the
   committed `package-lock.json`.
2. Run `/usr/lib/keel-app/keel-app-install` as root.

That is all for an application that reads `HOST`, `PORT`, `DATABASE_URL`
(or `PG*`) and `KEEL_APP_FILES`. Other settings go in
`/etc/keel-app/app.env`.

The first boot asks what the parent asks. The base adds no question,
because the account of the application has no password. The list of the
parent comes from the preseed of the hand test and the names of the hooks:
the root password, the password of the database administrator
(`DB_PASS`), and the items of TurnKey (the hub key, the security alerts,
the security updates). keel-init did not run in the test, so the screens
are not checked.
Until keel-init has run, the init fence of TurnKey redirects outside ports
80 and 443 to its own page (evidence, result 5).

### 5. Ruby later; Go and Rust

**Ruby.** The model stays: the user, `/srv/app`, the service, the gate, the
route, the replicated directory, the database account and the logs. These
parts change:

- the runtime: Debian 13 `ruby`, or a Keel package of one line if the
  Debian line is too old or ends early, as 0083 says for Node.js. This is
  not checked;
- the install: `bundle install` with `BUNDLE_DEPLOYMENT=1` and
  `BUNDLE_WITHOUT=development:test` from the committed `Gemfile.lock`, in
  place of `npm ci`. Native gems need a compiler and headers at install
  time;
- the start: `keel-app-run` runs the application server (for example
  `bundle exec puma`) on `127.0.0.1:3000`;
- the path unit watches the Ruby binary.

**Go and Rust** need no runtime package, no line pin and no path unit: the
binary is the application, and a new binary is a new install. They use the
user, `/srv/app`, the service with `keel-app-run` that runs the binary
itself, the gate, the route, the replicated directory, the database
account and the logs. When a second language base comes, the service model
can move into one package that each base installs.

### 6. `keel-nodejs-nginx`

Not reused. Its parts are Debian's `nodejs` 20, `npm` and `redis-server` on
Core, with no Keel Web and no manifest. LNMN and LNPN replace it as the
Node.js stack. 0082 decided that it gets no new build and is archived after
NodeBB passes the commissioning of 0082 step 7, and that the name is not
used again. This note does not change that.

## Not tested

- A pair, the VIP, the role file, Syncthing on the replicated directory, a
  promote and a failover.
- The cloud modes: Coraza and Anubis with a websocket, server-sent events
  and an upload, and the body limit of `keel-front.d`.
- Monit on `php-fpm` in a cloud mode.
- That the account `app` replicates to the replica of a pair. It is in the
  `mysql` database (MariaDB) or the cluster catalogue (PostgreSQL), which a
  pair replicates (0059, point 3), so it is expected.
- An image built from the prototypes, its first boot with keel-init, and
  the commissioning of 0075.
- The next Node.js line, a native npm module, an upgrade of the code of the
  application.

## Open points

1. The path unit fires twice for one change of the binary, about 1.1 s
   apart, so the application restarts twice. A rate limit or a short delay
   in `keel-runtime-restart.service` can make it one restart. NodeBB's
   `nodebb-nodejs.path` has the same unit form.
2. The gate closes up to 5 s after the database becomes read-only. Until
   then the application answers writes with its own error. 0087 has the
   same delay.
3. `keel-app-install` starts the service in its gate pass, then restarts it.
4. The proto map of the route copies NodeBB's. keel-web 0.4.4 gives
   `$keel_web_https` (0087, section 7). The route can use it when 0.4.4 is
   in the stable suite.
5. The gate closes the site when the database does not answer, as the gate
   of 0087 does. So each restart of MariaDB or PostgreSQL, for example by a
   security update, also stops and starts the application. `serve.py` of
   NodeBB does the opposite: with no answer it changes nothing. The base
   follows 0087, the choice that fails closed.
6. On `lnpp`, the gunicorn of the check page runs from the first boot to
   the next reboot (62 MB RSS, evidence, result 1). That is a fact of
   `lnpp`, not of this note.

## What this amends

- **0082, section 1**: "no Node.js stack". Keel gets two Node.js stacks as
  a product. NodeBB stays on `lnpp` in this note (question 5).

It applies 0047, 0050, 0059, 0068, 0075, 0079, 0083, 0087, 0089 and 0090.

## Questions for the maintainer

1. The parent of the two bases: A, B, C or D (section 1)?
   Recommendation: **B**.
2. The names `lnmn` and `lnpn`, and the repositories `Keel-Linux/keel-lnmn`
   and `Keel-Linux/keel-lnpn`: yes or no? Recommendation: **yes**.
3. The contract of section 3, with `KEEL_APP_SERVE=writer` as the default:
   yes or no? Recommendation: **yes**.
4. Create the two repositories, add the check page and the contract of
   0075, and build the two images on the testing track for commissioning:
   yes or no? Recommendation: **yes**, after questions 1 to 3.
5. NodeBB stays on `lnpp` until its own commissioning, and a move to `lnpn`
   is a later decision: yes or no? Recommendation: **yes**.
