# The Node.js bases on LNMP and LNPP: the first test by hand

Date: 2026-11-12

This file is the evidence for decision note 0091. It is a test by hand on
two containers. No image and no package was built. It is not a
commissioning test (0075). Each container was a single node in the simple
mode. No pair, no cloud mode, no Coraza and no Anubis were in the path.

## The questions

1. What does PHP cost on `lnmp`, and Python on `lnpp`, for a Node.js
   application that does not use them?
2. Does `keel-nodejs-24` install from `trixie-testing` with no other
   package from that suite?
3. Do the files of the prototypes `keel-lnmn` and `keel-lnpn` work on a
   node of the published image: the manifest, the image check, the first
   boot hook, the gate, the route and the service?
4. How many steps does a user need to put an application on the base?
5. Does a sample application answer through nginx: the health path, a
   write and a read of one row, an upload kept on disk, server-sent events
   and a websocket?
6. Does the application restart when the node binary changes?
7. What happens when the database becomes read-only?
8. How much memory does the application use at idle?

## The machines

| Item | CT 9402 (MariaDB case) | CT 9403 (PostgreSQL case) |
|---|---|---|
| Host | BR1, `hw12-br1`, pve-manager 9.2.11 | the same |
| Container | unprivileged, `nesting=1`, 2 cores, 3072 MiB, 1024 MiB swap, 8 GiB on `local-lvm` | the same |
| Network | `vtnet88` tag 5, DHCP and SLAAC, `--nameserver 2606:4700:4700::1111`. Each CT got a public IPv6 address and a private IPv4 address | the same |
| Image | `debian-13-keel-lnmp_19.0-6_amd64.tar.zst` | `debian-13-keel-lnpp_19.0-9_amd64.tar.zst` |
| sha512 | equal to the `.sha512` file of mirror.keellinux.org (`00-host.log`) | the same |
| First boot | Preseed in `/etc/inithooks.conf`: `ROOT_PASS` and `DB_PASS` made on the host with `openssl rand`, never printed, and `SKIP` for the hub key, the alerts and the updates. No `fatal` in the inithooks log | the same |
| Keel packages | keel 0.23.96, keel-web 0.4.2, keel-nodejs-24 24.22.3+keel1 | the same |
| Prototype | `keel-lnmn` (local, no remote), the commits at the time of each copy are in `10-deploy.log` | `keel-lnpn` (local, no remote) |

The logs are in `/home/navigator/Projects/Keel/repos/nodejs-bases-hand-tests/t1/`
(a local directory with no remote). `cx.sh CT LOG` and `hx.sh LOG` write
each command and its output into the log. `cx.sh` refuses every CT except
9402 and 9403. No password, key or token is in a log.

The sample application is `app/mariadb/` and `app/postgresql/` in the same
directory: one `server.js` (`node:http`, the websocket handshake of RFC 6455
with `node:crypto`, no framework) and one database driver each.

| Driver | Version | Integrity (from `package-lock.json`) |
|---|---|---|
| `mariadb` | 3.5.5 (published 2026-11-05) | `sha512-xvR622+h/ANbFvbi5SCkGnJWAFG2pGCUdSyISXXU3ObJ+P2X8KqdF8goCXquCD/lKnmqDeWfgTt1YY7dDI5i2Q==` |
| `pg` | 8.23.1 (published 2026-09-30) | `sha512-aL96AHANtWjPLDOLqnhx+ngp9+UK7ETEU8VJrDCGvsSSi/mGLcWYsS6Herg7lmaBJe4uwrfqsa7gTEFaSizDoQ==` |

`mariadb` brings 7 more packages and `pg` 13 more. Each one has its
integrity in the committed lock file. The sha256 of each file that the
user step copied is in `12-user-steps.log`.

## Results

### 1. The cost of the language that the base does not use (`03-baseline.log`, `04-php-fpm-process.log`, `20-memory-idle.log`)

