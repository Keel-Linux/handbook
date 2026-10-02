# 0046: Keel Cloud, version 1 scope

Date: 2026-10-02
Status: **proposed**. Nothing here is decided or implemented, no
repository is created and no service code is written until the maintainer
decides it. The questions he has to answer are under "Open questions",
each with a recommendation.

## What was asked

On 2026-10-02 the maintainer asked to start working on Keel Cloud. 0020
named it ("keel-cloud, a separate project": DNS, membership and key
exchange) and said it "starts with its own decision note"; this is that
note. It fixes what Keel Cloud is, what its first version does and does
not do, how it is built, what a node trusts it with, and the order in
which it is built. The same day the maintainer confirmed the order of the
public traffic mechanisms of 0044 (DNS with a health check first, edge
nodes with VRRP second, VRRP between Keel Web nodes last) and that Keel
DNS (0045) is authoritative; this note builds on both.

## Why a note, and why now (brief section 10)

Since 0020, three notes moved pieces away from Keel Cloud and onto the
nodes: membership and the registry to etcd (0025), discovery to the mesh
itself (0026), and the DNS server to an appliance any operator runs, Keel
DNS (0045). This note gives Keel Cloud a job again, so the brief's
three-part justification applies.

1. **Why the current approach is not enough on its own.** Without a
   service, the first contact is typed. 0026 asks for the address of one
   node and an entry secret; in cloud simple there is no etcd (0041), so
   the WireGuard public key and endpoint the primary generates (0028) are
   carried to the replica by hand. A node behind NAT whose address changes
   must already know where Keel DNS is to update its name (0045, question
   4). And a public DNS answer needs the operator to run two Keel DNS
   servers in two sites before the first name resolves.
2. **Whether it can be made to work.** It does work, and it stays: every
   one of those paths remains the standalone path, and nothing in this
   note removes or weakens it. Keel Cloud is never required (0020,
   "Decided").
3. **Why adding Keel Cloud is better.** It removes the copy and paste
   (one API key, offered at installation, instead of an address, a key and
   an endpoint per node), and it gives a public, health checked DNS answer
   to an operator who does not yet run two Keel DNS servers. Because it
   drives the same spec fields and the same Keel DNS records the operator
   would write by hand, it adds no second code path on the node.

## What Keel Cloud is

- **A separate project and service**, in the `keel-cloud` repository of
  the organisation (0020, "Decided, second round"), apart from `keel`.
  Brief section 2 keeps fleet tooling out of `keel`; Keel Cloud is fleet
  tooling, and it consumes Keel's spec rather than extending `keel`.
- **It coordinates Keel nodes that the operator owns.** It runs nothing on
  them and holds none of their data. It tells nodes about each other and
  publishes names for them.
- **Self-hostable.** The project runs one instance; any operator can run
  their own from the same packages ("The self-hosted path").
- **Never needed for a feature to work: standalone parity.** 0020's rule,
  "a standalone appliance has every feature an appliance in Keel Cloud
  has", is the test every Keel Cloud feature passes before it is built:

  | Keel Cloud does | Without Keel Cloud, the same result by |
  | --- | --- |
  | Membership and discovery: nodes find each other's WireGuard public keys and endpoints | the address of one node and the entry secret (0026); in cloud simple, the primary's key and endpoint carried to the replica (0028) |
  | DNS with a health check | the operator's own Keel DNS servers (0045), with the same LUA records |
  | Updates of a node's own name when its address changes | RFC 2136 with TSIG to the operator's Keel DNS, or the etcd feed (0045, question 4) |
  | A registry view of nodes and sites, with their Monit state | the status panel of 0020 and the site view over etcd of 0040 |
  | The election and failover | nothing to replace: they run on the nodes (0020), never in Keel Cloud |

  **No Hub-style hard dependency** (brief section 3, problem 7): a node
  that loses Keel Cloud keeps its mesh, its peers, its election and its
  sites. What stops is what Keel Cloud adds: new peers are no longer
  announced, and names Keel Cloud serves stop following failures until it
  is back (their last answers keep being served by the Keel DNS secondaries
  that hold them; see "Architecture").

## The API key

- **What it identifies: an account**, which is an operator or an
  organisation. Every node, set, zone and key belongs to one account.
  The key does not identify a node; a node is identified by its WireGuard
  public key once it registers.
