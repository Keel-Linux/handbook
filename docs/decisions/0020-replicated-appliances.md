# 0020: Replicated appliances, and what Keel Cloud does for them

Date: 2026-09-29
Status: **proposed**. The direction was set by the maintainer on
2026-09-29 and is listed under "Decided". How the pieces are split between
the appliance and separate projects is this note's proposal, and the
questions at the end are open. It extends decision 0013, and it would amend
two of its lines and one of the brief's, which the maintainer has to accept
explicitly (brief section 11): see "What this changes in 0013 and the brief".

## What was asked for

An appliance people depend on, a WordPress or an Odoo, served by more than
one machine: a name that keeps answering when a machine is lost, the
database replicated, and the files the application writes copied between
the machines over a private WireGuard network. A Keel Cloud service, a
future project of its own, highly available and distributed, keeps the DNS
entry pointing at a machine that is alive. It is in the spirit of TurnKey's
HubDNS, which only updates a name to a machine's address; the health check
is new.

## Decided 2026-09-29

- **A standalone appliance has every feature an appliance in Keel Cloud
  has.** Keel Cloud coordinates and automates; it is never required. The
  brief lists the TurnKey Hub as a hard dependency to remove (problem 7), and
  this must not recreate one. An API key for Keel Cloud is an option offered
  at installation, never a precondition.
- **The role is chosen at installation, by hand, on each LXC or VM:**
  standalone, primary or replica. Nothing assigns roles at installation from
  outside. This is the console flow 0013 already decided for databases,
  widened to the whole appliance.
- **One primary and replicas on standby.** One machine takes writes; the
  others follow it and can be promoted. Not active-active: with two writers,
  files synchronised both ways conflict, and an Odoo filestore must move
  together with its database.
- **At least three nodes for automatic failover, to avoid split brain.**
  With two, neither can tell a dead peer from a broken link between them,
  and both would promote. With three, a node acts only with a majority.
  Fewer than three stays supported, with promotion by hand, as 0013 says.
- **DNS with a health check** is the Keel Cloud service that sends visitors
  to the current primary.

## One role, in one vocabulary

The spec already has `database.server.role` with `standalone`, `primary` and
`replica` (decision 0013, docs/spec.md in keel). The appliance does not get a
second role field that could disagree with it: the database's role is the
appliance's role, and the file copy and the overlay follow it. The words are
0013's, `replica` and not `standby`, following the precedent of 0009.

**The role in the spec is the one chosen at installation. Once an election
runs, the current role is runtime state.** After a failover the old
primary's spec still says `primary`. If `apply` converged that field, a
returning old primary would take writes again and create the split brain the
election exists to prevent. So on a machine where an election is configured,
`inspect` reports the elected role, `diff` shows the difference from the
spec as information and not as drift to repair, and `apply` never converges
the role. On a machine without an election, 0013's rule stands: a promotion
by hand is drift, and `apply` refuses to silently demote.

Everything that depends on the role follows **the elected role**, not the
spec's: the source a replica pulls files from, whether the primary's rsync
module is open, the pull timer, and whether the web tier is read-only.
`apply` leaves all of them to the election. Otherwise a replica still
pulling from the old primary's address, where that machine is still
reachable, would roll back the new primary's files, or with `--delete` erase
its uploads. Demotion closes the rsync module before anything else.

## Where each piece lives

The brief keeps fleet orchestration out of this codebase (section 2). The
split below keeps that line for the keel repository: every piece in it
configures the machine it runs on. The piece that decides for several
machines is a separate project that consumes Keel's spec.

| Piece | Where | What it does |
| --- | --- | --- |
| The role | the spec, set at installation (inithooks, confconsole) | `database.server.role`, read by `keel inspect`, compared by `keel diff` |
| WireGuard overlay | the spec, converged by `apply` (0018 owns the interface, `/etc/wireguard/`) | this node's interface and its declared peers; the key pair generated on first boot, never shipped in an image (keel-core#8) |
| Database replication | 0013, phase 3 | the database follows the role |
| Files | the stack layer, from the mutable state map (brief 4.2) | copied one way, pulled by each replica from the primary over WireGuard |
| Health | `keel verify` | the signal everything else reads |
| Promotion | `keel database promote`, widened | the database and the file tree promoted together, or neither |
| Election | a separate project, running on the nodes | a majority of three decides who is primary, promotes it, and fences the loser |
| DNS, membership, key exchange | Keel Cloud, a separate project | points the name at the primary, lets nodes find each other, distributes WireGuard public keys |

