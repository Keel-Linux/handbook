# Nextcloud 35 on the Keel LNMP image: the first test by hand

Date: 2026-11-11

This file is the evidence for the places marked "(first test)" in
decision note 0087. It is a test by hand on one container. No image
and no package was built. It is not a commissioning test (0075).

## The questions

1. Does Nextcloud 35.0.2 install and run on PHP 8.4 and MariaDB 11.8
   of the published LNMP image, behind the default site of keel-web?
2. Which nginx rules does it need, and which paths hold its state?
3. What does Redis do for it, and what happens when Redis stops, when
   Redis is 250 ms away, and when a session is lost?
4. What can a node with a read-only database serve (a fenced replica
   of a pair)?
5. What does `occ upgrade` need, and what does a replica need after
   the primary upgrades?

## The machine

| Item | Value |
|---|---|
| Container | CT 9380 on BR1, unprivileged, 2 cores, 4096 MiB, 8 GB disk on `local-lvm`, standalone node, bridge `vtnet88` tag 5 |
| Image | `debian-13-keel-lnmp_19.0-6_amd64.tar.zst`, sha256 `f8743dcb434f2ecea01b153e34b6cda028a9aac580cbd7236f2adcff5ef3f141` (the image of the stable channel) |
| Debian | 13.7 |
| Packages after the test setup | keel 0.23.96, keel-web 0.4.2, nginx 1.26.3-3+deb13u9, mariadb-server 1:11.8.6-0+deb13u1, php8.4-fpm 8.4.27-1~deb13u1, redis-server 5:8.0.2-3+deb13u3, php8.4-apcu 5.1.24-1, php8.4-redis 6.2.0-1, php8.4-imagick 3.8.0-2 |
| `nextcloud-33.0.10.tar.bz2` | sha256 `427110b96fd8580d8feb23a40a41d00657e975f945e0848485a6a26d777d7cae` |
| `nextcloud-34.0.5.tar.bz2` | sha256 `04ec3dddf465c9f2c2a9e6ee5f39b818399d4f3d581556f41d0872beeb59b0a9` |
| `nextcloud-35.0.2.tar.bz2` | sha256 `dfc7955eaec5621de90e031d10f76006173b3f3e31d5d6e174821d1da14f162d` (upstream 2026-10-15, the latest release on 2026-11-11) |
| Signature | each tarball has a good signature of the key `28806A878AE423A28372792ED75899B9A724937A` ("Nextcloud Security") from `https://nextcloud.com/nextcloud.asc` |

The logs are on the workstation of the maintainer, in
`repos/nextcloud-hand-tests/t1/` of the Keel folder. Each section
below names its log. No password, token or key is in the logs or in
this file. The test passwords were made in the container, in a
directory that only root can read, and were never printed.

## Setup (logs 10, 11, 20, 21)

- The image does not have the PHP modules Nextcloud needs. Added from
  Debian: `php-gd php-xml php-mbstring php-zip php-curl php-intl
  php-bcmath php-gmp php-apcu php-redis php-imagick php-bz2`,
  `redis-server`, and `bzip2` (the image cannot unpack a `.tar.bz2`
  without it). apt upgraded PHP from 8.4.26 to 8.4.27 in the same run.
- etckeeper committed `/etc/redis` into `/etc/.git` at the apt run. A
  file in `/etc` that holds a password goes into `/etc/.git` at the
  next apt run.
- The layout: code in `/var/www/nextcloud`, owned by root; `config/`
  and `custom_apps/` owned by `www-data`; the data directory
  `/var/lib/nextcloud/data`, mode 0750, outside the web root.
- The account `www-data@localhost` already exists in the LNMP image
  (unix_socket, a grant on `keel_check`). It got `ALL` on the schema
  `nextcloud` only.
- `occ maintenance:install` as `www-data`, with
  `--database-host=localhost:/run/mysqld/mysqld.sock`,
  `--database-user=www-data` and an empty database password: code 0,
  16 s, 138 tables. `config.php` has `dbpassword` with length 0. No
  new database account was made.
- The administrator password came from a throwaway value at install,
  then `occ user:resetpassword --password-from-env`. The real password
  was never an argument of a process.

## Operator error and its repair (log 41)

