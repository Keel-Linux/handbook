# 0045: Keel DNS, PowerDNS authoritative servers with automatic failover of names

Date: 2026-10-24, second round 2026-11-23
Status: **proposed, for the maintainer. Second round 2026-11-23.** The
first round of 2026-10-24 replaced the 0045 part of handbook#38. The
maintainer decided the premise there on 2026-10-02: Keel DNS is an
appliance, it runs PowerDNS Authoritative, health checked answers use
LUA records, and the servers run on different sites. Those points stand.

The second round adds the automatic failover of names and rewrites the
note as one text. The number stays, because the note was never accepted
and nothing is built from it. The section "What changed in the second
round" lists the changes. The evidence is
`evidence/powerdns-failover-study-2026-11-23.md`. Nothing here is
implemented.

The maintainer approved the rule of section 11 (the pair moves by
itself, and its five limits) on 2026-11-23. He agreed to the scope of
version 1 (section 10 I) on 2026-11-23, to confirm when the note is
accepted. The items that this revision proposes are marked
**(proposed)**. Only two things are open: the acceptance of the note by
the maintainer, and the results of the real tests.

## What was asked

**First round.** The maintainer asked for a Keel DNS appliance on
PowerDNS. It answers for the operator's zones, and only with addresses
that are alive. It takes updates from nodes behind NAT whose IPv6 prefix
changes (the open item of 0024). Four questions followed: the database
back end, the DNSSEC keys, the API and web interface, and the recursor.
A fifth question came from 0050: which replication do the servers use
across sites?

**Second round, 2026-11-23.** The maintainer said that PowerDNS is the
most urgent of the applications that wait. He asked for a function that
he calls essential for Keel as a whole. When an address stops
answering, the DNS servers that are still alive give the failover
address by themselves. His example: `clientdomain.com` points to a Keel
node on BR1. On BR2, another Keel node is a replica: it receives the
database replication and the file synchronisation. If BR1 goes down,
PowerDNS points the name to the address on BR2.

On 2026-11-10 he called this entry by name "the final test" of a
`cloud_advanced` pair, and put it on standby. This round completes that
test.

His answers of 2026-11-23 give these requirements:

1. DNSSEC with live signing is required.
2. Keel DNS must be able to take over the zones and DNSSEC keys of an
   existing PowerDNS Authoritative Server (4.9 or 5.x) on a generic SQL
   back end (`gpgsql` or `gmysql`).
3. In `cloud_advanced`, the pair must move by itself for each failure
   that makes the service unusable. An alert and a promote by hand is
   refused (section 11).

## Why (brief section 10)

1. **Why the current approach is not enough.** Keel has no name server.
   0020 and 0044 make DNS with a health check the first way for a public
   client to reach a live node. The mesh does not help, because a public
   resolver is outside it. Today a name does not follow the pair.
2. **Whether it can be made to work.** It can, with parts that exist.
   PowerDNS Authoritative has LUA records with health checks, live
   DNSSEC signing and RFC 2136 updates with TSIG. PostgreSQL streaming
   replication gives each server a local copy of the zones and the
   keys. Keel already runs PostgreSQL replication (0054).
3. **Why this is better.** Each server answers and signs from its local
   copy, and needs no other Keel service in its query path. Each server
   checks the pair by itself. A name follows the pair when the pair
   moves, with no person in the path.

## Decision

### 1. Upstream (proposed: the 5.1 line)

| Item | Value (checked 2026-11-23) |
| --- | --- |
| Debian trixie and trixie-security | `pdns` 4.9.18-0+deb13u1 |
| Debian forky and sid | `pdns` 5.1.5-2 |
| trixie-backports | none |
| LUA records in the Debian build | yes: `--enable-lua-records` in `debian/rules` |
| Upstream | the supported train is 5.1 (5.1.5); 5.2.0 is in alpha only |
| Licence | GPL-2.0 |
| TurnKey prior art | none for the authoritative server |

**Upstream support** (`docs/appendices/EOL.rst` on `master`):

- 5.1 is the supported train. Its critical-only time starts about
  January 2027, and its end of life is about January 2028.
- 5.0 gets critical updates only, and ends when 5.2 is released.
- 4.9 gets critical updates only since 2025-08-22, and ends when 5.2
  is released. The table estimated September 2026. 5.2 is not released,
  and 4.9.18 came out on 2026-10-21. Thus 4.9 still gets critical fixes
  today, but its end can come at any 5.2 release.

**Decision (proposed): Keel DNS uses the 5.1 line.** The package is a
Keel backport of the Debian source package `pdns` 5.1.5-2 from forky,
built for trixie. It keeps the Debian names (`pdns-server`,
`pdns-backend-pgsql`), as the naming rule of 2026-11-16 says. It enters
the scope of 0096 as a later package (0096, section 1). Four reasons:

1. The data to take over can come from PowerDNS 5.x. For such data, an
   image on 4.9 would be a step back.
2. 4.9 is near the end of its upstream life. 5.1 has support to about
   January 2028.
3. 5.0 and 5.1 give the options of section 7.
4. The `gpgsql` schema is the same file in 4.9.18, 5.0.8 and 5.1.5
   (evidence section 12). The `gmysql` schema is also the same file in
   these versions (evidence section 10). Data of a 4.9 or 5.x server on
   these back ends goes to 5.1.5 with no schema change.

**The cost.** Debian security does not cover the backport. Keel follows
the 5.1 releases through 0096. That the source of 5.1.5-2 builds on
trixie is not verified (work list, item 6).

