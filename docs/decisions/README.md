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
| 0005 | Signing key custody and repository hosting | key generated and rotated; hosting names decided |
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
| 0016 | Mirror layout, channels and rollback | accepted |
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
| [0047](0047-one-image-per-application.md) | One image per application: the installation mode decides what runs; WordPress on Core, Web and PHP with an embedded MariaDB; Keel Cloud in no application image | decided 2026-10-02 |
| [0048](0048-joining-the-mesh-with-one-command.md) | Joining the mesh with one command: `keel mesh invite` prints `keel mesh join keel1:<token>`, valid one hour and once; an HMAC authenticated HTTPS port with a pinned certificate, a fallback command; both sides under 0018's window; etcd forms at the third node, with its own TLS | decided 2026-10-03 |

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