During the upgrade test the 33.0.10 tarball was unpacked in
`/var/www`. It unpacks to `nextcloud/`, so it wrote over the 35.0.2
code tree. The repair: keep `config/config.php` and `custom_apps/`,
remove the tree, unpack 35.0.2 again, put the two back. Result:
`occ integrity:check-core` code 0, every probe of the site passes
again. The database and the data directory were not touched. This
shows that the code tree holds no state: `config.php` and
`custom_apps/` are the only parts to keep. The later unpacks went
through a script that refuses `/var/www/nextcloud` as a destination.

## PHP and the local cache (logs 22, 23, 25)

- PHP settings that `occ setupchecks` accepts: `memory_limit = 512M`,
  `output_buffering = 0`, `opcache.interned_strings_buffer = 16`, the
  upload limits 512M, and `env[PATH]` in the PHP-FPM pool.
- APCu as `memcache.local` with `apc.enable_cli = 0`: `occ` and
  `cron.php` return 0. The site uses APCu, the command line falls
  back. With `apc.enable_cli = 1` the same commands return 0.
- Without a writable app directory, the update notification job
  logs "Cannot write into apps directory". `apps_paths` with
  `custom_apps` (writable) removes it.
- `occ setupchecks` shows "Database transaction isolation level:
  Read committed" although the server global is REPEATABLE-READ.
  Nextcloud sets its own isolation level for its session.
- The LNMP standalone node has `log_bin = 0` and `binlog_format =
  MIXED`. keel sets `binlog_format = ROW` on a pair
  (`keel/system/dbmariadb.py`), which is what Nextcloud requires.
- The serverinfo database advisor reports one warning:
  `innodb_log_file_size` is 96 MiB, and it asks for 128 MiB or more.
- Not fixed in the test: HSTS (keel-web leaves it out while the
  certificate is self-signed), "server ID is not configured" (a value
  for each node when several nodes serve), no SVG in Imagick.

## nginx (logs 20, 26)

The upstream example of the admin manual 35 ("Version 2026-06-09")
cannot go in as it is: the default site of keel-web already has
`location /` and `index index.html`. The route was ported like the
WordPress route: exact locations, `^~` prefixes and regular
expressions only, in `/etc/nginx/keel-default.d/`. The check page of
LNMP was removed. Results with `Host: nc.test` on the loopback:

| Path | Answer |
|---|---|
| `/` | 302 to `/login` |
| `/login`, `/status.php`, `/ocs-provider/`, `/robots.txt` | 200 |
| `/.well-known/caldav`, `/.well-known/carddav` | 301 to `/remote.php/dav/` |
| `/.well-known/webfinger` | 301 to `/index.php/.well-known/webfinger` |
| `/data/nextcloud.log`, `/config/config.php`, `/occ`, `/3rdparty/autoload.php`, `/composer.json`, `/core/shipped.json`, `/.ncdata` | 404 |
| `/keel-health` | 204 |
| a `.mjs` file of `dist/` | 200, `text/javascript` |
| public port 80 `/status.php` (0079) | 200; `/` redirects to `http://nc.test/login` |
| public port 80 `/.well-known/acme-challenge/x` | 404 from keel-web: its `^~` location is longer and wins |

- The catch-all location needs `index index.php index.html
  /index.php$request_uri`, or `/ocs-provider/` fails the setup check.
- `fastcgi_param HTTPS` comes from Debian's `fastcgi_params`
  (`$https if_not_empty`), not `on`, so port 80 and 443 both work.
- `fastcgi_intercept_errors` stays off: keel-web sets `error_page 404`
  and `500 502 503 504` for the server, and they would replace the
  answers of WebDAV.
- nginx 1.26 has no `.mjs` type. The static location includes
  `mime.types` and adds `text/javascript mjs`.
- `occ setupchecks`: WebDAV, `.well-known`, JavaScript modules, source
  maps, fonts, data directory protected: all pass.

## WebDAV (log 27)

With an app password (`occ user:auth-tokens:add`, kept in a root-only
file): PUT of 100 MiB 201 in 1.3 s; PROPFIND 207; GET returns the same
sha256; MKCOL, COPY, MOVE 201; DELETE 204; a chunked upload (v2, three
parts, then MOVE of `.file`) 201 and the same sha256.

## State paths (log 32)

