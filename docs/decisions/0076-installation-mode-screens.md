# 0076: The installation mode screens, and a guide per mode with one column for each node

Date: 2026-11-05
Status: **decided by the maintainer, 2026-11-05** (the five choices below:
"Tudo sim pode ser"). The design is by the coordinator under the
maintainer's delegation.

## What was found

Decision 0028 says that at first boot the operator chooses one of three
modes: simple, cloud simple and cloud advanced. On 2026-11-05 the first boot
of every Keel image had no screen for this:

- Nothing writes `installation.mode`. confconsole reads it
  (`keelmenu.py`), and a fresh description has only `version: 1`
  (`keelcli.py`).
- The role screen offers Standalone, Primary and Replica (0013), and only
  for MariaDB. PostgreSQL, Core and Web get no screen.
- The Cloud screens of confconsole are the typed flow of 0013: the peer's
  key, the address to replicate from and a password shown once. They do
  not call `keel mesh` or `keel vip`, which is the path the real-node tests
  proved (the evidence of 2026-10-08, 2026-10-14 and 2026-10-15: an invite
  line, `appliance.vip`, and the pair record).
- Cloud advanced (etcd of three, a witness) is reached only by writing
  `instance.yaml` by hand.

The maintainer asked for the three modes on every appliance, Core and Web
included, with a screen that makes each one easy, and for a guide that shows
each node in its own column: the screens of that node, in order, and what
the operator types or chooses on each.

## Decided

1. **Cloud advanced, for an application, is the pair with its embedded
   database plus a witness.** That is what 0057 and the real-node evidence
   of 2026-10-15 proved. The variant of 0047 (the database turned off and
   discovered, 0026) is not built, and it stays out of scope until it is.
2. **A witness is always a Keel Core container**, with no application and no
   data: `installer`, `wireguard`, `etcd` and `crowdsec` enabled, `vip`
   disabled (0057). It fits a small site, such as BR3.
3. **keel proposes the VIP and carries it in the invite**, so the operator
   never types it. The primary takes the next free address of the VIP range
   (`::ffff:n` of the mesh prefix); the invite token names it; the replica
   reads it from the join.
4. **Web gets a pair of files only.** In a cloud mode, Web replicates its
   site files with Syncthing in one direction, from the node that holds
   the VIP, with no database to follow. Core in a cloud mode is a mesh
   member, and in cloud advanced it is the witness.
5. **The release gate of a cloud mode includes BR3**, as the witness site of
   cloud advanced. Single-node passes stay on BR1 and BR2 (0075).

## The screens

All new screens are steps of `keelfirstboot.py` in confconsole. Each step
uses the commit path that exists: stage the description, `keel spec
validate`, commit, `keel spec apply --system-only`.

**Mode** (every node). Simple, Cloud simple or Cloud advanced; only the
modes the appliance's manifest allows are offered (a `modes:` list in
manifest v1, new). It writes `appliance.name`, `installation.mode` and
every overlay of the chain at that mode's column, and applies.

**Role** (cloud modes). Cloud simple: Primary or Replica. Cloud advanced:
Primary, Replica or Witness (the Witness is offered on Core only).

### Simple: one node

| Node 1 |
|---|
| Mode: Simple. The simple column of the chain is applied. |
| No role screen. A database appliance records `database.server.role: standalone`. |

### Cloud simple: two nodes, failover by hand

| Node 1, primary (BR1) | Node 2, replica (BR2) |
|---|---|
| Mode: Cloud simple | Mode: Cloud simple |
| Role: Primary | Role: Replica (the local database is replaced, it says so) |
| `keel mesh create`, then `keel mesh invite`: shows one `keel1:` line, which carries the VIP | Join a mesh: paste the line (`keel mesh join -`) |
| Waits for the member (`keel mesh status`) | `keel vip pair` with node 1, then apply |
| Status: VIP holder, database primary | Status: replica, files follow |

### Cloud advanced: two data nodes and a witness

| Node 1, primary (BR1) | Node 2, replica (BR2) | Node 3, witness, Core (BR3) |
|---|---|---|
| Mode: Cloud advanced | Mode: Cloud advanced | Mode: Cloud advanced |
| Role: Primary | Role: Replica | Role: Witness |
| `keel mesh create`, two invites | Join with invite 1 | Join with invite 2: etcd forms with three voters |
| Waits for `etcd: 3 voter(s)`, then the VIP and the pair | `keel vip pair` with node 1, after etcd has formed, then apply | Status: no data, a vote only |

No password is copied between nodes: only the invite lines. The replication
credential comes over the members' channel from the pair record.

## The guide

For every appliance and every mode, an evidence file in the handbook shows
one column for each node, with the screenshot of each screen of that node in
order, and under it what the operator typed or chose. The screenshots come
from the commissioning run (0075) on the real sites: the VM from the ISO on
BR1 and BR2, and the witness container on BR3.

## What has to be built

- **confconsole:** the Mode step and screen; Join a mesh and Invite a node;
  the Cloud Primary and Replica screens rewritten to `keel mesh` and `keel
  vip pair`; the Witness role; PostgreSQL among the replicating engines.
- **inithooks:** `75keel-role` runs the Mode step before the Role step; a
  described `installation.mode` skips it.
- **keel:** the VIP proposed and carried in the invite; `modes:` in manifest
  v1; the file-only pair for Web; the witness without `appliance.vip` must
  not fail its follow unit.
- **keel-commission (0075):** a contract with several nodes (site, template,
  mode, role, answers); the console driver copies the invite line from one
  node to the next; proofs across nodes (a row written on the primary is
  read through the VIP, one VIP holder, three etcd voters, the file
  direction, one planned promote and its return).

## Not decided here

- Three data nodes (the pair record holds two).
- An invite that can be described in `instance.yaml` before the boot.
- The failover, rejoin and failback choices of 0020.
