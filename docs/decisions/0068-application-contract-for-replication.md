# 0068: The application contract for replication

Date: 2026-10-25
Status: **decided by the maintainer, 2026-10-25**: the contract for file
and database replication on a pair, and the default replicate path of
Keel Web.

## What was asked

An operator or a contributor who builds an application image on the Keel
framework must declare three things: which stack the application uses,
which database the stack carries, and which filesystem paths replicate
between pair nodes. The decisions that define each piece exist (0034 the
contract, 0041 the manifest, 0050 the file replication, 0059 the stacks),
but no single note says what the author of an application writes and what
the platform does with it. This note does.

A second question: Keel Web, the base of every web appliance, declares the
Syncthing overlay (0050's amendment, item 1) but no replicate path. A pair
of a stack image (LNMP, LNPP) replicates its database and no file, so a
failover loses what the operator put on disk. The maintainer asked for a
default replicate path on Web itself.

## Why (brief section 10)

1. **Why the current approach is not enough.** The contract is spread across
   four decisions, the manifest reference, the Syncthing code and the
   WordPress manifest. A contributor reads six documents and pieces together
   which fields to write. WordPress and Odoo each had to discover the
   pattern by building it. A single reference makes the third application
   easier than the second.
2. **Whether it can be made to work.** Every piece exists. This note adds
   no code and one manifest field value.
3. **Why this is better.** A contributor reads one note, writes one manifest,
   and the platform handles replication, failover and backup.

## Decision

### 1. What a base stack brings

The stack determines the database engine and the web server. The
application does not choose either separately.

| Stack | Database | Web server | Inherits |
| --- | --- | --- | --- |
| `lnmp` | MariaDB | Nginx | Web → Core |
| `lnpp` | PostgreSQL + gunicorn | Nginx | Web → Core |
| `web` | none | Nginx | Core |

The database replicates by its own protocol: MariaDB's binary log (0031)
or PostgreSQL's streaming replication (0054). The application does not
configure database replication. `keel database follow` handles the role,
the seeding and the catch-up.

### 2. What Web brings: the Syncthing service and a default path

Keel Web declares the Syncthing overlay, disabled in simple and enabled in
the cloud modes (0050's amendment, item 1). In a pair, the service runs,
exchanges device identities over the members' channel, and replicates
every path the resolved manifest declares under `state.replicate`.

**Web declares one default path:**

```yaml
state:
  replicate:
    - /var/www/keel-default
```

`/var/www/keel-default` is the document root of the default Nginx site
(keel-web 0.2.0). On a fresh image it is a symlink to the package's
placeholder pages under `/usr/share/keel-web/default-site`. When an
operator replaces the symlink with a directory and puts content there, that
content replicates to the other node of the pair.

An application that sets `web.root` to its own path (WordPress sets
`/var/www/wordpress`) does not use `/var/www/keel-default`, but the folder
exists and is harmless: Syncthing skips a symlink target under `/usr/share`
(it is read-only and owned by the package), and an empty directory
replicates nothing.

### 3. What the application declares

An application is an appliance manifest with `base: lnmp`, `base: lnpp` or
`base: web`. It declares:

| Field | What it means | Example (WordPress) |
| --- | --- | --- |
| `base` | The stack, which determines the database | `lnmp` |
| `services.database` | The engine, version, placement and credential | `engine: mariadb`, `secret: db_password` |
| `state.replicate` | The paths the application writes at run time, each a directory | `uploads`, `themes`, `plugins`, `languages` under `/var/www/wordpress/wp-content/` |
| `state.exclude` | Paths inside a replicated one that must not replicate: caches, temp files, locks | (WordPress declares none: `cache`, `upgrade` and `upgrade-temp-backup` are not inside a replicated path) |

The application inherits Web's default path. Its own paths are additional.

**Worked example: WordPress on LNMP.**

```yaml
manifest_version: 1
kind: appliance
name: wordpress
title: Keel WordPress
summary: WordPress on nginx, PHP-FPM and MariaDB (0047, 0059)
base: lnmp
state:
  replicate:
    - /var/www/wordpress/wp-content/uploads
    - /var/www/wordpress/wp-content/themes
    - /var/www/wordpress/wp-content/plugins
    - /var/www/wordpress/wp-content/languages
services:
  database:
    engine: mariadb
    version: ">= 10.11"
    required: true
    placement: {simple: embedded, cloud_simple: embedded, cloud_advanced: discovered}
    durable: true
    secret: db_password
    defaults: {name: wordpress, user: wordpress}
```

**Worked example: a bare LNMP pair.** An operator installs LNMP in
`cloud_simple`, makes a database pair, and puts a custom site under
`/var/www/keel-default`. The pair replicates the database (MariaDB) and
the default path (from Web). No application manifest exists and none is
needed.

### 4. What the platform does

The platform, not the application, handles everything below:

| Concern | Who does it | Decided in |
| --- | --- | --- |
| Database replication | `keel database follow`, the binary log or streaming replication | 0031, 0054 |
| File replication | The Syncthing overlay, one folder per replicated path | 0050, this note |
| The flip | `keel database promote`: changes the database role **and** the Syncthing folder directions in one operation | 0050's amendment, item 5 |
| Ownership | A flip to primary restores the application owner over the replicated paths | keel#225 |
| Boot resume | A boot pauses the folders until the first proven follow | keel#228 |
| Backup | TKLBAM reads `state.replicate` minus the excludes | 0037 |
| Monitoring | Monit reads every process and check of the resolved chain | 0040 |

### 5. Redis and other parallel services

A future application may use Redis as a session store or a cache beside
the primary database. Redis is a data service (0033) with its own
replication (Redis Sentinel or Redis Cluster), not file replication. Its
placement follows the same `services.<name>` schema.

This note does not specify how Redis replicates in a pair. That is a
decision for the first application that needs it (Mastodon, 0035, declared
`durable: false` and `rebuild` for its Redis, 0062 for Nextcloud). Until
then, Redis on a pair is out of scope.

## What this amends

- **0034**: the contract is now complete, with file replication (0050) and
  the flip. The four items of 0034 remain: runtime overlays, data services,
  replication paths, and workers.
- **0041, docs/manifest-v1.md**: `state.replicate` moves from the
  application sections only to also being valid on a base layer. Web
  declares one path. The validation rule 23 applies to both. The derivation
  row "File replication" changes from `cloud_advanced` only to
  `cloud_simple` and `cloud_advanced` (already amended by 0050).
- **0050's amendment, item 1**: confirmed and cited. Files replicate in
  `cloud_simple` and `cloud_advanced`.
