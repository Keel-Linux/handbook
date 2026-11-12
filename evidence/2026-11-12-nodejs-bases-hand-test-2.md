# LNMN on Keel Web with MariaDB and no PHP: the second test by hand

Date: 2026-11-12

This file is the evidence for the amendment of decision note 0091 (t2). The
maintainer decided that LNMN is a layer on `web` with MariaDB in the layer
and no PHP. This test repeats the MariaDB checks of the first test
(`evidence/2026-11-12-nodejs-bases-hand-test.md`, t1) on that layer. It is
a test by hand on one container. No image and no package was built. It is
not a commissioning test (0075). The node was a single node in the simple
mode.

## The questions

1. Does the image of LNMN have no PHP: no package, no unit, no process?
2. Do the copies of the MariaDB half of `keel-lnmp` work on a `web` node:
   the bind, the socket masks, the admin account from `DB_PASS`?
3. Do the t1 checks pass again: the manifest, the image check, the first
   boot hook, the user steps, the route, the websocket, the server-sent
   events, the upload, the restart on a new node binary, a read-only
   database, the idle memory, a reboot?
4. Does `keel-nodejs-24` install from the stable suite `trixie`?

## The machine

| Item | Value |
|---|---|
| Container | CT 9402 on BR1, destroyed and made again: unprivileged, `nesting=1`, 2 cores, 3072 MiB, 1024 MiB swap, 8 GiB on `local-lvm`. No other CT was touched (`cx2.sh` refuses every CT except 9402) |
| Network | `vtnet88` tag 5, DHCP and SLAAC, `--nameserver 2606:4700:4700::1111`. Public IPv6 address and private IPv4 address |
| Image | `debian-13-keel-web_19.0-13_amd64.tar.zst`, the published stable `web`. Its sha512 is equal to the `.sha512` file of mirror.keellinux.org (`00-host.log`) |
| First boot | Preseed in `/etc/inithooks.conf`, made on the host with `openssl rand`, never printed. No `fatal` in the inithooks log |
| Keel packages | keel 0.23.96, keel-web 0.4.2, keel-overlay-coraza 0.1.4 of the image; keel-nodejs-24 24.22.3+keel1 from `trixie` |
| Prototype | `keel-lnmn` (local, no remote) at `a1668c0`, then the gate, the library and the install command at `efbcb17` (`04-deploy.log`) |
| common | `overlays/mysql` and `conf/mysql` of `Keel-Linux/common` at `5feab33` |

The logs are in `/home/navigator/Projects/Keel/repos/nodejs-bases-hand-tests/t2/`.
No password, key or token is in a log. The sample application is the one
of t1 (`app/mariadb/`, the same sha256, `09-user-steps.log`).

## How the layer was made on the node

The node is not an image of LNMN. The build steps ran by hand on the `web`
node, in the order of a build:

1. `apt-get install` of the plan: `default-mysql-server python3-pymysql
   webmin-mysql mysqltuner` (`turnkey/mysql`), `mariadb-client`,
   `inithooks confconsole keel`, `keel-nodejs-24`. Only `trixie` and
   `trixie-security` were enabled. `trixie-testing` stayed off, and no test
   pin was written (`03-plan-packages.log`).
2. common's `overlays/mysql` and `conf/mysql` (`04-deploy.log`,
   `05-conf-scripts.log`).
3. The overlay of `keel-lnmn`, with owner root and modes 755 and 644 at the
   copy. The owners and the modes of `/` and of each directory were checked
   after the copy (`04-deploy.log`).
4. `conf.d/10-mariadb`, then `conf.d/main` (`05-conf-scripts.log`).
5. The first boot hooks `35mysqlpass` and `42keel-app` (`06-firstboot-hooks.log`,
   `08-mysqlpass-preseed.log`).

## Results

### 1. No PHP (`03-plan-packages.log`, `07-baseline-no-php.log`, `16-reboot.log`)

- The `web` image had no `php*` and no `mariadb*` package (`02-firstboot.log`).
- The plan installed 26 packages. None of them is PHP or Apache.
- After the build steps and after a reboot: 0 installed `php*` packages, 0
  PHP units in `/usr/lib/systemd/system`, 0 PHP processes, 0 PHP units in
  `systemctl list-units --all`, no `php` binary, no `fastcgi_pass` that is
  not a comment in `/etc/nginx`.
- The resolved manifest of `lnmn` lists the processes of Core and Web and
  `mariadb` from `lnmn`, no `php-fpm` (`07-baseline-no-php.log`,
  `17-manifest-and-cleanup.log`).

### 2. The MariaDB half (`05-conf-scripts.log`, `06-firstboot-hooks.log`, `08-mysqlpass-preseed.log`)

- `conf.d/10-mariadb` ran with no error: the admin accounts for
  `localhost`, `::1` and `127.0.0.1`, both socket units masked (links to
  `/dev/null`), `keel-socket-wildcard / 3306` passed, `webmin-mysql`
  installed, and `keel-project-packages` found inithooks 2.3.6+keel38,
  confconsole 2.2.3+keel24 and keel 0.23.96 at the candidate of `trixie`.
- `conf.d/main`: `keel manifest validate lnmn` ok, "resolved along core,
  web, lnmn"; the image check passed.
