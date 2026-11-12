# 0087: Nextcloud: Redis on each node, only the writer serves, the shared values come from the pair

Date: 2026-11-12
Status: **proposed** until the image passes the commissioning of 0075.
The maintainer decided its choices on 2026-11-12: "(a)" for Redis (one
Redis on each node, with the gate, sections 3 and 4), and the answers to
the five questions of the first draft (sections 3 and 7, "Decided
2026-11-12"). The note amends
0062 where two tests on real machines showed something different.
Nothing in it is released. The prototype is a local repository,
`keel-nextcloud`, with no image.

Three tests by hand are the basis of this note:

- the first test, one container on BR1
  (`evidence/2026-11-11-nextcloud-35-first-test.md`), marked "(first
  test)";
- the second test, an LNMP pair in cloud advanced across BR1 and BR2
  with a Core witness (`evidence/2026-11-12-nextcloud-35-cloud-advanced-pair.md`),
  marked "(second test)";
- the third test, on the same pair: the cause of the nginx memory under
  Coraza, and the scheme behind Anubis
  (`evidence/2026-11-12-nextcloud-35-third-test-coraza-scheme.md`),
  marked "(third test)".

## What was asked

Wave 2 of the migration to Keel is the Nextcloud appliance. On
2026-11-11 the maintainer gave two rules for it:

1. Redis is mandatory, for performance: the file locks
   (`memcache.locking`), the distributed cache and the PHP sessions, with
   APCu as the local cache. In the cloud modes the Redis must be the
   shared one of the Keel pattern, not a private Redis on each node.
2. The acceptance test is cloud advanced: a database pair across two
   sites, Syncthing, Redis, 2 containers on BR1 and 1 on BR2, netem.

The coordinator added on the same day: go on with the proposal that is
written below as section 3 (the least power), and record four
conditions (a) to (d). This note answers them in section 3. On
2026-11-12 the maintainer chose that proposal ("(a)"), and the
coordinator set the pass criterion of the gate: zero time with two open
gates.

## Facts checked

| Item | Fact | Source |
| --- | --- | --- |
| Release | 35.0.2 is the latest, 2026-10-15. Other lines: 34.0.5 and 33.0.10, also 2026-10-15 | download.nextcloud.com/server/releases |
| Signature | Each tarball has a signature of the key `28806A878AE423A28372792ED75899B9A724937A` ("Nextcloud Security") | nextcloud.com/nextcloud.asc; first test |
| PHP | 8.3, 8.4, 8.5 (8.5 recommended). Debian 13 has 8.4 | admin manual 35, system requirements |
| MariaDB | 10.11, 11.4, 11.8, 12.3. READ COMMITTED; `binlog_format = ROW` when the binary log is on | same |
| Isolation | Nextcloud sets READ COMMITTED for its session; `occ setupchecks` passes with the global REPEATABLE-READ of LNMP | first test |
| Binary log | keel sets `binlog_format = ROW` on a pair (`keel/system/dbmariadb.py`); a standalone LNMP node has `log_bin = 0` | keel source; first test |
| Upgrade | One major at a time: the latest point release of the current major first, then the next major. After a major, run `cron.php` 2 to 3 times before the next one | admin manual 35, "How to upgrade" |
| Caching | APCu for the local cache, Redis for the distributed cache and the locks; in a cluster all nodes must use the same Redis | admin manual 35, memory caching |
| Shared Redis in Keel | None: keel-redis has `modes: [simple]`, and 0068 section 5 leaves the Redis of a pair to the first application that needs it. WordPress and Odoo do not use Redis | keel-redis manifest; 0068 |
| keel hooks | keel runs no hook of an application at a promote; overlays have state hooks only | `keel/system/hooks.py` |

## What the tests showed

1. **Install.** `occ maintenance:install` as `www-data` over the socket,
   with no database password, 16 s, 138 tables. The code tree holds no
   state: after an operator error the tree came back from the tarball
   with `config.php` and `custom_apps` only (first test).
