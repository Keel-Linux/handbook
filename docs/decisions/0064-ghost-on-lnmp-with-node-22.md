# 0064: Ghost on the LNMP stack with Node.js 22, on MariaDB that upstream does not support

Date: 2026-10-24
Status: **proposed, 2026-10-24.** The maintainer ordered the Ghost
appliance on 2026-10-24. The coordinator assigned this note. Section 2
and open point 1 need a maintainer answer before any build.

## What was asked

A Ghost appliance, as a layer on a Keel stack, that survives a failover
between sites. This note answers: the version, the base, the database
engine, the run-time state, what runs only on the primary, and the front.
It does not build anything.

## Why (brief section 10)

1. **Why the current approach is not enough.** Keel has no Ghost image.
   Decision 0036 lists Ghost as "Node, MariaDB". That row is wrong in one
   point: Ghost supports MySQL 8 only. The row also names no run-time
   state, and Ghost needs a Node.js version that Debian 13 does not have.
2. **Whether it can be made to work.** It can, with three conditions.
   Node.js comes from upstream, pinned. MariaDB must pass a gate of our own,
   because upstream gives no support for it. Ghost runs only on the primary,
   because it has no read-only mode.
3. **Why this is better.** The appliance reuses the LNMP pair (0031, 0049)
   and the file replication (0050). No second database engine enters Keel
   for one application. If the gate fails, the note says what to do instead.

## Decision

### 1. Upstream, version and prior art

| Item | Fact | Source |
| --- | --- | --- |
| Version | Ghost **6.72.0**, released 2026-10-20, pinned | GitHub releases of `TryGhost/Ghost`; npm `ghost@6.72.0` |
| Form | the npm package `ghost-6.72.0.tgz` (14.8 MB, 158 dependencies); the layer pins its sha512 and a reviewed lock file | npm registry |
| Licence | MIT, Ghost Foundation | `LICENSE`, `package.json` |
| Node.js | `^22.23.1 \|\| ^24.20.0` | `ghost/package.json` at v6.72.0 |
| Database | "MySQL 8 is the only supported database in production" | docs.ghost.org, FAQ "Supported databases" |

Debian 13 has no package for Ghost. Debian 13 has Node.js 20.19.2, which
Ghost 6.72.0 refuses. The layer cannot use the Debian package.

**Node.js 22.** The layer installs the upstream Node.js 22.23.x tarball
from nodejs.org, pinned by sha256 (0012), under `/opt/node`. Ghost builds
its own image on 22.23.3 (`Dockerfile.production`), so 22 is the tested
line. Node.js 22 ends on 2027-04-30; Node.js 24 ends on 2028-04-30 and
Ghost accepts it from 24.20. The move to 24 is open point 3.

**TurnKey prior art.** `turnkeylinux-apps/ghost` exists: 209 commits, the
last one on 2022-11-11. It installs Node.js 16 with `n`, MariaDB from the
TurnKey MySQL stack and Ghost with `ghost-cli`, under `/opt/ghost`. That
design is too old and needs the network at build time. The fork with full
history is `Keel-Linux/keel-ghost` on git.pop.coop. We keep its inithook
pattern and the confconsole service list. We do not keep `ghost-cli`.

Why not `ghost-cli`. It writes systemd units, nginx files and users by
itself, and it installs from the network. Keel does these steps in
overlays, with packages and pins.

### 2. Base and database

**The base is `lnmp`, with PHP-FPM turned off.** LNMP already carries
nginx (Keel Web), MariaDB 11.8 and the pair files (0059, section 3). There
is no stack with Node.js and a database. A new stack is more power than one
application needs. The layer adds Node.js and Ghost, and its manifest sets
the `php-fpm` overlay to `disabled` in the three modes.

**MariaDB does not match upstream, and the note says so.** Facts checked:

- Ghost supports MySQL 8.0 and 8.4 only. The install guide lists "MySQL 8.0
  or 8.4". The FAQ says: "We strongly recommend migrating from MariaDB to
  MySQL 8."
