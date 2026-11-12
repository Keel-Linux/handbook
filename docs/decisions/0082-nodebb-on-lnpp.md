# 0082: NodeBB on the LNPP stack, on PostgreSQL, with Node.js 24 from the Keel Node.js package

Date: 2026-11-10
Status: **decided by the maintainer, 2026-11-10.** The maintainer
answered the three open points on 2026-11-10: point 1 with "sim" (option
D, decision 0083), points 2 and 3 with "sim tudo". Nothing in it is
built.

## What was asked

How do the Node.js stack (`keel-nodejs-nginx`) and the NodeBB appliance
(`keel-nodebb`) move to the composition architecture, to the standard of
the applications of round A3? This note picks the stack, Node.js, the
database, the modes, the live forum and the order of work.

## Why (brief section 10)

1. **Why the current approach is not enough.** `keel-nodejs-nginx`
   (main 07facd5, 19.0-1) is a layer on `core` with nginx, nodejs, npm
   and redis-server. It has no Keel Web, no manifest and no tests.
   `keel-nodebb` (main 3c285dc, 19.0-6) is a monolithic image: NodeBB
   4.10.3 on a local Redis, its own nginx site, no contract. It cannot
   make a pair, because Keel has no Redis pair.
2. **Whether it can be made to work.** It can, with the parts that
   passed round A3: Keel Web, `lnpp` with the PostgreSQL pair (0054),
   the file replication (0050, 0068) and the writable gate of keel-odoo.
3. **Why this is better.** No new stack and no new data service enter
   Keel. NodeBB is the second application on `lnpp`, and its pair is the
   pair that Odoo commissioned in every mode.

## Facts checked

| Item | Fact | Source |
| --- | --- | --- |
| Version | NodeBB 4.16.7, released 2026-10-31 | GitHub releases of `NodeBB/NodeBB` |
| Node.js | 4.16.7 needs `node >=22`. undici 8.12.3 needs `>=22.19.0`. 4.10.3 was the last on `>=20` | `install/package.json` at v4.16.7 and v4.10.3; npm registry |
| Upstream test | the CI runs Node.js 24 only, on mongo, redis and postgres (PostgreSQL 18) | `.github/workflows/test.yaml` at v4.16.7 |
| Debian 13 | nodejs 20.19.2 (trixie-security deb13u3). No backport. forky has 24.22.2 | qa.debian.org madison |
| Node.js end of life | 20: 2026-04-30. 22: 2027-04-30. 24: 2028-04-30 | `nodejs/Release` schedule.json |
| Databases | `src/database/` has `redis`, `mongo` and `postgres`. Debian 13 has no MongoDB | NodeBB source; madison |
| Sessions | with no `redis` key, the session store is the primary database (`connect-pg-simple`, table `session`) | `src/database/index.js`, `postgres.js` |
| Pub/sub | with `isCluster` false, pub/sub is an in-process EventEmitter. With `isCluster` true and no Redis, NodeBB stops with `redis-required-for-pubsub`. An array in `port` forks one worker per port and sets `isCluster` true | `src/pubsub.js`, `loader.js` |
| Several processes | "Redis needs to be configured alongside your primary data store". The sample upstream block uses `ip_hash`. `jobsDisabled` on all but one server | docs.nodebb.org/configuring/scaling/ (read through a fetch tool, not quoted) |
| Writes at start | the primary process runs `CREATE TABLE IF NOT EXISTS "session"` | `postgres.js`, `createSessionStore` |
| Uploads | `upload_path`, default `public/uploads`, resolved against `base_dir`. An absolute path is allowed | `src/prestart.js` |
| Plugins | `acpPluginInstallDisabled` is a config key | `src/prestart.js` |
| Install, upgrade | `./nodebb setup '<json>'` takes every answer. `./nodebb upgrade` runs the schema, package and build steps. The global option `-y` (`--unattended`) answers its prompts | `src/cli/index.js` |
| Migration tool | `nodebb-postgres-converter` reads Redis and writes PostgreSQL. Its repository is archived (last push 2020-05-15), its last npm release is 0.1.1 (2022) | GitHub API, npm registry |

