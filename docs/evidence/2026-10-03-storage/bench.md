# Keel Web: replicated file storage over poor networks

> Copied into the handbook on 2026-10-04 as evidence for decision 0050
> ([docs/decisions/0050-the-keel-poor-networks-and-file-replication.md](../../decisions/0050-the-keel-poor-networks-and-file-replication.md)). This is the bench report as written on 2026-10-03,
> with host names, container addresses and MAC addresses masked. The `raw/`
> directory it refers to (scripts, JSONL results, logs) was not copied.

Comparative bench, 2026-10-03. A test VM, three throwaway unprivileged LXC
containers from the Keel Web step10 image. The WAN was emulated with
`tc netem`. All containers ran on one physical host, so see "Limits" before
reusing any number.

## Answer first

At the design case (250 ms RTT, P3 and P4), only **Syncthing (one-way,
primary to replicas)** keeps every per-request operation local. Reads and
`stat` cost the same at 250 ms + 2% loss as at 5 ms (about 50 ms for 500
files). Only replication slows down. **Garage** is the only candidate here
that does real multi-writer, strongly consistent object storage across 3
sites, but each request pays WAN round trips: a 200 KB PUT took 2.0 s at P3
and 6.2 s at P4. It also degrades badly while one site is unreachable. **JuiceFS
on etcd + Garage** was one to two orders of magnitude slower than both, lost a
50 MB write with EIO at P4, and is not fit for a 250 ms WAN. **GlusterFS** cannot
run in an unprivileged container at all.

Recommendation, detailed at the end: package code and static assets in the
`.deb`; serve `wp-content/uploads` from the local disk and replicate it with
Syncthing from one write primary; keep Garage for objects where many sites
must write and strong consistency matters more than latency (Nextcloud
primary storage on a regional cluster, backups). Do not use JuiceFS or GlusterFS
across sites.

## Setup

| Item | Value |
|---|---|
| Host | test VM, Debian 13, kernel 6.12.107+deb13-amd64, 4 vCPU, 3.9 GiB RAM, LXC 6.0.4, iproute2 6.15.0 |
| Image | `debian-13-keel-web_19.0-3+step10-20261003_amd64.tar.zst`, sha512 `ab567e8a…3f7f2001`, matches the local `.sha512`. An identical copy (same sha512) was already in `/root/images` on the test host, so it was not copied again. |
| Containers | `sb1`, `sb2`, `sb3`, unprivileged (idmap 200000/265536/331072 +65536), each on `lxcbr0` (addresses masked), memory.max 1300M, `/dev/fuse` bind-mounted per container (`lxc.mount.entry` + `lxc.cgroup.devices.allow = c 10:229 rwm`). No global LXC or host config was changed. |
| Roles | sb1 = writer (primary site). sb2, sb3 = other sites. Propagation was measured on sb2 and sb3. Reads and `stat` ran on sb2. |
| Storage under test | a tmpfs `/bench` (800M) in each container, see "Disk note" |
| Stopped in containers | fail2ban, monit, postfix (to free RAM; none are on the file path) |

**Versions**

| Component | Version | Source |
|---|---|---|
| Syncthing | 1.29.5~ds1-2 | Debian 13 package |
| etcd | 3.5.16-4 (`etcd-server`, `etcd-client`) | Debian 13 package |
| rclone | 1.60.1+dfsg-4 | Debian 13 package |
| GlusterFS | 11.1-6 (`glusterfs-server`, `glusterfs-client`) | Debian 13 package |
| fuse3 | 3.17.2-3 | Debian 13 package |
| python3-boto3 / botocore | 1.37.9-1 / 1.37.9+repack-1 | Debian 13 package (measurement client) |
| Garage | v2.4.1, `x86_64-unknown-linux-musl`, sha256 `ae49f8de4aaee6b5ca305f7cbdccc8cd8a29b2804aac074649f18bfb83d0a2b6` | **upstream static binary** (not in Debian), from `garagehq.deuxfleurs.fr/_releases/v2.4.1/`, in containers only |
| JuiceFS | 1.4.1+2026-07-30.0b90c7d, sha256 `1e111b642668992e04d62377e218a24e263f76af12370facb9097353e5b8d208` | **upstream static binary** (not in Debian), GitHub release `juicefs-1.4.1-linux-amd64.tar.gz`, in containers only |

