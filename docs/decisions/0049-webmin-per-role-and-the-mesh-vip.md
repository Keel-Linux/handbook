# 0049: Webmin per mode and role, and the VIP on the WireGuard mesh

Date: 2026-10-03
Status: **decided by the maintainer, 2026-10-03**, in two rounds the same
day: Webmin's access per mode and role first (Keel-Linux/tracker#57), then
the six points the first draft of this note left open, under "Decided,
second round". The text below already reflects both. A third round, on
2026-10-04, settled five questions keel's VIP implementation found; it is
under "Decided, third round" and overrides the text above where they
differ. The maintainer asked
that the VIP be settled before the database work, as structural. Nothing
here is implemented.

## What was asked

Webmin is public on every Keel machine today (0041, Core's table: 12321,
`public`). On a replicated pair in a cloud mode (0028) that is wrong twice:
a panel that runs as root is reachable from the Internet on two machines
instead of one, and an operator who opens the replica's Webmin by mistake
can change data that must take no changes but the primary's. The
maintainer decided where Webmin answers per mode and role (tracker#57). The
primary's rule, "only through the VIP", rests on a VIP that 0029 describes
in two sentences and keel does not implement: a search of keel's main
branch for `vip` finds nothing, and no engine repository has a `vip`
component yet. So this note decides how the VIP exists on a WireGuard mesh,
who moves it, how two nodes are kept from holding it at once, what an old
primary does when it comes back, and what keel reports about it.

## Why (brief section 10)

1. **Why the current approach is not enough.** Webmin listens on every
   address with no `allow` list, so in a cloud mode the replica's panel is
   as reachable as the primary's, from anywhere, and nothing tells the
   operator which one is in front of them. The database does not protect
   itself either: MariaDB's `read_only` stops every account except one
   holding `READ_ONLY ADMIN`, which root holds, and Webmin's MySQL module
   connects as root (keel's docs/apply.md says so today). A write there
   diverges the replica the way tracker#26 did, silently, until a failover
   loses it. A replicated file changed on a replica is overwritten by the
   primary or never reaches it (0032).
2. **Whether it can be made to work.** The pieces exist. WireGuard routes
   by `AllowedIPs`, and one prefix belongs to exactly one peer on a given
   node, so moving a `/128` from one peer to another is a single `wg set`
   on each node. Webmin's miniserv binds the addresses it is told to and
   refuses clients outside its `allow` list. MariaDB 11.8 lets the privilege
   that writes through `read_only` be taken from root too (below), and
   GTID, `pg_rewind` and Redis's resync bring an old primary back without
   copying everything. What does not work is the obvious tool: keepalived
   and VRRP need multicast and ARP on a shared link, and WireGuard is layer
   3 with neither (0020, 0029).
3. **Why this is better.** One address always means "the primary" of a
   replicated pair, for people as well as for programs; the replica cannot
   be reached at that address, and the address it can be reached at says
   so on every page. The VIP is the same mechanism with or without etcd:
   only the actor that moves it changes. The database refuses root's writes
   on a replica by itself, so Webmin's read-only module is a convenience and
   not the guard. And an old primary that comes back rejoins on its own
   when nothing was lost, and waits for the operator when something would
   be.

## Decision

### Webmin, per mode and role

The role is the node's role for **any replicated data**: a database
(0031), replicated directories (0032), or both. It is not whether the node
runs a database.

| Mode and role | Where Webmin answers | Warning | Database module |
| --- | --- | --- | --- |
| Simple installation (standalone) | every address, public, as today; confconsole offers to restrict it | none | full |
| Cloud mode, primary of a replicated pair | the pair's VIP only, inside the WireGuard mesh; never the public address | none | full |
| Cloud mode, replica of a replicated pair | its own mesh address and a private LAN address | on every page, acknowledged once per session | read-only |
| Cloud mode, a node that replicates nothing | its own mesh address and a private LAN address | none | full |

Webmin is never public in a cloud mode. The warning names what the node
replicates, with `<vip>` filled in. For a database:

> This node is a REPLICA, not the primary. Changes to the database here
> are not replicated and can break replication or lose data on failover.
> Use it only if you know what you are doing, for example to compare a
> file that is missing here but present on the primary. The primary is at
> <vip>.

For replicated files (a Keel Web pair, an application's `replicate:`
directories):

> This node is a REPLICA, not the primary. Changes to replicated files
> here are not propagated to the primary and are overwritten by it. Use it
> only if you know what you are doing, for example to compare a file that
> is missing here but present on the primary. The primary is at <vip>.

A node that replicates both shows both paragraphs on one page.

Promotion, demotion and rejoin switch all of it: the bind, the `allow`
list, the warning and the module's ACL follow the role keel observes,
never a hand edit.

### The VIP on the mesh

- **The VIP belongs to the appliance, not to a service inside it.** Every
  replicated appliance pair (or set) has one VIP, and everything the pair
  serves to the mesh is reached at it: for WordPress with its built-in
  MariaDB in cloud simple (0047), the two WordPress containers share one
  VIP, and the database is reached at that same VIP. There is no separate
  database VIP per appliance. A node that replicates nothing has none.
- **The VIP is a `/128` inside the overlay prefix.** The allocator of 0048
  takes it like any address and never hands it to a node. It is IPv6
  only; the optional IPv4 overlay of docs/spec.md gets no VIP in this
  version.
- **The current primary carries it on `wg0`**, as a second address beside
  its own: `ip -6 addr add <vip>/128 dev wg0`.
- **Every other peer routes it to the primary** by listing `<vip>/128` in
  the `allowed_ips` of the primary's entry, beside the primary's own
  `/128`. Because the VIP is inside the overlay prefix, which the node's
  own address already routes to `wg0`, no kernel route changes on any node
  when it moves: only WireGuard's table of which peer owns which prefix.
- **Moving it** is removing it from the old primary's entry and adding it
  to the new one's, on every peer. WireGuard does both in one step: giving
  a prefix to a peer takes it from whichever peer had it on that node
  (which is why docs/spec.md refuses a prefix given to two peers), so the
  move on each node is one `wg set wg0 peer <new> allowed-ips
  <new>/128,<vip>/128`, then the same list written to the rendered
  `/etc/wireguard/wg0.conf`, so a restart keeps it.
- **Who moves it.**
  - **Before etcd** (cloud simple, and cloud advanced until the third node
    forms the quorum, 0048): `keel database promote` on the new primary,
    in the same operation that promotes the database and flips the
    replicated folders (0032). It asks the old primary to release the VIP,
    takes it, and announces the move to every peer over the overlay, by
    the channel 0048 uses to announce a new peer: a message sent from the
    new primary's own overlay address, which only its key can use, so the
    source authenticates it. Each peer applies the `wg set` above.
  - **With etcd** (cloud advanced): the VIP controller of 0025 and 0029,
    in its own repository. The holder of the election lease of 0020 is the
    primary; it writes the VIP's holder under the pair's key, and every
    node's controller watches that key and applies the same `wg set`.
    `keel database promote` still works by hand, and with etcd it writes
    the key instead of announcing.
- **Fencing: an epoch, and release before take.**
  - Every VIP has an epoch, an integer that only grows, recorded on each
    node with the holder's public key in `/var/lib/keel/vip/<address>`.
    With etcd the epoch is the etcd revision of the holder's key. A node
    applies a move only when its epoch is higher than the one it holds,
    and only when the announcement comes from the new holder's own overlay
    address; equal epochs (two promotes at once, possible only with three
    or more nodes in a set) go to the lower public key.
  - **The new primary takes the address only after the old one released
    it.** The old primary, asked to release, removes the address from its
    `wg0` first and acknowledges after; promote waits for the
    acknowledgement. **When the old primary does not answer, promote
    refuses to move the VIP unless `--old-primary-gone` is given**: only
    the operator knows that, which keel's promote already says in its
    output today. With etcd, the lease is the fence: the holder drops the
    address when it cannot renew the lease, at half its TTL, so it is gone
    before the lease can expire and be won by another node.
  - **A node carries the VIP only while it is the primary and holds the
    highest epoch it knows.** An old primary that comes back learns the
    higher epoch from any peer (it asks each peer's epoch over the overlay
    at boot and on a timer), drops the address at once, turns its data
    read-only, and rejoins as below.
- **0018's window: the VIP move is exempt, as 0029's was, extended to the
  manual move.** 0029 exempted a move made by the controller that touches
  only the VIP's `allowed_ips` entry. This note extends the exemption to
  the same change made by `keel database promote` before etcd, and to the
  holder adding or removing the VIP as an address on its own `wg0`. The
  reason holds and is stronger than 0029 stated it: no kernel route, no
  key, no endpoint and no node's own overlay address changes, so no SSH
  session and no node-to-node traffic loses its way; apply.md's route
  check still runs before the move and refuses it if it would capture a
  gateway or the operator's client, which inside the overlay prefix it
  cannot. Every other overlay change stays under the window. One sentence
  of 0029 has to change (see "Reconciled with 0029, 0041 and keel").
- **Clients outside the mesh do not reach the VIP.** It is an address of
  the mesh, for mesh members (an application node reaching its database,
  0042's VIP upstreams) and for Webmin over the overlay. Public traffic is
  0044's and 0045's: DNS with a health check and the edge, never the VIP
  (0044 already restates 0029 that way).
- **Operators reach Webmin from outside the mesh only through an SSH
  tunnel, for now.** A workstation is not a mesh member, so the way is a
  local forward through any node, whose sshd stays public: `ssh -L
  12321:[<vip>]:12321 root@<any node>`, then `https://localhost:12321`. The
  connection reaches the VIP from that node's overlay address, which the
  primary's `allow` list accepts.

### The old primary coming back

A returning old primary does not stay a second primary and does not stay
merely read-only: it catches up from the new primary and rejoins as a
replica, fetching what was written there while it was away. **Read-only is
its state from the moment it learns the higher epoch until it is a
replica**, and stays its state when it cannot rejoin safely. Replication
uses real addresses (0029), so "the VIP's holder" below is the holder's own
overlay address, not the VIP.

The safe path is decided per engine by one question: **does the old
primary hold writes the new primary lacks?** If not, it rejoins
automatically, since nothing can be lost. If so, it stays read-only, keel
reports the divergence and alerts through keel's alerts (0040), and the
operator decides: discard and reseed from the new primary, keeping 0020's
dump of what the node held first, or reconcile by hand.

**MariaDB: compare GTID sets.**

1. keel sets `gtid_strict_mode=ON` on every node of a set, so the server
   itself refuses a replica that asks for a GTID its primary's binary log
   does not have.
2. The old primary's errant transactions are the GTIDs in its
   `@@gtid_binlog_state` that the new primary's lacks: for each domain and
   server ID, a sequence number on the old primary higher than the one the
   new primary records for the same domain and server ID. keel reads both
   over the overlay, with the root lock above in place.
3. **None** (the normal case: with `AFTER_SYNC` semi-synchronous
   replication, 0031, the primary commits nothing the replica has not
   received): keel sets `gtid_slave_pos` to the old primary's
   `@@gtid_binlog_pos`, runs `CHANGE MASTER TO` the VIP holder's overlay
   address with `MASTER_USE_GTID=slave_pos`, starts replication, takes
   `READ_ONLY ADMIN` from its accounts as on any replica, and writes
   `role: replica` and the new primary's address into its own spec (each
   node writes only its own, 0013). The window where semi-synchronous
   replication fell back to asynchronous (0031) is the case where errant
   transactions can exist, which is why the comparison always runs.
4. **Some**: it stays read-only and is not connected to the new primary.
   keel reports the errant GTIDs, by domain, server ID and sequence
   number, in `keel diff` and in the alert.

**PostgreSQL: the timelines.** The new primary's promotion started a new
timeline at a fork point, which its timeline history file records.

1. **The old primary's WAL ends at or before the fork point**: it holds
   nothing the new primary lacks. keel writes `standby.signal` and
   `primary_conninfo` for the VIP holder's overlay address, with
   `recovery_target_timeline = latest`, and it follows.
2. **Its WAL goes past the fork point, with no commit record past it**
   (read with `pg_waldump`): nothing committed is lost, and keel runs
   `pg_rewind` from the new primary, then follows as in 1. keel sets
   `wal_log_hints = on` on every PostgreSQL node of a set, which
   `pg_rewind` needs, and keeps the WAL since the fork on the new primary
   through the replication slot. When `pg_rewind` cannot run (the WAL it
   needs is gone), keel reseeds with `pg_basebackup`, which loses nothing
   either in this case.
3. **A commit record past the fork point**: divergence. It stays
   read-only, started as a standby with no `primary_conninfo`, so every
   session is refused writes, the superuser's included, and keel reports
   the fork point and the last commit past it.

**Redis: `replicaof`, with a full resync accepted.** Redis keeps no
transaction history to compare and its replication is asynchronous. keel
runs `REPLICAOF` the VIP holder's overlay address; Redis resumes partially
when the replication IDs and offsets allow it, and otherwise does a full
resync, which discards what the old primary wrote after the split. That
loss is accepted for Redis (0033's data services hold sessions, caches and
queues there), and keel logs which of the two happened. A replica is
read-only to clients from the `REPLICAOF` on (`replica-read-only yes`).

**Replicated files.** The old primary's folders are flipped to receive-only
(0032) before anything else. A receive-only folder that finds local changes
reports them rather than reverting them; when it reports none, the node
rejoins with its folders; when it reports some, keel lists them, alerts,
and leaves the folder as it is for the operator, the file counterpart of
errant transactions.

**After rejoin** the node is a replica in every respect: its Webmin shows
the warning, its VIP state shows the holder, and 0031's failback, if the
operator chose automatic, can run once it has caught up.

### What `keel inspect` and `keel diff` show

- **The spec** gains one field, `appliance.vip`: the pair's VIP, the same
  on every node of the pair, written by the installer on the primary and
  handed to the replica with the other values the primary generates (0028,
  0048). Who holds the VIP is not in the spec: it is state, like the role
  after a promote (docs/diff.md).
- **`inspect`** reports, as machine state beside the spec: the VIP's
  address, whether this node carries it on `wg0`, the holder and the epoch
  it knows, and which peer this node's table routes the VIP to. It reads
  the peers' `allowed_ips` back with the VIP `/128` taken out, so a peer
  read back is the peer the spec declares. On a node that came back, it
  reports the rejoin's state: catching up, rejoined, or diverged with the
  errant GTIDs, the fork point, or the locally changed files.
- **`diff`** compares `appliance.vip` like any field, and compares peers
  without the VIP `/128`, so a move is never drift. It reports, as findings
  with their reason, the states that must not exist: a node that carries
  the VIP and is not the primary; a primary without it; the VIP routed to a
  peer that is not the holder of the highest epoch; a node whose epoch is
  behind a peer's; a diverged old primary. `apply` corrects only the safe
  direction, removing the VIP from a node that is not the primary. It never
  adds the VIP to a node, except once at installation, at epoch 1, on the
  first primary of a pair when no epoch exists; every later move is a
  promote's or the controller's.

### The private LAN address

A private LAN address is an address on the node's uplink, not on `wg0`,
inside RFC 1918 (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`) or the
unique local range of RFC 4193 (`fc00::/7`), and outside the overlay
prefix. Not `100.64.0.0/10` (RFC 6598), which is the provider's shared
space and not the operator's network, and not a link local address. When
the uplink has none, Webmin answers on the mesh address alone, and
confconsole says so.

The source matters as much as the address: some providers give a machine
only a private address and NAT a public one to it one to one, so a
listener on the private address can be reached from the Internet with the
client's public source address preserved. The `allow` list is what refuses
those: it holds only the prefixes on link on that uplink, never a route's.

### How miniserv is configured per role

keel renders the address keys of `/etc/webmin/miniserv.conf`, `bind`,
`sockets`, `allow` and `ipv6`, from the mode and the observed role, and
restarts Webmin when they change. `port` stays 12321. The rest of the file
stays Webmin's.

| Mode and role | `bind` and `sockets` | `allow` |
| --- | --- | --- |
| Simple, default | unset: every address | unset |
| Simple, restricted in confconsole | unset | `127.0.0.1 ::1`, the uplink's on-link private prefixes, and the overlay prefix when there is one |
| Cloud, primary | the VIP | the overlay prefix, `127.0.0.1 ::1` |
| Cloud, replica, or a node that replicates nothing | its own overlay address, and each private LAN address of its uplink | the overlay prefix, the on-link private prefixes of its uplink, `127.0.0.1 ::1` |

**In a cloud mode the public address is refused three times:** miniserv
does not listen on it, its `allow` list does not hold it, and where
keel-firewall exists (cloud advanced, `firewall.enabled: true`) the derived
ruleset accepts 12321 only on `wg0` and, off the primary, from the on-link
private prefixes of the uplink. In cloud simple, where keel touches no
firewall it does not own (0048), the first two carry it. Core's manifest
keeps `expose: public` for Webmin, which is the simple installation's; in
a cloud mode the derived firewall and miniserv follow this note.

### The replica's warning and module

- **The acknowledgement** is Webmin's pre-login banner, a page the browser
  must click through before the login form, once per session, rendered
  with the warning and the VIP. **The warning on every page** is a header
  the theme shows on every page. Both are shipped in `common` (0036), by
  the overlays that replicate (the database overlays and syncthing), and
  switched by a role file keel writes, which says what the node replicates.
- **The database module is read-only on a database replica**: its Webmin
  ACL for root and for every Webmin user, with every capability that
  writes off (create and drop databases and tables, edit rows, users and
  privileges, run arbitrary SQL, start and stop the server), the same way
  0019 ships the network module. On promotion the full ACL comes back and
  the banner goes. A file replica keeps its modules; the warning is its
  guard, and the receive-only folder (0032) reports what was changed.

### The MariaDB guard on a replica

The ACL is Webmin's. What keeps a MariaDB replica read-only is the server:

- **What MariaDB 11.8 does.** `read_only` refuses writes to every account
  but those holding `READ_ONLY ADMIN`, and the replication thread. Since
  10.11 `SUPER` no longer includes `READ_ONLY ADMIN`, and MariaDB's own
  documentation draws the consequence: "one can remove the READ_ONLY ADMIN
  privilege from all users and ensure that no one can make any changes on
  any non-temporary tables" ([GRANT, READ_ONLY
  ADMIN](https://mariadb.com/docs/server/reference/sql-statements/account-management-sql-statements/grant)).
  The same privilege is what changes `read_only`'s global value, so an
  account without it can neither write nor turn `read_only` off.
- **What it does not have.** A setting that stops an account holding the
  privilege, MySQL's `super_read_only`, arrives as
  `read_only=NO_LOCK_NO_ADMIN` in MariaDB 12.0.1
  ([MDEV-36425](https://jira.mariadb.org/browse/MDEV-36425), fix version
  12.0.1: `read_only` becomes `OFF`, `ON`, `NO_LOCK` and
  `NO_LOCK_NO_ADMIN`, the last refusing even `READ_ONLY ADMIN`). Debian 13
  ships 11.8.6 (0013), so the guard is the privilege, not the setting.
- **On a MariaDB replica, root loses `READ_ONLY ADMIN` as well.** keel
  revokes it from `'root'@'localhost'` with `sql_log_bin` off, records it
  in `/var/lib/keel/database/read-only-admin` with the other accounts keel
  already takes it from, and gives it back on promotion. One account keeps
  it: `'mysql'@'localhost'`, which MariaDB creates with every privilege and
  `unix_socket` only, so only the system's `mysql` user reaches it. keel
  runs its own replica statements through it (`runuser -u mysql --
  mariadb`): the seed, `CHANGE MASTER`, the lock, the rejoin, and the
  promotion that turns `read_only` off and gives the privilege back. Root
  through Webmin, or at a shell with `mariadb`, then gets error 1290 on a
  replica like the application does. Root cannot grant itself the
  privilege back, since `GRANT` gives only what the granter holds, and
  cannot edit `mysql.global_priv` by hand, since `read_only` refuses that
  write too. The same lock holds on an old primary while it catches up or
  stays diverged.
- **What it is not.** A guard against accidents, not against a root who
  means it: the system's root can still restart the server with another
  configuration or become `mysql`. That is the line 0019 draws for the
  network: the panel cannot do it by mistake, the command line can do it
  on purpose. When Keel's MariaDB reaches 12.x, `NO_LOCK_NO_ADMIN` on the
  replica replaces the revoke.
- **PostgreSQL needs nothing more.** A hot standby refuses writes in every
  session, a superuser's included; the warning still applies to files and
  services.

## Decided, second round (2026-10-03)

The six points the first draft left open, answered by the maintainer and
carried into the decision above:

1. **Yes**: on a MariaDB replica, root loses `READ_ONLY ADMIN` as well.
2. **The VIP belongs to the appliance (the container), not to the database
   inside it.** The pair of WordPress containers in cloud simple shares one
   VIP, and the database is reached at it. Every replicated appliance pair
   has one VIP; 0041 is amended accordingly.
3. **Yes**: promote refuses to move the VIP while the old primary does not
   answer, unless `--old-primary-gone` is given.
4. **Not just read-only**: a returning old primary catches up from the new
   primary and rejoins as a replica when it holds no writes the new primary
   lacks (GTID sets on MariaDB, the timelines and `pg_rewind` on
   PostgreSQL, `replicaof` with a full resync accepted on Redis); with
   errant writes it stays read-only, keel reports and alerts, and the
   operator decides between discarding and reseeding, and reconciling.
   Read-only is the state while catching up.
5. **No**: the warning follows the node's role for any replicated data,
   files included (0032), not whether it runs a database. A file replica,
   a Keel Web pair for example, shows the same kind of warning worded for
   files. Only a node that replicates nothing gets none.
6. **Yes**: operators reach Webmin from outside the mesh only through an
   SSH tunnel, for now.

## Decided, third round (2026-10-04)

Five questions the design of keel's VIP raised, where this note met 0020,
0025 and 0048, each approved by the maintainer as recommended:

1. **The code lives in keel.** The VIP state, the move, promote and the
   etcd lease controller are keel's, as `keel mesh` and etcd are. A
   `keel-overlay-vip` package in Keel-Linux/common ships only the unit
   files, as the etcd overlay does. There is no separate keel-quorum
   repository: the election of 0020 for a replicated pair is the VIP's
   etcd lease.
2. **No new role field.** The primary is the VIP's holder: the node of the
   pair that holds the highest epoch it knows for `appliance.vip`; the
   other node of the pair is the replica. 0020's one role stands, and is
   observed, not declared. The command is **`keel vip promote`**, with
   `--old-primary-gone`; it works with or without a database, and `keel
   database promote` calls it.
3. **Only the nodes of the pair may claim the VIP**: the nodes whose spec
   declares the same `appliance.vip`, as their roster on the members'
   channel says, and that the receiver trusts by 0048's amendment. A
   claim is signed with the claimant's signing key and sent from its own
   overlay address; any other trusted member's claim is refused.
4. **Nodes that are not cloud advanced learn of moves through the signed
   announcement** on the members' channel, with etcd as without it; a
   cloud advanced node watches etcd as well.
5. **`--old-primary-gone` with etcd waits for the old primary's lease to
   expire**, up to its TTL, and never revokes another node's lease.

**The lease.** Its TTL is 20 seconds, and the holder drops the address
after 10 seconds without a renewal, counted from the send of the last
renewal etcd answered. Against etcd's 5 second election timeout (keel's
docs/mesh.md, "Timeouts"): a re-election in the majority takes 5 to 10
seconds, during which renewals fail but etcd extends every lease on a
leader change, so 10 seconds rides out one re-election without a move;
and etcd cannot expire the lease before 20 seconds after that send, so a
holder cut off from the majority has dropped the address 10 seconds
before any other node can win it. The epoch with etcd is the revision of
the pair's key, which a claimant writes only by a compare-and-swap on
the revision it saw.

**What this amends.** 0020, "Where each piece lives" and "Names and
home": the election row is keel's VIP lease, not keel-quorum, and the
watchdog of hard part 1 is not built in this version. 0025, "What this
amends", the brief's section 2: the VIP controller acts on the registry
from keel, as the etcd member keel runs does; it configures only the
machine it runs on. "Who moves it" and "How it is carried out" above
read `keel vip promote` where they say `keel database promote` for the
VIP.

## Reconciled with 0029, 0041 and keel

- **0029, "Resolved"**: "node-to-node and management traffic use real
  addresses, never the VIP" is no longer true for Webmin, which on a
  primary answers on the VIP only. It becomes: SSH and node-to-node
  traffic, replication and rejoin included, never use the VIP. A move does
  cut the Webmin sessions open on the old primary, and that is intended:
  they must not land on what is now a replica. The exemption stays safe
  because the window protects the session that made the change, and
  promote runs on the new primary over SSH or a console on its real
  address. `keel database demote` on the old primary refuses when its own
  session arrived over the VIP, by the session lookup 0018 already uses,
  since it would cut itself off.
- **0029, "the controller watching etcd ... built with the etcd phase"**:
  the controller stays the mover with etcd; before etcd, promote moves it.
  So the VIP, and with it the primary's Webmin, exist in cloud simple, from
  Phase 2, not only from the etcd phase.
- **0041, "Resolved"**: "the VIP is only for database appliances" was
  written before 0047 put a built-in MariaDB in the WordPress image, which
  runs as primary and replica in cloud simple. It becomes: every replicated
  appliance pair has one VIP, the appliance's, and a node that replicates
  nothing has none.
- **keel, docs/apply.md and `keel/system/dbreadonly.py`**: both say root
  "can grant itself anything it lacks" and that MariaDB 11.8 has nothing
  that stops root. The second half is right about settings and wrong about
  privileges, per MariaDB's documentation above; both are corrected with
  the revoke.

## How it is carried out

1. **keel**: `appliance.vip` in the spec; the VIP state file and epoch;
   promote's release, take and announce, and `--old-primary-gone`; `keel
   database demote`; the epoch check at boot and on a timer; the rejoin per
   engine, with its comparison, its report and its alert; inspect and diff
   as above; the miniserv keys per role; the role file the banner reads;
   the revoke from root, and the `mysql` account for keel's own statements;
   `gtid_strict_mode` on MariaDB and `wal_log_hints` on PostgreSQL in every
   set.
2. **keel-overlay-vip** in `common` (0036): the boot and timer units of
   the epoch check. The etcd controller is added to it in Phase 5. The
   overlay moves from the database appliances' composition to every
   appliance that replicates, as 0041 is amended.
3. **The replicating overlays in `common`** (the databases and syncthing):
   the pre-login banner and the header, worded for what they replicate,
   and the read-only ACLs for the `mysql` and `postgresql` modules.
4. **confconsole**: the restrict option in the simple installation, and a
   line saying where Webmin answers (the VIP, or this node's mesh and LAN
   addresses, with the SSH tunnel to use).
5. **0048's allocator** reserves the VIP; its announcement carries moves.

Done when, on built images and not on machines assembled by hand (as
tracker#57 says): two WordPress containers in cloud simple over WireGuard,
Webmin and the database both on the one VIP reaching the primary; the
replica's Webmin shows the banner, the header and a read-only module, and
an `INSERT` through Webmin's SQL page as root is refused with 1290; the
public address refuses 12321 in both cloud modes; `keel database promote`
moves the VIP, the banner and the module, with no `keel network confirm`;
a promote with the old primary stopped is refused without
`--old-primary-gone`; the old primary started again drops the VIP and
rejoins as a replica with no errant GTID, and with one written while it was
cut off it stays read-only, reports the GTID and alerts; a Keel Web pair's
replica shows the file warning; `keel diff` on every node reports no drift
after a move and a rejoin.

## Consequences

- Webmin is no longer public on any node in a cloud mode; an operator who
  used the public address uses the SSH tunnel or the LAN.
- The VIP is built in Phase 2 with the database work, not in Phase 5:
  before etcd it is moved by promote, and Phase 5 adds the controller.
- Every replicated appliance pair carries the `vip` overlay, not only the
  database appliances.
- A promote with an unreachable old primary needs one more word from the
  operator, which is the fact only the operator has.
- An old primary that lost nothing rejoins with no operator; one that holds
  writes the others lack never rejoins without one.
- On a MariaDB replica, root at a shell is refused writes as well;
  maintenance writes on a replica go through keel or the `mysql` account,
  with `sql_log_bin` off.
- The mesh has one reserved address per replicated pair.

## Possible future work (not decided)

- **`keel mesh invite --workstation`**, a WireGuard peer for an operator's
  workstation, so Webmin could be reached over the mesh without an SSH
  tunnel. It needs either every node to update the workstation's peer on a
  move or a node that forwards for it, which is a decision of its own.

## What this amends

- **0018, "The converge, and why it reverts by itself"**: as 0029 amended
  it, extended. A VIP move made by `keel database promote` before etcd,
  and the holder adding or removing the VIP on its own `wg0`, are not
  under the window. Everything else in 0018 stands.
- **0020, "The hard parts" item 4 and the rejoin row of "Decided, second
  round"**: rejoin is automatic when the old primary holds nothing the new
  primary lacks, since there is nothing to lose, and always waits for the
  operator when it holds something; the dump and the copy of the files
  0020 asks for are kept before a discard and reseed.
- **0029, "Resolved"**: management traffic may use the VIP (Webmin on a
  primary); the mover before etcd is promote, the controller after; the
  fencing is the epoch and release before take. Its decision is unchanged:
  the VIP is for delivering the service, replication uses real addresses,
  and automatic promotion stays for appliances that carry a database.
- **0041, "Resolved"** and Core's table: every replicated appliance pair
  has one VIP, the appliance's (second round, point 2); Webmin's `expose:
  public` holds for the simple installation only.
- **0036**: the `vip` overlay is in every appliance that replicates, not
  only in Keel PostgreSQL and Keel MariaDB.
- **0013, "What the operator sees"**: confconsole says where Webmin
  answers, and offers the restriction in the simple installation.
- **0031**: unchanged and applied. The replica serves nothing; its Webmin
  is for system work and comparison. Failback runs only after the rejoin
  has caught up, as it already requires.
- **0032**: unchanged and applied; the receive-only folder's report of
  local changes is the file side of the rejoin's comparison.
- **0025**: the VIP controller is one of the actors on the registry it
  names; the epoch is an etcd revision there.
- **0028**: the VIP's address is one of the values the primary generates
  and hands to the replica.
- **0048**: the allocator reserves the VIP, and the overlay announcement
  carries VIP moves as well as new peers.
- **0019**: unchanged; Webmin still changes no network, and keel, not
  Webmin, writes miniserv's address keys.
- **0044**: unchanged; the VIP never faces the public, as it says.