All files that changed during one PUT, one preview, one `cron.php`
run, one app installed from the app store (`notes` 6.1.1, 7 s, 27 MB)
and one `occ config:system:set`, outside `/proc`, `/sys`, `/run`,
`/dev`, `/tmp` and `/root`:

| Path | What it is |
|---|---|
| `/var/lib/nextcloud/data/admin/files/...` | the user files |
| `/var/lib/nextcloud/data/appdata_<instanceid>/preview/...` | previews |
| `/var/lib/nextcloud/data/appdata_<instanceid>/appstore/apps.json` | the cache of the app store |
| `/var/www/nextcloud/custom_apps/notes/...` | the app from the app store |
| `/var/lib/mysql/...` | new tables of the app, and rows |
| `/var/log/nginx/access.log`, the journal, `fail2ban.sqlite3` | logs of the node |

The data directory also holds `appdata_<instanceid>/identityproof`
(the key pair of the server), `.ncdata`, `index.html`, `.htaccess`
and `nextcloud.log`. The directory name `appdata_<instanceid>` depends
on `instanceid` in `config.php`. `config/config.php` changes with each
`occ config:system:set`, and at install and upgrade.

## Redis (logs 24, 25, 27)

Redis 8.0.2 of Debian on its socket, with an ACL user for Nextcloud
whose password is a SHA-256 digest in the Redis configuration. Set:
`memcache.local` APCu, `memcache.distributed` and `memcache.locking`
Redis, and the PHP sessions in Redis by
`php_admin_value[session.save_handler] = redis` in a pool file of
mode 0600. Result: setup check "Transactional File Locking" passes,
and the PHP sessions are keys `PHPREDIS_SESSION:<id>` with a TTL of
1440 s.

## A lost session (log 28)

The login form needs an `Origin` header of a trusted domain and the
field `rememberme`. A browser login, then the session key deleted in
Redis:

| Case | Next page |
|---|---|
| `rememberme=1`, session key deleted | 200 |
| `rememberme=0`, session key deleted | 200 |
| `rememberme=1`, then `FLUSHALL` (sessions, cache and locks) | 200 |

Nextcloud keeps the token of each session in `oc_authtoken` in the
database, and it logs the browser in again from the session cookie.
So a lost Redis does not log the users out, as long as the database
has the token.

## Redis stops (log 29)

| Request | Redis up | Redis stopped | Redis started again, empty |
|---|---|---|---|
| `/status.php` | 200 | **200** | 200 |
| files page, logged in | 200 | 500 | 200 |
| login page | 200 | 500 | 200 |
| PROPFIND, PUT | 207, 201 | 503, 503 | 207, 201 |
| `occ status`, `cron.php` | 0, 0 | 0, 0 | 0, 0 |

`status.php` answers 200 with Redis down, so it is not a health check.

**A secret in the log.** With Redis stopped, PHP writes the warning
`session_start(): Failed to read session data: redis (path: ...)`,
and the path holds `auth[pass]=` with the Redis password. Nextcloud
writes the warning into `nextcloud.log` (level 2). The password was
also in log 29 of the workstation. It was replaced with `REDACTED`
there, and the Redis password in the container was changed (log 30).

## A session-only Redis user (log 47)

A second ACL user, `nextcloud-session`, may use the keys
`PHPREDIS_SESSION:*` only, with the commands that the session handler
needs. Its password is the one in `session.save_path`. Results: `GET`
of another key, `KEYS` and `FLUSHALL` answer `NOPERM`; login, pages,
DAV, `occ` and `cron.php` all pass. A leaked session password then
opens only the session keys. Nextcloud encrypts the session data with
a key that is in the cookie of the browser (`oc_sessionPassphrase`).

## Redis at 250 ms RTT (log 46)

Nextcloud's Redis traffic (cache, locks and sessions) went over TCP to
`127.0.0.1:6379`, and netem put 125 ms on each direction of the
loopback (ping 250.1 ms). The requests went to the eth0 address, so
only the Redis traffic had the delay. Three runs of each:

| Request | 0 ms | 250 ms |
|---|---|---|
| `/status.php` (no Redis) | 0.02 to 0.04 s | 0.79 s |
| files page with a session | 0.08 to 0.32 s | 12.6 to 27.2 s |
| PROPFIND depth 1 | 0.79 to 0.99 s | 12.0 s |
| GET of a small file | 0.73 to 0.89 s | 12.8 to 12.9 s |
| PUT of 1 KiB | 0.79 to 1.25 s | 17.1 s |
| login POST | 2.5 s | 15.1 s |