**Security gate.** PowerDNS advisory 2026-13 (CVE-2026-73206, a denial
of service in the decompression of names) is fixed in 4.9.18, 5.0.8 and
5.1.5. Keel DNS does not release with a version that has an open
advisory of PowerDNS or of Debian.

**TurnKey prior art.** `turnkeylinux-apps` has no `powerdns` or `pdns`
repository. `turnkeylinux/tracker` issue 2089 and
`turnkeylinux/pdns-recursor` are about the Recursor, not the
authoritative server. Nothing is forked.

### 2. Base: the `postgresql` layer, no web layer (proposed)

**Keel DNS is a layer on the `postgresql` layer of Keel** (Keel Core
and PostgreSQL, `Keel-Linux/keel-postgresql`). It is not on `web`,
`lnmp` or `lnpp`. DNS is not HTTP, so nginx, Coraza, Anubis, the PHP
of `lnmp` and the Python of `lnpp` (0059) have no work. The appliance is `dns`, its
repository is `Keel-Linux/keel-dns`, and its overlay is
`keel-overlay-pdns` (0036): the unit, `pdns.conf`, the first boot hook,
the role hook and the checks.

### 3. The replication across sites (proposed: PostgreSQL streaming replication)

**Fixed constraints** (evidence section 8):

1. A zone with LUA records is signed live. The signing keys must be on
   each server that builds an answer. The failover records cannot be
   presigned.
2. A PowerDNS secondary marks a zone `PRESIGNED` by itself when an AXFR
   brings DNSSEC records. Thus a signing primary with AXFR secondaries
   breaks the LUA records on the secondaries.
3. PowerDNS documents one way for live signing on several servers: one
   SQL database with the records, the keys and the DNSSEC settings,
   "replicated to all PowerDNS instances", over an encrypted connection.

| Way | The keys reach each server | A key roll | When the sites are cut | What is new |
| --- | --- | --- | --- | --- |
| N: `gpgsql`, one PostgreSQL writer and 3 hot standbys by streaming replication | with the rows | one act on the writer | each standby answers and signs from its local copy | a writer with several standbys in `keel` |
| F: an unsigned writer that does not answer the public, and front-signing secondaries | `keel` copies them with `pdnsutil export-zone-key` and `import-zone-key` | `keel` repeats each step on each server | each secondary answers and signs alone | a key-copy channel and a roll procedure in `keel` |
| L: LMDB and Lightning Stream | an S3 store | one act | each server answers alone | not in Debian; an S3 store |
| `gsqlite3` and AXFR (the first round) | not at all | not possible | each secondary answers | refused by constraint 2 |

**Decision (proposed): way N.** Five reasons:

1. It is the way that PowerDNS documents for live signing.
2. No `keel` code copies a private key. The keys travel with the rows,
   over the mesh, with TLS.
3. A key roll is one act on the writer.
4. A standby reads only its local PostgreSQL. Thus the query path
   depends on no other Keel part.
5. An operator who already runs PowerDNS on PostgreSQL moves without a
   schema conversion, and the keys come with the rows.

This is not the Keel database pair. It is asynchronous streaming
replication: one writer and 3 hot standbys, with no synchronous commit
and no etcd. A cut of a site must not stop the writes of the writer.
Way F is the fallback if the real test of way N fails.

**What PowerDNS needs from a hot standby.** The documentation says: "A
PowerDNS server only requires database write access if it is
participating as a primary or secondary in zone transfers, or has a
frontend attached for managing records" (`docs/modes-of-operation.rst`,
"Native replication"). Thus a standby runs with:

- `primary=no` and `secondary=no`;
- `api=no`;
- `dnsupdate=no`;
- `gpgsql-dnssec=yes`, so that it reads the keys;
- no `pdnsutil` act that writes.

**To test:**

- A hot standby answers each query of a signed zone with LUA records.
- It logs no error of a read-only transaction.
- The replay of the writer does not cancel the short queries of
  PowerDNS (`hot_standby_feedback`, `max_standby_streaming_delay`).

### 4. The set of servers

**Keel DNS has four servers: one writer and three hot standbys.** They
are on at least three sites, with at most two on one site. At least one
server is on a site that holds no node of the pairs that it serves.

| | Writer | Standby |
| --- | --- | --- |
| Public port 53, answers, live signing, LUA checks | yes | yes |
| RFC 2136, the renderer, `pdnsutil` writes | yes | no |
| PostgreSQL | read and write | hot standby, read only |

- **The mesh VIP is the address of the writer for the control path
  only** (0049). Nodes send RFC 2136 updates to it, and the standbys
  replicate from the writer through it. It never appears in an NS
  record, a glue record or a public answer.
- **A move of the writer is by hand in version 1** (`keel database
  promote` for a writer with several standbys, to build). The read side
  needs no move: each standby keeps its copy and answers while the
  writer is down. Only changes to zones wait.
- **The renderer** writes the zones and the failover names of the spec
  into the database. It runs on the writer only, as a oneshot unit with
  a role condition.
- **Replicated paths.** The appliance declares no `state.replicate`.
  PostgreSQL replicates `/var/lib/postgresql`. The Syncthing overlay is
  `disabled` in each mode.
- **No outside secondary in version 1.** A zone with failover names
  cannot have one (section 3, constraint 2).

### 5. Updates from nodes, and the TSIG keys

