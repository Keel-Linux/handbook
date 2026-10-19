# 0062: Nextcloud on the LNMP stack, the data directory on the 0050 replication

Date: 2026-10-19
Status: **decided by the coordinator under the maintainer's delegation,
2026-10-19** (the maintainer asked for the Nextcloud appliance with
"pode começar o NEXTCLOUD" and delegates design calls, least power each
time). The maintainer decided the standing rules this note applies:
0050 (file replication), 0059 (LNMP), 0049 (VIP and roles) and 0061
(one image per merge).

## What was asked

The Nextcloud appliance, as a layer on the LNMP stack (0059), with a
release test across two sites. This note picks: the data directory
across sites, locking and cache, background jobs, the write path on a
fenced node, the front behind Anubis and Coraza, and the version.

## Why (brief section 10)

1. **Why the current approach is not enough.** There is no Nextcloud
   image. The questions this note answers have different answers for
   Nextcloud than for WordPress: Nextcloud writes far more files
   (versions, thumbnails, chunks), it locks files while it writes, its
   sync clients speak WebDAV with large bodies, and its file cache
   lives in its database, so files and rows must agree after a
   failover.
2. **Whether it can be made to work.** It can, with the parts Keel
   already has: the one-writer database pair (0031, 0049), the file
   replication of 0050 with the folder flip on promote and demote, the
   nginx route pattern of the WordPress layer (0059), and the measured
   netem profiles of 0050 as the design case.
3. **Why this is better.** The data directory stays plain files in a
   plain directory, so a failover is one promote, one folder flip and
   one `occ files:scan --all`, and no data store beyond the database
   pair and the replication keel already runs learns about Nextcloud.

## Decision

### 1. Stack and version

Nextcloud is a layer on `lnmp` (nginx and PHP-FPM 8.4, MariaDB 11.8),
as WordPress is. Nextcloud 35 needs PHP 8.3 or newer; Debian 13 has
8.4. Nextcloud 35 needs MariaDB 10.11 or newer; the stack has 11.8.

The version is **Nextcloud 35.0.2**, the current upstream stable on
2026-10-15, **pinned by sha256** in the layer (0012, as the other
layers pin their sources). Upgrades move the pin, one release at a
time, after the same release test.

### 2. The data directory across sites: the 0050 replication

**The data directory replicates with the Syncthing service of 0050,
one writer per pair, and object storage as primary storage is
rejected for this appliance.**

- The primary's folder is send-only; every replica's folder is
  receive-only with versioning, as 0050 decides. The folder is the
  whole Nextcloud data directory (`data/`).
- The folder direction flips with the database and the VIP in one
  promote or demote operation (0049), and **the promotion runs `occ
  files:scan --all`**, as 0050 already records for Nextcloud: the file
  cache lives in the database, and the scan reconciles the rows with
  the files after the failover.
- **Why not object storage as primary storage.** Three reasons.
  First, 0050 measured it: every request to a quorum store pays the
  round trip of the link, 0.96 s per small read at 250 ms in the bench,
  and Garage documents 200 ms or less between nodes, below the design
  case. Second, primary storage stores files as objects, not as files:
  `occ files:scan` cannot reconcile them, the exit plan of 0050 (a
  copy, not a migration) does not hold, and the operator cannot read
  the data with shell tools. Third, Garage is not in Debian and stays
  a later regional step by 0050's own decision. Object storage keeps
  its 0058 role as the second step, not the first.
- **What "no acknowledged upload lost or orphaned" means here.** An
  upload is acknowledged when the client got a success answer. The
  semi-synchronous pair (0031) loses no committed row; the folder flip
  plus the scan loses no acknowledged file: a file whose row committed
  but that had not finished replicating is found by the scan, and an
  unfinished chunk upload is removed by the chunked-file cleanup job,
  so no file stays without its row and no row stays without its file.

### 3. Locking and cache: APCu and the database

**The local cache is APCu and transactional file locking uses the
database. Redis is not part of this appliance.**

- Only one node writes at a time (0049), so no distributed lock or
  shared cache exists to serve. APCu is per-node and fast; the
  database lock is correct across a failover, because the lock lives
  in the database the promote just moved.
- Redis (a second keel-redis pair, another fenced state) is more power
  than one writer needs. The day an application of Keel Web needs
  several writers, 0050's open point 1 names the direction, and the
  Redis layer already exists as a data service (0033).
- `memcache.local` is APCu in `config.php`; `memcache.locking` stays
  at the database default.

### 4. Background jobs: a systemd timer on the writable node

**A systemd timer runs Nextcloud's cron every 5 minutes, and only the
writable node runs it.** The timer unit carries a condition that
reads the node's role (the same role file the WordPress layer uses):
on a replica the job does not start, so no background job writes on a
fenced node. The timer runs `occ cron.php` as the web user, which is
Nextcloud's supported cron path. The web cron and AJAX cron stay off.

### 5. The write path: a warm standby, like Odoo

