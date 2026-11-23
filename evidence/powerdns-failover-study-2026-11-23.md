# Evidence: automatic failover of names with PowerDNS, a study

Date: 2026-11-23. Site: none. Status: study, for decision 0045 (second
round). No real-platform test is in this file. No guest, container or DNS
server was made or changed.

## Question

On 2026-11-23 the maintainer asked for this function, which he calls essential for Keel: when an address
stops answering, the DNS servers that are alive give the failover
address by themselves. His example: `clientdomain.com` points to a Keel
node on BR1. A Keel node on BR2 is a replica of it, with the database
replication and the file synchronisation. If BR1 goes down, PowerDNS must
point the name to the address on BR2.

This file answers 10 questions before the note (6 to 10 come from the
answers of the maintainer later on 2026-11-23):

1. What does Debian trixie ship, and are LUA records in the Debian build?
2. How do LUA record health checks work in the trixie version?
3. Which replication of the DNS servers keeps LUA records, and what
   happens when the sites are cut from each other?
4. Which resolver and client behaviour limits a switch by DNS?
5. Which administration tools exist?
6. How do DNSSEC, LUA records and several servers combine?
7. Which failures move a `cloud_advanced` pair by itself today?
8. What do PowerDNS 4.9 and 5.x mean for Keel DNS, and how does a check
   pass through an edge?
9. Does the data of a PowerDNS 4.9 or 5.x server on a generic SQL back
   end move to 5.1.5 with no change?
10. How can the certificate of a name reach the replica?

It also records how a Keel pair decides its primary today, and what a
node shows that says "I am the primary and I accept writes".

Each result says if it was **read in a primary source** (with the URL),
**read in Keel code** (with the path), or **not verified**.

## 1. PowerDNS Authoritative in Debian (read in a primary source)

Source: <https://qa.debian.org/madison.php?package=pdns&table=debian&text=on>,
read 2026-11-23.

| Suite | Version of `pdns` |
| --- | --- |
| bookworm | 4.7.3-2 |
| trixie | 4.9.18-0+deb13u1 |
| trixie-security | 4.9.18-0+deb13u1 |
| trixie-proposed-updates, trixie-backports | none |
| forky, sid | 5.1.5-2 |