The decision of handbook#38 stands. A node behind NAT updates its own
names by RFC 2136 with TSIG, sent to the VIP of the writer over the
mesh. In `cloud_advanced` the etcd registry feeds the zones later
(Phase 5).

- The writer sets `dnsupdate=yes` and `dnsupdate-require-tsig=yes`
  (5.0). Each zone sets `ALLOW-DNSUPDATE-FROM` to the mesh prefix and
  `TSIG-ALLOW-DNSUPDATE` to the key name.
- `lua-dnsupdate-policy-script` limits each key to the names of its own
  node.
- The TSIG keys are rows of the `tsigkeys` table. Thus they replicate to
  each standby with the zones. A standby never accepts an update
  (`dnsupdate=no`).
- A key is never in the image, in the spec or in the handbook (0041).

### 6. DNSSEC

**DNSSEC with live signing is required** (the maintainer, 2026-11-23).
Each server signs each answer with the keys in its local copy.

**A key roll** (`guides/zskroll.rst`, `guides/kskroll.rst`):

- **ZSK.** On the writer: add the new key as inactive and published,
  wait, activate it, wait, then deactivate and remove the old key.
- **KSK.** The same steps, and a change of the DS record at the parent
  zone. The DS change is an act of the operator at the registrar. Its
  waits add the TTL of the DS record.
- **Each wait** is longer than the sum of: the DNSKEY TTL, the
  replication lag alert (60 s), `dnssec-key-cache-ttl` (default 30 s)
  and `zone-metadata-cache-ttl` (default 60 s). A standby that lags then
  serves the old key set for a time that is still safe.

**Items for the real test, not decided:** the algorithm of the keys,
NSEC or NSEC3 (and NSEC3 narrow), and the CPU cost of live signing.

**Custody.** The keys are rows in the `cryptokeys` table. The
replication uses TLS on the mesh. The backup is encrypted (0037). The
keys are never on the build host (0055). Their custody is never in the
handbook.

### 7. LUA records and the health checks (proposed)

- `enable-lua-records=yes` on each server, in the file.
- `lua-health-checks-interval` stays at 5 s.
- `lua-health-checks-expire-delay` is 86400 s. A timer on each server
  queries each failover name every 5 minutes, so that its checks stay.
- `enable-lua-record-updates` (5.1, default `no`) stays `no` on the
  standbys. On the writer it is `yes` only if the renderer uses the
  API. The real test checks if `pdnsutil` needs it.
- `minimumFailures` stays at its default of 1. A value of 2 is unsafe:
  in the 5.1.5 code a first failed check sets the status to up
  (`state->status = ++state->failures < minimumFailures`). A replica that
  answers 503 would then count as up for one interval after each start.
