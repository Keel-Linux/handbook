# 0086: Loops, the federated short-video application, on LNMP

Date: 2026-11-11
Status: **proposed, 2026-11-11**, for the maintainer. Nothing in it is
built or released. One test by hand ran on a real container on BR1
(`evidence/2026-11-11-loops-beta-15-hand-test.md`). A local prototype of
the layer exists, with no remote. Its first boot hook and its gate ran on
the same container (evidence, item 13) and found 3 defects, which are fixed.
No image was built. The section "Open points" lists what the maintainer
must settle.

## What was asked

A Keel appliance for Loops, the short-video application of the Pixelfed
developers that federates with ActivityPub
(<https://github.com/joinloops/loops-server>, <https://joinloops.org>).
The design is for cloud advanced first: the database pair, Redis, the
media on file replication or object storage, and one node that runs the
scheduler.

## Facts checked

Checked on 2026-11-11 in the upstream repository at tag `v1.0.0-beta.15`
(commit `0d2a881e`) and at `main` (`d942be8e`), and with the GitHub API.
"Hand test" means the evidence file of this note.

| Item | Fact | Source |
| --- | --- | --- |
| Licence | AGPL-3.0 | `LICENSE`; GitHub API |
| Releases | 17 releases from `v1.0.0-alpha.1` (2025-09-04) to `v1.0.0-beta.15` (2026-10-23). There is no stable release. GitHub marks none as a pre-release | `git tag`; GitHub API `releases` |
| Production | The notes of beta.12 to beta.15 say "Some rough edges (it's an beta!)" and "Active development and frequent updates". No upstream text says that the software is ready for production. No upstream text gives a support period | release notes of beta.12 to beta.15 |
| Security | beta.15 is a "Security Release". It updates the PHP of the Docker image for 2 CVEs and says "Please update your local packages for non-docker instances. ASAP!" | release notes of beta.15 |
| Signatures | The tags are lightweight tags. GitHub shows the commit of beta.15 as verified. The releases have no files and no checksums | GitHub API `git/ref`, `commits`, `releases` |
| Upgrade method | `git pull origin main`, `composer install --no-dev`, `npm ci && npm run build`, `php artisan migrate`, caches, `horizon:terminate`. The method names `main`, not a tag | `INSTALLATION.md`, "Updates" |
| `main` | 87 commits after beta.15, with 2 new migrations. nodeinfo on `main` still says `1.0.0-beta.15` | `git rev-list`; hand test 12 |
| No Docker | `INSTALLATION.md` is an install with no Docker: git, composer, npm, Supervisor for Horizon, cron for the scheduler. Docker Compose is a second method | `INSTALLATION.md`; `README.md` |
| PHP | `^8.3|^8.4|^8.5`. The CI of upstream runs static checks on PHP 8.5 only. It runs no test suite | `composer.json`; `.github/workflows/` |
| PHP modules | BCMath, Ctype, Fileinfo, JSON, Intl, Mbstring, OpenSSL, PDO, Tokenizer, XML, GD or Imagick, Redis. The image driver default is `gd` | `INSTALLATION.md`; `config/intervention-image.php` |
| Database | "MySQL 8.0+". The Docker Compose file uses `mysql:9`. MariaDB is not supported: issue #421 "Support MariaDB officially" is open. PostgreSQL cannot work: migrations use `ALTER TABLE ... MODIFY COLUMN ... ENUM` | `INSTALLATION.md`; `docker-compose.yml`; issue #421; `database/migrations/2026_01_26_110904_update_comments_table_status_enum.php` |
| Redis | Required. Cache, sessions and queues are on Redis, the rate limiter is `throttleWithRedis`, and 76 calls in `app/` use `Redis::` directly | `INSTALLATION.md`; `bootstrap/app.php`; `app/Services/*.php` |
| Queue | Laravel Horizon. In production it starts at least 10 general workers, 1 video worker, 1 audio worker and 1 mail worker | `config/horizon.php` |
| Scheduler | `schedule:run` each minute from cron. 17 tasks, most with `onOneServer()`, which needs a shared cache lock | `INSTALLATION.md`; `routes/console.php` |
| Video | ffmpeg and ffprobe from `FFMPEG_BINARIES`. The output is H.264, 720 on the short edge, preset `slow`, CRF 23. The original upload stays. The default limit of an upload is 40 MiB | `config/loops.php`; `app/Jobs/Video/VideoOptimizeJob.php`; `app/Http/Requests/StoreVideoRequest.php`; hand test 5 |
| Storage | S3 by default. All media go through a disk named `s3`. For a local disk, upstream tells the operator to edit `config/filesystems.php` | `INSTALLATION.md`, "Using Local Storage Instead of S3" |
| Front end | Vue and Vite, built with Node.js "20+" (Vite 7.3 needs `^20.19.0 || >=22.12.0`). The build puts `VITE_APP_URL` into the built files | `INSTALLATION.md`; `package-lock.json`; hand test 1 |
| Federation | ActivityPub, WebFinger, HTTP signatures (RFC 9421 and the Cavage draft), shared inbox. Off after an install | `FEDERATION.md`; `config/loops.php`; hand test 6 |
| Actor keys | One RSA key pair signs for the instance and for every local user. It is in `storage/app/private/pki_*.txt` | `app/Services/SigningService.php`; hand test 6 |
| Outgoing calls | `version:check` calls `beacon.joinloops.org` twice a day. Other calls go to `push.loopsplatform.com` (push), `api.klipy.com` (GIFs) and `api.fedidb.org` (an admin action) | `routes/console.php`; `app/Services/VersionCheckService.php`; `app/Providers/AppServiceProvider.php`; hand test 7 |
| Contributions | "AI-generated contributions are not accepted" (pull requests, patches, issues and the rest) | `README.md` |

**What upstream does not support:**

1. A stable release, a support period, or an upgrade from tag to tag.
2. MariaDB (issue #421 is open) and PostgreSQL.
3. Local media with no change of an upstream file.
4. A build that leaves the git tree clean: after `npm run build`, the
   next `git pull` stops (hand test 12).
5. A version number that names the code on `main`.
6. A test suite in CI, and any PHP but 8.5 in CI.

## Why (brief section 10)

1. **Why the current approach is not enough.** Keel has no video
   application and no ActivityPub application in commissioning. Loops by
   hand needs 6 services, a front end build of 2.2 GiB of memory, a
   change of an upstream file for local media, and an upgrade method that
   fails after one build.
2. **Whether it can be made to work.** The hand test installed beta.15 on
   the LNMP image of the stable channel with Debian packages only. The
   migrations, the pages, an upload and its transcode, the federation
   endpoints, a reboot and an upgrade to `main` passed (evidence, items 1
   to 12).
3. **Why this is better.** The layer builds the application once, keeps
   upstream files unchanged except one line, and makes the keys, the
   media and the workers follow the pair of 0049, 0050 and 0068.

## Decision (proposed)

### 1. Stack

`keel-loops` is an application layer on `lnmp` (0059), with MariaDB 11.8
and PHP-FPM 8.4. LNPP is not possible (PostgreSQL, see Facts). Debian 13
has no MySQL server, and Keel has no MySQL. The hand test found no error
on MariaDB 11.8.6 with the `mysql` driver of Laravel and strict mode.
Upstream does not test MariaDB, so the commissioning (0075) is the proof.
Open point 2 asks the maintainer.

The layer adds from Debian 13: `php8.4-bcmath`, `-curl`, `-gd`, `-intl`,
`-mbstring`, `-xml`, `-zip`, `-redis`, `-mysql`, `redis-server` and
`ffmpeg`. Composer, Node.js and npm are build tools only. The layer
removes them after the build. Hand test 11 proved that the site and the
transcode work with no Node.js.

### 2. The code, built once

- The build clones one pinned tag (first `v1.0.0-beta.15`) and checks the
  commit id. `.git` is removed from the image.
- `composer install --no-dev --optimize-autoloader`, then `npm ci` and
  `npm run build` with `VITE_APP_URL` set to the placeholder
  `https://keel-build-placeholder.invalid`. The build resets the 2 files
  that it changes in the tree. It removes `node_modules`, the caches and
  the packages that the build added. The parent image has `git`, which
  etckeeper needs, so the build compares the lists of installed packages
  before and after, and keeps `git`.
- The code is in `/var/www/loops`, owned by root. Only `storage/` and
  `bootstrap/cache/` belong to `www-data`.
- The Node.js of the build is Debian's 20.19.2, which the hand test used.
  When the Keel Node.js package of 0083 exists, the build uses it.

### 3. The first boot

The hook `firstboot.d/45loops` does these steps:

1. It checks the options. `url` is the public HTTPS address. ActivityPub
   ids contain it, and they cannot change after the first federation. If
   `url` is not set and `federation` is false, the hook uses
   `https://` and the name of the machine, and says so. If `url` is not
   set and `federation` is true, the hook stops. A later run with a new
   `url` replaces the old address in the built files.
2. On a writable server: it makes the database `loops` and the socket
   account `www-data` (no password, as keel-laravel), and it keeps the
   APP_KEY, the Passport key pair and the ActivityPub key pair as rows of
   a table `keel_settings`. `openssl genpkey` makes the two key pairs
   (RSA 4096 and 2048). A row that exists is kept.
3. On a read-only server: it writes nothing to the database. It reads the
   rows. A read-only server never makes a key.
4. It writes `.env` (0600, `www-data`) and the key files (0600, the
   ActivityPub public key 0644) from the rows. Passport refuses a key file
   that is not 0600 or 0660 (evidence, item 13).
5. It replaces the placeholder name in the built files with `url`, and
   it fails if the placeholder stays.
6. It clears the cached configuration. A cached configuration hides the
   new `.env` from artisan (evidence, item 13).
7. On a writable server: it runs `migrate` and
   `app:composer-post-install-command`, sets the name of the instance and
   the federation switch in `admin_settings`, and runs that command again,
   because Loops keeps its settings in the cache (evidence, item 13). If
   `secrets.app_password` is set and no administrator exists, it makes
   the first administrator. If the secret is not set, it makes none and
   says so.
8. It makes the caches, waits for `/up`, and writes the mark
   `/var/lib/keel-loops/ready`. Federation stays off unless the option
   `federation` is true. The default is false, as upstream.

**The first boot of a cloud replica runs before keel pairs it.** The
inithooks order puts `45loops` before `75keel-role` and `80keel-cloud`.
So a replica makes keys of its own at its first boot, and keel then seeds
its database from the primary. The gate of section 6 corrects this: before
Loops serves, it writes `.env` and the key files again from the rows.

### 4. Media on the local disk

The layer adds one provider, `KeelMediaDiskServiceProvider`, and one line
in `bootstrap/providers.php`. The provider points the disk `s3` at
`storage/app/public` at run time. Hand test 2 proved it with a cached
configuration. `config/filesystems.php` stays as upstream.

### 5. nginx

The route is `/etc/nginx/keel-default.d/60-keel-loops.conf`, as
keel-laravel: only `public/index.php` runs, `/storage/` is static files,
the body limit is 64 MiB, and the site is closed with 503 until the first
boot writes `.env`. PHP-FPM gets `upload_max_filesize` and
`post_max_size` of 64M. The LNMP image has 16M (hand test 3).

### 6. The pair in cloud advanced

The pair is the pair of 0049 and 0057: the primary on BR1, the replica on
BR2, the witness (Core) on BR3.

| Part | On the primary | On the replica |
| --- | --- | --- |
| MariaDB | writable | read-only follower, lnmp's pair |
| Redis | the queue, the cache, the sessions | see below |
| Media | Syncthing sends | Syncthing receives (0050) |
| Web pages of Loops | serve | a notice page: "this node is the replica" |
| `loops-horizon`, `loops-scheduler` | run | stopped |

**One node serves.** Hand test 8 made a replica by hand: with the
database read-only, the reads gave 200. With Redis read-only too, 13 of
16 requests gave 500. A replica Redis is read-only (0065 uses
`REPLICAOF`). So the replica does not serve Loops. A gate,
`keel-loops-serve`, asks MariaDB `@@global.read_only` every 2 s, as the
gate of keel-odoo asks PostgreSQL. It acts only when the answer changes:

- Writable: it writes `.env` and the key files from the rows of
  `keel_settings`, caches the configuration, clears the copy of the
  ActivityPub key in the cache, starts Horizon and the scheduler, and
  removes the mark `/run/keel-loops/replica`.
- Read-only: it stops the two units and writes the mark. nginx shows the
  notice while the mark exists.
- No answer: it changes nothing.
- Before the first boot ends: the two units stay stopped, with no mark.

Evidence item 13 ran the gate on a real node: a new ActivityPub row
reached the actor document after one round, and the read-only round
stopped the units.

**Redis.** Redis follows the model of 0065 section 3.2: the replica runs
`REPLICAOF` the VIP holder. keel has no Redis follow step yet. Until it
has one, Redis runs on each node alone, and a failover loses the queue
and the web sessions. Hand test 9 flushed Redis: the likes, the API
tokens and the instance key stayed, because they are in MariaDB and on
the disk. Open point 5 asks if this stage can ship.

**Media.** The manifest declares one replicated path:

```yaml
state:
  replicate:
    - /var/www/loops/storage/app/public
```

It holds `videos/`, `avatars/` and the files that the install writes. A
45 s clip used 29.7 MB (the original and the 720p file, hand test 5).
Object storage (Garage, 0081) is a later step. The disk `s3` of upstream
can point at it with no change of code, which was not tested.

**Secrets that must be equal on both nodes:** `app_key`
(`shared: true` in the manifest), the Passport key pair and the
ActivityPub key pair (rows of `keel_settings`). Hand test 6 showed that a
node with no key file and an empty cache makes a new key. A remote server
then refuses its signatures. Thus the gate writes the files from the rows
before Loops serves.

**The scheduler** runs on the writable node only, through the gate.
`onOneServer()` then has one server.

### 7. Anubis and Coraza in the cloud modes

Anubis must not challenge federation, the mobile applications or the
media. These paths pass with no challenge: `/.well-known/`, `/nodeinfo/`,
`/ap/`, `/api/`, `/oauth/`, `/storage/`, `/up`, `/embed`, and each
request with an ActivityPub `Accept` or `Content-Type` header. Coraza
gets a body limit of 64 MiB on `/api/v1/studio/upload` only. Loops needs
`TRUST_PROXIES` for the Anubis socket. None of this was tested.

### 8. Size of a node

| Item | Measured |
| --- | --- |
| Memory | Horizon 765 MiB idle, 1.3 GB peak during a transcode. MariaDB 161 MiB. The CT has 4096 MiB, the minimum of the layer |
| CPU | About 2.5 s of CPU for each second of 1080x1920 video (preset `slow`, Xeon E5-2630 v2) |
| Disk | Code 170 MiB. Media: each upload keeps the original and the 720p file |
| Build host | `npm run build` 2.2 GiB peak, 107 s |

### 9. Upgrades

Upstream upgrades with `git pull` of `main`. Keel does not do that: the
code tree has no `.git`, and `main` has no version number. A new Keel
release pins a new tag. The steps on a node are those of hand test 12:
stop the workers, dump the database, replace the code, `migrate`, the
caches, start the workers. The code comes built, so the outage is the
migrations and the caches, not the 112 s of the front end build. Open
point 3 asks how the code reaches a node.

### 10. Outgoing calls

The version check fails after 10 s with no network and logs a warning.
The site works (hand test 7). The layer keeps it, because it tells the
administrator about a security release. Push and GIFs are off until the
administrator sets them.

### 11. The commissioning contract (0075)

`tests/commission.yaml` checks: the questions of the chain and the Loops
password; root, the database login, the password of the first
administrator (a hash check in Laravel); `/` 200, `/up` 200,
`/keel-health` 204, `http://127.0.0.1/` the application (0079); nodeinfo
404 while federation is off; `nginx`, `php8.4-fpm`, `mariadb`,
`redis-server`, `keel-loops-serve`, `loops-horizon`, `loops-scheduler`
active; no `keel_check` database, no `node_modules`, no `.git` and no
Node.js in the image. In the cloud modes: the same APP_KEY and the same
key pairs on both nodes, the workers on the primary only, the notice on
the replica, the media replicated, and a promotion and its return.

Two parts of the contract cannot pass yet:

- The interactive pass: keel-init has no screen for the Loops password.
  With no secret the first boot makes no administrator, and the proof of
  the password fails.
- `create-admin-account` takes the password as a command option, so it is
  in the process list while the command runs.

## Not chosen

- **LNPP.** The migrations of Loops use MySQL statements.
- **A build of the front end at the first boot.** It needs Node.js on the
  node, 2.2 GiB of memory and 110 s. Only 2 built files hold the name.
- **The upstream edit of `config/filesystems.php`.** Each upgrade would
  have to apply it again.
- **Both nodes serve.** A read-only Redis gives 500 (hand test 8).
- **Garage in the first release.** 0050 and 0065 give the reasons.

## Open points

1. Upstream is a beta with no stable release. May Keel release
   `keel-loops` on a beta, after it passes 0075? (yes/no)
2. Upstream supports MySQL only. Do we use MariaDB of the LNMP stack, with
   the commissioning as the proof? (yes/no)
3. How does a new Loops reach a node? (a) a new image only, until upstream
   has a stable release; (b) a Keel package with an upgrade by apt, as
   OJS in 0084.
4. Does the replica show a notice page and serve no Loops page, as
   above? (yes/no)
5. May the first release run Redis alone on each node, so that a
   failover loses the queue and the web sessions, until keel has the
   Redis follow of 0065? (yes/no)
6. Upstream accepts no AI-generated issues or patches. Do defects that
   Keel finds go to upstream only through the maintainer? (yes/no)
7. May the main session create `Keel-Linux/keel-loops` on git.pop.coop
   from the local prototype? (yes/no)
