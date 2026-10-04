# Keel Web replicated storage: due diligence

> Copied into the handbook on 2026-10-04 as evidence for decision 0050
> ([docs/decisions/0050-the-keel-poor-networks-and-file-replication.md](../../decisions/0050-the-keel-poor-networks-and-file-replication.md)). This is the due diligence report as written on 2026-10-03,
> unchanged. It names no host and no address.

Date of study: 2026-10-03. All figures were collected on that date unless another date is given.
Method:
- **Repository statistics:** `gh api`. Commit counts come from `stats/contributors` for the default branch, merges excluded, window 2025-10-03 to 2026-10-03. Garage's numbers come from `git log` on a clone of the upstream Forgejo repository, because the GitHub mirror under-counts authors.
- **Debian data:** `qa.debian.org/madison.php`, `apt-cache show` on a trixie host, tracker.debian.org, the security tracker and bugs.debian.org.
- **Everything else:** project documentation, linked below.

"Response time" is the median number of hours to the first comment by someone other than the reporter. The sample is the first 20 issues opened between 2026-06-01 and 2026-08-31. Issues closed only by a commit count as "no reply", so this measure is pessimistic for projects such as SeaweedFS that fix bugs without commenting.

---

## 1. Summary

| | License fit | Project health | Debian fit | Tech fit at 250 ms | Ops simplicity | **Total /25** |
|---|---|---|---|---|---|---|
| **Syncthing** | 5 | 4 | 3 | 4 | 5 | **21** |
| **Garage** | 3 | 4 | 1 | 3 | 4 | **15** |
| JuiceFS CE | 5 | 4 | 1 | 1 | 2 | 13 |
| GlusterFS | 4 | 1 | 4 | 1 | 2 | 12 |
| SeaweedFS | 4 | 3 | 1 | 3 | 2 | 13 |
| Ceph (RGW multisite) | 4 | 5 | 4 | 2 | 1 | 16 |
| MooseFS CE | 4 | 2 | 4 | 1 | 3 | 14 |
| MinIO CE | 1 | 0 | 0 | 3 | 4 | excluded (archived) |
| LizardFS | 4 | 0 | 0 | 1 | 2 | excluded (dead) |

Ceph's total is high only because of its health and packaging scores. It does not run in unprivileged LXC, and it is too much to operate for a tiny team (see §6).

**Recommendation: Syncthing** is the one component to build into Keel Web. It should run in a strict single-writer-per-application topology:
- The active site's folder is "send only" and the standby sites' folders are "receive only".
- Standby sites keep versioning turned on.
- Application code and databases stay local and are not replicated by Syncthing.

**There is no silver bullet.** No candidate gives multi-writer POSIX storage that is consistent, survives partitions, works at 250 ms, is in Debian and is simple to run.
- Syncthing gives the right failure behaviour for poor networks: local reads, asynchronous writes, and every site keeps serving during a partition. It does not give shared-write semantics.
- Garage is the right *object* store if Keel later needs true multi-writer storage, for example Nextcloud with S3 primary storage. But it is not in Debian, and its own documentation targets ≤200 ms.

**Main risk:** Debian packaging of Syncthing has fallen behind upstream.
- Trixie ships 1.29.5, from a v1 branch that upstream has frozen.
- v2 is not packaged anywhere in Debian.
- sid/forky 1.29.5~ds1-5 is due for autoremoval from testing on 2026-10-13.
- One maintainer wrote 63% of upstream commits.

**Exit plan:** the data stays plain files in plain directories, so there is no lock-in. Syncthing can be replaced by lsyncd+rsync, Unison, or by Garage plus an S3 offload plugin, without changing the applications.

---

## 2. Candidate by candidate

### 2.1 Syncthing

**License**
- MPL-2.0 (GitHub API, 2026-10-03). The copyleft is file-level only.
- There is no network-use clause and no CLA.
- Shipping it inside appliances has no obligations beyond offering the source of MPL files we modify.

