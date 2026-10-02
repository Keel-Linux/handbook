# 0045: Keel DNS, PowerDNS authoritative

Date: 2026-10-02
Status: **decided by the maintainer on 2026-10-02** for the points under
"Decision": a new appliance, Keel DNS, built on PowerDNS Authoritative and
its LUA records with health checks, which is the DNS with a health check of
0020 and 0044 and the DNS successor that 0024 left open. The details he did
not decide are under "Open questions", each with a recommendation. Nothing
here is implemented.

## What was asked

0020 and 0044 make DNS with a health check the primary way public clients
reach a live node. 0024 left open the DNS successor for nodes behind NAT
whose IPv6 prefix changes, "likely a PowerDNS overlay" fed from etcd. Both
need the same thing: a name server that Keel ships, that answers for the
operator's zones, and that answers only with addresses that are alive.

## Decision

1. **Keel DNS is an appliance**, built on Keel Core (not on Keel Web), that
   runs **PowerDNS Authoritative** from Debian 13.
2. **It is authoritative for the zones it serves.** This is what sets it
   apart from every other appliance: it is not a client of DNS, it is the
   answer. The operator delegates a zone (or a subzone such as
   `svc.example.org`) to it at the parent, and from then on Keel DNS's
   answers are the truth for those names.
3. **Health checked answers use PowerDNS's built in LUA records**, with
   `ifportup` (a TCP connect to a port) and `ifurlup` (an HTTP or HTTPS
   request that must succeed), so a name resolves only to the nodes that
   are alive. No external health checker and no script edits the zone on
   failure; each server checks and answers by itself.
4. **At least two authoritative servers, in different sites**, following
   0025's site rule: two copies of the same data are never in the same
   site, and a zone served from one site is lost with that site.
5. **It fills 0024's open item.** Nodes behind NAT whose IPv6 prefix
   changes update their own records, either by **RFC 2136 dynamic update
   authenticated with TSIG**, or **through the etcd registry** (0025),
   from which Keel DNS is fed.

## What Debian 13 gives us

Measured on this Debian 13 machine (13.7) with `apt-cache policy pdns-server
pdns-backend-*`, and confirmed read only on packages.debian.org (trixie,
`pdns-server (4.9.17-0+deb13u1)`), 2026-10-02.

| Package | Version | For |
| --- | --- | --- |
| pdns-server | 4.9.17-0+deb13u1 (trixie and trixie-security) | the authoritative server |
| pdns-backend-sqlite3 | 4.9.17-0+deb13u1 | the recommended backend (open question 1) |
| pdns-backend-pgsql, pdns-backend-mysql, pdns-backend-lmdb, pdns-backend-bind | 4.9.17-0+deb13u1 | the alternatives considered |
| pdns-backend-remote, pdns-backend-pipe, pdns-backend-lua2 | 4.9.17-0+deb13u1 | a live etcd backend would be one of these; not recommended (open question 1) |
| pdns-backend-geoip, -ldap, -odbc, -tinydns | 4.9.17-0+deb13u1 | not used |
| pdns-tools | 4.9.17-0+deb13u1 | test and diagnostic tools for the gate |
| bind9-dnsutils | 1:9.20.29-1~deb13u1 | `nsupdate`, the RFC 2136 client on a node |
| dnsdist | 1.9.16-0+deb13u1 | not used in version 1 (open question 5) |

**LUA records are supported in this version.** They exist upstream since
PowerDNS Authoritative 4.2, and the trixie build carries them: `pdns-server`
depends on `libluajit-5.1-2`, and the binary of `4.9.17-0+deb13u1`
(downloaded with `apt-get download`, not installed) contains the settings
`enable-lua-records`, `lua-health-checks-interval`,
`lua-health-checks-expire-delay` and `lua-records-exec-limit`, and the
functions `ifportup`, `ifurlup` and `pickclosest`. They are off by default
(`enable-lua-records`), so Keel DNS turns them on. The same binary has
`allow-dnsupdate-from`, the `TSIG-ALLOW-DNSUPDATE` zone metadata and
`lua-dnsupdate-policy-script` for RFC 2136, and `default-catalog-zone` for
catalog zones.

