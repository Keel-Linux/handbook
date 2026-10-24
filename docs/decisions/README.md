# Decision notes

One note per direction taken, numbered in the order the number was taken.
A note says in its status line who decided it and when, and a later note
that changes an earlier one says so under "What this amends".

## Index

| Note | Subject | State |
| --- | --- | --- |
| 0001 | Name, domains and hosting | decided 2026-09-24 |
| 0002 | tklbam is the last component to be ported | decided |
| 0003 | Test coverage standard | decided |
| 0004 | How shell code is tested and measured | decided |
| 0005 | Signing key custody and repository hosting | key generated and rotated; hosting names decided; unattended signing superseded by 0055 |
| 0006 | Organization guidelines | decided; tracker reversal 2026-09-27 |
| 0007 | License of new code, and review policy | decided |
| 0008 | What kind of fork Keel is | proposed |
| 0009 | Four corrections to the spec vocabulary | implemented |
| 0010 | Composable component repositories | accepted with a prerequisite |
| 0011 | Two signing keys | open PR, handbook#11 |
| 0012 | Pinning the packages an image is built from | accepted and implemented |
| 0013 | Database topologies configurable from the console | scope decided |
| 0014 | Appliance identity, and what it says about backup | open PR, handbook#6 |
| 0015 | Operator facing commands carry the Keel name | decided |
| 0016 | Mirror layout, channels and rollback | accepted; "not the release key" superseded by 0055 |
| 0017 | Owning fab | open PR, handbook#18 |
| 0018 | The network on a running machine | decided |
| 0019 | Webmin does not change the network | accepted |
| 0020 | Replicated appliances | decided |
| 0021 | A resource monitor | decided |
| 0022 | An LNPP stack, and Odoo from git | open PR, handbook#23 |
| 0023 to 0040 | The composition architecture, below | decided 2026-09-30 |
| [0041](0041-the-appliance-manifest-version-1.md) | The appliance manifest, version 1 (format: [docs/manifest-v1.md](../manifest-v1.md)) | decided 2026-09-30 |
| [0042](0042-keel-web-sites.md) | Keel Web sites: modes, the spec, certificates through the Certificate feature, Debian's Nginx layout | decided 2026-09-30 |
| [0043](0043-release-formats.md) | Release formats: only the ISO and the `.tar.zst` (Docker through `docker import`), AWS and OpenStack by local conversion later, names, layout, signed SHA512SUMS, GitHub Releases | decided 2026-10-01 |
| [0045](0045-keel-dns-powerdns-authoritative.md) | Keel DNS: PowerDNS Authoritative on Keel Core, one local `gsqlite3` database per server and zone replication by NOTIFY, AXFR and catalog zones (not the database pair, not LMDB: no RFC 2136 in 4.9); the primary holds the VIP of 0049 for the mesh control path only, every server answers on its own public address; no `state.replicate`, Syncthing off; TSIG for transfers and updates; no DNSSEC in version 1; no web interface; the recursor out of scope; the 4.9.17 package waits for the fix of CVE-2026-73206; replaces the 0045 part of handbook#38 | proposed |
| [0047](0047-one-image-per-application.md) | One image per application: the installation mode decides what runs; WordPress on Core, Web and PHP with an embedded MariaDB; Keel Cloud in no application image | decided 2026-10-02 |
| [0048](0048-joining-the-mesh-with-one-command.md) | Joining the mesh with one command: `keel mesh invite` prints `keel mesh join keel1:<token>`, valid one hour and once; an HMAC authenticated HTTPS port with a pinned certificate, a fallback command; both sides under 0018's window; etcd forms at the third node, with its own TLS | decided 2026-10-03, third round 2026-10-04 (etcd: intermediate CAs, state not spec, `keel mesh etcd form`, removal rule); amendment (admission evidence) approved 2026-10-04 |
| [0049](0049-webmin-per-role-and-the-mesh-vip.md) | Webmin per mode and role, and the VIP on the WireGuard mesh: the primary's Webmin only on the VIP, a replica's (database or files) on its mesh and private LAN addresses with a warning; one VIP per replicated appliance pair, a `/128` the primary carries on `wg0` and peers route by `allowed_ips`, moved by promote before etcd and by the controller with it, fenced by an epoch; an old primary rejoins by itself when it holds nothing the new one lacks; root loses `READ_ONLY ADMIN` on a MariaDB replica; third round: the code in keel, `keel vip promote`, only the pair claims (a signed pair record), a 20 s etcd lease; precision of 2026-10-11: the rejoin leaves the spec alone, the role is runtime state, the root CA in every cloud mode signs a `database` leaf per node, `ip_nonlocal_bind` binds the VIP on both nodes | decided 2026-10-03, third round 2026-10-04, precision 2026-10-11 |
| [0050](0050-the-keel-poor-networks-and-file-replication.md) | The keel: everything that spans nodes is designed and tested for 250 ms with jitter and loss, under netem profiles; the hot path stays local and only changes replicate; application files on Syncthing v2, one writer per application, the folder flipped by keel's role, built into Keel Web; Garage a later regional step; JuiceFS and GlusterFS rejected; evidence in [docs/evidence/2026-10-03-storage](../evidence/2026-10-03-storage/) | decided 2026-10-04 |
| [0051](0051-regions-and-federated-root-cas.md) | Regions and federated root CAs: a root CA per region on its holder, certifying its nodes locally, another region's root when it is down; etcd one cluster trusting a bundle of every root, the bundle changed only by a majority of the roots and approved on each holder; each root revokes what it issued, a whole root by a majority that counts it but needs not its signature (two regions need a third, or `distrust` on each member); CRLs merged per member; `installation.region` and a /112 per region; at most five voters, placed so losing any region keeps a quorum; the roots' status in confconsole, `keel mesh status` and `keel diff`, alerted by email; keel#78 the single region case with the bundle and region field, keel#79 the rest | decided 2026-10-04, two rounds (tracker#60) |
| [0052](0052-every-release-ships-both-formats.md) | Every release ships both formats: each appliance release stages the `.tar.zst` and the ISO from one build and is published only when both pass; the container drops the boot set (kernel, initrd, firmware, GRUB, installer, about 192 MB of Core's 903.6 MB unpacked), which moves to a per appliance boot layer only the ISO uses; both scanned, signed and listed, the Proxmox index the `.tar.zst` only; the ISO boot tested under BIOS and UEFI in QEMU on the build host as a gate; amends 0043 | decided 2026-10-10, with the five points of the proposal approved as recommended: the boot layer, UEFI as a gate, the install to disk once automated, `.tar.zst` only testing pre-releases until the ISO builder exists, the 990 pin first |
| [0053](0053-no-merge-on-a-red-check-and-evidence-for-every-real-test.md) | No merge on a red check, and evidence for every test on the real platform: a failing check, required or not, is a bug fixed before the merge, never known noise, and the fix to a wrong check is the first PR (the case: keel-mariadb's `appliance / boot-published-layer`, red since 2026-09-30, fixed by reordering `tests/lib/boot-test-lib.sh`); every run on real nodes leaves `evidence/<date>-<topic>.md` with commands, trimmed output, dpkg versions, hashes and timings, and a report without it is not a result (the case: 0.22.0 from dpkg against 0.19.0 from `keel --version`, keel#98); the undecided items under "What comes next" | decided 2026-10-08 |
| [0054](0054-the-postgresql-database-pair.md) | The PostgreSQL database pair: twin of the MariaDB converge, basebackup seeding, timeline divergence probe, confirmed-reseed failback, no-timeout synchronous commit | decided 2026-10-13 |
| [0055](0055-one-key-per-purpose-signed-on-the-build-host.md) | One key per purpose, signed on the build host: main, security, testing and images, each its own certificate and keyring file; subkeys without passphrase on the build host only, 3 year expiry with an alert; supersedes part of 0005 and 0016 | decided |
| [0056](0056-git-pop-coop-is-the-source-github-is-a-mirror.md) | git.pop.coop is the source, GitHub is a mirror: the organization `Keel-Linux` on git.pop.coop holds the repositories, issues, pull requests and CI (Forgejo Actions on the Keel runners); each GitHub copy is a push mirror with one deploy key, no branch protection and no new issues; `keel`, `handbook` and `.github` cut over last | decided 2026-10-14 |
| [0057](0057-an-etcd-witness-and-a-pair-that-moves-to-cloud-advanced.md) | An etcd witness, and a pair that moves to cloud advanced: a witness is a Keel Core node in `cloud_advanced` with etcd and no role (0020's data-less voter, 0028's external arbiter); an existing `cloud_simple` pair moves to `cloud_advanced` by its spec, then `keel mesh etcd form` on the root's holder; only that direction; proved by the BR3-THIN evidence before keel's docs change | decided 2026-10-15 |
| [0058](0058-link-profiles-for-a-mesh-of-three-sites.md) | Link profiles for a mesh of 3 sites: measure RTT, jitter, loss and MTU between the sites, map the link to the profiles of 0050, and from the profile derive the etcd timings, a TCP outage limit only for the connections that need it, and the MTU of the overlay; open questions, measurements and criteria; `tcp_retries2 = 5` of the 0050 amendment stays until a decided note replaces it | proposed, for later evaluation |
| [0059](0059-nginx-is-the-only-web-server-lnmp-and-lnpp.md) | nginx is the only web server, and LNMP and LNPP are the base stacks: Apache retired from Keel, the recipes that use it move to nginx one PR each (WordPress, Moodle, Odoo, ejabberd, then the clean up); `lnmp` (PHP-FPM, MariaDB) and `lnpp` (Python, gunicorn on a systemd socket, PostgreSQL) are layers on Web, one image each, the database pair by the spec; routes in keel-web's include directory `/etc/nginx/keel-default.d/`; a read-only check page at `/keel-check/`; amends 0023, 0030, 0047 | decided 2026-10-16 |
| [0060](0060-keel-images-for-incus.md) | Keel images for Incus, from Keel's own simplestreams remote: `images.linuxcontainers.org` publishes only what stgraber's lab builds and usually refuses a small derivative (lxc-ci#959, #923), so the keel-core base is likely refused now and the appliances are out of scope there; plan: `images.keellinux.org` built with distrobuilder from a definition in lxc-ci format, published with `incus-simplestreams`, tested with lxc-ci's `bin/test-image`, containers and VMs, amd64 first, HTTPS and sha256 with no GPG; starts when all applications are stable on the Proxmox image server; an lxc-ci issue for the base only when Keel has outside users | proposed, a plan for when all applications are stable on Keel's own image server |
| [0061](0061-one-image-build-per-merge.md) | One image build per merge: the build host polls `git.pop.coop` every 5 min, builds only the changed layer and the layers above it, signs with the staging key, pushes to a drop directory on the runner VM and dispatches `image-boot.yml` of `Keel-Linux/image-gate`; the runner boots the bits as built and holds no key; on a pass the build host signs the same files with main and images into `/srv/keel-ci/testing/` (no Proxmox index, no channel move, nothing public); on a failure an issue; package repositories (keel) do not trigger, so keel main does not enter an image; amends 0016; amendment of 2026-10-17: the CI builds the testing track, each appliance on its own, build trees removed | decided 2026-10-16 |
| [0062](0062-nextcloud-on-lnmp.md) | Nextcloud on the LNMP stack, version 35.0.2 pinned by sha256: the data directory on the 0050 Syncthing replication (object storage as primary storage rejected), APCu and the database for cache and locking, a systemd timer for the cron on the writable node only, a warm standby that refuses DAV write methods with 503, the official CRS Nextcloud exclusions plus body inspection off for DAV file payloads, Anubis passes the sync clients; applies 0049, 0050, 0059 and 0061 | decided 2026-10-19 |
| [0063](0063-keel-ntfy-alerts-outside-the-cluster.md) | keel-ntfy: one standalone alert server per site (ntfy 2.11.0 from trixie on the web layer), outside the cluster that it watches; not highly available across clusters; keel sends each alert to every server; tenants as topic prefixes with ntfy access control | decided 2026-10-22 |
| [0068](0068-application-contract-for-replication.md) | The application contract for replication: one note for what a contributor declares (base stack, `state.replicate`, `state.exclude`, `services.database`) and what the platform does (database replication, file replication, the flip, ownership, boot resume, backup, monitoring); Web declares `/var/www/keel-default` as a default replicate path; Redis as a parallel service is future work; amends 0034, 0041 and 0050 | decided 2026-10-25 |
| [0064](0064-ghost-on-lnmp-with-node-22.md) | Ghost 6.72.0 on the LNMP stack with PHP-FPM off and upstream Node.js 22 (Debian 13 has 20.19, Ghost needs 22.23.1 or newer): upstream supports MySQL 8 only, so MariaDB 11.8 ships behind a three-part gate (migrations, Ghost database tests, cross-site failover) and a MySQL 8 pair is a separate decision; five content paths replicate (`images`, `media`, `files`, `themes`, `settings`, with the redirects moved into `settings`); `ghost.service` runs on the primary only, with a cold standby that answers 503; amends 0036 | proposed 2026-10-24 |

## The composition architecture (0023 to 0040)

Recorded from the maintainer's architecture session of 2026-09-30, which
numbered its decisions ADR-001 to ADR-017, with ADR-012a. The ADR numbers
are kept only as this mapping; the handbook refers to the note numbers.

| ADR | Note | Subject | Amends |
| --- | --- | --- | --- |
| ADR-001 | [0023](0023-composition-of-appliances.md) | Composition of appliances instead of monolithic appliances | 0013, 0010, 0006, 0022, 0008 |
| ADR-002 | [0024](0024-the-mesh-is-the-base.md) | The mesh is the base, not an extra | 0020 (0018 unchanged) |
| ADR-003 | [0025](0025-etcd-is-the-mesh-registry.md) | etcd is the mesh registry, not only quorum | 0020, brief section 2 |
| ADR-004 | [0026](0026-installation-by-discovery.md) | Installation by discovery, not by typing | 0013, 0020 |
| ADR-005 | [0027](0027-the-yaml-file-is-the-source-of-truth.md) | The YAML file is the source of truth | brief section 5.2, 0009 |
| ADR-006 | [0028](0028-installation-modes.md) | Installation modes at first boot | 0013, 0020 |
| ADR-007 | [0029](0029-core-ships-crowdsec-and-wireguard.md) | Keel Core ships CrowdSec and WireGuard, and a VIP on the mesh | 0020, 0018 |
| ADR-008 | [0030](0030-keel-web.md) | Keel Web: Nginx, Coraza and Anubis | 0013, 0022 |
| ADR-009 | [0031](0031-database-failover-semantics.md) | Database failover semantics | 0020 (synchronous replication; automatic failback implemented, the operator's choice and its manual default kept), 0013 |
| ADR-010 | [0032](0032-directory-replication.md) | Directory replication is a generic mesh service | 0020, brief section 4.2 |
| ADR-011 | [0033](0033-data-services-are-first-class.md) | Data services are first-class appliances | 0013, 0010 |
| ADR-012a | [0034](0034-application-appliance-contract.md) | The application appliance contract | 0010, brief section 4.2, 0021, 0014 |
| ADR-012 | [0035](0035-mastodon-reference-appliance.md) | Mastodon as the reference appliance | tracker#20, 0006 |
| ADR-013 | [0036](0036-common-versus-appliance.md) | What lives in common, and what is an appliance | 0010, 0013, 0022, 0006 |
| ADR-014 | [0037](0037-backup-destination-appliance.md) | Backup as a destination appliance | 0002, 0014, 0013 |
| ADR-015 | [0038](0038-object-storage-on-garage.md) | Object storage appliance on Garage | 0002, 0032 |
| ADR-016 | [0039](0039-upgrades-from-the-keel-repository.md) | Upgrades come from the Keel repository | 0016, 0020, 0022 |
| ADR-017 | [0040](0040-monitoring-with-monit-and-etcd.md) | Monitoring per machine with Monit, aggregated in etcd | 0021 |

Technical caveats raised when the decisions were recorded were answered
by the maintainer on 2026-09-30, and each note carries them under
"Resolved": the new decision stands, and the earlier note it amends is
superseded on that point. The one exception is failback in 0031: the
operator keeps 0020's choice, with manual as the default, and Keel
implements automatic failback after full catch-up. Points that are not
doubts about a decision stay open under "Review notes": the entry secret
(0026), the manifest format proposed as the first deliverable (0034), and
the two open items below.

Open architecture items of the same session, not yet decided: the
successor to HubDNS for nodes behind NAT whose IPv6 prefix changes (likely
a PowerDNS overlay fed from etcd), and Elasticsearch or OpenSearch.
