# 0065: Mastodon on the LNPP stack, Redis in the pair, media on the 0050 replication

Date: 2026-10-24
Status: **proposed, 2026-10-24**, for the maintainer. The maintainer
ordered the new appliances on 2026-10-24. Decision 0035 made Mastodon the
reference appliance and left the design open. This note makes 0035
concrete for the rules of today: 0049 (VIP and roles), 0050 (file
replication), 0054 (PostgreSQL pair) and 0059 (LNPP). Section "Open
points" lists what the maintainer must settle.

## What was asked

A decision note for `keel-mastodon`. It states the version, the base, the
database and Redis on a pair across sites, the processes that run on the
primary only, the media files, and the search engine.

## Why (brief section 10)

1. **Why the current approach is not enough.** 0035 and the Mastodon
   example of docs/manifest-v1.md were written on 2026-09-30, before
   0049, 0050, 0054 and 0059. The example says `base: ruby`, requires
   object storage, and declares no `state`. Three of its facts no longer
   hold. Garage is a second step, not a first one (0050 section 5).
   Node.js 20 is too old for Mastodon 4.7. The worker rule forbids the
   media writes that Sidekiq must make.
2. **Whether it can be made to work.** It can. PostgreSQL 17 and Ruby 3.3
   are in trixie, and upstream supports both. The stack LNPP already has
   the PostgreSQL pair. The 0050 replication already covers WordPress
   run-time directories, and the media directory of Mastodon has the same
   shape. Redis has a decided pair design in 0049.
3. **Why this is better.** Mastodon is built on parts that exist. The
   only new parts are Node.js 24, a Redis follow step in keel, and one
   small amendment of the worker rule. No object store is needed in the
   first release.

## Decision

### 1. Upstream, version, licence and prior art

- **Version: Mastodon 4.7.3**, released 2026-10-01, the latest stable
  upstream. The layer pins the source tarball
  `https://github.com/mastodon/mastodon/archive/refs/tags/v4.7.3.tar.gz`
  by sha256 `b9fca0d53c9005c2e84f23f55b2e32b045909afeb1931ae6de350a63497b85b2`
  (0012). The tag points to commit `8ff11c2bb7b9`. Mastodon is not in
  Debian. An upgrade moves the pin, one release at a time.
- **Licence: AGPL-3.0**, upstream `LICENSE`. The source of the pinned
  release is the corresponding source that the licence needs.
- **Ruby: Debian ruby3.3 3.3.8** from trixie. The Gemfile says
  `ruby '>= 3.3.0', '< 4.1.0'`, and the upstream CI matrix tests 3.3. The
  file `.ruby-version` and the upstream container use 4.0.6. Keel does not
  follow them, because the Debian Ruby gets security updates and needs no
  compiler on the node. The gems are built into the image with
  `bundle install --deployment`. No `rbenv` is on the node.
- **Node.js: 24.** `package.json` and `streaming/package.json` need
  `node >= 22`. The file `.nvmrc` and the upstream container use 24.
  Trixie has 20.19.2. Forky has 24.21.0. **Keel carries a Node.js 24
  package** under 0039, built from the Debian forky source for trixie.
  If this build is too heavy, the fallback is the upstream binary
  tarball, pinned by sha256. Node.js runs the streaming server on the node
  and builds the assets at image build.
- **PostgreSQL: 17** from the stack. Upstream needs 14 or newer and tests
  14. **Redis: 8.0.2** from trixie. Upstream needs 7.0
  or newer and tests 7. The Debian package of Redis 8 has the licence
  choice RSALv2, SSPLv1 or AGPLv3. Valkey 8.1.1 is in trixie, but upstream
  does not test it, so Keel does not use it now.
- **Prior art.** The repository `turnkeylinux-apps/mastodon` does not
  exist (GitHub returns 404). The request is the open issue
  `turnkeylinux/tracker#2092`. The work is on git.pop.coop as
  `turnkeylinux/mastodon` (2 commits, 2026-03-18) and
  `organica/mastodon-turnkey`. It installs Mastodon `main` unpinned at
  build, with rbenv and a Node.js from `n`, and a local `public/system`.
  Keel keeps the unit files and the first boot idea, and changes the
  rest as this note says. There is no `Keel-Linux/keel-mastodon` yet. Its
  creation is an open point.

### 2. Base: the `lnpp` layer

**`keel-mastodon` is a layer on `lnpp`** (0059). It adds Ruby, Node.js,
Redis, the Mastodon source and its units.

