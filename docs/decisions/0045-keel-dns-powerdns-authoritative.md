# 0045: Keel DNS, PowerDNS authoritative servers with native zone replication

Date: 2026-10-24
Status: **proposed, for the maintainer.** This note replaces the 0045
part of handbook#38. The maintainer decided the premise there on
2026-10-02: Keel DNS is an appliance, it runs PowerDNS Authoritative,
health checked answers use LUA records, and at least two servers run in
different sites. Those points stand. The backend, the pair, DNSSEC, the
API and the recursor are decided here again against 0049, 0050, 0054,
0059 and 0063. Nothing here is implemented.

## What was asked

The maintainer asked for a Keel DNS appliance on PowerDNS. It must answer for the operator's zones and answer only with addresses that are alive. It must also take updates from nodes behind NAT whose IPv6 prefix changes (the open item of 0024). The coordinator then asked four questions: the
database backend, the DNSSEC keys, the API and web interface, and the
recursor. A fifth question comes from the premise of 0050. Which replication does the appliance use across sites: the Keel pair, or the replication of DNS itself?

## Why (brief section 10)

1. **Why the current approach is not enough.** Keel has no name server.
   0020 and 0044 make DNS with a health check the first way for a public
   client to reach a live node. The mesh does not help, because a public resolver is outside it. One site with the only copy of a zone takes every name down with it.
2. **Whether it can be made to work.** It can, with parts that exist.
   PowerDNS Authoritative is in Debian 13. It has LUA records with
   health checks, RFC 2136 updates with TSIG, catalog zones and zone
   transfer. The zone transfer is the replication that DNS has used for
   decades, and every secondary server in the world speaks it.
3. **Why this is better.** Each server answers from a local copy and
   needs no other Keel service in its query path. A new site is a new
   secondary, not a new database member. An outside secondary that the
   operator already runs works with the same mechanism.

## Decision

### 1. Upstream

| Item | Value (checked 2026-10-24) |
| --- | --- |
| Package | `pdns-server` 4.9.17-0+deb13u1 in trixie, from the Debian package `pdns` |
| Upstream | PowerDNS Authoritative 4.9.x; the newest series is 5.1.5, and 5.2.0 is in alpha |
| Licence | GPL-2.0 (PowerDNS Authoritative). PowerDNS-Admin is MIT |
| Debian sid and forky | 5.1.5-1 |
| TurnKey prior art | none for the authoritative server |

**Security gate.** The Debian security tracker lists CVE-2026-73206 as
vulnerable in trixie. PowerDNS advisory 2026-13 of 2026-10-21 describes
it: a crafted DNS packet causes a denial of service while the server
decompresses names. It affects Authoritative up to 4.9.17 and is fixed
in 4.9.18, 5.0.8 and 5.1.5. A public port 53 makes this a gate:

- Keel DNS does not release with 4.9.17.
- If Debian ships 4.9.18 or newer before the release, the appliance uses
  the Debian package.
- If Debian does not, the Keel archive carries a rebuild of the upstream 4.9.18 source for trixie, as it does for Syncthing (0050).
- The series stays 4.9, so the configuration does not change.

The 5.x series is not chosen. It renames tools (`pdnsutil zone secure`)
and adds settings such as `dnsupdate-require-tsig` (since 5.0.0), and the
LMDB backend gains RFC 2136 only in 5.0.0. The note uses the 4.9
documentation at tag `auth-4.9.12` for every feature below.

**TurnKey prior art.** The organisation `turnkeylinux-apps` has no
`powerdns` or `pdns` repository. The Keel-Linux organisation on
`git.pop.coop` has none either, so there is nothing to fork with its
history. Two items exist and neither is the authoritative server:

- `turnkeylinux/tracker` issue 2089 is the PowerDNS **Recursor** proposal
  of the maintainer. It is open and assigned to a TurnKey maintainer.
- `turnkeylinux/pdns-recursor` on `git.pop.coop` is its source (version
  18.0-6, Debian 12, Recursor 4.8, an nginx dashboard). It is not forked
  into Keel-Linux (section 9).

### 2. Base: Keel Core, no web layer

**Keel DNS is an appliance on `core`.** It is not on `web`, `lnmp` or
`lnpp`. DNS is not HTTP, so nginx, Coraza and Anubis have no work, and
the PHP of `lnmp` and `lnpp` has none. The set has no `/keel-check/`
page and no nginx route. Health comes from Monit and from keel (section
8).

The appliance adds one overlay, `keel-overlay-pdns` (0036): the
`pdns.service` unit, `pdns.conf`, the first boot hook, the role hook
and the checks. The name of the appliance is `dns` and its repository is
`Keel-Linux/keel-dns`.

### 3. The backend and the replication across sites

The brief asks for a choice, with the replication of DNS compared with
the pair. The choices are four:

