# 0013: Database topologies configurable from the console

Status: **scope decided 2026-09-27**, phases 1 and 4 deferred, sharding deferred. The maintainer chose the console flow described under "What the operator sees" below. Asked for by the maintainer:
every Keel database appliance should be configurable from confconsole for
standalone, cloud (master or slave) and sharding, for MariaDB and PostgreSQL
alike, and the configuration should actually configure the database. This
note is the plan that was asked for alongside it, because the request does
not decide the hard parts and they are better decided before code exists.

## First, the case that motivated it does not need any of this

The example given was WordPress with its database in the cloud. That needs
one thing: the application pointing at a database somewhere else instead of
one on its own machine. It is a setting on the application side, no
replication and no sharding involved, and it is the cheapest useful piece of
the whole subject. It should ship first, and it is listed as phase 1 below.

## What the three modes actually are

"Master/slave" and "sharding" are names for mechanisms that differ per
engine, and pretending otherwise produces a console that lies.

| Mode | MariaDB | PostgreSQL |
| --- | --- | --- |
| Standalone | one server, what we ship today | one server, what we ship today |
| Primary | binary log, `server_id`, GTID, a replication account | `wal_level=replica`, a replication slot, a replication role, `pg_hba` entry |
| Replica | `CHANGE MASTER TO ... MASTER_USE_GTID`, seeded from a backup of the primary | `pg_basebackup` then `standby.signal` and `primary_conninfo` |
| Multi-primary | Galera, a genuinely different animal: synchronous, quorum based, minimum three nodes | nothing equivalent in the archive |
| Sharding | Spider storage engine, or a router in front | no packaged option |

## What Debian 13 gives us, measured on the build host

| Package | Version |
| --- | --- |
| galera-4 | 26.4.23-0+deb13u1 |
| mariadb-plugin-spider | 1:11.8.6-0+deb13u1 |
| patroni | 4.0.7-3~deb13u1 |
| repmgr | 5.5.0+debpgdg-1 |
| pgpool2 | 4.6.1-2 |
| postgresql-17-pglogical | 2.4.5-1 |
| citus | absent |
| maxscale | absent |

So replication has a packaged path on both engines, Galera gives MariaDB a
real multi-primary mode, and sharding has a packaged path on MariaDB only.
PostgreSQL sharding would need a third party repository, which costs us both
the reproducibility work and the sovereignty claim: an image nobody can
rebuild from our own archive is not one we should ship. That is a reason to
say no to PostgreSQL sharding for now, and to say it out loud in the console
rather than offering a menu entry that cannot work.

## Where this collides with the brief, and how it stays inside it

The brief forbids fleet orchestration in this codebase. Replication and
sharding are cluster properties, so the line has to be drawn precisely:

- **In scope:** configuring the role of *this* instance. This node is a
  primary. This node is a replica of that address. This node is a Spider
  head or a data node. Each screen configures the machine it runs on.
- **Out of scope:** deciding which node should be primary, moving that role
  around, watching for failure, and reconfiguring others. That is an
  orchestrator, and we are not writing one here.

The consequence must be stated in the console, not buried: replication
without automatic failover is not high availability. Promotion is an
operator action on the replica. A console that implies otherwise is worse
than one that offers less.

## The problems to plan for, which the request does not settle

1. **Becoming a replica destroys local data.** A standby is a copy of the
   primary. The apply path must refuse unless the database is empty or the
   operator confirms destruction explicitly, and `keel diff` must never
   trigger it on its own.
2. **A replica needs the primary to exist first.** First boot is a
   single-machine event, so the declarative spec has to express a
   dependency the machine cannot satisfy alone: convergence must be
   idempotent, retryable and honest about waiting rather than failing.
3. **Credentials and trust between nodes.** Replication carries a password
   and, over anything but a trusted link, TLS. The spec references secrets by
   file today; a replica also needs the primary's address and its certificate
   authority. IPv6 first means global addresses and no NAT, which makes this
   simpler than it is elsewhere.
4. **Promotion creates drift by design.** After a promotion the spec says
   replica and the machine says primary. Diff must report it and apply must
   refuse to silently demote. This is the same class of problem as the
   password fields, and the vocabulary work of 0009 is the precedent.
5. **Backups and upgrades change shape.** A replica should not be backed up
   like a primary, and a major version upgrade of a replicated pair has an
   order. Whatever we ship must say which.
6. **Testing needs two machines.** The appliance gate boots one container.
   Proving replication needs two on the same bridge, and proving Galera needs
   three. That is new test infrastructure and it is part of this work, not an
   afterthought.
7. **The console can only configure one node.** confconsole runs on the
   machine. It can ask for the primary's address and credentials; it cannot
   coordinate. The screens must be written from that point of view.

## Phases, each with what would prove it

**Phase 1: the application points elsewhere.** An appliance can use a remote
database instead of its local one, declared in the instance spec and
configurable in confconsole. Proof: a WordPress appliance with no local
database server, answering over IPv6, with its data in a Keel MariaDB
appliance on another container, and `keel diff` clean on both.

**Phase 2: the vocabulary and the reading.** The spec gains a database
section, `keel inspect` reports the role the machine is actually in, and
`keel diff` compares them. No configuration is changed by this phase. It is
cheap and everything later depends on it. Proof: a standalone appliance
reports standalone, and a machine put into replication by hand reports
replica with drift.

**Phase 3: primary and replica, PostgreSQL first.** Streaming replication is
the best documented and the least surprising, and `pg_basebackup` makes the
seeding step explicit. Then MariaDB with GTID. Proof: a two container test in
the gate, data written on the primary readable on the replica, the replica
refusing to be built over a non empty database, and promotion as a separate
operator action.

