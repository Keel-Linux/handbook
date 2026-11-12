# 0088: Pixelfed, the federated photo-sharing application, on LNMP

Date: 2026-11-12
Status: **proposed, 2026-11-12**, for the maintainer. Nothing in it is
built or released. One test by hand ran on a real container on BR1
(`evidence/2026-11-12-pixelfed-0.15.2-hand-test.md`, "hand test" below).
A local prototype of the layer, `keel-pixelfed`, has no remote. Its first
boot hook and its gate ran on the same container (hand test, item 14) and
found 2 defects, which are fixed. No image was built. The section
"Questions for the maintainer" lists what the maintainer must settle.

## What was asked

A Keel appliance for Pixelfed, the federated alternative to Instagram
(<https://github.com/pixelfed/pixelfed>, <https://pixelfed.org>). Pixelfed
comes before Loops (0086). The family is the same: Laravel, Redis,
Horizon. The design reuses the pattern of 0086 and 0087.

These rules of the maintainer apply:

1. MariaDB.
2. Redis alone on each node (0087, "(a)").
3. The replica shows a notice, and only the writer serves.
4. A release needs the commissioning of 0075.
5. No Docker anywhere.
6. The paths of federation may go past Anubis, with Coraza still on them.

## Facts checked

Checked on 2026-11-12 in the upstream repository at tag `v0.15.2` (commit
`b19607f1`), in its documentation repository (`pixelfed/docs`, commit
`746adf0a`), and with the GitHub API.

| Item | Fact | Source |
| --- | --- | --- |
| Licence | AGPL-3.0 | `LICENSE`; GitHub API |
| Latest stable | `v0.15.2`, 2026-10-21, "Security Update: PHP RCE + CA Update Compromise". It asks for PHP 8.4.27 or 8.5.12 at a minimum | GitHub API `releases`; release notes |
| Rhythm | 13 stable releases from `v0.12.9` (2026-08-24) to `v0.15.2` (2026-10-21), and 2 release candidates. `dev` has 230 commits after `v0.15.2` (2026-11-10) | GitHub API; `git rev-list` |
| Support period | None written. `SECURITY.md` gives only an address for reports. Each release note tells how to upgrade from the release before | `SECURITY.md`; release notes |
| Signatures | Lightweight tags. No release files, no checksums | `git cat-file`; GitHub API |
| No Docker | The documentation has an install with no Docker: Composer, a PHP-FPM pool, Horizon under systemd or Supervisor, cron for the scheduler. The release notes call the Docker guide "official" and the other one "not complete because everybody has their own snowflake of a server" | `running-pixelfed/installation.md`; release notes of `v0.15.2` |
| PHP | `^8.4|^8.5`. 8.5 is recommended, 8.4 "Active support ends 31 Dec 2026". `v0.15.0` dropped 8.3. The documentation still says 8.3 | `composer.json`; `README.md`; release notes of `v0.15.0`; `prerequisites.md` |
| PHP modules | bcmath, ctype, curl, intl, json, mbstring, openssl, redis; an image driver | `composer.json` |
| Database | The documentation lists MySQL 5.7+, MariaDB 10.3+ and PostgreSQL 10+. The CI runs its tests on SQLite. A matrix with MySQL 9, MariaDB 12.3 and PostgreSQL runs only by hand and "is expected to fail". Issue #6082 (MariaDB 10.11) reports a reblog defect and a `GROUP BY` defect | `prerequisites.md`; `.github/workflows/`; issue #6082 |
| Redis | Required: the queue, the cache, Horizon | `composer.json`; `.env.example` |
| Queue | Laravel Horizon, 5 supervisors, up to 30 workers by default | `config/horizon.php` |
| Scheduler | `schedule:run` each minute, 16 tasks, each with `onOneServer()` | `bootstrap/scheduledtasks.php` |
| Images | Driver `vips` by default (FFI), else `gd` or `imagick` with an error in the log. Optimizers: jpegoptim, pngquant, optipng, gifsicle, cwebp | `config/image.php`; `app/Util/Media/ImageDriverManager.php`; `config/image-optimizer.php` |
| Video | Off by default (`MEDIA_TYPES` has images only). ffmpeg makes a thumbnail; no transcode | `config/pixelfed.php`; hand test 4 |
| Storage | The local disk by default. S3 is an option (`PF_ENABLE_CLOUD`) | `config/pixelfed.php`; `.env.example` |
| Front end | The maintainers commit the built files, so an install needs no Node.js | `CONTRIBUTING.md`; hand test 1 |
| Upgrade method | `git checkout` of the new tag, `composer install`, `config:cache`, `route:cache`, `migrate --force`, `app:home-feed-rebuild` | release notes of `v0.15.2` |
| Large instances | Issue titles name a flood of delete jobs from remote servers (#3981), a slow home timeline (#5275) and PHP memory limit failures (#5548). `v0.15.2` turned the cached timelines on by default. The bodies were not read | GitHub search; release notes |
| Contributions | "AI-generated contributions are not accepted": pull requests, patches, documentation, translations, issues. Security reports go by email | `README.md`; `SECURITY.md` |

## What the hand test showed

The numbers are items of the evidence file.

1. **Install.** Debian packages only: 55 s of apt, 15 s of Composer, 15 s
   of migrations (268), 7 s for the places. No Node.js (1).
2. **A read-only database.** With the database session store, every page
   gives 500, because every request writes `sessions`. With the Redis
   session store, the pages and the API reads give 200. A like and a login
   give 500 in both (6).
3. **The inbox queues.** A POST to an inbox gives 200 at once and puts the
   activity on the Redis queue of the node, signed or not, also with a
   read-only database (5, 6).
4. **An empty Redis.** No post, like, key or API token is lost. Waiting
   jobs are lost; the hourly `media:optimize` finds an unprocessed photo
   again. With the Redis session store a browser logs in again (7).
5. **Keys.** The ActivityPub keys are rows of the database. Only the
   APP_KEY and the Passport key pair are outside it (8).
6. **The federation switch** is a row of `config_cache`. It wins over
   `.env`, and the cache keeps it for 12 h (5).
7. **Size.** Horizon 1.2 GB idle with 22 processes. A 12 MP photo costs
   1.3 s of CPU with vips and 2.1 s with gd. The original is not kept (3,
   4).
8. **Upgrade.** `v0.15.1` to `v0.15.2` in 12 s, 1 migration, no key
   changed (10).
9. **Outgoing calls.** `versions.pixelfed.org` after each Composer run,
   about 11 s with no network (9).
10. **Two upstream defects.** `user:create --is_admin=1` makes no
    administrator (1). Passport refuses a token when the user id is equal
    to the client id, because `oauth_clients` has no `grant_types` (13).

## Where Pixelfed differs from 0086 (Loops)

| Item | Loops (0086) | Pixelfed (this note) | Source |
| --- | --- | --- | --- |
| Releases | Beta only | Stable releases, about one in 5 days, no support period | Facts |
| MariaDB | Not supported (issue #421) | Listed as supported; not tested in CI | Facts |
| Front end | Built with Node.js, 2.2 GiB; 2 built files hold the address | Built by upstream; nothing to build, no placeholder | hand test 1 |
| Local media | One provider and one changed line of upstream | The upstream default; no change | hand test 4 |
| ActivityPub keys | One key pair in files; rows of `keel_settings` | Rows of Pixelfed (`instance_actors`, `profiles`) that the pair copies | hand test 8 |
| Federation switch | Row of `admin_settings` | Row of `config_cache`, plus the `AP_*` values of `.env` | hand test 5 |
| Health route | `/up` | None; the gate needs none | hand test 2 |
| Video | Transcode to 720p, 2.5 s of CPU for each second | Off by default; a thumbnail only | hand test 4 |
| Gate | `read_only` only, every 2 s | The signals of 0087 (role file, `read_only`, VIP), at each address event, Redis emptied before it opens | prototype |
| Horizon idle | 765 MiB | 1.2 GB | hand test 3 |
| Upgrade | `git pull` of `main`, broken after a build | `git checkout` of a tag; works | hand test 10 |

## Why (brief section 10)

1. **Why the current approach is not enough.** Keel has no photo
   application and no ActivityPub application in commissioning. Pixelfed by
   hand needs 6 services, a settings table that wins over `.env`, and keys
   in two places. A replica with a read-only database gives 500.
2. **Whether it can be made to work.** The hand test installed
   `v0.15.2` on the LNMP image of the stable channel with Debian packages
   only. The pages, an upload, the federation endpoints, a reboot and an
   upgrade from `v0.15.1` passed. The prototype hook and gate passed on
   the same node.
3. **Why this is better.** Pixelfed needs less than Loops: no front end
   build, no change of an upstream file, and the ActivityPub keys follow
   the database pair by themselves. The layer reuses the gate of 0087 and
   the rows of 0086.

## Decision (proposed)

### 1. Stack

`keel-pixelfed` is an application layer on `lnmp` (0059), with MariaDB
11.8 and PHP-FPM 8.4 of Debian 13. The layer adds from Debian 13:
`php8.4-bcmath`, `-curl`, `-gd`, `-intl`, `-mbstring`, `-xml`, `-zip`,
`-redis`, `-mysql`, `redis-server`, `ffmpeg`, `libvips42t64`, `jpegoptim`,
`optipng`, `pngquant`, `gifsicle` and `webp`. The build checks that
`php8.4-cli` is 8.4.27 or later. Upstream does not test MariaDB in CI, so
the commissioning (0075) is the proof.

### 2. The code

- The build clones one pinned tag (first `v0.15.2`) and checks the commit
  id. It runs `composer install --no-dev --optimize-autoloader`, checks
  that the git tree is clean, and removes `.git`, Composer and the build
  caches. The parent image keeps `git` for etckeeper.
- The code is in `/var/www/pixelfed`, owned by root. Only `storage/` and
  `bootstrap/cache/` belong to `www-data`.
- The image holds no `.env` and no key.

### 3. The first boot

The hook `firstboot.d/45pixelfed`:

1. It checks the options: `name`, `url`, `database`, `admin_user`,
   `admin_email`, `federation`. `url` is the public HTTPS address. If it
   is not set and `federation` is false, the hook uses the name of the
   machine and says so. If it is not set and `federation` is true, the
   hook stops.
2. On a writable server: it makes the database and the socket account
   `www-data` with no password, and keeps the APP_KEY and the Passport key
   pair (RSA 4096) as rows of `keel_settings`. A row that exists is kept.
3. On a read-only server: it writes nothing to the database. It reads the
   rows.
4. It writes `.env` (0600) and the two key files (0600) from the rows.
   `.env` has the MariaDB socket, the Redis of the node, the session store
   (section 6), `ACTIVITY_PUB` and the `AP_*` values from `federation`,
   and no `TRUST_PROXIES`.
5. On a writable server: `migrate`, `import:cities` when `places` is
   empty, `instance:actor`, the rows `app.name`,
   `federation.activitypub.enabled` and `pixelfed.open_registration` of
   `config_cache`, the first administrator when `secrets.app_password` is
   set (`user:create --is_admin=true`), and `cache:clear`.
6. It makes the caches and writes the mark `/var/lib/keel-pixelfed/ready`.
   Federation stays off unless `federation` is true.

As in 0086, the first boot of a cloud replica runs before keel pairs it.
The gate corrects this: before the node serves, it writes `.env` and the
key files again from the rows.

### 4. nginx

The route `/etc/nginx/keel-default.d/60-keel-pixelfed.conf`: only
`public/index.php` runs, `/storage/` is static files, the body limit is
64 MiB. The application answers only while the mark
`/run/keel-pixelfed/open` exists. Before the first boot and on every node
that is not the writer, each request to the application gets 503 with a
notice page and `Retry-After: 30`. Thus a remote server sends its inbox
post again later, and no node takes an activity into a Redis that the
gate empties later. The media stay on both nodes. PHP-FPM gets
`upload_max_filesize` and `post_max_size` of 64M.

### 5. The gate: only the writer serves

The gate `keel-pixelfed-gate` is the gate of 0087, section 4, with the
workers of 0086. It opens when all of these are true: the first boot has
finished; keel's role file says `role=primary`, or there is no role file;
MariaDB answers `read_only = 0`; when the role file names a VIP, the VIP is
on this node. A timer runs it every 5 s, and a watcher runs it at each
address event (`ip monitor address`).

- **It opens:** it writes the APP_KEY and the Passport key files from the
  rows, caches the configuration, empties the Redis of the node
  (`FLUSHALL`), starts Horizon and the scheduler, and writes the mark.
- **It closes:** it removes the mark first, then stops the two units.
- **No change:** nothing.

Hand test 14 ran it on a real node: open, closed with `read_only=1`, the
three role-file cases, and the timer within 7 s.

### 6. Redis and the sessions

Redis 8 of Debian runs alone on each node, on the loopback, with no RDB
file and no AOF. The gate empties it when the node becomes the writer.
The prototype keeps the sessions in Redis: with the database store, every
page writes `sessions` (hand test 6), and on a pair each write waits for
the replica (0087: a PUT of 1 KiB took 2.4 s at 250 ms). The cost: after a
failover a browser user logs in again. API tokens stay (hand test 7).
Question 1 asks the maintainer.

### 7. The pair in cloud advanced

| Part | On the primary | On the replica |
| --- | --- | --- |
| MariaDB | writable | read-only follower, lnmp's pair |
| Redis | queue, cache, sessions | alone, not used |
| Media | Syncthing sends | Syncthing receives (0050) |
| Pixelfed | serves | 503 with the notice |
| Horizon, scheduler | run | stopped |

The manifest declares one replicated path,
`/var/www/pixelfed/storage/app/public`, and one secret, `app_key`
(`generate: allowed`, `shared: true`). The ActivityPub keys need nothing:
keel copies the database. The Passport key pair and the APP_KEY are rows
of `keel_settings`. A Passport key that differs makes every API token of
the mobile applications invalid after a failover.

What a failover loses: the jobs in the Redis of the old writer (outgoing
deliveries, media jobs; `media:optimize` finds the photos again), the
browser sessions, and the cache, which Pixelfed makes again. The loss of
outgoing deliveries is inferred, not tested.

### 8. Anubis and Coraza in the cloud modes

The front file `keel-front.d/60-keel-pixelfed.conf` sends these paths past
Anubis to the application, with Coraza still on them: `/.well-known/`,
`/api/`, `/oauth/`, `/f/`, `/i/actor`, `/users/`, `/storage/`, and `/p/`
when the request has an ActivityPub `Accept` header. A browser keeps the
challenge on every other path. None of this was tested. Pixelfed behind
the socket of Anubis sees no client address unless `TRUST_PROXIES` names
the front; that is open (point 2).

### 9. Upgrades

Upstream upgrades with `git checkout` of the next tag; hand test 10 passed
from `v0.15.1`. Keel does not run git on a node: the image has no `.git`.
A new Keel release pins a new tag. The steps on a node: stop the workers,
dump the database, replace the code, `migrate`, the caches,
`app:home-feed-rebuild --no-interaction`, start the workers. Upstream
releases often and gives security fixes only in the newest release.
Question 2 asks how the code reaches a node.

### 10. Outgoing calls

The version check (`versions.pixelfed.org`) stays: it tells the
administrator about a security release. With no network it costs about
11 s and the site works. The suggestions of `beagle.pixelfed.net` and the
directory of pixelfed.org stay as upstream sets them; they were not
reached in the test.

### 11. The commissioning contract (0075)

The contract checks: the questions of the chain and the Pixelfed password;
the administrator (a hash check in Laravel); `/` 200, `/keel-health` 204,
`/api/v1/instance` 200; nodeinfo 200 with `"activitypub"` only when
federation is on; `nginx`, `php8.4-fpm`, `mariadb`, `redis-server`,
`keel-pixelfed-gate.timer`, `keel-pixelfed-gate-watch`,
`pixelfed-horizon`, `pixelfed-scheduler` active; no `.git`, no Composer
and no `keel_check` database in the image. In the cloud modes: the same
APP_KEY and Passport key on both nodes, the workers on the primary only,
503 with the notice on the replica, the media replicated, and a promotion
and its return.

Two parts cannot pass yet, as in 0086: keel-init has no screen for the
Pixelfed password, and `user:create` takes the password as an option, so
it is in the process list while the command runs.

## Not chosen

- **LNPP.** The maintainer chose MariaDB. PostgreSQL is listed by
  upstream and was not tested.
- **The Docker image of upstream.** No Docker anywhere.
- **Both nodes serve.** With a read-only database the pages give 500
  (hand test 6), and an inbox post on the replica goes into a Redis that
  the gate empties.
- **A shared or replicated Redis.** The maintainer's rule is one Redis on
  each node (0087).
- **Video on by default.** Upstream keeps it off. Pixelfed keeps the
  original file with no transcode, so a video costs disk only.

## Open points

1. Horizon uses 1.2 GB idle in a container of 4096 MiB. The limits
   `HORIZON_*_MAX_PROCESSES` can lower it. Not tested.
2. `TRUST_PROXIES` behind Anubis, for the rate limits and the logs.
3. The password of the first administrator in the process list
   (section 11).
4. The `GROUP BY` path of issue #6082 on MariaDB was not exercised.
5. A token is refused when the user id is equal to the client id (hand
   test 13). Seen with a personal access client only.

## Tests before the release

1. The image of the prototype: the three passes of 0075 on BR1 and BR2.
2. Cloud advanced: Syncthing on the media, a failover and a return, the
   API token of a mobile application across the failover.
3. The same at 250 ms with loss.
4. The front: a remote fetch of an actor and a post through Anubis, a
   signed inbox post, an upload of 15 MB through Coraza.
5. Federation with a test instance that Keel owns, never a public one
   without the maintainer's yes.

## Questions for the maintainer

1. The session store: (a) Redis, so a failover logs browser users out and
   API tokens stay; (b) the database, so every page writes and waits for
   the replica. Which letter?
2. How does a new Pixelfed reach a node? (a) a new image for each upstream
   release; (b) a Keel package with an upgrade by apt, as OJS in 0084.
   Which letter?
3. MariaDB with the commissioning as the proof, because upstream CI does
   not test it. Yes or no?
4. Video stays off by default, as upstream. Yes or no?
5. The paths past Anubis of section 8, `/api/` and `/p/` (by header)
   included. Yes or no?
6. Upstream accepts no AI-generated issues or patches. Do the two defects
   of the hand test go to upstream only through the maintainer? Yes or
   no?
7. May the main session create `Keel-Linux/keel-pixelfed` on git.pop.coop
   from the local prototype? Yes or no?