| | `gsqlite3` and zone transfer | `gmysql` on LNMP | `gpgsql` on LNPP | `lmdb` |
| --- | --- | --- | --- | --- |
| Who replicates | DNS: NOTIFY and AXFR | MariaDB pair (0031) | PostgreSQL pair (0054) | DNS: NOTIFY and AXFR |
| Servers in the set | 2 or more, one per site | 2 (a pair), 3 with a witness | 2 (a pair) | 2 or more |
| Answers need another Keel part | no | the database, local on each node | the database, local on each node | no |
| RFC 2136 in 4.9 | yes | yes | yes | **no** (since 5.0.0) |
| Extra parts in the image | none | nginx, PHP | nginx, PHP | none |
| An outside secondary works | yes | yes, by AXFR | yes, by AXFR | yes |

**Keel DNS uses `gsqlite3`, one local database on each server, and
replicates zones with NOTIFY and AXFR.** Five reasons:

1. **Redundancy is the list of NS records, not a VIP.** A pair has one
   writer and one address that moves (0049). A resolver needs several
   addresses, in several sites, all with an answer. Every server answers; one server accepts changes.
2. **The query path depends on nothing else.** Other appliances depend on DNS. A database pair would put semi-synchronous replication (0031), the VIP and etcd under it. The 0045 of handbook#38 refused this circle, and this note keeps the refusal.
3. **The set has three sites.** BR1, BR2 and BR3 are three NS records.
   The database pairs have two members. A third DNS server is a third
   secondary, with no change to the other two.
4. **The image stays small.** `lnmp` and `lnpp` carry nginx and PHP that
   a name server never uses. A MariaDB engine with no web layer would
   need its own overlay for one table set.
5. **The outside secondary needs AXFR in any case.** The operator's
   second server, which 0045 of handbook#38 already makes the operator's
   own, pulls zones by AXFR. The pair would add a second mechanism.

**LMDB is rejected on a fact.** The 4.9 documentation of the LMDB
backend lists no DNS update. The 5.x documentation says "since version 5.0.0". 0024's open item needs RFC 2136 on the series of trixie.

**What a database pair would give, and what replaces it.** A pair would
carry the TSIG keys and, later, the DNSSEC keys with the rows. With zone
transfer they do not travel. Section 5 states how Keel carries the TSIG
keys. Section 6 states why DNSSEC is not in version 1.

### 4. The set across sites

**Roles.** One server is the **primary**: the node that holds the VIP of
0049. Every other server is a **secondary**. The role is the role file
of 0049 and moves with `keel database promote` or its DNS equivalent,
by hand in version 1.

| | Primary | Secondary |
| --- | --- | --- |
| Zones in the database | primary zones (kind `Master` in the 4.9 tools) | secondary zones (kind `Slave`), or members of the catalog |
| Public port 53, answers, LUA checks | yes | yes |
| Accepts RFC 2136, API writes, spec renderer | yes | no |
| Pulls zones | no | yes, from the VIP |
| `forward-dnsupdate` | not used | `no`, set in the file |

**The VIP is used on the mesh only.** The secondaries pull from it. The
nodes send RFC 2136 updates to it, and the API is reached on it. It
never appears in an NS record, a glue record or a public answer. This
changes the text of 0029 in handbook#38: Keel DNS is not behind the
VIP for the public, and it uses the VIP for the control path. After a
promote, the secondaries do not change their configuration: the VIP
moves.

**Catalog zones.** The primary produces a catalog zone. A secondary
consumes it, so a new zone appears on every secondary without a setting
on that node. TSIG protects the catalog zone and every zone transfer. The 4.9 documentation says to use TSIG on every AXFR of a zone with LUA records. Catalog zones exist in the
4.9 series since 4.7.0. If a catalog consumer cannot become a producer in the gate, keel renders the zone list from the spec on every node.

**Replicated paths.** The appliance declares **no `state.replicate`**.
The only run-time state is `/var/lib/powerdns`, with the SQLite
database. The overlay declares it as `data` with `replication: native`,
because the engine of DNS replicates it. It is never replicated by file
(0032), and the Syncthing overlay is `disabled` in every mode. A copy of an open SQLite file can be corrupt, so a file copy is wrong in any case (0050 and 0063 say the same of ntfy).

**What runs only on the primary:**

- the renderer that writes the zones and the health checked names of the spec into the database, as a oneshot unit with a role condition (the Nextcloud cron timer of 0062 does the same);
- the RFC 2136 updates and the API writes;
- the catalog producer;
- in Phase 5, the process that writes the etcd registry into the zones.

**How it stops on a secondary.** The unit has the role condition, so it
does not start. The zones are secondary zones, and PowerDNS refuses a
record change on them. `forward-dnsupdate=no` makes a secondary refuse an update, not send it on. The LUA health checks run on every server, on purpose. Each server checks from where it is, so a secondary serves health checked answers without the primary.