**Network profiles.** A host-side egress `netem` qdisc sat on each
container's veth (`vsb1..3`). A packet between two containers crosses exactly
one of them, so each qdisc carried half the RTT and half the jitter. Loss
applied once per packet, in each direction.

| Profile | Per-veth netem | Measured |
|---|---|---|
| P1 | `delay 2.5ms` | ping 5.2 ms min RTT |
| P2 | `delay 50ms 5ms` | 100 ms ±10 ms |
| P3 | `delay 125ms 12.5ms` | 250 ms ±25 ms |
| P4 | `delay 125ms 12.5ms loss 2%` | as P3 plus 2% loss per packet |
| P5 | P3, then sb3 partitioned: `netem loss 100%` on egress plus an ingress `matchall action drop`, then healed back to P3 | |

**Jitter control.** netem jitter reorders packets, so I checked whether that
alone was hurting TCP. A single TCP stream (curl, 30 s) between two containers
got 1706 KiB/s at P3 and 1706 KiB/s at P3 without jitter. It got 87 KiB/s at P4
and 84 KiB/s at P4 without jitter. Jitter had no measurable effect. The
**2% loss** is what costs: a single TCP CUBIC stream at 250 ms RTT is capped
near 85 KiB/s. BBR is not loaded on the host, and loading it would have
changed the host, so it was not tested.

**Disk note.** The first Syncthing run used the container rootfs on the VM
disk. A 4 KiB `O_DSYNC` write took about 140 ms there (`dd … oflag=dsync`: 50
writes in 7.2 s). The disk, not the network, then dominated: 100 × 200 KB took
40 s to reach the replicas at P1, P2 and P3 alike (raw file
`raw/results-st-disk.jsonl`). It would also have crippled etcd, whose WAL
fsyncs every commit. All stores therefore ran on tmpfs, so the results isolate
the network. **On real sites the disk adds its own fsync cost**, and Keel
hosts need SSD/NVMe for any of these.

## Method

Every measure was taken by one helper, `bench.py`, run inside the containers.
Timestamps come from the shared host clock, so they are comparable across
containers.

- (a) **Write**: sb1 copies 100 × 200 KB random files (`f000..f099.jpg`), then 1 × 50 MB,
  - POSIX stores (Syncthing folder, JuiceFS mount): sequential `open/write/fsync/close` per file.
  - Garage: `rclone copy` / `rclone copyto` through the S3 API on sb1's local endpoint (rclone default 4 transfers, `--s3-no-check-bucket --no-traverse`).
  - "writer done" = the writer returned. "on all 3 nodes" = from write start until **both** sb2 and sb3 see every file at full size. Pollers: `os.scandir` every 50 ms (POSIX) or `ListObjectsV2` every 50 ms (Garage, local endpoint).
- (b) **Single file**: one 200 KB file written on sb1 (Garage: one boto3 `PutObject`, like an offload plugin). Measured: writer latency, visibility on sb2+sb3, then a full read on sb2.
- (c) **Metadata-heavy**: 500 × 4 KB `.php` files seeded once. sb2 does sequential `os.stat` + `open` + `read` + `close` for each (Garage: `HeadObject` + `GetObject`).
- (d) **P5**: see its section.
- (e) **Idle**: RSS of the candidate's processes (`/proc/<pid>/status`) and CPU over 60 s (utime+stime), at P3 after the runs.
- Each measure was repeated 3 times and the **median** is given. Exceptions are marked `n=`.
- Run directories were deleted after each repetition.

**Fewer repetitions for JuiceFS.** JuiceFS P1 has 3 repetitions. P2, P3 and P4
have **1 each**. One JuiceFS repetition took 40 min at P2 and 90 min at P3. The
500-file `stat` alone took 52 min at P3, so at P4 it was cut to **50 files**. The
gap to the other candidates is one to two orders of magnitude, so extra
repetitions would not change the decision.

**Overlap.** Garage P4 repetition 1 overlapped Syncthing P4 repetitions 2 and 3.
netem has no rate limit, so the flows did not share bandwidth, and the
repetitions that ran alone gave the same numbers (Garage 100 files: 350, 351,
351 s).

## Results by candidate (median of 3 unless marked)

