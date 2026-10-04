# 0050: The keel: poor networks are the design case, and application files replicate with Syncthing

Date: 2026-10-04
Status: **decided by the maintainer, 2026-10-03 and 2026-10-04**: the
premise on 2026-10-03, while the storage bench was being planned, and the
storage choice, its packaging, the second step, the rejections and the exit
plan on 2026-10-04, after the due diligence and the bench below. Nothing
here is implemented.

## What was asked

0032 made directory replication a generic mesh service on Syncthing, and
0038 made Garage the home for media and backups, both on 2026-09-30 and
both without a measurement. Before Keel Web replicates its first
application's files, the maintainer asked which storage to build in, with
evidence, and set the condition it has to meet: it must work over the
networks Keel's operators actually have, which are often slow, far apart
and lossy. That condition is not specific to storage, so this note records
it first, as a premise for everything that spans nodes, and then the
storage decision that follows from it.

## Why (brief section 10)

1. **Why the current approach is not enough.** Nothing in the handbook
   says what network a multi-node feature is designed for, so each note
   assumes its own, and the tests run between containers on one bridge,
   at well under a millisecond. 0038 chose Garage as "designed for
   geo-distributed nodes on unequal links" without its documented limit,
   200 ms or less, which is below the round trip from Brazil to Europe or
   the United States. 0032 chose Syncthing without numbers either, and
   relied on a receive-only folder "reporting" local changes, which the
   bench shows is true only for new files: an edit to an existing file on
   a replica is overwritten without a trace.
2. **Whether it can be made to work.** It can, if the hot path does not
   cross the network. Measured on 2026-10-03 at 250 ms with jitter and at
   250 ms with 2% loss: with one-way Syncthing, reads, `stat` and writes
   cost the same as at 5 ms (52 ms for 500 files), and only propagation
   slows down (a 200 KB upload reaches the other sites in 2.2 s, 5.1 s with
   loss). Every store that keeps a quorum or a metadata server across the
   WAN pays it on every request: Garage 0.96 s per small read, JuiceFS
   minutes. The database already works this way (0031): reads local,
   writes to one primary.
3. **Why this is better.** A site that is far away, or cut off, keeps
   serving at local speed, and the network only decides how fresh the
   replicas are, never whether a page loads. One writer per application
   matches the one-writer database Keel already runs, so files and
   database fail over together in one step (0020, hard part 3; 0032). The
   data stays plain files in plain directories, so leaving Syncthing is a
   copy, not a migration. And the premise gives every later multi-node
   decision (the mesh, etcd, failover) the same design case and the same
   test profiles, instead of a fast lab.

## Decision

### 1. The premise: the keel

**Everything that spans nodes must work over poor networks**: the mesh
(0024), etcd (0025), database replication (0031), file replication (this
note), file and object storage, and failover. The design case is **250 ms
round trip time**, Brazil to Europe or to the United States, with jitter
and some packet loss. 5 ms is the ideal case, not the design case.

The maintainer's image, which is the meaning of the project's name:

> Every boat, however old, needs a keel. It is old technology, heavy lead
> at the bottom, but it is what keeps the boat stable in hurricanes. [...]
> 5 ms of latency would be ideal, but it is not the reality of everyone on
> planet Earth.[^keel]

**Every multi-node test runs under `tc netem`** with at least these
profiles, and the decision or the PR states the measured behaviour in each:

| Profile | Round trip | Loss |
| --- | --- | --- |
| ideal | 5 ms | none |
| regional | 100 ms ±10 ms | none |
| design case | 250 ms ±25 ms | none |
| design case, lossy | 250 ms ±25 ms | 2% |
| partition and heal | one node cut off under the design case, then healed | 100% while cut off |

The bench of 2026-10-03 is the reference
implementation: one egress qdisc per container veth on the host, each
carrying half the round trip and half the jitter.

### 2. The design rule that follows

**The per-request hot path stays local, and only changes are replicated.**

