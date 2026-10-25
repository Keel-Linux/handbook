# 0067: SimpleX SMP and XFTP servers on Keel Core, with a PostgreSQL pair

Date: 2026-10-24
Status: **proposed**, for the maintainer. Nothing is built. The facts below
come from the upstream source and release of 2026-10-24. Only `init` and
`ldd` of the upstream binaries ran, on a scratch directory of a trixie
machine. No server started, so no platform evidence exists yet.

## What was asked

The coordinator asked for a decision note on the self-hosted SimpleX Chat
servers: the SMP server (message queues) and the XFTP server (file
chunks), from `simplex-chat/simplexmq`. The note covers the upstream,
the base layer, the pair across sites, the ports and the open points.

## Why (brief section 10)

1. **Why the current approach is not enough.** Keel has no private chat
   relay. A SimpleX client uses the servers that its app lists, and the
   default list belongs to a third party. A relay of our own keeps the
   queues and the file chunks on our hardware.
2. **Whether it can be made to work.** It can. Upstream publishes the
   release binaries, and they start on trixie (`ldd` resolves every
   library). Since 6.5.0 both servers store their state in PostgreSQL,
   which the 0054 pair already replicates.
3. **Why this is better.** A relay with its own database needs no new
   replication method. The address of a server holds the fingerprint of
   its CA certificate and not of its host, so a standby that holds the
   same certificates answers at the same address after a failover.

## Decision

### 1. Upstream

| Item | Value | Source |
| --- | --- | --- |
| Version | 7.0.1.0 (tag `v7.0.1`, 2026-07-31) | the `stable` branch head equals this tag |
| Newer | 7.1.0-beta.4 | beta, not used |
| Licence | AGPL-3.0-only | `simplexmq.cabal`, file `LICENSE` of the release |
| Debian | no package | sources.debian.org finds no `simplexmq` |
| TurnKey | no appliance | no repository in `turnkeylinux-apps` |
| Keel-Linux | no repository | org listing on `git.pop.coop`, 2026-10-24 |

Upstream marks every release as a pre-release on GitHub, also 7.0.1. We
follow the `stable` branch, not the GitHub flag.

**Packaging.** Upstream ships ELF binaries for Ubuntu 22.04 and 24.04, and
a script for Ubuntu only. It ships no `.deb`. The binaries link to
`libcrypto.so.3`, `libssl.so.3`, `libgmp`, `libzstd`, `libz` and, in the
PostgreSQL build, `libpq.so.5`. Trixie has all of them.

Keel builds one `.deb` that holds the two PostgreSQL builds,
`smp-server-postgres` and `xftp-server-postgres` of 7.0.1, taken from the
release. The build pins their sha256 values and refuses any other file.
The memory-only builds are not shipped. A build from source is not
possible in the first release: the Haskell project needs a pinned GHC and
git dependencies, and Debian has no package for it. Upstream states that
the builds are reproducible. A reproduction is a task for a later step.

**AGPL.** Keel does not change the code, so section 13 asks only that a
user can find the source. The `source_code` key in `[INFORMATION]` of
each server holds the URL of the tag. The `.deb` carries the licence file.

### 2. Base: Core, not Web, not LNMP, not LNPP

- **Base `core`.** The protocols are binary protocols on TLS, not HTTP.
  They have no PHP, no web root and no use for Coraza or Anubis. A WAF in
  front would break them.
- **No Keel Web.** Nginx would own 443, which the XFTP server needs. If a
  Web layer joins the machine later, a `tls-passthrough` site (0042) can
  share 443 by SNI, because the TLS stays intact. This is not in scope.
- **PostgreSQL is the only engine.** The manifest declares the service
  `database` with engine `postgresql`, as `keel-odoo` does. It is
  `embedded` in simple and cloud simple, and `discovered` in cloud
  advanced (0054, 0041).
- **MariaDB does not fit.** Upstream supports PostgreSQL only, so the
  LNMP stack gives nothing here.

### 3. Storage

Upstream has three stores for queues and messages. Only one fits.