The 16 requests of one run used 860 Redis commands. The DAV times at
0 ms include a check of the password on each request, so the times at
250 ms are an upper bound for DAV. The files page is the clean number.
The Redis that a serving node uses must be on its own site.

## A read-only database: the fenced replica (logs 31, 48)

`SET GLOBAL read_only = 1`. `www-data` has no `READ_ONLY ADMIN`.

| Request | read-write | read-only, locking in Redis | read-only, locking in the database |
|---|---|---|---|
| `/status.php` | 200 | **200** | **200** |
| files page, existing session | 200 | 200 | 200 |
| new login | 303 | **500** | **500** |
| PROPFIND, GET of a file (account password) | 207, 200 | **503, 503** | **503, 503** |
| PROPFIND, GET of a file (app password, log 48) | 207, 200 | **503, 503** | not run |
| preview of an image | 200 | 200 | 200 |
| PUT, MKCOL | 201, 201 | 503, 503 | 503, 503 |
| `occ status`, `occ files:scan` | 0, 0 | 0, 0 | 0, 0 |
| `cron.php` | 0 | **1** | **1** |

The traces show the writes: the DAV authentication
(`OCA\DAV\Connector\Sabre\Auth::check`), the first-login listener
(`JobList::add`), and token checks (`PublicKeyTokenMapper::invalidate`).
So a node with a read-only database cannot serve sync clients, not
even for reads, and the choice of the lock backend does not change
that. With the database lock backend, `oc_file_locks` had 92 rows.

## Upgrades (logs 40, 42, 43, 44)

A second instance in the same container (`/var/www/nc-up`, schema
`nc_up`, data `/var/lib/nc-up/data`): 33.0.10 installed in 14 s, a user
with 50 files, the app `notes`.

| Step | Result |
|---|---|
| 33.0.10 to 35.0.2 | refused: "Updates between multiple major versions and downgrades are unsupported", code 5, 0 s. No table and no app version changed. **`config.php` keeps `maintenance = true`** and gets `loglevel = 2` |
| back to 33, `occ maintenance:mode --off` | 33.0.10, no upgrade needed |
| 33.0.10 to 34.0.5 | code 0, 18 s, 132 tables, `notes` stays enabled. In `config.php` only `version` changed. Three `cron.php` runs after it: code 0 |
| 34.0.5 to 35.0.2 | code 0, 23 s, 139 tables, `dav` 2.0.0, `files` 3.0.0. In `config.php` only `version` changed. Three `cron.php` runs: code 0, 162 s |

The core version is in `config.php` (`version`) only. After the
upgrade, `oc_migrations` has the row `core`
`35000Date20260527162338`, which is the newest file of
`core/Migrations/` in the 35.0.2 code tree (log 49).

**The replica after the primary upgrades** (log 44): the code 35.0.2,
the database already upgraded, `read_only = 1`, and the replica's own
`config.php` of 34.0.5. `occ status` says `needsDbUpgrade: true`.
`occ upgrade` on it fails, code 5, and leaves `maintenance = true`.
With only `version` copied from the primary's `config.php` (one
`occ config:system:set`, which writes the file and not the
database), `occ status` says `needsDbUpgrade: false`.

## Several configuration files (logs 49, 50)

- A file `config/NAME.config.php` wins over `config.php` for each key
  it sets.
- `occ config:system:set` writes `config.php`, and it writes the
  merged values: after one such call, the keys of the other file are
  in `config.php` too. A key that the other file sets keeps the value
  of that file.
- A file with `instanceid`, `secret` and `passwordsalt`, made before
  `occ maintenance:install`: the install passes, and it uses that
  `instanceid` (`appdata_<that id>`). It writes a new `secret` and
  `passwordsalt` into `config.php`; the values of the other file win
  when Nextcloud reads them.

## Not tested here

A pair, Syncthing, a failover, netem between two nodes, Anubis and
Coraza in front (the node was standalone, Anubis inactive), a desktop
or mobile client, IPv6-only (the container also had a DHCP IPv4
address), a read-only `config.php` (`config_is_read_only`), large data
(the data directory was 363 MB), and the image or a package.
