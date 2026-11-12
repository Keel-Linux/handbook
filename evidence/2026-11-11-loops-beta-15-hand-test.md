# Loops 1.0.0-beta.15 on the Keel LNMP image: the first test by hand

Date: 2026-11-11

This file is the evidence for decision note 0086. It is a test by hand on
one container. No image and no package was built. It is not a
commissioning test (0075). The node did not federate with a real
instance, and it was never reachable as a public instance.

## The questions

1. Does Loops install and run on Debian 13, PHP 8.4 and MariaDB 11.8,
   with no Docker?
2. Which nginx rules does it need on the route directory of Keel Web?
3. Which paths hold state, for the Syncthing paths of 0050 and 0068?
4. How much disk and CPU does a video upload and its transcode use?
5. What does a second node need?
6. Which federation endpoints answer?
7. Does the upgrade method of upstream work?

## The machine

| Item | Value |
|---|---|
| Container | CT 9390 on BR1, unprivileged, `nesting=1`, 4 cores (Xeon E5-2630 v2), 4096 MiB, 1024 MiB swap, 8 GiB disk on `local-lvm` |
| Network | `vtnet88` tag 5, DHCP and SLAAC, `--nameserver 2606:4700:4700::1111`. The CT got a public IPv6 address and a private IPv4 address |
| Image | `debian-13-keel-lnmp_19.0-6_amd64.tar.zst`, sha256 `f8743dcb434f2ecea01b153e34b6cda028a9aac580cbd7236f2adcff5ef3f141` (the same image as the OJS tests) |
| First boot | Preseed in `/etc/inithooks.conf` (root and database passwords made on the host, never printed). All hooks completed, no `fatal` |
| Debian, PHP, MariaDB, nginx | 13.7; PHP 8.4.27-1~deb13u1 after the modules; 11.8.6-MariaDB-0+deb13u1; nginx 1.26.3 |
| Keel packages | keel 0.23.96, keel-web 0.4.2, inithooks 2.3.6+keel38, confconsole 2.2.3+keel24 |
| Loops | Tag `v1.0.0-beta.15`, commit `0d2a881e459327ff5d551850ec55664e29717982` (2026-10-23). Later upgraded to `main` at `d942be8e` (2026-11-04) |
| Mode | Simple. MariaDB standalone, Redis on the loopback |

Added from Debian 13 (`10-apt.log`, 89 s): `php8.4-bcmath`, `-curl`,
`-gd`, `-intl`, `-mbstring`, `-xml`, `-zip`, `-redis` (6.2.0), `-mysql`,
`-sqlite3`, `redis-server` 8.0.2, `ffmpeg` 7.1.5, `composer` 2.8.8,
`nodejs` 20.19.2, `npm` 9.2.0, `git`, `unzip`, and `time` and `sysstat` for
the measurements.

## The firewall of the test

After the install, a table `inet loopstest` (`files/loopstest.nft`) was
loaded, and a unit loaded it again at each boot before the network:

- In: only the loopback, answers and ICMP. All other new packets are
  dropped.
- Out: only the loopback, answers and DNS. All other new packets are
  dropped, and their destinations go into a set.

From the BR1 host, `https://[2804:710:d0:5:be24:11ff:fe3a:8140]/` gave no
answer (curl code 28) before and after a reboot (`34-firewall.log`,
`63-reboot.log`). The site name was `loops.keel.test`, a name in
`/etc/hosts` of the CT only. Each request used `curl --resolve` to the
loopback.

## Results

### 1. Install

| Step | Result | Log |
|---|---|---|
| `git clone --depth 1 --branch v1.0.0-beta.15` as `www-data` | Code 0 | `20-clone-composer.log` |
| `composer install --no-dev --optimize-autoloader` | Code 0, 16 s, 100 MiB peak RSS, `vendor/` 152 MiB. No Pail error | `20-clone-composer.log` |
| `npm ci` | Code 0, 28 s, 500 MiB peak RSS, `node_modules/` 496 MiB, 537 packages | `21-npm-build.log` |
| `npm run build` | Code 0, 107 s, **2.2 GiB peak RSS**, `public/build/` 13 MiB | `21-npm-build.log` |
| Database: `utf8mb4_unicode_ci`, account `www-data`@`localhost` `IDENTIFIED VIA unix_socket`, `DB_CONNECTION=mysql`, `DB_SOCKET` | The login works with no password | `31-db-env.log` |
| `php artisan migrate --force` | Code 0, 4 s, 156 migrations, 99 tables, no error | `32-migrate.log` |
| `passport:keys`, `storage:link`, `create-admin-account` | Code 0 | `32-migrate.log` |
| `config:cache`, `route:cache`, `view:cache` | Code 0 | `33-start.log` |