- **Application code and static assets come from the package or the
  image**, identical on every node, and are never on a distributed or
  replicated file system. At 250 ms a `stat` and `open` over a network
  store cost 1 to 6 s per file in the bench, and a WordPress request opens
  hundreds; locally it is 0.1 ms. Sites update code by package (0039).
- **Database reads are local; writes go to the primary** (0031).
- **Only user data is replicated by file**: what an application writes at
  run time and keeps on a filesystem.

### 3. Application files: Syncthing

**Syncthing replicates application files**: WordPress uploads
(`wp-content/uploads`) first, and later Nextcloud's data directory, in
active/passive.

- **One writer per application.** The primary's folder is **send-only**;
  every replica's is **receive-only**, with **versioning on**.
- **The folder direction flips on promote and demote**, driven by keel's
  role (0049), in the same operation that promotes the database and moves
  the VIP. Nextcloud's promotion also runs `occ files:scan --all`, since its
  file cache lives in its database.
- **It is built into Keel Web as a component**: the `syncthing` overlay in
  `common`, by the overlay pattern of 0036, so every application on Keel
  Web gets it without carrying its own. Each application declares its
  folders in its manifest (`state.replicate` and `state.exclude`, 0041);
  keel derives the Syncthing configuration from them and from the role.
  Nothing about folders is typed by an operator.
- **How it runs**, from the bench: as a dedicated system user, not root;
  discovery, relays and NAT traversal off, peers at their overlay
  addresses; the filesystem watcher on with a short delay (1 s in the
  bench, against the default 10 s); keel monitors `receiveOnlyChangedFiles`
  and `needFiles` on every replica.

### 4. Packaging

Debian 13 has `syncthing` 1.29.5, on a v1 branch upstream has frozen
(v1.30.0, July 2025, was the last v1 release; further v1 releases only for
serious security problems). v2 is not packaged in any Debian suite, and the
package in testing was marked for autoremoval on 2026-10-13 over transitive
bugs. So:

- **Keel carries a v2 `.deb` in the Keel repository for now**, built from
  upstream source, under 0039.
- **Keel offers the work to the Debian Go Packaging Team**, which maintains
  the Debian package, through the existing Debian packaging effort
  (tracker#15). When Debian ships v2, Keel uses Debian's.
- **v1 and v2 interoperate on the wire**, so a mesh with mixed versions
  during the transition is safe.

### 5. Second step, not a replacement: Garage

**Garage is the designated second step** for many-writer, strongly
consistent object storage **within one region**: Nextcloud primary storage
on a new instance, and backups. It is not used across 250 ms links.

- **Revisit it only when it is in Debian and measured on Keel's own
  sites.** Today it is not in any suite; #1118368 is an RFP, not an ITP,
  with about 17 Rust crates still missing on 2026-09-02.
- **Its documented limit is 200 ms or less** between nodes (with 50 Mbps or
  more), below the design case. In the bench it worked at 250 ms, slowly:
  every request pays a quorum round trip.
- **Its CONTRIBUTING forbids contributions made with AI agents.** That
  limits how Keel can carry fixes upstream, and is one more reason not to
  depend on it for the first step.
- In the bench it was the only candidate that **refused a minority write**
  (HTTP 503 in 0.2 s) instead of diverging, and it lost nothing. That is
  what earns it the second step.

### 6. Rejected

- **JuiceFS between sites.** The community edition has one central
  metadata engine, so every `open` and `stat` from a remote site crosses the
  WAN (4 to 7 round trips each in the bench); on a partition the cut-off
  node's file calls hung and its session was cleaned up by the others; a
  50 MB write failed with EIO at 250 ms with loss. Cross-region metadata is
  in its closed enterprise edition only.
- **GlusterFS.** It does not run in an unprivileged LXC container (bricks
  need `trusted.*` extended attributes, which need `CAP_SYS_ADMIN` in the
  initial user namespace; reproduced in the bench), its replication is
  synchronous, the project is in maintenance with no release in 15 months,
  and Proxmox VE 9 dropped it.
- **MinIO Community Edition** is archived upstream; it was already set
  aside in 0038 and is now out of the question.

### 7. The replica warning, and why it exists

**Syncthing silently overwrites an edit made on a receive-only replica**
once the primary sends a newer version of the file, and keeps no
`.sync-conflict` copy. This was observed in the bench's partition case: a
file appended on the cut-off replica and on the primary held the
primary's version on all three nodes after the heal, with no trace of the
replica's edit. A new file created on a replica is the other case: it
stays there, never propagates, is never removed until an operator reverts
local changes, and is the one case the folder reports
(`receiveOnlyChangedFiles`).

That is the one-way design working as intended, and it is why a replica
must be read-only to the application and why the Webmin warning on
replicas exists: its file paragraph says changes there "are overwritten
by it", and this is the mechanism (tracker#57, decided in
[0049](0049-webmin-per-role-and-the-mesh-vip.md)). Versioning on the
replicas is what can keep a copy of an overwritten edit; see "Open
points".