## How a health checked name looks

```
; N active (0044): answer with every Keel Web node whose port 443 accepts
shop.example.org.  60  IN  LUA  AAAA  "ifportup(443, {'2001:db8:10::11', '2001:db8:20::12'}, {selector='all'})"
shop.example.org.  60  IN  LUA  A     "ifportup(443, {'192.0.2.11', '198.51.100.12'}, {selector='all'})"

; active and standby (0044): the first list while any of it is up, else the second
erp.example.org.   60  IN  LUA  AAAA  "ifurlup('https://erp.example.org/health', {{'2001:db8:10::21'}, {'2001:db8:20::22'}})"
```

Three properties of LUA records that the design relies on, and states:

- **Each server checks from where it is.** Two Keel DNS servers in two
  sites run their own checks and can disagree for a check interval, or for
  longer when a link between one site and one node is broken. A visitor's
  resolver asks one of them; either answer leads to a node that the server
  could reach.
- **When every address is down, PowerDNS answers with an address from
  the list anyway** (its `backupSelector`, random by default) rather than
  with nothing, so a total outage shows the visitor 0042's
  maintenance page or a connection error, not a name that does not exist.
- **LUA records travel by zone transfer as records**, and a secondary with
  LUA records enabled runs their checks itself, so a replica serves health
  checked answers without reaching the primary.

## How it differs from the other appliances

| | Other appliances | Keel DNS |
| --- | --- | --- |
| Public port | 80 and 443 through Keel Web | **53, UDP and TCP**, served by PowerDNS directly |
| Keel Web in front | always (0030) | **none**: DNS is not HTTP, so Nginx, Coraza and Anubis have nothing to do |
| Exposure class (0041, decision 6) | public through Keel Web's ports | **public** on 53/udp and 53/tcp; the PowerDNS HTTP API, when enabled, `loopback`; zone transfers and dynamic updates accepted only from `mesh` addresses |
| Failure | affects that appliance | **affects every appliance whose names it serves**: it is the first appliance on which the others depend |
| Dependencies | may use data services over the mesh | **depends on no other Keel appliance** in its query path: its backend is local, etcd only feeds it, so DNS keeps answering while etcd or a database set is down |

Because its failure affects all the others, Keel DNS has a rule the others
do not: its own servers are never named only inside the zones it serves
without glue at the parent, and its records that do not need a health
check (NS, SOA, MX, plain host records) keep an ordinary TTL.

## Installation modes (0028)

| Mode | Keel DNS |
| --- | --- |
| Simple | one authoritative server. The screen says in one line that a delegated zone needs a second server in another site, which may be a second Keel DNS or any secondary the operator already has |
| Cloud simple | a primary and a replica (a DNS secondary), in different sites; zones reach the replica by NOTIFY and zone transfer over the mesh, and a catalog zone makes a new zone appear on the replica without configuring it there |
| Cloud advanced | three or more servers in different sites, and the zone feed from the etcd registry (open question 1) |

## Open questions (for the maintainer)

- [ ] **1. The backend.** Recommendation: **`gsqlite3`**
  (pdns-backend-sqlite3), one local database per server, with primary and
  replica by NOTIFY, zone transfer and catalog zones. It supports dynamic
  update, catalog zones and DNSSEC, it needs no database appliance (a
  `gpgsql` backend would make DNS depend on a PostgreSQL set, the circular
  dependency the table above refuses), and it runs the same in every mode.
  **The etcd feed of 0025 is a writer, not a backend**: a small process
  (Phase 5) watches the registry and writes the records of the nodes it
  announces into the primary through the PowerDNS HTTP API on the loopback,
  and zone transfer carries them to the replicas. A live backend reading
  etcd on every query (`remote` or `pipe`) is not recommended: it puts the
  quorum in the query path, so losing etcd would stop public DNS, and 0025
  keeps etcd for a few control plane writes a minute, not for public
  queries. Liveness is not the feed's job either: LUA checks handle it on
  every server; the feed changes only which nodes exist.