The front end build reads `VITE_APP_URL` from `.env`. The build ran with
the name `keel-build-placeholder.invalid`. The name is in 2 built files
only: `public/build/assets/download-the-app-*.js` and `public/embed.js`
(`21-npm-build.log`).

The build also changed 2 files that git tracks:
`resources/js/auto-imports.d.ts` and `.eslintrc-auto-import.json`
(`31-db-env.log`).

`create-admin-account` takes the password as a command option
(`--password=`). The value is then in the process list while it runs.

### 2. Media on the local disk with no change of an upstream file

Loops writes all media through the disk `s3`. A provider of 20 lines,
`files/KeelMediaDiskServiceProvider.php`, sets that disk to the local
driver at run time (`storage/app/public`, URL `APP_URL/storage`). It reads
no `env()`, so it works with a cached configuration. The only upstream
file that changed is `bootstrap/providers.php` (one line). Uploads,
thumbnails and the transcoded files went to `storage/app/public/videos/`,
and nginx served them (`41-upload-clip10.log`, `44-limit-and-serve.log`).

### 3. nginx

The route is `files/loops.nginx.conf` in `/etc/nginx/keel-default.d/`,
the pattern of keel-laravel: regular expression locations, no server of
its own. `nginx -t` passed. The rules:

- `client_max_body_size 200m` (the default limit of Loops is 40 MiB for
  a video, see below).
- Only `public/index.php` runs. Other `.php` paths give 404. Hidden
  files give 403, except `/.well-known/`.
- `/storage/` is static files from `public/storage`. A range request gave
  206 with `video/mp4` (`44-limit-and-serve.log`).
- `fastcgi_read_timeout 300s`.

PHP-FPM needed `upload_max_filesize = 64M` and `post_max_size = 64M`. The
LNMP image has 16M for both (`40-upload-prep.log`).

| Path | Status | Log |
|---|---|---|
| `/`, `/explore`, `/login`, `/@keeladmin` | 200 | `33-start.log`, `50-readonly.log` |
| `/up` (Laravel health) | 200 | `33-start.log` |
| `/keel-health` | 204 | `33-start.log` |
| `http://` port 80, `/` | 200 (0079: no redirect with the self-signed certificate) | `33-start.log` |

### 4. Services

| Unit | What | Result |
|---|---|---|
| `loops-horizon.service` | `php artisan horizon` as `www-data`, `Restart=always`, `TimeoutStopSec=1020` | Active. 17 processes, 765 MiB in its cgroup when idle, 0.7 s of CPU in 60 s idle (`42-idle-and-limits.log`) |
| `loops-scheduler.service` | `php artisan schedule:work` as `www-data`, `Restart=always` | Active. It ran the 5 minute and 10 minute tasks in the background (`51-scheduler-outbound.log`) |
| `redis-server` | Debian 8.0.2, `127.0.0.1` and `::1`, RDB saves | Active |

`php artisan horizon:terminate` ends Horizon with code 0. With
`Restart=always`, systemd started it again (restart counter 1). With
`Restart=on-failure`, it would stay stopped (`62-restart-reboot-prep.log`).

After `pct reboot`, the firewall, nginx, PHP-FPM, MariaDB, Redis, Horizon
and the scheduler were active, and `/up` and `/ap/actor` gave 200
(`63-reboot.log`).

### 5. A video upload and its transcode

Clips made in the CT with `ffmpeg -f lavfi testsrc2` and a sine tone,
1080x1920, 30 frames per second, H.264 and AAC. Upload through
`POST /api/v1/studio/upload` with a personal access token, which a file
in the CT held. The CPU is the delta of `cpu.stat` of the cgroup of
`loops-horizon.service`.