**Promotion is manual in version 1.** The role hook of the 0050
amendment (`/usr/lib/keel/roles.d/`) sets the zone kinds and the
catalog. There is no automatic failover of the write side. The read side needs none: every server keeps its copy and keeps answering while the primary is down.

**SOA timers for 250 ms and 2% loss.** NOTIFY is one UDP packet and the
network can lose it. The refresh timer is the second path, so it is
short. The defaults of the screen:

| Field | Value |
| --- | --- |
| refresh | 300 s |
| retry | 60 s |
| expire | 1209600 s (14 days), so a secondary survives a long loss of the primary's site |
| negative TTL | 300 s |

A zone transfer runs on TCP, so the 5 retransmissions of the amendment of 0050 apply. A transfer that stalls ends and starts again after the retry time. The gate measures a transfer under the five netem profiles
of 0050.

**An outside secondary.** The operator may add any secondary. It pulls
by AXFR on 53/tcp from the primary or from a Keel secondary. Each zone
sets `TSIG-ALLOW-AXFR` to a key of that secondary, and `allow-axfr-ips`
stays at its loopback default, so no unsigned transfer works from the
Internet.

### 5. Updates from nodes, and the TSIG keys

The decision of handbook#38 stands. A node behind NAT updates its own
names by RFC 2136 with TSIG, sent to the VIP over the mesh. In cloud
advanced the etcd registry feeds the zones from Phase 5.

- On 4.9, no setting makes TSIG mandatory (`dnsupdate-require-tsig` is from 5.0.0). Each zone sets `ALLOW-DNSUPDATE-FROM` to the mesh prefix and `TSIG-ALLOW-DNSUPDATE` to the key name.
- `lua-dnsupdate-policy-script` limits each key to the names of its own node. The script turns the other rules off, so it checks the key.
- Each TSIG key is a secret of the instance (`generate: required`). The
  secondaries need the transfer keys, so these are `shared: true` and
  travel in the primary-to-replica channel of 0028. The node keys stay on
  the primary and on the node.
- A key is never in the image, in the spec or in the handbook (0041).

### 6. DNSSEC

**Version 1 signs no zone.** Two facts of the 4.9 documentation decide
this:

- LUA records and pre-signed zones do not combine. The signing key must
  be on every server that builds an answer from a LUA record.
- A zone transfer carries signed data, not the private keys. A secondary
  that signs for itself needs the keys copied to it.

So a signed zone with health checked names needs the private keys on every server. The zone transfer does not carry them. This is the one cost of the native replication. It needs a key-copy channel, a rule for the key roll and a rule for the backup. These are a note of their own, as handbook#38 already recommended.

That note must choose between three ways:

- pre-signed static zones, with the keys on the primary only;
- a delegated unsigned subzone for the health checked names;
- the keys copied to every server by keel.

The keys are never on the build host (0055). Their custody is never in the handbook. Version 1 closes none of the three ways. The database supports DNSSEC (`gsqlite3-dnssec`), and the answers do not change when a zone is signed later.

### 7. LUA records and the health checks

The decision of handbook#38 stands. The settings are `enable-lua-records` on and `lua-health-checks-interval` at its default of 5 s. Health checked names have a TTL of 60 s, with 30 s as the floor. When every address in a
list is down, PowerDNS answers with an address from the list: the
`backupSelector` default is `random`. A visitor then sees the
maintenance page of 0042 or a connection error, not a name that does not
exist. Each server checks from its own site, so two servers can disagree
for a check interval.

### 8. Ports, mesh, TLS and health

| Port | Protocol | Exposure | Use |
| --- | --- | --- | --- |
| 53 | udp, tcp | `public` | queries; AXFR to a TSIG holder |
| 53 | udp, tcp | `mesh` | NOTIFY, AXFR and RFC 2136 on the mesh and the VIP |
| 8081 | tcp | `loopback` | the PowerDNS API and its web server |

- **There is no TLS and no nginx route.** DNS over TLS is not in version
  1. The API is on the loopback and has no certificate.
- **The API stays on the loopback.** CVE-2026-33257, CVE-2026-33260 and
  CVE-2026-42005 are web requests that make the PowerDNS web server
  allocate memory without a limit. Keel does not expose it. The renderer
  and the feed run on the primary and use the loopback.
- **Monit checks:** `protocol dns` against the SOA of each served zone, on every server (0040).
- **Serial check:** on the primary, keel compares the serial of each secondary with its own, with a query over the mesh. A secondary that is behind by more than 2 refresh times raises an alert.
- **CrowdSec** (0029) runs on the host. PowerDNS never recurses, so Keel
  DNS is not an open resolver. UDP answers can still be used for
  reflection, and the answers stay small. `dnsdist` is a later overlay if
  the production shows abuse. Version 1 has no front.