### 1. Syncthing, one-way (sb1 `sendonly`, sb2/sb3 `receiveonly`, full mesh)

| Measure | P1 | P2 | P3 | P4 |
|---|---|---|---|---|
| (a) 100 x 200 KB: writer done | 67 ms | 53 ms | 59 ms | 63 ms |
| (a) 100 x 200 KB: on all 3 nodes | 2.5 s | 6.3 s | 14.5 s | 312 s |
| (a) 1 x 50 MB: writer done | 112 ms | 78 ms | 103 ms | 118 ms |
| (a) 1 x 50 MB: on all 3 nodes | 3.3 s | 15.1 s | 31.8 s | 803 s |
| (b) 1 x 200 KB: writer done | 1 ms | 1 ms | 1 ms | 1 ms |
| (b) 1 x 200 KB: on all 3 nodes | 1.3 s | 1.7 s | 2.2 s | 5.1 s |
| (b) read on sb2 of file written on sb1 | 1 ms | 1 ms | 1 ms | 1 ms |
| (c) 500 x stat+open+read, 4 KB | 49 ms | 47 ms | 52 ms | 52 ms |

How to read this table:

- Writes and reads are always local.
- Visibility includes the 1 s filesystem-watcher delay (`fsWatcherDelayS=1`; the default is 10 s).
- At P4 one TCP connection per peer is loss-bound, at about 85 KiB/s. The P4 single-file times (5.1 s) show that small uploads still propagate in seconds.

### 2. Garage, 3 zones, replication_factor 3, consistency_mode "consistent"

| Measure | P1 | P2 | P3 | P4 |
|---|---|---|---|---|
| (a) 100 x 200 KB: writer done (rclone, 4 parallel) | 3.6 s | 39.9 s | 91.2 s | 351 s |
| (a) 100 x 200 KB: on all 3 nodes | 3.7 s | 39.9 s | 91.0 s | 354 s |
| (a) 1 x 50 MB: writer done | 2.1 s | 5.7 s | 12.0 s | 717 s |
| (a) 1 x 50 MB: on all 3 nodes | 2.2 s | 5.8 s | 12.0 s | 727 s |
| (b) 1 x 200 KB: writer done (one PutObject) | 60 ms | 830 ms | 2.0 s | 6.2 s |
| (b) 1 x 200 KB: on all 3 nodes | 155 ms | 1.1 s | 2.6 s | 12.4 s |
| (b) read on sb2 of file written on sb1 | 18 ms | 116 ms | 280 ms | 537 ms |
| (c) 500 x HEAD+GET, 4 KB | 39.7 s | 183 s | 482 s | 570 s |

How to read this table:

- Writes return only after a quorum of 2 sites has the data, so "on all 3 nodes" equals "writer done". The small positive gap is the poller's own `List` round trip, not staleness: Garage is read-after-write consistent.
- Every request, reads included, pays at least one WAN round trip for the quorum: 0.96 s per HEAD+GET pair at P3. Seeding 500 × 4 KB objects with rclone at P4 took 488 s.

### 3. JuiceFS: metadata in etcd (3 members), data in Garage bucket `jfs`, FUSE mount on each node

etcd ran with `--heartbeat-interval 300 --election-timeout 3000`, tuned for
250 ms RTT. The etcd leader was on sb3 for the P1–P4 runs, so it was neither
the writer nor the reader. JuiceFS mounted with its default caches (1 s
attr/entry), `--cache-size 256`, and `--trash-days 0` at format time.

| Measure | P1 | P2 (n=1) | P3 (n=1) | P4 (n=1) |
|---|---|---|---|---|
| (a) 100 x 200 KB: writer done | 16.7 s | 302 s | 760 s | 1057 s |
| (a) 100 x 200 KB: on all 3 nodes | 16.8 s | 322 s | 1324 s | 1594 s |
| (a) 1 x 50 MB: writer done | 2.0 s | 5.3 s | 11.8 s | **failed: EIO after about 12 min** |
| (a) 1 x 50 MB: on all 3 nodes | 2.2 s | 7.2 s | 15.5 s | never (> 1500 s) |
| (b) 1 x 200 KB: writer done | 158 ms | 2.3 s | 6.8 s | 8.6 s |
| (b) 1 x 200 KB: on all 3 nodes | 237 ms | 4.5 s | 9.6 s | 9.9 s |
| (b) read on sb2 of file written on sb1 | 74 ms | 1.3 s | 5.4 s | 4.3 s |
| (c) 500 x stat+open+read, 4 KB | 22.5 s | 669 s | **3099 s** | 347 s for **50** files (6.9 s/file) |