| Item | CT 9402 on `lnmp` | CT 9403 on `lnpp` |
|---|---|---|
| Unused packages, installed size | `php*`: 23,883 kB (`php8.4-common`, `-fpm`, `-cli`, `-opcache`, `-mysql`, `-readline`) | `gunicorn` and `python3-psycopg`: 761 kB. Python 3 is in Core: `keel` depends on it |
| Unused process at idle | `php8.4-fpm.service`: 3 processes, RSS 35.9 MB in sum, cgroup 20.6 MB | none after the layer removes the check page |
| Watched by Monit | yes: `keel manifest show lnmp --resolved` lists `php-fpm` (`php8.4-fpm.service`, from `lnmp`) as a process. A child manifest only adds (`keel/manifest/resolve.py`) | no process of `lnpp` but PostgreSQL |
| Security updates waiting in the stable image | 6 `php8.4-*` packages (8.4.26 to 8.4.27-1~deb13u1) | none for Python |

On `lnpp`, the check page of the stack ran after the first boot: gunicorn,
3 processes, RSS 62 MB in sum, started at 07:22:02, the time of the first
boot. The check hook asked the page once, and the socket unit kept the
service. This is a fact of the `lnpp` image, not of the prototype.

### 2. The Node.js package from `trixie-testing` only (`05-nodejs-install.log`)

- A general record `Package: * Pin: release n=trixie-testing
  Pin-Priority: -1` in a file named `nb-t1-testing-only` did not win: the
  general record of `/etc/apt/preferences.d/keel` (`o=Keel Linux`, 990)
  comes first in the order of the files, and apt took it. `keel-web` 0.4.4
  of testing was then a candidate. The file was renamed
  `00-nb-t1-testing-only`, and `keel-web` went back to 0.4.3 of `trixie`.
- The record of a named package won in both orders: `keel-nodejs-24` had
  priority 500 before and after the rename.
- `apt-get -s install keel-nodejs-24` installed one package and changed no
  other. Installed: `keel-nodejs-24 24.22.3+keel1`, `node v24.22.3`, `npm
  11.19.1`, `/usr/bin/node` a link to `/usr/lib/keel-nodejs/bin/node`.

### 3. The prototype on the node (`10-deploy.log`, `11-firstboot-hook.log`)

- `conf.d/main` of each prototype ran on the node: the user `app`, `/srv/app`,
  `/var/lib/keel-app/files`, the parent check page removed, the units
  enabled.
- `keel manifest validate lnmn`: ok, "resolved along core, web, lnmp,
  lnmn". `keel manifest validate lnpn`: ok, "resolved along core, web,
  lnpp, lnpn".
- The first run of the image check failed on a real defect of the check:
  `keel-nodejs-24` ships `/usr/bin/node` as a relative link
  (`../lib/keel-nodejs/bin/node`), and the check compared the absolute
  path. A test came first, then the fix. Then the image check passed on
  both nodes.
- On 9403, `userdel keel-check` failed while the gunicorn of the check
  page ran as that user. A build tree has no running process, so the build
  is not affected. The service was stopped and the step ran again.
- `nginx -t` passed with the route of the base as the only file of
  `keel-default.d`.
- Before the hook, `https://127.0.0.1/` answered 503 with the page "The
  application does not serve on this node". `/keel-health` answered 204.
- The hook `42keel-app` made the database `app` and the account `app`:
  - MariaDB: `GRANT USAGE ON *.* ... IDENTIFIED VIA unix_socket` and `GRANT
    ALL PRIVILEGES ON app.*`, nothing global. `runuser -u app -- mysql`
    logged in as `app@localhost`.
  - PostgreSQL: role `app`, not superuser, no `CREATEDB`, no `CREATEROLE`,
    no password (`rolpassword IS NULL`). Database `app`, owner `app`.
    `runuser -u app -- psql` logged in as `app`.
  - `/etc/keel-app/database.env`: mode 0640, `root:app`, the socket and the
    account. It has no password, because there is none.

### 4. The steps of the user (`12-user-steps.log`)

Two steps, on each node:

1. Copy `server.js`, `package.json` and `package-lock.json` into
   `/srv/app`.
2. Run `/usr/lib/keel-app/keel-app-install`.