**The replicas pull the files; the primary does not push.** 0013 decided that
a primary authorizes its replicas and does not enumerate them ("A primary
authorizes, it does not enumerate"). A pushing tool like lsyncd would need
the list of replicas on the primary. So each replica runs rsync from the
primary on a short timer. The primary holds only the authorization: the
WireGuard peers it accepts and a read-only rsync module. The cost is a lag
of the timer's period instead of lsyncd's near-immediate push, which is
stated with the other losses below.

**The election runs on the nodes, not in Keel Cloud.** That is what keeps
the first decision true: three standalone appliances that were given each
other's addresses by hand elect and fail over without any service outside
them. So the election's package ships in Keel images, or in a layer on top
of them, even though its code lives in its own repository. Keel Cloud adds
what cannot live on the nodes: a public DNS answer, and discovery so the
operator does not copy keys by hand.

**Who confirms an overlay change.** The WireGuard interface is converged
under 0018's window, so a change to it needs `keel network confirm` over
the new configuration. By hand, the operator confirms from a new session.
With Keel Cloud, its agent confirms once it reaches the node again over the
overlay. Without either, the change reverts, as 0018 intends.

## What Debian 13 gives us

Measured with `apt-cache policy` on trixie, 2026-09-29.

| Package | Version | For |
| --- | --- | --- |
| wireguard-tools | 1.0.20210914-3 | the overlay; the module is in the kernel, and in a container the host loads it (0018) |
| rsync | 3.5.0+ds1-0+deb13u1 | the replicas' pull of the file tree |
| patroni | 4.0.7-3~deb13u1 | PostgreSQL election, promotion and demotion |
| python3-pysyncobj | 0.3.14-2 | Patroni's built-in Raft, a majority without a separate store |
| etcd-server | 3.5.16-4 | a majority store, if one election covers every engine |
| lsyncd | 2.2.3-1+b1 | not proposed: it pushes, which needs the primary to list its replicas |
| syncthing | 1.29.5~ds1-2 | not proposed: made for syncing both ways, which one writer does not want |
| keepalived | 1:2.3.3-1 | not proposed: a floating address needs a shared link layer, which nodes in different places do not have |

So every piece can be rebuilt from the archive, which keeps the sovereignty
claim of 0013.

## The hard parts, planned for before code

1. **Fencing.** A majority prevents two elections, not two writers. A
   primary cut off from the other two keeps accepting writes unless it stops
   itself. The mechanism: the primary holds a lease from the majority, and
   when it cannot renew it, it demotes itself before the lease expires, and
   the others wait for expiry before electing. Demoting covers the database
   **and** the web tier, which turns read-only, because uploads would
   otherwise keep landing on the fenced machine's disk while DNS still points
   at it (hard part 5). Patroni makes this safe with a hardware or softdog
   watchdog that reboots a node which failed to demote in time. An LXC
   container has no `/dev/watchdog`, so in a container the guarantee rests on
   the process demoting itself on time, and the note says so rather than
   claiming more. A VM can have the watchdog.
2. **What is lost at failover.** The database replication and the file pull
   are both asynchronous. Whatever the primary accepted in the last seconds
   before it died may not be on the replica, and not by the same amount: an
   upload can be recorded in the database without its file, or the file be
   there without its row. The console and the docs state this as a window
   measured in the gate, not as "high availability".
3. **The database and the files promote together.** A replica promoted with
   its database but not its file tree serves pages whose uploads are
   missing. Promotion stops the pull, promotes the database, and opens the
   tree for writes as one operation, or refuses.
4. **The old primary coming back.** It must rejoin as a replica, which means
   replacing its data with a copy of the new primary. 0013 makes that an
   explicit, confirmed act. Automatic rejoin would break that rule, so it
   needs its own decision.
5. **DNS is not instant.** With a low TTL and a health check, clients follow
   a failover in one to five minutes, and some resolvers ignore low TTLs.
   This is stated, not hidden.
6. **Tested with three machines.** 0013 phase 4 needed a three-container
   gate and was deferred, so the gate does not exist: this work builds it.
   Three containers on the build host's bridge. Write on the primary, stop
   it, watch a replica win the election and serve, and bring the old primary
   back as a replica. Then cut one node off the overlay and check that it
   turns read-only, database and web tier both. Untested, none of it ships.

## What this changes in 0013 and the brief

Accepted as proposed, this note amends three lines. The maintainer has to
say yes to each, because they move the brief's boundary:

- 0013 says "watching for failure, moving that role around" is an
  orchestrator "we are not writing here". The election does exactly that.
  The amendment: it is written, in its own repository, and its package ships
  on the appliance, because standalone parity requires it.
- 0013 says the console must state there is no automatic failover. The
  amendment: that stays true for fewer than three nodes, and for three with
  an election the console states what the failover guarantees and what it
  loses (hard parts 1 and 2).
- Brief section 2 keeps fleet orchestration out of this codebase. The
  amendment: it stays out of the keel repository, and an election among the
  nodes of one appliance is not fleet orchestration. Keel Cloud, which
  manages many appliances, remains outside.

## Order

Nothing here starts before the network field of keel#35 (0018) is done. Then:

1. 0013 phases 2 and 3: the role read, then primary and replica for the
   databases, promotion by hand. Useful alone.
2. The WireGuard overlay in the spec, converged under 0018's window.
3. The file pull from the mutable state map, and promotion of database and
   files together, still by hand.
4. The three-container gate, then the election on three nodes with fencing.
5. Keel Cloud as its own project: DNS with a health check, membership, key
   exchange. It starts with its own decision note.

Steps 1 to 3 give a standalone operator a warm replica they promote by hand;
step 4 makes it automatic; step 5 removes the manual DNS and key work.

## Open for the maintainer

- The three amendments above.
- Where this sits against the roadmap's phase 3, the orchestrated upgrade
  (WordPress first). The proposal is to keep phase 3 first, since an upgrade
  of a replicated set needs the upgrade path of one machine to exist.
- The election mechanism: Patroni with its built-in Raft for PostgreSQL, and
  something else for MariaDB and the web tier; or one etcd-based election
  for the whole appliance. Whether the third node may be a small witness
  that votes but holds no data, which halves the cost of three.
- Whether the old primary may rejoin by itself (hard part 4), or only by an
  operator's confirmed act, as 0013 has it today.
- The name of the election project, and whether it lives in the Keel-Linux
  organisation beside Keel Cloud.