**Phase 4: multi-primary for MariaDB with Galera.** Only after phase 3, and
only if the three node test can run in the gate. Proof: three containers, a
write on any node visible on the others, and a node rejoining after being
stopped.

**Phase 5: sharding, MariaDB only, with Spider.** Configure this node as a
head or a data node. PostgreSQL sharding stays unavailable and the console
says why. Proof: a table sharded across two data nodes, queried through the
head, with both nodes built from published layers.

## What would make me argue against going further

If phase 3 cannot be tested in the gate with two containers, the rest should
not be built. An untested replication feature in an appliance people trust
with data is worse than no feature, and the project's own rule about coverage
exists for smaller risks than this one.


## What the operator sees, decided 2026-09-27

The maintainer settled the shape: choosing a database appliance means choosing
its mode, and the mode choice leads to a configuration screen. Sharding comes
later. So the console offers exactly this, on both database appliances:

    Database mode
      Standalone            one server, what the appliance is today
      Cloud                 this node takes part in replication
        Primary             other nodes replicate from this one
        Replica             this node replicates from another

Standalone needs no second screen. Primary asks what the replicas will need
and shows it: the address to replicate from, the replication account, and
where its password is kept. Replica asks for the primary's address and that
password, and warns before it acts, because becoming a replica replaces the
local data with a copy of the primary.

Two properties the screens must keep, and they are the reason this is written
down before any code:

- **Each screen configures the machine it runs on.** The primary screen does
  not create replicas, and the replica screen does not promote anything
  elsewhere. Promotion is its own entry on the replica, an explicit act.
- **The console says what it is not.** Replication here has no automatic
  failover, so the screen says so in a line the operator cannot miss. A
  console that lets somebody believe they bought high availability is worse
  than one that offers less.

Phase 1 of the plan above, an application using a database on another machine,
is not what was asked for now and waits. Phase 4, Galera multi-primary, and
phase 5, sharding, wait behind the replication work, and the console shows no
entry for a mode it cannot configure.


## The catalog shape, decided 2026-09-27

Proposed by the maintainer as `mariadb-std` and `mariadb-cloud`, `lamp-standalone`
and `lamp-cloud`, and settled the other way after the argument below.

**An image is never split by topology.** Standalone, primary and replica differ
by configuration, not by content: the same server, the same packages, a
different `server_id`, binary log and replication account. Two artifacts for
that would be byte identical in content while each paid for its own build, boot
test, audit, publication, signature and reproducibility. Worse for the
operator: somebody who installed the standalone one and later wanted
replication would have to change image instead of changing a setting, which is
the opposite of what this work is for.

**An image is split when the content differs.** A stack with a local database
server and one without are genuinely different images: in one the server is
installed, in the other it is absent. That difference deserves two artifacts,
and the names say what is in them rather than what topology they are running.

| Artefact | How many | Where the mode lives |
| --- | --- | --- |
| mariadb, postgresql | one each | standalone, primary or replica, chosen in the console |
| lamp, lapp | two each, with and without a local database server | the remote endpoints configured in the console |

The instinct behind the maintainer's proposal is right and is answered
elsewhere: an operator should not have to know any of this before choosing from
the catalogue. That is the job of the catalogue description and the console
screen, not of duplicating images per topology.

**Consequence for the layer model.** The database stops being a parent layer
and becomes a component, which is what decision 0010 built the unit mechanism
for. The composition becomes:

| Artefact | Composition |
| --- | --- |
| apache-php | a layer on core |
| lamp | child of apache-php carrying the mariadb unit |
| lapp | child of apache-php carrying the postgresql unit |
| lamp without a local database | apache-php with no database unit |
| mariadb, postgresql | child of core carrying the same unit |

So the unit extraction of mariadb and postgresql, and the `apache-php` layer,
come before LAMP and LAPP, and WordPress comes on top of LAMP inheriting the
choice of where its database lives. `apache-php` shared by both stacks is the
second consumer 0010 was waiting for.


## The standard set, decided 2026-09-27: MariaDB, PostgreSQL, Redis

The maintainer chose three engines to carry the whole treatment: the unit
extraction, the console modes, the configuration and the boot tests. Measured
against what Debian 13 can rebuild, this is also the largest set that keeps the
sovereignty claim intact.

| Upstream appliance | Debian 13 | Verdict |
| --- | --- | --- |
| mysql, which installs MariaDB | yes | ours, keel-mariadb |
| postgresql | yes | ours, keel-postgresql |
| redis | yes, `redis-server 5:8.0.2-3+deb13u2` | next, the fork keel-redis exists untouched |
| couchdb | absent, comes from Apache's own repository | out while it needs a third party |
| mongodb | absent, removed over the SSPL licence change, upstream recipe untouched since 2022 | out while it needs a third party |

Redis is the engine where these modes are cheapest, which is worth stating
because it inverts the usual assumption that the SQL engines lead. Replication
is one directive, `replicaof`, with `masterauth` for the credential. Failover
has `redis-sentinel`, packaged with the server. Sharding is native in Redis
Cluster and needs no extra package at all, where PostgreSQL has no packaged
option and MariaDB needs Spider. So the room left in `role` for shard and
multi-primary values will be exercised by Redis first, and a vocabulary shaped
only around SQL would have to be broken to fit it.

Debian 13 also ships `valkey-server 8.1.1`, the fork made after Redis changed
its licence. Recorded as the ready escape if Redis tightens further: the same
configuration unit can serve both, and the choice would be a package, not a
new topology.