- **How a node gets one.** The operator creates it in the Keel Cloud web
  interface or with its command line, or, on a self-hosted instance, with
  that instance's command line (`keel-cloud key create`). It is a long
  random token with a fixed prefix that says which instance format it is,
  so a key pasted into the wrong field is recognised. Keel Cloud stores a
  hash of it, never the key itself, and shows it once.
- **When it is asked for.** At installation, as an option, in every mode
  of 0028: the screen offers "Keel Cloud API key, or skip". Skip is the
  default and gives a standalone node (0020). The key can be added or
  removed later from the console; removing it leaves the node standalone
  with everything it already has.
- **What the node does with it.** It registers itself: its **WireGuard
  public key**, its **addresses** (public IPv6, public IPv4 when it has
  one, overlay address, WireGuard endpoint), its **site** label (0025),
  its **appliance** (0041) and its **role** (0020, 0044), and the set it
  joins. It then keeps that record current (a changed endpoint, an elected
  role) and reads the peers of its sets. All of it is public information
  about this node; nothing private leaves it.
- **Where it is stored.** A secret file, root's and mode 0600, referenced
  by the spec like every other secret, never inlined:

  ```yaml
  cloud:
    endpoint: https://cloud.example.org    # absent: the project's instance
    api_key:
      file: /etc/keel/secrets/keel_cloud_api_key
    set: shop                              # the set this node joins
  ```

  `cloud.api_key` takes `skip` or a secret reference, as `hub.api_key`
  already does in the spec; `keel diff` never compares it, and `spec
  render` masks it. The section is additive, so the spec stays `version:
  1`. The node piece that reads it is the `cloud` overlay below, whose
  state is `ask` in every mode (0041, decision 3).

## Version 1 services: the smallest useful set

### 1. Membership and discovery

Nodes find each other and exchange WireGuard public keys and endpoints
without copy and paste.

- A node registers (above) and asks to **join a set**, the group of nodes
  of one appliance or one mesh (0020, 0025). The join carries the entry
  secret proof of "The trust model"; Keel Cloud relays it and cannot forge
  it.
- The nodes already in the set read the request, check the proof, and add
  the new node to `network.overlay.wireguard.peers` in their own spec,
  which `apply` converges under 0018's window. The new node does the same
  for them. Each node writes only its own spec, which keeps 0013's rule.
- **Endpoints stay current.** A node whose address changes updates its
  record, and its peers update the endpoint in their spec. WireGuard's
  roaming covers most of it; the record covers a node that both peers
  lost.
- **Outbound only.** The node agent calls Keel Cloud; Keel Cloud never
  connects to a node. That is 0024's rule (tunnels from inside to
  outside) applied to the control channel, so a node behind NAT needs
  only outbound HTTPS.
- **After the mesh is up, etcd is the registry** (0025), in cloud
  advanced. Keel Cloud does not replace it: it is how the nodes find each
  other the first time and when one moves, and how a cloud simple pair,
  which has no etcd, exchanges keys.
- **Shared secrets never pass through Keel Cloud.** The replication
  password and the other `shared` secrets of 0041 (decision 8) go from the
  primary to the new node over the WireGuard tunnel, once it is up, as
  0028 has the primary generate them. Keel Cloud carries public keys and
  addresses only.

### 2. DNS with a health check

Keel Cloud serves health checked names through **Keel DNS zones** (0045),
using the same LUA records (`ifportup`, `ifurlup`) an operator would write
on their own Keel DNS.

- **A delegated zone.** The operator delegates a zone, or a subzone such
  as `svc.example.org`, to Keel Cloud's name servers at the parent. The
  delegation of a subzone rather than the apex is the recommendation (see
  "The trust model").
- **A Keel-provided subdomain**, for an operator with no zone yet: a name
  under a parent domain that Keel Cloud serves, one label per account.
  Which parent domain is a hosting question for the maintainer (0001),
  not answered here.
- **What it publishes.** For each set: the node names (AAAA, and A where a
  node has public IPv4), and the service names over them, as 0044 lays
  out: an AAAA list of every live Keel Web node, and an A record for the
  IPv4 front door of 0044's addendum or an A list where there are several
  IPv4 addresses. The records follow the registrations: a node that
  registers or changes address changes the address lists; liveness is the
  LUA checks' job, on every Keel DNS server, never the API's.