| Clip | Upload | Optimize job | CPU of the workers | Files kept | Log |
|---|---|---|---|---|---|
| 10 s, 7.4 MB | HTTP 200, 1.1 s | 8 s | 26 s | original 7.4 MB, `720p.mp4` 2.3 MB, thumbnail 71 kB | `41-upload-clip10.log` |
| 45 s, 19.6 MB | HTTP 200, 0.3 s | 31 s | 111 s | original 19.6 MB, `720p.mp4` 10.0 MB, thumbnail 66 kB | `43-upload-clip45.log` |
| 60 s, 44.9 MB | HTTP 422, "must be between 250 and 40960 kilobytes" | none | none | none | `44-limit-and-serve.log` |
| 10 s on `main` | HTTP 200 | 9 s | 32 s; peak of `/tmp` 9.8 MB | as above | `72-after-upgrade.log` |

- The transcode used about 2.5 s of CPU for each second of video, with the
  upstream default preset `slow`, on this CPU. The output is 720x1280.
- Loops keeps the original upload next to the 720p file. The disk use is
  the sum of both.
- The peak memory of the Horizon cgroup was 1.3 GB during a transcode.
- Debian's ffmpeg 7.1.5 did the work. Upstream's Docker image compiles
  ffmpeg 9.0.2. No error came from the older version.

### 6. Federation endpoints

Federation is off after the install (`federation.enableFederation` is
`false` in `admin_settings`). Then `/.well-known/nodeinfo`,
`/nodeinfo/2.1` and `/.well-known/host-meta` give 404 (`33-start.log`,
`35-federation-on.log`). The test set it to `true` with the firewall in
place.

| Request | Result | Log |
|---|---|---|
| `GET /.well-known/nodeinfo`, `/nodeinfo/2.1` | 200. `software.version` is `1.0.0-beta.15`, `openRegistrations` is false | `35-federation-on.log` |
| `GET /.well-known/host-meta` | 200, `application/xrd+xml` | `35-federation-on.log` |
| `GET /.well-known/webfinger?resource=acct:keeladmin@loops.keel.test` | 200, `self` is `/ap/users/<id>` | `35-federation-on.log` |
| `GET /.well-known/webfinger?resource=acct:loops.keel.test@loops.keel.test` | 200, the instance actor `/ap/actor` | `35-federation-on.log` |
| `GET /ap/actor`, `/ap/users/<id>`, `.../outbox`, `.../followers` with `Accept: application/activity+json` | 200, `application/activity+json` | `36-actors-inbox.log` |
| `POST /ap/inbox`, `/ap/actor/inbox`, `/ap/users/<id>/inbox` with no signature | 401, "Missing signature header" | `36-actors-inbox.log` |

A signed delivery from a second instance was not tested.

**One key for all actors.** The instance actor and the user actor show the
same public key (`36-actors-inbox.log`). `profiles.public_key` is NULL for
the local user (`61-instance-key.log`). The key pair is in
`storage/app/private/pki_private.txt` and `pki_public.txt`, mode 0644. The
first request for an actor made the files. Loops keeps a copy in the
cache forever (`pki::public`, `pki::private`).

| Step | Public key, sha256 prefix | Log |
|---|---|---|
| Start | `22f663bb1527b18e` | `61-instance-key.log` |
| Cache cleared, files kept | `22f663bb1527b18e` | same |
| Cache cleared, files moved away | `3eee3e724f67f15a`: **a new key** | same |
| Files back, cache cleared | `22f663bb1527b18e` | same |

### 7. Outgoing calls with no network

The set of the firewall kept the destination of each new outgoing
packet. From 23:13 to 23:20 UTC, with the scheduler and Horizon active,
the Loops processes made no outgoing call. Then each scheduled command
that calls out was run by hand
(`51-scheduler-outbound.log`, `52-outbound-commands.log`):