- Binary packages of trixie (<https://packages.debian.org/source/trixie/pdns>):
  `pdns-server`, `pdns-tools`, `pdns-ixfrdist`, and the back ends
  `pdns-backend-bind`, `-geoip`, `-ldap`, `-lmdb`, `-lua2`, `-mysql`,
  `-odbc`, `-pgsql`, `-pipe`, `-remote`, `-sqlite3`, `-tinydns`.
- The trixie changelog
  (<https://sources.debian.org/data/main/p/pdns/4.9.18-0+deb13u1/debian/changelog>):
  "pdns (4.9.18-0+deb13u1) trixie-security ... New upstream version
  4.9.18, fixing security issue CVE-2026-73206 (Closes: #1152255)", of
  2026-10-27.
- The security tracker
  (<https://security-tracker.debian.org/tracker/source-package/pdns>)
  shows every listed CVE as fixed for trixie, forky and sid. Only
  bookworm is vulnerable.
- PowerDNS advisory 2026-13
  (<https://doc.powerdns.com/authoritative/security-advisories/powerdns-advisory-2026-13.html>):
  CVE-2026-73206, 2026-10-21, affects up to 4.9.17, 5.0.7 and 5.1.4,
  first fixed in 4.9.18, 5.0.8 and 5.1.5.

**Result: the CVE gate of 0045 section 1 is cleared.** Trixie ships
4.9.18. The rebuild of the upstream source is not necessary.

**LUA records are compiled in the Debian build.**
`debian/rules` of 4.9.18-0+deb13u1, line 42
(<https://sources.debian.org/data/main/p/pdns/4.9.18-0+deb13u1/debian/rules>):
`--enable-lua-records \`. The build depends on `libluajit-5.1-dev` on
amd64 and arm64. The trixie amd64 package of `pdns-server` depends on
`libluajit-5.1-2`. The file was read on sources.debian.org, not on Salsa.

## 2. LUA records in 4.9.18 (read in a primary source)

doc.powerdns.com serves only the current documentation. The text below
comes from the documentation source at the git tag, for example
`https://raw.githubusercontent.com/PowerDNS/pdns/auth-4.9.18/docs/lua-records/functions.rst`,
and from the code at the same tag.

### 2.1 Functions and options

- `enable-lua-records`: "One of no, yes (or empty), or shared", default
  `no`. A zone can also set the metadata `ENABLE-LUA-RECORDS` = 1.
- `ifportup(portnum, addresses[, options])`: a TCP connect only. "both
  IPv4 and IPv6 addresses can be tested, but ... it is an error to list
  IPv4 addresses on an AAAA record". AAAA works.
- `ifurlup(url, addresses[, options])`: an address is up "if the HTTP
  response code is 200 and optionally ... stringmatch". It accepts sets
  of addresses: "The first set with at least one available address is
  selected".
- In the 4.9.18 code, `ifurlup` takes a flat list or a list of sets
  (`boost::variant<iplist_t, ipunitlist_t>`, `pdns/lua-record.cc`,
  lines 1200 to 1202).
- `ifurlextup`: the check URL is separate from the address that is
  answered.
- Options in 4.9: `selector` and `backupSelector` (`random`, `hashed`,
  `pickclosest`, `all`, both with the default `random`), `source`,
  `timeout` (default 2 s), `stringmatch`, `useragent` (default
  "PowerDNS Authoritative Server"), `byteslimit`.
- 4.9 has no per-check `interval`, no `minimumFailures` and no
  `failOnIncompleteCheck`. 5.0.8 adds the three. 5.1.5 adds the
  `backupSelector` value `empty` ("fail-close backupselector mode") and
  the `ifurlup` option `headers`.

### 2.2 How the checks run (read in the 4.9.18 code)

Source: `pdns/lua-record.cc` at tag `auth-4.9.18`.

- Each PowerDNS process keeps its own check state. Each server checks
  from where it is, in the background, with no shared state. Two servers
  can give different answers for a short time.
- **The first query of a record finds every address down.** `isUp()`
  adds the new check, wakes the checker thread and returns `false`
  (lines 281 to 312). A new check starts as `status{false}` (line 81).
  The first answer then comes from the `backupSelector` over all the
  candidates (lines 876 to 882). The 5.0 documentation states this: "the
  first time they're called, they effectively treat all addresses as
  failing which means that whatever fallback behavior is used will apply
  to that first resolution."
- **When every address is down, the answer is the `backupSelector` over
  all the candidates.** With the default `random`, that is one random
  address, alive or dead. With `backupSelector='all'`, it is every
  address. The 4.9 `index.rst` says "all candidates are returned", and
  `functions.rst` says "will return a random element". The code agrees
  with `functions.rst`. The upstream test uses `backupSelector='all'`
  (`regression-tests.auth-py/test_LuaRecords.py`, line 66).
- 4.9 cannot answer "nothing" when all are down. `empty` is from 5.1.
- One loop runs all checks in parallel. It sleeps
  `lua-health-checks-interval` less the time of the round (lines 186 to
  234). One failed check marks an address down, because 4.9 has no
  `minimumFailures`.
- A check that no query used for `lua-health-checks-expire-delay` is
  deleted (line 201). The next query then gets the first-query answer
  again. A restart of `pdns` also deletes all check state.
- **TLS of `ifurlup` is not verified.** The checker calls
  `mc.getURL(cd.url, rem, ..., timeout, false, false, byteslimit)`
  (lines 132 and 135). The sixth argument is `verify`
  (`pdns/minicurl.hh`, line 50). `pdns/minicurl.cc` sets
  `CURLOPT_SSL_VERIFYPEER` and `CURLOPT_SSL_VERIFYHOST` from it (lines
  171 and 172), and pins the host name of the URL to the candidate
  address with `CURLOPT_RESOLVE` (line 157). Thus the check sends the
  host name of the URL as SNI and `Host`, connects to the candidate
  address, and accepts a self-signed certificate.

### 2.3 Settings (4.9.18 `docs/settings.rst`)

| Setting | Default |
| --- | --- |
| `lua-health-checks-interval` | 5 s |
| `lua-health-checks-expire-delay` | 3600 s |
| `lua-records-exec-limit` | 1000 |
| `lua-records-insert-whitespace` | yes before 5.0, no in 5.0 |

5.1 adds `enable-lua-record-updates`, default `no`: "Allow updating LUA
records as part of AXFR/IXFR, DNS Update or API operations." A 5.1
secondary thus refuses LUA records in a zone transfer until this is
`yes`.

### 2.4 DNSSEC and zone transfer (`docs/lua-records/index.rst`, same in 4.9.18 and 5.1.5)

- "LUA records can be DNSSEC signed, but because they are dynamic, it is
  not possible to combine pre-signed DNSSEC zone and LUA records. In
  other words, the signing key must be available on the server creating
  answers based on LUA records."
- "They can also be transferred via AXFR to other PowerDNS servers."
- "A non-supporting DNS server will also serve a zone with LUA records,
  but they will not function, and will in fact leak the content of the
  LUA records."
- "Use TSIG on AXFR even from trusted sources!"
- A long LUA record goes in a zone transfer as segments of at most 255
  bytes. The type is `LUA = 65402` (`pdns/qtype.hh`).

### 2.5 The zone apex and ALIAS

- ALIAS gives "CNAME-like mechanisms on a zone's apex"
  (`docs/appendices/types.rst`). It needs the `resolver` setting.
- **Not verified:** a LUA record at the zone apex. The documentation and
  the upstream test show no example. The test plan includes it.

## 3. Replication of the DNS servers (read in a primary source)

| Way | LUA records on every server | When the sites are cut | Notes |
| --- | --- | --- | --- |
| Primary and secondaries by NOTIFY and AXFR (0045) | yes, on PowerDNS secondaries only | each secondary answers from its copy until the SOA expire (0045: 14 days) | PowerDNS "cannot serve IXFR updates" (`docs/modes-of-operation.rst`, 4.9.18 and 5.1.5); `pdns-ixfrdist` can |
| Native replication of `gmysql` or `gpgsql` | yes, the rows are the same | each server answers from its local database; a replica refuses writes | binlog format MIXED or ROW (`docs/backends/generic-mysql.rst`) |
| LMDB with Lightning Stream | yes | each server answers from its LMDB; changes wait for the S3 store | Lightning Stream v1.0.5 (2026-10-20), MIT, needs S3; **not in Debian** |

- Catalog zones exist since 4.7.0, with RFC 9432 (version 2) as producer
  and consumer (`docs/catalog.rst`).
- `lmdb-lightning-stream` exists since 4.8.0 (`docs/backends/lmdb.rst`).
- **What Keel has.** The MariaDB pair (0031) and the PostgreSQL pair
  (0054) have 2 data nodes, 3 with an etcd witness (0057). The DNS set
  has 4 servers. A pair does not give 4 independent servers.

## 4. Resolver and client limits (read in a primary source)

| Item | Value | Source |
| --- | --- | --- |
| Google Public DNS | caps TTL at about 6 h; no documented minimum | <https://developers.google.com/speed/public-dns/faq> |
| Cloudflare 1.1.1.1 | keeps up to 3 h; "if the specified record has TTL that is shorter than 3 hours, the resolver respects that" | <https://blog.cloudflare.com/refresh-stale-dns-records-on-1-1-1-1/> |
| Unbound | `cache-min-ttl` default 0 | <https://unbound.docs.nlnetlabs.nl/en/latest/manpages/unbound.conf.html> |
| BIND 9.20 | `min-cache-ttl` default 0, at most 90 s | <https://bind9.readthedocs.io/en/stable/reference.html> |
| Chrome, built-in DNS client | keeps a result at least 60 s (`kMinimumTTLSeconds = 60`) | `net/dns/host_resolver_manager_job.cc`, Chromium main |
| Chrome, system resolver | keeps a result 60 s | same file |
| Java | caches 30 s by default, negative 10 s | OpenJDK `java.security` |
| systemd-resolved | no minimum TTL | `man/resolved.conf.xml` |
| Windows client (old documentation) | negative cache 300 s | Windows 2000 documentation, cc959309 |

Measurements:

- RIPE Labs, 2017-12-01
  (<https://labs.ripe.net/Members/giovane_moura/dns-ttl-violations-in-the-wild-with-ripe-atlas-2>):
  with a TTL of 333 s, 4.17 % of resolvers gave a longer TTL and 1.97 %
  a shorter one.
- Moura et al., "Cache Me If You Can", IMC 2019
  (<https://par.nsf.gov/servlets/purl/10315383>): after a change, about
  90 % of resolvers moved, and about 2.25 % of vantage points stayed on
  the old answer ("sticky resolvers").
- Negative caching (RFC 2308, section 5): the TTL of a negative answer is
  the minimum of the SOA MINIMUM field and the TTL of the SOA.

**Switch time.** Decision 0045, section 10 J, gives the estimate with
each term. It is not measured here. The first version of this file left
out GRACE, the 3 failed checks of the pair rule, the packet cache and
the client floor after a full TTL. Section 14 gives the settings.

## 5. Administration tools (read in a primary source)

- **PowerDNS-Admin** (<https://github.com/PowerDNS-Admin/PowerDNS-Admin>,
  read 2026-11-23): not archived, latest release v2026.11.1 of
  2026-11-07. Its README says "Support for versions older than 5.0 has
  been dropped entirely". `app-support.json` lists Auth 5.0 and 5.1. It
  does not support the 4.9.18 of trixie. It is not in Debian.
- **The HTTP API** (4.9.18 `docs/settings.rst`): `api` and `webserver`
  default `no`, `webserver-address` 127.0.0.1, port 8081,
  `webserver-allow-from` 127.0.0.1 and ::1. The API key can be a salted
  hash since 4.6.0.
- **`pdnsutil`**: 5.0 changes the syntax to `pdnsutil <object> <action>`
  (`zone create`, `metadata set`). The old syntax still works
  (`docs/upgrading.rst`, 5.1.5).

## 6. How a Keel pair decides its primary (read in Keel code)

Repository `Keel-Linux/keel`, `origin/main` at `35e8aa6` (keel 0.23.97).

- **The primary is the node that holds the VIP.** "The primary is the
  node that holds it ... there is no role field beside it"
  (`docs/vip.md`, lines 11 to 13). `database.server.role` in the spec is
  the role at installation only (`docs/replication.md`, "The pair").
- **`cloud_advanced`: automatic.** The holder renews an etcd lease every
  2 s and carries the VIP only while its last confirmed renewal is under
  15 s old. The kernel removes the address at that time. The other node
  claims when the lease is gone: "0020's automatic failover, which
  etcd's three voters make possible" (`docs/vip.md`, lines 350 to 376).
- **`cloud_simple`: by hand.** Without etcd, promotion is
  `keel database promote [--old-primary-gone]` by the operator (0020,
  lines 37 to 40; 0057, "What was asked"). "Without etcd, an old primary
  that is alive but cannot be reached keeps the VIP on its `wg0` and
  stays writable until it learns the newer claim (its next `keel vip
  check`, at boot and every minute): only the operator knows that it is
  gone" (`docs/vip.md`, lines 246 to 250). On a node that declares
  `database.server`, `keel database follow` does that check at boot, at
  each VIP change and at each `keel database watch` run (`docs/vip.md`,
  lines 258 to 266). The watch timer runs every 30 s
  (`debian/keel.keel-database-watch.timer`, `OnUnitActiveSec=30s`).
- **The role file.** `keel database follow` writes `/var/lib/keel/role`
  (`role=`, `replicates=`, `vip=`) only when it proved the role
  (`keel/system/dbpair.py`, `ROLE_FILE` and `ROLE_TEXT`;
  `keel/system/dbfollow.py`, lines 356 to 361).
- **The role file is not enough to say "writable".** During the
  holder's doubt (keel#195) the holder is read only, and "the role file
  is left" (`keel/system/dbfollow.py`, branch `_in_doubt`). The mark of
  the doubt is `/var/lib/keel/vip/<vip>.unconfirmed` (`docs/vip.md`,
  "The holder's doubt"). A lagging holder also stays read only
  (keel#271, `docs/replication.md`, "PROMOTION REFUSED").
- **What a node shows today.** `keel database status` and `keel vip
  status` show the role on the command line. etcd holds
  `/keel/<mesh id>/vip/<vip>/holder` on the mesh only. The LNMP check
  page `/keel-check/` shows "writable, or read-only on a replica"
  (`keel-lnmp/README.rst`). That page answers 200 on both nodes and is
  behind Anubis in the cloud modes (`keel-web/README.rst`,
  `keel-default.d`). **No public HTTP address answers 200 only on the
  writable primary.** It is to build.
- **Where it could be served.** keel-web includes
  `/etc/nginx/keel-front.d/*.conf` in its front server on 443
  (`keel-web/README.rst`, at 05631a0). **Not verified:** that a
  `location` there is served before Anubis.
- **Fail-back.** An old primary that comes back learns the newer claim,
  drops the address, turns read only, catches up and rejoins as a
  replica (`docs/vip.md`, lines 252 to 257). 0031: the role returns to
  the original primary "only after it has fully caught up".

## 7. Related project facts

- 2026-11-10: the maintainer called the public entry by name of a
  `cloud_advanced` pair "the final test" before production, and put it
  on standby. Two ways were offered: A, one record per site on an
  existing DNS; B, Keel DNS with health checked records. He did not
  choose.
- 0045 was on `main` with the status proposed (commit `55d97e4`) before
  this work. Its older text is in the open PR handbook#38, which this
  work does not change.
- 0094: no new web panel on a node. 0095: a new function starts at the
  laboratory level.

## 8. DNSSEC with LUA records and several servers (read in a primary source)

Requirement of 2026-11-23: DNSSEC with live signing. The text below is from the 4.9.18 documentation
source (`docs/` at tag `auth-4.9.18`).

- **Online signing with a replicated database.** `dnssec/modes-of-operation.rst`:
  "there is a single "SQL" database that contains, in separate tables,
  all domain data, keying material, and other DNSSEC related settings.
  This database is then replicated to all PowerDNS instances, which all
  serve identical records, keys, and signatures." It also says that the
  replication must use "a secure network, or ... an encrypted
  connection".
- **A zone transfer makes a secondary presigned.** `domainmetadata.rst`,
  `PRESIGNED`: "PowerDNS sets this flag automatically upon incoming zone
  transfers (AXFR) if it detects DNSSEC records in the zone." A
  presigned zone cannot carry LUA records (section 2.4). Thus a signing
  primary that sends AXFR to PowerDNS secondaries breaks the failover
  names on those secondaries.
- **Front-signing.** `dnssec/modes-of-operation.rst`: "PowerDNS can
  operate as a signing server which operates as a slave to an unsigned
  master ... if keying material is available for an unsigned zone that
  is retrieved from a master server, this keying material will be used".
  Thus AXFR with DNSSEC and LUA needs an unsigned primary that does not
  answer the public, and the keys on each secondary.
- **Live signatures.** "signatures ... are calculated on the fly, and
  heavily cached." The RRSIG validity is 3 weeks and moves every
  Thursday. DNSKEY TTL comes from the SOA minimum field.
- **NSEC3 narrow** "denies incoming AXFRs for zones in this mode".
- **Back ends.** `gmysql`: "DNSSEC: Yes (set `gmysql-dnssec`)", default
  no. `gsqlite3`: "DNSSEC: Yes". `docs/backends/generic-mysql.rst`,
  "Using MySQL replication": binlog format MIXED or ROW.
- **Key tools in 4.9** (`manpages/pdnsutil.1.rst`): `add-zone-key ...
  [active|inactive] [published|unpublished]`, `publish-zone-key`,
  `activate-zone-key`, `deactivate-zone-key`, `unpublish-zone-key`,
  `remove-zone-key`, `export-zone-key`, `import-zone-key`. The guides
  `guides/zskroll.rst` and `guides/kskroll.rst` describe the rolls.

**Not tested:** LUA records with live signing on a PostgreSQL hot
standby; the
DNSSEC answer of the first query after a cold start; a ZSK roll while
one replica lags; the import of the keys of a zone that is already signed.

## 9. Which failures move a `cloud_advanced` pair today (read in Keel code, not tested unless stated)

Repository `Keel-Linux/keel`, `origin/main` at `35e8aa6`.

**The only trigger of an automatic move is the etcd lease of the
holder.** `keel/mesh/vipetcd.py`, `holding()` and `renew()`: the holder
renews its lease every 2 s and keeps the VIP while the last renewal that
the majority confirmed is under 15 s old. "any error of etcd is no
renewal". `fail_over()`: the other node claims only when the lease of
the newest claim is gone. No code path in `vipetcd.py` reads the state
of the database, of nginx, of the application, of the disk or of a
certificate. `keel/system/dbwatch.py` alerts on the database and on
replication. It does not release the VIP. The controller asks its own
etcd first and then the other members (`docs/vip.md`, "the controller
asks this member's etcd first, then the others of the cluster record").

| Failure on the primary site | Moves by itself today | Why |
| --- | --- | --- |
| Node down (power, kernel) | yes | renewals stop; the lease ends at 20 s; the other node claims. **Tested** on keel 0.23.68: "Other writable +24.6 s" (`evidence/2026-11-01-keel-0.23.68-mariadb-faults.md`, K2) |
| Site cut from both other sites | yes | the holder loses the majority; it is read only at 6 s, drops the VIP at 15 s; the other node claims after the lease. Tested in the same file, K2 (SIGKILL and cut) |
| The VIP controller stops for good | yes | the kernel removes the address at the end of its lifetime (15 s), and the lease ends (`docs/vip.md`, "enforced by the kernel") |
| etcd of the primary node stops | no, and correctly | the controller renews through the other members (`docs/vip.md`) |
| Database server stops | no | the lease does not depend on it; `dbwatch` alerts |
| Application stops, node up | no | nothing reads it |
| nginx or the web front stops | no | nothing reads it |
| Public uplink of the site stops, the mesh still works | no | etcd and replication still work, so the lease stays |
| Disk full, or file system read only | no | the controller keeps its state in memory and renews over the network; the database and the application fail |
| Certificate missing or expired | no | nothing reads it |

**Rules that a new trigger must keep** (read in code and notes): a
replica that lags never takes writes (keel#271, `docs/replication.md`,
"PROMOTION REFUSED"); an old primary returns as a replica (0049,
`docs/vip.md`); a release before a take, so the holder drains its
writes first (`keel vip promote`, `docs/vip.md`); the epoch fence.

## 10. PowerDNS 4.9 and 5.x for Keel DNS (read in a primary source)

Requirement: Keel DNS can take over the zones and DNSSEC keys of an
existing PowerDNS Authoritative Server (4.9 or 5.x) on a generic SQL
back end (`gpgsql` or `gmysql`).

- **Support.** `docs/appendices/EOL.rst` on the `master` branch, read
  2026-11-23: "The currently supported release train of PowerDNS
  Authoritative Server is 5.1." "PowerDNS Authoritative Server 4.9 will
  only receive critical updates; it will be end of life after PowerDNS
  Authoritative Server 5.2 is released." The table: 5.1 released
  2026-06-03, critical-only about January 2027, end of life about
  January 2028. 5.0 critical-only since 2026-06-03, end of life about
  March 2027. 4.9 critical-only since 2025-08-22, end of life about
  September 2026. The newest tag is `auth-5.2.0-alpha0` (2026-06-02).
  4.9.18 came out on 2026-10-21, so 4.9 still gets critical fixes after
  the estimate. "~January 2027" for 5.1 is the start of its
  critical-only time, not its end. The copy of `EOL.rst` at tag
  `auth-5.1.5` is older and still names 5.0.
- **Debian.** trixie and trixie-security: 4.9.18-0+deb13u1. forky and
  sid: 5.1.5-2. trixie-backports: none (section 1).
- **The `gmysql` schema.** `modules/gmysqlbackend/schema.mysql.sql` at
  the tags `auth-4.9.18`, `auth-5.0.8` and `auth-5.1.5`: the 3 files are
  the same (`diff` gives no output).
- **Upgrade notes.** `docs/upgrading.rst` at `auth-5.1.5`, "4.9.0 to
  5.0.0": "Version 5.0.0-alpha1 ships a new version of the LMDB database
  schema (called version 6) ... There is no downgrade process." No
  schema change is listed for the generic SQL back ends from 4.9 to
  5.1. "5.0.x to 5.1.x": "LUA record updates no longer allowed by
  default" (`enable-lua-record-updates`), the web server sends no
  `access-control-allow-origin: *`, `pdnsutil` shows trailing dots, the
  API normalises record data.
- **LUA options in 5.x** (`docs/lua-records/functions.rst` at
  `auth-5.1.5`): `minimumFailures` "The number of unsuccessful checks in
  a row required to mark the address as down. Defaults to 1";
  `failOnIncompleteCheck` "if set to `true`, return SERVFAIL instead of
  applying `backupSelector`, if none of the addresses have completed
  their background health check yet"; per-check `interval`;
  `backupSelector='empty'` (5.1). In `pdns/lua-record.cc` at
  `auth-5.1.5`, the option is compared with the string `"true"` (line
  413).
- **TLS of the check in 5.1.5.** `minicurl.getURL(cd.url, rem, ...,
  timeout, &mch, false, false, byteslimit, http_code)` (lines 169 and
  172): `verify` is still `false`.
- **Not verified:** that the Debian source 5.1.5-2 builds on trixie.

## 11. How a check passes through an edge (read in a primary source)

This file states general rules only. It does not describe how a
production site is built.

- **Documentation** (`docs/lua-records/functions.rst` at `auth-5.1.5`):
  `ifurlup` "attempts an actual http(s) connection to `url`", and the
  addresses are the "List of sets of addresses to check the URL on". It
  says nothing about SNI, `Host`, redirects or the certificate.
- **Code**, `pdns/minicurl.cc` at `auth-5.1.5`: line 137 sets
  `ports{80, 443}`; line 145 makes `"%s:%u:%s"` of the host of the URL,
  the port and the listed address; line 155 gives it to curl as
  `CURLOPT_RESOLVE`; line 160 sets `CURLOPT_FOLLOWLOCATION` to true; line
  169 sets `CURLOPT_SSL_VERIFYPEER` from `verify`, which
  `pdns/lua-record.cc` passes as `false` (lines 169 and 172). The
  4.9.18 code is the same (section 2.2).
- **Result.** The check connects to the listed address, sends the host
  of the URL as SNI and as `Host`, and accepts any certificate.
  `CURLOPT_RESOLVE` pins only the host of the URL. A redirect to another
  name resolves through public DNS. Thus the check address must never
  redirect.
- **General rules for an edge.** Where an edge passes 443 in TCP by
  SNI, the check reaches the node that the edge gives for the name.
  Where an edge ends TLS, it must pass the check path unchanged, and
  never cache, answer or redirect it. A TCP open on 443 of an edge
  proves only the edge. The edge of the other site must know the name
  and hold a valid certificate before a name can move. **Not tested.**

## 12. The PostgreSQL back end (read in a primary source)

Requirement: as in section 10. This section reads the `gpgsql` back
end.

- **The schema.** `modules/gpgsqlbackend/schema.pgsql.sql` at the tags
  `auth-4.9.18`, `auth-5.0.8` and `auth-5.1.5`: 98 lines each, and the 3
  files are the same (`diff` gives no output).
- **Upgrade files.** The directory `modules/gpgsqlbackend` at
  `auth-5.1.5` holds upgrade files up to `4.3.0_to_4.7.0_schema.pgsql.sql`.
  It holds none for 4.7 to 5.x. `docs/upgrading.rst` at `auth-5.1.5`
  lists no schema change of the generic SQL back ends from 4.9 to 5.1.
  Its only PostgreSQL note for 5.0 to 5.1 is the TSIG key query, which
  needs PostgreSQL 9.5 or newer.
- **Result.** The data of a PostgreSQL server of PowerDNS 5.0 or 5.1, on
  the unchanged upstream schema, goes to 5.1.5 with no schema change.
  **Not verified:** that a given source server has no local change to
  its schema.
- **The back end** (`docs/backends/generic-postgresql.rst` at
  `auth-5.1.5`): "Native: Yes", "DNSSEC: Yes (set `gpgsql-dnssec`)",
  "Views: No", "API: Read-Write".
- **Read-only databases** (`docs/modes-of-operation.rst`, "Native
  replication", 4.9.18 and 5.1.5): "Typically, a database secondary will
  be configured as read-only as uni-directional database replication is
  usually sufficient. A PowerDNS server only requires database write
  access if it is participating as a primary or secondary in zone
  transfers, or has a frontend attached for managing records, etc."
- **Keel.** The layer `postgresql` is built on `core`
  (`Keel-Linux/keel-postgresql`, `README.rst`, at `76160f6`). 0054 and
  `keel/system/dbpg*.py` make a PostgreSQL pair, not a writer with
  several standbys.
- **Not tested:** PowerDNS on a PostgreSQL hot standby with signed
  zones and LUA records; query cancels during replay.

## 13. The certificate on the replica (read in Keel code)

Repository `Keel-Linux/keel`, `origin/main` at `35e8aa6`.

- `docs/apply.md`, "tls.acme": the certificate comes from
  `dehydrated-wrapper --log-info --challenge http-01`. "Refused, with
  the reason, and the run fails: `dns-01` (a DNS provider and its
  credentials have no field in the spec yet)". An `http-01` challenge
  reaches only the node that DNS gives.
- No code copies the public certificate of a name to the replica.
- **The members' channel** (`keel/mesh/vipserve.py`, `shared()`): "A
  secret the pair shares, to the other member alone". It answers only
  the other member of the pair record, over TLS inside WireGuard. Today
  it gives the Anubis key (`keel/system/anubiskey.py`) and the
  replication credential (`keel/system/dbsecret.py`).
- `keel/system/anubiskey.py`: "A key that is there is never replaced".
  A certificate is renewed, so a copy of a certificate needs a rule to
  replace an older copy.

## 14. Further facts for the second round (read in a primary source)

- **Cold start with 5.x options** (`pdns/lua-record.cc` at
  `auth-5.1.5`): a new check starts with `status{false}` and
  `first{true}` (lines 107 to 122). `isUp()` returns the stored status
  for an existing entry, with no look at `first` (lines 376 to 404).
  Only the query that makes a new entry gets -1 with
  `failOnIncompleteCheck` (lines 405 to 416). After a failed check,
  `state->status = ++state->failures < minimumFailures` (line 346),
  with the upstream comment "expose 'down, but not enough times yet'
  targets as up". Thus with `minimumFailures=2`, a first failed check
  sets the status to up.
- **No address up.** `useSelector()` returns an empty list for
  `"empty"` (line 715). An exception of a LUA record is logged and
  thrown again (lines 1910 to 1930). `pdns/packethandler.cc` at
  `auth-5.1.5`, the catch of `std::exception`: "Exception building
  answer packet ... sending out servfail" (lines 1731 to 1735). Thus a
  LUA record that raises an error when its result is empty gives
  SERVFAIL. **Not tested.** A LUA record that starts with `;` runs as
  Lua code with its own `return` (`docs/lua-records/index.rst`).
- **Shared Lua state** (`docs/lua-records/index.rst`): "the state is
  per-thread ... there is no single shared Lua environment". Thus a
  "last known good primary" cannot be kept reliably in Lua.
- **Settings** (`docs/settings.rst` at `auth-5.1.5`): `cache-ttl`
  default 20, `dnssec-key-cache-ttl` default 30,
  `zone-metadata-cache-ttl` default 60, `dnsupdate`, and
  `dnsupdate-require-tsig` (since 5.0.0). `api-readonly` is not a
  setting of 5.1.5. It appears only as an old rename in
  `docs/upgrading.rst`.
- **SERVFAIL caching** (RFC 2308, section 7.1): a resolver may keep a
  server failure for up to 5 minutes.
- **The Recursor** (<https://security-tracker.debian.org/tracker/CVE-2026-73206>,
  read 2026-11-23): `pdns-recursor` 5.2.13-0+deb13u1 in trixie is
  vulnerable, 5.4.9-1~deb13u1 in trixie-security is fixed (DSA-6630-1).
- **The VIP code** (`keel/mesh/vipetcd.py` at `35e8aa6`): a lease
  revoked while the holder renews it makes the holder claim again at the
  next epoch; the other node waits GRACE after a lease that ends early;
  `GRACE = RELEASE_AFTER + RENEW + CALL_TIMEOUT` (15 + 2 + 2 = 19 s).
  `docs/vip.md`, "keel vip promote": the node that becomes the primary
  asks the holder to release, and waits for its lease, up to the TTL.

## Not verified

1. A LUA record at the zone apex.
2. A documented minimum TTL for Google, Cloudflare, Quad9 or OpenDNS.
3. The DNS cache of Windows 10 and 11.
4. That a `location` in `keel-front.d` is served before Anubis.
5. That the Debian source `pdns` 5.1.5-2 builds on trixie.
6. PowerDNS on a PostgreSQL hot standby with no write (section 12).
7. That the packet cache holds the answers of LUA records.
8. The NSEC and NSEC3 records of names that carry LUA records.
9. The SERVFAIL of a LUA record that raises an error (section 14).
10. The check through an edge (section 11).
11. Any switch time.
12. The Debian packaging files were read on sources.debian.org, not on
    Salsa.

## Not done

No guest, container or DNS server was made. No production DNS server
was touched. No repository other than the handbook was changed.