2. **A fenced node cannot serve sync clients.** With a read-only
   database, PROPFIND and GET answer 503 and a new login 500, with the
   locks in Redis or in the database. Each DAV request writes (the DAV
   authentication, the first-login listener). An existing browser
   session still loads pages (first test).
3. **A lost session is not a lost login.** After `FLUSHALL` of Redis the
   next page is 200: Nextcloud logs the browser in again from
   `oc_authtoken` (first test). After a real failover the same cookie and
   the same app password work on the other node (second test).
4. **Redis must be on the site of the serving node.** With Redis at
   250 ms, the files page took 12.6 to 27.2 s instead of 0.08 to 0.32 s
   (first test).
5. **A secret in the log.** With Redis down, PHP writes
   `session.save_path` with its password into a warning, and Nextcloud
   writes the warning into `nextcloud.log` at log level 2. At level 3 it
   does not (first test).
6. **Upgrades.** 33 to 35 is refused (code 5) and leaves
   `maintenance = true`. 33 to 34 and 34 to 35 pass (18 s, 23 s). Only
   `version` changes in `config.php`. A read-only replica with the new
   code asks for an upgrade; `occ upgrade` fails there and leaves
   `maintenance = true`; the `version` of the primary is all it needs
   (first test).
7. **Several configuration files.** A file `config/NAME.config.php` wins
   over `config.php`. A file made before the install gives its
   `instanceid` to the install (first test).
8. **The front.** Coraza refused PROPFIND and PUT (rule 911100). Anubis
   answered the desktop and mobile clients with its challenge page.
   While the rule set read a 100 MiB body, one nginx worker grew to
   3.5 GB, the container ran out of memory, and keel moved the VIP
   (second test).
9. **Failover.** The service came back 35 s after the hard stop of the
   primary. The upload in progress broke, and left no file and no lock
   (second test).
10. **250 ms between the sites.** A PUT of 1 KiB took 2.4 s instead of
    0.15 s on the primary: each commit waits for the replica (second
    test).

## Why (brief section 10)

1. **Why the current approach is not enough.** 0062 has no Redis, and
   the maintainer now asks for it. 0062 lets the standby serve reads, and
   the first test shows that a node with a read-only database cannot
   serve a sync client at all. 0062 does not say how two nodes get the
   same `secret`, `passwordsalt` and `instanceid`, nor what a replica
   does after an upgrade of the primary.
2. **Whether it can be made to work.** It can, with parts that exist:
   Redis of Debian on each node, the role and the `read_only` that keel
   already gives, the shared secrets of the manifest (`shared: true`),
   and the merge of `config/*.config.php` that Nextcloud does. The second
   test ran the prototype hook and gate on a real pair across two sites.
3. **Why this is better.** keel needs no change. No Redis traffic
   crosses the link between the sites, which test 1 measured as the
   cause of 12 s pages. The Redis contents need no replication, because
   a lost session costs no login.

## Decision

### 1. Version and source

Nextcloud is a layer on `lnmp` (0062, confirmed). The layer unpacks the
upstream tarball 35.0.2, pinned by sha256 and checked against the
signature of the key `28806A878AE423A28372792ED75899B9A724937A`, which
the repository carries. An upgrade moves the pin one major at a time,
after the same tests (0062, confirmed; the signature is new).

### 2. Layout

| Path | Owner | What |
| --- | --- | --- |
| `/var/www/nextcloud` | root | the code, no state |
| `/var/www/nextcloud/config` | www-data | `config.php` of the node, `keel-pair.config.php` of the pair |
| `/var/www/nextcloud/custom_apps` | www-data | apps from the app store |
| `/var/lib/nextcloud/data` | www-data, 0750 | the data directory, outside the web root |
| `/var/log/nextcloud/nextcloud.log` | www-data | the log, outside the data directory |

The site logs in to MariaDB as `www-data` over the socket with no
password, as WordPress does. No path of the data directory may go
through a symbolic link: Nextcloud refuses it (second test).

### 3. Redis: one on each node, only the writer uses it (amends 0062 section 3; decided 2026-11-12)

- **The caches.** `memcache.local` is APCu. `memcache.distributed` and
  `memcache.locking` are Redis. The PHP sessions are in Redis
  (`session.save_handler = redis`).