**Governance and funding**
- The Syncthing Foundation is a Swedish non-profit. Its board is Audrius Butkevicius, Jakob Borg and Simon Frei. It pays for infrastructure: discovery and relay servers, and builds. ([syncthing.net/foundation](https://syncthing.net/foundation/))
- Commercial support comes from Kastelo Inc., which also sponsors development. ([kastelo.net](https://kastelo.net/blog/))

**Activity (12 months to 2026-10-03)**
- 224 commits by 14 contributors.
- Bus factor:
  - calmh (Jakob Borg) wrote 143 commits (63%).
  - st-release, the release automation, wrote 47 (20%).
  - marbens-arch wrote 9 (4%).
  - Bus factor is effectively 1.
- Releases:
  - 11 stable releases in 12 months.
  - The latest stable is v2.1.5 (2026-09-08).
  - v2.1.6-rc.4 is out (2026-09-30).
- Issues:
  - 242 were opened in 12 months: 181 closed and 61 still open. 371 are open in total.
  - Median first response is 1 h (sample n=20, 7 without a reply).

**Security**
- 2 GitHub advisories in total: CVE-2021-21404 (relay crash, 2021-04-06) and CVE-2022-46165 (XSS in the GUI, 2023-06-06).
- The Debian security tracker lists CVE-2022-46165 as "no DSA, ignored" for older suites.

**Status and roadmap**
- Syncthing 2.0 (August 2025) moved the database from LevelDB to SQLite, with a one-time migration on first start. ([GitHub release v2.0.0](https://github.com/syncthing/syncthing/releases/tag/v2.0.0), [Neowin](https://www.neowin.net/news/syncthing-20-released-with-major-changes-switching-from-leveldb-to-sqlite/))
- Other 2.0 changes:
  - Deleted items are forgotten after 6 months.
  - Single-dash CLI flags are gone.
  - Multiple connections are used by default.
- v2 stays protocol-compatible with v1, so mixed v1 and v2 clusters work.
- v1.30.0 (July 2025) is the final v1 release. Upstream will issue further v1 releases only for significant (security) problems. ([forum: roadmap and deprecation of v1](https://forum.syncthing.net/t/roadmap-and-deprecation-of-v1-release-branch/24918))
- The data on disk is the user's own files, so there is no storage format to migrate. Only the index database changes.

**Debian**
- trixie: 1.29.5~ds1-2 in main.
- forky and sid: 1.29.5~ds1-5.
- No backports.
- Maintained by the Debian Go Packaging Team; the uploader is Félix Sipma.
- tracker.debian.org, 2026-10-03:
  - "A new upstream version is available: 2.1.6-rc.4".
  - "Marked for autoremoval on 13 October due to golang-github-frankban-quicktest, panicparse: #1146192, #1146228". This affects testing (forky), not trixie.
- Debian is therefore one major version behind, on a branch upstream has frozen.
- Upstream also runs its own signed apt repository at apt.syncthing.net.

**Fit to the use case**
- **Consistency:** eventual consistency and asynchronous. There is no quorum. Concurrent edits to the same file produce `.sync-conflict-*` copies.
- **Partitions:**
  - Every site keeps reading and writing locally.
  - Changes reconcile when the link returns.
  - For WordPress uploads, which are write-once with unique names, conflicts are practically nil.
- **Latency:**
  - Reads are always local disk.
  - Replication is asynchronous over TCP or QUIC, and v2 opens multiple connections.
  - 250 ms RTT and 2% loss slow propagation but do not block the application.
  - This is the best behaviour of all the candidates for the stated design case.
- **Unprivileged LXC:**
  - Syncthing is an ordinary user-space daemon on a normal directory. It needs no FUSE and no special capabilities.
  - The host may need a higher inotify watch limit. Without it Syncthing falls back to periodic rescans.
- **Interface:** POSIX. The application sees a plain directory.
- **Resources:** a single Go binary. Memory use grows with the number of files.
- **Operations:**
  - Device IDs, folder sharing, a GUI and a REST API.
  - Keel can generate the configuration.
  - Easiest for a non-expert of all the candidates.
- **Applications:**
  - WordPress needs no plugin; `wp-content/uploads` is just replicated.
  - Nextcloud must not run on several sites over the same Syncthing folder at once. Nextcloud's file cache lives in its database, and outside changes need `occ files:scan`.
  - For Nextcloud, use active/passive: on failover, promote the standby and rescan.

**Limits**
- Syncthing is not shared storage. There is no locking and no global namespace consistency.
- Deletes propagate, including accidental ones. Versioning must stay on at the receiving sites.

### 2.2 Garage (Deuxfleurs)

**License**
- AGPL-3.0 (LICENSE; `license = "AGPL-3.0"` in Cargo.toml; checked 2026-10-03). There is no CLA.
- AGPL §13 applies only to a *modified* Garage. Anyone who interacts with a modified Garage over the network must be offered its source.
- Unmodified, the obligation is the same as GPL when we convey binaries: we must provide the corresponding source, and a Debian-style source package does that.
- Our users' WordPress sites are not covered: they talk to Garage over the S3 API and are not derivative works.
- **Note for Keel:** CONTRIBUTING.md (main-v2, 2026-10-03) says "**Do not** use AI agents to make contributions to Garage". This limits how Keel could upstream fixes.

**Governance and funding**
- Steered by Deuxfleurs, a French non-profit association.
- GOVERNANCE.md was added in v2.4.0 and reflects the state as of July 2026:
  - Lead developer is Alex (lx).
  - Maintainers are Alex, Trinity and Maximilien.
  - Decisions are by "lazy consensus with the lead developer settling".
  - To become a maintainer you must "earn the personal trust of Alex".
  - "There is no set process for changing the governance."
- Funding, from [garagehq.deuxfleurs.fr](https://garagehq.deuxfleurs.fr/):
  - NGI POINTER 2021-2022: 3 FTE for one year.
  - NLnet / NGI0 Entrust 2023-2024: 1 FTE.
  - NLnet / NGI0 Commons 2025: 1.5 FTE.
  - A further NLnet / NGI0 Commons grant, "Garage reliability and performance", started in April 2026 and funds about one year of work. ([blog 2026-04](https://garagehq.deuxfleurs.fr/blog/2026-04-performance-reliability/), [nlnet.nl/project/Garage-Performance](https://nlnet.nl/project/Garage-Performance/))
  - The funding is almost entirely EU grants. That is a strength today and a cliff risk if NGI funding ends; Deuxfleurs itself published an open letter on NGI funding in 2024.

**Activity (upstream git, 12 months)**
- 339 non-merge commits on main-v2 by 67 distinct authors.
- Top authors:
  - Alex Auvolat: 75 (22%).
  - Gwen Lg: 71 (21%).
  - Arthur Carcano: 43 (13%).
  - The top 3 wrote 56%.
- Releases in the last 12 months: v2.2.0 / v1.3.1 (2026-01-24), v2.3.0 (2026-04-16), v2.4.0 (2026-09-06) and v2.4.1 (2026-09-08).
  - Upstream Forgejo API dates.
  - The v1.x line still receives maintenance releases.
- Issues on Forgejo: 165 open in total. Of issues updated since 2025-10-03, 119 are open and 155 closed.
- Response time:
  - Median first response is about 165 h (≈7 days). Sample n=13, 2 without a reply.
  - That is slow by comparison, and normal for a grant-funded team of 2-4.

**Security**
- No CVEs are on record.
- One security release, v0.9.2 / v0.8.6 (2024-03-01), fixed timing side channels found in an audit by Radically Open Security.
- SECURITY.md was added in v2.4.0. It promises a reply "within a few weeks".

**Status and roadmap**
- Active.
- Each major version has a migration document: 0.3→0.4, …, 0.9→1.0, 1→2.
- v1→v2 needs a coordinated restart of all nodes, and the configuration changes (`replication_mode` becomes `replication_factor`). Upstream recommends `garage meta snapshot` first. ([migration-2](https://garagehq.deuxfleurs.fr/documentation/working-documents/migration-2/))
- The metadata database is LMDB by default; the documentation warns that LMDB files can be corrupted after an unclean shutdown. SQLite is offered as the more robust alternative. ([real-world deployment](https://garagehq.deuxfleurs.fr/documentation/cookbook/real-world/))

**Debian**
- Not in any suite.
- [#1118368](https://bugs.debian.org/1118368) is an **RFP, not an ITP**. Andrea Pappacoda filed it on 2025-10-18.
- Packaging work by Wesley Hershberger is under way on salsa (rust-team/garage):
  - On 2026-09-02, re-run against 2.3.0, he listed about 17 crates still missing, including the whole aws-smithy and aws-sdk family, two of them already merged.
  - On 2026-05-31 he had counted 27 crates.
  - He also objected to packaging the unmaintained `parse_duration` crate (upstream issue #1246).
- Realistically Garage is not in Debian before forky (14), if at all.

**Fit to the use case**
- **Consistency:**
  - Built on CRDTs with read and write quorums, and no Raft.
  - The default `consistency_mode = consistent` gives read-after-write consistency. ([blog 2023-12](https://garagehq.deuxfleurs.fr/blog/2023-12-preserving-read-after-write-consistency/))
  - `degraded` mode drops the read quorum to 1; `dangerous` drops both quorums to 1.
- **Latency:**
  - The homepage lists the requirement as "Network: 200 ms or less, 50 Mbps or more", with data "replicated in 3 zones". **Our design case of 250 ms is outside the documented envelope.**
  - Upstream benchmarked with mknet at 100 ms ±20 ms jitter, and was clearly faster than MinIO there. ([benchmarks](https://garagehq.deuxfleurs.fr/documentation/design/benchmarks/))
- **Partitions:**
  - With replication factor 3 across 3 sites, a write needs 2 of 3 zones, so every PUT pays at least one WAN round trip.
  - A consistent read also needs a metadata quorum, so every GET pays at least one 250 ms round trip unless there is a local cache in front.
  - A site cut off from both others can neither write nor do consistent reads; its applications lose their media.
  - The safe side (the majority) keeps working.
- **Unprivileged LXC:** yes. It is an ordinary daemon with no FUSE.
- **Interface:** S3 objects only, not POSIX.
- **Resources:** a single Rust binary. The recommended minimum is 1 GB RAM and 16 GB disk; old x86_64 or ARM machines are fine.
- **Operations:**
  - Simple for a distributed store: one binary, `garage layout` commands, zones.
  - An admin UI is in progress under an NLnet grant.
  - The documentation recommends XFS for data and BTRFS or ZFS for metadata.
- **Applications:**
  - **Nextcloud** supports S3 as primary storage natively. But changing an existing instance to object storage is unsupported and makes existing files inaccessible; a new instance must be set up for it from the start. ([Nextcloud admin manual](https://docs.nextcloud.com/server/23/admin_manual/configuration_files/primary_storage.html))
  - **WordPress** needs a plugin. All of the following are GPL:
    - [Human Made S3-Uploads](https://github.com/humanmade/S3-Uploads): GPL-2.0, v3.0.13 (2026-02-25). Custom endpoint via the `s3_uploads_s3_client_params` filter.
    - [Advanced Media Offloader](https://wordpress.org/plugins/advanced-media-offloader/): GPLv2+, v4.5.2 (2026-09-09), about 7,000 active installs, "any S3-compatible service".
    - [WP Offload Media Lite](https://wordpress.org/plugins/amazon-s3-and-cloudfront/): GPLv2, v3.4.3 (2026-09-21), about 30,000 installs. Its readme names only AWS, DigitalOcean and GCS. Offloading existing media is a Pro feature.
  - Offload plugins rewrite media URLs in the WordPress database. That is application-level lock-in that Syncthing avoids.

### 2.3 JuiceFS Community Edition

**License and governance**
- Apache-2.0 (GitHub API).
- Open-core. The Enterprise Edition is closed source, with a proprietary Raft metadata engine, mirror file systems and cross-region replication. ([Juicedata blog](https://juicefs.com/en/blog/solutions/juicefs-enterprise-edition-features-vs-community-edition))
- Steered by Juicedata Inc.

**Activity (12 months)**
- 789 commits by 49 contributors.
- Top authors: jiefenghuang 27%, zhijian-pro 14%, Xuyuchao-juice 10%.
- 8 releases. The latest are v1.4.1 (2026-07-30) and v1.3.3 (2026-08-07).
- Issues: 284 opened in 12 months, 210 closed. Median response 36 h (sample n=20, 16 without a reply).
- 0 GitHub advisories in 12 months.

**Debian**
- Not packaged.
- ITP [#1034560](https://bugs.debian.org/1034560) (2023) is stale.

**Fit**
- A POSIX FUSE client built from two parts: a metadata database (Redis, PostgreSQL, MySQL, TiKV…) and an object store.
- The Community Edition has **one** metadata engine. Every metadata operation (open, stat, create) from a remote site crosses the WAN to it. Cross-region mirroring exists only in the Enterprise Edition. ([JuiceFS multi-cloud](https://juicefs.com/en/blog/solutions/consistency-low-latency-data-distribution-multi-cloud-storage))
- It needs FUSE, so the extra LXC feature is required.
- Operationally three things must stay healthy: the metadata database, the object store and the FUSE client.
- It also *still needs* a replicated object store underneath, so it does not remove the Garage or SeaweedFS decision.
- **Unsuitable at 250 ms.**

### 2.4 GlusterFS

**License**
- GPL-2.0 / LGPL-3.0+ dual license; GitHub reports GPL-2.0.

**Governance**
- Red Hat Gluster Storage reached end of life on 2024-12-31; RHGS 3.5 was the last series. ([bigiron.cc](https://www.bigiron.cc/guides/the-state-of-glusterfs-after-redhat-killed-it-2026))
- No vendor has taken over.
- Proxmox VE 9 removed the native GlusterFS storage plugin, citing upstream maintenance and QEMU deprecation. ([Proxmox forum](https://forum.proxmox.com/threads/glusterfs-is-still-maintained-please-dont-drop-support.168804/))

**Activity (12 months)**
- 31 commits by 5 contributors. ThalesBarretto wrote 67%.
- Recent commits are build-system cleanups (2026-09-23).
- **No release in 12 months.** The latest is v11.2 (2025-07-02).
- Issues: 108 opened in 12 months, 46 closed. 259 open in total.
- Median response is about 1,139 h, roughly 47 days (sample n=13, 10 without a reply).

**Debian**
- trixie: 11.1-6.
- bookworm-backports: 11.1-3~bpo12+1.
- forky and sid: 11.2-5.
- Single maintainer: Patrick Matthäi.

**Fit**
- Replication (AFR) is synchronous and client-driven: every write waits for all replicas, which at 250 ms is painful, and split-brain handling is manual.
- Geo-replication is asynchronous master→slave only.
- Bricks need `trusted.*` extended attributes, which require CAP_SYS_ADMIN. **They fail in unprivileged LXC** with "Operation not permitted". ([gluster#1239](https://github.com/gluster/glusterfs/issues/1239), [LXC forum](https://discuss.linuxcontainers.org/t/setting-extended-attributes-failed-reason-operation-not-permitted/10670))
- The client is FUSE.
- **Reject:** the project is in maintenance mode and the architecture is wrong for the case.

### 2.5 Other options assessed

**SeaweedFS**
- License and governance:
  - Apache-2.0, open-core.
  - The Enterprise Edition is under a proprietary EULA, free under 25 TB. ([seaweedfs.com](https://seaweedfs.com/))
  - Chris Lu runs it with Seaweed Data.
- Activity, 12 months:
  - 4,054 commits by 178 contributors. chrislusf wrote 70%; dependabot 9%; an account named "claude" 104 commits.
  - 47 releases; the latest is 4.48 (2026-09-28).
  - **25 GitHub advisories in 12 months, 9 critical and 12 high.** These include unauthenticated IAM identity injection, SFTP empty password and AQL injection, all in September 2026.
  - Median response 9 h (sample n=20, 15 without a reply).
- Debian: ITP [#956957](https://bugs.debian.org/956957) from 2020, stale.
- Fit:
  - Asynchronous active-active `filer.sync` between clusters is a reasonable WAN design. ([wiki](https://github.com/seaweedfs/seaweedfs/wiki/Filer-Active-Active-cross-cluster-continuous-synchronization))
  - But it means a master, volume and filer in every site plus the sync daemons. That is a lot to operate.
  - Bus factor 1, a release pace that is hard to track, and a poor security record for a 12-month window.

**MinIO Community Edition**
- AGPL-3.0; relicensed from Apache-2.0 in 2021.
- Admin features were removed from the community console in 2025. The repository went into maintenance mode in December 2025.
- **The repository is archived.** The GitHub API returned `archived: true` on 2026-10-03, and the README says "THIS REPOSITORY IS NO LONGER MAINTAINED" and points to the proprietary "AIStor Free".
- Secondary sources give the archive date as either 2026-02-13 or 2026-04-25. ([stormdevelopments.ca](https://stormdevelopments.ca/blog/minio-s-community-edition-is-archived-what-still-runs-in-2026/), [vonng](https://blog.vonng.com/en/db/minio-resurrect/))
- The last release is RELEASE.2025-10-15T17-29-55Z.
- **Excluded.**

**Ceph (RGW multisite, CephFS)**
- License and governance:
  - Mostly LGPL-2.1/3; GitHub reports "NOASSERTION".
  - Ceph Foundation under the Linux Foundation; IBM is the main contributor.
- Activity, 12 months:
  - ≥7,364 commits by ≥156 contributors. The stats endpoint caps at the top 100 contributors.
  - Top author 7%: the healthiest project in this study.
  - Stable releases are v20.2.x Tentacle (v20.2.0 on 2025-10-30). Tag v21.3.0 was created 2026-06-10.
- Debian:
  - trixie: 18.2.7+ds-1+deb13u1.
  - forky and sid: 20.2.4+ds-1.
  - Maintained by the Ceph Packaging Team.
- Fit:
  - RGW multisite replicates asynchronously between zones and handles WAN latency well.
  - But each site needs its own RADOS cluster: at least 3 monitors plus OSDs.
  - OSDs need raw block devices or privileges and cannot run in unprivileged LXC.
  - It is far too much for a tiny team. Keep it as the heavyweight reference and as a possible exit target only.

**MooseFS**
- GPL-2.0; Saglabs SA.
- Activity: 35 commits in 12 months, 88% by acid-maker. The latest release is v4.59.2 (2026-05-18).
- Debian: trixie 4.57.5-1, trixie-backports 4.58.1, sid 4.59.2; maintainer Dmitry Smirnov.
- Master failover and multi-location clusters are **Pro-only**. ([moosefs.com/pro-vs-community](https://moosefs.com/pro-vs-community))
- The Community Edition has a single-master point of failure, and the client is FUSE.
- **Reject.**

**LizardFS**
- The last commit was 2024-08-11 and the last tag is 3.13.0-rc3 (2020-08-24). Not in Debian. Dead.
- SaunaFS (Leil Storage) is the living fork, ITP #1080956. Same architecture class as MooseFS.

**rclone**
- MIT; Nick Craig-Wood wrote 70% of 1,152 commits in 12 months. 16 releases; the latest is v1.75.1 (2026-09-04).
- Debian:
  - trixie: 1.60.1+dfsg-4, from 2022.
  - sid: 1.69.3.
  - **The security tracker lists 31 CVE-2026 entries**, and several are "vulnerable (no DSA)" for trixie.
- rclone is a copy and sync tool, not a replicated store; `bisync` is not HA.
- Its value here is as the **migration and exit tool** (S3↔S3, S3↔POSIX).

---

## 3. Scores with justification

**Syncthing (21)**

| Criterion | Score | Justification |
|---|---|---|
| License | 5 | MPL-2.0, no network clause, no CLA. |
| Health | 4 | Foundation, 11 releases a year, 1 h response; but calmh writes 63% of commits. |
| Debian | 3 | In trixie main via the Go team, but on a frozen v1 branch; v2 unpackaged; autoremoval from testing pending (2026-10-13). |
| Tech at 250 ms | 4 | Local reads, async writes, available during partitions; loses a point for having no consistency or locking. |
| Ops | 5 | One daemon on a plain directory, no FUSE, unprivileged. |

**Garage (15)**

| Criterion | Score | Justification |
|---|---|---|
| License | 3 | AGPL is fine unmodified, but any patch must be published, and upstream forbids AI-agent contributions. |
| Health | 4 | 67 authors, top author 22%, grant-funded into 2027; governance informal and grant-dependent; replies take about 7 days. |
| Debian | 1 | Not packaged; RFP only; about 17 Rust crates missing as of 2026-09-02. |
| Tech at 250 ms | 3 | Designed for geo-distribution, but documented for ≤200 ms; every request pays a round trip; an isolated site loses reads. |
| Ops | 4 | Single binary, clear layout model, 1 GB RAM; S3 plus a WordPress plugin adds a moving part. |

**JuiceFS CE (13)**

| Criterion | Score | Justification |
|---|---|---|
| License | 5 | Apache-2.0. |
| Health | 4 | 789 commits from 49 people, company-backed; open-core. |
| Debian | 1 | ITP stale since 2023. |
| Tech at 250 ms | 1 | A single metadata database means every file operation crosses the WAN; geo features are Enterprise-only. |
| Ops | 2 | Metadata database plus object store plus FUSE. |

**GlusterFS (12)**

| Criterion | Score | Justification |
|---|---|---|
| License | 4 | GPL-2.0/LGPL-3.0. |
| Health | 1 | No release in 15 months, 5 contributors, about 47-day response, vendor gone. |
| Debian | 4 | In trixie and sid, though with a single maintainer. |
| Tech at 250 ms | 1 | Synchronous replication, and fails unprivileged because of `trusted.*` xattrs. |
| Ops | 2 | Split-brain handling is expert work. |

**SeaweedFS (13)**

| Criterion | Score | Justification |
|---|---|---|
| License | 4 | Apache, but open-core. |
| Health | 3 | Very active, but 70% one person and 9 critical advisories in 12 months. |
| Debian | 1 | ITP stale since 2020. |
| Tech at 250 ms | 3 | Asynchronous active-active filer.sync is the right idea. |
| Ops | 2 | Three daemon types per site plus the sync processes. |

**Ceph (16)**

| Criterion | Score | Justification |
|---|---|---|
| License | 4 | LGPL. |
| Health | 5 | Foundation, broad contributor base. |
| Debian | 4 | In trixie with a team. |
| Tech at 250 ms | 2 | RGW multisite is fine, but needs a full cluster per site and no unprivileged LXC. |
| Ops | 1 | Requires a specialist. |

**MooseFS CE (14)**

| Criterion | Score | Justification |
|---|---|---|
| License | 4 | GPL-2.0. |
| Health | 2 | 88% one author. |
| Debian | 4 | trixie plus backports. |
| Tech at 250 ms | 1 | HA and multi-location are Pro-only; FUSE. |
| Ops | 3 | Not scored further. |

---

## 4. Recommendation

**Build Syncthing into Keel Web**, under one design rule: **one writer per application at a time.**

- **Topology.** Each application has a home site, whose `wp-content/uploads` (later the Nextcloud `data/`) is shared as *send only*. The two other sites receive it as *receive only*, with staggered versioning enabled.
- **Failover.** An operator action promotes a standby: it flips folder types and, for Nextcloud, runs `occ files:scan --all`. This matches how the database must fail over anyway. Multi-primary MariaDB across 250 ms is not realistic, so the application is single-writer regardless of what the storage layer can do.
- **What is replicated.**
  - **Code stays local.** It comes from the .deb or image, so every site has an identical copy and code is never replicated by Syncthing.
  - **Configuration** comes from Keel.
  - **Only user data** is replicated by Syncthing.
- **Packaging.** Do not depend on Debian's 1.29.5.
  - Package v2 in Keel's repository: from upstream's source, or by repackaging upstream's signed apt.syncthing.net builds.
  - Offer the work to the Debian Go team. That is also the cheapest way to help keep it in forky.
  - v1 and v2 interoperate on the wire, so mixed versions during the transition are safe.

**Is there a silver bullet? No.** The honest shape of the answer is:
1. **Code local**, from packages.
2. **One replication component for user data.**
   - For Keel's design case (250 ms, loss, partitions, tiny team, Debian-first), that is Syncthing.
   - Its asynchronous, partition-tolerant model matches the network. It needs no FUSE and no privileges. It keeps applications unmodified.
3. **Garage is the designated second step, not a replacement.** Revisit it only if a product needs true multi-writer object storage across sites, which most likely means Nextcloud with S3 primary storage on a new instance. Revisit it only after:
   - Garage is in Debian, or Keel accepts building it;
   - the 250 ms behaviour has been measured on Keel's own test sites against the documented ≤200 ms envelope;
   - and a local read cache sits in front of each site.

## 5. Main risk and exit plan

**Main risks**
1. **Packaging.** Debian is behind upstream: trixie ships 1.29.5 on a frozen v1 branch, v2 is unpackaged, and the testing autoremoval notice is dated 2026-10-13. Keel will carry a v2 package itself for a while.
2. **Bus factor.** Jakob Borg wrote 63% of commits.
3. **Semantics.** The model cannot be used for multi-writer workloads. If a future product needs that, Syncthing is the wrong tool, and that product (not Keel Web as a whole) brings in Garage.

**Exit plan if Syncthing dies**
- The data is ordinary files in ordinary directories on every site, with no proprietary format and no index needed to read it.
- Replacements in order of effort:
  1. lsyncd + rsync, or Unison: same single-writer model, both in Debian.
  2. Garage or Ceph RGW plus an S3 offload plugin or Nextcloud S3, migrated with rclone.
- None needs an application change beyond configuration.
- The Syncthing index database is discarded.

## 6. Surprising findings
- **MinIO Community Edition is archived** (`archived: true` on GitHub, README says it is no longer maintained). Many "Garage vs MinIO" comparisons are now moot.
- **Garage's own homepage says "200 ms or less"**, which is below the 250 ms design case. Its Debian bug is an RFP, not an ITP.
- **Garage forbids AI-agent contributions** (CONTRIBUTING.md). That matters for how Keel would upstream patches.
- **Syncthing is effectively stuck at v1 in Debian.** v2 shipped upstream in August 2025, and the package is due for autoremoval from testing on 2026-10-13 over transitive RC bugs.
- **SeaweedFS had 9 critical advisories in 12 months**, and an account named "claude" made 104 commits to it.
- **rclone in trixie is 1.60.1 (2022)**, with dozens of open 2026 CVEs in the security tracker.
- **GlusterFS has not released in 15 months**, and Proxmox VE 9 dropped it.