## Decision

### 1. The stack: no Node.js stack, NodeBB is a layer on `lnpp`

| Option | Facts | Result |
| --- | --- | --- |
| A. Keep `nodejs-nginx` on `core` | no Keel Web, no Coraza, no Anubis, no pair. It is the architecture before 0059 | rejected |
| B. A Node.js stack on `web` with no database | the layer must copy the database half of `lnpp` | rejected |
| C. A new stack, Web plus PostgreSQL plus Node.js | a fourth stack for one application. Ghost (0064) is on MariaDB | rejected for now |
| D. NodeBB on `lnpp`, Node.js in the application layer | the pair and its contract exist. The layer removes the socket-activated check page of `lnpp`, as Odoo does | **chosen** |

Node.js is not in the layer. The layer installs the Keel Node.js package
of 0083, and a second image that needs Node.js installs the same package.
Common's `conf/nodejs`, which installs Node.js with `n`, is not used.

**The old layer.** `keel-nodejs-nginx` gets no new build. After step 7,
its repository is archived with a README line to this note, and the name
is not used again.

### 2. Node.js: version 24, from the Keel Node.js package of 0083

| Option | Facts | Result |
| --- | --- | --- |
| A. Node.js 24 from the nodejs.org tarball, pinned by sha256 (0012) under `/opt/node` | the line that NodeBB tests. Supported to 2028-04-30. Ghost accepts `^24.20` (0064). No apt update: a Node.js security release is an image rebuild (0073) | rejected: apt can update an installed machine, but it cannot update a file in an image. It is not a fallback: the layer waits for the package of D |
| B. Debian's Node.js 20 | NodeBB stays at 4.10.3, six minor releases behind. Upstream ended Node.js 20 on 2026-04-30 | rejected: an old NodeBB on a line with no upstream support |
| C. A Keel archive package of forky's 24 (the 0074 pattern) | apt updates, but a V8 build and new build dependencies on trixie | rejected: the official binary of D gives the same line with no V8 build |
| D. A Keel package of the official Node.js 24 binary from nodejs.org (0083) | the build checks `SHASUMS256.txt.asc` against the pinned release keys and the pinned sha256. Updates come by apt through `trixie-testing`, then stable. One line for all Keel applications | **chosen** |

**Decision: D**, by the maintainer on 2026-11-10 in 0083. The package
name is a proposal (`keel-nodejs`), and 0083 lists its open points. Ghost
(0064) and Mastodon (0065) use the same package and the same line.
NodeBB ships no lock file, so the layer commits a reviewed
`package-lock.json` and runs `npm ci` (0012).

### 3. The database: PostgreSQL in every mode, no Redis

**NodeBB uses the PostgreSQL of `lnpp`: embedded in `simple`, the 0054
pair in `cloud_simple` and `cloud_advanced`.** Redis is not in the
image.

- Redis as the database is rejected: Keel has no Redis pair (0068,
  section 5). MongoDB is rejected: Debian 13 has no package.
- Redis is needed only when more than one NodeBB process serves one
  forum (pub/sub, the socket.io adapter). A pair has one writer (0049).
  `config.json` sets one `port` value, never an array, so `isCluster`
  stays false. Several processes are 0081's question.
- `config.json`: `database: postgres` on `127.0.0.1`, database and user
  `nodebb`, the password from `db_password`.

### 4. The modes: all three in one image, from the first release

**One image serves `simple`, `cloud_simple` and `cloud_advanced`
(0047), and the contract runs all five passes of 0075.** The pattern is
keel-odoo's, item by item:

- **Writable gate.** NodeBB writes at start, so it cannot start against
  a server in recovery. A watcher, like `serve.py`, starts NodeBB on the
  node whose PostgreSQL accepts writes and stops it on a standby.
  `nodebb.service` is not a manifest process, for the Monit reason that
  `odoo.yaml` gives.
