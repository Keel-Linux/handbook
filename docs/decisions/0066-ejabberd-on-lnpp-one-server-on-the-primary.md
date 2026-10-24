# 0066: ejabberd on the LNPP stack, one server on the primary, PostgreSQL for all state

Date: 2026-10-24
Status: **proposed for the maintainer, 2026-10-24.** The maintainer
ordered the new appliances (Ghost, PowerDNS, Mastodon, ejabberd,
SimpleX) on 2026-10-24. This note picks the design for ejabberd and
follows the standing rules: 0031, 0049, 0050, 0054 and 0059.

## What was asked

An XMPP server appliance for Keel. The old TurnKey recipe is Apache,
Mnesia and a dead web client. The questions: which version, which
database, how the server lives on a pair across sites at 250 ms, which
files are run-time state, which ports are open, and what the scope of
STUN and TURN is.

## Why (brief section 10)

1. **Why the current approach is not enough.** `keel-ejabberd` is a
   fork of `turnkeylinux-apps/ejabberd` (archived, last push
   2015-09-14). It uses the old `ejabberd.cfg` format, Apache,
   Mnesia on one node and the Speeqe web client. Upstream dropped that
   configuration format long ago. The recipe has no pair, no
   replication and no TLS design for 2026.
2. **Whether it can be made to work.** It can, with parts that exist.
   ejabberd stores all durable data in PostgreSQL if `default_db: sql`
   is set. The upload directory is a plain directory. The pair of 0054
   and the file replication of 0050 cover both.
3. **Why this is better.** The server holds no state of its own except
   the upload directory. A failover is a promote, a folder flip and a
   start of one service. No Erlang cluster crosses a slow link.

## Decision

### 1. Upstream, version and licence

| Item | Value | Source |
| --- | --- | --- |
| Debian trixie | `ejabberd` 24.12-3+deb13u2 | sources.debian.org/src/ejabberd |
| trixie-backports | 26.07-1~bpo13+1 | same |
| Upstream latest | 26.09, released 2026-09-30 | github.com/processone/ejabberd/releases |
| Licence | GPL-2.0-or-later with OpenSSL exception; pubsub files EPL-1.1 | `debian/copyright` |

- **Ship the trixie package, 24.12-3+deb13u2.** The Debian security
  team maintains it. No Keel package is needed. This follows 0063. The
  package is a source of the layer, pinned by version in the build.
- **Backports 26.07 is the escape.** If a security fix is not in
  trixie, the layer moves to backports in its own pull request.
- **The option names differ.** 24.12 uses `new_sql_schema`. Upstream
  renamed it to `sql_schema_multihost` in 25.10. A move to 26.x changes
  one line of the configuration.
- **Install the PostgreSQL driver by name.** `erlang-p1-pgsql` is only
  a `Suggests` of the `ejabberd` package in trixie. The layer lists it.

**TurnKey prior art.** `turnkeylinux-apps/ejabberd` is archived. It
configures a node `ejabberd@localhost`, a legacy SSL port, in-band
registration and an admin console on port 12322. Keel keeps three
ideas: the fixed node name, the first-boot hook for the domain and the
admin password, and the confconsole entry. Keel drops Speeqe, Apache
and open in-band registration. The repository
`Keel-Linux/keel-ejabberd` already exists on git.pop.coop with the full
history. No new fork is needed.

### 2. Base and database

**The base is `lnpp` (Core, Web, `lnpp`), and the database is
PostgreSQL.**

- ejabberd needs no PHP and no Python. LNPP is chosen for the
  PostgreSQL pair of 0054 and for Keel Web, which 0059 already names for
  ejabberd (step 7). The unused Python is the cost. Slimming the base
  is a later step.
- **PostgreSQL, not MariaDB.** ejabberd supports both with its own
  Erlang drivers, and upstream CI runs its database tests on both. The
  upstream MySQL tutorial states the requirement as MySQL 5.6 and
  newer, and names no MariaDB version. Upstream names MySQL more often
  in its changelog fixes (26 lines against 16 for PostgreSQL in the
  current changelog), mostly schema updates. This is a weak signal. It
  agrees with the other reasons: the pair of 0054 is the newer, and
  PostgreSQL gives a hot standby with a clear timeline.