- **Why `lnpp`.** Mastodon needs PostgreSQL. The layer `lnpp` has the
  PostgreSQL 17 server, the pair by `database.server` (0054), the nginx
  route directory `/etc/nginx/keel-default.d/` and the page
  `/keel-check/`. Mastodon needs no Python. The Python of `lnpp` serves
  only the check page, and costs a few MiB. A layer on `web` would copy
  the PostgreSQL files of the stack a third time (0059 item 3), which is
  worse.
- **The database fits the pair.** Mastodon supports PostgreSQL only. It
  uses one database and one role, `mastodon`. The pair of 0054 gives one writer, a
  semi-synchronous standby and `pg_rewind` for the old primary. Mastodon
  holds all its accounts and posts in this database, so the pair is the
  most important part of the appliance.
- **Not `ruby` as base.** The manifest example says `base: ruby`. No
  such layer exists, and 0059 replaced the stack idea. The manifest says
  `base: lnpp`.
- **The standalone mode** is one node with the database, Redis and the
  files on the node. The cloud modes use the pair.

### 3. The pair across sites

#### 3.1 PostgreSQL

The PostgreSQL pair is the one of 0054, with the VIP of 0049. The layer
adds nothing to it. Mastodon connects to the VIP holder on loopback or
through the VIP, as the `database.client` section of the spec says. The
secret `db_password` is shared. Mastodon has no read replica use that is
safe on a standby, so `database.client.replicas` stays empty.

#### 3.2 Redis: a follower of the primary, with a full resync accepted

Redis holds the home and list feeds, the Sidekiq queues and locks, the
cache and the pub/sub channels of the streaming server. Upstream says in
its backup page: "Losing the Redis database is almost harmless". Only the
queued jobs and the scheduled retries are lost. `tootctl feeds build
--all` makes the feeds again.

- **The target is 0049.** The Redis of the replica runs `REPLICAOF` the
  address of the VIP holder, with `replica-read-only yes`. After a
  failover the new primary has the queue up to the replication lag. A full
  resync of an old primary discards what it wrote after the split. 0049
  accepts this loss for Redis.
- **Tuning for 250 ms.** The layer sets `repl-backlog-size` large enough
  to keep a partial resync possible after a cut of some minutes. The
  release test measures how often a full resync happens.
- **The cache is separate.** The layer runs a second Redis instance on
  loopback port 6380 for `CACHE_REDIS_URL`. It has no disk save, a
  `maxmemory` limit and `allkeys-lru`, as the upstream scaling page
  advises. It is not replicated, because cache churn would use the link
  for no gain. The main instance, port 6379, is the one in the pair.
- **After the flip,** the role hook runs `tootctl feeds build --all` on
  the new primary when the follow step reports a full resync. The loss of
  queued jobs means that some deliveries to other servers are never made.
  Keel logs and alerts the resync, as 0049 requires.
- **What keel lacks today.** keel reads Redis and does not converge it
  (`keel.system.dbstate` leaves "a Redis" alone), and `database.server`
  holds one engine. The step needs a second server section in the spec
  and the follow step for Redis in `keel`. **Until this work is done,
  Redis runs on each node alone, not replicated.** The new primary then
  starts with an empty queue, and the role hook builds the feeds. This
  stage loses the whole queue at a failover, not only the lag. Open point
  1 asks the maintainer if this stage may ship.

#### 3.3 Media files: the 0050 replication, no object storage

**Media are files on a replicated directory. Garage is not used.**

- `PAPERCLIP_ROOT_PATH` is `/var/lib/mastodon/system`. The default is
  `public/system` in the source tree, which is under `/usr/share` and is
  read-only. The URL stays `/system`.
- The manifest declares one replicated path:

  ```yaml
  state:
    replicate:
      - /var/lib/mastodon/system
  ```

- **No exclude.** The remote media cache is under `system/cache/`
  (`config/initializers/paperclip.rb`). It looks like a good exclude, but
  a database row of a cached remote file stays valid while the file is
  missing. After a failover, the site would give 404 for these files until
  the retention job clears the row. So the cache replicates with the rest.
- **The size is bounded by retention.** The built-in vacuum job removes
  cached remote media after the retention period. `config/settings.yml`
  has no default for `media_cache_retention_period`, so the first boot
  sets it to 7 days. The first release test measures the daily churn at
  250 ms.
- **Why not Garage.** 0050 section 5 and 0062 give the reasons. Every
  request pays the round trip of the link, and the documented limit is
  200 ms. Object
  storage keeps its place as a later step of 0050. The example in
  docs/manifest-v1.md requires `s3`. This note removes that requirement.