- **Standby notice.** On the standby the watcher writes a mark, and
  nginx answers every NodeBB path with the replica notice, status 200.
- **`state.replicate`.** One path: `/var/lib/nodebb/uploads`, set as
  `upload_path`. The code in `/var/www/nodebb` is owned by root, except
  what NodeBB writes on each node: `build/`, `config.json`, `logs/` and
  the pidfile. `nodebb` owns them, and they do not replicate.
- **Plugins and themes are image content.** `acpPluginInstallDisabled`
  is true. An admin who activates a bundled plugin or theme writes the
  database, and `build/` must follow. The watcher runs `./nodebb build`
  before the start when the active set in the database differs from the
  set of the last build on that node.
- **Secrets.** `db_password` is the stack's, `shared: true`. NodeBB's
  `secret` signs the session cookie. It is a manifest secret with
  `shared: true`, so a login survives a promote: the session row
  replicates and both nodes accept its cookie.
- **WebSocket.** One process holds all sockets, so no `ip_hash` and no
  sticky session. After a promote the socket.io client connects again
  to the VIP. The contract measures the time to the first write after
  the VIP moves. It is not measured today.
- **Upgrades.** The image carries the code. The watcher runs `./nodebb
  -y upgrade -s` (a schema write) on the writable node only.

### 5. Routes, front and first boot