- **When no address is up, the server answers SERVFAIL (proposed, to be
  tested).** The record uses `backupSelector='empty'` (5.1) and Lua code
  that raises an error when the result is empty. The 5.1.5 code turns an
  error of a LUA record into SERVFAIL ("Exception building answer packet
  ... sending out servfail", `pdns/packethandler.cc`). A resolver then
  asks another server of the zone. A server never gives the replica as a
  second address because it cannot see the primary.
- `failOnIncompleteCheck='true'` (5.0) gives SERVFAIL on the query that
  starts a check. Later queries before the first result find all
  addresses down, and the rule above gives SERVFAIL too.
- Health checked names have a TTL of 60 s.

The costs of SERVFAIL: a resolver can keep a SERVFAIL for up to 5
minutes (RFC 2308, section 7.1). In the gap of a move, when no node
answers as the primary, all servers answer SERVFAIL. The real test
measures this gap and compares it with `backupSelector='all'`.

### 8. Ports, mesh, TLS and health

| Port | Protocol | Exposure | Use |
| --- | --- | --- | --- |
| 53 | udp, tcp | `public` | queries |
| 53 | udp, tcp | `mesh` | RFC 2136 updates to the VIP of the writer |
| 5432 | tcp | `mesh` | PostgreSQL streaming replication, with TLS |
| 8081 | tcp | `loopback` | the PowerDNS API, on the writer only |

- **Port 53 reaches the server directly**, or through a plain address
  translation. It never goes through an HTTP proxy.
- **There is no TLS on 53 and no nginx route.** DNS over TLS is not in
  version 1.
- **The API stays on the loopback of the writer.** CVE-2026-33257,
  CVE-2026-33260 and CVE-2026-42005 are web requests that make the
  PowerDNS web server allocate memory without a limit.
- **Monit checks** (0040): `protocol dns` against the SOA of each served
  zone, on each server.
- **Replication lag check:** a standby that is more than 60 s behind the
  writer raises an alert (0063).
- **CrowdSec** (0029) runs on the host. PowerDNS never recurses, so Keel
  DNS is not an open resolver. `dnsdist` is a later overlay if the
  production shows abuse.

### 9. The API, the web interface and the recursor

**No web interface.** The Keel console writes zones and failover names
into the spec, and `keel` renders them. A person who needs a record that
the spec does not carry uses `pdnsutil` on the writer, or an RFC 2136
update with a key.

PowerDNS-Admin (MIT, v2026.11.1 of 2026-11-07) supports Authoritative
5.0 and 5.1. It is not in Debian, it has its own database and its own
accounts, and its edits would compete with the spec. Decision 0094 also
keeps web panels off the nodes. Settings go through confconsole menus
that call `keel` (0094).

**The recursor is out of scope.** An authoritative server and a
recursor have different clients, exposure and failures. Trixie-security
carries Recursor 5.4.9-1~deb13u1, which fixes CVE-2026-73206 (DSA-6630-1).
If Keel needs a resolver, it is a separate appliance with its own note.

### 10. The failover of names

**DNS follows the pair. It does not choose the primary.** A name moves
from BR1 to BR2 when the pair moves its primary to BR2. The pair moves
by itself only in `cloud_advanced`, with 3 etcd voters (two nodes and
the witness of 0057). Section 11 makes the pair move for each failure of
service.

#### A. What the health check tests

| Level | The check | The failure that it allows |
| --- | --- | --- |
| (i) | `ifportup(443, ...)` | DNS sends users to a replica that is alive and read only. Through an edge, it proves only the edge. |
| (ii) | `ifurlup` on a page of the application | the same: a replica serves its pages too |
| (iii) | `ifurlup` on a Keel address that answers 200 only on the primary that accepts writes | none of the above |

**Keel uses level (iii).** It is the least-power level that cannot send
writes to a replica.

**The check address (to build).** Each node of a pair serves
`https://<name>/.well-known/keel/primary`. It answers 200 with the body
`keel-primary <token>` only when all of these are true at the time of
the request:

1. `/var/lib/keel/role` says `role=primary` for the VIP of the pair.
2. The VIP is on `wg0`.
3. The mark of the holder's doubt, `/var/lib/keel/vip/<vip>.unconfirmed`,
   is not there (keel#195).
4. The node is not fenced and did not release the VIP.
5. The database accepts writes: MariaDB `read_only` is off, or
   PostgreSQL is not in recovery.

Otherwise it answers 503. The role file alone is not enough. During the
holder's doubt, and on a holder that lags (keel#271), the role file
says `primary` while the database is read only.

Rules for the check address:

- **The token** is a random value per pair, made by the primary and
  shared with the replica (proposed). It is not the VIP, because the
  body is public.
- **It never redirects**, and nothing in front of it redirects. The
  PowerDNS checker follows redirects (`CURLOPT_FOLLOWLOCATION`, true in
  `pdns/minicurl.cc`). A redirect to another name resolves through public
  DNS, and can reach the other node.
- **It is served before Anubis**, in the front server of keel-web
  (`keel-front.d`). That this works is not verified.
- The LNMP page `/keel-check/` is not usable: it answers 200 on both
  nodes and is behind Anubis.

**How the check connects** (evidence section 2.2 and section 11). The
documentation says only that `ifurlup` "attempts an actual http(s)
connection to `url`" on each listed address. The code gives curl the
host of the URL, the port and the listed address (`CURLOPT_RESOLVE`).
Thus the check connects to the listed address, sends the host of the
URL as SNI and as `Host`, and does not verify the certificate.

**The answer comes from the node, never from an edge.** Only a node of
the pair writes the token, and only while it is the writable primary. If
an edge stays up and the node behind it is the replica, the check gets
503 from the replica, and the name leaves that address. An error page,
a maintenance page or a cache must never hold the token.

#### B. Who decides

| | Each DNS server alone | The pair writes the record | The pair publishes, each DNS server checks |
| --- | --- | --- | --- |
| Source of truth | what each server sees | the pair | the pair |
| Works when the sites are cut | yes | no: the update must reach the writer across the cut | yes |
| Needs a path from the node to DNS during the failure | no | yes | no |
| Two servers can disagree | for one check interval | for the replication lag | for one check interval |

**Keel uses the third way.** The pair publishes who is the primary
(section A). Each DNS server checks it by itself with a LUA record. The
record does not change at a failover. `keel` writes it once, when the
administrator turns on failover for a name.

**A DNS server with a wrong view.** A server that cannot reach the
primary, or that has no egress in one address family, sees no address
up. It answers SERVFAIL (section 7), and the resolver asks another
server. It never gives the replica as a second address.

**Partitions.** In `cloud_advanced`, a holder that is cut from the etcd
majority turns read only after 6 s (the holder's doubt). It loses the
VIP at 15 s. The other node claims after the lease of 20 s and GRACE.
Thus no moment has two nodes that answer 200. A short gap has none.

#### C. Fail-back

DNS has no rule of its own. An old primary rejoins as a replica (0049),
and its check address answers 503. The name returns to it only when the
pair moves its primary back. 0031 decides a fail-back of a healthy pair.
The operator chooses automatic or manual. The role returns only after a
full catch-up.

#### D. Where the DNS servers run, and the migration

- The servers follow section 4. The servers of a name never all depend
  on a site that the name protects.
- **Every server of a zone with LUA records is PowerDNS of the same
  series.** A server that is not PowerDNS serves the LUA record as data:
  the failover does not work, and the record content leaks.
- Each server checks and signs by itself, and keeps its answers through
  a cut of the sites.

**The migration of existing servers (later, a separate act that the
maintainer approves, not started).** Production servers are not
touched by this work. A migration from an existing PowerDNS server on
the generic PostgreSQL back end checks, in this order:

1. The PowerDNS and PostgreSQL versions of the source. A dump with
   `pg_dump` and a restore into the PostgreSQL of trixie works across
   major versions. A physical copy does not.
2. That the schema is the upstream `gpgsql` schema of its version, with
   no local change.
3. That the DNSSEC keys are rows of `cryptokeys`, so that they come with
   the dump and the DS records at the parents do not change.
4. The zone kinds and the metadata (`PRESIGNED`, `NSEC3PARAM`,
   `SOA-EDIT`, TSIG keys), and whether the source uses catalog zones or
   views.
5. A copy into a Keel DNS writer on the testing channel. Then a
   comparison of the answers of each zone, signed and unsigned. Only
   then a change of the NS records, one server at a time.

#### E. Which names get failover

Failover is per name and opt-in. The administrator turns it on in a
confconsole menu on the DNS writer, which calls `keel`. The renderer
writes, for one domain and one pair, the apex and `www`, each with an A
record and an AAAA record. Each is a LUA record with `ifurlup`, the
addresses of the pair for that family in one set, `selector='all'`, and
the TTL of 60 s.

An example of the content, with documentation addresses and a
placeholder token:

```
clientdomain.com. 60 IN LUA AAAA ";local r = ifurlup('https://clientdomain.com/.well-known/keel/primary', {'2001:db8:1::10', '2001:db8:2::10'}, {stringmatch='keel-primary TOKEN', selector='all', backupSelector='empty', failOnIncompleteCheck='true'}) if #r == 0 then error('no primary') end return r"
```

That this Lua form works (the type of `r`, the SERVFAIL) is to be
tested.

**Both families list both sites, or the family has no record.** If the
AAAA record lists BR1 only and the A record lists BR2 only, the A record
has the replica as its only candidate.

#### F. What already exists

The first round decided the appliance, the TSIG keys and LUA records
with health checks. Release A3 proved the pair from the inside: database
failover, the VIP and file replication. On 2026-11-10 the maintainer
called the entry by name of a `cloud_advanced` pair "the final test" and
put it on standby. This round is that test.

#### G. Promise level (0095)

Keel DNS starts at the **laboratory** level: the testing channel only,
after the real tests and commissioning (0075) on BR1 and BR2 pass. The
**product** level also needs:

1. `pdns` in the automatic update pipeline of 0096.
2. An upgrade test of 0090 for the `keel-dns` layer.
3. The check address and the pair rule of section 11 in a stable `keel`
   and `keel-web`.
4. The real tests passed at each netem profile of 0050.
5. One migration of a real name server done and observed.

#### H. The edge in front of the nodes, per address family

A site can have an edge in front of the nodes, and the edge can differ
per address family. The design works per family:

1. **One record per family.** A failover name has an A record and an
   AAAA record. Their targets can differ: an edge address in one family
   and a node address in the other. Each record checks only the
   addresses of its own family, because PowerDNS refuses an IPv4
   address in an AAAA record.
2. **An edge that passes 443 in TCP by SNI.** The check reaches the node
   that the edge gives for the name. The edge does not see the path.
   This works with no change to the edge.
3. **An edge that ends TLS.** It must pass `/.well-known/keel/primary`
   to the node of its own site with the path, the `Host` header and the
   answer unchanged. It must not cache it, answer it itself or redirect
   it. Version 1 does not cover this case (section I).
4. **A TCP open on 443 of an edge proves only the edge.** Thus
   `ifportup` is not usable through an edge.
5. **The edge of the other site must be ready before a move.** The
   public address of BR2 in each family must already know the customer
   name and send 443 to the BR2 node. The certificate must be valid
   where TLS ends. This is configuration of the infrastructure, outside
   Keel. Keel gives it the list of failover names and the address of
   each node of the pair, from `keel` on the DNS writer.
6. **A failure of the edge** is a failure of service. The observers of
   section 11 check the address that DNS gives, on each family. The pair
   moves, and the name follows.
7. **Health checks of the edge.** An edge that sends traffic to the
   other site makes the switch faster for clients with the old address.
   This is a later item of the infrastructure. DNS failover is still
   necessary, because no traffic reaches an edge that is down.

#### I. The scope of version 1

The maintainer agreed on 2026-11-23, to confirm when the note is
accepted:

1. **Version 1 covers only names whose TLS ends on the node.** The check
   then proves the node with no change to an edge, and the certificate
   stays with the pair (section 12).
2. **Version 1 is only for `cloud_advanced` pairs.** Only these pairs
   move by themselves (section 11).

**Later, with what each needs:**

- **Names whose TLS ends on an edge.** The edge rule of section H, item
  3, a valid certificate on the edge of each site (outside Keel), and
  real test cases of their own.
- **`cloud_simple` pairs.** The replica does not move by itself, and a
  promote during a cut gives two writers. They need a move to
  `cloud_advanced` first (0057), or a separate decision.
- **`simple` installations.** There is one node, so there is nothing to
  fail over to.

#### J. Switch time (estimate, to be measured)

These are estimates from the code and the documentation. A real test
gives the numbers. The terms:

| Term | Estimate | Source |
| --- | --- | --- |
| Node down or site cut: the other node writable | about 25 s (measured 24.6 s on keel 0.23.68) | `evidence/2026-11-01-keel-0.23.68-mariadb-faults.md`, K2 |
| Failure of service (section 11): 3 failed checks and the next tick | 15 s to 20 s | section 11 |
| The promote: release, the wait for the lease (up to the TTL of 20 s), GRACE (19 s) when a lease was revoked, the writes back | up to about 50 s | `docs/vip.md`, `keel/mesh/vipetcd.py`, keel#169 |
| Each DNS server sees the new primary | one interval and the timeout, 5 s + 2 s | section 7 |
| The packet cache of PowerDNS (`cache-ttl` 20 s), if it holds LUA answers | 0 s to 20 s | not verified |
| The resolver cache | up to the TTL, 60 s | |
| The client: Chrome keeps an answer for at least 60 s, Java 30 s | up to 60 s | evidence section 4 |

Thus a failure of service gives an estimate of about 2 to 4 minutes for
most clients, and a node down less. About 2 % of resolvers keep an old
answer for longer (Moura et al., 2019).

#### K. The real test of the DNS part

No image of Keel DNS is released before this test passes. It follows
0053 and ships an evidence file. The real tests of section 11 pass
first.

**Machines.**

- 2 Keel nodes as a `cloud_advanced` pair, one on BR1 and one on BR2,
  with the etcd witness on BR3 (0057). An application with a write
  path, for example WordPress. TLS ends on the nodes.
- The four Keel DNS servers of section 4: one writer and three hot
  standbys, on at least 3 sites, at most 2 on one site.
- A signed test zone delegated from `keellinux.org` or `pop.coop`. No
  production zone and no production name server.
- A validating resolver (Unbound) behind netem at 250 ms ±25 ms with
  2 % loss, and a client that writes every second.
- **Precondition** (section H, item 5): the public address of BR2 in
  each family knows the test name and sends 443 to the BR2 node. The
  certificate there is valid.

**Cases.** For each case, measure two times at each DNS server, at the
resolver and at the client. The first is the time to the first answer
with BR2 only. The second is the time to the first write that succeeds.

1. Node down: stop the BR1 node.
2. Site cut: drop all traffic of the BR1 node, mesh and public.
3. Application down, node up.
4. Public path of the BR1 node down, mesh up.
5. Fail-back: BR1 comes back as a replica, and the name stays on BR2.
   Then the operator fails back, and the name returns to BR1.
6. The DNS servers cut from each other: each one answers alone and
   correctly.
7. A DNS server that cannot reach either node, and a DNS server with no
   egress in one family. Each answers SERVFAIL. The resolver gets the
   answer from another server.
8. A restart of `pdns` during a failure: SERVFAIL until the first
   results, then the right answer.
9. The apex and `www`, A and AAAA, each checked on its own family.
10. Through an edge that passes 443 by SNI: the check reaches the node,
    and gets 503 when that node is the replica.
11. An edge in front of BR1 stops: the pair moves, and the name follows.
12. DNSSEC through the switch: the validating resolver gets a `secure`
    answer from each server before, during and after cases 1 to 5.
13. A ZSK roll while one standby lags by more than 60 s: no `bogus`
    answer.
14. The import of the keys of a signed test zone: the DS record at the
    parent does not change, and the answers stay `secure`.
15. The gap of a move: how long all servers answer SERVFAIL, against
    `backupSelector='all'`.
16. The DNSSEC algorithm, NSEC or NSEC3, and the CPU cost of live
    signing: measured, then chosen.

**Done when** each case gives the expected answer and no case sends a
write to a read-only replica that returns OK.

### 11. A required change in the keel pair: it moves by itself for each failure of service

**The rule of the maintainer, 2026-11-23:** "NÃO PODE EXISTIR a
possibilidade de o par não trocar sozinho, isso é a definição de como o
Keel tem que trabalhar 100% das vezes que precisar trabalhar em modo
cloud avançado." (It must not be possible that the pair does not change
by itself. This is the definition of how Keel works, each time that it
works in `cloud_advanced`.)

**Approved.** The maintainer approved the mechanism below and its five
limits on 2026-11-23. The numbers 5 s, 3 checks and 10 minutes are
values to confirm in the real test.

**The requirement.** In `cloud_advanced`, each failure that makes the
service of the primary site unusable for users moves the pair by
itself. The name follows (section 10). This change is in `keel` and
comes before the DNS part.

#### What moves the pair today

Read in code, not tested unless the row says so (evidence section 9).
The only trigger is the etcd lease of the holder
(`keel/mesh/vipetcd.py`, `holding()`, `renew()` and `fail_over()`).

| Failure on the primary site | Moves by itself today |
| --- | --- |
| Node down | yes (tested on keel 0.23.68: writable on the other node after 24.6 s) |
| Site cut from both other sites | yes (tested on keel 0.23.68) |
| The VIP controller stops for good | yes |
| Database server down | no |
| Application down, node up | no |
| nginx or the web front down | no |
| Public path of the site down, mesh up | no |
| Disk full, or file system read only | no |
| Certificate missing or expired | no |

#### The mechanism (approved; the details marked proposed)

**1. A service check on each node of the pair.** `keel` runs it every
5 s on both nodes. It passes only when all of these are true:

- the database answers, and on the holder it accepts writes;
- nginx answers on 443 with the certificate of each name of the pair,
  and the certificate is valid for more than 7 days;
- the health URL of the application answers 200 through the front, with
  a fixed string (0041, a new field of the manifest);
- the disk has free space above a limit, and the data file systems are
  writable.

Each node writes its result, its count of failures in a row and its
replication position to its own etcd key, on its own lease. The replica
runs the same check against its own services, with the database read
only.

**2. Outside observers (proposed).** The observers of version 1 are not
DNS servers: the witness (0057) and one more observer on a different
network. Neither is on the network of BR1 or BR2. Each checks the public
check address of both nodes, on each address family, and writes the
result to etcd. The rule needs both observers to agree.

**3. The replica starts the move (proposed).** The replica moves the
pair by the existing promote path when all of these are true:

- the holder's service check failed 3 times in a row, **or** both
  observers failed to reach the holder 3 times in a row on one family,
  while they reached the replica on that family;
- the replica's own service check passed 3 times in a row;
- the replica is caught up. Its applied position is at or past the
  newest position record of the holder in etcd (keel#271,
  `/keel/<mesh id>/etcd/database/<vip>`). When the holder's database is
  down, that record is its last position before the stop. With
  synchronous commit (0031, 0054), each acknowledged write is already on
  the replica. During a fallback to asynchronous commit, which
  `keel database watch` alerts, the record can be ahead, and the move
  waits (limit 2). To be tested;
- the last move of this pair was more than 10 minutes ago, in either
  direction (a record in etcd).

The promote path asks the holder to release (`docs/vip.md`, "keel vip
promote"). The holder turns its database read only and drops the VIP.
The replica waits for the holder's lease to end, up to the TTL, then
claims at the next epoch. No acknowledged write is lost.

**What stops the old holder from claiming again.** It released the VIP
when asked, so it is marked released, not fenced (`docs/vip.md`). Its
controller claims only when the lease of the newest claim is gone
(`fail_over()`), and the lease of the new holder is alive. The new code
is: the service check and its etcd key, the observers, the trigger in
the replica, and the record of the last move. The path of a revoked
lease, which claims again at the next epoch, is not used.

**4. A move never goes to a node that fails the same check.** If the
replica fails the check, the holder stays.

#### Dangers, stated honestly

- **Flapping.** The 3 failures in a row and the 10 minutes between moves
  limit it. The rule moves the pair away from a failed holder, in either
  direction. It never moves a healthy pair only to return it to its
  first primary: that fail-back stays the choice of 0031.
- **A move to a replica that is behind.** It is refused: a lagging
  replica never takes writes (keel#271). The move waits until the
  replica is caught up.
- **A fault that both sites share.** A bad release, a full disk on both
  nodes, or an expired certificate on both makes both checks fail. Rule
  4 refuses the move.
- **A wrong outside view.** The two observers are on two networks that
  are not BR1's or BR2's, and the rule needs both.
- **A check that is wrong.** A health URL that fails while users are
  served moves the pair for nothing. Commissioning (0075) tests the URL.

#### What "100 %" means, and its limits (approved)

The rule moves the pair for each failure that the service check or the
observers see, when a healthy, caught-up replica and an etcd majority
exist. In these cases no automatic move is safe. They are the limits of
the rule, not exceptions for convenience:

1. **Both sites fail the check.** The holder stays.
2. **The replica is behind.** The move waits until it is caught up.
3. **No etcd majority.** No node can prove that it alone holds the VIP.
   The pair waits for the majority.
4. **A second failure less than 10 minutes after a move.** The pair
   stays on the node that it moved to.
5. **A failure that no check sees**, for example wrong content with a
   200 answer.

In each of these cases, the node stays as it is and sends an alert to
ntfy (0063) once, with the case number. The administrator can still run
`keel database promote`.

#### Real tests of the pair change

On a `cloud_advanced` pair, BR1 and BR2, with the witness on BR3, at the
netem profiles of 0050. For each case: the time to the first write on
BR2, and no acknowledged write lost.

1. Each "no" row of the table above: the pair moves.
2. Both nodes fail the check: the pair stays, and one alert goes out.
3. The replica is behind at the failure: the pair waits, then moves.
4. A check that fails and passes every 20 s: at most one move in 10
   minutes.
5. No etcd majority: no move.
6. One observer cut from both nodes: no move.
7. After each move, the old holder rejoins as a replica and does not
   claim again.

### 12. The certificate on the replica (proposed: a decided prerequisite)

The replica's service check needs a valid certificate for each name of
the pair. Keel gets a certificate by ACME `http-01` only, and refuses
`dns-01` (`docs/apply.md` of keel, "tls.acme"). An `http-01` challenge
reaches only the node that DNS gives, so the replica cannot get its own
certificate before a move. Today nothing copies the certificate to the
replica. Without a certificate, rule 4 refuses every move.

| Way | How | Danger |
| --- | --- | --- |
| (a) a copy | the replica asks the primary for the certificate and its key on the members' channel, as it asks for the Anubis key (`keel.system.anubiskey`, `keel.mesh.vipserve.shared`); the channel answers only the other member of the pair, with TLS inside WireGuard | the private key is on both nodes; a copy can be old if the primary stops for a long time |
| (b) `dns-01` through Keel DNS with RFC 2136 | each node gets its own certificate from a TXT record | every pair then depends on Keel DNS, needs a TSIG key, and works only for zones on Keel DNS |

**Decision (proposed): way (a).** It works with any DNS and makes no
pair depend on Keel DNS. The replica holds a full copy of the data of
the pair already. What must be built:

1. A new shared secret on the members' channel: the certificate and its
   key for the names of the pair.
2. The replica asks again at each `keel database watch` run, and
   replaces its copy when the primary's certificate is newer and valid.
   The Anubis key is never replaced, but a certificate is renewed, so
   this rule differs.
3. The renewal job runs only on the primary. The role hook turns it on
   at a promote and off on a replica. After a move, the new primary
   renews by `http-01`, because DNS now gives its address.

**What must be tested:**

- A renewal on the primary reaches the replica.
- A certificate near its end on the replica makes its service check
  fail (the 7 days of section 11).
- After a move, the new primary renews.

## How it is carried out

**Work list, in order.** Nothing is started. Each item waits for the
maintainer to accept this note.

1. **The certificate on the replica** (section 12), in `Keel-Linux/keel`,
   with its tests.
2. **The check address** (section 10 A), in `Keel-Linux/keel` and
   `Keel-Linux/keel-web`: served before Anubis, never a redirect, the
   token per pair. First verify that `keel-front.d` serves it before
   Anubis.
3. **The observers** that are not DNS servers (section 11): the witness
   and one more on a different network.
4. **The pair change** of section 11 in `Keel-Linux/keel`: the service
   check, the trigger in the replica, the record of the last move, the
   limits and their alerts. Then its real tests, with an evidence file.
5. **The failover name** in the spec of Keel DNS and the renderer of its
   LUA records (section 10 E), in `Keel-Linux/keel`. The confconsole
   menu calls it (0094).
6. **The `pdns` 5.1.5-2 backport** for trixie, in the scope of 0096.
7. **The DNS servers** in `Keel-Linux/keel`. One PostgreSQL writer has 3
   asynchronous hot standbys over the mesh with TLS. Add the lag alert,
   the move of the writer by hand, and the key roll of section 6. The
   code of 0054 makes a pair. A writer with several standbys is to build
   on it.
8. **The appliance:** `keel-overlay-pdns` in `Keel-Linux/common`, then
   `Keel-Linux/keel-dns` on the `postgresql` layer, and
   `conf/image-ci` of `Keel-Linux/apt` (0061).
9. **The real test** of section 10 K, with its evidence file.
10. Commissioning (0075) and the testing channel (laboratory, 0095).
11. Later, as separate acts that the maintainer approves: the migration
    of existing name servers, and the product level.

## Risks

- **A new PowerDNS advisory** can open a gate again (section 1).
- **The 5.1 package is a Keel backport.** Debian security does not
  cover it. The pipeline of 0096 must follow each 5.1 release.
- **DNS failover is slow at its best.** About 2 % of resolvers keep an
  old answer after a change, and browsers keep an answer for 60 s. The
  times of section 10 J are estimates until the real test.
- **SERVFAIL in the gap of a move** can be kept by resolvers for up to
  5 minutes (section 7). The real test measures it.
- **The private DNSSEC keys are on four servers.** A server that is
  broken into gives the keys of each zone. The replication uses TLS, and
  the backup is encrypted (0037).
- **A key roll that goes faster than the replication and the caches**
  gives `bogus` answers. Each wait of section 6 is longer than their sum.
- **Way N is not tested yet.** If PowerDNS fails on a hot standby,
  section 3 falls back to way F.
- **The pair change of section 11 is new code in the most sensitive
  part of Keel.** It can move the pair for a fault that is not real. Its
  own real tests come first.
- **DNS is the first service whose failure takes other services down.**
  A zone whose servers are on one site is lost with that site. Section 4
  puts the servers on at least three sites.

## Open points

No question is open for the maintainer. Two things are open:

1. The acceptance of this note by the maintainer, with the items marked
   proposed.
2. The results of the real tests of sections 10 K and 11, and of the
   items marked "to be tested".

## What changed in the second round

- **Requirements:** the failover of names, DNSSEC with live signing,
  the takeover of the zones and keys of an existing PowerDNS server on a
  generic SQL back end, and a pair
  that moves by itself (approved).
- **Section 1:** the 5.1 line as a Keel backport, in place of 4.9 from
  trixie.
- **Sections 2 to 4:** the `postgresql` layer, and PostgreSQL streaming
  replication with one writer and three hot standbys, in place of
  `gsqlite3`, AXFR, catalog zones and SOA timers.
- **Section 5:** the TSIG keys replicate as rows, and
  `dnsupdate-require-tsig=yes`.
- **Section 6:** DNSSEC is required, with live signing on each server.
- **Section 7:** SERVFAIL when no address is up, and `minimumFailures`
  stays at 1.
- **Section 8:** the ports of PostgreSQL, and the lag check in place of
  the serial check.
- **Section 9:** PowerDNS-Admin and the Recursor facts corrected.
- **Sections 10 to 12, new:** the failover of names, the pair change, and
  the certificate on the replica.
- **Production facts** are not in this note. It states only general
  rules for an edge.

## What this amends

This note replaces the 0045 part of handbook#38. Where they differ, this
note decides. The 0044 part of handbook#38 is not changed.

- **0020:** DNS with a health check is an appliance, not a Keel Cloud
  piece. Failover in `cloud_advanced` happens on each failure of service
  (section 11), not only on the loss of a node.
- **0024, "Review notes":** the DNS successor for nodes behind NAT is
  Keel DNS, with RFC 2136 and TSIG at the VIP of the writer.
- **0028:** primary and replica read as the writer and the standbys of
  Keel DNS.
- **0029:** the public answers of Keel DNS are never behind the VIP.
  The VIP serves the control path on the mesh only.
- **0041:** the manifest gets a health URL for the application. Decision
  6 applies for the first time to a public port that is not Keel Web's:
  53, udp and tcp.
- **0049:** the replica can start a move by the promote path when the
  rule of section 11 holds.
- **0057:** the witness is also an outside observer.
- **0063:** the limits of section 11 and the replication lag send
  alerts.
- **0081 (proposed, handbook#163):** a failover name gives one writer
  per pair. It does not spread load over many nodes.
- **0031 and the decisions of 2026-11-01:** not changed. A lagging
  replica stops writes, and fail-back stays the choice of the operator.
