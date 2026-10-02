# 0044: Keel Web in the cloud

Date: 2026-10-02
Status: **decided by the maintainer on 2026-10-02** for the points under
"Decision": how public traffic reaches Keel Web in the cloud modes of 0028,
what balances load in front of applications and in front of Keel Web
itself, and that Keel Web gets a role and replicated configuration. The
details he did not decide are under "Open questions", each with a
recommendation. Nothing here is implemented.

## What was asked

0042 made Keel Web serve declared sites on one machine, with upstreams that
may be other nodes of the mesh. In a cloud mode (0028) there is more than
one Keel Web node, and three questions follow: how a visitor on the public
Internet reaches a live Keel Web node, what spreads load across the Keel
Web nodes themselves, and how those nodes stay configured alike.

## Decision

### 1. Public traffic to Keel Web in the cloud modes

Four mechanisms, ranked.

1. **Primary: DNS with a health check**, as 0020 already says, with a low
   TTL to shorten failover. The authoritative server answers only with the
   addresses of live Keel Web nodes; the server is Keel DNS (0045). The
   limit is stated, not hidden, as 0020's hard part 5 does: some resolvers
   and clients ignore a low TTL and keep a dead address for minutes, so a
   failover reaches most visitors within one to five minutes, not all of
   them at once.
2. **Second: an edge node.** A rendezvous point of 0024, which has a real
   edge and a fixed address, receives public traffic and forwards it over
   the mesh to the live Keel Web nodes. Its own redundancy is VRRP between
   edge nodes: two or more edge nodes in one datacenter share a network,
   which is the condition a floating address needs, so that is where VRRP
   fits. The edge is what serves a Keel Web node that has no public address
   of its own (behind NAT, or IPv4-only behind a NAT64 rendezvous point),
   and it covers the clients that ignore a low TTL, because the address
   they cached does not move.
3. **Low priority: VRRP with a floating public address between Keel Web
   nodes themselves.** A floating public IPv4 address is unrealistic,
   because IPv4 addresses are scarce and a provider rarely routes a spare
   one between machines; IPv6 is the realistic case. It also needs the
   nodes on the same physical network, which a cloud oriented Keel, with
   nodes in different sites (0025), usually does not have. It is not
   built before 1 and 2.
4. **The WireGuard VIP of 0029 is mesh internal and never faces the
   public.** It is a route on the overlay (`AllowedIPs`), reachable only
   from mesh peers, and it stays for database appliances (0041). It is not
   how a visitor reaches Keel Web.

### 2. Load balancing

| In front of | Mechanism | Decided in |
| --- | --- | --- |
| Applications | Keel Web's upstream groups: several servers, loopback or mesh addresses of other nodes, `backup` and `max_fails` passive failover, Monit active checks that alert | 0042, decision 6 |
| The Keel Web nodes themselves | DNS with a health check (Keel DNS, 0045), plus VRRP between the edge nodes, which forward to the live Keel Web nodes | this note |

### 3. Keel Web has a role in the cloud modes

A Keel Web node in a cloud mode has a role, as the database has primary and
replica (0013, 0020): **active and standby**, or **N active**. The role is
chosen at installation, on the node, as every role is (0020, "Decided"),
and is shown on the status panel of 0020.

**The configuration of the Keel Web nodes replicates across them over the
mesh**: the sites of 0042 and their certificates. The proposed mechanism,
whose details are open questions below:

- **The spec's `web` section is the source of truth, and each node applies
  it.** The sites, the upstreams, `web.real_ip` and `web.logs`, and the
  list of named certificates (`tls.acme.certificates`), are the same on
  every Keel Web node of a set. Each node renders its own Nginx from them
  with `keel spec apply --system`, test first and keeping the old files on
  failure (0042, decision 10). No node writes another node's files, which
  keeps 0013's rule that each machine configures only itself.
- **Certificates are shared through the shared secret policy of 0041**
  (decision 8: `shared`, every node of a set holds the same value). One
  node issues and renews each named certificate; the others receive the
  certificate and its private key over the mesh, install them where
  dehydrated would, and run `deploy.d` (0042, "Renewal reloads Nginx").
  0041 already treats Anubis's key this way, so that a failover does not
  make every visitor solve the challenge again; a certificate follows the
  same rule.

## How the edge forwards (proposed)

The edge reuses 0042 rather than adding a component. It is Keel Web
running only `tls-passthrough` sites: port 443 is read for its SNI name and
passed intact, with the PROXY protocol, to an upstream group that lists the
mesh addresses of the Keel Web nodes, with `max_fails` and `fail_timeout`
doing the passive failover. Port 80 forwards the ACME challenge path and
redirects the rest, as 0042 already does for a passthrough site.

```yaml
# on an edge node
web:
  upstreams:
    - name: web-nodes
      servers:
        - {address: "fd4b:7c1e:30a2::11"}
        - {address: "fd4b:7c1e:30a2::12"}
      max_fails: 2
      fail_timeout: 10s
      check: {type: tcp}
  sites:
    - name: shop
      mode: tls-passthrough
      names: [shop.example.org]
      to: {upstream: web-nodes, port: 443}
      proxy_protocol: true
```

