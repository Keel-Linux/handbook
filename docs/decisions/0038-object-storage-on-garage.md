# 0038: Object storage appliance on Garage

Date: 2026-09-30
Status: **decided by the maintainer, 2026-09-30** (ADR-015).

## Decision

- **Object storage is an appliance on Garage**, delivered as an `s3`
  overlay in common.
- **Garage over MinIO:** it is designed for geo-distributed nodes on
  unequal links, it is one small binary, its zones map to the etcd site
  label (replication factor 3 across three zones), and it is AGPL without
  a commercial edition.
- **Object storage is the recommended home** for media, attachments and
  backups. File replication (0032) shrinks to what applications insist on
  keeping on a filesystem.
- **Garage nodes announce themselves in etcd** (0025).

## What this amends

- **0002, "Consequences"**: the `s3-endpoint-url` option for duplicity
  gets its target.
- **0032**: fewer paths to replicate by file.
- **0013's sovereignty claim**: Garage is not in Debian (see below), so it
  ships as a Keel package.

## Packages (checked 2026-09-30 against the Debian archive and WNPP)

- **Garage is not in Debian.** It has an ITP, #1118368, and is being
  packaged. Until a package reaches Debian, Keel builds it from source
  into the Keel repository under 0039.
- **Garage is a candidate for Keel to contribute to Debian**, through the
  existing Debian packaging effort (tracker#15), coordinating with the
  owner of ITP #1118368 rather than packaging in parallel.