- **Hidden primary as an option.** An operator who runs their own Keel
  DNS can make it the primary of the zone and Keel Cloud's servers its
  secondaries by zone transfer, which 0045 already describes; Keel Cloud
  then serves names it cannot change.

### 3. The registry view

A read-only view of the account's nodes and sites, from etcd (0025) and
the Monit summaries of 0040: per node its site, appliance, role, elected
leader, `keel verify` health, and Monit's summary; per site the nodes in
it and the rule of 0025 that two replicas of the same data never share a
site, shown as satisfied or not.

- **The nodes push; Keel Cloud never joins the operator's etcd.** Each
  node agent sends a copy of its own registry key and its own Monit
  summary, the ones 0040 already writes. In cloud simple, which has no
  etcd, the agent sends the same summary directly.
- **Read only.** The view changes nothing on a node, like the status panel
  of 0020. Promotion, rejoin and every other action stay on the node they
  concern.

## What it is not, in version 1

- **No orchestration or scheduling of workloads.** Keel Cloud does not
  start, place, move or upgrade appliances. Roles are chosen at
  installation, on the node (0020); the election runs on the nodes (0020);
  upgrades are `apt upgrade` ordered by the nodes (0039).
- **No backup.** Backup is Keel Backup (0037), an appliance of its own.
- **No relay of traffic.** Keel Cloud carries control messages only; a
  node with no reachable endpoint uses a rendezvous point of 0024, run by
  the operator.
- **No remote shell, no remote configuration**: Keel Cloud never writes a
  node's spec. The node agent writes its own spec from what it reads.
- **No commercial content.** This note and the ones after it describe the
  architecture only.

## Architecture

**Keel Cloud runs as Keel appliances itself.** Each Keel Cloud site is
three pieces on Keel Core, in one or several machines:

| Piece | What it is | Decided in |
| --- | --- | --- |
| Keel DNS | the authoritative servers for the delegated zones and the Keel-provided subdomain, with LUA health checks | 0045 |
| etcd | Keel Cloud's own state: accounts, key hashes, sets, node records, zones, the pushed registry copies. Control plane only, a few writes a minute | 0025 |
| `keel-cloud-api` | the API service, behind Keel Web, on the loopback | this note |
| Keel Web | TLS termination, Coraza and Anubis for the web interface, CrowdSec | 0030, 0042 |

The etcd here is **Keel Cloud's**, not any operator's: no node ever joins
it, and Keel Cloud never joins a node's.

**The API writes zones through the Keel DNS primary's HTTP API on the
loopback**, as the etcd feed of 0045 (question 1) does, and zone transfer
carries them to the other sites. So the query path of public DNS does not
go through the API or etcd: if both are down, the Keel DNS servers keep
answering, and keep health checking, with the last records they have.