How to read this table:

- JuiceFS is strongly consistent. The "on all 3 nodes" times at P3 and P4 are inflated by how slowly the pollers can even list 100 files: 16 polls in 22 min.
- Probe at P2: one `stat` took 0.4–0.7 s and one `open` took 0.1–0.5 s, which is 4–7 RTT per operation. Each metadata transaction does linearizable reads (a ReadIndex round trip to the leader) plus a forwarded commit.

**Cache-tuned variant (P3, sb2 remounted with `--attr-cache=3600 --entry-cache=3600 --dir-entry-cache=3600 --open-cache=3600`, 50 files):**

- First pass: 101.8 s (2.0 s/file).
- Second and third passes: 37 ms and 29 ms.

Long caches make warm code reads local, but the client gets no cross-node
invalidation. Another site's change can stay invisible for up to the cache TTL,
which is the same trade as Syncthing without its simplicity.

### 4. GlusterFS replica 3: does not fit unprivileged containers

- glusterd 11.1 started in all three containers, and `gluster peer probe` worked (2 peers Connected).
- `gluster volume create gv replica 3 …/bench/gl/brick … force` failed: `Glusterfs is not supported on brick … Setting extended attributes failed, reason: Operation not permitted`.
- The cause: bricks need `trusted.*` xattrs (`trusted.gfid`, `trusted.glusterfs.volume-id`). The kernel allows `trusted.*` only with CAP_SYS_ADMIN in the **initial** user namespace. `setfattr -n trusted.test` fails in the container, while `user.test` works.
- It would need privileged containers or the host, which goes against Keel's unprivileged-container design. It was not measured further.

## (d) Partition, P5 (under P3; sb3 cut off; writes on sb1, a write attempted on sb3)

| | Syncthing | Garage | JuiceFS |
|---|---|---|---|
| Partition length | 120 s | **367 s** (see note) | **1290 s** (see note) |
| Writes on the majority side continue? | yes, local. 20 × 200 KB written in 13 ms. sb2 had them 11.6 s later | yes, but **20 PUTs took 363 s (18 s each)** while sb3 was silently unreachable | yes, but **20 files took 1137 s (57 s each)**, including an etcd re-election (term 4 → 5, leader sb3 → sb1) |
| Write on the cut-off node | accepted locally (receive-only replica) | **rejected in 0.2 s**: `Could not reach quorum of 2 … 1 of 3 request succeeded` (HTTP 503) | **hung > 60 s** and never landed (directory absent after heal). sb3's JuiceFS session was declared stale and cleaned by the others ("Session 2 was stale and cleaned up, but now it comes back again") |
| After heal: cut-off node sees all writes | 18 s | 3.3 s through the S3 API (quorum reads). **Local block copies complete only after 1140 s (19 min)** of resync | 67 s |
| Data checksums after heal (sha1 of all 20 files on sb1, sb2, sb3) | identical | identical | identical |
| Conflicts / data loss | see below | none. The minority write was refused, so nothing was lost silently | none for acknowledged writes. The minority write never happened, and the client got no clear error within 60 s |

**Partition length note.** The script slept "120 s minus the time already
spent". For Garage and JuiceFS, the writes during the partition took longer
than 120 s, so the partition lasted 367 s and 1290 s. Those two numbers are
themselves the finding: with one site silently dropping packets, both
quorum systems slowed every write by 10–60×, instead of excluding the site
quickly.

## Conflicts and data loss seen

1. **Syncthing, edit on a receive-only replica, then a newer edit on the primary.**
   - During P5, `php/p000.php` was appended on sb3 (`changed-on-sb3`) and on sb1 (`changed-on-sb1`).
   - After heal, all three nodes held sb1's version. **sb3's local edit was silently overwritten**: no `.sync-conflict` copy was kept.
   - This is the one-way design working as intended, but replicas must be read-only for the application.