- **The public path of 53** is open to the maintainer (question 1).

### 9. The API, the web interface and the recursor

**No web interface in version 1.** The Keel console writes zones and
health checked names into the spec, and keel renders them. The API is on
the loopback. A person who needs a record that the spec does not carry
uses `pdnsutil` on the primary or an RFC 2136 update with a key.

PowerDNS-Admin (MIT, release v2026.08.1 of 2026-08-30) is the usual interface. It is not in Debian, so it comes from upstream with pip. It is a Flask application with its own database and its own user accounts. Its edits would compete with the spec as the source of the zones. It can come later as its own appliance on `lnpp`, and it can use the API through the mesh.

**The recursor is out of scope.** An authoritative server and a recursor
have different clients, different exposure and different failures. A host that does both can answer recursion for the Internet after one mistake. The recursor of the maintainer (the TurnKey proposal) is a Debian 12 appliance with a web dashboard. Trixie carries Recursor 5.2.13, which also has CVE-2026-73206 open. If Keel needs a resolver, it is a
separate appliance with its own note. No fork is made now.

## How it is carried out

1. `Keel-Linux/common`: `keel-overlay-pdns`, with its manifest: the
   unit, the ports of section 8, the data path with `replication:
   native`, the role hook and the Monit checks.
2. `Keel-Linux/keel-dns`: the appliance on `core`, simple mode first.
   The vip and etcd overlays follow the other pairs in the cloud modes.
   The Syncthing overlay is `disabled` in all modes.
3. `Keel-Linux/keel`: the renderer (spec to zones), the role hook for
   zone kinds, and the secondary serial check.
4. `Keel-Linux/apt`: `conf/image-ci` watches `keel-dns` (0061).
5. The release test of 0053: two containers on BR1 and one on BR2, as
   primary and two secondaries, at the five netem profiles of 0050.

**Done when** all of these hold at each netem profile:

- All three servers serve a test zone with a health checked name.
- A change on the primary reaches both secondaries within one refresh time.
- If a Keel Web node stops, its address leaves every answer within one check interval plus the TTL.
- After a promote by hand, the new primary accepts an update at the VIP and the old primary refuses one.
- An `nsupdate` with a node key changes the name of that node and not the name of another node.
- An AXFR request without TSIG from a public address is refused.

## Risks

- **CVE-2026-73206** is open in trixie today. The release waits for 4.9.18
  (section 1).
- **A catalog consumer that becomes a producer** is the least tested part
  of the promote. The gate decides between the catalog and the rendered
  zone list.
- **The TSIG keys, and later the DNSSEC keys, are not in the zone transfer.** The backup of the SQLite database holds them. The backup is encrypted (0037) and runs on a secondary.
- **DNS is the first service whose failure takes other services down.** A
  zone that has only one site's NS records is lost with that site. The
  screen warns in a simple installation.
- **The documentation of 4.9 and 5.x differs** (for example in the
  default of `forward-dnsupdate`). Keel sets every setting it relies on
  in the file.

## Open points for the maintainer

1. **How does public 53 reach each node?** BR1 uses a pool that proxies
   TLS, BR2 has a port forward on IPv4, BR3 has IPv6. A name server needs
   a public address per site that carries UDP and TCP on 53 with no
   proxy. This is a question for the edge of Rudder (pop/rudder#867).
2. **Is the CVE gate right?** The release waits for Debian 4.9.18 or uses
   the rebuild of the upstream 4.9.18 source.
3. **Is it right that version 1 has no DNSSEC?** The cost is a signed
   zone that needs a key-copy rule. Recommendation: yes, and a note of
   its own.
4. **The names of the servers.** Recommendation: `ns1.pop.coop`,
   `ns2.pop.coop` and `ns3.pop.coop`, one per site, with glue at the
   parent.

## What this amends

This note replaces the 0045 part of handbook#38. Where that note and this
one differ, this one decides. The 0044 part of handbook#38 is not changed.

- **0020, "Decided" and "Where each piece lives":** DNS with a health
  check is an appliance, not a Keel Cloud piece. This is as in
  handbook#38.
- **0024, "Review notes":** the open item of the DNS successor for nodes
  behind NAT is decided. It is Keel DNS, with RFC 2136 and TSIG at the VIP, and the etcd feed in Phase 5.
- **0028:** primary and replica read as the primary and the secondaries
  of DNS in the cloud modes.
- **0029:** the public answers of Keel DNS are never behind the VIP. The
  VIP serves the control path on the mesh only.
- **0041, decision 6:** unchanged. It applies for the first time to a public port that is not Keel Web's: 53, udp and tcp.