- **The schema is the multihost one.** Set `new_sql_schema: true`. The
  singlehost schema needs one database per domain. Keel serves many
  tenant domains (0063 section 4), and the conversion later is manual.
  ejabberd creates and updates the tables itself, because
  `update_sql_schema` is on by default since 24.06. The database role
  owns the database.
- **All durable data goes to SQL.** Set `default_db: sql` and
  `auth_method: [sql]`. Accounts, rosters, message archive, offline
  messages, rooms and pubsub are then rows. Sessions and routes stay in
  Mnesia RAM tables. They are lost when the server stops, and clients
  log in again. The release test checks that Mnesia holds no durable
  table with data.
- **Connection.** `sql_server` is `127.0.0.1`, the embedded primary of
  the node. The secret `db_password` is `shared` as for Odoo.

### 3. The pair: one server, on the primary only

**ejabberd runs only on the node that holds the VIP and the writable
database. The standby runs the database as a hot standby and nothing
else of ejabberd.**

- **Why a cold standby.** ejabberd writes at each login and each
  message, and `update_sql_schema` writes when the server starts. A
  fenced standby refuses writes (0049, 0054), so a running ejabberd
  would fail on it. No warm standby is possible, which differs from
  Nextcloud in 0062.
- **How it stops.** The unit `ejabberd.service` has a drop-in with an
  `ExecCondition` that reads the role file of 0049. On a replica the
  unit does not start. keel starts the unit after the promote and stops
  it at the demote. The nginx routes of section 5 answer 503 with a
  Retry-After header on the standby.
- **What else runs on the primary only.** Nothing else. ejabberd has no
  cron and no mail. The upload cleanup is the module
  `mod_http_upload_quota` inside the server, so it stops with it.
- **The first write after a failover** needs the VIP move (target of
  about 5 s, 0059) and one start of the Erlang VM. The release test
  measures the sum. No figure exists yet.
- **Message loss.** The semi-synchronous commit loses no committed row.
  A message that the server had not yet written is lost, as in any
  XMPP failover. Clients that use stream management resume fail and log
  in again. The archive (`mod_mam`) lets them fetch what they missed.

**Native clustering is rejected.** ejabberd clusters with Erlang
distribution and shared Mnesia schemas.

- Upstream says: "Cluster should be set up in a single data center: The
  clustering in ejabberd Community Server relies on low latency
  networking" (docs.ejabberd.im, Clustering).
- Erlang declares a node down after `net_ticktime`, 60 s by default,
  of silence. A link with 250 ms and loss can cause false "node down"
  events, and Mnesia does not merge divergent tables after a partition
  without help.
- Three sites would need an Erlang mesh over the 0058 link profiles.
- No measurement of ejabberd at 250 ms exists in this repository. The
  argument rests on the upstream text and on the Erlang defaults. The
  release test (section 6) provides the evidence required by 0053.

A pair with PostgreSQL has one writer, the same failure model as the
other appliances, and no new protocol across sites.

### 4. Run-time state

The files that the application writes:

- **`/var/lib/ejabberd/upload`**: the files of `mod_http_upload`
  (XEP-0363). Set `docroot` to this path in the configuration.
  Upstream default is `@HOME@/upload`, and the Debian home of the
  `ejabberd` user is `/var/lib/ejabberd`. The server keeps no row for an
  upload. The path in the URL is the only index.

```yaml
state:
  replicate: [/var/lib/ejabberd/upload]
```

- **Not replicated:** the rest of `/var/lib/ejabberd`. It holds the
  Mnesia files and `.erlang.cookie`. Mnesia is open while the server
  runs, so a file copy can be corrupt (0032, 0050). The cookie is per
  node. The replicate path is a subdirectory, so rule 23 of the manifest
  is met.
- **No `state.exclude`.** The upload directory holds only uploads.
- **Upload window.** A client gets "201 Created" when the file is on the
  primary. If the primary fails before Syncthing copies the file, the new
  primary answers 404 for that URL. The message still arrives, with a
  dead link. The window is a few seconds on a good link. This is
  accepted for v1, and the release test measures it.
- **Quota.** `mod_http_upload_quota` with `max_days: 30` and a size
  limit per user keeps the directory small. The values are inputs of
  the instance.