2. **Syncthing, new file created on a replica.**
   - `p5-sb3-local.jpg` stayed only on sb3. The folder reported `receiveOnlyChangedFiles: 1`.
   - It never propagates and is never deleted unless an operator presses "Revert local changes".
   - This is divergence, not loss.
3. **JuiceFS at P4: a 50 MB write failed with EIO.**
   - Garage PUTs of 4 MiB blocks hit S3 client timeouts (`request send failed … exceeded maximum number of attempts`), and JuiceFS reported `write inode:1142 error: input/output error`.
   - The application saw the error, so the loss was not silent, but the upload was lost.
4. **JuiceFS: stale sessions.**
   - Under P4 and during P5, a client whose session refresh could not reach etcd was "cleaned up" by the other clients. It came back when the network did.
   - JuiceFS uses sessions to keep open-but-unlinked files and locks, so a long WAN hiccup can drop that state.
5. **Garage**: no conflicts and no loss.
   - Minority writes fail fast with 503.
   - Last-writer-wins applies to concurrent PUTs of the same key. That was not exercised here.

## (e) Idle RAM and CPU per node (P3, 60 s)

| Candidate | sb1 | sb2 | sb3 |
|---|---|---|---|
| Syncthing (2 processes: monitor + main) | 183 MiB, 0.18% | 90 MiB, 0.18% | 87 MiB, 0.13% |
| Garage | 40 MiB, 0.20% | 33 MiB, 0.20% | 35 MiB, 0.22% |
| JuiceFS stack: etcd + juicefs mount (3 processes) | 264 MiB, 3.6% | 255 MiB, 4.0% | 246 MiB, 3.7% |
| plus the Garage under JuiceFS | 43 MiB, 0.63% | 36 MiB, 0.70% | 43 MiB, 0.70% |

sb1's Syncthing RSS is the Go heap after sending everything. The receivers sat
near 90 MiB.

## (f) Operational complexity

| | Syncthing | Garage | JuiceFS | GlusterFS |
|---|---|---|---|---|
| Packages | 1 Debian package | 1 upstream static binary (not in Debian) | 1 upstream static binary + Debian `etcd-server` + Garage (as above) + `fuse3` | Debian `glusterfs-server` |
| Container needs | nothing special | nothing special | `/dev/fuse` in the container (per-container config) | privileged (trusted xattrs): **blocker** |
| Config written here | about 25 lines generated into `config.xml` (folder, type, 2 peers with static addresses, discovery/relays/NAT off, watcher 1 s) | 17-line TOML + 7 CLI steps (connect, layout assign × 3, apply, bucket, key, allow) | etcd: 9 flags per member; JuiceFS: 1 `format` + 1 `mount` per node; plus all of Garage | n/a |
| Moving parts per site | 1 daemon | 1 daemon | 3 daemons (etcd, juicefs, garage) and 2 quorum systems | 2+ daemons |
| Failure modes seen | none in transport. Replica edits overwritten or orphaned. Slow catch-up under loss (one TCP connection per peer) | silent peer partition → 18 s per write. Block resync takes ~19 min after heal. 3.9 s per small PUT at P4 | EIO on a 50 MB write at P4; stale-session cleanup; hung FUSE calls on the cut-off node; etcd re-elections at P4/P5 | cannot create a volume unprivileged |
| Gotchas | Must not run as a system user in production (warning shown). Needs a folder marker. An old index DB from a different path put the folder in "folder marker missing" error state until the DB was reset. | Region must match `s3_region` for clients (set to `us-east-1`). Path-style addressing. | `--trash-days 0` or deleted data lingers. Metadata latency depends on where the etcd leader is. | |

## Recommendation for Keel Web

Principle: **the per-request hot path stays local, and only changes are
replicated.**

1. **Code, themes, plugins and core static assets: from the package, never from a replicated store.**
   - In this bench a stat+open of code over any network store cost 1–6 s per file at 250 ms. A WordPress request opens hundreds.
   - The local copy costs 0.1 ms per file. Opcache helps but does not remove the stat calls (`opcache.validate_timestamps`).
   - Ship it in the `.deb` or the image; sites update by package.