| Item | Choice |
| --- | --- |
| NodeBB | `127.0.0.1:4567`, never on the mesh |
| Routes | `keel-default.d/` and `keel-front.d/`. NodeBB's own site goes |
| `/socket.io/` | the `Upgrade` headers and a long read timeout, as Odoo's `/websocket`. Anubis passes it |
| Body size | the upload route only is raised (keel-web#15), as in 0062 |
| Coraza | posts carry HTML and Markdown in JSON. The layer test lists each exclusion |
| Port 80 | 0079: port 80 serves NodeBB while the certificate is self-signed. `url` is the `https` URL. The contract checks port 80 and the login cookie |
| First boot | `45nodebb`, after `35pgsqlpass` and `40lnpp-check`. A primary or `simple` node runs `./nodebb setup`. A replica writes `config.json` and nothing in the database |

### 6. The live forum

`forum.keellinux.org` answers today. Its public API on 2026-11-10 shows
5 categories, 0 topics, 0 posts and 2 users. That is what a guest sees,
so a private category does not show. The data is on Redis in the
`forum` container on the build host. `docs/infra-recovery.md` says no
backup of it exists.

**Decision: create the forum again on the new appliance and copy no
data.** The maintainer decided this on 2026-11-10 ("sim tudo"). The
categories and settings are entered again by hand. The converter is
archived and is not tested on NodeBB 4.x, and nobody tests it.

### 7. The order of work

Each step is one PR and has its own test.

Before step 1, the Keel Node.js package of 0083 is built from its own
source repository and published to `trixie-testing`. Test: the build
checks the signature and the sha256, and `node -v` shows the pinned
version. That work belongs to 0083, not to this note.

1. `keel-nodebb`: base `lnpp`. Drop Redis, the own nginx site and the
   build-time apt block. The `plan` installs the Keel Node.js package.
   NodeBB 4.16.7 by sha256, the lock file, `npm ci`. Test: the layer
   builds, `node -v` and the image check.
2. The manifest `nodebb.yaml`: `base: lnpp`, `state.replicate`, the two
   shared secrets, no process. Test: `tests/manifest.bats` and `keel
   validate`.
3. `config.json`, the first boot `45nodebb` and the watcher. Test: bats
   and pytest of each branch, kcov 90 % or more (0003).
4. The routes, Anubis, Coraza and the replica notice. Test:
   `tests/nginx.bats`, `nginx -t`.
5. `tests/commission.yaml`: secrets root, db, app. Checks: a row and an
   upload replicate, NodeBB on the primary only, a login across a promote.
6. `Keel-Linux/apt`: `conf/image-ci` watches `keel-nodebb` (0061). The
   image of the testing track takes the Node.js package from
   `trixie-testing`.
7. Commissioning of 0075 on BR1 and BR2: lxc-interactive, lxc-preseed,
   vm-iso, `cloud_simple`, `cloud_advanced`, with screenshots and the
   evidence file.
8. The new forum with no data copy (section 6). Then the archive of
   `keel-nodejs-nginx`, after NodeBB passed step 7.

**Not in this note:** several NodeBB processes (0081), a Redis pair,
the Ghost layer (0064), ActivityPub, the public proxy, a forum backup.

## Consequences

- `lnpp` has two applications. A change to the stack is tested on both.
- A Node.js security release is a new build of the Keel Node.js package,
  which apt installs on a machine through the Keel channel (0083). An
  image rebuild is not necessary for it.
- A plugin that is not in the image cannot be installed from the admin.

## Open points for the maintainer

1. **Answered on 2026-11-10.** The maintainer decided the Keel Node.js
   package (option D) in 0083. Options A, B and C are rejected.
2. **Answered on 2026-11-10 ("sim tudo").** The forum is created again
   with no data copy. No private content of the old forum is kept.
3. **Answered on 2026-11-10 ("sim tudo").** `keel-nodejs-nginx` is
   archived after NodeBB passes the commissioning of step 7.

## Not verified

Step 7 measures the first write after a promote and `./nodebb build`.
Nobody checked NodeBB on PostgreSQL 17, private forum content or the
converter on NodeBB 4.x.

## What this amends

- **0036**: the "Keel Node" image is not made. NodeBB is on `lnpp`.
- **`docs/forum.md`**: the database is PostgreSQL. Node.js comes from
  the Keel archive (0083), not from the Debian archive.

It applies 0047, 0049, 0050, 0054, 0059, 0068, 0075, 0079 and 0083.

## Amendment 2026-11-12: the results of the prototype

The maintainer answered the questions of the first real-node test on
2026-11-12. The coordinator chose answer A for the session secret. The
evidence is `evidence/2026-11-11-keel-nodejs-nodebb-real-node-test.md`
and `evidence/2026-11-12-keel-nodejs-24-restart-and-session-secret.md`.

1. **The Node.js package of the layer is `keel-nodejs-24`.** Each line is
   its own package (0083, amendment). The plan names the line. A change
   of line is a change of the plan and a new commissioning.
2. **A path unit of the layer restarts NodeBB.** The package has no
   maintainer script, so NodeBB keeps the old binary after an upgrade.
   `nodebb-nodejs.path` watches `/usr/lib/keel-nodejs/bin/node` and runs
   `systemctl try-restart nodebb.service`.
3. **The session secret is in the database, not in the manifest.**
   Section 4, "Secrets", said that NodeBB's `secret` is a manifest secret
   with `shared: true`. The layer keeps it in the one-row table
   `keel_nodebb_secret` of the database `nodebb`, as WordPress keeps its
   salts. The first writable boot writes the row, from
   `KEEL_SECRET_NODEBB_SECRET` when the spec declares
   `secrets.nodebb_secret`, else a new value. No later boot and no
   replica changes it. `serve.py` gives it to NodeBB in the environment.
   So the secret replicates with the session rows. That a login survives
   a promote is not tested until a pair test runs.
4. **Known gap of keel:** keel has no general path that gives one
   generated value to both nodes of a pair. `shared: true` of a manifest
   is only validated. This note does not need it, and nobody works on it
   now.
5. **The writable list of section 4 gets one path:**
   `node_modules/nodebb-plugin-emoji/build`, and `build/emoji` in it.
   The plugin writes its data there at the first start of a node.
6. **NodeBB 4.16.7 runs on PostgreSQL 17.11** ("Not verified" above).