- **Where.** Each node of a pair runs Redis 8 of Debian on its unix
  socket, and Nextcloud on that node uses it. Its data is not durable: no
  RDB file, no AOF. No Redis port is opened, and no Redis password
  crosses the mesh.
- **Which Redis serves.** Only the node that takes writes serves
  (section 4), so only the Redis of the writer is used. This is what the
  maintainer chose on 2026-11-12. It is not the shared Redis at the VIP
  that the first rule named: that variant was not built and not tested.
- **The flush.** When a node becomes the writer, the gate empties its
  Redis before it opens the site. Condition (a): the second test showed
  no stale lock and no broken session after the flush; an upload in
  progress at the failover breaks at the client, leaves no file and no
  lock, and a new upload of the same path passes. A stale cache and a
  stale lock were not seen without the flush either (nginx buffers the
  body, so Nextcloud locks only after the body arrived). The flush stays
  as a precaution.
- **Locks need one Redis.** Condition (b): the file locks are correct
  only while every node that serves uses the same Redis. The gate makes
  sure that only one node serves: a node that is not the writer answers
  503 and never serves with its local Redis. The second test measured
  zero time with two open gates (section 4).
- **Scale-out (0081).** Several application nodes in one site need one
  Redis that all of them reach: a Redis at an address of the mesh (the
  VIP of a Redis pair, or the address of the writer), with the account
  and the password of the pair. They also need shared data storage
  (Syncthing has one writer only), a different `serverid` in each
  `config.php`, and `cron.php` on one node only. This note does not
  build it.
- **The passwords.** Condition (c): two ACL users, each password stored
  as its SHA-256 digest only. `nextcloud` holds the cache and the locks.
  `nextcloud-session` may use the keys `PHPREDIS_SESSION:*` only, with the
  commands of the session handler; it cannot read another key, list keys
  or flush (first test). **The Redis password must not reach
  `nextcloud.log`:** the log level is 3, at which Nextcloud does not
  write the warning that holds `session.save_path` (first test), and the
  password in `session.save_path` is the one of the session user. At
  level 2 the session user alone does not keep its password out of the
  log (third test). The cost of level 3: Nextcloud logs no warning.
  Decided 2026-11-12 (maintainer: yes).

### 4. Only the writer serves (amends 0062 section 5)

A gate on each node opens the route of the site only when all of these
are true:

- the first boot has made the site;
- keel's role file says `role=primary`, or there is no role file (a
  standalone node);
- the database answers `read_only = 0`;
- when the role file names a VIP, that VIP is on a local interface.

The gate runs at each change of an address of the node
(`ip monitor address`), and every 5 s as a backstop. Each signal is
needed (second test): at a failover keel turned `read_only` off 8 s
before it flipped the Syncthing folder; a primary that stopped hard
booted read only with `role=primary` still in its role file; and in the
unplanned failover a node kept `read_only` off and `role=primary` for 4
minutes while no node carried the VIP. With the timer alone the two
gates were open together for about 70 ms at one promote; with the pass
at each address event the time with two open gates was zero in both
directions, and the old holder closed within 0.4 s of losing the VIP.
On every other node the route answers 503, `status.php` too. When no
node carries the VIP, a client gets no answer at the VIP and 503 at each
node. The background jobs run only while the gate is open. When the
database does not answer, the gate closes the site.

0062 section 5 had a warm standby that serves reads and refuses DAV
writes. That is contradicted: the standby cannot serve a sync client.

### 5. The values of the pair

The manifest declares four secrets with `generate: required` and
`shared: true`: `nextcloud_secret`, `nextcloud_passwordsalt`,
`redis_password`, `redis_session_password`. The first boot of each node
writes the same `config/keel-pair.config.php` from them: `instanceid`
(made from the secret), `secret`, `passwordsalt`, the cache settings and
the Redis account. Nextcloud reads that file after `config.php`, and its
values win (first test). Each node keeps its own `config.php`: the
database host, the trusted domains, the data directory, the log, the
apps paths and `version`. A replica writes its whole `config.php` in the
hook and runs no `occ`, because `occ` does not start before the data
directory has arrived (second test).