`npm ci` took 1 s (8 packages, MariaDB) and 0.9 s (14 packages,
PostgreSQL). `/srv/app` and `node_modules` became `app:app`. The gate
opened, and `/health` answered at once. The install command ran a gate
pass that started the service, then a `try-restart`: the service started
twice. No setting in `/etc/keel-app/app.env` was necessary.

### 5. Through nginx (`13-through-nginx.log`, `14-through-nginx-2.log`, `15-websocket-files-sandbox.log`)

- The first requests from the BR1 host to the public IPv6 address of each
  CT got `Server: SimpleHTTP/0.6`, not nginx. The TurnKey init fence of the
  image redirects outside ports 80, 443, 12321 and 12322 to
  `simplehttpd.py` (`iptables -t nat`, `REDIRECT --to-ports 60080/60443`)
  until keel-init runs. The preseed ran no keel-init. The requests to
  `127.0.0.1` reached nginx. `systemctl stop turnkey-init-fence` removed the
  redirect, as the end of keel-init does.
- After that, from the host over IPv6, on both nodes:

| Check | CT 9402 | CT 9403 |
|---|---|---|
| `GET /health` over HTTPS | 200, `Server: nginx`, 12 ms, `db: writable` | 200, 18 ms, `db: writable` |
| `POST /row`, then `GET /row` | 200, the row came back with its time | the same |
| `PUT /files/upload-1.bin` (200,000 random bytes), then `GET` | 201, the same sha256 back | the same |
| A file name with `../` | 400 | 400 |
| `GET /health` on port 80 (0079) | 200 | 200 |
| `GET /events` (server-sent events) | an event every 1.0 s, each read 2 to 5 ms after the time in it: nginx did not buffer | the same |
| Websocket handshake over HTTPS, HTTP/1.1 | `101 Switching Protocols`, `Sec-WebSocket-Accept` correct | the same |
| Websocket from the node client of Node.js 24 over port 80 | the server frame, then the echo of `ping-1`, in 28 ms | in 20 ms |

  The line "timeout" after each websocket result is the timer of the test
  client, which ran after the close. It is not a failure.
- The uploaded file is on disk: `/var/lib/keel-app/files/upload-1.bin`,
  200,000 bytes, `app:app`.
- In the mount namespace of the service, the user `app` cannot write
  `/srv/app` ("Read-only file system") and can write
  `/var/lib/keel-app/files`. The unit has `ProtectSystem=strict`,
  `ReadWritePaths=/var/lib/keel-app`, `NoNewPrivileges=yes`.

### 6. A change of the node binary (`16-runtime-restart.log`, `19-read-only-postgresql.log`)

`trixie-testing` has one version of the package, so the change was
`apt-get install --reinstall keel-nodejs-24`. dpkg put a new file in place
(a new inode).

| Case | CT 9402 | CT 9403 |
|---|---|---|
| `keel-runtime-restart.path` stopped | the PID stayed (5891); `/proc/5891/exe` showed `/usr/lib/keel-nodejs/bin/node (deleted)` | the same (6011) |
| `keel-runtime-restart.path` active | a new PID (7637); `exe` without `(deleted)` | a new PID (7915) |
| The application stopped by the gate | not done | `keel-app.service` stayed `inactive`: the restart of `keel-runtime.target` does not start a unit that does not run |

The path unit started its service twice for one reinstall, 1.07 s and
1.10 s apart. So the application restarted twice. Each restart took 0.25 to
0.35 s from "Stopping" to "listening". A change to the next line
(`keel-nodejs-26`) was not tested: no package of line 26 exists.

### 7. A read-only database (`17-read-only-mariadb.log`, `18-read-only-mariadb-2.log`, `19-read-only-postgresql.log`)

With `KEEL_APP_SERVE=all` (the application serves on every node):

| Engine | How | `/health` | `GET /row` | `POST /row` |
|---|---|---|---|---|
| MariaDB | `SET GLOBAL read_only = 1` | 200, `db: read-only` | 200, the row | 503 from the application, `ER_OPTION_PREVENTS_STATEMENT` |
| PostgreSQL | `standby.signal`, restart: `pg_is_in_recovery()` = `t` | 200, `db: read-only` | 200, the row | 503 from the application, SQLSTATE `25006` |