2. **WordPress `wp-content/uploads`: Syncthing, one write primary, receive-only replicas.**
   - Uploads land on local disk at local speed. Every site serves them locally (0.05 ms per stat).
   - Propagation of a typical 200 KB upload: 2.2 s at P3, 5.1 s at P4.
   - A 50 MB file takes 32 s at P3 and about 13 min at P4. That is acceptable for media, and it does not block anyone.
   - Requirements:
     - (i) only the primary site accepts admin uploads, which matches a single-writer WordPress database;
     - (ii) replicas must be read-only to PHP, because local edits are overwritten or orphaned (see Conflicts 1–2);
     - (iii) Keel should monitor `receiveOnlyChangedFiles` and `needFiles`;
     - (iv) run Syncthing as a dedicated user;
     - (v) set `fsWatcherDelayS` low.
   - Failover of the primary is a Keel decision (promote one replica to `sendonly`), not something Syncthing does.
   - Lowest RAM after Garage, about 90 MiB per replica.
3. **Garage: where several sites must write the same namespace and strong consistency matters more than latency.**
   - It is the only candidate that refused a minority write instead of diverging, and it lost nothing.
   - Use it behind an S3-aware application, with local caching:
     - Nextcloud primary object storage inside **one region**, with sites within a few tens of ms of each other;
     - off-site backup target;
     - an S3 offload plugin if Keel ever needs multi-writer uploads.
   - Do not put it on a per-request path across 250 ms links: 0.5–1 s per HEAD+GET.
   - Two items must be tested before production:
     - the 18 s per-write stall while a peer silently drops packets;
     - the ~19 min block resync after heal.
4. **Nextcloud data across continents.**
   - None of these gives multi-writer POSIX at 250 ms with usable latency.
   - Options:
     - (a) one primary site with Syncthing-style one-way replicas for disaster recovery;
     - (b) Garage as primary storage within a region, with cross-region replicas for disaster recovery only.
   - Nextcloud's file locking and database must stay at the primary in both cases.
5. **Not recommended across sites:**
   - JuiceFS on etcd: metadata costs 4–7 RTT per operation, 52 min for 500 stats at P3, EIO at P4, stale sessions.
   - GlusterFS: impossible unprivileged. Its replica writes are synchronous and would also pay the WAN on every write.

**For the Keel design notes:**

- etcd timeouts tuned for 250 ms (heartbeat 300 ms, election 3 s) kept the cluster stable, but it still re-elected under P4/P5. Anything that does a quorum round trip per request will feel that.
- Under 2% loss a single TCP stream tops out near 85 KiB/s. Replication that uses one connection per peer (Syncthing) or per object (Garage multipart) benefits from parallel streams or BBR. BBR is per network namespace and needs the `tcp_bbr` module on the host; test it next.

## Limits (be careful with these numbers)

- **One physical host, emulated WAN.**
  - The three "sites" share 4 vCPUs and memory, and the same kernel and clock.
  - netem gives fixed-distribution delay, uniform jitter and independent random loss. Real paths have bursty loss, asymmetric routes, bufferbloat and bandwidth limits; netem had no rate limit here.
- **tmpfs instead of disks.** fsync is free here; real sites add their own disk latency. On the test host's own disk, Syncthing was disk-bound, with 40 s for 100 small files at every RTT.
- **Repetitions.** JuiceFS P2–P4 have 1 repetition, and its P4 `stat` covered 50 files. P5 ran once per candidate. Garage P4 repetition 1 overlapped Syncthing P4.
- **Workload.** Synthetic files and a Python client, not a running WordPress or Nextcloud. boto3 adds per-request overhead to Garage's (c) numbers. That overhead is constant, though, while the RTT-driven growth is not.
- **Scope.**
  - Only defaults plus the tuning named here.
  - Not tried: JuiceFS with a different metadata engine (for example TiKV or a local Redis per site); Garage `consistency_mode = "degraded"`; Syncthing with more connections; BBR.
- **Gaps in P5.**
  - A partition of the primary (sb1) was not run for Syncthing. Writes there stay local by design, and replicas stay stale until heal.
  - Concurrent writers to the same key were not tested for Garage.

## Clean-up

Done on the test host:

- `sb1`–`sb3` destroyed (`lxc-destroy`).
- `/root/sbench`, the baseline snapshot and `/tmp/sb-*` removed.
- netem/ingress qdiscs removed.
- The tc modules this test auto-loaded (`sch_netem`, `sch_ingress`, `cls_matchall`, `act_gact`) unloaded.

