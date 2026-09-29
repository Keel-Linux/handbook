# 0020: Replicated appliances, and what Keel Cloud does for them

Date: 2026-09-29
Status: **proposed**. The direction was set by the maintainer on
2026-09-29 and is listed under "Decided"; how the pieces are split between
the appliance and a separate project is this note's proposal, and the
questions at the end are open. Extends decision 0013, which already draws
the line for databases: each node configures itself, and nothing in this
codebase decides for other nodes.

## What was asked for

An appliance people depend on, a WordPress or an Odoo, served by more than
one machine: a name that keeps answering when a machine is lost, the
database replicated, and the files the application writes copied between
the machines over a private WireGuard network. A Keel Cloud service, a
future project of its own, highly available and distributed, keeps the DNS
entry pointing at a machine that is alive, in the spirit of TurnKey's
HubDNS.

## Decided 2026-09-29

- **A standalone appliance has every feature an appliance in Keel Cloud
  has.** Keel Cloud coordinates and automates; it is never required. The
  brief lists the TurnKey Hub as a hard dependency to remove (problem 7), and
  this must not recreate one. An API key for Keel Cloud is an option offered
  at installation, never a precondition.
- **The role is chosen at installation, by hand, on each LXC or VM:**
  standalone, primary or standby. Nothing assigns roles from outside. This
  is the console flow 0013 already decided for databases, widened to the
  whole appliance.
- **One primary and standby replicas.** One machine takes writes; the others
  follow it and can be promoted. Not active-active: with two writers, files
  synchronised both ways conflict, and an Odoo filestore must move together
  with its database.
- **At least three nodes for automatic failover, to avoid split brain.**
  With two, neither can tell a dead peer from a broken link between them,
  and both would promote. With three, a node acts only with a majority.
  Fewer than three stays supported, with promotion by hand, as 0013 says.
- **DNS with a health check, in the style of HubDNS,** is the Keel Cloud
  service that sends visitors to the current primary.

## Where each piece lives

The brief keeps fleet orchestration out of this codebase (section 2). The
split below keeps that line: every piece inside the appliance configures the
machine it runs on, and every piece that decides for several machines is a
separate project that consumes Keel's spec.

| Piece | Where | What it does |
| --- | --- | --- |
| The role | the spec, set at installation (inithooks, confconsole) | `standalone`, `primary` or `standby`; `keel inspect` reports what the machine is actually doing, `keel diff` the difference |
| WireGuard overlay | the spec, converged by `apply` (0018 owns the interface) | this node's interface and its declared peers; the key pair generated on first boot, never shipped in an image (keel-core#8) |
| Database replication | 0013, phase 3 | the database follows the appliance's role |
| Files | the stack layer, from the mutable state map (brief 4.2) | one way, primary to standbys, over WireGuard |
| Health | `keel verify` | the signal everything else reads |
| Promotion | an explicit command on the standby | database and files promoted together, never one without the other |
| Election | a separate project, running on the nodes | a majority of three decides who is primary and triggers the promotion |
| DNS, membership, key exchange | Keel Cloud, a separate project | points the name at the primary, lets nodes find each other, distributes WireGuard public keys |

The election runs **on the nodes, not in Keel Cloud**. That is what keeps
the first decision true: three standalone appliances that were given each
other's addresses by hand elect and fail over without any service outside
them. Keel Cloud adds the parts that cannot live on the nodes: a public DNS
answer, and discovery so the operator does not copy keys by hand.

## What Debian 13 gives us

Measured with `apt-cache policy` on trixie, 2026-09-29.

| Package | Version | For |
| --- | --- | --- |
| wireguard-tools | 1.0.20210914-3 | the overlay (the module is in the kernel) |
| lsyncd | 2.2.3-1 | watching the file tree and pushing changes |
| rsync | 3.5.0+ds1-0+deb13u1 | the copy lsyncd drives |
| etcd-server | 3.5.16-4 | a majority store for the election |
| patroni | 4.0.7-3~deb13u1 | PostgreSQL election and promotion over etcd |
| keepalived | 1:2.3.3-1 | not proposed: a floating address needs a shared link layer, which nodes in different places do not have |
| syncthing | 1.29.5 | not proposed: made for syncing both ways, which the one-writer model does not want |

So every piece can be rebuilt from the archive, which keeps the sovereignty
claim of 0013. Whether the election is etcd for every appliance, or Patroni
for PostgreSQL and something else for MariaDB and the files, is open below.

## The hard parts, planned for before code

1. **Fencing.** A majority prevents two elections, not two writers: a
   primary cut off from the other two keeps accepting writes unless it stops
   itself. A primary that loses the majority must turn read-only on its own,
   within a bound shorter than the election delay. Without this, three nodes
   do not prevent split brain; they only make it rarer.
2. **What is lost at failover.** Database replication and the file copy are
   both asynchronous. Whatever the primary accepted in the last seconds
   before it died may not be on the standby. The console and the docs state
   this as a number measured in the gate, not as "high availability".
3. **Database and files promote together.** A standby promoted with the
   database but not the file tree serves pages whose uploads are missing.
   Promotion is one operation over both, or it refuses.
4. **The old primary coming back.** It must rejoin as a standby, which means
   replacing its data with a copy of the new primary. 0013 makes that an
   explicit, confirmed act. Automatic rejoin would break that rule, so it
   needs its own decision.
5. **DNS is not instant.** With a low TTL and a health check, clients follow
   a failover in one to five minutes; some resolvers ignore low TTLs. This is
   stated, not hidden.
6. **Tested with three machines.** Three containers on the build host's
   bridge: write on the primary, stop it, watch a standby win the election
   and serve, bring the old primary back as a standby. Then cut one node off
   the overlay and check it turns read-only. 0013 phase 4 already needs a
   three-container gate; this shares it. Untested, none of it ships.

## Order

Nothing here starts before the network field of keel#35 (0018) is done. Then:

1. 0013 phases 2 and 3: the role read, then primary and replica for the
   databases, promotion by hand. Useful alone.
2. The WireGuard overlay in the spec, converged under 0018's window.
3. The one-way file copy from the mutable state map, and promotion of
   database and files together, still by hand.
4. The election on three nodes, with fencing, in the three-container gate.
5. Keel Cloud as its own project: DNS with a health check, membership, key
   exchange. It starts with its own decision note.

Steps 1 to 3 give a standalone operator a warm standby they promote by hand;
step 4 makes it automatic; step 5 removes the manual DNS and key work.

## Open for the maintainer

- Where this sits against the roadmap's phase 3, the orchestrated upgrade
  (WordPress first). The proposal is to keep phase 3 first, since an upgrade
  of a replicated set needs the upgrade path of one machine to exist.
- The election mechanism: one etcd-based election for the whole appliance,
  or Patroni for PostgreSQL alone and something to be chosen for MariaDB.
- Whether the old primary may rejoin by itself (hard part 4), or only by an
  operator's confirmed act, as 0013 has it today.
- The name of the separate election project, and whether it lives in the
  Keel-Linux organisation beside Keel Cloud.