- The Ghost CI and the Ghost dev setup use MySQL 8.0 and 8.4, and SQLite
  for tests. The `.github` tree and the compose files name no MariaDB.
- Ghost 6.72.0 has no code that refuses MariaDB. A search of
  `ghost/core` finds no MariaDB test and no `utf8mb4_0900` collation. This
  shows that Ghost may start on MariaDB. It does not show that every
  migration and query is correct.
- Debian 13 has no MySQL 8 package. It has MariaDB 11.8.6 only. MySQL 8
  means Oracle's repository or a build of our own.
- A MySQL 8 pair is a new pair. Decision 0031 is about MariaDB semi-sync
  replication and its fencing. A second engine needs its own decision
  and its own real-platform test.

**Decision: Ghost ships on the MariaDB 11.8 pair, behind a gate, and the
release notes say that upstream does not support the database.** SQLite is
rejected: upstream does not support it in production, and a database file
cannot replicate by file (0032, 0054). The gate has three parts. All three
must pass before the first pre-release:

1. A clean install and the full migration chain of 6.72.0 run on MariaDB
   11.8 with no error.
2. The database tests of Ghost (`ghost/core`, MySQL mode) run against
   MariaDB 11.8 in the CI of `keel-ghost` with no failure that is not on
   a list we justify, one line each.
3. The failover test of the maintainer's rule (section 6) passes.

The gate runs again for every Ghost version we pin. If part 1 or 2 fails
and the cause is not a small patch, Ghost waits for a MySQL 8 decision.
That decision is not part of this note.

### 3. The pair across sites

| Item | Choice |
| --- | --- |
| Database | `ghost`, in the MariaDB pair of the stack (0031, 0049). `db_password` is `shared` |
| Ghost secrets | none to share. Sessions, the members keys and the settings are rows in the database |
| Run-time state | the paths below |

**`state.replicate`.** The content path is `/var/lib/ghost/content`
(`paths.contentPath`). The code is in `/var/www/ghost`, owned by root, and
Ghost writes only to the content path, and its logs go to journald. Five paths replicate:

```yaml
state:
  replicate:
    - /var/lib/ghost/content/images
    - /var/lib/ghost/content/media
    - /var/lib/ghost/content/files
    - /var/lib/ghost/content/themes
    - /var/lib/ghost/content/settings
```

- `images`, `media` and `files` hold the uploads.
- `themes` holds the themes that an editor uploads in the admin.
- `settings` holds `routes.yaml`, which the admin uploads.
- Ghost keeps `redirects.json` and `redirects.yaml` in `content/data`, with
  the JSON exports and the backups. We do not replicate `content/data`.
  The layer sets `adapters.redirects.FileStore.basePath` to the
  `settings` path, so the redirects replicate with `routes.yaml`. The
  layer test must prove that setting. If it fails, open point 4 applies.
- `content/public` holds assets that Ghost builds at start. `content/logs`
  holds logs. `content/adapters` holds code that the layer ships. None of
  them replicates.
- No `state.exclude` is needed: no excluded path lies inside a replicated one.

**What runs only on the primary.** Ghost runs all its jobs inside one Node
process: the post scheduler, the newsletter batches, the member emails,
the webhooks and the update check. All of them write to the database.
Ghost has no read-only mode and no separate worker. Thus:

- **`ghost.service` runs on the primary and on a standalone node only.**
  It is not a manifest `worker`, because a worker writes no local file
  (0034) and Ghost writes uploads. The unit has a condition on the role
  file, as the Nextcloud timer has (0062). The promote operation starts it
  and the demote operation stops it, in the same step as the folder flip.
- **The standby is cold for the application.** nginx and MariaDB run.
  Ghost does not. nginx answers `503` with `Retry-After` on every path
  except `/keel-check/`. This differs from Odoo and Nextcloud, which have
  a warm standby, and the cause is that Ghost writes at start and on read.