### 5. Ports, mesh exposure, nginx route, TLS and health

| Port | Use | Exposure | Notes |
| --- | --- | --- | --- |
| 5222/tcp | client to server, STARTTLS | public | the VIP |
| 5269/tcp | server to server, STARTTLS | public | needs the SRV record |
| 5443/tcp | HTTP: upload, BOSH, WebSocket | loopback | nginx proxies to it |
| 4369/tcp and the Erlang port | Erlang distribution | loopback | `ERL_EPMD_ADDRESS=127.0.0.1`, one fixed `ERL_DIST_PORT` |
| 5432/tcp | PostgreSQL | mesh | from the stack, 0059 |

- **No port of ejabberd is opened on the mesh.** The server has one
  node. Erlang distribution never leaves the machine.
- **The nginx route.** Keel Web terminates HTTPS on 443 for the web name
  of the domain, for example `xmpp.<domain>`. It proxies `/upload`,
  `/bosh` and `/ws` to 5443 on loopback. The route has no proxy
  buffering for uploads, `client_max_body_size` equal to the upload
  limit of ejabberd, and long timeouts for WebSocket. Anubis does not
  challenge these paths, because the clients are apps (as in 0063).
  Coraza does not inspect the body of `/upload` (as for DAV in 0062).
  The web admin of ejabberd has no route. The administrator uses
  `ejabberdctl`.
- **TLS.** ejabberd reads the certificate that the spec obtains with
  `tls.acme` (0009, 0018) through `certfiles`, and reloads on renewal.
  The certificate must cover the domain and the `xmpp.` name. The
  ACME of ejabberd stays off.
- **DNS.** The records `_xmpp-client._tcp` and `_xmpp-server._tcp`
  point to the public name of the VIP. They are an input of the
  instance.
- **Health checks** (only on the active node):
  1. `tcp` on 5222;
  2. `command`: `ejabberdctl status`;
  3. the boot test opens a stream with
     `openssl s_client -starttls xmpp` and logs in a test account.
- **Registration.** `mod_register` is off by default. The administrator
  creates accounts with `ejabberdctl register`. Open registration is a
  choice for the instance, with limits.

### 6. STUN and TURN

**STUN and TURN are not in v1.**

- Debian `ejabberd` provides `stun-server` and `turn-server`. The
  module `ejabberd_stun` serves both, with `mod_stun_disco` to announce
  them (XEP-0215). Calls behind symmetric NAT need a relay.
- A relay is public UDP traffic with a large port range and real
  bandwidth. On a pair it runs on one node only, and the allocations
  are lost at a failover. An open relay is an abuse risk.
- If a relay is needed, use the built-in `ejabberd_stun` first, with
  `auth_type: user`, before a second package. `coturn` is a separate
  appliance per site, standalone like 0063, never clustered.
  `mod_stun_disco` then announces it.

## How it is carried out

1. `Keel-Linux/keel-ejabberd`: remove Apache, Speeqe and the old
   configuration. Write the layer on `lnpp`, the manifest, the
   `ejabberd.yml`, the route, the inithooks, the boot test and the image
   gate (0061).
2. `Keel-Linux/common`: only if the role drop-in is not yet an overlay.
3. Release test (0053, 0059): 2 containers on BR1 and 1 on BR2, a
   pair across sites with netem. Measure: the login time after a
   promote, the upload window, the archive after a failover, and the
   Mnesia check. Ship the evidence file.
4. No release before Syncthing and the database pair pass on the
   platform (rule of 2026-10-20).

Done when a client keeps its accounts, rooms and archive across a
promote, and an upload made before the promote is served after it.

## Risks and open points

- **Version.** 24.12 is two years old. The security team covers it.
  Moving to 26.x needs one option rename.
- **Edge.** The pop.coop edge must pass raw TCP on 5222 and 5269 to the
  VIP. The edge today serves HTTP. This is open for the maintainer.
- **Upload window** and **login time** have no measurement yet.
- **s2s.** Federation needs a valid certificate and SRV records.
  Without them the server works for local users only.
- **Questions for the maintainer.** (1) Do you accept the trixie package
  24.12 for v1? (2) Do you accept no STUN or TURN in v1? (3) Can the
  edge forward TCP 5222 and 5269 to the VIP?