### 6. Upgrades

- `occ upgrade` runs on the writer only.
- A refused upgrade leaves `maintenance = true`; the upgrade path of
  Keel must handle that state.
- A replica follows: when the newest core migration of its code is a row
  of `oc_migrations` in the replicated database and its `config.php` has
  an older `version`, the gate copies the version of the code into
  `config.php` (first test: that is all a replica needs).
- After a major, the background jobs need 2 to 3 runs (162 s for 34 to
  35 in the first test). No major upgrade is unattended.

### 7. The front of keel-web in the cloud modes (decided 2026-11-12)

- **What the WAF does with a DAV body.** A plugin of the rule set
  (`keel-nextcloud-before.conf`, ids 10111 and 10112) allows the DAV
  methods on the DAV paths only. For a DAV PUT it does not read the body
  (`ctl:requestBodyAccess=Off`) and removes rules 920340 (no
  Content-Type) and 920420 (a type outside the policy, such as
  `application/octet-stream`). The global body limit of Coraza (128 MiB)
  stays. With the plugin, a PUT of 100 MiB grew one nginx worker from 66
  to 87 MB, and four GETs of 100 MiB added nothing (second test); a PUT
  of 100 MiB with `application/octet-stream` passes (third test). The
  maintainer said yes on 2026-11-12.
- **The sync clients pass Anubis.** A file of `keel-front.d` sends the
  paths of the sync clients (`remote.php`, `public.php`, `status.php`, the
  OCS API, Login Flow v2) from the front to the app socket with no
  Anubis. Coraza still reads them, and Nextcloud asks for a login on each.
  A browser keeps the challenge everywhere else (0062 section 6,
  confirmed). The maintainer said yes on 2026-11-12.