- [ ] **2. The low TTL policy.** Recommendation: **60 seconds** on health
  checked records, the default of the screen, with 30 as the floor the
  screen accepts; `lua-health-checks-interval` at its default of 5
  seconds; every other record at 3600. 0020's one to five minutes for a
  failover stays the stated figure, because some resolvers ignore a low
  TTL (0044).
- [ ] **3. DNSSEC.** Not decided. Recommendation: not in the first
  version, and decided in a note of its own before any zone is signed.
  PowerDNS can sign LUA answers as it serves them, so the choice of LUA
  records does not close the door.
- [ ] **4. Updates from nodes behind NAT.** Recommendation: **through etcd
  in cloud advanced**, where a node already announces itself and its
  address (0025), and the feed rewrites both the node's own name and the
  address lists of the LUA records that include it. **RFC 2136 with TSIG
  in simple and cloud simple**, where no etcd runs (0041), and for a
  standalone appliance outside a mesh: the node sends `nsupdate` over the
  mesh when its prefix changes, with a TSIG secret of its own (a `generate:
  required` secret under 0041's policy), and `lua-dnsupdate-policy-script`
  limits each secret to that node's own names. An RFC 2136 update changes
  the node's own name only; a health checked service name over that node
  is rewritten by the feed, or by the operator on Keel DNS.
- [ ] **5. Abuse of a public port 53.** PowerDNS Authoritative never
  recurses, so Keel DNS is not an open resolver, but its UDP answers can
  still be used for reflection, and it has no response rate limiting of
  its own. Recommendation: version 1 ships without a front, with CrowdSec
  (0029) on the host and answers kept small; `dnsdist` (in trixie) as a
  later `dnsdist` overlay in front of PowerDNS if the gate or production
  shows abuse.
- [ ] **6. Who runs the second server.** Recommendation: the operator
  always, in any mode; Keel Cloud may offer one, but a standalone set never
  needs it (0020, "Decided").

## Order

Keel DNS does not need etcd, so it does not wait for the mesh control
plane. Placed in the roadmap (tracker#46) **after Phase 3 (Keel Web) and
before Phase 5 (mesh control plane)**:

1. The `keel-overlay-pdns` package (PowerDNS from trixie, `gsqlite3`, LUA
   records on) with its manifest: process `pdns.service`, ports 53/udp and
   53/tcp `public`, a Monit `protocol dns` check against each served zone's
   SOA.
2. The `keel-dns` appliance on Core, simple mode: zones and health checked
   names written by the console into the spec and rendered by keel, as
   0042 does for sites.
3. Cloud simple: primary and replica by NOTIFY, transfer and a catalog
   zone over the mesh; RFC 2136 updates from nodes, with TSIG, accepted
   from mesh addresses only.
4. Phase 5: the feed from the etcd registry, and cloud advanced on three
   sites.

**Done when:** two Keel DNS servers in two containers on different bridges
answer for a test zone; stopping one of two Keel Web nodes removes its
address from both servers' answers within one check interval plus the TTL;
an `nsupdate` with the node's TSIG changes its own name and is refused for
another node's name.

## What this amends

- **0020, "Decided" and "Where each piece lives"** (DNS with a health check
  is a Keel Cloud service, in the `keel-cloud` repository): the service is
  an appliance, Keel DNS, which a standalone operator runs without Keel
  Cloud, keeping standalone parity. Keel Cloud may host Keel DNS servers;
  it no longer owns the DNS piece.
- **0024, "Review notes"** (the DNS successor for nodes behind NAT is not
  decided; a PowerDNS overlay fed from etcd is the likely shape): decided.
  It is Keel DNS, an appliance rather than an overlay on every node, fed
  from etcd in cloud advanced and updated by RFC 2136 elsewhere.
- **0028, the modes**: Keel DNS reads them as every appliance does, with
  primary and replica meaning a DNS primary and secondary in cloud simple.
- **0029**: Keel DNS is not behind the WireGuard VIP. Its redundancy is
  several NS records in different sites, which is how DNS has always been
  made redundant, and the VIP stays mesh internal and for database
  appliances (0041).
- **0041, decision 6**: unchanged, and used for the first time for a
  public port that is not Keel Web's: 53, UDP and TCP.