- **Sessions** are cookies in the database and Redis, not files, as 0032
  requires. `tmp`, `log` and `public/assets` are not state. The assets
  are built into the image.
- **Secrets.** The secrets `secret_key_base`, `vapid_private_key`,
  `vapid_public_key` and the three Active Record encryption keys are
  `shared`. A replica that signs or decrypts with other keys breaks
  logins and two-factor codes after a flip. The secret `otp_secret` of the
  example is removed: `.env.production.sample` of 4.7.3 does not have it.

#### 3.4 What runs on the primary only

| Process | Where it runs | How it stops on a replica |
| --- | --- | --- |
| `mastodon-sidekiq` | the primary | worker of the manifest, gated by keel |
| `mastodon-streaming` | the primary | the role hook stops the unit |
| `mastodon-web` (Puma) | the primary | the role hook stops the unit |
| PostgreSQL | both nodes | the pair of 0054 |
| Redis | both nodes | `REPLICAOF` on the replica |

- **Sidekiq is a worker with `singleton: true`.** One process runs all
  queues. Upstream says the `scheduler` queue must never run in more than
  one process. The scheduler of Mastodon (`config/sidekiq.yml`) runs the
  periodic jobs, vacuum and trends inside Sidekiq, so no system timer is
  needed. Outgoing mail goes through the `mailers` queue, so mail is on
  the primary only.
- **Why the role hook, not a unit condition.** A `Condition` in a systemd
  unit is checked when the unit starts. It does not stop a unit that
  runs. After a demote, the hook of 0050 amendment item 7
  (`/usr/lib/keel/roles.d/40-mastodon`, called with `primary` or
  `replica`) stops or starts the three units. The units also carry
  `ExecCondition` on the role file, so a boot of a replica starts none.
- **Puma stops on a replica.** Almost every request of Mastodon writes: a
  plain `GET` touches the session, the rate limiter and the Redis cache,
  and Redis is read-only on a replica. A warm Puma, as Odoo and Nextcloud
  have it, would fail on most requests. The replica answers `503` with
  `Retry-After` on every route except `/keel-check/`. The cost is the cold
  start of Rails after a promote. The release test measures it against the
  target of about 5 s for the first write (0059). Open point 2 covers the
  result.
- **Migrations** run on the primary only, through `hooks.migrate`. The
  post-deployment migrations run after the new code runs on the primary.
- **The worker rule needs one amendment.** Rule 24 of docs/manifest-v1.md
  gives a worker no writable path, and the unit gets no `ReadWritePaths`.
  Sidekiq downloads and resizes remote media into `system/`. The
  amendment: **keel adds a `ReadWritePaths` entry to the unit of a worker
  for each path of the same manifest's `state.replicate`, and for no other
  path.** A worker still cannot write to any other place.

### 4. Ports, mesh exposure, route, TLS and health

| Port | Service | Exposure |
| --- | --- | --- |
| 443, 80 | nginx of Keel Web | the uplink, as the stack |
| 3000 | Puma | loopback |
| 4000 | streaming server | loopback |
| 5432 | PostgreSQL | mesh, by the stack |
| 6379 | Redis (pair) | loopback, and mesh for the follow step |
| 6380 | Redis (cache) | loopback |

- **Redis on the mesh** needs `requirepass` and `masterauth`. The secret
  `redis_password` is `shared`. Redis has no origin rule (docs/spec.md), so
  the mesh firewall is the only other protection.
- **The routes** are in `/etc/nginx/keel-default.d/50-keel-mastodon.conf`:
  `/` to port 3000; `/api/v1/streaming` to port 4000 as a websocket; and
  `/system/` as static files from `/var/lib/mastodon/system`, with
  `autoindex off`. Upstream marks a file list of `/system/` as dangerous.
- **TLS** ends in nginx of Keel Web. `LOCAL_DOMAIN` is an option with no
  default, because Mastodon cannot change it after the first account
  exists. `WEB_DOMAIN` is a second option for a split domain.
- **Anubis must not challenge federation or clients.** The paths
  `/.well-known/`, `/inbox`, `/users/*/inbox`, `/actor`, `/api/`,
  `/oauth/`, `/system/` and the streaming websocket pass without the
  proof of work. A request with an ActivityPub `Accept` header passes too.
  Browser traffic to the web interface keeps the challenge. Without these
  rules, federation fails. This follows the pattern of common#62 and 0062.