| Command | Result |
|---|---|
| `version:check --force` (scheduled at 09:00 and 17:00) | Code 0 after 10.6 s. It logs a warning, a timeout to `https://beacon.joinloops.org/latest.json`. The set shows the 4 addresses of `beacon.joinloops.org` on port 443 |
| `instances:update-stats`, `app:instance-stats-collector-command`, `feed:update-interests`, `app:system-message-seeder` | Code 0, 0.4 s each, no outgoing packet |

The other entries in the set came from the test itself: `github.com` (a
curl check) and the Debian mirror (`apt-get`).

### 8. A replica: the database read-only, then Redis read-only

The same 18 requests ran as a guest and as a user (`files/ro.sh`).

| State | Result | Log |
|---|---|---|
| MariaDB writable, Redis writable | All 200, except 2 paths that do not exist (`/api/v0/feed/recommended`, 404) | `50-readonly.log` |
| `SET GLOBAL read_only=1`, Redis writable | All reads 200. A like gives 500 (`SQLSTATE[HY000] 1290 ... --read-only`) | `50-readonly.log` |
| MariaDB read-only and Redis a read-only replica (`REPLICAOF` a port with no server) | 13 of 16 paths give 500. Only `/up`, webfinger, nodeinfo and the actors give 200. The log has `READONLY You can't write against a read only replica` from the rate limiter script and the cache | `53-readonly-redis.log` |

Thus the application reads from a read-only database, but it does not
work with a read-only Redis.

The first read-only run lost its log lines: a `touch` as root made the
log file, and `www-data` could not write it. The run was made again after
a `chown` (`50-readonly.log`).

### 9. Redis lost

With Horizon and the scheduler stopped, `redis-cli flushall` removed all
74 keys (`54-redis-flush.log`). After the restart, Redis had 10 keys, and:

- the like count and "has liked" of a video were the same (they are in
  MariaDB);
- all 18 requests gave the same status as before;
- the instance key was the same (from the file);
- the API token was valid (Passport keeps it in MariaDB).

Queued jobs and the sessions of web logins are in Redis, and a flush
loses them. This was not measured with a job in the queue.

### 10. State on the disk

`60-state-inventory.log`:

| Path | What | State or not |
|---|---|---|
| `/var/www/loops/.env` | the settings and `APP_KEY`, 0600 | secret, one per installation |
| `storage/oauth-private.key`, `oauth-public.key` | Passport keys, 0600 and 0660 | secret, must be equal on all nodes |
| `storage/app/private/pki_*.txt` | the ActivityPub key pair, 0644 | secret, must be equal on all nodes |
| `storage/app/public/videos/`, `avatars/` | media | state, grows |
| `storage/app/public/software-logos/`, `storage/app/page-templates/`, `storage/app/notifications/` | files that the install writes | made again by the install |
| `storage/framework/`, `storage/logs/`, `bootstrap/cache/` | caches, compiled views, logs | not state |
| MariaDB `loops` | 99 tables, 169 MiB of `/var/lib/mysql` in total | state |
| Redis | cache, sessions, queues, Horizon, rate limits | see 9 |

Sizes: `vendor/` 153 MiB, `public/build/` 13 MiB, `.git` 3.9 MiB,
`node_modules/` 499 MiB, npm and composer caches 120 MiB.

### 11. Node.js at run time

With `node_modules/` moved away and `/usr/bin/node` mode 0, the pages
gave 200 and a 10 s upload completed its transcode
(`73-node-build-only.log`). Node.js is a build tool only.

### 12. The upgrade method of upstream

INSTALLATION.md says: `git pull origin main`, `composer install`,
`npm ci && npm run build`, `php artisan migrate`, clear and rebuild the
caches, `horizon:terminate`. The test did these steps from beta.15 to
`main` with Horizon and the scheduler stopped, a dump first, and the
outgoing firewall open for the downloads only.

| Run | Result | Log |
|---|---|---|
| 1 | `git checkout` **refused**: "Your local changes to the following files would be overwritten by checkout: resources/js/auto-imports.d.ts". The front end build of the install changed that file. The other steps ran on the old code | `70-upgrade.log` |
| 2 | The 2 changed build files were reset first. Then: checkout code 0 (87 commits), composer 10 s, `npm ci` 28 s, build 112 s, 2 migrations in 1 s, total 157 s with the workers stopped. All requests gave the same status as before | `71-upgrade-retry.log` |