- **The scheme behind Anubis: option B.** keel-web passes the scheme
  (Keel-Linux/keel-web#35, keel-web 0.4.4): a conffile
  `/etc/nginx/conf.d/keel-web-scheme.conf` gives `$keel_web_https`, which
  is `on` for a request on the app socket whose front was HTTPS, and
  `$https` everywhere else. The route of Nextcloud sets
  `fastcgi_param HTTPS $keel_web_https if_not_empty;`. A request to port
  443 gets `https://` links, port 80 keeps `http://` links (0079), and a
  forged `X-Forwarded-Proto` of a client changes nothing (third test).
  No `overwriteprotocol`. The maintainer chose B on 2026-11-12.
- **The nginx memory under Coraza: found, a release blocker until
  fixed.** Rule 10013 of keel-overlay-coraza turns body inspection off
  for a Content-Type outside the parsed list, and rule 10012 limits form,
  JSON and XML bodies to 256 KiB. A request with **no** Content-Type
  matches neither, so its body is read by the Core Rule Set up to the
  global limit of 128 MiB. A POST of 10 MiB to `/` with no type and no
  login made one worker grow to 1.29 GB and work for minutes; a PUT of
  100 MiB, to 2.48 GB (third test). Every site of keel-web in the cloud
  modes is exposed, whatever the application. It is a defect of
  keel-overlay-coraza, not of Nextcloud, and more memory is not a fix. The
  text parts of a multipart body had the same gap (third test). The fix
  is keel-overlay-coraza 0.1.5 (Keel-Linux/common#83): rule 10014 does not
  inspect a body with no Content-Type, the treatment that rule 10013 gives
  an unknown type, and rule 10015 refuses more than 256 KiB of text parts
  in a multipart body, files not counted. With 0.1.5 every untyped,
  oddly typed, chunked and multipart case ended in 1.3 s or less, uploads
  of files and DAV PUTs passed, and the biggest worker peaked at 110 MB.
  Before a release of any application in the cloud modes: 0.1.5 in the
  archive, and a test of large DAV uploads and downloads (1 GB, several at
  the same time) with the memory of each worker logged.

### 8. Replicated paths and checks

- `state.replicate`: `/var/lib/nextcloud/data` and
  `/var/www/nextcloud/custom_apps` (0062 section 2, confirmed for the
  data directory; `custom_apps` is new). The log is outside both.
- `status.php` answers 200 with Redis down and with a read-only
  database (first test). It is not a health check: the contract asks for
  the login page and a WebDAV login.

## How it is carried out

1. The prototype `keel-nextcloud`: the layer files,
   the hook, the gate, the timers, the manifest, the rule-set plugin, the
   front file, the dialog of keel-init, 99 bats tests, line coverage 95 to
   100 % per file, a CI workflow, a
   contract draft that `keel-commission --check` accepts.
2. The Forgejo repository `Keel-Linux/keel-nextcloud` (created on
   2026-11-12, the maintainer's yes); the tree for a first build is
   Keel-Linux/keel-nextcloud#1.
3. The image, built on the build host, then the commissioning of 0075 on
   BR1 and BR2 in all three modes.

## Open points

1. The scheme behind Anubis: the route line waits for keel-web 0.4.4
   (Keel-Linux/keel-web#35 and Keel-Linux/keel-nextcloud#2).
2. The dialog of keel-init asks the administrator password
   (Keel-Linux/keel-nextcloud#1); it ran in bats only, not on a machine.
3. The official rule-set plugin of Nextcloud
   (`coreruleset/nextcloud-rule-exclusions-plugin`) against the two rules
   of the prototype.
4. Syncthing did not report a directory that was made after it watched
   the folder; its rescan interval is 3600 s (second test).
5. The excludes inside the data directory (previews, upload chunks):
   none is declared yet.
6. etckeeper commits the pool file of PHP-FPM, which holds the session
   password, into `/etc/.git` at the next apt run.
7. Under memory starvation of the primary, keel moved the VIP twice in
   9 minutes, a node stayed writable for 4 minutes with no VIP on any
   node, and for about 5 s both databases may have taken writes (second
   test). That is for keel.
8. A Nextcloud package moved by apt (the method of 0084) instead of a
   tarball in the layer.
9. The defect of nginx memory under Coraza (section 7): the fix is
   keel-overlay-coraza 0.1.5 (Keel-Linux/common#83); a release waits for
   it in the archive.

## Tests before the release

1. The image of the prototype: the three passes of 0075 on BR1 and BR2.
2. Cloud advanced with the image and the manifest paths: Syncthing on
   the data directory and `custom_apps`, a failover and a return, an app
   installed on the pair, an `occ upgrade` on the pair.
3. The same at 250 ms, with loss, and a cut of the link instead of a
   stopped container.
4. A real desktop client and a mobile client through the front.
5. Large DAV uploads and downloads through the front, with the memory of
   the nginx workers logged (section 7).
6. A data directory of about 10 GB.

## Questions for the maintainer

None open. The fix of keel-overlay-coraza was approved on 2026-11-12;
it waits for its merge and publication.

## Rejected alternatives

- **A replicated Redis that follows the role of the database.** Condition
  (d). `replicaof` on the replica, and a promote of Redis in the same
  step as the database. It keeps the sessions and the cache across a
  failover, and it needs a Redis role in keel's promote and demote. It is
  needed only when more than one node serves (the scale-out of 0081).
  With one serving node the tests showed no loss without it: a lost
  session costs no login, and no lock was left. Rejected by the
  maintainer's answer of 2026-11-12.
- **A shared Redis at the VIP for every node.** Not tested. With one
  serving node it adds a Redis port and a password on the mesh, and a
  bind to an address that moves, for no gain.
- **The warm standby of 0062.** A node with a read-only database cannot
  serve a sync client (first test).

## What this amends

- **0062 section 3**: Redis replaces the database for the locks and
  becomes the distributed cache and the session store, as the maintainer
  asked. APCu stays the local cache.
- **0062 section 5**: the standby serves nothing; only the writer serves.
- **0062 section 7**: the replica writes its `config.php` and runs no
  `occ`; the values of the pair come from shared secrets.
- **0068 section 5**: Nextcloud is the first application with Redis on a
  pair. Its Redis is not replicated.
- 0062 sections 1, 2, 4 and 6 stand, with the additions above.