Compared with the pre-test snapshot, the following are unchanged:

- the `tc qdisc show` output;
- the links;
- `dpkg -l` (483 lines, no host packages added);
- mounts;
- `/var/lib/lxc` (one other container, unrelated to the bench);
- iptables and ip6tables rules (packet counters only).

The other container was never touched and is still running.

Two things remain:

- **`net.bridge.bridge-nf-*` sysctls.** They were present in the pre-test snapshot and are absent now, because the `br_netfilter` module is no longer loaded. Nothing in this test loads or unloads `br_netfilter`, there is no unload in the journal, and the cause is unknown; another session using the test host may have done it. It was **not** reloaded, because doing that blindly could undo someone else's deliberate change. The maintainer should check.
- **Three DHCP leases.** dnsmasq on `lxcbr0` still holds leases for MACs `<masked>`. They expire on their own.

## Exact commands and raw data

Everything is in `raw/` next to this report:

- `results.jsonl`: every repetition, every measure.
- `p5.jsonl` and `p5-*.log`.
- `idle-*.jsonl`.
- `results-st-disk.jsonl`: the disk-bound first run.
- The scripts:
  - `netem.sh`: the profiles;
  - `bench.py`: all measures;
  - `run.sh`/`run2.sh`: one profile × 3 repetitions;
  - `p5.sh`;
  - `st-setup.sh` + `st-config.py`;
  - `garage-setup.sh`;
  - `jfs-setup.sh`, `jfs-tuned.sh`;
  - `idle.sh`;
  - `chain.sh`, `chain2.sh`.

`summarize.py results.jsonl` regenerates the tables. `results.jsonl` next to
this report equals `raw/results.jsonl` except for one record: in the JuiceFS P4
50 MB write, `"w":,` (the writer crashed with EIO and printed nothing) was
replaced by an explicit error object.

Key invocations:

```sh
# containers (per n): rootfs extracted inside a user namespace, unprivileged config
zstd -dc $IMG | unshare --user --map-users=0:$BASE:65536 --map-groups=0:$BASE:65536 \
  --setuid 0 --setgid 0 -- tar -xpf - -C /var/lib/lxc/sbN/rootfs --numeric-owner --exclude='./dev/*'
# netem (host side), e.g. P4
tc qdisc replace dev vsbN root netem delay 125ms 12.5ms loss 2% limit 100000
# partition / heal of sb3
tc qdisc replace dev vsb3 root netem loss 100%; tc qdisc replace dev vsb3 ingress
tc filter replace dev vsb3 ingress pref 1 matchall action drop
# Syncthing
syncthing serve --home=/bench/stbench --no-browser --no-restart --gui-address=127.0.0.1:8384 --no-upgrade
# Garage
garage -c /etc/garage-bench.toml server
garage node connect <id>@<sbN-address>:3901; garage layout assign -z z1|z2|z3 -c 10G <id>; garage layout apply --version 1
rclone copy /root/data/small g:bench/<tag> --s3-no-check-bucket --no-traverse --retries 1
# etcd (per member)
etcd --name sbN --data-dir /bench/etcd --listen-peer-urls http://IP:2380 --initial-advertise-peer-urls http://IP:2380 \
  --listen-client-urls http://IP:2379,http://127.0.0.1:2379 --advertise-client-urls http://IP:2379 \
  --initial-cluster sb1=…,sb2=…,sb3=… --initial-cluster-state new --heartbeat-interval 300 --election-timeout 3000
# JuiceFS
juicefs format --storage s3 --bucket http://127.0.0.1:3900/jfs --access-key … --secret-key … --trash-days 0 \
  "etcd://<sb1-address>:2379,<sb2-address>:2379,<sb3-address>:2379/jfs" jfs
juicefs mount --cache-dir /bench/jfscache --cache-size 256 --no-usage-report "etcd://…/jfs" /mnt/jfs
# GlusterFS attempt
gluster peer probe <sb2-address>; gluster peer probe <sb3-address>
gluster volume create gv replica 3 <sb1-address>:/bench/gl/brick <sb2-address>:/bench/gl/brick <sb3-address>:/bench/gl/brick force
```