- **Coraza.** The body limit of the front site is 1 MB (keel-web#15). The
  layer raises it to 99 MB on `/api/v1/media` and `/api/v2/media` only.
  The value is `VIDEO_LIMIT` in `MediaAttachment`. The layer carries its
  own rule exclusions. No official CRS plugin for Mastodon is known. A
  federation test finds the rules to relax.
- **Checks.** Puma: `/health` answers 200. Streaming:
  `/api/v1/streaming/health` answers 200. Redis answers `PING` on both
  ports. PostgreSQL has the check of the stack. Monit also watches
  `mastodon-sidekiq`. On a replica the three application checks are off,
  because the units are stopped by design. `/keel-check/` reports the
  role, the database state, the Redis link state and the replication state
  of the files.

### 5. Search: off in the first release

**The search engine is not part of the first release.** `ES_ENABLED` is
`false` and the example keeps `placement: none`. Upstream tests only
Elasticsearch 7, which is end of life. It "should support" OpenSearch and
Elasticsearch 8 and 9. Debian trixie has neither. OpenSearch 2.4.1 is in
sid only. The open item of 0033 stands: which engine, and its package.
When an engine exists, the index is derived data, built by `tootctl search
deploy` when a node joins, and never replicated by file (0033). Without
search, a user finds accounts and hashtags, but no text of posts.

### 6. The first boot

The first boot is unattended with inithooks, as in the other layers: the
domain, the admin name and email, the database password, and the
generated secrets. A primary or standalone node runs `db:setup` and makes
the admin account. A replica writes `.env.production` and nothing in the
database, and receives the shared secrets from the primary.

## How it is carried out

1. `Keel-Linux/keel-mastodon`: the layer on `lnpp`, the manifest, the
   units, the nginx route, the first boot, the tests and the boot test of
   the image gate (0061). It starts from `turnkeylinux/mastodon` with its
   history.
2. A Keel package of Node.js 24 in `Keel-Linux/apt` (0039).
3. `Keel-Linux/keel`: a second server section for Redis in the spec; the
   follow step for Redis in `dbfollow`; the worker `ReadWritePaths` rule;
   the call of `/usr/lib/keel/roles.d/`, which 0050 plans.
4. `Keel-Linux/keel-web` or `common`: the Anubis passes and the Coraza
   limit on the media routes, by the overlay pattern of 0036.
5. This repository: the Mastodon example of docs/manifest-v1.md gets the
   corrections in "What this amends".
6. The release test of the maintainer's rule (2 LXC on BR1, 1 on BR2, a
   pair across the sites, 3 etcd members, the netem profiles). It posts
   and uploads media through the failovers, and it federates with a
   second test server. The evidence file is
   `docs/evidence/<date>-mastodon-cross-site.md`.

No release of this application happens before the 0050 replication and
the database pair pass on a real pair (maintainer rule of 2026-10-20).

## Consequences

- The delivery of posts to other servers can lose the jobs in the queue at
  a failover. Posts and accounts in PostgreSQL lose nothing that
  committed.
- The first write after a flip waits for the cold start of Rails.
- The media directory of a federated server grows and churns more than the
  WordPress uploads. The link carries all of it.
- Search is absent until the engine question is settled.

## Open points

1. **Redis stage.** May the first release ship with Redis per node, not
   replicated (section 3.2), until keel converges Redis? The queue is
   lost at each failover in that stage.
2. **Cold Puma.** If the cold start of Rails is far above 5 s, is a warm
   Puma with a `503` gate at the route worth its added risk?
3. **Worker rule.** Does the maintainer accept the amendment of rule 24
   (workers may write inside the replicated paths of their manifest)?
4. **Node.js 24.** A Keel package built from the forky source, or the
   upstream tarball pinned by sha256?
5. **Media churn.** The remote cache may exceed what 250 ms links carry.
   The release test measures it. The fallback is a shorter retention.
6. **The repository.** Is `Keel-Linux/keel-mastodon` created as a fork of
   `turnkeylinux/mastodon` with its history?
7. **Search engine.** 0033 still has no choice between Elasticsearch and
   OpenSearch.

## What this amends

- **0035:** the database and Redis are embedded and follow the pair of
  0049 and 0054. They are not "from the mesh" in the first release. The
  base is `lnpp`.
- **docs/manifest-v1.md, the Mastodon example:** `base: lnpp`, not
  `ruby`; `nodejs` is `>= 24`, not `>= 20`; no `s3` service and no
  `objects` placement; a `state.replicate` of
  `/var/lib/mastodon/system`; the secret `otp_secret` is removed; Sidekiq
  has `singleton: true`; the derived row "Replication" lists the one
  folder; the closing text about object storage is removed.
- **docs/manifest-v1.md, rule 24:** a worker may write inside the
  `state.replicate` paths of its own manifest.