- **Mail.** Ghost sends transactional mail by SMTP, from the `mail`
  config. Newsletters use Mailgun only, with the keys in the settings
  table. Only the primary runs Ghost, so only the primary sends mail.
- **First write after the VIP moves.** It waits for the start of Ghost.
  The time is not measured. The release test measures it and records it.

**Native replication.** Ghost has none. The choice is the pair for rows and
Syncthing for files, as for WordPress.

### 4. Ports, mesh, route, TLS and checks

| Item | Choice |
| --- | --- |
| Ghost | `127.0.0.1:2368`, `server.host` set to loopback, never `mesh` |
| Mesh ports | none from Ghost. MariaDB 3306 and the Syncthing port are those of the stack and of 0050 |
| Route | `web.routes: [{path: /, to: {port: 2368}}]` in the nginx site of Keel Web |
| TLS | Keel Web terminates it. nginx sends `X-Forwarded-Proto: https`. The config `url` is the `https` URL, or Ghost redirects without end |
| Health | `GET /ghost/api/admin/site/` expects 200. It reads the database, and it needs no login |
| Monit | the `ghost` unit, only where the role is writable; the health probe; the checks of the stack |
| Body size | uploads go through `/ghost/api/admin/`. The 1 MB limit of keel-web#15 is raised on that route only, as 0062 does for DAV |
| Anubis | the Content API (`/ghost/api/content/`), the Admin API with a token and the webhooks bypass the challenge. Readers keep it |
| Coraza | the editor sends HTML in JSON bodies. A rule exclusion for `/ghost/api/admin/` is needed, as for WordPress and Nextcloud. The layer test lists it |

### 5. First boot and first test

The inithook sets the `url`, the admin account, the `db_password` and the
SMTP host. A primary creates the schema through Ghost itself. A replica
writes the config and nothing in the database. The layer test is a boot
test, then the gate of section 2, then the release test of the maintainer:
2 LXC on BR1, 1 on BR2, the pair across sites, at base and under the
250 ms profiles of 0050. Uploads and post publication run through the
failovers. The evidence file is `docs/evidence/<date>-ghost-cross-site.md`.

## Risks

1. **Unsupported database.** A Ghost migration may use a MySQL feature that
   MariaDB lacks. The gate catches it for one version only. Each upgrade
   carries the same risk.
2. **No warm standby.** The failover time includes the start of Ghost. If
   the time is too long, the maintainer may want a warm standby, which
   Ghost does not allow.
3. **Pinned lock file.** 158 dependencies include native modules (`sharp`).
   Each Node.js or Ghost bump must rebuild and test them.
4. **PHP is carried and unused.** `php-fpm` is installed and disabled on
   the stack. It costs disk and update work.
5. **Node.js 22 ends in 6 months.** A move to 24 is a test, not a risk,
   but it has a date.

## Open points for the maintainer

1. **Do we ship Ghost on MariaDB that upstream does not support, behind
   the gate of section 2?** The other path is a MySQL 8 pair, which needs
   its own decision. Yes or no.
2. **Do we accept the cold standby, with `503` on the standby?** The
   alternative is no Ghost on the pair. Yes or no.
3. **Node.js 22 now and 24 later, or 24 now?** Ghost builds on 22. The
   coordinator proposes 22.
4. **Is a `redirects` path outside the replicated set acceptable if the
   `basePath` setting does not work?** The cost is that redirects do not
   follow a failover.
5. **Should the stack get a Node variant?** A layer `lnmn` would drop PHP
   for Ghost and NodeBB. This note does not propose it.
6. **The `ghost.service` rule needs a manifest field.** A web process
   that runs only on the active node has no place in manifest version 1.
   This note uses a role condition on the unit. An erratum of 0041 may
   add a field.

## What this amends

- **0036**: the Ghost row of the application table ("Node, MariaDB")
  is replaced by this note. MariaDB is gated, upstream supports MySQL 8
  only, and the replicated state is the five content paths.

It amends nothing else. It applies 0031, 0034, 0049, 0050, 0059, 0061 and 0062.