The pool of `pg` connected again after the restart of PostgreSQL with no
action.

With `KEEL_APP_SERVE=writer` (the default), probes every 0.25 s:

| Engine | Event | What the probe saw |
|---|---|---|
| MariaDB, first run | read-only at 07:43:34.40 | writes 503 from the application, then the gate closed at 07:43:38.67 (4.3 s): the route answered 503 with the notice and the service stopped |
| MariaDB, first run | writable at 07:43:43.50 | one answer 502 at 07:43:43.92, then 200 from 07:43:44.26 |
| MariaDB, after the fix | read-only at 08:09:46.33 | the gate closed at 08:09:50.98 (4.6 s) |
| MariaDB, after the fix | writable at 08:09:55.39 | 503 until the application listened, then 200 from 08:09:56.67 (1.3 s), no 502 |
| PostgreSQL | a gate pass in recovery | closed, the service `inactive`, 503 with the notice |
| PostgreSQL | `pg_ctlcluster 17 main promote` at 08:10:45.33 | 200 from 08:10:47.96 (2.6 s), no 502 |

The 502 of the first run came from the gate: it wrote the mark when
`systemctl start` returned, and node listened 0.25 s later. A test came
first, then the fix: the gate waits until `127.0.0.1:3000` accepts a
connection, up to 15 s, before it writes the mark. The close takes up to
one tick of the timer (5 s): the watch on addresses sees no change of the
database.

### 8. Memory at idle (`20-memory-idle.log`)

After 60 s with no request:

| Item | CT 9402 (`mariadb` driver) | CT 9403 (`pg` driver) |
|---|---|---|
| node, RSS | 72.0 MB (anonymous 26.1 MB, file 45.9 MB) | 56.7 MB (anonymous 15.8 MB, file 40.9 MB) |
| `keel-app.service`, cgroup | 27.9 MB | 17.2 MB |
| `php8.4-fpm.service`, cgroup | 20.6 MB | not there |
| The database service, cgroup | `mariadb` 139.6 MB | `postgresql@17-main` 39.3 MB |
| `nginx.service`, cgroup | 4.7 MB | 4.6 MB |
| `free -m`, used | 226 MB of 3072 MB | 134 MB of 3072 MB |

### 9. A reboot (`21-reboot.log`)

`keel-app.service` is `static`: nothing enables it. After `pct reboot`, the
gate started it on both nodes. node listened 1.7 s after "Startup
finished", and `/health` answered 200.

### 10. A manifest of the user (`22-user-manifest.log`)

A file `/usr/share/keel/appliances/myapp.yaml` with `base: lnmn` and a
second replicated path `/var/lib/keel-app/media`:

- `keel manifest validate myapp`: ok, "resolved along core, web, lnmp,
  lnmn, myapp";
- the resolved replicated paths: `/var/www/keel-default` (web),
  `/var/lib/keel-app/files` (lnmn), `/var/lib/keel-app/media` (myapp);
- `keel inspect` named the appliance `myapp`.

The file was removed after the test. The spec of keel has no field for a
replicated path (`keel/spec/`). Syncthing did not run: no pair existed.

## Not tested

- A pair (0049, 0054), the VIP, the role file, Syncthing on
  `/var/lib/keel-app/files`, a promote and a failover.
- The cloud modes: Coraza and Anubis in the path of a websocket, of the
  server-sent events and of an upload.
- An image built from the prototypes, its first boot, keel-init with
  questions, and the commissioning of 0075.
- A change to the next Node.js line.
- A native module (an npm package that compiles with node-gyp).
- The upgrade of the application code by a user (a second
  `keel-app-install` with new code).

## What was left

- CT 9402 and CT 9403 are stopped. They hold the test files
  `/root/nb-proto`, `/root/nb-main.out`, `/root/nb-probe.sh`, the pin
  `/etc/apt/preferences.d/00-nb-t1-testing-only`, the `trixie-testing`
  source enabled, and the preseed file `/etc/inithooks.conf`.
- The BR1 host keeps no file of the test.