### 8. Exit plan

The data stays plain files in plain directories on every node, with no
format that needs Syncthing to read it. If Syncthing has to be replaced:

1. **lsyncd plus rsync, or Unison**: the same one-writer model, both in
   Debian. (0032 rejected lsyncd as the first choice; it stays the exit.)
2. **Garage plus an S3 offload plugin** for WordPress, or Nextcloud on S3
   primary storage on a new instance, **migrated with rclone**.

Syncthing's index database is discarded; nothing else changes.

## The evidence

Two reports of 2026-10-03, copied into the handbook with this note:
the due diligence
([docs/evidence/2026-10-03-storage/due-diligence.md](../evidence/2026-10-03-storage/due-diligence.md))
and the bench
([docs/evidence/2026-10-03-storage/bench.md](../evidence/2026-10-03-storage/bench.md)),
with host names and addresses masked in the bench.

### The bench at the design case

Three unprivileged LXC containers from the Keel Web image on one host, the
WAN emulated with `netem`, stores on tmpfs so the network is isolated.
Medians of three runs, except JuiceFS at these profiles (one run each).
Syncthing was Debian's 1.29.5, send-only to receive-only; Garage v2.4.1,
three zones, replication factor 3, `consistent`; JuiceFS 1.4.1 on a
three-member etcd and Garage.

| Measure | Syncthing 250 ms | Syncthing 250 ms, 2% loss | Garage 250 ms | Garage 250 ms, 2% loss | JuiceFS 250 ms | JuiceFS 250 ms, 2% loss |
| --- | --- | --- | --- | --- | --- | --- |
| One 200 KB upload: the writer returns | 1 ms | 1 ms | 2.0 s | 6.2 s | 6.8 s | 8.6 s |
| One 200 KB upload: on all three nodes | 2.2 s | 5.1 s | 2.6 s | 12.4 s | 9.6 s | 9.9 s |
| Reading it on another node | 1 ms | 1 ms | 280 ms | 537 ms | 5.4 s | 4.3 s |
| 500 × 4 KB `stat`, `open` and read on a replica | 52 ms | 52 ms | 482 s | 570 s | 3,099 s | 347 s for 50 files |
| 100 × 200 KB: on all three nodes | 14.5 s | 312 s | 91.0 s | 354 s | 1,324 s | 1,594 s |
| 50 MB: on all three nodes | 31.8 s | 803 s | 12.0 s | 727 s | 15.5 s | failed (EIO) |

Syncthing's per-request numbers do not move with the network. Its bulk
propagation does: with 2% loss one TCP connection per peer is capped near
85 KiB/s, and Garage moves a large file as fast or faster. That is
replication lag, which the design accepts, not latency a visitor sees.

### The partition and heal case