After the upgrade, `main` at `d942be8e` still reports `1.0.0-beta.15` in
nodeinfo. The version string does not name the code. The build changed
the same 2 files again, so the next `git pull` fails again.

The firewall table was loaded again after the downloads. That reset its
set, so the hosts of the download window are not in a log. The tools used
`github.com`, `repo.packagist.org` and `registry.npmjs.org`.

### 13. The first boot hook and the gate of the prototype, on the same CT

On 2026-11-12 the files `45loops`, `lib/loops.sh` and `keel-loops-serve` of
the local prototype `keel-loops` ran on CT 9390 against a new database
`loops_proto`, with the code of `main` from item 12
(`95-proto-run.log`, `96-proto-hook.log`, `97-proto-gate.log`). The sha256
of each pushed file matched the file of the prototype (`95-proto-run.log`).

| Run | Result | Log |
|---|---|---|
| Hook, run 1 | **Defect.** The configuration that item 12 cached named the database `loops`, so `migrate` ran on `loops` and not on `loops_proto`. The hook then stopped: `admin_settings` did not exist. Fix: `config:clear` after `.env` is written | `96-proto-hook.log` |
| Hook, run 2 | Code 0, 10 s. 3 rows in `keel_settings`, 102 tables, one administrator, the name and the federation switch in `admin_settings`. **Defect:** the page title stayed "My Loops Instance", because Loops keeps its settings in the cache. Fix: `app:composer-post-install-command` again after the update | `96-proto-hook.log` |
| Hook, run 3 | Code 0. Title "Keel Loops proto". nodeinfo and webfinger 404 (federation off). The password check of the contract gave `ok` for the secret and `no` for another password, with `HOME=/tmp` (psysh cannot write a root-owned home) | `96-proto-hook.log` |
| Gate, writable | `start`: Horizon and the scheduler active. The key of `/ap/actor` equals the key of the row | `97-proto-gate.log` |
| Gate after a new `activitypub_key` row (a stand-in of the seed from a primary) | Before the gate, the actor showed the old key. After `start`, the actor, the row and the file showed the new key | `97-proto-gate.log` |
| Gate, `read_only=1`, then `read_only=0` | `stop`: both units inactive, the mark `/run/keel-loops/replica` written. Then `start`: both active, the mark removed | `97-proto-gate.log` |
| A Passport token with the key pair that `openssl genpkey` made | **Defect:** HTTP 500, "Key file ... oauth-public.key permissions are not correct, recommend changing to 600 or 660 instead of 644". Fix: the public key 0600. Then HTTP 200 | `97-proto-gate.log` |
| A signature with the ActivityPub key that `openssl genpkey` made | `openssl_sign` and `openssl_verify` through `SigningService`: ok | `97-proto-gate.log` |

The 3 defects were fixed in the prototype and in its tests. The nginx route
of the prototype and its notice page did not run on this CT. The code tree
was the one of the hand test, owned by `www-data`.

## Not tested

- A second node, a database pair, Syncthing, a Redis follower, netem.
- Anubis and Coraza (cloud modes), and `TRUST_PROXIES`.
- A signed delivery from a real or a second test instance.
- The web login and the web upload in a browser. Only the API.
- Mail. `MAIL_MAILER` was `log`.
- An IPv6-only node. The CT had IPv4 too.
- A long video near the 40 MiB limit, two transcodes at the same time,
  and the 900 s job timeout of `main`.
- MariaDB as the server in an upstream test. Upstream tests MySQL only
  (note 0086).

## What is left on BR1

CT 9390 is stopped. It holds `/var/www/loops/.env` (`APP_KEY`), the
Passport and ActivityPub keys, the databases `loops` and `loops_proto`,
`/root/loops-token`, `/root/loops-admin.pass` and a database dump
`/root/loops-pre-upgrade.sql.zst`. The host keeps
`/root/loops-test1/` with the files pushed for the test and the
`pct create` output (no secret). Remove both when this evidence is merged.

The logs are in the workstation folder
`/home/navigator/Projects/Keel/repos/loops-hand-tests/t1/` (not in a
repository).