```yaml
# on each Keel Web node behind it
web:
  real_ip:
    source: proxy_protocol
    trusted: ["fd4b:7c1e:30a2::1/128", "fd4b:7c1e:30a2::2/128"]  # the edge nodes
```

Why this shape: TLS ends on the Keel Web nodes, so the edge holds no
certificate and no private key, and Coraza, Anubis and CrowdSec see the
real client address through PROXY (0042, "Real client IP"). keepalived
holds the floating address between the edge nodes.

## What Debian 13 gives us

Checked with `apt-cache policy` on trixie, 2026-10-02.

| Package | Version | For |
| --- | --- | --- |
| nginx | 1.26.3-3+deb13u9 | the Keel Web nodes, and the edge's stream front (0042) |
| keepalived | 1:2.3.3-1 | VRRP between edge nodes only |
| wireguard-tools | 1.0.20210914-3 | the mesh the edge forwards over (0024) |

## Open questions (for the maintainer)

- [ ] **Which role by default.** Recommendation: **N active** in both cloud
  modes. A Keel Web node holds no application data, only its rendered
  configuration, so two active nodes cannot conflict the way two database
  writers do, and DNS and the edge already spread load across all live
  nodes. **Active and standby** stays as the operator's choice, for a set
  where the application behind it must see one entry point at a time; in
  that case Keel DNS answers with the standby only while the active is
  down (0045, an ordered `ifurlup` list).
- [ ] **The field in the spec.** 0020 refused a second role field that
  could disagree with `database.server.role`. A Keel Web appliance has no
  database, so it needs its own. Recommendation: `web.cluster.mode`
  (`n_active` or `active_standby`, shared by the set) and
  `web.cluster.role` (`active` or `standby`, this node's), present only in
  a cloud mode. On an appliance that has both a database and Keel Web,
  the web role follows the elected database role (0020), and
  `web.cluster.role` is not written.
- [ ] **How the `web` section reaches the other nodes.** Recommendation:
  in **cloud advanced**, the section is stored in the etcd registry (0025)
  by the node where it is edited, and every Keel Web node watches it and
  applies; a node whose `nginx -t` fails keeps its previous files and
  reports the failure to etcd and the status panel. In **cloud simple**,
  where no etcd runs (0041, "Resolved"), the standby or the second active
  pulls the section from the node it was installed from, over the mesh, on
  a timer, as 0020 has replicas pull files: the first node authorizes, it
  does not enumerate (0013).
- [ ] **Which node issues certificates.** Recommendation: one issuer per
  set, the active in active and standby, and in N active the node elected
  in etcd (cloud advanced) or the first node installed (cloud simple).
  Prefer DNS-01, answered through Keel DNS by an RFC 2136 update (0045),
  so issuance does not depend on which node a challenge request lands on;
  HTTP-01 stays possible only if every node serves the same challenge
  directory, which this note does not propose.
- [ ] **Edge node as Keel Web, or its own appliance.** Recommendation: Keel
  Web with only passthrough sites plus a `vrrp` overlay (keepalived),
  enabled only on a node marked as a rendezvous point. A separate appliance
  would duplicate 0042's stream front.
- [ ] **Health check path for DNS.** Nginx's `/keel-health` answers on the
  loopback only (0041). Keel DNS checks from outside the node.
  Recommendation: Keel DNS checks port 443 by default (`ifportup`), and a
  site may name a public health path for `ifurlup`; `/keel-health` stays
  loopback.

## What this amends

- **0020, "Decided"** (DNS with a health check is the Keel Cloud service
  that sends visitors to the current primary): confirmed as the primary
  mechanism for Keel Web, with the edge node as the second. The service is
  now an appliance, Keel DNS (0045), which a standalone operator can run
  without Keel Cloud, keeping 0020's standalone parity.
- **0020, "What Debian 13 gives us"** (keepalived not used, because a
  floating address needs a shared link layer): the reasoning stands for
  nodes in different places, and keepalived is now used where the link
  layer is shared, between edge nodes in one datacenter.
- **0020, "One role, in one vocabulary"**: an appliance that has a database
  keeps one role, the database's. Keel Web alone has none, so it gets its
  own (open question above).
- **0024, rendezvous points**: they gain a second job. Besides translating
  for IPv4-only nodes, a rendezvous point may be an edge node that receives
  public traffic and forwards it over the mesh.
- **0028, cloud modes**: the modes describe the database and the files;
  a Keel Web node in a cloud mode now also has a role chosen at
  installation, and its `web` configuration is replicated across the set.
- **0029**: the WireGuard VIP is restated as mesh internal and never
  public; it stays for database appliances only (0041), and public clients
  reach Keel Web through DNS and the edge, not through the VIP.