- MariaDB listens on `127.0.0.1:3306` and `[::1]:3306` only.
- The first boot of `web` empties `/etc/inithooks.conf` at its end. So
  `35mysqlpass`, run after that boot, found no `DB_PASS`, said so, and left
  the account `admin` unable to authenticate. That is the behaviour of the
  hook when nobody declares the password. A new value was then written to
  `/etc/inithooks.conf` (mode 0600), as the first boot of an image of LNMN
  would see it. With it, `35mysqlpass` printed "MariaDB account 'admin' set
  from DB_PASS (32 characters), verified on [::1]:3306". `admin` logged in
  over TCP on `::1` and on `127.0.0.1`, and a wrong password was refused.
  The file was emptied again, and no `/root/.my.cnf` exists. A first try
  with another file path did nothing: the hook reads `INITHOOKS_CONF` from
  `/etc/default/inithooks`.
- `42keel-app`: the account `app` with `unix_socket` and `GRANT ALL ON
  app.*`, nothing global. `database.env` holds no secret.

### 3. A defect of the gate, and its fix (`09-user-steps.log`, `10-user-steps-2.log`)

- First run: the copy of the code into `/srv/app` came about 3 s before
  `keel-app-install`. In that time the gate timer saw `server.js` and
  started the service. node stopped with "Cannot find module 'mariadb'",
  systemd restarted it until "start-limit-hit", and `keel-app-install`
  failed at its start of the service. In t1 the two steps came close enough
  together, so the defect did not show.
- The fix, test first in `keel-lnmn` and `keel-lnpn`: `keel-app-install`
  writes a stamp (the sha256 of `package-lock.json`, or `no-lock`) after a
  good `npm ci` and removes it before. The gate opens only when the stamp
  matches the code. The install clears a failed state, then restarts a
  running service once, or else runs one gate pass.
- Second run, with 7 s between the two steps: before step 2 the gate said
  `closed: ... app=not-installed`, the service was `inactive`, and the
  journal had no "Cannot find module". Step 2 took 1.5 s (`npm ci`, 8
  packages). The stamp was the sha256 of the lock file, the service started
  once, and `/health` answered 200.

### 4. Through nginx (`11-through-nginx.log`, `12-websocket-files-sandbox.log`)

The init fence was stopped as in t1 (`02-firstboot.log`). From the BR1 host
over IPv6:

| Check | Result |
|---|---|
| `GET /health` over HTTPS | 200, `Server: nginx`, 16 ms, `db: writable` |
| `POST /row`, then `GET /row` | 200, the row came back |
| `PUT /files/upload-1.bin` (200,000 random bytes), then `GET` | 201, the same sha256 back |
| A file name with `../` | 400 |
| `GET /health` on port 80 (0079) | 200 |
| `GET /keel-check/` | 404 from the application: LNMN has no check page |
| `GET /events` | an event every 1.0 s, each read 2 to 5 ms after the time in it |
| Websocket handshake over HTTPS | `101 Switching Protocols`, `Sec-WebSocket-Accept` correct |
| Websocket from the client of Node.js 24 over port 80 | the server frame, then the echo of `ping-1`, in 26 ms |

The uploaded file is in `/var/lib/keel-app/files`, owner `app`. In the
mount namespace of the service, `/srv/app` is read-only and
`/var/lib/keel-app/files` is writable.

### 5. A change of the node binary (`13-runtime-restart.log`)

`keel-nodejs-24` 24.22.3+keel1 came from `trixie` (priority 990). The first
try of the reinstall did nothing: `conf.d/main` empties the apt lists, as a
build does. After `apt-get update`:

- `keel-runtime-restart.path` stopped: the PID stayed, and `/proc/PID/exe`
  showed `(deleted)`;
- the path unit active: a new PID, `exe` without `(deleted)`;
- the path service ran twice for one reinstall, as in t1 (open point 1 of
  0091).

### 6. A read-only database (`14-read-only.log`)

| Mode | Event | What the probe saw |
|---|---|---|
| `writer` | `read_only = 1` at 09:24:54.50 | writes 503 from the application, then the gate closed at 09:24:57.30 (2.8 s): 503 with the notice, the service stopped |
| `writer` | `read_only = 0` at 09:25:03.59 | 503 until the application listened, then 200 from 09:25:08.03 (4.4 s), no 502 |
| `all` | `read_only = 1` | `/health` 200 with `db: read-only`, `GET /row` 200, `POST /row` 503 with `ER_OPTION_PREVENTS_STATEMENT` |

The close and the open wait for the timer of the gate (5 s).

### 7. Memory at idle (`15-memory-idle.log`)

After 60 s with no request: node RSS 71.8 MB (anonymous 25.9 MB, file 45.9
MB); cgroups: `keel-app.service` 27.7 MB, `mariadb.service` 97.2 MB,
`nginx.service` 4.6 MB; `free -m` used 217 MB of 3072 MB. There is no
PHP-FPM (on the `lnmp` node of t1 it used 20.6 MB).

### 8. A reboot (`16-reboot.log`)

After `pct reboot`: "Startup finished in 4.698s"; node listened 1.7 s
later, and the gate opened the route. `/health` answered 200. The init
fence of TurnKey was up again after the boot (ports 60080 and 60443), as in
t1.

## Not tested

- An image of LNMN built by fab, its first boot with the preseed in one
  boot, and keel-init with its screens.
- A pair, the VIP, Syncthing, a promote and a failover.
- The cloud modes: Coraza, Anubis, and `keel-front.d`.
- The PostgreSQL base again: LNPN did not change except the shared files of
  the gate and the install, which ran in bats only.

## What was left

- CT 9402 is stopped. The test files in `/root` were removed.
  `/etc/inithooks.conf` is empty (0 bytes). No test pin and no
  `trixie-testing` source were on the node. It keeps the prototype files,
  MariaDB with the accounts `admin` and `app`, the sample application, and
  the apt lists of the last `apt-get update`.
- CT 9403 is stopped and was not touched in this test.
- The BR1 host keeps no file of the test.