One node cut off for at least 120 s under the design case, writes on the
primary, a write attempted on the cut-off node:

- **Syncthing**: the majority side kept writing locally (20 files in
  13 ms, on the second node 11.6 s later); the cut-off node accepted a
  local write; after the heal it had everything in 18 s, with identical
  checksums. The replica's edit to an existing file was overwritten and
  its new file stayed local only (section 7).
- **Garage**: the cut-off node's write was refused in 0.2 s, and nothing
  was lost. But while the node silently dropped packets, each write on the
  majority side took 18 s, and the local block copies finished 19 minutes
  after the heal.
- **JuiceFS**: each write on the majority side took 57 s, across an etcd
  re-election; the cut-off node's write hung and never landed; its session
  was cleaned up as stale.

### The due diligence scores (out of 25)

| Candidate | License | Health | Debian | At 250 ms | Operations | Total |
| --- | --- | --- | --- | --- | --- | --- |
| **Syncthing** | 5 | 4 | 3 | 4 | 5 | **21** |
| Ceph (RGW multisite) | 4 | 5 | 4 | 2 | 1 | 16 |
| **Garage** | 3 | 4 | 1 | 3 | 4 | **15** |
| MooseFS CE | 4 | 2 | 4 | 1 | 3 | 14 |
| JuiceFS CE | 5 | 4 | 1 | 1 | 2 | 13 |
| SeaweedFS | 4 | 3 | 1 | 3 | 2 | 13 |
| GlusterFS | 4 | 1 | 4 | 1 | 2 | 12 |
| MinIO CE, LizardFS | | | | | | excluded: archived, dead |

Ceph's total comes from its health and packaging; it does not run in
unprivileged LXC and needs a cluster per site and a specialist to run.
Syncthing's main risks are its Debian packaging (section 4) and its bus
factor: one maintainer wrote 63% of the last year's commits.

## How it is carried out