**Only the writable node accepts writes. The standby node is warm:
it runs nginx and PHP-FPM and serves reads, and it refuses writes at
the route, the way Odoo's `serve.py` does** (keel-odoo): a small
service watches the role and re-renders the route's write methods.
DAV write methods (`PUT`, `POST`, `DELETE`, `MOVE`, `MKCOL`, `COPY`,
`PATCH`, `PROPPATCH`, `LOCK` with a write intent) answer **503** on
the standby, with a short Retry-After, so a client that keeps a
connection through a failover retries on the new holder instead of
writing into a fence. Reads (`GET`, `HEAD`, `PROPFIND`, `OPTIONS`,
`REPORT`) answer normally. The route gate and the database fence
(0049's `read_only` and the loss of `READ_ONLY ADMIN`) agree: the
application cannot write on a fenced node two ways.

The first write after the VIP lands stays the measured target of 0059
and the WordPress and Odoo evidence: about 5 s. The warm standby is
what keeps it: PHP-FPM and MariaDB on the new holder are already
running when the VIP moves.

### 6. The front: WebDAV and large bodies behind Anubis and Coraza

**WebDAV, the sync clients and chunked uploads work behind Anubis and
Coraza, with only the exclusions they need.**

- The exclusions are the official CRS Nextcloud rule-exclusion plugin
  (`coreruleset/nextcloud-rule-exclusions-plugin`, vendored at a pinned
  version), plus one Keel rule: **request body inspection is off for
  DAV file payloads** (`PUT` of `/remote.php/dav/...`), because Coraza
  buffers the body and a 100 MB upload is not an attack surface to
  inspect with CRS rules. The body limit of the front site (keel-web#15,
  1 MB) is raised on the DAV routes only, to the PHP upload limit;
  every other route keeps the 1 MB limit that protects the machine.
- **Anubis passes the sync clients**: the DAV endpoints, `status.php`,
  the OCS API and the desktop, mobile and `nextcloudcmd` user agents
  reach the app without the proof-of-work challenge, as the websocket
  path already does for Odoo (common#62). Browser traffic keeps the
  challenge.
- Chunked uploads (the v2 chunking endpoint) are plain DAV `PUT`s of
  chunks, so they take the same route and the same limits.

### 7. The first boot

The first boot is unattended with inithooks: the admin password, the
domain and `trusted_domains`. A primary or a standalone node installs
the site (the schema, the admin, the config). A replica writes
`config.php` and nothing in the database, as the WordPress layer does,
and seeds from the primary with `keel spec apply --system-only`.
`/keel-check/` reports the role, the database state, the replication
lag and the scan state, like the other layers.

## How it is carried out

1. `Keel-Linux/syncthing`: the Syncthing v2 package of 0050, built from
   upstream source, carried in the Keel archive (0039).
2. `Keel-Linux/common`: the `keel-overlay-syncthing` overlay (0036): the
   service as a dedicated user, the configuration derived from the
   manifests' `state.replicate` folders and the role, discovery, relays
   and NAT traversal off, versioning on the receive-only folders.
3. `Keel-Linux/keel`: the folder flip in promote and demote, with the
   database and the VIP (0049), and the report of local changes on a
   replica in `keel diff` and in the alert.
4. `Keel-Linux/keel-nextcloud`: the layer, the manifest (`base: lnmp`),
   the route, the first boot, the cron timer, the writable gate, the
   tests and the boot test of the image gate.
5. `common` or `keel-web`: the DAV limits and the CRS plugin, by the
   overlay pattern of 0036.
6. `Keel-Linux/apt`: `conf/image-ci` watches `keel-nextcloud`, and the
   CI set gains `nextcloud` (0061).
7. The release test of the maintainer's rule: 2 LXC on BR1 and 1 on
   BR2, the pair across the sites, 3 etcd members, at base and under
   the 250 ms netem profiles, with uploads running through the
   failovers. The evidence file is `docs/evidence/2026-10-19-
   nextcloud-cross-site.md`.

## Consequences

- Nextcloud's data directory is the first real application of 0050's
  replication on a running application; the WordPress uploads folder
  takes the same path.
- The data directory holds versions and thumbnails, so it is larger
  and churns more than WordPress uploads; the replication lag the
  design accepts (0050) is what a reader on the standby sees.
- Uploads larger than 1 MB work in the cloud modes on the DAV routes;
  the 1 MB limit stays everywhere else until keel-web#15 has a
  general answer.

## Open points

1. keel-web#15: the general body limit of the front site. This note
   carves the DAV routes out of it; it does not solve it.
2. 0050's open points stand, open point 4 included: the rejoin check
   for edited files relies on the receive-only report, which covers
   new files. The release test exercises the cut cases of the list.
3. Several writers at once: 0050's open point 1. Nothing here changes
   it.

## What this amends

Nothing. This note applies 0049, 0050, 0059 and 0061 to the Nextcloud
layer. It rejects object storage as primary storage for this appliance
under 0050's section 5, which already made Garage a regional second
step.