**High availability across at least three sites**: three etcd voters, one
per site (0025's odd quorum); a `keel-cloud-api` in each site, stateless,
reached through a name that Keel DNS health checks with `ifurlup` on the
API's health path; Keel DNS servers in each site, glued at the parent
(0045's rule for its own servers).

**IPv6 first, TLS only.** The API and the web interface listen on
`[::]:443` through Keel Web and are published with an AAAA record. IPv4 is
offered for IPv4-only nodes through an A record, served the way 0044
serves IPv4. There is no plain HTTP listener: certificates are issued by
DNS-01 through Keel Cloud's own Keel DNS (0042, 0044), so port 80 is not
needed even for ACME.

**The language: Python.** Proposed, with the reasons:

- `keel`, confconsole and inithooks are Python, so the people who maintain
  Keel can maintain Keel Cloud, and the node agent can share the spec
  library rather than reimplement it.
- Everything it needs is in Debian 13 (checked with `apt-cache policy` on
  trixie, 2026-10-02): `python3-aiohttp` 3.11.16 for the server and its
  client. It reaches etcd through etcd's own v3 JSON gateway over the
  loopback, so it needs no etcd client library (`python3-etcd3` 0.12.0
  exists in trixie but is no longer maintained upstream). No package is
  installed from PyPI, which keeps the rule 0039 and 0042 set (lexicon from
  PyPI at run time is a defect 0042 records, not a precedent).
- Go was considered: its etcd client is etcd's own, and a static binary is
  easy to ship. It was not chosen because Go builds in Debian need every
  dependency packaged or vendored, which Keel already carries for Anubis
  and Garage (0039) and should not add to for a small API service, and
  because it would be the only Go program the core maintainers write.

**Packaging (0039):** everything is a `.deb` in the Keel repository,
built from the `keel-cloud` repository.

| Package | Installed on | What it is |
| --- | --- | --- |
| `keel-cloud-api` | Keel Cloud's own machines | the API service, its systemd unit, its manifest (0041), the `keel-cloud` command line for accounts and keys |
| `keel-overlay-cloud` | every Keel image, state `ask` in each mode | the node agent: reads `cloud` from the spec, registers, joins, writes this node's peers into its own spec, pushes its registry copy |

The agent ships in the images, not only when a key is given, because 0013
does not split images by topology and 0041 decides what runs by state.
Disabled, it runs nothing.

## The trust model

- **Enrollment uses the entry secret of 0026.** Each set has an entry
  secret, generated by its first node and shown to the operator there.
  Joining a set needs a proof of it: an HMAC, keyed with the entry secret,
  over the joining node's WireGuard public key, the set and a timestamp.
  **Keel Cloud relays the proof and never holds the entry secret**, so it
  cannot produce a valid proof for a key of its own. The nodes already in
  the set check it. This is also the first answer to 0026's open point
  on the entry secret's scope: what it admits is one public key into one
  set.
- **Enrolled nodes exchange only public keys** and addresses.
- **The cloud never holds node private keys or application data.** The
  WireGuard private key is made on the node (keel-core#8) and never leaves
  it; `shared` secrets go over the tunnel between nodes; databases, files
  and certificates never pass through Keel Cloud.
- **A compromised Keel Cloud can:** redirect the DNS names it serves, and
  announce bogus peers or bogus endpoints for real peers. It cannot read
  traffic between nodes (WireGuard), cannot add a peer to a set without
  the entry secret, and cannot reach into a node (outbound only, no remote
  configuration).
- **Mitigations:**

  | Threat | Mitigation |
  | --- | --- |
  | A bogus peer announced | the entry secret proof above, checked by the nodes; **peers are pinned per set**: once a node has a peer's public key, Keel Cloud can change that peer's endpoint but never replace its key; a new key for a known node is a new peer |
  | A peer the operator did not intend | **an operator confirms new peers**: by default a new peer is held, and shown on the status panel of 0020, until the operator confirms it on one node of the set; automatic admission is a per-set choice (open question 3) |
  | A bogus endpoint for a real peer | WireGuard authenticates the peer by its key, so a wrong endpoint fails the handshake: traffic stops, it is not intercepted; the node keeps the last endpoint that worked and reports the change |
  | Redirected DNS | delegate a subzone, not the apex; a CAA record restricting issuance to the operator's ACME account (RFC 8657), so a redirect does not also obtain a certificate by DNS-01; the hidden primary option of service 2; DNSSEC when 0045 decides it |
  | A stolen API key | it admits nothing to a set without the entry secret; it can register bogus nodes in the account, which the operator sees and which no set accepts; the key is revoked in the web interface or command line, and keys are scoped (open question 2) |
  | Keel Cloud gone | standalone parity: nothing that works stops working |

## The self-hosted path

One operator can run their own Keel Cloud on **three Keel nodes in three
sites**, each with Keel DNS, etcd, Keel Web and `keel-cloud-api`, the same
packages as the project's instance and nothing more. Their nodes point at
it with `cloud.endpoint`. The self-hosted instance creates its accounts
and keys with `keel-cloud` on any of its nodes. Fewer than three sites is
allowed with the warning of 0028 (three nodes on one host), because etcd
cannot keep a majority with fewer voters in fewer places.

## Phased plan

Each phase is done only when its criterion holds on built packages and
images, not on a machine assembled by hand.

| Phase | Work | Done when |
| --- | --- | --- |
| A. API, membership and key exchange | `keel-cloud` repository; `keel-cloud-api` with accounts, API keys, node registration, sets, the entry secret proof and peer pinning, on one site first; `keel-overlay-cloud` on Core; the `cloud` section in the spec | two Core containers on different bridges, each given only the API key and the set's entry secret at installation, find each other through Keel Cloud, converge each other as WireGuard peers under 0018's window, and ping over the overlay; a third container with the API key but a wrong entry secret is refused by both; the shared secrets of 0041 reach the second node over the tunnel and never appear in Keel Cloud's etcd |
| B. DNS with a health check through Keel DNS | the API writes health checked records into Keel DNS (0045) for a delegated test zone and for the Keel-provided subdomain; node address changes follow | a test zone delegated to Keel Cloud's Keel DNS answers AAAA with both Keel Web nodes of a set; stopping one removes it within one check interval plus the TTL (0045's figure); a node that changes its address is answered at the new one without the operator touching DNS |
| C. Registry and Monit view | nodes push their registry copy and Monit summary; the web interface and the command line show the view per site | the three-container gate of Phase 5 shows, through Keel Cloud, each node's site, role, elected leader and Monit summary, and a stopped service on one node appears in the view within one push interval |
| HA | Keel Cloud itself across three sites: three etcd voters, three API instances, Keel DNS in each site | stopping any one Keel Cloud site leaves registration, joins and DNS answers working |

**Where it fits in the roadmap (tracker#46).** Keel Cloud comes **after
Keel DNS** (0045), which itself comes after Phase 3 (Keel Web), and
**before or alongside Phase 5** (mesh control plane):

- Phase A needs only Core with WireGuard (Phase 1) and is useful in cloud
  simple, which has no etcd, so it can start before Phase 5.
- Phase B needs Keel DNS's steps 1 to 3 (0045, "Order").
- Phase C reads the Monit summaries and the registry that Phase 5 builds,
  so it runs alongside Phase 5 and is done with it.

The roadmap issue is updated when this note is decided, not before.

## Open questions (for the maintainer)

- [ ] **1. The language.** Recommendation: **Python**, for the reasons
  under "Architecture": the same language as `keel` and confconsole,
  everything from Debian 13, no etcd client library needed.
- [ ] **2. The scope of an API key.** Recommendation: **two scopes**. An
  account key (web interface and command line) manages the account; an
  **enrollment key**, the one offered at installation and stored on
  nodes, can only register nodes, update their own records, read the
  peers of their sets and push their own registry copy. A key read off a
  node then cannot delete nodes, change zones or create keys.
- [ ] **3. Operator confirmation of new peers.** Recommendation:
  **confirmation required by default**, on any one node of the set, for
  every set; automatic admission (entry secret proof alone) as a per-set
  choice stored with the set's other choices (0020, "Decided, second
  round"), for an operator who installs many nodes and accepts the risk.
- [ ] **4. The entry secret's lifetime** (0026's open point).
  Recommendation: one secret per set, reusable until the operator rotates
  it on a node of the set; rotation does not affect peers already
  admitted, since they are pinned by key. A single-use token per joining
  node is the stricter option, at the cost of one more step per node.
- [ ] **5. The parent domain of the Keel-provided subdomain.**
  Recommendation: a subdomain of a domain decided under 0001, one label
  per account, chosen by the operator and checked for collisions. The
  name itself is the maintainer's (brief section 11, domains).
- [ ] **6. How the agent learns of changes.** Recommendation: **long
  polling over HTTPS**, outbound only, with a fallback to a plain poll
  every minute; no inbound connection and no persistent socket that a
  NAT would drop.
- [ ] **7. Whether the project's instance offers Keel DNS secondaries to
  operators who run their own primary** (0045, question 6, "Keel Cloud
  may offer one"). Recommendation: yes, as the hidden primary option of
  service 2, in Phase B; it is the same zone transfer, the other way
  round.
- [ ] **8. The repository.** Recommendation: create `keel-cloud` when this
  note is decided and Phase A starts, not before.

## What this amends

- **0020, "Where each piece lives"** (`keel-cloud`: DNS, membership and
  key exchange) and **0024, 0025, 0026**, which moved membership and
  discovery to the nodes: those notes stand. Keel Cloud's membership is a
  bootstrap and a directory over the same spec fields, the registry stays
  etcd's, and every path they decided remains the standalone path.
- **0045, "What this amends"** (Keel Cloud no longer owns the DNS piece):
  confirmed. Keel Cloud is an operator of Keel DNS, with the same records,
  not a second DNS implementation.
- **0026, "Review notes"** (the entry secret's lifetime and scope): its
  scope is proposed here (one public key into one set); the lifetime is
  open question 4.
- **The spec** gains a `cloud` section beside `hub`, additive under
  `version: 1`.