1. **Packaging** (0039, tracker#15): a `syncthing` v2 source package in
   the Keel repository, built from upstream's source; the offer to the
   Debian Go Packaging Team.
2. **`keel-overlay-syncthing`** in `common` (0036): the unit running as a
   dedicated user, the configuration derived from the manifests' folders
   and the role (discovery, relays and NAT off; peers on the overlay;
   versioning on receive-only folders; watcher delay), and the Monit checks
   of `receiveOnlyChangedFiles` and `needFiles` (0040).
3. **keel**: the folder flip in promote and demote, with the database and
   the VIP (0049); the report of local changes on a replica in `keel diff`
   and in the alert.
4. **Keel Web and the WordPress image**: the overlay in Keel Web's
   composition; WordPress's manifest replicates `wp-content/uploads`, and
   its themes and plugins come from packages.
5. **The test harness**: the netem profiles of section 1 as a shared
   script used by every multi-node test (the mesh join of 0048, the VIP and
   rejoin of 0049, replication here).

Done when, on built images and not on machines assembled by hand: two
WordPress containers over WireGuard under each netem profile; an upload on
the primary is served by the replica, and a page on the replica loads as
fast at 250 ms with 2% loss as at 5 ms; `keel database promote` flips the
folders with the database; an edit on a replica is reported, kept by
versioning, and alerted; the partition and heal case leaves identical
checksums.

## Consequences

- Every multi-node feature is designed for 250 ms with loss and is tested
  under the five profiles; a PR that spans nodes states its results under
  them.
- Application code is never replicated by file; an application whose
  code is changed at run time (a plugin installed from WordPress's admin
  page, say) needs a decision of its own (see "Open points").
- Only one node of a pair accepts uploads at a time; a replica serves
  them, read-only, seconds to minutes behind.
- Keel carries one more package of its own, Syncthing v2, until Debian
  ships it.
- Object storage (0038) moves from the recommended home for media to a
  later, regional option; WordPress uploads stay on a filesystem.
- 90 MiB of RAM per replica, about 180 MiB on the sending node, for
  Syncthing (bench, idle at 250 ms).

## Open points

1. **One writer at a time does not scale** (Keel-Linux/tracker#58). This
   is the main open point, and it is an open problem, not an accepted
   limit: an application that needs several sites writing the same files
   at once has no answer here. Garage within a region is the known
   direction, not yet a decision.
2. **Syncthing v2 is not measured.** The bench ran Debian's 1.29.5. v2 is
   what Keel will ship; its multiple connections per peer may help the
   lossy case, and its numbers have to be taken under the same profiles
   before it replaces the bench's.
3. **Versioning on the replicas was not enabled in the bench.** That it
   keeps a copy of an edit the primary overwrites is the documented
   behaviour and has to be shown on Keel's images (the "done when" above).
4. **The rejoin check for files in 0049** relies on the receive-only
   folder's report of local changes. The report covers new files only, so
   an old primary's edits to existing files, made while it was cut off,
   would be overwritten without being reported. The check needs versioning
   or its own comparison before the flip.
5. **Not covered by the bench**: a partition of the primary itself, the
   promote and demote flip, real disks (on the test host's own disk
   Syncthing was disk bound, 40 s for 100 small files at every round
   trip), BBR, and a running WordPress or Nextcloud rather than synthetic
   files.
6. **Run-time code**: WordPress plugins and themes installed from its
   admin page land in `wp-content`, outside `uploads`, and would be on the
   primary only.
7. **Which modes replicate files**: docs/manifest-v1.md derives Syncthing
   folders in cloud advanced only, while 0049 has a file replica, and its
   warning, in cloud simple. Which one holds is for the implementation of
   the overlay to settle.

## What this amends

- **0032, "Resolved"**: Syncthing stands, now with evidence; a
  receive-only folder reports local changes only for new files, and
  overwrites edits to existing ones without a conflict copy (section 7).
  Versioning on receive-only folders is added. Debian's 1.29.5 is replaced
  by Keel's v2 package. Lsyncd stays rejected as the first choice and
  becomes part of the exit plan.
- **0038**: Garage is the second step, regional only, not the recommended
  home for media; its documented limit (200 ms or less) and its Debian
  state (#1118368 is an RFP, not an ITP) correct the note. Backups stay a
  use for it. Its relation to 0032, "fewer paths to replicate by file",
  no longer holds for WordPress uploads.
- **0036**, the packages table: syncthing becomes "Keel packages v2
  (0039); Debian's 1.29.5 is a frozen v1 branch", and the `s3` (Garage)
  row reads RFP #1118368, not ITP. Keel Web's composition gains the
  `syncthing` overlay.
- **0041 and docs/manifest-v1.md**, the WordPress example: `state.replicate`
  is `wp-content/uploads`, not `wp-content`; themes and plugins are code
  from packages. The rule that folders are derived, never declared by an
  operator, is unchanged and applied.
- **0049, "Replicated files"** under "The old primary coming back": see
  open point 4. Its warning for file replicas is unchanged and now has its
  observed cause.
- **0003**: unchanged on coverage; a multi-node test also runs under the
  netem profiles of section 1.
- **0024, 0025, 0031 and 0048**: unchanged in what they decide; the premise
  sets their design case, and their tests run under the profiles. The bench
  kept etcd stable at 250 ms with a heartbeat of 300 ms and an election
  timeout of 3 s, and it still re-elected under loss and partition.

[^keel]: The maintainer, 2026-10-03, in Portuguese: "Todo barco, por mais
    antigo que seja, ele precisa de uma quilha. É uma tecnologia antiga,
    chumbo, pesado embaixo, mas é o que garante que ele seja estável, que
    ele consiga enfrentar condições de tempo muito violentas, furacões e
    situações desse tipo. [...] Obviamente, se a gente tiver uma latência
    de 5 milissegundos, seria o ideal. Mas não é a realidade de todo mundo
    no planeta Terra."