| Store | Setting | Why not |
| --- | --- | --- |
| Memory with append-only log | `store_queues = memory`, `store_messages = memory` | The server saves undelivered messages only at a stop with SIGINT. A crash loses them. A file log cannot be replicated while it is open (0032, 0050). |
| Journal files | `store_messages = journal` | Upstream announced its deprecation in 6.5.0 (#1653). |
| PostgreSQL | `store_queues = database`, `store_messages = database` | **Chosen.** |

SMP uses the database `smp_server_store`, schema `smp_server`. XFTP sets
`store_files = database` and uses the database `xftp_server_store`. The
XFTP chunks stay as files, in the directory of the `[FILES]` section.
Both servers use one PostgreSQL service and one role each. The connection
string, with its password, is in the INI file that only the service user
reads.

### 4. The pair across sites

**Native replication.** None. SimpleX has no server-to-server
replication. Upstream gets redundancy from the client: a client lists
several servers, and each server has its own identity. There are two
ways to use this, and we pick the first.

1. **One identity, a pair (chosen).** The standby gets the same
   certificates, and PostgreSQL carries the queues. After a failover the
   same address works. No queue is lost, because 0054 confirms a commit
   only after the standby has it.
2. **Independent servers, as in 0063.** One server per site, three
   identities, no pair. The clients spread over them. A lost server loses
   its queues. This stays possible with the same image: an operator runs
   a second instance in `simple` mode.

**Identity.** The address is `smp://<fingerprint>@<host>`. The
fingerprint is the hash of `ca.crt`. Clients check the CA and the server
certificate against it. The standby must hold the same `ca.crt`,
`server.crt` and `server.key`. These files are under `/etc`, which
`state.replicate` refuses. They are `shared` secrets (0028): the primary
generates them, and the standby receives them with the rest. Each server
has its own CA.

**Failover.** The VIP moves (0049). The clients keep the host name. Their
TLS connections drop, then each app reconnects and subscribes again to
all its queues. With many queues, the first minutes after a failover are
busy. The test must measure this.

**Files.** The exact `state.replicate` list:

```yaml
state:
  replicate:
    - /var/lib/keel-simplex/xftp-files
```

SMP has no durable file: its state is in PostgreSQL, and the statistics
and the information page are rebuilt. The XFTP chunks expire after 48
hours. A chunk can be in the database of the standby before its file
arrives (Syncthing is asynchronous). After a failover a download of that
chunk fails until the file arrives, and the sender sends again. We
accept this. The option `xftp_quota` defaults to 20 GiB, so a full
resync across the link stays bounded.

**Option `xftp`, default `false`.** The XFTP server is off until the
operator turns it on. This is the least-power choice: the replicated file
volume is the one open risk of this note.

**What runs only on the primary.** Both daemons. There are no workers,
no cron and no mail. On the standby the units are stopped, and keel
starts them at a promotion, after the PostgreSQL promotion. A pair
member that serves a client before it holds the role would write into a
read-only database.

**Gap in manifest version 1.** `workers[]` never write to disk and are
not public. `web` is for HTTP. A listening daemon of an application that
runs on the active node only has no field. The keel step proposes one
key for it. A new key raises `manifest_version` (rule 10 of 0041), so
this is a decision of the maintainer, and it is open question 2.

**Cost of the pair.** 0054 has no timeout on the synchronous commit.
Every write of the SMP server waits one round trip, about 250 ms. A
single message exchange takes several writes. A small relay is fine,
because commits of many clients share one round trip. A big relay is
not. The test uses the netem profiles of 0058 and measures messages per
second and the delay of one message.

### 5. Ports, TLS, health

| Service | Port | Exposure | Notes |
| --- | --- | --- | --- |
| SMP | 5223/tcp | public | The ini default is `5223,443`. We set `5223` only, because XFTP owns 443. |
| XFTP | 443/tcp | public | Upstream default. Only if `xftp` is `true`. |
| Control ports | 5224 and 5226 | closed | Off by default. Keep them off. |
| PostgreSQL | 5432/tcp | mesh | Only in cloud advanced, 0054. |

- **TLS is the protocol's own.** Each server has an own CA and a server
  certificate from `init`. The client pins the CA fingerprint. Let's
  Encrypt does not apply, and Keel Web is not there to renew it.
- **The `[WEB]` page and `web.crt` stay off** in the first release.
- **Firewall and Monit** come from the manifest. The firewall opens the
  public ports. The standby has no listener, because the unit is stopped.
- **Health check.** Monit checks each process. A keel script opens a TLS
  connection to the port, reads the CA certificate and compares its hash
  with the `fingerprint` file. A mismatch is a failure. The same check
  proves the identity after a failover.
- **Address.** The first boot prints the server address to the console
  and writes it to the instance state. The `create_password` of upstream
  is a secret of the instance (`generate: required`), and it is part of
  the address that the operator hands out.

## How it is carried out

1. `Keel-Linux/simplexmq-bin`: the `.deb` with the pinned binaries, the
   licence and the source URL.
2. `Keel-Linux/keel-simplex`: the layer on Core, the manifest, the units,
   the first boot (`init` in a scratch directory, the shared secrets, the
   password), the health script and the boot test.
3. `Keel-Linux/keel`: the manifest key for an active-node daemon, if the
   maintainer agrees.
4. Tests and evidence on the real platform, per 0053: a pair across BR1
   and BR2 with the netem profile, a failover with the same fingerprint,
   and the XFTP resync. No application is released before Syncthing and
   the database pair pass across sites (maintainer rule of 2026-10-20).

## Risks

- **Pre-release flag.** Upstream flags all releases as pre-release. The
  docs describe `_sha256sums.asc`, but the 7.0.1 release has no such
  asset. We pin the sha256 values of the release text, and we reproduce
  the build later.
- **Ubuntu binaries on Debian.** `ldd` is clean. A run on a real
  container is still to do.
- **Synchronous commit** at 250 ms, see section 4.
- **The reconnect wave** after a failover, see section 4.
- **A public relay can be abused.** The `create_password` closes it.

## Open questions for the maintainer

1. Does the CA private key stay off the server? Upstream advises this.
   If yes, someone keeps `ca.key` offline, and only that person can
   rotate the server certificate. Upstream advises a rotation every 3
   months. If no, the key stays on the primary and the standby.
2. May the keel step add the manifest key for an active-node daemon?
3. Is the relay private (`create_password`, the default here) or open?
4. Which names? For example `smp.pop.coop` and `xftp.pop.coop`, pointing
   to the VIP of the pair.
